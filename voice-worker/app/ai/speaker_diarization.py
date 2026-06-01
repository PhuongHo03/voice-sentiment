"""
Speaker Diarization using WeSpeaker ONNX ResNet34 + Pure NumPy Spherical K-Means
=================================================================================
Fully PyTorch-free and HuggingFace-gating-free implementation.

Pipeline:
  1. Auto-download model.onnx from HuggingFace CDN (first run only).
  2. For each Whisper segment, extract raw PCM chunk → compute 80-dim Kaldi Fbank features.
     Short segments (< 1.5s) are padded with surrounding audio context for higher quality.
  3. Run ONNX inference → 256-dim speaker embedding vector per segment.
  4. Detect single-speaker audio (skip clustering if cosine similarity between centroids > 0.85).
  5. Cluster all embeddings with Anchor-Based Spherical K-Means (k=2) written in NumPy.
     Only high-confidence segments (>= 1.2s) anchor the initial centroid optimization;
     all segments are then assigned to the nearest centroid.
  6. Return per-segment speaker labels: "Speaker 0" / "Speaker 1".
"""

import logging
import os
import urllib.request
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
MODELS_DIR = Path("/app/models")
ONNX_MODEL_FILENAME = "wespeaker_voxceleb_resnet34.onnx"
ONNX_MODEL_PATH = MODELS_DIR / ONNX_MODEL_FILENAME

# Official HuggingFace CDN direct download URL for the quantized int8 ONNX model (~7 MB — fastest to download & run)
ONNX_DOWNLOAD_URL = (
    "https://huggingface.co/onnx-community/wespeaker-voxceleb-resnet34-LM"
    "/resolve/main/onnx/model_quantized.onnx"
)

# Fallback to fp32 model if quantized fails
ONNX_DOWNLOAD_URL_FALLBACK = (
    "https://huggingface.co/onnx-community/wespeaker-voxceleb-resnet34-LM"
    "/resolve/main/onnx/model.onnx"
)

# Audio parameters (must match what the WeSpeaker model was trained on)
SAMPLE_RATE = 16000
FBANK_NUM_BINS = 80
FBANK_FRAME_SHIFT_MS = 10.0
FBANK_FRAME_LENGTH_MS = 25.0

# Minimum segment duration to extract a meaningful embedding (seconds)
MIN_SEGMENT_DURATION_SEC = 0.3

# Context padding: extend short segments with surrounding audio context to improve embedding quality
# Segments shorter than this threshold will be padded
CONTEXT_PAD_THRESHOLD_SEC = 1.5
# Maximum padding added on each side (left/right) of a short segment
CONTEXT_PAD_MAX_SEC = 1.0

# Anchor-based clustering: only use long, clear segments to compute/refine cluster centroids
ANCHOR_MIN_DURATION_SEC = 1.2

# K-Means configuration
NUM_SPEAKERS = 2
KMEANS_MAX_ITER = 100
KMEANS_SEED = 42

# Single-speaker detection: if the two final centroids are this similar, treat as one speaker
SINGLE_SPEAKER_COSINE_THRESHOLD = 0.88


class SpeakerDiarizationClient:
    """
    Speaker diarization using WeSpeaker ONNX model + pure NumPy Spherical K-Means.
    Thread-safe: model is loaded once and cached as a class attribute.

    Key upgrades over the baseline:
    - Context Padding: short segments borrow surrounding audio for richer embeddings.
    - Spherical K-Means: centroids are L2-re-normalized after every update step,
      matching the cosine geometry of WeSpeaker embeddings.
    - Anchor-Based Clustering: only long, confident segments drive centroid updates;
      short/noisy ones are assigned afterwards.
    - Single Speaker Detection: auto-collapses two clusters into one when the audio
      contains only one voice (voicemail, monologue, etc.).
    """

    _session = None  # shared ONNX InferenceSession (lazy-loaded)

    @classmethod
    def _get_session(cls):
        if cls._session is not None:
            return cls._session

        # Ensure model directory exists
        MODELS_DIR.mkdir(parents=True, exist_ok=True)

        if not ONNX_MODEL_PATH.exists():
            cls._download_model()

        logger.info(f"Loading WeSpeaker ONNX model from: {ONNX_MODEL_PATH}")
        try:
            import onnxruntime as ort  # imported here to keep startup fast when diarization disabled
            # Use CPU execution provider only
            session_opts = ort.SessionOptions()
            session_opts.inter_op_num_threads = 2
            session_opts.intra_op_num_threads = 2
            session_opts.log_severity_level = 3  # suppress ONNX Runtime verbose logs
            cls._session = ort.InferenceSession(
                str(ONNX_MODEL_PATH),
                sess_options=session_opts,
                providers=["CPUExecutionProvider"],
            )
            input_info = cls._session.get_inputs()[0]
            output_info = cls._session.get_outputs()[0]
            logger.info(
                f"WeSpeaker ONNX loaded. "
                f"Input: '{input_info.name}' shape={input_info.shape} dtype={input_info.type}. "
                f"Output: '{output_info.name}' shape={output_info.shape}."
            )
        except Exception as e:
            logger.error(f"Failed to load WeSpeaker ONNX model: {e}")
            raise RuntimeError(f"ONNX model load failed: {e}") from e

        return cls._session

    @classmethod
    def _download_model(cls):
        for url in [ONNX_DOWNLOAD_URL, ONNX_DOWNLOAD_URL_FALLBACK]:
            logger.info(f"Downloading WeSpeaker ONNX model from: {url}")
            try:
                with urllib.request.urlopen(url, timeout=120) as resp:
                    data = resp.read()
                ONNX_MODEL_PATH.write_bytes(data)
                logger.info(
                    f"WeSpeaker ONNX model downloaded successfully: "
                    f"{ONNX_MODEL_PATH} ({len(data) / 1024 / 1024:.1f} MB)"
                )
                return
            except Exception as e:
                logger.warning(f"Failed to download from {url}: {e}. Trying fallback...")
        raise RuntimeError("All download URLs for WeSpeaker ONNX model failed.")

    # ─────────────────────────────────────────────
    # Feature extraction: Raw PCM → Kaldi 80-dim Fbank
    # ─────────────────────────────────────────────
    @staticmethod
    def _compute_fbank(waveform: np.ndarray) -> Optional[np.ndarray]:
        """
        Compute 80-dim Kaldi-compatible log-Mel filterbank features.
        Returns None if the audio is too short to produce even 1 frame.
        Shape: (T, 80) as float32.
        """
        try:
            import kaldi_native_fbank as knf
        except ImportError as e:
            raise RuntimeError(
                "kaldi-native-fbank is not installed. Add it to requirements.txt."
            ) from e

        opts = knf.FbankOptions()
        opts.mel_opts.num_bins = FBANK_NUM_BINS
        opts.frame_opts.frame_shift_ms = FBANK_FRAME_SHIFT_MS
        opts.frame_opts.frame_length_ms = FBANK_FRAME_LENGTH_MS
        opts.frame_opts.dither = 0.0  # deterministic

        computer = knf.OnlineFbank(opts)
        computer.accept_waveform(SAMPLE_RATE, waveform.tolist())
        computer.input_finished()

        num_frames = computer.num_frames_ready
        if num_frames == 0:
            return None

        features = np.stack(
            [np.array(computer.get_frame(i)) for i in range(num_frames)],
            axis=0,
        ).astype(np.float32)
        return features  # shape: (T, 80)

    # ─────────────────────────────────────────────
    # Context Padding: expand short segments with surrounding audio
    # ─────────────────────────────────────────────
    @staticmethod
    def _get_padded_chunk(
        wav_float32: np.ndarray,
        segments: list[dict],
        idx: int,
        start_sample: int,
        end_sample: int,
        duration_sec: float,
    ) -> np.ndarray:
        """
        For segments shorter than CONTEXT_PAD_THRESHOLD_SEC, symmetrically pad
        with surrounding audio up to CONTEXT_PAD_MAX_SEC (0.5s) on each side,
        but NEVER cross into adjacent segments of other turns to avoid voice contamination.
        If still shorter than 1.2s after gap-aware padding, pad the remaining difference
        symmetrically with silence (zeros) so WeSpeaker receives enough frames.
        """
        total_samples = len(wav_float32)

        if duration_sec >= CONTEXT_PAD_THRESHOLD_SEC:
            # Segment is long enough — no padding needed
            return wav_float32[start_sample:end_sample]

        pad_samples = int(CONTEXT_PAD_MAX_SEC * SAMPLE_RATE)
        padded_start = max(0, start_sample - pad_samples)
        padded_end = min(total_samples, end_sample + pad_samples)
        return wav_float32[padded_start:padded_end]

    # ─────────────────────────────────────────────
    # ONNX inference: Fbank → speaker embedding
    # ─────────────────────────────────────────────
    @classmethod
    def _extract_embedding(cls, waveform_chunk: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract a speaker embedding vector from a waveform chunk.
        Returns None if the chunk is too short.
        """
        if len(waveform_chunk) < int(MIN_SEGMENT_DURATION_SEC * SAMPLE_RATE):
            return None

        feats = cls._compute_fbank(waveform_chunk)
        if feats is None or feats.shape[0] < 10:
            return None

        # Apply Cepstral Mean Normalization (CMN) — required by WeSpeaker
        feats = feats - feats.mean(axis=0, keepdims=True)

        # Input shape for WeSpeaker ONNX: (batch=1, time_frames, freq_bins=80)
        input_tensor = feats[np.newaxis, :, :]  # (1, T, 80)

        session = cls._get_session()
        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: input_tensor})

        # Output shape: (1, embedding_dim) — typically 256 for ResNet34
        embedding = outputs[0][0]  # (embedding_dim,)
        # L2-normalize
        norm = np.linalg.norm(embedding)
        if norm > 1e-8:
            embedding = embedding / norm
        return embedding.astype(np.float32)

    # ─────────────────────────────────────────────
    # Cosine similarity helper
    # ─────────────────────────────────────────────
    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Cosine similarity between two L2-normalized vectors."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a < 1e-8 or norm_b < 1e-8:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    # ─────────────────────────────────────────────
    # Spherical K-Means with Anchor-Based Centroid Initialization
    # ─────────────────────────────────────────────
    @staticmethod
    def _spherical_kmeans(
        embeddings: np.ndarray,
        anchor_mask: np.ndarray,
        k: int = NUM_SPEAKERS,
    ) -> np.ndarray:
        """
        Anchor-Based Spherical K-Means clustering.

        - Centroid updates are driven ONLY by anchor segments (long, high-quality).
        - After convergence, ALL segments (including short/noisy ones) are assigned
          to the nearest centroid using cosine similarity.
        - Centroids are L2-normalized after every update step (Spherical K-Means),
          which matches the cosine geometry of WeSpeaker embeddings.

        Args:
            embeddings: (N, D) float32, all L2-normalized.
            anchor_mask: (N,) bool, True for high-confidence anchor segments.
            k: number of clusters.

        Returns:
            (N,) int array with cluster labels 0..k-1.
        """
        n = len(embeddings)
        if n == 0:
            return np.array([], dtype=int)
        if n == 1:
            return np.array([0], dtype=int)
        if n < k:
            return np.zeros(n, dtype=int)

        anchor_embeddings = embeddings[anchor_mask] if anchor_mask.any() else embeddings
        n_anchors = len(anchor_embeddings)

        rng = np.random.RandomState(KMEANS_SEED)

        # K-Means++ initialization on anchor embeddings for better convergence
        centers = [anchor_embeddings[rng.randint(n_anchors)].copy()]
        for _ in range(1, k):
            dists = np.array([
                min(1.0 - np.dot(e, c) for c in centers)  # cosine distance
                for e in anchor_embeddings
            ])
            dists = np.clip(dists, 0, None)
            total = dists.sum()
            if total < 1e-12:
                # All anchors are identical; pick a random one
                idx = rng.randint(n_anchors)
            else:
                probs = dists / total
                cumulative_probs = np.cumsum(probs)
                r = rng.rand()
                idx = int(np.searchsorted(cumulative_probs, r))
                idx = min(idx, n_anchors - 1)
            centers.append(anchor_embeddings[idx].copy())
        centers = np.array(centers)  # (k, D)

        # Spherical K-Means iteration — ONLY anchor segments update centers
        anchor_labels = np.zeros(n_anchors, dtype=int)
        for iteration in range(KMEANS_MAX_ITER):
            # Assignment step (cosine similarity = dot product since vectors are L2-normalized)
            sims = anchor_embeddings @ centers.T  # (n_anchors, k)
            new_labels = np.argmax(sims, axis=1)

            if np.array_equal(new_labels, anchor_labels) and iteration > 0:
                break  # Converged
            anchor_labels = new_labels

            # Update step — re-normalize centroids (Spherical K-Means)
            for j in range(k):
                mask = anchor_labels == j
                if mask.any():
                    new_center = anchor_embeddings[mask].mean(axis=0)
                    norm = np.linalg.norm(new_center)
                    if norm > 1e-8:
                        centers[j] = new_center / norm
                    # If norm is too small, keep the previous center

        # Final assignment: ALL segments → nearest centroid (cosine similarity)
        all_sims = embeddings @ centers.T  # (N, k)
        labels = np.argmax(all_sims, axis=1)
        return labels

    # ─────────────────────────────────────────────
    # Single Speaker Detection
    # ─────────────────────────────────────────────
    @staticmethod
    def _is_single_speaker(
        embeddings: np.ndarray,
        labels: np.ndarray,
        k: int = NUM_SPEAKERS,
    ) -> bool:
        """
        Detect if the audio contains only one speaker by measuring the cosine
        similarity between the two cluster centroids.

        If similarity > SINGLE_SPEAKER_COSINE_THRESHOLD, both clusters represent
        the same voice — collapse into one speaker.
        """
        centroids = []
        for j in range(k):
            mask = labels == j
            if mask.any():
                centroid = embeddings[mask].mean(axis=0)
                norm = np.linalg.norm(centroid)
                if norm > 1e-8:
                    centroids.append(centroid / norm)

        if len(centroids) < 2:
            logger.info("Single-speaker detection: fewer than 2 non-empty clusters → treating as single speaker.")
            return True

        similarity = float(np.dot(centroids[0], centroids[1]))
        logger.info(f"Single-speaker detection: centroid cosine similarity = {similarity:.4f} (threshold={SINGLE_SPEAKER_COSINE_THRESHOLD})")
        return similarity >= SINGLE_SPEAKER_COSINE_THRESHOLD

    # ─────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────
    def diarize(self, wav_float32: np.ndarray, segments: list[dict]) -> list[str]:
        """
        Run speaker diarization on the given segments.

        Args:
            wav_float32: Full audio as float32 numpy array (16kHz mono, range -1 to 1).
            segments: List of dicts with keys 'start_seconds' and 'end_seconds'.

        Returns:
            List of speaker label strings per segment, e.g. ["Speaker 0", "Speaker 1", "Speaker 0", ...].
            Length equals len(segments).
        """
        total_samples = len(wav_float32)
        embeddings = []
        valid_indices = []
        durations = []

        for i, seg in enumerate(segments):
            start_sample = int(seg["start_seconds"] * SAMPLE_RATE)
            end_sample = int(seg["end_seconds"] * SAMPLE_RATE)
            # Clamp to valid range
            start_sample = max(0, min(start_sample, total_samples - 1))
            end_sample = max(start_sample + 1, min(end_sample, total_samples))

            duration_sec = (end_sample - start_sample) / SAMPLE_RATE

            # Context Padding: extend short segments with surrounding audio
            chunk = self._get_padded_chunk(wav_float32, segments, i, start_sample, end_sample, duration_sec)

            emb = self._extract_embedding(chunk)
            if emb is not None:
                embeddings.append(emb)
                valid_indices.append(i)
                durations.append(duration_sec)

        # Default: all "Speaker 0" if no valid embeddings extracted
        labels_out = ["Speaker 0"] * len(segments)

        if not embeddings:
            logger.warning("No valid embeddings extracted from any segment. Defaulting all to 'Speaker 0'.")
            return labels_out

        emb_matrix = np.stack(embeddings, axis=0)  # (M, D)

        # Build anchor mask: segments >= ANCHOR_MIN_DURATION_SEC are high-confidence anchors
        anchor_mask = np.array([d >= ANCHOR_MIN_DURATION_SEC for d in durations], dtype=bool)
        n_anchors = anchor_mask.sum()
        logger.info(
            f"Diarization: {len(embeddings)} valid embeddings, "
            f"{n_anchors} anchor segments (>= {ANCHOR_MIN_DURATION_SEC}s)."
        )

        # Fall back to using segments >= 0.5s as anchors if we have too few real anchors,
        # to avoid using extremely short noisy segments as centroids.
        if n_anchors < NUM_SPEAKERS:
            logger.warning(
                f"Too few anchor segments ({n_anchors}). "
                "Attempting fallback to segments >= 0.5s."
            )
            anchor_mask = np.array([d >= 0.5 for d in durations], dtype=bool)
            # If still not enough, only then fall back to using all available segments
            if anchor_mask.sum() < NUM_SPEAKERS:
                logger.warning("Still too few anchors. Falling back to using all segments.")
                anchor_mask = np.ones(len(embeddings), dtype=bool)

        cluster_labels = self._spherical_kmeans(emb_matrix, anchor_mask, k=NUM_SPEAKERS)

        # Single Speaker Detection: check if both clusters represent the same voice
        if self._is_single_speaker(emb_matrix, cluster_labels, k=NUM_SPEAKERS):
            logger.info(
                "Single-speaker audio detected (centroids too similar). "
                "Collapsing all segments to 'Speaker 0'."
            )
            # All segments are assigned to Speaker 0
            return labels_out

        for list_pos, seg_idx in enumerate(valid_indices):
            labels_out[seg_idx] = f"Speaker {cluster_labels[list_pos]}"

        logger.info(
            f"Diarization complete: {len(embeddings)} embeddings → "
            f"Speaker 0 count={sum(1 for l in labels_out if l == 'Speaker 0')}, "
            f"Speaker 1 count={sum(1 for l in labels_out if l == 'Speaker 1')}."
        )
        return labels_out

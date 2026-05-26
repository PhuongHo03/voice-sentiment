"""
Speaker Diarization using WeSpeaker ONNX ResNet34 + Pure NumPy K-Means
=======================================================================
Fully PyTorch-free and HuggingFace-gating-free implementation.

Pipeline:
  1. Auto-download model.onnx from HuggingFace CDN (first run only).
  2. For each Whisper segment, extract raw PCM chunk → compute 80-dim Kaldi Fbank features.
  3. Run ONNX inference → 256-dim speaker embedding vector per segment.
  4. Cluster all embeddings with K-Means (k=2) written in NumPy.
  5. Return per-segment speaker labels: "Speaker 0" / "Speaker 1".
"""

import io
import logging
import os
import struct
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

# K-Means configuration
NUM_SPEAKERS = 2
KMEANS_MAX_ITER = 100
KMEANS_SEED = 42


class SpeakerDiarizationClient:
    """
    Speaker diarization using WeSpeaker ONNX model + pure NumPy K-Means.
    Thread-safe: model is loaded once and cached as a class attribute.
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
    # Pure NumPy K-Means clustering (k=2)
    # ─────────────────────────────────────────────
    @staticmethod
    def _kmeans_cluster(embeddings: np.ndarray, k: int = NUM_SPEAKERS) -> np.ndarray:
        """
        Runs K-Means clustering using only NumPy.
        embeddings: (N, D) float32
        Returns: (N,) int array with cluster labels 0..k-1
        """
        n = len(embeddings)
        if n == 0:
            return np.array([], dtype=int)
        if n == 1:
            return np.array([0], dtype=int)
        if n < k:
            # Not enough segments to form k clusters — assign all to cluster 0
            return np.zeros(n, dtype=int)

        rng = np.random.RandomState(KMEANS_SEED)

        # K-Means++ initialization for better convergence
        centers = [embeddings[rng.randint(n)]]
        for _ in range(1, k):
            dists = np.array([min(np.linalg.norm(e - c) ** 2 for c in centers) for e in embeddings])
            probs = dists / dists.sum()
            cumulative_probs = np.cumsum(probs)
            r = rng.rand()
            idx = np.searchsorted(cumulative_probs, r)
            centers.append(embeddings[min(idx, n - 1)])
        centers = np.array(centers)  # (k, D)

        labels = np.zeros(n, dtype=int)
        for iteration in range(KMEANS_MAX_ITER):
            # Assignment step
            dists = np.linalg.norm(embeddings[:, np.newaxis, :] - centers[np.newaxis, :, :], axis=2)  # (N, k)
            new_labels = np.argmin(dists, axis=1)

            if np.array_equal(new_labels, labels) and iteration > 0:
                break  # Converged
            labels = new_labels

            # Update step
            for j in range(k):
                mask = labels == j
                if mask.any():
                    centers[j] = embeddings[mask].mean(axis=0)

        return labels

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

        for i, seg in enumerate(segments):
            start_sample = int(seg["start_seconds"] * SAMPLE_RATE)
            end_sample = int(seg["end_seconds"] * SAMPLE_RATE)
            # Clamp to valid range
            start_sample = max(0, min(start_sample, total_samples - 1))
            end_sample = max(start_sample + 1, min(end_sample, total_samples))

            chunk = wav_float32[start_sample:end_sample]
            emb = self._extract_embedding(chunk)
            if emb is not None:
                embeddings.append(emb)
                valid_indices.append(i)

        # Default: all "Speaker 0" if no valid embeddings extracted
        labels_out = ["Speaker 0"] * len(segments)

        if not embeddings:
            logger.warning("No valid embeddings extracted from any segment. Defaulting all to 'Speaker 0'.")
            return labels_out

        emb_matrix = np.stack(embeddings, axis=0)  # (M, D)
        cluster_labels = self._kmeans_cluster(emb_matrix, k=NUM_SPEAKERS)

        for list_pos, seg_idx in enumerate(valid_indices):
            labels_out[seg_idx] = f"Speaker {cluster_labels[list_pos]}"

        logger.info(
            f"Diarization complete: {len(embeddings)} embeddings → "
            f"Speaker 0 count={sum(1 for l in labels_out if l == 'Speaker 0')}, "
            f"Speaker 1 count={sum(1 for l in labels_out if l == 'Speaker 1')}."
        )
        return labels_out

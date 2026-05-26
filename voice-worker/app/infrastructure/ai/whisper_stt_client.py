import io
import logging
import struct
import subprocess

import numpy as np
from faster_whisper import WhisperModel

from app.core.config import settings
from app.infrastructure.ai.speaker_diarization import SpeakerDiarizationClient

logger = logging.getLogger(__name__)


class WhisperSpeechToTextClient:
    def __init__(self):
        # We use the 'small' model which offers the perfect balance of Vietnamese ASR accuracy and CPU speed.
        # Run on CPU with int8 quantization for minimal system RAM footprint and fast performance.
        self.model_size = "small"
        self._model = None
        self._diarizer = SpeakerDiarizationClient()

    @property
    def model(self) -> WhisperModel:
        if self._model is None:
            logger.info(f"Initializing faster-whisper model '{self.model_size}' on CPU (int8)...")
            try:
                self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
                logger.info("faster-whisper model loaded successfully!")
            except Exception as e:
                logger.error(f"Failed to load faster-whisper model: {str(e)}")
                raise
        return self._model

    def normalize_to_wav(self, audio_bytes: bytes) -> bytes:
        """
        Normalizes any input audio (mp3, webm, wav, etc.) to 16kHz, mono, 16-bit PCM WAV
        using ffmpeg through a subprocess.
        """
        if not audio_bytes:
            raise ValueError("Audio content is empty.")

        cmd = [
            "ffmpeg",
            "-y",                    # overwrite output files
            "-i", "pipe:0",          # read input from stdin
            "-f", "wav",             # output format wav
            "-acodec", "pcm_s16le",  # 16-bit signed PCM
            "-ac", "1",              # mono channel
            "-ar", "16000",          # 16000 Hz sample rate
            "pipe:1"                 # write output to stdout
        ]

        try:
            logger.info("Starting FFmpeg audio normalization...")
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate(input=audio_bytes)

            if process.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="ignore")
                logger.error(f"FFmpeg failed with code {process.returncode}: {error_msg}")
                raise RuntimeError(f"FFmpeg audio normalization failed: {error_msg}")

            logger.info(f"Successfully normalized audio. Original size: {len(audio_bytes)} bytes, Output size: {len(stdout)} bytes")
            return stdout
        except FileNotFoundError as exc:
            logger.error("FFmpeg executable not found. Ensure FFmpeg is installed in the system/container path.")
            raise RuntimeError("FFmpeg executable is not found in PATH.") from exc
        except Exception as exc:
            logger.error(f"Error during audio normalization: {str(exc)}")
            raise

    @staticmethod
    def _wav_bytes_to_float32(wav_bytes: bytes) -> np.ndarray:
        """
        Parse a 16-bit PCM WAV byte-string (output of ffmpeg) into a float32 numpy array
        normalized to [-1.0, +1.0].  This avoids any extra runtime dependency.
        """
        # Skip the 44-byte WAV header (standard PCM RIFF header)
        pcm_data = wav_bytes[44:]
        n_samples = len(pcm_data) // 2  # 16-bit = 2 bytes per sample
        samples = struct.unpack(f"<{n_samples}h", pcm_data[:n_samples * 2])
        arr = np.array(samples, dtype=np.float32) / 32768.0
        return arr

    def transcribe(self, audio: bytes) -> list[dict]:
        """
        Transcribes the given audio bytes using faster-whisper, then runs ONNX-based
        speaker diarization (WeSpeaker ResNet34) to assign 'Speaker 0'/'Speaker 1' labels
        to each segment based on voice embeddings — not naive alternating.
        """
        logger.info("Starting local faster-whisper transcription on CPU...")
        try:
            # 1. Normalize audio to standard WAV format (16kHz, mono, 16-bit PCM)
            normalized_wav = self.normalize_to_wav(audio)

            audio_file = io.BytesIO(normalized_wav)

            # 2. Parse language code from voice_language_code setting (e.g. 'vi-VN' -> 'vi')
            lang = None
            if settings.voice_language_code and settings.voice_language_code.lower() != "auto":
                lang = settings.voice_language_code.split("-")[0]

            if lang:
                logger.info(f"Transcribing audio with explicit language: {lang} (Configured: {settings.voice_language_code})")
            else:
                logger.info("Transcribing audio with AUTOMATIC language detection...")

            # 3. Run Whisper ASR
            segments, info = self.model.transcribe(audio_file, language=lang, beam_size=5)

            if not lang and info:
                logger.info(f"Auto-detected language: '{info.language}' with probability {info.language_probability:.2f}")

            # 4. Collect raw segment data from Whisper (generator must be consumed before diarization)
            raw_segments = []
            for segment in segments:
                raw_segments.append({
                    "text": segment.text.strip(),
                    "start_seconds": round(segment.start, 2),
                    "end_seconds": round(segment.end, 2),
                })
            logger.info(f"faster-whisper transcription completed. Found {len(raw_segments)} segments.")

            if not raw_segments:
                return []

            # 5. Run ONNX speaker diarization
            #    Convert WAV bytes → float32 array for diarization model
            try:
                wav_float32 = self._wav_bytes_to_float32(normalized_wav)
                speaker_labels = self._diarizer.diarize(wav_float32, raw_segments)
                logger.info("ONNX speaker diarization completed successfully.")
            except Exception as diar_err:
                # Non-fatal: if diarization fails, fall back to "Speaker 0" for all
                logger.warning(f"Speaker diarization failed (falling back to default): {diar_err}")
                speaker_labels = ["Speaker 0"] * len(raw_segments)

            # 6. Assemble final turn list
            turns = []
            for seg, spk_label in zip(raw_segments, speaker_labels):
                turns.append({
                    "speaker": spk_label,   # "Speaker 0" or "Speaker 1" — LLM will map to roles
                    "text": seg["text"],
                    "start_seconds": seg["start_seconds"],
                    "end_seconds": seg["end_seconds"],
                })

            return turns

        except Exception as e:
            logger.error(f"Error during faster-whisper transcription: {str(e)}")
            raise RuntimeError(f"Whisper ASR failed: {str(e)}") from e

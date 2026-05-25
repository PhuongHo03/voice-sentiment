import io
import logging
from faster_whisper import WhisperModel
from app.core.config import settings

logger = logging.getLogger(__name__)


class WhisperSpeechToTextClient:
    def __init__(self):
        # We use the 'small' model which offers the perfect balance of Vietnamese ASR accuracy and CPU speed.
        # Run on CPU with int8 quantization for minimal system RAM footprint and fast performance.
        self.model_size = "small"
        self._model = None

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

    def transcribe(self, audio: bytes) -> list[dict]:
        """
        Transcribes the given audio bytes using faster-whisper.
        """
        logger.info("Starting local faster-whisper transcription on CPU...")
        try:
            audio_file = io.BytesIO(audio)
            # Parse language code from voice_language_code setting (e.g. 'vi-VN' -> 'vi')
            lang = None
            if settings.voice_language_code and settings.voice_language_code.lower() != "auto":
                lang = settings.voice_language_code.split("-")[0]

            if lang:
                logger.info(f"Transcribing audio with explicit language: {lang} (Configured: {settings.voice_language_code})")
            else:
                logger.info("Transcribing audio with AUTOMATIC language detection...")

            segments, info = self.model.transcribe(audio_file, language=lang, beam_size=5)
            
            if not lang and info:
                logger.info(f"Auto-detected language: '{info.language}' with probability {info.language_probability:.2f}")

            turns = []
            for segment in segments:
                turns.append({
                    "speaker": "Khách hàng",  # Label default speaker
                    "text": segment.text.strip(),
                    "start_seconds": round(segment.start, 1),
                    "end_seconds": round(segment.end, 1)
                })
                
            logger.info(f"faster-whisper transcription completed successfully. Found {len(turns)} segments.")
            return turns
        except Exception as e:
            logger.error(f"Error during faster-whisper transcription: {str(e)}")
            raise RuntimeError(f"Whisper ASR failed: {str(e)}") from e

from app.ai.whisper_stt_client import WhisperSpeechToTextClient


class TranscriptionService:
    def __init__(self, stt_client: WhisperSpeechToTextClient | None = None):
        self.stt_client = stt_client or WhisperSpeechToTextClient()

    def transcribe(self, filename: str | None, content: bytes) -> dict:
        turns = self.stt_client.transcribe(content)
        return {"filename": filename, "turns": turns}

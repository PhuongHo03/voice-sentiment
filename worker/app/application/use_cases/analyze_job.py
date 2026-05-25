from app.infrastructure.ai.whisper_stt_client import WhisperSpeechToTextClient
from app.infrastructure.ai.llm_client import LlmTextAnalyticsClient
from app.infrastructure.cache.redis_cache import RedisJobCache
from app.infrastructure.database.analysis_repository import SqlAlchemyAnalysisRepository
from app.infrastructure.storage.minio_storage import MinioAudioStorage


class AnalyzeJob:
    def __init__(self, repository: SqlAlchemyAnalysisRepository, storage: MinioAudioStorage, cache: RedisJobCache, stt: WhisperSpeechToTextClient, analytics: LlmTextAnalyticsClient):

        self.repository = repository
        self.storage = storage
        self.cache = cache
        self.stt = stt
        self.analytics = analytics

    def execute(self, message: dict) -> None:
        job_id = message["job_id"]
        self.repository.mark_processing(job_id)
        self.cache.set_status(job_id, {"job_id": job_id, "status": "processing"})
        try:
            if message["input_type"] == "audio":
                audio = self.storage.read(message["audio_object_key"])
                transcript = self.stt.transcribe(audio)
            else:
                transcript = [{"speaker": "unknown", "text": message["text"], "start_seconds": None, "end_seconds": None}]
            analytics = self.analytics.analyze(transcript)
            result = {"transcript": transcript, **analytics}
            self.repository.save_completed(job_id, result)
            self.cache.set_status(job_id, {"job_id": job_id, "status": "completed", "result": result})
        except Exception as exc:
            self.repository.save_failed(job_id, str(exc))
            self.cache.set_status(job_id, {"job_id": job_id, "status": "failed", "error_message": str(exc)})
            raise

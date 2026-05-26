import logging
import httpx
from app.core.config import settings
from app.infrastructure.ai.llm_client import LlmTextAnalyticsClient
from app.infrastructure.cache.redis_cache import RedisJobCache
from app.infrastructure.database.analysis_repository import SqlAlchemyAnalysisRepository
from app.infrastructure.storage.minio_storage import MinioAudioStorage

logger = logging.getLogger(__name__)


class AnalyzeJob:
    def __init__(
        self,
        repository: SqlAlchemyAnalysisRepository,
        storage: MinioAudioStorage,
        cache: RedisJobCache,
        analytics: LlmTextAnalyticsClient
    ):
        self.repository = repository
        self.storage = storage
        self.cache = cache
        self.analytics = analytics

    def execute(self, message: dict) -> None:
        job_id = message["job_id"]
        logger.info(f"Starting orchestration execution for Job ID: {job_id} (Input Type: {message['input_type']})")
        
        self.repository.mark_processing(job_id)
        self.cache.set_status(job_id, {"job_id": job_id, "status": "processing"})
        
        try:
            if message["input_type"] == "audio":
                logger.info(f"Retrieving raw audio from MinIO: '{message['audio_object_key']}'...")
                audio = self.storage.read(message["audio_object_key"])
                
                # Make HTTP POST call to stateless voice-worker web server
                voice_url = f"{settings.voice_server_uri.rstrip('/')}/api/transcribe"
                logger.info(f"Connecting to stateless voice-worker server to transcribe audio at: '{voice_url}'...")
                
                files = {'file': (message.get("audio_object_key", "audio.wav"), audio, 'audio/wav')}
                try:
                    with httpx.Client(timeout=1800) as client:
                        response = client.post(voice_url, files=files)
                        response.raise_for_status()
                        result_data = response.json()
                        transcript = result_data["turns"]
                        logger.info(f"Audio transcription completed by voice-worker! Found {len(transcript)} segments.")
                except httpx.HTTPError as http_err:
                    logger.error(f"HTTP connection to voice-worker failed: {str(http_err)}")
                    raise RuntimeError(f"Voice-worker STT service connection failed: {str(http_err)}") from http_err
            else:
                logger.info("Direct text input detected. Bypassing voice-worker STT...")
                transcript = [{"speaker": "unknown", "text": message["text"], "start_seconds": None, "end_seconds": None}]

            logger.info("Sending transcript turns to remote LLM server for analysis...")
            analytics = self.analytics.analyze(transcript)
            
            result = {"transcript": transcript, **analytics}
            
            logger.info("Saving completed analysis results to PostgreSQL and caching to Redis...")
            self.repository.save_completed(job_id, result)
            self.cache.set_status(job_id, {"job_id": job_id, "status": "completed", "result": result})
            logger.info(f"Job ID: {job_id} successfully completed and saved!")
            
        except Exception as exc:
            logger.error(f"Job execution failed for Job ID: {job_id} - Error: {str(exc)}")
            self.repository.save_failed(job_id, str(exc))
            self.cache.set_status(job_id, {"job_id": job_id, "status": "failed", "error_message": str(exc)})
            raise

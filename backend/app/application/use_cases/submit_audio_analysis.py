from app.infrastructure.database.analysis_repository import SqlAlchemyAnalysisRepository
from app.infrastructure.queue.rabbitmq_publisher import RabbitMqJobPublisher
from app.infrastructure.storage.minio_storage import MinioAudioStorage
from app.infrastructure.cache.redis_cache import RedisJobCache


class SubmitAudioAnalysis:
    def __init__(self, repository: SqlAlchemyAnalysisRepository, storage: MinioAudioStorage, publisher: RabbitMqJobPublisher):
        self.repository = repository
        self.storage = storage
        self.publisher = publisher

    def execute(self, filename: str, content: bytes, content_type: str, owner_id: str | None = None) -> dict:
        object_key = self.storage.save(filename, content, content_type, owner_id=owner_id)
        job = self.repository.create_audio_job(object_key, name=filename, owner_id=owner_id)
        
        # 1. Publish to RabbitMQ queue
        self.publisher.publish({"job_id": str(job.id), "input_type": "audio", "audio_object_key": object_key, "owner_id": owner_id}, owner_id=owner_id)
        
        # 2. Cache initial 'pending' status in Redis immediately to avoid PostgreSQL polling overhead
        try:
            RedisJobCache().set_status(str(job.id), {"job_id": str(job.id), "status": "pending"}, owner_id=owner_id)
        except Exception as e:
            # Non-blocking caching write
            import logging
            logging.getLogger(__name__).warning(f"Failed to cache pending job {job.id}: {e}")

        return {"job_id": str(job.id), "status": job.status}

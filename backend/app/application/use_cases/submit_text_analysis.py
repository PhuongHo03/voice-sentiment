from app.infrastructure.database.analysis_repository import SqlAlchemyAnalysisRepository
from app.infrastructure.queue.rabbitmq_publisher import RabbitMqJobPublisher
from app.infrastructure.cache.redis_cache import RedisJobCache


class SubmitTextAnalysis:
    def __init__(self, repository: SqlAlchemyAnalysisRepository, publisher: RabbitMqJobPublisher):
        self.repository = repository
        self.publisher = publisher

    def execute(self, text: str, owner_id: str | None = None) -> dict:
        name = text[:60] + "..." if len(text) > 60 else text
        job = self.repository.create_text_job(text, name=name, owner_id=owner_id)
        
        # 1. Publish to RabbitMQ queue
        self.publisher.publish({"job_id": str(job.id), "input_type": "text", "text": text, "owner_id": owner_id}, owner_id=owner_id)
        
        # 2. Cache initial 'pending' status in Redis immediately to avoid PostgreSQL polling overhead
        try:
            RedisJobCache().set_status(str(job.id), {"job_id": str(job.id), "status": "pending"}, owner_id=owner_id)
        except Exception as e:
            # Non-blocking caching write
            import logging
            logging.getLogger(__name__).warning(f"Failed to cache pending job {job.id}: {e}")

        return {"job_id": str(job.id), "status": job.status}

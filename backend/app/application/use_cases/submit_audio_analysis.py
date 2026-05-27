from app.infrastructure.database.analysis_repository import SqlAlchemyAnalysisRepository
from app.infrastructure.queue.rabbitmq_publisher import RabbitMqJobPublisher
from app.infrastructure.storage.minio_storage import MinioAudioStorage


class SubmitAudioAnalysis:
    def __init__(self, repository: SqlAlchemyAnalysisRepository, storage: MinioAudioStorage, publisher: RabbitMqJobPublisher):
        self.repository = repository
        self.storage = storage
        self.publisher = publisher

    def execute(self, filename: str, content: bytes, content_type: str, owner_id: str | None = None) -> dict:
        object_key = self.storage.save(filename, content, content_type, owner_id=owner_id)
        job = self.repository.create_audio_job(object_key, name=filename, owner_id=owner_id)
        self.publisher.publish({"job_id": str(job.id), "input_type": "audio", "audio_object_key": object_key, "owner_id": owner_id}, owner_id=owner_id)
        return {"job_id": str(job.id), "status": job.status}

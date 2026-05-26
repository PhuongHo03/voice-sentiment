from app.infrastructure.database.analysis_repository import SqlAlchemyAnalysisRepository
from app.infrastructure.queue.rabbitmq_publisher import RabbitMqJobPublisher
from app.infrastructure.storage.minio_storage import MinioAudioStorage


class SubmitAudioAnalysis:
    def __init__(self, repository: SqlAlchemyAnalysisRepository, storage: MinioAudioStorage, publisher: RabbitMqJobPublisher):
        self.repository = repository
        self.storage = storage
        self.publisher = publisher

    def execute(self, filename: str, content: bytes, content_type: str) -> dict:
        object_key = self.storage.save(filename, content, content_type)
        job = self.repository.create_audio_job(object_key, name=filename)
        self.publisher.publish({"job_id": str(job.id), "input_type": "audio", "audio_object_key": object_key})
        return {"job_id": str(job.id), "status": job.status}

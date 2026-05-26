from app.infrastructure.database.analysis_repository import SqlAlchemyAnalysisRepository
from app.infrastructure.queue.rabbitmq_publisher import RabbitMqJobPublisher


class SubmitTextAnalysis:
    def __init__(self, repository: SqlAlchemyAnalysisRepository, publisher: RabbitMqJobPublisher):
        self.repository = repository
        self.publisher = publisher

    def execute(self, text: str) -> dict:
        name = text[:60] + "..." if len(text) > 60 else text
        job = self.repository.create_text_job(text, name=name)
        self.publisher.publish({"job_id": str(job.id), "input_type": "text", "text": text})
        return {"job_id": str(job.id), "status": job.status}

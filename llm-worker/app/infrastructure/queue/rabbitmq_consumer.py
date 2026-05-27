import json
import logging
import pika
from app.core.config import settings
from app.infrastructure.ai.llm_client import LlmTextAnalyticsClient
from app.infrastructure.cache.redis_cache import RedisJobCache
from app.infrastructure.database.analysis_repository import SqlAlchemyAnalysisRepository
from app.infrastructure.database.session import SessionLocal
from app.infrastructure.storage.minio_storage import MinioAudioStorage
from app.application.use_cases.analyze_job import AnalyzeJob

logger = logging.getLogger(__name__)


class RabbitMqAnalysisConsumer:
    queue_name = "analysis.jobs"

    def start(self) -> None:
        logger.info(f"Connecting to RabbitMQ Broker: '{settings.rabbitmq_url}'...")
        params = pika.URLParameters(settings.rabbitmq_url)
        params.heartbeat = 0  # Disable heartbeats to prevent timeouts during long voice transcription HTTP calls
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.queue_declare(queue=self.queue_name, durable=True)
        channel.basic_qos(prefetch_count=1)

        def handle(_, method, __, body: bytes) -> None:
            message = json.loads(body.decode("utf-8"))
            job_id = message.get("job_id")
            logger.info(f"Received consumed job from queue: '{method.routing_key}' - Job ID: {job_id}")
            
            with SessionLocal() as session:
                use_case = AnalyzeJob(
                    SqlAlchemyAnalysisRepository(session),
                    MinioAudioStorage(),
                    RedisJobCache(),
                    LlmTextAnalyticsClient()
                )

                try:
                    use_case.execute(message)
                    channel.basic_ack(delivery_tag=method.delivery_tag)
                    logger.info(f"Acknowledged Job ID: {job_id}")
                except Exception as exc:
                    logger.error(f"Error handling Job ID: {job_id} - {str(exc)}. Message acknowledged anyway.")
                    channel.basic_ack(delivery_tag=method.delivery_tag)

        count = settings.rabbitmq_queue_count
        if count <= 1:
            queues = ["analysis.jobs"]
        else:
            queues = [f"analysis.jobs.{i}" for i in range(1, count + 1)]

        for q in queues:
            channel.queue_declare(queue=q, durable=True)
            channel.basic_consume(queue=q, on_message_callback=handle)
            logger.info(f"Waiting for jobs on queue: '{q}'...")

        channel.start_consuming()

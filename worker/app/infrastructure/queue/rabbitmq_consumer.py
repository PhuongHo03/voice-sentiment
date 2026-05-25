import json

import pika

from app.core.config import settings
from app.infrastructure.ai.whisper_stt_client import WhisperSpeechToTextClient
from app.infrastructure.ai.llm_client import LlmTextAnalyticsClient
from app.infrastructure.cache.redis_cache import RedisJobCache
from app.infrastructure.database.analysis_repository import SqlAlchemyAnalysisRepository
from app.infrastructure.database.session import SessionLocal
from app.infrastructure.storage.minio_storage import MinioAudioStorage
from app.application.use_cases.analyze_job import AnalyzeJob


class RabbitMqAnalysisConsumer:
    queue_name = "analysis.jobs"

    def start(self) -> None:
        connection = pika.BlockingConnection(pika.URLParameters(settings.rabbitmq_url))
        channel = connection.channel()
        channel.queue_declare(queue=self.queue_name, durable=True)
        channel.basic_qos(prefetch_count=1)

        def handle(_, method, __, body: bytes) -> None:
            message = json.loads(body.decode("utf-8"))
            with SessionLocal() as session:
                use_case = AnalyzeJob(SqlAlchemyAnalysisRepository(session), MinioAudioStorage(), RedisJobCache(), WhisperSpeechToTextClient(), LlmTextAnalyticsClient())

                try:
                    use_case.execute(message)
                    channel.basic_ack(delivery_tag=method.delivery_tag)
                except Exception:
                    channel.basic_ack(delivery_tag=method.delivery_tag)

        channel.basic_consume(queue=self.queue_name, on_message_callback=handle)
        channel.start_consuming()

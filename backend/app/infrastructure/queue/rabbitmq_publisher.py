import json

import pika

from app.core.config import settings


class RabbitMqJobPublisher:
    queue_name = "analysis.jobs"

    def publish(self, message: dict) -> None:
        connection = pika.BlockingConnection(pika.URLParameters(settings.rabbitmq_url))
        channel = connection.channel()
        channel.queue_declare(queue=self.queue_name, durable=True)
        channel.basic_publish("", self.queue_name, json.dumps(message).encode("utf-8"), pika.BasicProperties(delivery_mode=2))
        connection.close()

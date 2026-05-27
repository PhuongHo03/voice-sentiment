import hashlib
import random
import pika
import json

from app.core.config import settings


class RabbitMqJobPublisher:
    def publish(self, message: dict, owner_id: str | None = None) -> None:
        count = settings.rabbitmq_queue_count
        if count <= 1:
            target_queue = "analysis.jobs"
        else:
            # Deterministically route by hashing owner_id if present, or route randomly
            if owner_id:
                hasher = hashlib.md5(owner_id.encode("utf-8"))
                queue_idx = (int(hasher.hexdigest(), 16) % count) + 1
            else:
                queue_idx = random.randint(1, count)
            target_queue = f"analysis.jobs.{queue_idx}"

        connection = pika.BlockingConnection(pika.URLParameters(settings.rabbitmq_url))
        channel = connection.channel()
        channel.queue_declare(queue=target_queue, durable=True)
        channel.basic_publish("", target_queue, json.dumps(message).encode("utf-8"), pika.BasicProperties(delivery_mode=2))
        connection.close()

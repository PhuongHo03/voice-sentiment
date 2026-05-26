import logging
from app.infrastructure.queue.rabbitmq_consumer import RabbitMqAnalysisConsumer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger("llm_worker_main")

if __name__ == "__main__":
    logger.info("Starting RabbitMQ LLM Analysis Worker...")
    RabbitMqAnalysisConsumer().start()

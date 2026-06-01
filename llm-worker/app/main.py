import logging
from app.configs.metrics import start_metrics_server
from app.configs.queue import RabbitMqAnalysisConsumer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger("llm_worker_main")

if __name__ == "__main__":
    start_metrics_server()
    logger.info("Starting RabbitMQ LLM Analysis Worker with metrics on 0.0.0.0:9100...")
    RabbitMqAnalysisConsumer().start()

import logging
from app.configs.metrics import start_metrics_server
from app.configs.queue import RabbitMqAnalysisConsumer

import os

log_dir = "/app/logs"
try:
    os.makedirs(log_dir, exist_ok=True)
    test_file = os.path.join(log_dir, ".write_test")
    with open(test_file, "w") as f:
        f.write("test")
    os.remove(test_file)
except (PermissionError, OSError):
    log_dir = "./logs"
    os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(log_dir, "llm-worker.log"), encoding="utf-8")
    ]
)

logger = logging.getLogger("llm_worker_main")

if __name__ == "__main__":
    start_metrics_server()
    logger.info("Starting RabbitMQ LLM Analysis Worker with metrics on 0.0.0.0:9100...")
    RabbitMqAnalysisConsumer().start()

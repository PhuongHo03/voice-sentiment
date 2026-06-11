import logging
import threading
import time

from app.configs.cache import RedisJobCache
from app.configs.queue import RabbitMqJobPublisher
from app.configs.session import SessionLocal
from app.repositories.analysis_repository import SqlAlchemyAnalysisRepository
from app.services.analysis_service import AnalysisService, JOB_RECOVERY_INTERVAL_SECONDS

logger = logging.getLogger(__name__)


def run_stuck_job_recovery_once() -> int:
    with SessionLocal() as session:
        service = AnalysisService(
            SqlAlchemyAnalysisRepository(session),
            RedisJobCache(),
            RabbitMqJobPublisher(),
        )
        return service.recover_stuck_jobs()


def start_stuck_job_recovery_loop() -> None:
    def _loop() -> None:
        logger.info("Starting stuck analysis job recovery loop.")
        while True:
            try:
                run_stuck_job_recovery_once()
            except Exception as exc:
                logger.error(f"Stuck analysis job recovery failed: {exc}")
            time.sleep(JOB_RECOVERY_INTERVAL_SECONDS)

    thread = threading.Thread(target=_loop, name="stuck-job-recovery", daemon=True)
    thread.start()

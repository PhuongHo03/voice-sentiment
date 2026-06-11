import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from alembic.config import Config
from alembic import command

from app.configs.config import settings
from app.configs.metrics import PrometheusMiddleware, metrics_response
from app.controllers.analysis_controller import router as analysis_router
from app.controllers.health_controller import router as health_router
from app.controllers.auth_controller import router as auth_router
from app.controllers.admin_controller import router as admin_router
from app.controllers.files_controller import router as files_router
from app.services.job_recovery_service import start_stuck_job_recovery_loop

logger = logging.getLogger(__name__)

app = FastAPI(title="Voice Sentiment Backend")
app.add_middleware(PrometheusMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(health_router)
app.include_router(analysis_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(files_router)
app.add_api_route("/metrics", metrics_response, methods=["GET"], include_in_schema=False)


@app.on_event("startup")
def startup() -> None:
    logger.info("Running database migrations via Alembic...")
    try:
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations applied successfully!")
        start_stuck_job_recovery_loop()
    except Exception as exc:
        logger.error(f"Failed to apply database migrations: {str(exc)}")
        raise

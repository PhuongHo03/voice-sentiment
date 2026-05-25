import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from alembic.config import Config
from alembic import command

from app.core.config import settings
from app.interfaces.controllers.analysis_controller import router as analysis_router
from app.interfaces.controllers.health_controller import router as health_router

logger = logging.getLogger(__name__)

app = FastAPI(title="Voice Sentiment Backend")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(health_router)
app.include_router(analysis_router)


@app.on_event("startup")
def startup() -> None:
    logger.info("Running database migrations via Alembic...")
    try:
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations applied successfully!")
    except Exception as exc:
        logger.error(f"Failed to apply database migrations: {str(exc)}")
        raise


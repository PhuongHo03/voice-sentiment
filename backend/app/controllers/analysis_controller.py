from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.configs.cache import RedisJobCache
from app.configs.metrics import ANALYSIS_SUBMISSIONS_TOTAL
from app.configs.queue import RabbitMqJobPublisher
from app.configs.session import get_session
from app.configs.storage import MinioAudioStorage
from app.dtos.analysis_schema import (
    AudioFromKeyRequest,
    JobAcceptedResponse,
    JobStatusResponse,
    RenameRequest,
    SessionListResponse,
    TextAnalysisRequest,
)
from app.middlewares.dependencies import get_current_user
from app.models.models import UserModel
from app.repositories.analysis_repository import SqlAlchemyAnalysisRepository
from app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/api/analysis", tags=["analysis"])
SUPPORTED_AUDIO_TYPES = {"audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav", "audio/webm", "audio/mp4", "video/mp4"}


def _analysis_service(session: Session) -> AnalysisService:
    return AnalysisService(SqlAlchemyAnalysisRepository(session), RedisJobCache(), RabbitMqJobPublisher(), MinioAudioStorage())


@router.post("/audio", response_model=JobAcceptedResponse)
async def analyze_audio(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    if file.content_type not in SUPPORTED_AUDIO_TYPES:
        raise HTTPException(status_code=400, detail="Only .mp3, .wav, .webm, and .mp4 audio/video uploads are supported")
    content = await file.read()
    result = _analysis_service(session).submit_audio(file.filename or "audio.bin", content, file.content_type or "application/octet-stream", owner_id=current_user.id)
    ANALYSIS_SUBMISSIONS_TOTAL.labels("audio").inc()
    return result


@router.post("/text", response_model=JobAcceptedResponse)
def analyze_text(
    payload: TextAnalysisRequest,
    session: Session = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    result = _analysis_service(session).submit_text(payload.text, owner_id=current_user.id)
    ANALYSIS_SUBMISSIONS_TOTAL.labels("text").inc()
    return result


@router.post("/audio-from-key", response_model=JobAcceptedResponse)
def analyze_audio_from_key(
    payload: AudioFromKeyRequest,
    session: Session = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    result = _analysis_service(session).submit_audio_from_key(payload.object_key, payload.name, owner_id=current_user.id)
    ANALYSIS_SUBMISSIONS_TOTAL.labels("audio").inc()
    return result


@router.get("", response_model=SessionListResponse)
def list_sessions(
    limit: int = 20,
    offset: int = 0,
    session: Session = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    return _analysis_service(session).list_sessions(limit, offset, owner_id=current_user.id)


@router.get("/stats")
def get_stats(
    session: Session = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    return _analysis_service(session).get_stats(owner_id=current_user.id)


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_analysis(
    job_id: str,
    session: Session = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    return _analysis_service(session).get_analysis(job_id, current_user)


@router.patch("/{job_id}", response_model=JobStatusResponse)
def rename_session(
    job_id: str,
    payload: RenameRequest,
    session: Session = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    return _analysis_service(session).rename_session(job_id, payload.name, current_user)


@router.delete("/{job_id}")
def delete_session(
    job_id: str,
    session: Session = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    return _analysis_service(session).delete_session(job_id, current_user)

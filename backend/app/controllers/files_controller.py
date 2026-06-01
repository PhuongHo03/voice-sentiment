from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.configs.session import get_session
from app.middlewares.dependencies import get_current_user
from app.models.models import UserModel
from app.repositories.analysis_repository import SqlAlchemyAnalysisRepository
from app.services.file_service import FileService

router = APIRouter(prefix="/api/files", tags=["files"])
SUPPORTED_AUDIO_TYPES = {"audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav", "audio/webm", "audio/mp4", "video/mp4"}


@router.post("/upload")
async def upload_user_file(
    file: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    """Upload a file to MinIO without starting analysis. Returns object metadata."""
    if file.content_type not in SUPPORTED_AUDIO_TYPES:
        raise HTTPException(status_code=400, detail="Only .mp3, .wav, .webm, and .mp4 audio/video uploads are supported")
    content = await file.read()
    return FileService().upload(file.filename or "audio.bin", content, file.content_type or "application/octet-stream", current_user.id)


@router.get("")
def list_user_files(current_user: UserModel = Depends(get_current_user)) -> dict[str, Any]:
    """List all audio files uploaded to MinIO by the current user."""
    return FileService().list_files(current_user.id)


@router.get("/url")
def get_file_presigned_url(
    object_key: str,
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, str]:
    """Generate a presigned URL for a file owned by the current user."""
    return FileService().get_presigned_url(object_key, current_user.id)


@router.get("/stream")
def stream_file(
    object_key: str,
    request: Request,
    token: str | None = None,
    db: Session = Depends(get_session),
) -> StreamingResponse:
    """Stream a file owned by the current user from MinIO directly through the backend."""
    return FileService(SqlAlchemyAnalysisRepository(db)).stream(object_key, request, token)


@router.delete("")
def delete_user_file(
    object_key: str,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> dict[str, str]:
    """Delete a file from MinIO owned by the current user."""
    return FileService(SqlAlchemyAnalysisRepository(db)).delete(object_key, current_user.id)

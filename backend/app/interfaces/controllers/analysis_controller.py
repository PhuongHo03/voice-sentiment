from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.application.use_cases.submit_audio_analysis import SubmitAudioAnalysis
from app.application.use_cases.submit_text_analysis import SubmitTextAnalysis
from app.infrastructure.cache.redis_cache import RedisJobCache
from app.infrastructure.database.analysis_repository import SqlAlchemyAnalysisRepository
from app.infrastructure.database.session import get_session
from app.infrastructure.queue.rabbitmq_publisher import RabbitMqJobPublisher
from app.infrastructure.storage.minio_storage import MinioAudioStorage
from app.interfaces.schemas.analysis_schema import (
    JobAcceptedResponse,
    JobStatusResponse,
    TextAnalysisRequest,
    SessionListResponse,
    SessionListItem,
    RenameRequest,
)
from app.infrastructure.dependencies import get_current_user
from app.infrastructure.database.models import UserModel

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.post("/audio", response_model=JobAcceptedResponse)
async def analyze_audio(
    file: UploadFile = File(...), 
    session: Session = Depends(get_session),
    current_user: UserModel = Depends(get_current_user)
) -> dict:
    if file.content_type not in {"audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav", "audio/webm", "audio/mp4", "video/mp4"}:
        raise HTTPException(status_code=400, detail="Only .mp3, .wav, .webm, and .mp4 audio/video uploads are supported")
    content = await file.read()
    use_case = SubmitAudioAnalysis(SqlAlchemyAnalysisRepository(session), MinioAudioStorage(), RabbitMqJobPublisher())
    return use_case.execute(file.filename or "audio.bin", content, file.content_type or "application/octet-stream", owner_id=current_user.id)


@router.post("/text", response_model=JobAcceptedResponse)
def analyze_text(
    payload: TextAnalysisRequest, 
    session: Session = Depends(get_session),
    current_user: UserModel = Depends(get_current_user)
) -> dict:
    use_case = SubmitTextAnalysis(SqlAlchemyAnalysisRepository(session), RabbitMqJobPublisher())
    return use_case.execute(payload.text, owner_id=current_user.id)


@router.get("", response_model=SessionListResponse)
def list_sessions(
    limit: int = 20, 
    offset: int = 0, 
    session: Session = Depends(get_session),
    current_user: UserModel = Depends(get_current_user)
) -> dict:
    repository = SqlAlchemyAnalysisRepository(session)
    db_sessions = repository.list_jobs(limit=limit, offset=offset, owner_id=current_user.id)
    total = repository.count_jobs(owner_id=current_user.id)
    
    sessions_list = []
    for job, result in db_sessions:
        sessions_list.append({
            "job_id": str(job.id),
            "name": job.name,
            "status": job.status,
            "input_type": job.input_type,
            "created_at": job.created_at,
            "sentiment": result.sentiment if result else None,
            "confidence": result.confidence if result else None
        })
        
    return {
        "sessions": sessions_list,
        "total": total,
        "offset": offset,
        "limit": limit
    }


@router.get("/stats")
def get_stats(
    session: Session = Depends(get_session),
    current_user: UserModel = Depends(get_current_user)
) -> dict:
    repository = SqlAlchemyAnalysisRepository(session)
    return repository.get_analytics_stats(owner_id=current_user.id)


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_analysis(
    job_id: str, 
    session: Session = Depends(get_session),
    current_user: UserModel = Depends(get_current_user)
) -> dict:
    repository = SqlAlchemyAnalysisRepository(session)
    job = repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Analysis job not found")
        
    # Check permissions (only filter if job has owner_id and it doesn't match current user)
    if job.owner_id and job.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to access this session")
        
    cached = RedisJobCache().get(job_id, owner_id=current_user.id)
    if cached:
        cached["name"] = job.name
        return cached

    result = repository.get_result(job_id)
    result_payload = None
    if result:
        result_payload = {
            "transcript": result.transcript_json,
            "summary": result.summary_json,
            "sentiment": result.sentiment,
            "sentiment_reason": result.sentiment_reason,
            "confidence": result.confidence,
            "agent_score": result.agent_score,
            "agent_advice": result.agent_advice_json
        }
    return {"job_id": str(job.id), "name": job.name, "status": job.status, "input_type": job.input_type, "result": result_payload, "error_message": job.error_message}


@router.patch("/{job_id}", response_model=JobStatusResponse)
def rename_session(
    job_id: str, 
    payload: RenameRequest, 
    session: Session = Depends(get_session),
    current_user: UserModel = Depends(get_current_user)
) -> dict:
    repository = SqlAlchemyAnalysisRepository(session)
    job = repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Analysis job not found")
        
    # Check permissions
    if job.owner_id and job.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to access this session")
        
    job = repository.update_job_name(job_id, payload.name)
    
    result = repository.get_result(job_id)
    result_payload = None
    if result:
        result_payload = {
            "transcript": result.transcript_json,
            "summary": result.summary_json,
            "sentiment": result.sentiment,
            "sentiment_reason": result.sentiment_reason,
            "confidence": result.confidence,
            "agent_score": result.agent_score,
            "agent_advice": result.agent_advice_json
        }
    return {"job_id": str(job.id), "name": job.name, "status": job.status, "input_type": job.input_type, "result": result_payload, "error_message": job.error_message}


@router.delete("/{job_id}")
def delete_session(
    job_id: str, 
    session: Session = Depends(get_session),
    current_user: UserModel = Depends(get_current_user)
) -> dict:
    repository = SqlAlchemyAnalysisRepository(session)
    job = repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Analysis job not found")
        
    # Check permissions
    if job.owner_id and job.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to access this session")
        
    audio_key = job.audio_object_key
    
    # Delete from DB
    repository.delete_job(job_id)
    
    # Delete from MinIO if exists
    if audio_key:
        try:
            MinioAudioStorage().delete(audio_key)
        except Exception:
            pass
    
    try:
        RedisJobCache().delete(job_id, owner_id=current_user.id)
    except Exception:
        pass
        
    return {"message": "Session deleted successfully"}

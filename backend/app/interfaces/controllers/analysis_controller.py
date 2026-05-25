from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.application.use_cases.submit_audio_analysis import SubmitAudioAnalysis
from app.application.use_cases.submit_text_analysis import SubmitTextAnalysis
from app.infrastructure.cache.redis_cache import RedisJobCache
from app.infrastructure.database.analysis_repository import SqlAlchemyAnalysisRepository
from app.infrastructure.database.session import get_session
from app.infrastructure.queue.rabbitmq_publisher import RabbitMqJobPublisher
from app.infrastructure.storage.minio_storage import MinioAudioStorage
from app.interfaces.schemas.analysis_schema import JobAcceptedResponse, JobStatusResponse, TextAnalysisRequest

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.post("/audio", response_model=JobAcceptedResponse)
async def analyze_audio(file: UploadFile = File(...), session: Session = Depends(get_session)) -> dict:
    if file.content_type not in {"audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav", "audio/webm", "audio/mp4", "video/mp4"}:
        raise HTTPException(status_code=400, detail="Only .mp3, .wav, .webm, and .mp4 audio/video uploads are supported")
    content = await file.read()
    use_case = SubmitAudioAnalysis(SqlAlchemyAnalysisRepository(session), MinioAudioStorage(), RabbitMqJobPublisher())
    return use_case.execute(file.filename or "audio.bin", content, file.content_type or "application/octet-stream")


@router.post("/text", response_model=JobAcceptedResponse)
def analyze_text(payload: TextAnalysisRequest, session: Session = Depends(get_session)) -> dict:
    use_case = SubmitTextAnalysis(SqlAlchemyAnalysisRepository(session), RabbitMqJobPublisher())
    return use_case.execute(payload.text)


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_analysis(job_id: str, session: Session = Depends(get_session)) -> dict:
    cached = RedisJobCache().get(job_id)
    if cached:
        return cached
    repository = SqlAlchemyAnalysisRepository(session)
    job = repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Analysis job not found")
    result = repository.get_result(job_id)
    result_payload = None
    if result:
        result_payload = {"transcript": result.transcript_json, "summary": result.summary_json, "sentiment": result.sentiment, "sentiment_reason": result.sentiment_reason, "confidence": result.confidence}
    return {"job_id": str(job.id), "status": job.status, "input_type": job.input_type, "result": result_payload, "error_message": job.error_message}

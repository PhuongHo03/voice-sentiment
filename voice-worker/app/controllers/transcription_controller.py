import logging
import time

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.configs.metrics import VOICE_TRANSCRIPTION_DURATION_SECONDS, VOICE_TRANSCRIPTIONS_TOTAL, VOICE_UPLOAD_BYTES
from app.services.transcription_service import TranscriptionService

logger = logging.getLogger(__name__)
router = APIRouter()
transcription_service = TranscriptionService()


@router.post("/api/transcribe")
def transcribe_audio(file: UploadFile = File(...)):
    logger.info(f"Received transcription request for file: '{file.filename}' (Content-Type: '{file.content_type}')")
    start = time.perf_counter()
    try:
        content = file.file.read()
        VOICE_UPLOAD_BYTES.observe(len(content))
        result = transcription_service.transcribe(file.filename, content)
        VOICE_TRANSCRIPTIONS_TOTAL.labels("success").inc()
        VOICE_TRANSCRIPTION_DURATION_SECONDS.observe(time.perf_counter() - start)
        return result
    except Exception as e:
        VOICE_TRANSCRIPTIONS_TOTAL.labels("error").inc()
        VOICE_TRANSCRIPTION_DURATION_SECONDS.observe(time.perf_counter() - start)
        logger.error(f"Failed to transcribe audio file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

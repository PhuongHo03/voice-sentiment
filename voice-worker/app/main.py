import logging
from fastapi import FastAPI, File, UploadFile, HTTPException
import uvicorn
from app.infrastructure.ai.whisper_stt_client import WhisperSpeechToTextClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("voice_worker_main")

app = FastAPI(title="Voice ASR Web Server", description="Stateless Speech-to-Text API")
stt_client = WhisperSpeechToTextClient()


@app.post("/api/transcribe")
def transcribe_audio(file: UploadFile = File(...)):
    logger.info(f"Received transcription request for file: '{file.filename}' (Content-Type: '{file.content_type}')")
    try:
        content = file.file.read()
        turns = stt_client.transcribe(content)
        return {"filename": file.filename, "turns": turns}
    except Exception as e:
        logger.error(f"Failed to transcribe audio file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/health")
def health_check():
    return {"status": "ok", "service": "voice-worker"}


if __name__ == "__main__":
    logger.info("Starting Voice ASR Web Server on 0.0.0.0:8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)

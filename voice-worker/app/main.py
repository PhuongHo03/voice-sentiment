import logging

import uvicorn
from fastapi import FastAPI

from app.configs.metrics import PrometheusMiddleware, init_metrics, metrics_response
from app.controllers.transcription_controller import router as transcription_router

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
        logging.FileHandler(os.path.join(log_dir, "voice-worker.log"), encoding="utf-8")
    ]
)
logger = logging.getLogger("voice_worker_main")
init_metrics()

app = FastAPI(title="Voice ASR Web Server", description="Stateless Speech-to-Text API")
app.add_middleware(PrometheusMiddleware)
app.include_router(transcription_router)
app.add_api_route("/metrics", metrics_response, methods=["GET"], include_in_schema=False)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "voice-worker"}


if __name__ == "__main__":
    logger.info("Starting Voice ASR Web Server on 0.0.0.0:8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)

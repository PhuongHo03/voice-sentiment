import time
from collections.abc import Callable

from fastapi import Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

SERVICE_NAME = "voice-worker"

HTTP_REQUESTS_TOTAL = Counter(
    "voice_sentiment_http_requests_total",
    "Total HTTP requests handled by service.",
    ["service", "method", "path", "status"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "voice_sentiment_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ["service", "method", "path"],
)
VOICE_TRANSCRIPTIONS_TOTAL = Counter(
    "voice_sentiment_voice_transcriptions_total",
    "Total voice transcription requests by result.",
    ["result"],
)
VOICE_TRANSCRIPTION_DURATION_SECONDS = Histogram(
    "voice_sentiment_voice_transcription_duration_seconds",
    "Voice transcription duration in seconds.",
)
VOICE_UPLOAD_BYTES = Histogram(
    "voice_sentiment_voice_upload_bytes",
    "Uploaded audio payload size in bytes.",
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.scope.get("route").path if request.scope.get("route") else request.url.path
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            HTTP_REQUESTS_TOTAL.labels(SERVICE_NAME, request.method, path, "500").inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(SERVICE_NAME, request.method, path).observe(time.perf_counter() - start)
            raise
        HTTP_REQUESTS_TOTAL.labels(SERVICE_NAME, request.method, path, str(response.status_code)).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(SERVICE_NAME, request.method, path).observe(time.perf_counter() - start)
        return response


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

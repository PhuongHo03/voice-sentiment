from prometheus_client import Counter, Gauge, Histogram, start_http_server

LLM_WORKER_UP = Gauge(
    "voice_sentiment_llm_worker_up",
    "LLM worker process liveness marker.",
)
LLM_JOBS_TOTAL = Counter(
    "voice_sentiment_llm_jobs_total",
    "Total LLM worker jobs by input type and result.",
    ["input_type", "result"],
)
LLM_JOB_DURATION_SECONDS = Histogram(
    "voice_sentiment_llm_job_duration_seconds",
    "LLM worker job processing duration in seconds.",
    ["input_type"],
)
LLM_VOICE_REQUESTS_TOTAL = Counter(
    "voice_sentiment_llm_voice_requests_total",
    "Total voice-worker calls made by LLM worker.",
    ["result"],
)
LLM_ANALYTICS_REQUESTS_TOTAL = Counter(
    "voice_sentiment_llm_analytics_requests_total",
    "Total LLM analytics calls made by worker.",
    ["result"],
)


def start_metrics_server(port: int = 9100) -> None:
    LLM_WORKER_UP.set(1)
    start_http_server(port)

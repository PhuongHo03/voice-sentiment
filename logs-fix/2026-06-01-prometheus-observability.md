# Prometheus observability dashboard

## Issue
The system had no dedicated observability plane for service and infrastructure metrics. Admin UI could not query Prometheus metrics independently, and metrics access should not be routed through the backend API.

## Fix
- Added `infras/nginx.conf` and `infras/prometheus.yml`.
- Added Prometheus plus Postgres, Redis, RabbitMQ, and Nginx exporters in `docker-compose.yml`.
- Exposed Prometheus API through Nginx at `/observability/api/*` without adding backend-owned metrics endpoints for frontend queries.
- Added `/metrics` instrumentation for backend and voice-worker.
- Added embedded LLM worker metrics server on internal port `9100`.
- Added admin frontend observability tab at `/admin/observability`.
- Updated README, explanation docs, and planning docs.

## Validation
- `docker compose config` passed.
- `python -m compileall backend/app && python -m compileall voice-worker/app && python -m compileall llm-worker/app` passed.
- `npm --prefix frontend run build` passed.
- `docker compose up -d --build` completed.
- `http://localhost:9090/observability/api/v1/query?query=up` returned `status: success`.
- Prometheus targets reported `up=1` for backend, voice-worker, llm-worker, postgres, redis, rabbitmq, and nginx.
- `http://localhost:9090/admin/observability` returned HTTP 200.

## Risk
`/observability/api/*` is proxied by Nginx without app-level authentication. It is acceptable for local/dev but should be protected with Nginx basic auth, IP allowlist, VPN, or auth_request before production exposure.

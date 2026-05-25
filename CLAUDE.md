# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common commands

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m compileall app
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Worker:

```powershell
cd worker
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m compileall app
python -m app.main
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
npm run build
```

Local stack:

```powershell
docker compose config
docker compose up --build
```

## Architecture

The app is split into three product services plus root runtime compose:

- `backend/` — FastAPI UI-facing API. It validates requests, stores metadata in PostgreSQL, stores audio in MinIO, publishes RabbitMQ jobs, reads Redis/PostgreSQL status, and returns results to the frontend. It must not import NVIDIA Riva or vLLM clients.
- `worker/` — AI processing process. It consumes RabbitMQ jobs, downloads audio from MinIO, runs NVIDIA Riva STT, calls the self-hosted vLLM-compatible endpoint for summary/sentiment, persists PostgreSQL results, and updates Redis cache.
- `frontend/` — React/Vite dashboard. It uploads/records audio, submits text, polls backend job status, and renders transcript/summary/sentiment.
- `docker-compose.yml` — local PostgreSQL, MinIO, Redis, RabbitMQ, Nginx, backend, worker, frontend.

Primary flow:

```text
Frontend → Backend → MinIO/PostgreSQL/RabbitMQ → Worker → Riva + vLLM → PostgreSQL/Redis → Backend → Frontend
```

## Structure rules

Keep the Clean Architecture boundaries:

- `domain/` contains entities/enums only.
- `application/` contains use cases and ports/interfaces.
- `infrastructure/` contains concrete DB/object storage/cache/queue/AI adapters.
- `interfaces/` contains HTTP controllers and API schemas.
- `.env.example` stays inside the service folder that owns those variables.

## Project rules

Read these rule files before making changes:

- `.claude/rules/andrej-karpathy-skills.md`
- `.claude/rules/update-explanation.md`
- `.claude/rules/update-planning.md`

## Documentation upkeep

For code/config behavior changes:

1. Implement the source change.
2. Verify with the smallest relevant check.
3. Update the matching `docs/explanations/*-explanation.md` if future-session understanding changes.
4. Update `docs/plannings/planning.md` if structure, phase, runtime behavior, ports, services, or explanation-file coverage changes.
5. Final response must state whether docs/planning were updated or intentionally skipped.

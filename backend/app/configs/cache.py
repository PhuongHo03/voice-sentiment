import json
import redis
from app.configs.config import settings


class RedisJobCache:
    def __init__(self) -> None:
        self.client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

    def get(self, job_id: str, owner_id: str | None = None) -> dict | None:
        prefix = f"cache:user:{owner_id}:" if owner_id else ""
        value = self.client.get(f"{prefix}analysis:{job_id}")
        return json.loads(value) if value else None

    def set_status(self, job_id: str, payload: dict, owner_id: str | None = None) -> None:
        prefix = f"cache:user:{owner_id}:" if owner_id else ""
        self.client.setex(f"{prefix}analysis:{job_id}", 3600, json.dumps(payload, ensure_ascii=False))

    def delete(self, job_id: str, owner_id: str | None = None) -> None:
        prefix = f"cache:user:{owner_id}:" if owner_id else ""
        self.client.delete(f"{prefix}analysis:{job_id}")

    # â”€â”€â”€ Dashboard Stats Cache (Optimization) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def get_stats(self, owner_id: str) -> dict | None:
        value = self.client.get(f"cache:user:{owner_id}:stats")
        return json.loads(value) if value else None

    def set_stats(self, owner_id: str, stats: dict) -> None:
        # Cache stats for 24 hours (86400 seconds)
        self.client.setex(f"cache:user:{owner_id}:stats", 86400, json.dumps(stats, ensure_ascii=False))

    def delete_stats(self, owner_id: str) -> None:
        self.client.delete(f"cache:user:{owner_id}:stats")

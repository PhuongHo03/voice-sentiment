import json
import redis
from app.configs.config import settings


class RedisJobCache:
    def __init__(self) -> None:
        self.client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

    def set_status(self, job_id: str, payload: dict, owner_id: str | None = None) -> None:
        prefix = f"cache:user:{owner_id}:" if owner_id else ""
        self.client.setex(f"{prefix}analysis:{job_id}", 3600, json.dumps(payload, ensure_ascii=False))

    def delete_stats(self, owner_id: str) -> None:
        self.client.delete(f"cache:user:{owner_id}:stats")


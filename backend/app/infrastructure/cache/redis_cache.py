import json

import redis

from app.core.config import settings


class RedisJobCache:
    def __init__(self) -> None:
        self.client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

    def get(self, job_id: str, owner_id: str | None = None) -> dict | None:
        prefix = f"cache:user:{owner_id}:" if owner_id else ""
        value = self.client.get(f"{prefix}analysis:{job_id}")
        return json.loads(value) if value else None

    def delete(self, job_id: str, owner_id: str | None = None) -> None:
        prefix = f"cache:user:{owner_id}:" if owner_id else ""
        self.client.delete(f"{prefix}analysis:{job_id}")

import json

import redis

from app.core.config import settings


class RedisJobCache:
    def __init__(self) -> None:
        self.client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

    def get(self, job_id: str) -> dict | None:
        value = self.client.get(f"analysis:{job_id}")
        return json.loads(value) if value else None

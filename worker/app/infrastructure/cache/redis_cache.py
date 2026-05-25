import json

import redis

from app.core.config import settings


class RedisJobCache:
    def __init__(self) -> None:
        self.client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

    def set_status(self, job_id: str, payload: dict) -> None:
        self.client.setex(f"analysis:{job_id}", 3600, json.dumps(payload, ensure_ascii=False))

import json
from typing import Any

import redis.asyncio as aioredis
import structlog

from app.core.config import settings

logger = structlog.get_logger()

_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


class CacheManager:
    PREFIX = "quantyx"

    def __init__(self, redis: aioredis.Redis):
        self.redis = redis

    def _build_key(self, key: str) -> str:
        return f"{self.PREFIX}:{key}"

    async def get(self, key: str) -> Any | None:
        try:
            raw = await self.redis.get(self._build_key(key))
            if raw:
                return json.loads(raw)
        except Exception as e:
            logger.warning("cache_get_error", key=key, error=str(e))
        return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        try:
            await self.redis.setex(
                self._build_key(key),
                ttl,
                json.dumps(value, default=str),
            )
        except Exception as e:
            logger.warning("cache_set_error", key=key, error=str(e))

    async def delete(self, key: str) -> None:
        try:
            await self.redis.delete(self._build_key(key))
        except Exception as e:
            logger.warning("cache_delete_error", key=key, error=str(e))

    async def invalidate_company(self, company_id: int) -> None:
        """Invalidate all cached analytics for a company (on data ingestion)."""
        try:
            pattern = self._build_key(f"*:{company_id}:*")
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
        except Exception as e:
            logger.warning("cache_invalidate_error", company_id=company_id, error=str(e))

    async def rate_limit_check(
        self, identifier: str, max_requests: int, window_seconds: int
    ) -> tuple[bool, int]:
        """Sliding window rate limiter. Returns (is_allowed, current_count)."""
        try:
            key = self._build_key(f"rl:{identifier}")
            current = await self.redis.incr(key)
            if current == 1:
                await self.redis.expire(key, window_seconds)
            return current <= max_requests, current
        except Exception:
            return True, 0  # fail open on Redis error


async def get_cache_manager() -> CacheManager:
    redis = await get_redis()
    return CacheManager(redis)

"""Redis cache utilities with non-blocking SCAN and sliding-window rate limits.

Production Redis is single-threaded; KEYS blocks the event loop and can stall
all tenants. SCAN spreads key discovery across small batches (workspace default:
100). Rate limits use a sorted-set sliding window with Lua for atomicity so
denied requests are not inserted into the ZSET (avoids memory blowups). Redis
errors on rate limiting fail open so availability beats strict throttling.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

import redis.asyncio as aioredis
import structlog
from redis.asyncio.client import Redis

from app.core.config import settings
from app.utils.metrics import REDIS_OPERATIONS_TOTAL

logger = structlog.get_logger(__name__)

REDIS_CACHE_TYPE_LABEL = "json"

REDIS_MAX_CONNECTIONS = 50
REDIS_HEALTH_CHECK_INTERVAL_SECONDS = 30
SCAN_COUNT_PER_ITERATION = 100
RATE_LIMIT_EXPIRE_SLACK_SECONDS = 1

_SLIDING_WINDOW_RATE_LIMIT_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window_start = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local expire_secs = tonumber(ARGV[4])
local member = ARGV[5]
redis.call('zremrangebyscore', key, '-inf', window_start)
local count = redis.call('zcard', key)
if count < limit then
  redis.call('zadd', key, now, member)
  redis.call('expire', key, expire_secs)
  local new_count = redis.call('zcard', key)
  return {1, limit - new_count}
end
redis.call('expire', key, expire_secs)
return {0, 0}
"""

_redis_client: Redis | None = None


async def get_redis_client() -> Redis:
    """Return the shared asyncio Redis client with a bounded connection pool.

    A single client is reused across requests to avoid TCP setup overhead and
    to cap simultaneous connections under load.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=REDIS_MAX_CONNECTIONS,
            socket_keepalive=True,
            socket_keepalive_options={},
            retry_on_timeout=True,
            health_check_interval=REDIS_HEALTH_CHECK_INTERVAL_SECONDS,
        )
    return _redis_client


async def _merge_redis_server_info(redis: Redis, payload: dict[str, Any]) -> None:
    """Attach INFO fields when the backend supports it (fakeredis may not)."""
    try:
        info = await redis.info("server")
    except Exception as exc:
        logger.debug("cache.health.info_unavailable", error=str(exc))
        return
    if not isinstance(info, dict):
        return
    payload["redis_version"] = info.get("redis_version")
    payload["connected_clients"] = info.get("connected_clients")
    payload["used_memory_human"] = info.get("used_memory_human")


class CacheManager:
    """Namespaced JSON cache with SCAN invalidation and sliding-window limits."""

    KEY_PREFIX = "quantyx"

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    def _build_key(self, key: str) -> str:
        """Build `quantyx:{logical_key}` matching existing analytics cache keys."""
        return f"{self.KEY_PREFIX}:{key}"

    def _rate_limit_redis_key(self, identifier: str) -> str:
        """Redis key for sorted-set rate limiter state."""
        return f"{self.KEY_PREFIX}:ratelimit:{identifier}"

    async def get(self, key: str) -> Any | None:
        """Load a JSON value from cache, or None on miss or parse error."""
        try:
            raw = await self.redis.get(self._build_key(key))
            if raw is None:
                REDIS_OPERATIONS_TOTAL.labels(
                    operation="get", cache_type=REDIS_CACHE_TYPE_LABEL, hit_or_miss="miss"
                ).inc()
                return None
            REDIS_OPERATIONS_TOTAL.labels(
                operation="get", cache_type=REDIS_CACHE_TYPE_LABEL, hit_or_miss="hit"
            ).inc()
            return json.loads(raw)
        except Exception as exc:
            logger.warning("cache.get.error", key=key, error=str(exc))
            return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Store JSON with TTL; returns False when Redis rejects the write."""
        try:
            await self.redis.setex(
                self._build_key(key),
                ttl,
                json.dumps(value, default=str),
            )
            REDIS_OPERATIONS_TOTAL.labels(
                operation="set", cache_type=REDIS_CACHE_TYPE_LABEL, hit_or_miss="write"
            ).inc()
            return True
        except Exception as exc:
            logger.warning("cache.set.error", key=key, error=str(exc))
            return False

    async def invalidate_company(self, company_id: int) -> int:
        """Delete all cache entries for one tenant using SCAN, not KEYS.

        KEYS is O(N) and blocks Redis; SCAN yields batches so latency stays
        bounded per iteration.
        """
        pattern = f"{self.KEY_PREFIX}:*:{company_id}:*"
        cursor = 0
        deleted = 0
        try:
            while True:
                cursor, keys = await self.redis.scan(
                    cursor=cursor,
                    match=pattern,
                    count=SCAN_COUNT_PER_ITERATION,
                )
                if keys:
                    deleted += int(await self.redis.delete(*keys))
                    logger.debug(
                        "cache.invalidate.batch",
                        keys_deleted=len(keys),
                        company_id=company_id,
                    )
                if cursor == 0:
                    break
            logger.info(
                "cache.invalidate.complete",
                total_deleted=deleted,
                company_id=company_id,
            )
            return deleted
        except Exception as exc:
            logger.error(
                "cache.invalidate.error",
                company_id=company_id,
                error=str(exc),
            )
            return 0

    async def rate_limit_check(
        self,
        identifier: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        """Sliding-window limiter: (allowed, remaining_slots_after_this_if_allowed).

        Lua keeps trim / conditional ZADD / EXPIRE atomic. On Redis errors we
        allow traffic so outages do not become user-facing 5xx from throttling.
        """
        now = time.time()
        window_start = now - float(window_seconds)
        full_key = self._rate_limit_redis_key(identifier)
        expire_secs = window_seconds + RATE_LIMIT_EXPIRE_SLACK_SECONDS
        member = f"{now}:{uuid.uuid4().hex}"
        try:
            raw = await self.redis.eval(  # type: ignore[misc]
                _SLIDING_WINDOW_RATE_LIMIT_LUA,
                1,
                full_key,
                str(now),
                str(window_start),
                str(max_requests),
                str(expire_secs),
                member,
            )
            allowed = bool(raw[0])
            remaining = int(raw[1])
            if not allowed:
                logger.info(
                    "rate_limit.exceeded",
                    key=identifier,
                    limit=max_requests,
                    window_seconds=window_seconds,
                )
            return allowed, remaining
        except Exception as exc:
            logger.warning(
                "rate_limit.redis_error.fail_open",
                key=identifier,
                error=str(exc),
            )
            return True, max_requests

    async def health_check(self) -> dict[str, Any]:
        """Ping Redis and optionally merge INFO fields for ops dashboards."""
        start = time.monotonic()
        try:
            await self.redis.ping()
            latency_ms = round((time.monotonic() - start) * 1000, 2)
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}

        payload: dict[str, Any] = {
            "status": "healthy",
            "latency_ms": latency_ms,
        }
        await _merge_redis_server_info(self.redis, payload)
        return payload


async def get_cache_manager() -> CacheManager:
    """Build a CacheManager wired to the shared Redis pool."""
    client = await get_redis_client()
    return CacheManager(client)

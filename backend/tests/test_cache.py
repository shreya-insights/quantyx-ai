"""Unit tests for Redis cache utilities (fakeredis; no real Redis required)."""

import asyncio

import pytest
from fakeredis import FakeAsyncRedis

from app.utils.cache import CacheManager


def _make_cache() -> CacheManager:
    redis = FakeAsyncRedis(decode_responses=True)
    return CacheManager(redis)


@pytest.mark.asyncio
async def test_sliding_window_allows_within_limit() -> None:
    cache = _make_cache()
    for _ in range(5):
        allowed, remaining = await cache.rate_limit_check("user-a", 5, 60)
        assert allowed is True
        assert remaining >= 0


@pytest.mark.asyncio
async def test_sliding_window_blocks_over_limit() -> None:
    cache = _make_cache()
    for _ in range(5):
        await cache.rate_limit_check("user-b", 5, 60)
    allowed, remaining = await cache.rate_limit_check("user-b", 5, 60)
    assert allowed is False
    assert remaining == 0


@pytest.mark.asyncio
async def test_sliding_window_resets_after_window() -> None:
    cache = _make_cache()
    window_seconds = 2
    for _ in range(5):
        allowed, _ = await cache.rate_limit_check("user-c", 5, window_seconds)
        assert allowed is True
    await asyncio.sleep(window_seconds + 0.3)
    for _ in range(5):
        allowed, _ = await cache.rate_limit_check("user-c", 5, window_seconds)
        assert allowed is True


@pytest.mark.asyncio
async def test_fixed_window_vs_sliding_window_boundary() -> None:
    """Rolling window still counts recent events; no fresh burst before old ones age out."""
    cache = _make_cache()
    window_seconds = 3
    limit = 5
    for _ in range(limit):
        allowed, _ = await cache.rate_limit_check("user-d", limit, window_seconds)
        assert allowed is True
    await asyncio.sleep(1.9)
    for _ in range(limit):
        allowed, remaining = await cache.rate_limit_check("user-d", limit, window_seconds)
        assert allowed is False
        assert remaining == 0


@pytest.mark.asyncio
async def test_scan_invalidation_deletes_company_keys() -> None:
    cache = _make_cache()
    company_id = 42
    for i in range(20):
        logical = f"k:{company_id}:item{i}"
        await cache.set(logical, {"i": i})
    deleted = await cache.invalidate_company(company_id)
    assert deleted == 20
    for i in range(20):
        assert await cache.get(f"k:{company_id}:item{i}") is None


@pytest.mark.asyncio
async def test_invalidation_does_not_delete_other_company() -> None:
    cache = _make_cache()
    await cache.set("x:1:keep", {"a": 1})
    await cache.set("x:2:drop", {"b": 2})
    deleted = await cache.invalidate_company(2)
    assert deleted >= 1
    assert await cache.get("x:1:keep") == {"a": 1}
    assert await cache.get("x:2:drop") is None


@pytest.mark.asyncio
async def test_health_check_returns_latency() -> None:
    cache = _make_cache()
    out = await cache.health_check()
    assert out["status"] == "healthy"
    assert isinstance(out["latency_ms"], (int, float))
    assert out["latency_ms"] >= 0.0


@pytest.mark.asyncio
async def test_denied_request_does_not_inflate_zset() -> None:
    """Regression: over-limit requests must not add ZSET members (Lua path)."""
    cache = _make_cache()
    key = cache._rate_limit_redis_key("inflation-test")
    for _ in range(3):
        await cache.rate_limit_check("inflation-test", 3, 60)
    await cache.rate_limit_check("inflation-test", 3, 60)
    cardinality = await cache.redis.zcard(key)
    assert cardinality == 3

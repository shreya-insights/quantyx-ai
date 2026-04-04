"""Rate limit service unit tests (fakeredis; no real Redis)."""

import pytest
from fakeredis import FakeAsyncRedis

from app.services.rate_limit_service import RateLimitService, first_day_next_month_utc
from app.utils.cache import CacheManager


def _svc() -> RateLimitService:
    return RateLimitService(CacheManager(FakeAsyncRedis(decode_responses=True)))


@pytest.mark.asyncio
async def test_ip_limit_allows_under_cap() -> None:
    svc = _svc()
    for _ in range(5):
        ok, rem, lim, _ = await svc.check_ip_limit("203.0.113.1")
        assert ok is True
        assert lim == 100
        assert rem >= 0


@pytest.mark.asyncio
async def test_user_plan_limit_respects_plan_name() -> None:
    svc = _svc()
    ok, rem, lim, _ = await svc.check_user_limit(1, 42, "starter")
    assert ok is True
    assert lim == 60
    assert rem == 59


@pytest.mark.asyncio
async def test_monthly_quota_check_unlimited_plan() -> None:
    svc = _svc()
    ok, used = await svc.check_monthly_quota(9, None, 0)
    assert ok is True
    assert used == 0


@pytest.mark.asyncio
async def test_increment_updates_effective_monthly_count() -> None:
    svc = _svc()
    await svc.increment_usage(7, 0)
    n = await svc.get_effective_monthly_calls(7, 0)
    assert n == 1


def test_first_day_next_month_is_after_today() -> None:
    from datetime import date

    nxt = first_day_next_month_utc()
    assert nxt > date.today()
    assert nxt.day == 1

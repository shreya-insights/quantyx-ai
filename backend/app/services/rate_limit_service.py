"""Redis-backed API metering: sliding-window per-minute limits and monthly quotas.

Reads plan limits from cache with DB fallback. Fails open on Redis errors so
outages do not become hard outages for customers.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.subscription import Subscription, SubscriptionStatus
from app.schemas.subscription import DailyUsage
from app.utils.cache import CacheManager, get_redis_client

logger = structlog.get_logger(__name__)

DAILY_BAR_SERIES_DAYS = 30


@dataclass(frozen=True)
class PlanContext:
    """Cached subscription snapshot for rate limit and quota decisions."""

    plan_name: str
    api_calls_limit: int | None
    api_calls_used_db: int


def _utc_year_month(now: datetime | None = None) -> str:
    ts = now or datetime.now(timezone.utc)
    return f"{ts.year:04d}-{ts.month:02d}"


def first_day_next_month_utc() -> date:
    today = date.today()
    if today.month == 12:
        return date(today.year + 1, 1, 1)
    return date(today.year, today.month + 1, 1)


def _seconds_until_month_quota_expiry() -> int:
    """TTL for monthly quota key: first of next month plus one day (UTC)."""
    now = datetime.now(timezone.utc)
    y, m = now.year, now.month
    if m == 12:
        next_start = datetime(y + 1, 1, 1, tzinfo=timezone.utc)
    else:
        next_start = datetime(y, m + 1, 1, tzinfo=timezone.utc)
    expire_at = next_start + timedelta(days=1)
    return max(int((expire_at - now).total_seconds()), 60)


def _month_quota_logical_key(company_id: int, ym: str | None = None) -> str:
    return f"quota:{company_id}:{ym or _utc_year_month()}"


def _plan_cache_logical_key(company_id: int) -> str:
    return f"plan:{company_id}"


async def _flush_subscription_api_usage_to_db(company_id: int, redis_total: int) -> None:
    from sqlalchemy import update

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(Subscription)
                .where(
                    Subscription.company_id == company_id,
                    Subscription.status.in_(
                        [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]
                    ),
                )
                .values(api_calls_used=redis_total),
            )
            await session.commit()
    except Exception as exc:
        logger.warning(
            "quota.db_sync_failed",
            company_id=company_id,
            error=str(exc),
        )


async def _load_plan_from_db(session: AsyncSession, company_id: int) -> PlanContext | None:
    result = await session.execute(
        select(Subscription)
        .where(
            Subscription.company_id == company_id,
            Subscription.status.in_(
                [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]
            ),
        )
        .order_by(Subscription.created_at.desc())
        .limit(1),
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        return None
    return PlanContext(
        plan_name=sub.plan_name.value,
        api_calls_limit=sub.api_calls_limit,
        api_calls_used_db=int(sub.api_calls_used or 0),
    )


class RateLimitService:
    """Per-tenant metering: ZSET minute windows, STRING monthly quota + daily bars."""

    def __init__(self, cache: CacheManager) -> None:
        self._cache = cache

    def _redis_key(self, logical: str) -> str:
        return self._cache._build_key(logical)

    async def fetch_plan_context(
        self, company_id: int, session: AsyncSession | None = None
    ) -> PlanContext | None:
        """Return plan limits from Redis cache or MySQL."""
        logical = _plan_cache_logical_key(company_id)
        try:
            raw = await self._cache.redis.get(self._redis_key(logical))
            if raw:
                data: dict[str, Any] = json.loads(raw)
                return PlanContext(
                    plan_name=str(data["plan_name"]),
                    api_calls_limit=data.get("api_calls_limit"),
                    api_calls_used_db=int(data.get("api_calls_used_db", 0)),
                )
        except Exception as exc:
            logger.warning("plan_cache.read_fail_open", company_id=company_id, error=str(exc))

        try:
            if session is not None:
                ctx = await _load_plan_from_db(session, company_id)
            else:
                async with AsyncSessionLocal() as inner:
                    ctx = await _load_plan_from_db(inner, company_id)
            if ctx is None:
                return None
            try:
                payload = {
                    "plan_name": ctx.plan_name,
                    "api_calls_limit": ctx.api_calls_limit,
                    "api_calls_used_db": ctx.api_calls_used_db,
                }
                await self._cache.redis.setex(
                    self._redis_key(logical),
                    settings.PLAN_CACHE_TTL_SECONDS,
                    json.dumps(payload),
                )
            except Exception as exc:
                logger.warning("plan_cache.write_fail", company_id=company_id, error=str(exc))
            return ctx
        except Exception as exc:
            logger.warning("plan_db.load_failed", company_id=company_id, error=str(exc))
            return None

    @staticmethod
    async def invalidate_plan_cache(company_id: int) -> None:
        try:
            r = await get_redis_client()
            logical = _plan_cache_logical_key(company_id)
            key = f"{CacheManager.KEY_PREFIX}:{logical}"
            await r.delete(key)
        except Exception as exc:
            logger.warning(
                "plan_cache.invalidate_failed",
                company_id=company_id,
                error=str(exc),
            )

    async def check_ip_limit(self, ip: str) -> tuple[bool, int, int, int]:
        """Sliding window per IP. Returns (allowed, remaining, limit, reset_epoch)."""
        limit = settings.IP_RATE_LIMIT_PER_MINUTE
        allowed, remaining = await self._cache.rate_limit_check(
            f"ip:{ip}",
            limit,
            settings.API_RATE_LIMIT_WINDOW_SECONDS,
        )
        reset_ts = int(time.time()) + settings.API_RATE_LIMIT_WINDOW_SECONDS
        return allowed, remaining, limit, reset_ts

    async def check_user_limit(
        self, company_id: int, user_id: int, plan_name: str
    ) -> tuple[bool, int, int, int]:
        per_min = settings.PLAN_RATE_LIMITS_PER_MINUTE.get(plan_name)
        if per_min is None:
            per_min = settings.PLAN_RATE_LIMITS_PER_MINUTE.get("starter", 60)
        ident = f"user:{company_id}:{user_id}"
        allowed, remaining = await self._cache.rate_limit_check(
            ident,
            per_min,
            settings.API_RATE_LIMIT_WINDOW_SECONDS,
        )
        reset_ts = int(time.time()) + settings.API_RATE_LIMIT_WINDOW_SECONDS
        return allowed, remaining, per_min, reset_ts

    async def check_monthly_quota(
        self, company_id: int, limit: int | None, db_baseline: int
    ) -> tuple[bool, int]:
        if limit is None:
            return True, 0
        try:
            key = self._redis_key(_month_quota_logical_key(company_id))
            raw = await self._cache.redis.get(key)
            used = int(raw) if raw is not None else db_baseline
            return used < limit, used
        except Exception as exc:
            logger.warning("quota.check.fail_open", company_id=company_id, error=str(exc))
            return True, 0

    async def increment_usage(self, company_id: int, db_baseline: int) -> None:
        """INCR monthly + daily; sync MySQL every QUOTA_SYNC_INTERVAL."""
        try:
            r = self._cache.redis
            ym = _utc_year_month()
            month_logical = _month_quota_logical_key(company_id, ym)
            month_key = self._redis_key(month_logical)
            ttl = _seconds_until_month_quota_expiry()
            base = str(db_baseline)
            await r.set(month_key, base, ex=ttl, nx=True)
            val = await r.incr(month_key)
            await r.expire(month_key, ttl)

            day = date.today().isoformat()
            day_key = self._redis_key(f"daily:{company_id}:{day}")
            await r.incr(day_key)
            await r.expire(day_key, settings.DAILY_USAGE_KEY_TTL_SECONDS)

            if val > 0 and val % settings.QUOTA_SYNC_INTERVAL == 0:
                asyncio.create_task(_flush_subscription_api_usage_to_db(company_id, val))
        except Exception as exc:
            logger.warning(
                "metering.increment.fail_open",
                company_id=company_id,
                error=str(exc),
            )

    async def get_effective_monthly_calls(
        self, company_id: int, db_fallback: int
    ) -> int:
        try:
            raw = await self._cache.redis.get(
                self._redis_key(_month_quota_logical_key(company_id))
            )
            if raw is None:
                return db_fallback
            return int(raw)
        except Exception as exc:
            logger.warning(
                "quota.read.fail_open",
                company_id=company_id,
                error=str(exc),
            )
            return db_fallback

    async def get_daily_breakdown(self, company_id: int) -> list[DailyUsage]:
        try:
            today = date.today()
            days = [today - timedelta(days=i) for i in range(DAILY_BAR_SERIES_DAYS - 1, -1, -1)]
            keys = [self._redis_key(f"daily:{company_id}:{d.isoformat()}") for d in days]
            values = await self._cache.redis.mget(keys)
            out: list[DailyUsage] = []
            for d, v in zip(days, values, strict=True):
                n = int(v) if v is not None else 0
                out.append(DailyUsage(date=d.isoformat(), calls=n))
            return out
        except Exception as exc:
            logger.warning(
                "daily_breakdown.fail_open",
                company_id=company_id,
                error=str(exc),
            )
            return []

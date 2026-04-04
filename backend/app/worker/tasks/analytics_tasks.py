"""Hourly analytics cache refresh — pre-aggregated tables per tenant."""

from __future__ import annotations

import asyncio
import time
import structlog
from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.models.company import Company
from app.repositories.analytics_cache_repo import (
    AnalyticsCacheRepository,
    default_kpi_period_dates,
)
from app.repositories.analytics_repo import AnalyticsRepository

logger = structlog.get_logger(__name__)

_REFRESH_ALL_TASK_NAME = "quantyx.analytics.refresh_all_analytics_caches"
_REFRESH_COMPANY_TASK_NAME = "quantyx.analytics.refresh_analytics_cache"
_MAX_RETRIES = 3
_DEFAULT_RETRY_SECONDS = 60
_REVENUE_MONTHS = 36
_MERCHANT_TOP_CAP = 100
_ROLLING_DAY_WINDOWS: tuple[int, ...] = (7, 30, 90, 365)


def _create_engine_session_factory() -> tuple[
    AsyncEngine, async_sessionmaker[AsyncSession]
]:
    engine = create_async_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=3,
    )
    factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return engine, factory


async def _list_active_company_ids() -> list[int]:
    engine, factory = _create_engine_session_factory()
    try:
        async with factory() as session:
            result = await session.execute(
                select(Company.id).where(Company.is_active.is_(True))
            )
            return [int(row[0]) for row in result.all()]
    finally:
        await engine.dispose()


async def _refresh_one_company(session: AsyncSession, company_id: int) -> str:
    cache_repo = AnalyticsCacheRepository(session)
    if await cache_repo.should_skip_idempotent_refresh(company_id):
        return "skipped"
    analytics = AnalyticsRepository(session)
    snapshot = await cache_repo.get_current_tx_count(company_id)
    revenue_rows = await analytics.get_revenue_trend(company_id, _REVENUE_MONTHS)
    await cache_repo.upsert_revenue_cache(company_id, revenue_rows, snapshot)
    for days in _ROLLING_DAY_WINDOWS:
        cat_rows = await analytics.get_spending_by_category(company_id, days)
        await cache_repo.upsert_category_cache(
            company_id, days, cat_rows, snapshot
        )
        merch_rows = await analytics.get_top_merchants(
            company_id, days, _MERCHANT_TOP_CAP
        )
        await cache_repo.upsert_merchant_cache(
            company_id, days, merch_rows, snapshot
        )
    start_d, end_d = default_kpi_period_dates()
    period_key = AnalyticsCacheRepository.kpi_period_type(start_d, end_d)
    kpi = await analytics.get_kpi_summary(company_id, str(start_d), str(end_d))
    fraud = await analytics.get_fraud_kpi(company_id, str(start_d), str(end_d))
    total_tx = int(kpi["total_transactions"] or 0)
    fraud_n = int(fraud["fraud_alert_count"] or 0)
    fraud_rate = round(fraud_n / total_tx * 100, 4) if total_tx > 0 else 0.0
    await cache_repo.upsert_kpi_cache(
        company_id,
        period_key,
        start_d,
        end_d,
        kpi,
        fraud_n,
        fraud_rate,
        snapshot,
    )
    await session.commit()
    return "refreshed"


async def _refresh_company_pipeline(company_id: int) -> dict[str, str | int]:
    engine, factory = _create_engine_session_factory()
    try:
        async with factory() as session:
            try:
                status = await _refresh_one_company(session, company_id)
            except Exception:
                await session.rollback()
                raise
            return {"company_id": company_id, "status": status}
    finally:
        await engine.dispose()


@shared_task(
    bind=True,
    name=_REFRESH_COMPANY_TASK_NAME,
    queue="analytics",
    max_retries=_MAX_RETRIES,
    default_retry_delay=_DEFAULT_RETRY_SECONDS,
)
def refresh_analytics_cache(self, company_id: int) -> dict[str, str | int]:
    """Recompute and upsert all analytics cache slices for one company."""
    start = time.perf_counter()
    logger.info(
        "analytics.cache_refresh_start",
        task_id=self.request.id,
        company_id=company_id,
    )
    try:
        result = asyncio.run(_refresh_company_pipeline(company_id))
        logger.info(
            "analytics.cache_refresh_done",
            task_id=self.request.id,
            elapsed_seconds=round(time.perf_counter() - start, 3),
            **result,
        )
        return result
    except Exception as exc:
        logger.error(
            "analytics.cache_refresh_error",
            task_id=self.request.id,
            company_id=company_id,
            error=str(exc),
            exc_info=True,
        )
        raise self.retry(exc=exc, countdown=_DEFAULT_RETRY_SECONDS) from exc


@shared_task(bind=True, name=_REFRESH_ALL_TASK_NAME, queue="analytics")
def refresh_all_analytics_caches(self) -> dict[str, Any]:
    """Enqueue per-company analytics refresh (hourly beat)."""
    ids = asyncio.run(_list_active_company_ids())
    for cid in ids:
        refresh_analytics_cache.delay(cid)
    logger.info(
        "analytics.cache_fanout",
        task_id=self.request.id,
        queued=len(ids),
    )
    return {"queued": len(ids)}

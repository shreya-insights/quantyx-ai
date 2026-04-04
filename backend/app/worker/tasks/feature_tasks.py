"""
Scheduled feature recompute — refreshes feature store rows for all tenants.

Design: sync Celery entrypoint; async work via asyncio.run like fraud_tasks.
Idempotent upserts in FeatureEngineeringService make duplicate beats safe.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

import structlog
from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.account import Account
from app.models.merchant import Merchant
from app.services.feature_engineering import FeatureEngineeringService

logger = structlog.get_logger(__name__)

_FEATURE_RECOMPUTE_TASK_NAME = "quantyx.features.recompute_all_features"
_MAX_TASK_RETRIES = 2
_DEFAULT_RETRY_SECONDS = 30


async def _recompute_all_async() -> dict[str, Any]:
    svc = FeatureEngineeringService()
    processed_users = 0
    failed_users = 0
    processed_merchants = 0
    failed_merchants = 0

    engine = create_async_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=3,
    )
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    try:
        async with session_factory() as session:
            user_pairs = await session.execute(
                select(Account.user_id, Account.company_id)
                .where(Account.user_id.is_not(None))
                .distinct()
            )
            pairs = list(user_pairs.all())

            for user_id, company_id in pairs:
                if user_id is None:
                    continue
                try:
                    await svc.compute_user_features(int(user_id), int(company_id), session)
                    await svc.compute_velocity_features(int(user_id), int(company_id), session)
                    processed_users += 1
                except Exception as exc:
                    failed_users += 1
                    logger.warning(
                        "features.user_recompute_failed",
                        user_id=user_id,
                        company_id=company_id,
                        error=str(exc),
                        exc_info=True,
                    )

            merchant_pairs = await session.execute(
                select(Merchant.id, Merchant.company_id)
            )
            for mid, company_id in merchant_pairs.all():
                try:
                    await svc.compute_merchant_features(int(mid), int(company_id), session)
                    processed_merchants += 1
                except Exception as exc:
                    failed_merchants += 1
                    logger.warning(
                        "features.merchant_recompute_failed",
                        merchant_id=mid,
                        company_id=company_id,
                        error=str(exc),
                        exc_info=True,
                    )
    finally:
        await engine.dispose()

    return {
        "status": "complete",
        "processed_users": processed_users,
        "failed_users": failed_users,
        "processed_merchants": processed_merchants,
        "failed_merchants": failed_merchants,
    }


@shared_task(
    bind=True,
    name=_FEATURE_RECOMPUTE_TASK_NAME,
    queue="features",
    max_retries=_MAX_TASK_RETRIES,
    default_retry_delay=_DEFAULT_RETRY_SECONDS,
)
def recompute_all_features(self) -> dict[str, Any]:
    """Batch refresh user, velocity, and merchant features for all companies."""
    start = time.perf_counter()
    logger.info("features.recompute_start", task_id=self.request.id)
    try:
        result = asyncio.run(_recompute_all_async())
        elapsed = time.perf_counter() - start
        logger.info(
            "features.recompute_done",
            task_id=self.request.id,
            elapsed_seconds=round(elapsed, 3),
            **{k: v for k, v in result.items() if k != "status"},
        )
        return result
    except Exception as exc:
        logger.error(
            "features.recompute_error",
            task_id=self.request.id,
            error=str(exc),
            exc_info=True,
        )
        raise self.retry(exc=exc, countdown=_DEFAULT_RETRY_SECONDS) from exc

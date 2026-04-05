"""Operational monitoring — weekly ML health and drift checks per active company."""

from __future__ import annotations

import asyncio
import time
from typing import Any

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
from app.services.model_monitoring_service import compute_model_health_for_company

logger = structlog.get_logger(__name__)

_MODEL_HEALTH_TASK_NAME = "quantyx.monitoring.run_model_health_check"
_MAX_RETRIES = 2
_DEFAULT_RETRY_SECONDS = 60


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


async def _run_model_health_pipeline() -> dict[str, Any]:
    ids = await _list_active_company_ids()
    engine, factory = _create_engine_session_factory()
    errors: list[dict[str, Any]] = []
    try:
        for cid in ids:
            async with factory() as session:
                try:
                    await compute_model_health_for_company(session, cid)
                except Exception as exc:
                    await session.rollback()
                    errors.append({"company_id": cid, "error": str(exc)})
                    logger.error(
                        "model_health.company_failed",
                        company_id=cid,
                        error=str(exc),
                        exc_info=True,
                    )
        return {
            "companies": len(ids),
            "errors": errors,
        }
    finally:
        await engine.dispose()


@shared_task(
    bind=True,
    name=_MODEL_HEALTH_TASK_NAME,
    queue="features",
    max_retries=_MAX_RETRIES,
    default_retry_delay=_DEFAULT_RETRY_SECONDS,
)
def run_model_health_check(self) -> dict[str, Any]:
    """Compute PSI, performance metrics, and admin notifications weekly."""
    start = time.perf_counter()
    logger.info("model_health.task_start", task_id=self.request.id)
    try:
        result = asyncio.run(_run_model_health_pipeline())
        logger.info(
            "model_health.task_done",
            task_id=self.request.id,
            elapsed_seconds=round(time.perf_counter() - start, 3),
            **{k: result[k] for k in ("companies",) if k in result},
            error_count=len(result.get("errors", [])),
        )
        return result
    except Exception as exc:
        logger.error(
            "model_health.task_error",
            task_id=self.request.id,
            error=str(exc),
            exc_info=True,
        )
        raise self.retry(exc=exc, countdown=_DEFAULT_RETRY_SECONDS) from exc

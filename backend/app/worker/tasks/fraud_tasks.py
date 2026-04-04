"""
Fraud analysis Celery task — offloads HTTP thread; at-least-once safe via idempotency.

Design:
    bind=True enables self.retry with exponential backoff.
    Idempotency: if fraud_analyzed_at is already set, skip (duplicate delivery safe).
    Workers run sync entrypoint; reuse async services via asyncio.run().
    Redis pub/sub publish is best-effort (fail-open) so broker issues never mask fraud commit.
    ML scoring: lazy-loads model on first Celery worker call (separate process from FastAPI).
    ML is fail-open: missing model file → rules-only, never blocks a transaction.
"""
from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import redis
import structlog
from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.fraud_alert import AlertSeverity, AlertType, FraudAlert
from app.models.transaction import Transaction
from app.services.fraud_service import FraudDetectionService
from app.utils.metrics import FRAUD_DETECTIONS_TOTAL

logger = structlog.get_logger(__name__)

_FRAUD_TASK_NAME = "quantyx.fraud.analyze_transaction"
_MAX_TASK_RETRIES = 3
_BASE_RETRY_SECONDS = 5


async def _load_transaction(session: AsyncSession, tx_id: int) -> Transaction | None:
    result = await session.execute(select(Transaction).where(Transaction.id == tx_id))
    return result.scalar_one_or_none()


async def _existing_alert_for_transaction(
    session: AsyncSession, transaction_id: int
) -> FraudAlert | None:
    result = await session.execute(
        select(FraudAlert)
        .where(FraudAlert.transaction_id == transaction_id)
        .limit(1)
    )
    return result.scalar_one_or_none()


def _publish_fraud_event(
    company_id: int, transaction_id: int, alerts: list[FraudAlert]
) -> None:
    if not alerts:
        return
    try:
        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            event = {
                "type": "fraud_alert",
                "transaction_id": transaction_id,
                "company_id": company_id,
                "alert_ids": [a.id for a in alerts],
                "severities": [a.severity.value for a in alerts],
            }
            client.publish(f"quantyx:events:{company_id}", json.dumps(event))
        finally:
            client.close()
    except Exception as exc:
        logger.warning(
            "fraud_task.pubsub_failed",
            transaction_id=transaction_id,
            error=str(exc),
        )


def _ml_prob_to_severity(prob: float) -> AlertSeverity:
    if prob >= 0.90:
        return AlertSeverity.CRITICAL
    if prob >= 0.75:
        return AlertSeverity.HIGH
    if prob >= 0.60:
        return AlertSeverity.MEDIUM
    return AlertSeverity.LOW


def _ensure_ml_loaded() -> bool:
    """Lazy-load ML model in the worker process. Returns True if model is ready."""
    from app.services.ml_fraud_service import MLFraudService

    if MLFraudService.is_loaded():
        return True
    try:
        MLFraudService.load()
        return True
    except FileNotFoundError:
        logger.warning("fraud_task.ml_model_not_found.rules_only")
        return False
    except Exception as exc:
        logger.error("fraud_task.ml_load_error", error=str(exc), exc_info=True)
        return False


async def _build_feature_dict(session: AsyncSession, tx: Transaction) -> dict[str, float]:
    """Delegate feature construction to FeatureEngineeringService (single source of truth)."""
    from app.services.feature_engineering import FeatureEngineeringService

    svc = FeatureEngineeringService()
    return await svc.get_features_for_transaction(
        account_id=tx.account_id,
        merchant_id=tx.merchant_id,
        amount=float(tx.amount),
        company_id=tx.company_id,
        transaction_date=tx.transaction_date,
        db=session,
    )


async def _run_ml_scoring(
    session: AsyncSession, tx: Transaction
) -> FraudAlert | None:
    """Score with ML; persist FraudAlert with SHAP JSON if fraud detected."""
    from app.services.ml_fraud_service import MLFraudService

    try:
        features = await _build_feature_dict(session, tx)
        ml_result = MLFraudService().predict_with_explanation(
            features,
            company_id=tx.company_id,
        )

        logger.info(
            "fraud_task.ml_scored",
            transaction_id=tx.id,
            probability=ml_result.fraud_probability,
            is_fraud=ml_result.is_fraud,
            model_version=ml_result.model_version,
        )

        if not ml_result.is_fraud:
            return None

        shap_payload = json.dumps(
            {
                "fraud_probability": ml_result.fraud_probability,
                "top_reasons": [r.model_dump() for r in ml_result.top_reasons],
                "explanation": ml_result.explanation_text,
            }
        )
        ml_alert = FraudAlert(
            company_id=tx.company_id,
            transaction_id=tx.id,
            alert_type=AlertType.ML_FRAUD_SCORE,
            severity=_ml_prob_to_severity(ml_result.fraud_probability),
            confidence_score=round(ml_result.fraud_probability * 100, 2),
            description=ml_result.explanation_text,
            rule_metadata=shap_payload,
            model_version=ml_result.model_version,
        )
        FRAUD_DETECTIONS_TOTAL.labels(
            severity=ml_alert.severity.value,
            alert_type=ml_alert.alert_type.value,
            company_id=str(tx.company_id),
        ).inc()
        session.add(ml_alert)
        await session.flush()
        return ml_alert

    except Exception as exc:
        logger.error(
            "fraud_task.ml_scoring_failed",
            transaction_id=tx.id,
            error=str(exc),
            exc_info=True,
        )
        return None


@asynccontextmanager
async def _task_session():
    """Create a per-task async engine so there is no event-loop mismatch.

    asyncio.run() starts a brand-new event loop each time a Celery task runs.
    Reusing the module-level engine (bound to a previous loop) causes
    'Future attached to a different loop'. Disposing after each task avoids
    connection-pool leaks.
    """
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
        autocommit=False,
        autoflush=False,
    )
    try:
        async with session_factory() as session:
            yield session
    finally:
        await engine.dispose()


async def _analyze_fraud_async(transaction_id: int, company_id: int) -> dict[str, Any]:
    async with _task_session() as session:
        tx = await _load_transaction(session, transaction_id)
        if not tx or tx.company_id != company_id:
            logger.error(
                "fraud_task.transaction_missing_or_tenant_mismatch",
                transaction_id=transaction_id,
                company_id=company_id,
            )
            raise ValueError("transaction_not_found_or_forbidden")

        if tx.fraud_analyzed_at is not None:
            logger.info("fraud_task.skip_already_marked", transaction_id=transaction_id)
            return {"status": "already_analyzed", "alert_ids": []}

        existing = await _existing_alert_for_transaction(session, transaction_id)
        if existing:
            tx.fraud_analyzed_at = datetime.now(timezone.utc)
            await session.commit()
            logger.info(
                "fraud_task.skip_duplicate",
                transaction_id=transaction_id,
                alert_id=existing.id,
            )
            return {"status": "already_analyzed", "alert_ids": [existing.id]}

        rule_svc = FraudDetectionService(session)
        rule_alerts = await rule_svc.analyze_transaction(tx)
        tx.fraud_analyzed_at = datetime.now(timezone.utc)
        await session.commit()

        ml_alert: FraudAlert | None = None
        if _ensure_ml_loaded():
            ml_alert = await _run_ml_scoring(session, tx)
            if ml_alert is not None:
                await session.commit()

        all_alerts = rule_alerts + ([ml_alert] if ml_alert else [])
        if all_alerts:
            _publish_fraud_event(company_id, transaction_id, all_alerts)

        logger.info(
            "fraud_task.complete",
            transaction_id=transaction_id,
            rule_alert_count=len(rule_alerts),
            ml_alert=ml_alert is not None,
        )
        return {
            "status": "complete",
            "alert_ids": [a.id for a in all_alerts],
        }


@shared_task(
    bind=True,
    name=_FRAUD_TASK_NAME,
    queue="fraud",
    max_retries=_MAX_TASK_RETRIES,
    default_retry_delay=_BASE_RETRY_SECONDS,
)
def analyze_transaction_fraud(self, transaction_id: int, company_id: int) -> dict[str, Any]:
    """Run rule-based + ML fraud detection for one transaction after API commit."""
    logger.info(
        "fraud_task.start",
        task_id=self.request.id,
        transaction_id=transaction_id,
        company_id=company_id,
    )
    try:
        return asyncio.run(_analyze_fraud_async(transaction_id, company_id))
    except ValueError as exc:
        if str(exc) == "transaction_not_found_or_forbidden":
            logger.warning(
                "fraud_task.skip_not_found",
                transaction_id=transaction_id,
                company_id=company_id,
            )
            return {"status": "skipped", "reason": str(exc)}
        raise
    except Exception as exc:
        logger.error(
            "fraud_task.error",
            transaction_id=transaction_id,
            error=str(exc),
            exc_info=True,
        )
        delay = 2 ** self.request.retries
        raise self.retry(exc=exc, countdown=delay) from exc

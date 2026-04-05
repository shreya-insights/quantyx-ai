"""Admin API — model quality trend + PSI drift summary."""

from __future__ import annotations

from datetime import date

import structlog
from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select

from app.core.dependencies import AdminUser, DBSession
from app.models.admin_notification import AdminNotification
from app.models.model_monitoring import (
    FeatureDistributionSnapshot,
    ModelPerformanceMetric,
    PsiStatus,
)
from app.services.model_monitoring_service import (
    load_ml_manifest,
    recommendation_from_metrics,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/model-health", tags=["Model health"])


class CurrentMetricsOut(BaseModel):
    """Classifier metrics for the latest completed period."""

    f1: float | None = None
    precision: float | None = None
    recall: float | None = None
    auc_pr: float | None = None
    false_positive_rate: float | None = None
    avg_ml_score: float | None = None


class TrendPoint(BaseModel):
    """One bucket for the 12-week chart."""

    week: str
    period_start: str
    f1: float | None = None
    precision: float | None = None
    recall: float | None = None
    auc_pr: float | None = None


class DriftFeatureOut(BaseModel):
    """Feature whose PSI exceeded the drift threshold."""

    feature: str
    psi: float | None = None
    status: str | None = None


class ModelHealthResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_version: str | None = None
    recommendation: str
    current_metrics: CurrentMetricsOut
    trend_12w: list[TrendPoint]
    drifted_features: list[DriftFeatureOut]
    unread_alerts: int


def _f_or_none(val: object) -> float | None:
    if val is None:
        return None
    return float(val)


def _iso_week_label(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


@router.get("", response_model=ModelHealthResponse)
async def get_model_health(
    _admin: AdminUser,
    db: DBSession,
    company_id: int = Query(..., ge=1, description="Tenant to inspect"),
) -> ModelHealthResponse:
    """Return latest metrics, drift, and recommendation for one company (admin-only)."""
    try:
        manifest = load_ml_manifest()
        mv = manifest.get("trained_at")
    except (OSError, FileNotFoundError, ValueError) as exc:
        logger.warning("model_health.manifest_unreadable", error=str(exc))
        mv = None

    latest_row = (
        (
            await db.execute(
                select(ModelPerformanceMetric)
                .where(ModelPerformanceMetric.company_id == company_id)
                .order_by(ModelPerformanceMetric.period_start.desc())
                .limit(1)
            )
        )
        .scalars()
        .first()
    )

    trend_rows = (
        (
            await db.execute(
                select(ModelPerformanceMetric)
                .where(ModelPerformanceMetric.company_id == company_id)
                .order_by(ModelPerformanceMetric.period_start.desc())
                .limit(12)
            )
        )
        .scalars()
        .all()
    )
    trend_rows = list(reversed(trend_rows))

    drifted: list[DriftFeatureOut] = []
    drift_count = 0
    monitor_count = 0
    if latest_row is not None:
        snap_q = await db.execute(
            select(FeatureDistributionSnapshot)
            .where(
                FeatureDistributionSnapshot.company_id == company_id,
                FeatureDistributionSnapshot.period_start == latest_row.period_start,
                FeatureDistributionSnapshot.psi_status == PsiStatus.DRIFT,
            )
            .order_by(FeatureDistributionSnapshot.psi_score.desc())
        )
        for s in snap_q.scalars().all():
            drifted.append(
                DriftFeatureOut(
                    feature=s.feature_name,
                    psi=_f_or_none(s.psi_score),
                    status=s.psi_status.value if s.psi_status else None,
                )
            )
        drift_count = len(drifted)
        monitor_count = int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(FeatureDistributionSnapshot)
                    .where(
                        FeatureDistributionSnapshot.company_id == company_id,
                        FeatureDistributionSnapshot.period_start
                        == latest_row.period_start,
                        FeatureDistributionSnapshot.psi_status == PsiStatus.MONITOR,
                    )
                )
            ).scalar_one()
        )

    unread = int(
        (
            await db.execute(
                select(func.count())
                .select_from(AdminNotification)
                .where(
                    AdminNotification.company_id == company_id,
                    AdminNotification.is_read.is_(False),
                )
            )
        ).scalar_one()
    )

    cur = CurrentMetricsOut()
    if latest_row is not None:
        cur = CurrentMetricsOut(
            f1=_f_or_none(latest_row.f1_score),
            precision=_f_or_none(latest_row.precision_score),
            recall=_f_or_none(latest_row.recall_score),
            auc_pr=_f_or_none(latest_row.auc_pr),
            false_positive_rate=_f_or_none(latest_row.false_positive_rate),
            avg_ml_score=_f_or_none(latest_row.avg_ml_score),
        )
        mv = latest_row.model_version or mv

    trend_12w = [
        TrendPoint(
            week=_iso_week_label(r.period_start),
            period_start=r.period_start.isoformat(),
            f1=_f_or_none(r.f1_score),
            precision=_f_or_none(r.precision_score),
            recall=_f_or_none(r.recall_score),
            auc_pr=_f_or_none(r.auc_pr),
        )
        for r in trend_rows
    ]

    rec = recommendation_from_metrics(
        cur.f1,
        cur.precision,
        drift_count,
        monitor_features=monitor_count,
    )

    return ModelHealthResponse(
        model_version=mv,
        recommendation=rec,
        current_metrics=cur,
        trend_12w=trend_12w,
        drifted_features=drifted,
        unread_alerts=unread,
    )

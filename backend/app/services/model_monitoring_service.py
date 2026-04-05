"""Weekly ML health: performance on analyst labels, PSI drift vs training baseline."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Final, Sequence

import numpy as np
import structlog
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.admin_notification import (
    AdminNotification,
    AdminNotificationSeverity,
    AdminNotificationType,
)
from app.models.analyst_label import AnalystGroundTruth
from app.models.fraud_alert import AlertType, FraudAlert
from app.models.model_monitoring import (
    FeatureDistributionSnapshot,
    ModelPerformanceMetric,
    PsiStatus,
)
from app.services.feature_engineering import FEATURE_COLUMNS, FEATURE_EPSILON

logger = structlog.get_logger(__name__)

PSI_PCT_EPSILON: Final[float] = 1e-6
RECOMMENDATION_STABLE: Final[str] = "stable"
RECOMMENDATION_MONITOR: Final[str] = "monitor"
RECOMMENDATION_RETRAIN: Final[str] = "retrain_recommended"

_MONITORING_BASE_SQL = text("""
SELECT
    t.id,
    t.amount,
    COALESCE(uf.avg_amount_7d, 0) AS avg_amount_7d,
    COALESCE(uf.avg_amount_30d, 0) AS avg_amount_30d,
    COALESCE(uf.avg_amount_90d, 0) AS avg_amount_90d,
    COALESCE(uf.std_amount_30d, 0) AS std_amount_30d,
    COALESCE(uf.tx_count_7d, 0) AS tx_count_7d,
    COALESCE(uf.tx_count_30d, 0) AS tx_count_30d,
    COALESCE(uf.unique_merchants_30d, 0) AS unique_merchants_30d,
    COALESCE(uf.fraud_rate_30d, 0) AS fraud_rate_30d,
    COALESCE(mf.fraud_rate_30d, 0) AS merchant_fraud_rate,
    HOUR(t.transaction_date) AS hour_of_day,
    DAYOFWEEK(t.transaction_date) AS day_of_week,
    CASE WHEN HOUR(t.transaction_date) BETWEEN 2 AND 5 THEN 1 ELSE 0 END AS is_night,
    CASE WHEN DAYOFWEEK(t.transaction_date) IN (1, 7) THEN 1 ELSE 0 END AS is_weekend
FROM transactions t
LEFT JOIN accounts a ON a.id = t.account_id AND a.company_id = t.company_id
LEFT JOIN user_features uf
       ON uf.user_id = a.user_id AND uf.company_id = t.company_id
LEFT JOIN merchant_features mf
       ON mf.merchant_id = t.merchant_id AND mf.company_id = t.company_id
WHERE t.company_id = :company_id
  AND t.transaction_date >= :start_ts
  AND t.transaction_date < :end_ts
""")

_MONITORING_VELOCITY_SQL = text("""
SELECT
    t.id AS transaction_id,
    COALESCE(v15.tx_count, 0) AS velocity_15min,
    COALESCE(v60.tx_count, 0) AS velocity_60min
FROM transactions t
LEFT JOIN accounts a ON a.id = t.account_id AND a.company_id = t.company_id
LEFT JOIN velocity_features v15
       ON v15.user_id = a.user_id
      AND v15.company_id = t.company_id
      AND v15.window_minutes = 15
LEFT JOIN velocity_features v60
       ON v60.user_id = a.user_id
      AND v60.company_id = t.company_id
      AND v60.window_minutes = 60
WHERE t.company_id = :company_id
  AND t.transaction_date >= :start_ts
  AND t.transaction_date < :end_ts
""")

_MONITORING_MERCHANT_NEW_SQL = text("""
SELECT
    t.id AS transaction_id,
    CASE WHEN EXISTS (
        SELECT 1 FROM transactions t2
        INNER JOIN accounts a2 ON a2.id = t2.account_id
        WHERE a2.user_id = (SELECT a0.user_id FROM accounts a0
                            WHERE a0.id = t.account_id AND a0.company_id = t.company_id)
          AND t2.merchant_id = t.merchant_id
          AND t2.company_id = t.company_id
          AND t2.id < t.id
    ) THEN 0 ELSE 1 END AS is_new_merchant
FROM transactions t
WHERE t.company_id = :company_id
  AND t.transaction_date >= :start_ts
  AND t.transaction_date < :end_ts
""")


@dataclass(frozen=True)
class ModelHealthComputationResult:
    """Outcome of one company weekly health run."""

    company_id: int
    period_start: date
    period_end: date
    alert_triggered: bool
    drift_feature_count: int
    recommendation: str


def load_ml_manifest() -> dict[str, Any]:
    """Read serving manifest + PSI baselines from ML_MODEL_DIR."""
    path = Path(settings.ML_MODEL_DIR) / "feature_columns.json"
    if not path.exists():
        raise FileNotFoundError(f"ML manifest missing: {path}")
    return json.loads(path.read_text())


def _previous_iso_week(reference: datetime) -> tuple[date, date]:
    """Monday–Sunday (UTC) of the calendar week immediately before reference's week."""
    ref = reference.astimezone(timezone.utc).date()
    days_since_monday = ref.weekday()
    this_monday = ref - timedelta(days=days_since_monday)
    prev_sunday = this_monday - timedelta(days=1)
    prev_monday = prev_sunday - timedelta(days=6)
    return prev_monday, prev_sunday


def _psi_from_histogram(expected_pct: Sequence[float], actual_pct: Sequence[float]) -> float:
    """PSI = sum((A-E)*ln(A/E)) with epsilon stabilization."""
    total = 0.0
    for e_raw, a_raw in zip(expected_pct, actual_pct, strict=True):
        e = max(float(e_raw), PSI_PCT_EPSILON)
        a = max(float(a_raw), PSI_PCT_EPSILON)
        total += (a - e) * math.log(a / e)
    return float(total)


def _status_for_psi(psi: float) -> PsiStatus:
    if psi < settings.MODEL_HEALTH_PSI_MONITOR_THRESHOLD:
        return PsiStatus.STABLE
    if psi < settings.MODEL_HEALTH_PSI_DRIFT_THRESHOLD:
        return PsiStatus.MONITOR
    return PsiStatus.DRIFT


def _build_bin_expected_actual(
    values: np.ndarray,
    bin_edges: list[float],
    expected_pct: list[float],
) -> tuple[list[float], list[float]] | None:
    """Map values into training bins; return normalized percentages or None if degenerate."""
    edges = np.asarray(bin_edges, dtype=np.float64)
    if edges.size < 2 or values.size == 0:
        return None
    counts, _ = np.histogram(values, bins=edges)
    actual = counts.astype(np.float64)
    s = actual.sum()
    if s <= 0:
        return None
    actual_pct = (actual / s).tolist()
    exp = np.asarray(expected_pct, dtype=np.float64)
    exp = exp / max(exp.sum(), PSI_PCT_EPSILON)
    return exp.tolist(), actual_pct


def compute_psi_for_feature(
    values: np.ndarray,
    baseline_entry: dict[str, Any] | None,
) -> tuple[float | None, PsiStatus | None]:
    """PSI for one feature vs training manifest bins."""
    if baseline_entry is None or values.size == 0:
        return None, None
    edges = baseline_entry.get("bin_edges")
    exp = baseline_entry.get("expected_pct")
    if (
        not isinstance(edges, list)
        or not isinstance(exp, list)
        or len(edges) < 2
        or len(exp) != len(edges) - 1
    ):
        return None, None
    mapped = _build_bin_expected_actual(values, [float(x) for x in edges], [float(x) for x in exp])
    if mapped is None:
        return None, None
    e_list, a_list = mapped
    psi = _psi_from_histogram(e_list, a_list)
    return psi, _status_for_psi(psi)


def _per_feature_quantiles(values: np.ndarray) -> dict[str, float | None]:
    if values.size == 0:
        return {
            "mean": None,
            "std": None,
            "p25": None,
            "p50": None,
            "p75": None,
            "p95": None,
        }
    return {
        "mean": float(np.mean(values)),
        "std": float(np.std(values)),
        "p25": float(np.percentile(values, 25)),
        "p50": float(np.percentile(values, 50)),
        "p75": float(np.percentile(values, 75)),
        "p95": float(np.percentile(values, 95)),
    }


async def _fetch_company_feature_matrix(
    db: AsyncSession,
    company_id: int,
    start_ts: datetime,
    end_ts: datetime,
) -> dict[int, dict[str, float]]:
    """Transaction-id keyed feature rows for drift window (same schema as training)."""
    velocity = await db.execute(
        _MONITORING_VELOCITY_SQL,
        {"company_id": company_id, "start_ts": start_ts, "end_ts": end_ts},
    )
    vel_map = {int(r[0]): (float(r[1]), float(r[2])) for r in velocity.all()}
    merch = await db.execute(
        _MONITORING_MERCHANT_NEW_SQL,
        {"company_id": company_id, "start_ts": start_ts, "end_ts": end_ts},
    )
    merch_map = {int(r[0]): float(r[1]) for r in merch.all()}

    rows_result = await db.execute(
        _MONITORING_BASE_SQL,
        {"company_id": company_id, "start_ts": start_ts, "end_ts": end_ts},
    )
    out: dict[int, dict[str, float]] = {}
    for r in rows_result.mappings().all():
        tid = int(r["id"])
        avg30 = float(r["avg_amount_30d"])
        std30 = float(r["std_amount_30d"])
        amount = float(r["amount"])
        vel = vel_map.get(tid, (0.0, 0.0))
        out[tid] = {
            "avg_amount_7d": float(r["avg_amount_7d"]),
            "avg_amount_30d": avg30,
            "avg_amount_90d": float(r["avg_amount_90d"]),
            "std_amount_30d": std30,
            "tx_count_7d": float(r["tx_count_7d"]),
            "tx_count_30d": float(r["tx_count_30d"]),
            "velocity_15min": vel[0],
            "velocity_60min": vel[1],
            "unique_merchants_30d": float(r["unique_merchants_30d"]),
            "fraud_rate_30d": float(r["fraud_rate_30d"]),
            "merchant_fraud_rate": float(r["merchant_fraud_rate"]),
            "amount": amount,
            "amount_to_avg_ratio": amount / (avg30 + FEATURE_EPSILON),
            "amount_zscore": (amount - avg30) / (std30 + FEATURE_EPSILON),
            "is_new_merchant": merch_map.get(tid, 0.0),
            "is_night": float(r["is_night"]),
            "is_weekend": float(r["is_weekend"]),
            "hour_of_day": float(r["hour_of_day"]),
            "day_of_week": float(r["day_of_week"]),
        }
    return out


async def _cohort_confusion_counts(
    db: AsyncSession,
    company_id: int,
    start_d: date,
    end_d: date,
) -> dict[str, int]:
    """TP/FP/TN/FN on txs with a confirmed analyst resolution in the period.

    y_true comes from human labels only. y_pred is whether an ML alert fired in-window.
    """
    start_ts = datetime.combine(start_d, datetime.min.time(), tzinfo=timezone.utc)
    end_ts = datetime.combine(end_d + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    q = text("""
        WITH confirmed AS (
            SELECT transaction_id,
                   MAX(CASE WHEN resolved_by_analyst_label = 'fraud' THEN 1 ELSE 0 END)
                       AS is_fraud
            FROM fraud_alerts
            WHERE company_id = :company_id
              AND COALESCE(is_confirmed, 0) = 1
              AND resolved_by_analyst_label IS NOT NULL
              AND resolved_at >= :start_ts
              AND resolved_at < :end_ts
            GROUP BY transaction_id
        )
        SELECT c.is_fraud AS y_true,
               CASE WHEN EXISTS (
                   SELECT 1 FROM fraud_alerts f
                   WHERE f.transaction_id = c.transaction_id
                     AND f.company_id = :company_id
                     AND f.alert_type = 'ml_fraud_score'
                     AND f.created_at >= :start_ts
                     AND f.created_at < :end_ts
               ) THEN 1 ELSE 0 END AS y_pred
        FROM confirmed c
    """)
    result = await db.execute(
        q, {"company_id": company_id, "start_ts": start_ts, "end_ts": end_ts}
    )
    tp = fp = tn = fn = 0
    for row in result.mappings():
        y_true = int(row["y_true"])
        y_pred = int(row["y_pred"])
        if y_true == 1 and y_pred == 1:
            tp += 1
        elif y_true == 0 and y_pred == 1:
            fp += 1
        elif y_true == 0 and y_pred == 0:
            tn += 1
        else:
            fn += 1
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn}


async def _auc_pr_on_ml_scores(
    db: AsyncSession,
    company_id: int,
    start_ts: datetime,
    end_ts: datetime,
) -> float | None:
    """Average precision on ML alerts with human labels (needs both classes)."""
    from sklearn.metrics import average_precision_score

    stmt = (
        select(FraudAlert.confidence_score, FraudAlert.resolved_by_analyst_label)
        .where(
            FraudAlert.company_id == company_id,
            FraudAlert.alert_type == AlertType.ML_FRAUD_SCORE,
            FraudAlert.is_confirmed.is_(True),
            FraudAlert.resolved_by_analyst_label.isnot(None),
            FraudAlert.created_at >= start_ts,
            FraudAlert.created_at < end_ts,
            FraudAlert.confidence_score.isnot(None),
        )
    )
    res = await db.execute(stmt)
    rows = res.all()
    if len(rows) < 5:
        return None
    y = np.array([1 if lbl == AnalystGroundTruth.FRAUD else 0 for _, lbl in rows])
    scores = np.array([float(s or 0) / 100.0 if (s or 0) > 1 else float(s or 0) for s, _ in rows])
    if len(np.unique(y)) < 2:
        return None
    return float(average_precision_score(y, scores))


async def _avg_ml_score_period(
    db: AsyncSession, company_id: int, start_ts: datetime, end_ts: datetime
) -> float | None:
    stmt = select(func.avg(FraudAlert.confidence_score)).where(
        FraudAlert.company_id == company_id,
        FraudAlert.alert_type == AlertType.ML_FRAUD_SCORE,
        FraudAlert.created_at >= start_ts,
        FraudAlert.created_at < end_ts,
        FraudAlert.confidence_score.isnot(None),
    )
    raw = (await db.execute(stmt)).scalar_one_or_none()
    if raw is None:
        return None
    val = float(raw)
    return val / 100.0 if val > 1.0 else val


def _rates_from_counts(counts: dict[str, int]) -> dict[str, float | None]:
    tp, fp, tn, fn = counts["tp"], counts["fp"], counts["tn"], counts["fn"]
    prec_d = tp + fp
    rec_d = tp + fn
    fpr_d = fp + tn
    return {
        "precision": (tp / prec_d) if prec_d else None,
        "recall": (tp / rec_d) if rec_d else None,
        "f1": None,
        "false_positive_rate": (fp / fpr_d) if fpr_d else None,
    }


def _f1_from_pr(p: float | None, r: float | None) -> float | None:
    if p is None or r is None or (p + r) <= 0:
        return None
    return 2 * p * r / (p + r)


async def _replace_snapshots(
    db: AsyncSession,
    company_id: int,
    period_start: date,
    period_end: date,
    snapshots: list[FeatureDistributionSnapshot],
) -> None:
    await db.execute(
        delete(FeatureDistributionSnapshot).where(
            FeatureDistributionSnapshot.company_id == company_id,
            FeatureDistributionSnapshot.period_start == period_start,
        )
    )
    for s in snapshots:
        db.add(s)


async def _upsert_performance(
    db: AsyncSession,
    company_id: int,
    period_start: date,
    period_end: date,
    metrics: dict[str, Any],
    model_version: str | None,
) -> None:
    stmt = select(ModelPerformanceMetric).where(
        ModelPerformanceMetric.company_id == company_id,
        ModelPerformanceMetric.period_start == period_start,
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        row = ModelPerformanceMetric(
            company_id=company_id,
            period_start=period_start,
            period_end=period_end,
        )
        db.add(row)
    row.period_end = period_end
    row.f1_score = metrics.get("f1")
    row.precision_score = metrics.get("precision")
    row.recall_score = metrics.get("recall")
    row.auc_pr = metrics.get("auc_pr")
    row.false_positive_rate = metrics.get("false_positive_rate")
    row.avg_ml_score = metrics.get("avg_ml_score")
    row.sample_count = int(metrics.get("sample_count", 0))
    row.model_version = model_version


def _recommendation(
    f1: float | None,
    prec: float | None,
    drifted_features: int,
    monitor_features: int,
) -> str:
    if drifted_features >= settings.MODEL_HEALTH_PSI_DRIFT_MIN_FEATURES:
        return RECOMMENDATION_RETRAIN
    if (
        (f1 is not None and f1 < settings.MODEL_HEALTH_F1_THRESHOLD)
        or (prec is not None and prec < settings.MODEL_HEALTH_PRECISION_THRESHOLD)
        or monitor_features >= 1
    ):
        return RECOMMENDATION_MONITOR
    return RECOMMENDATION_STABLE


def recommendation_from_metrics(
    f1: float | None,
    precision: float | None,
    drifted_features: int,
    *,
    monitor_features: int = 0,
) -> str:
    """Map latest metrics + drift counts to a stable / monitor / retrain label."""
    return _recommendation(f1, precision, drifted_features, monitor_features)


async def _maybe_raise_alert(
    db: AsyncSession,
    company_id: int,
    *,
    f1: float | None,
    precision: float | None,
    drifted_features: int,
    period_start: date,
) -> bool:
    low_f1 = f1 is not None and f1 < settings.MODEL_HEALTH_F1_THRESHOLD
    low_p = precision is not None and precision < settings.MODEL_HEALTH_PRECISION_THRESHOLD
    psi_bad = drifted_features >= settings.MODEL_HEALTH_PSI_DRIFT_MIN_FEATURES
    if not (low_f1 or low_p or psi_bad):
        return False
    title = "ML model health threshold breached"
    body_parts = []
    if low_f1:
        body_parts.append(f"F1 below threshold ({settings.MODEL_HEALTH_F1_THRESHOLD})")
    if low_p:
        body_parts.append(
            f"Precision below threshold ({settings.MODEL_HEALTH_PRECISION_THRESHOLD})"
        )
    if psi_bad:
        body_parts.append(
            f"PSI drift on >= {settings.MODEL_HEALTH_PSI_DRIFT_MIN_FEATURES} features"
        )
    meta = {
        "company_id": company_id,
        "period_start": period_start.isoformat(),
        "f1": f1,
        "precision": precision,
        "drifted_feature_count": drifted_features,
    }
    db.add(
        AdminNotification(
            company_id=company_id,
            notification_type=AdminNotificationType.MODEL_HEALTH,
            severity=AdminNotificationSeverity.CRITICAL,
            title=title,
            body="; ".join(body_parts),
            metadata_=meta,
        )
    )
    logger.critical(
        "model_health.alert",
        company_id=company_id,
        period_start=str(period_start),
        f1=f1,
        precision=precision,
        drifted_features=drifted_features,
    )
    return True


async def compute_model_health_for_company(
    db: AsyncSession,
    company_id: int,
    *,
    reference_time: datetime | None = None,
) -> ModelHealthComputationResult:
    """Persist weekly metrics + feature snapshots; raise admin alert if needed."""
    ref = reference_time or datetime.now(timezone.utc)
    period_start, period_end = _previous_iso_week(ref)
    manifest = load_ml_manifest()
    model_version = manifest.get("trained_at")
    psi_baselines: dict[str, Any] = manifest.get("feature_psi_baselines") or {}

    drift_days = settings.MODEL_HEALTH_DRIFT_WINDOW_DAYS
    drift_end = datetime.combine(
        period_end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc
    )
    drift_start = drift_end - timedelta(days=drift_days)

    matrix = await _fetch_company_feature_matrix(db, company_id, drift_start, drift_end)
    arrays: dict[str, np.ndarray] = {
        name: np.array([row[name] for row in matrix.values()], dtype=np.float64)
        for name in FEATURE_COLUMNS
    }

    snapshots: list[FeatureDistributionSnapshot] = []
    drifted = 0
    monitor_n = 0
    for feat in FEATURE_COLUMNS:
        arr = arrays.get(feat, np.array([]))
        stats = _per_feature_quantiles(arr)
        psi_val, psi_st = compute_psi_for_feature(arr, psi_baselines.get(feat))
        if psi_st == PsiStatus.DRIFT:
            drifted += 1
        elif psi_st == PsiStatus.MONITOR:
            monitor_n += 1
        snapshots.append(
            FeatureDistributionSnapshot(
                company_id=company_id,
                feature_name=feat,
                period_start=period_start,
                period_end=period_end,
                mean=stats["mean"],
                std=stats["std"],
                p25=stats["p25"],
                p50=stats["p50"],
                p75=stats["p75"],
                p95=stats["p95"],
                psi_score=psi_val,
                psi_status=psi_st,
            )
        )

    week_start_ts = datetime.combine(period_start, datetime.min.time(), tzinfo=timezone.utc)
    week_end_ts = datetime.combine(
        period_end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc
    )
    counts = await _cohort_confusion_counts(db, company_id, period_start, period_end)
    rates = _rates_from_counts(counts)
    rates["f1"] = _f1_from_pr(rates["precision"], rates["recall"])
    rates["auc_pr"] = await _auc_pr_on_ml_scores(db, company_id, week_start_ts, week_end_ts)
    rates["avg_ml_score"] = await _avg_ml_score_period(
        db, company_id, week_start_ts, week_end_ts
    )
    rates["sample_count"] = sum(counts.values())

    await _replace_snapshots(db, company_id, period_start, period_end, snapshots)
    await _upsert_performance(
        db,
        company_id,
        period_start,
        period_end,
        {**rates, "sample_count": rates.get("sample_count", 0)},
        model_version,
    )

    rec = _recommendation(rates["f1"], rates["precision"], drifted, monitor_n)
    alerted = await _maybe_raise_alert(
        db,
        company_id,
        f1=rates["f1"],
        precision=rates["precision"],
        drifted_features=drifted,
        period_start=period_start,
    )
    await db.commit()
    logger.info(
        "model_health.computed",
        company_id=company_id,
        period_start=str(period_start),
        recommendation=rec,
        drifted_features=drifted,
    )
    return ModelHealthComputationResult(
        company_id=company_id,
        period_start=period_start,
        period_end=period_end,
        alert_triggered=alerted,
        drift_feature_count=drifted,
        recommendation=rec,
    )

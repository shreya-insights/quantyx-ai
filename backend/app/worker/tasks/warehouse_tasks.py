"""Nightly warehouse ETL — sync SQLAlchemy session; idempotent DELETE + INSERT per company."""

from __future__ import annotations

import time
from datetime import date, datetime

import structlog
from celery import shared_task
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.company import Company
from app.utils.metrics import WAREHOUSE_ETL_DURATION_SECONDS

logger = structlog.get_logger(__name__)

_TASK_NAME = "quantyx.warehouse.run_nightly_etl"
_COHORT_MAX_MONTHS = 18
_HEATMAP_LOOKBACK_DAYS = 90
def _sync_session_factory() -> tuple[object, sessionmaker[Session]]:
    engine = create_engine(
        settings.SYNC_DATABASE_URL,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=2,
    )
    factory = sessionmaker(
        bind=engine,
        class_=Session,
        autocommit=False,
        autoflush=False,
    )
    return engine, factory


def _observe_step(step: str, started: float) -> None:
    elapsed = max(0.0, time.perf_counter() - started)
    WAREHOUSE_ETL_DURATION_SECONDS.labels(step=step).observe(elapsed)


def _build_cohort_retention(session: Session, company_id: int) -> int:
    t0 = time.perf_counter()
    session.execute(
        text("DELETE FROM cohort_retention_metrics WHERE company_id = :cid"),
        {"cid": company_id},
    )
    insert_sql = text(
        """
        INSERT INTO cohort_retention_metrics (
            company_id, cohort_month, months_since_cohort,
            user_count, retained_count, retention_rate, refreshed_at
        )
        WITH user_cohorts AS (
            SELECT u.id AS user_id, DATE_FORMAT(u.created_at, '%Y-%m') AS cohort_month
            FROM users u
            WHERE u.company_id = :company_id
        ),
        user_transactions AS (
            SELECT DISTINCT
                a.user_id,
                DATE_FORMAT(t.transaction_date, '%Y-%m') AS tx_month
            FROM transactions t
            INNER JOIN accounts a ON t.account_id = a.id
            WHERE t.company_id = :company_id
              AND t.status = 'completed'
              AND a.user_id IS NOT NULL
        ),
        cohort_activity AS (
            SELECT
                uc.cohort_month,
                uc.user_id,
                PERIOD_DIFF(
                    EXTRACT(YEAR_MONTH FROM STR_TO_DATE(CONCAT(ut.tx_month, '-01'), '%Y-%m-%d')),
                    EXTRACT(YEAR_MONTH FROM STR_TO_DATE(CONCAT(uc.cohort_month, '-01'), '%Y-%m-%d'))
                ) AS period_number
            FROM user_cohorts uc
            INNER JOIN user_transactions ut ON uc.user_id = ut.user_id
            WHERE PERIOD_DIFF(
                EXTRACT(YEAR_MONTH FROM STR_TO_DATE(CONCAT(ut.tx_month, '-01'), '%Y-%m-%d')),
                EXTRACT(YEAR_MONTH FROM STR_TO_DATE(CONCAT(uc.cohort_month, '-01'), '%Y-%m-%d'))
            ) BETWEEN 0 AND :max_months
        ),
        cohort_sizes AS (
            SELECT cohort_month, COUNT(DISTINCT user_id) AS cohort_size
            FROM user_cohorts
            GROUP BY cohort_month
        ),
        retention_raw AS (
            SELECT cohort_month, period_number, COUNT(DISTINCT user_id) AS retained_users
            FROM cohort_activity
            GROUP BY cohort_month, period_number
        )
        SELECT
            :company_id,
            cs.cohort_month,
            rr.period_number,
            cs.cohort_size,
            rr.retained_users,
            ROUND(rr.retained_users * 100.0 / NULLIF(cs.cohort_size, 0), 4),
            NOW(6)
        FROM cohort_sizes cs
        INNER JOIN retention_raw rr ON cs.cohort_month = rr.cohort_month
        """
    )
    session.execute(
        insert_sql,
        {
            "company_id": company_id,
            "max_months": _COHORT_MAX_MONTHS,
        },
    )
    cnt_row = session.execute(
        text(
            "SELECT COUNT(*) FROM cohort_retention_metrics WHERE company_id = :cid"
        ),
        {"cid": company_id},
    ).fetchone()
    n = int(cnt_row[0]) if cnt_row else 0
    _observe_step("cohort", t0)
    return n


def _ltv_segment_for_spend(spend: float, p33: float, p66: float) -> str:
    """Assign tertiles by empirical spend thresholds (p33 / p66 order stats)."""
    if spend <= p33:
        return "low"
    if spend <= p66:
        return "medium"
    return "high"


def _build_ltv_segments(session: Session, company_id: int) -> int:
    t0 = time.perf_counter()
    session.execute(
        text("DELETE FROM lifetime_value_metrics WHERE company_id = :cid"),
        {"cid": company_id},
    )
    rows = session.execute(
        text(
            """
            SELECT
                a.user_id AS user_id,
                MIN(DATE(t.transaction_date)) AS first_tx_date,
                SUM(t.amount) AS total_spend,
                COUNT(*) AS tx_count
            FROM transactions t
            INNER JOIN accounts a ON t.account_id = a.id
            WHERE t.company_id = :company_id
              AND t.status = 'completed'
              AND a.user_id IS NOT NULL
            GROUP BY a.user_id
            """
        ),
        {"company_id": company_id},
    ).mappings().all()
    if not rows:
        _observe_step("ltv", t0)
        return 0
    spends = sorted(float(r["total_spend"]) for r in rows)
    n_users = len(spends)
    p33 = spends[max(0, int(0.33 * (n_users - 1)))]
    p66 = spends[max(0, int(0.66 * (n_users - 1)))]

    insert_stmt = text(
        """
        INSERT INTO lifetime_value_metrics (
            company_id, user_id, first_tx_date, total_spend, tx_count,
            ltv_segment, refreshed_at
        ) VALUES (
            :company_id, :user_id, :first_tx_date, :total_spend, :tx_count,
            :ltv_segment, NOW(6)
        )
        """
    )
    for r in rows:
        txd = r["first_tx_date"]
        if isinstance(txd, datetime):
            txd_d: date = txd.date()
        elif isinstance(txd, date):
            txd_d = txd
        else:
            txd_d = date.fromisoformat(str(txd)[:10])
        seg = _ltv_segment_for_spend(float(r["total_spend"]), p33, p66)
        session.execute(
            insert_stmt,
            {
                "company_id": company_id,
                "user_id": int(r["user_id"]),
                "first_tx_date": txd_d,
                "total_spend": float(r["total_spend"]),
                "tx_count": int(r["tx_count"]),
                "ltv_segment": seg,
            },
        )
    _observe_step("ltv", t0)
    return n_users


def _build_hourly_heatmap(session: Session, company_id: int) -> int:
    t0 = time.perf_counter()
    session.execute(
        text("DELETE FROM hourly_transaction_heatmaps WHERE company_id = :cid"),
        {"cid": company_id},
    )
    insert_sql = text(
        """
        INSERT INTO hourly_transaction_heatmaps (
            company_id, day_of_week, hour_of_day,
            avg_count, avg_amount, fraud_rate, refreshed_at
        )
        SELECT
            :company_id AS company_id,
            MOD(DAYOFWEEK(t.transaction_date) + 5, 7) AS dow,
            HOUR(t.transaction_date) AS hod,
            ROUND(COUNT(t.id) / GREATEST(1, FLOOR(:days / 7)), 4) AS avg_count,
            ROUND(AVG(t.amount), 4) AS avg_amount,
            ROUND(
                COALESCE(SUM(CASE WHEN fa.id IS NOT NULL THEN 1 ELSE 0 END), 0)
                / NULLIF(COUNT(t.id), 0),
                6
            ) AS fraud_rate,
            NOW(6) AS refreshed_at
        FROM transactions t
        LEFT JOIN fraud_alerts fa
          ON fa.transaction_id = t.id AND fa.company_id = t.company_id
        WHERE t.company_id = :company_id
          AND t.status = 'completed'
          AND t.transaction_date >= DATE_SUB(NOW(), INTERVAL :days DAY)
        GROUP BY
            MOD(DAYOFWEEK(t.transaction_date) + 5, 7),
            HOUR(t.transaction_date)
        """
    )
    session.execute(
        insert_sql,
        {"company_id": company_id, "days": _HEATMAP_LOOKBACK_DAYS},
    )
    cnt_row = session.execute(
        text(
            "SELECT COUNT(*) FROM hourly_transaction_heatmaps WHERE company_id = :cid"
        ),
        {"cid": company_id},
    ).fetchone()
    n = int(cnt_row[0]) if cnt_row else 0
    _observe_step("heatmap", t0)
    return n


def _run_warehouse_for_company(session: Session, company_id: int) -> dict[str, int]:
    cohort_n = _build_cohort_retention(session, company_id)
    ltv_n = _build_ltv_segments(session, company_id)
    heat_n = _build_hourly_heatmap(session, company_id)
    return {
        "company_id": company_id,
        "cohort_rows": cohort_n,
        "ltv_rows": ltv_n,
        "heatmap_rows": heat_n,
    }


@shared_task(bind=True, name=_TASK_NAME, queue="analytics")
def run_nightly_warehouse_etl(self) -> dict[str, object]:
    """Populate warehouse tables for all active tenants; DELETE+INSERT is idempotent."""
    task_start = time.perf_counter()
    engine, factory = _sync_session_factory()
    results: list[dict[str, int]] = []
    try:
        with factory() as session:
            company_ids = session.scalars(
                select(Company.id).where(Company.is_active.is_(True))
            ).all()
            for cid in company_ids:
                cid_int = int(cid)
                company_t0 = time.perf_counter()
                try:
                    stats = _run_warehouse_for_company(session, cid_int)
                    session.commit()
                    elapsed_ms = int((time.perf_counter() - company_t0) * 1000)
                    logger.info(
                        "warehouse.etl_company_done",
                        task_id=self.request.id,
                        elapsed_ms=elapsed_ms,
                        **stats,
                    )
                    results.append(stats)
                except Exception:
                    session.rollback()
                    logger.error(
                        "warehouse.etl_company_error",
                        task_id=self.request.id,
                        company_id=cid_int,
                        exc_info=True,
                    )
                    raise
    finally:
        engine.dispose()

    total_ms = int((time.perf_counter() - task_start) * 1000)
    logger.info(
        "warehouse.etl_batch_done",
        task_id=self.request.id,
        companies=len(results),
        total_elapsed_ms=total_ms,
    )
    return {"companies_refreshed": len(results), "details": results}

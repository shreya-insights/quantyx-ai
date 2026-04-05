"""OLAP warehouse tables — denormalized, no FKs; populated by nightly Celery ETL.

Read path uses composite indexes on company_id; upserts use unique natural keys.
"""

from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import BigIntPK

_LTV_SEGMENT_LEN = 16


class CohortRetentionMetric(Base):
    """Cohort × months-since grid for retention heatmaps (one row per cell)."""

    __tablename__ = "cohort_retention_metrics"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigIntPK, nullable=False)
    cohort_month: Mapped[str] = mapped_column(String(7), nullable=False)
    months_since_cohort: Mapped[int] = mapped_column(Integer, nullable=False)
    user_count: Mapped[int] = mapped_column(Integer, nullable=False)
    retained_count: Mapped[int] = mapped_column(Integer, nullable=False)
    retention_rate: Mapped[float] = mapped_column(Float, nullable=False)
    refreshed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "cohort_month",
            "months_since_cohort",
            name="uq_cohort_retention_company_cohort_period",
        ),
        Index("ix_cohort_retention_company", "company_id"),
    )


class LifetimeValueMetric(Base):
    """Per-user LTV snapshot with tertile segment from spend percentiles."""

    __tablename__ = "lifetime_value_metrics"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigIntPK, nullable=False)
    user_id: Mapped[int] = mapped_column(BigIntPK, nullable=False)
    first_tx_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_spend: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    tx_count: Mapped[int] = mapped_column(Integer, nullable=False)
    ltv_segment: Mapped[str] = mapped_column(String(_LTV_SEGMENT_LEN), nullable=False)
    refreshed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "user_id",
            name="uq_ltv_company_user",
        ),
        Index("ix_ltv_company_segment", "company_id", "ltv_segment"),
    )


class HourlyTransactionHeatmap(Base):
    """7×24 pre-aggregated transaction intensity + fraud rate."""

    __tablename__ = "hourly_transaction_heatmaps"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigIntPK, nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    hour_of_day: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_count: Mapped[float] = mapped_column(Float, nullable=False)
    avg_amount: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    fraud_rate: Mapped[float] = mapped_column(Float, nullable=False)
    refreshed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "day_of_week",
            "hour_of_day",
            name="uq_heatmap_company_dow_hod",
        ),
        Index("ix_heatmap_company", "company_id"),
    )

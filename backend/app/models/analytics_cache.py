"""Pre-aggregated analytics cache tables — populated by Celery Beat.

These are not materialized views (MySQL has none); plain tables with
INSERT ... ON DUPLICATE KEY UPDATE for hourly, idempotent refreshes.
Tenant isolation: every row is keyed by company_id.
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


class DailyRevenueSummary(Base):
    """Monthly revenue aggregates per tenant (one row per calendar month)."""

    __tablename__ = "daily_revenue_summaries"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigIntPK, nullable=False)
    summary_month: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM
    inflow: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    outflow: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    net_flow: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    transaction_count: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_transaction: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    mom_growth_pct: Mapped[float | None] = mapped_column(Numeric(18, 4))
    transaction_snapshot_count: Mapped[int] = mapped_column(Integer, nullable=False)
    refreshed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "company_id", "summary_month", name="uq_revenue_company_month"
        ),
        Index("ix_revenue_company_refreshed", "company_id", "refreshed_at"),
    )


class MonthlyCategorySummary(Base):
    """Debit spending by category for a rolling window (period_days)."""

    __tablename__ = "monthly_category_summaries"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigIntPK, nullable=False)
    category_code: Mapped[str] = mapped_column(String(32), nullable=False)
    category_name: Mapped[str] = mapped_column(String(100), nullable=False)
    period_days: Mapped[int] = mapped_column(Integer, nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    transaction_count: Mapped[int] = mapped_column(Integer, nullable=False)
    pct_of_total: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    transaction_snapshot_count: Mapped[int] = mapped_column(Integer, nullable=False)
    refreshed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "category_code",
            "period_days",
            name="uq_category_company_code_period",
        ),
        Index("ix_category_company_refreshed", "company_id", "refreshed_at"),
    )


class MerchantRankingCache(Base):
    """Top-merchant ranking snapshot for a rolling window (period_days)."""

    __tablename__ = "merchant_ranking_caches"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigIntPK, nullable=False)
    merchant_id: Mapped[int] = mapped_column(BigIntPK, nullable=False)
    period_days: Mapped[int] = mapped_column(Integer, nullable=False)
    merchant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category_code: Mapped[str | None] = mapped_column(String(10))
    rank_position: Mapped[int] = mapped_column(Integer, nullable=False)
    total_revenue: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    transaction_count: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_transaction: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    revenue_share_pct: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    rank_in_category: Mapped[int] = mapped_column(Integer, nullable=False)
    transaction_snapshot_count: Mapped[int] = mapped_column(Integer, nullable=False)
    refreshed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "merchant_id",
            "period_days",
            name="uq_merchant_ranking_company_merchant_period",
        ),
        Index(
            "ix_merchant_ranking_company_refreshed", "company_id", "refreshed_at"
        ),
    )


class KPISummaryCache(Base):
    """Dashboard KPI snapshot for a date range (period_type encodes bounds)."""

    __tablename__ = "kpi_summary_caches"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigIntPK, nullable=False)
    period_type: Mapped[str] = mapped_column(String(64), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    total_transactions: Mapped[int] = mapped_column(Integer, nullable=False)
    total_volume: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    total_inflow: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    total_outflow: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    unique_customers: Mapped[int] = mapped_column(Integer, nullable=False)
    unique_merchants: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_transaction_value: Mapped[float] = mapped_column(
        Numeric(18, 4), nullable=False
    )
    fraud_alert_count: Mapped[int] = mapped_column(Integer, nullable=False)
    fraud_alert_rate_pct: Mapped[float] = mapped_column(Float, nullable=False)
    active_accounts: Mapped[int] = mapped_column(Integer, nullable=False)
    top_category: Mapped[str | None] = mapped_column(String(100))
    mom_volume_growth_pct: Mapped[float | None] = mapped_column(Float)
    transaction_snapshot_count: Mapped[int] = mapped_column(Integer, nullable=False)
    refreshed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("company_id", "period_type", name="uq_kpi_company_period"),
        Index("ix_kpi_company_refreshed", "company_id", "refreshed_at"),
    )

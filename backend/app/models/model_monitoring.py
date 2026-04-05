"""Time-sliced ML performance and feature distribution snapshots for drift monitoring."""

from datetime import date, datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import BigIntPK


class PsiStatus(str, PyEnum):
    """Population stability band for a feature vs training baseline."""

    STABLE = "stable"
    MONITOR = "monitor"
    DRIFT = "drift"


class ModelPerformanceMetric(Base):
    """Aggregated classifier quality for a company over a reporting period."""

    __tablename__ = "model_performance_metrics"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    f1_score: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    precision_score: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    recall_score: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    auc_pr: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    false_positive_rate: Mapped[float | None] = mapped_column(
        Numeric(10, 6), nullable=True
    )
    avg_ml_score: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    model_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    company: Mapped["Company"] = relationship("Company", back_populates="performance_metrics")  # noqa: F821

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "period_start",
            name="uq_perf_metric_company_period",
        ),
        Index("idx_perf_metric_company", "company_id"),
        Index("idx_perf_metric_period", "period_start"),
    )


class FeatureDistributionSnapshot(Base):
    """Per-feature distribution stats and PSI vs training baseline for one period."""

    __tablename__ = "feature_distribution_snapshots"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    feature_name: Mapped[str] = mapped_column(String(64), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    mean: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    std: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    p25: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    p50: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    p75: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    p95: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    psi_score: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    psi_status: Mapped[PsiStatus | None] = mapped_column(
        Enum(
            PsiStatus,
            values_callable=lambda x: [e.value for e in x],
            name="psi_status",
        ),
        nullable=True,
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    company: Mapped["Company"] = relationship("Company", back_populates="feature_snapshots")  # noqa: F821

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "feature_name",
            "period_start",
            name="uq_feature_snap_company_feature_period",
        ),
        Index("idx_feature_snap_company", "company_id"),
        Index("idx_feature_snap_feature", "feature_name"),
    )

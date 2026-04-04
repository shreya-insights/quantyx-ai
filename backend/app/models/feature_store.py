"""Feature store ORM — point-in-time snapshots per tenant + entity.

computed_at: enables temporal joins for training without future leakage.
version: supports rollback when feature logic changes.
Separate tables: user / merchant / velocity reflect different refresh cadences.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import BigIntPK


class UserFeatures(Base):
    """Rolling behavioral aggregates per user within a company."""

    __tablename__ = "user_features"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigIntPK, nullable=False)
    company_id: Mapped[int] = mapped_column(BigIntPK, nullable=False)
    # Baseline spend — deviation from history suggests fraud.
    avg_amount_7d: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    avg_amount_30d: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    avg_amount_90d: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # Activity volume — velocity spikes correlate with account takeover.
    tx_count_7d: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tx_count_30d: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tx_count_1h: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Merchant / category diversity — card testing shows merchant sprawl.
    unique_merchants_30d: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unique_categories_30d: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Historical fraud prevalence — prior alerts lift baseline risk.
    fraud_rate_30d: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # Temporal habits — unusual time vs history is a weak fraud signal.
    most_common_hour: Mapped[int] = mapped_column(Integer, default=12, nullable=False)
    most_common_dow: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # Dispersion for z-score features — stable users vs outlier amounts.
    std_amount_30d: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "company_id", name="uq_user_company_features"),
        Index("ix_user_features_company_computed", "company_id", "computed_at"),
        Index("ix_user_features_lookup", "user_id", "company_id"),
    )


class MerchantFeatures(Base):
    """Merchant risk profile — shared fraud across many users lifts suspicion."""

    __tablename__ = "merchant_features"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    merchant_id: Mapped[int] = mapped_column(BigIntPK, nullable=False)
    company_id: Mapped[int] = mapped_column(BigIntPK, nullable=False)
    avg_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    tx_count_30d: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fraud_rate_30d: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    unique_users_30d: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_high_risk_category: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("merchant_id", "company_id", name="uq_merchant_company_features"),
        Index("ix_merchant_features_company_computed", "company_id", "computed_at"),
    )


class VelocityFeature(Base):
    """Short-window velocity — burst spending in minutes is high-signal for fraud."""

    __tablename__ = "velocity_features"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigIntPK, nullable=False)
    company_id: Mapped[int] = mapped_column(BigIntPK, nullable=False)
    window_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    tx_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    unique_merchants: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "company_id",
            "window_minutes",
            name="uq_velocity_user_company_window",
        ),
        Index(
            "ix_velocity_lookup",
            "user_id",
            "company_id",
            "window_minutes",
            "computed_at",
        ),
    )

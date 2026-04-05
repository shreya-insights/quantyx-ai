from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import BigIntPK


class PlanName(str, PyEnum):
    STARTER = "starter"
    GROWTH = "growth"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, PyEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    TRIAL = "trial"


class BillingCycle(str, PyEnum):
    MONTHLY = "monthly"
    ANNUAL = "annual"


PLAN_LIMITS = {
    PlanName.STARTER: {
        "users": 1,
        "transactions_per_month": 10_000,
        "api_calls_per_month": 1_000,
        "features": ["core_analytics"],
    },
    PlanName.GROWTH: {
        "users": 10,
        "transactions_per_month": 500_000,
        "api_calls_per_month": 10_000,
        "features": ["core_analytics", "fraud_detection", "query_lab", "exports"],
    },
    PlanName.ENTERPRISE: {
        "users": -1,  # unlimited
        "transactions_per_month": -1,
        "api_calls_per_month": -1,
        "features": ["core_analytics", "fraud_detection", "query_lab", "exports", "custom_reports", "white_label"],
    },
}

PLAN_PRICING = {
    PlanName.STARTER: {"monthly": 0.0, "annual": 0.0},
    PlanName.GROWTH: {"monthly": 49.0, "annual": 470.0},
    PlanName.ENTERPRISE: {"monthly": 199.0, "annual": 1990.0},
}


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    plan_name: Mapped[PlanName] = mapped_column(
        Enum(PlanName, values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, values_callable=lambda x: [e.value for e in x]),
        default=SubscriptionStatus.TRIAL,
        nullable=False,
    )
    billing_cycle: Mapped[BillingCycle] = mapped_column(
        Enum(BillingCycle, values_callable=lambda x: [e.value for e in x]),
        default=BillingCycle.MONTHLY,
        nullable=False,
    )
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime)
    api_calls_limit: Mapped[int | None] = mapped_column(Integer)
    api_calls_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    transaction_limit: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="subscriptions")  # noqa: F821

    __table_args__ = (
        Index("idx_sub_company", "company_id"),
        Index("idx_sub_status", "status"),
        Index("idx_sub_company_status", "company_id", "status"),
    )

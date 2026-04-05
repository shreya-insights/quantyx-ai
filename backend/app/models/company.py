from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SubscriptionTier(str, PyEnum):
    STARTER = "starter"
    GROWTH = "growth"
    ENTERPRISE = "enterprise"


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    subscription_tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier, values_callable=lambda x: [e.value for e in x]),
        default=SubscriptionTier.STARTER,
        nullable=False,
    )
    api_key: Mapped[str | None] = mapped_column(String(255), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="company", lazy="select")  # noqa: F821
    accounts: Mapped[list["Account"]] = relationship("Account", back_populates="company", lazy="select")  # noqa: F821
    merchants: Mapped[list["Merchant"]] = relationship("Merchant", back_populates="company", lazy="select")  # noqa: F821
    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="company", lazy="select")  # noqa: F821
    fraud_alerts: Mapped[list["FraudAlert"]] = relationship("FraudAlert", back_populates="company", lazy="select")  # noqa: F821
    kpi_reports: Mapped[list["KpiReport"]] = relationship("KpiReport", back_populates="company", lazy="select")  # noqa: F821
    subscriptions: Mapped[list["Subscription"]] = relationship("Subscription", back_populates="company", lazy="select")  # noqa: F821
    saved_queries: Mapped[list["SavedQuery"]] = relationship("SavedQuery", back_populates="company", lazy="select")  # noqa: F821
    performance_metrics: Mapped[list["ModelPerformanceMetric"]] = relationship(
        "ModelPerformanceMetric", back_populates="company", lazy="select"
    )  # noqa: F821
    feature_snapshots: Mapped[list["FeatureDistributionSnapshot"]] = relationship(
        "FeatureDistributionSnapshot", back_populates="company", lazy="select"
    )  # noqa: F821

    __table_args__ = (
        Index("idx_company_slug", "slug"),
        Index("idx_company_tier", "subscription_tier"),
    )

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,  # used for model_version column
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import BigIntPK


class AlertType(str, PyEnum):
    RAPID_TRANSACTIONS = "rapid_transactions"
    UNUSUAL_AMOUNT = "unusual_amount"
    LOCATION_ANOMALY = "location_anomaly"
    NEW_DEVICE = "new_device"
    VELOCITY_BREACH = "velocity_breach"
    DUPLICATE_TRANSACTION = "duplicate_transaction"
    NIGHT_PATTERN = "night_pattern"
    ML_FRAUD_SCORE = "ml_fraud_score"


class AlertSeverity(str, PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FraudAlert(Base):
    __tablename__ = "fraud_alerts"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    transaction_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False
    )
    alert_type: Mapped[AlertType] = mapped_column(
        Enum(AlertType, values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity, values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    description: Mapped[str | None] = mapped_column(Text)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolved_by: Mapped[int | None] = mapped_column(
        BigIntPK, ForeignKey("users.id", ondelete="SET NULL")
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
    rule_metadata: Mapped[str | None] = mapped_column(Text)
    model_version: Mapped[str | None] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="fraud_alerts")  # noqa: F821
    transaction: Mapped["Transaction"] = relationship("Transaction", back_populates="fraud_alerts")  # noqa: F821

    __table_args__ = (
        Index("idx_fraud_company", "company_id"),
        Index("idx_fraud_severity", "severity"),
        Index("idx_fraud_resolved", "is_resolved"),
        Index("idx_fraud_company_resolved", "company_id", "is_resolved"),
        Index("idx_fraud_created", "created_at"),
    )

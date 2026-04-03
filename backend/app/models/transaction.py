from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    JSON,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TransactionType(str, PyEnum):
    DEBIT = "debit"
    CREDIT = "credit"
    TRANSFER = "transfer"
    REFUND = "refund"


class TransactionStatus(str, PyEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REVERSED = "reversed"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    merchant_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("merchants.id", ondelete="SET NULL")
    )
    category_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("categories.id", ondelete="SET NULL")
    )
    transaction_ref: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    transaction_type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus, values_callable=lambda x: [e.value for e in x]),
        default=TransactionStatus.PENDING,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    device_fingerprint: Mapped[str | None] = mapped_column(String(255))
    location_lat: Mapped[float | None] = mapped_column(Numeric(9, 6))
    location_lng: Mapped[float | None] = mapped_column(Numeric(9, 6))
    transaction_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="transactions")  # noqa: F821
    account: Mapped["Account"] = relationship("Account", back_populates="transactions")  # noqa: F821
    merchant: Mapped["Merchant | None"] = relationship("Merchant", back_populates="transactions")  # noqa: F821
    category: Mapped["Category | None"] = relationship("Category", back_populates="transactions")  # noqa: F821
    fraud_alerts: Mapped[list["FraudAlert"]] = relationship("FraudAlert", back_populates="transaction", lazy="select")  # noqa: F821

    __table_args__ = (
        # Composite covering index — most analytics queries filter by company + date
        Index("idx_tx_company_date", "company_id", "transaction_date"),
        Index("idx_tx_account_date", "account_id", "transaction_date"),
        Index("idx_tx_status", "status"),
        Index("idx_tx_company_status_type", "company_id", "status", "transaction_type"),
        Index("idx_tx_merchant", "merchant_id"),
        Index("idx_tx_date", "transaction_date"),
    )

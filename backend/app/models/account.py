from datetime import date, datetime
from enum import Enum as PyEnum

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Enum, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AccountType(str, PyEnum):
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT = "credit"
    INVESTMENT = "investment"


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL")
    )
    account_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    account_type: Mapped[AccountType] = mapped_column(
        Enum(AccountType, values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    balance: Mapped[float] = mapped_column(Numeric(18, 2), default=0.00, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    opened_at: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="accounts")  # noqa: F821
    user: Mapped["User | None"] = relationship("User", back_populates="accounts")  # noqa: F821
    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="account", lazy="select")  # noqa: F821

    __table_args__ = (
        Index("idx_account_company", "company_id"),
        Index("idx_account_user", "user_id"),
        Index("idx_account_type", "account_type"),
    )

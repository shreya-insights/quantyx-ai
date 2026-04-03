from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Merchant(Base):
    __tablename__ = "merchants"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category_code: Mapped[str | None] = mapped_column(String(10))
    country: Mapped[str | None] = mapped_column(String(3))
    city: Mapped[str | None] = mapped_column(String(100))
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="merchants")  # noqa: F821
    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="merchant", lazy="select")  # noqa: F821

    __table_args__ = (
        Index("idx_merchant_company", "company_id"),
        Index("idx_merchant_category", "category_code"),
        Index("idx_merchant_flagged", "is_flagged"),
    )

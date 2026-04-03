from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserRole(str, PyEnum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, values_callable=lambda x: [e.value for e in x]),
        default=UserRole.VIEWER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="users")  # noqa: F821
    accounts: Mapped[list["Account"]] = relationship("Account", back_populates="user", lazy="select")  # noqa: F821
    saved_queries: Mapped[list["SavedQuery"]] = relationship("SavedQuery", back_populates="user", lazy="select")  # noqa: F821

    __table_args__ = (
        Index("idx_user_company", "company_id"),
        Index("idx_user_email", "email"),
        Index("idx_user_role", "role"),
    )

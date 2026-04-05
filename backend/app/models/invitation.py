"""Invitation model — token-based user invitations.

Security design:
    token_hash stores SHA-256(raw_token) only — raw token is never persisted.
    expires_at is enforced at both application and query layer (defense in depth).
    invited_by_id + invited_by_email provide a full audit trail.
    company_name is snapshotted so the email template renders correctly even if
    the company is renamed after the invite was sent.
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import BigInteger, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="viewer")

    # SHA-256 hex digest of the raw URL-safe token — never store the raw token
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    # Audit trail: who sent this invite
    invited_by_id: Mapped[int] = mapped_column(Integer, nullable=False)
    invited_by_email: Mapped[str] = mapped_column(String(255), nullable=False)

    # Snapshot for email template — survives company renames
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)

    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    email_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resend_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    __table_args__ = (
        # Fast lookup: "does this email already have a pending invite for this company?"
        Index("ix_invitation_email_company", "email", "company_id"),
        # Fast expiry cleanup: WHERE status='pending' AND expires_at < NOW()
        Index("ix_invitation_status_expires", "status", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<Invitation id={self.id} email={self.email!r} status={self.status!r}>"

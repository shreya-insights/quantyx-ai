"""
AuditLog — Append-Only, Tamper-Evident Event Log.

Append-only is enforced at two independent layers:
  Layer 1 — SQLAlchemy event listeners (before_update / before_delete)
  Layer 2 — MySQL database triggers installed by migration 0007

Design decisions:
  - company_id / user_id are plain integers, NOT foreign keys.
    Records must survive company/user deletion (GDPR right-to-erasure + forensic integrity).
  - user_email is a point-in-time snapshot, not a join to the users table.
  - created_at uses server_default=func.now() — client cannot fake timestamps.
  - ip_address is PII. TODO(KMS): encrypt at rest before storing in production.
"""

from datetime import datetime

import structlog
from sqlalchemy import BigInteger, DateTime, Index, Integer, JSON, String
from sqlalchemy import event as sa_event
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base

logger = structlog.get_logger(__name__)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_email: Mapped[str | None] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(64))
    ip_address: Mapped[str | None] = mapped_column(String(64))  # TODO(KMS): encrypt in prod
    user_agent: Mapped[str | None] = mapped_column(String(512))
    request_path: Mapped[str] = mapped_column(String(512), nullable=False)
    request_method: Mapped[str] = mapped_column(String(8), nullable=False)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )

    __table_args__ = (
        Index("ix_audit_company_action_date", "company_id", "action", "created_at"),
        Index("ix_audit_user_date", "user_id", "created_at"),
    )


@sa_event.listens_for(AuditLog, "before_update")
def _prevent_audit_update(mapper, connection, target) -> None:  # type: ignore[type-arg]
    """Layer 1 append-only guard: blocks any ORM-level UPDATE on AuditLog rows."""
    raise RuntimeError(
        "AuditLog records are immutable. Append-only policy violation."
    )


@sa_event.listens_for(AuditLog, "before_delete")
def _prevent_audit_delete(mapper, connection, target) -> None:  # type: ignore[type-arg]
    """Layer 1 append-only guard: blocks any ORM-level DELETE on AuditLog rows."""
    raise RuntimeError(
        "AuditLog records cannot be deleted. Retention policy violation."
    )

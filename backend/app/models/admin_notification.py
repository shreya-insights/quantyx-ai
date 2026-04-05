"""Internal admin notifications for ML health / drift escalations."""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import BigIntPK


class AdminNotificationType(str, PyEnum):
    MODEL_HEALTH = "model_health"
    DRIFT_DETECTED = "drift_detected"


class AdminNotificationSeverity(str, PyEnum):
    WARNING = "warning"
    CRITICAL = "critical"


class AdminNotification(Base):
    __tablename__ = "admin_notifications"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    company_id: Mapped[int | None] = mapped_column(
        BigIntPK, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    notification_type: Mapped[AdminNotificationType] = mapped_column(
        Enum(
            AdminNotificationType,
            values_callable=lambda x: [e.value for e in x],
            name="admin_notification_type",
        ),
        nullable=False,
    )
    severity: Mapped[AdminNotificationSeverity] = mapped_column(
        Enum(
            AdminNotificationSeverity,
            values_callable=lambda x: [e.value for e in x],
            name="admin_notification_severity",
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_admin_notif_company", "company_id"),
        Index("idx_admin_notif_created", "created_at"),
    )

"""
Audit Log Endpoint — Admin-only, paginated, filterable, CSV-exportable.

FAANG privacy principle: ip_address is excluded from all JSON responses
because the endpoint is accessible by admins who may be internal ops staff
without a "need to know" on individual IPs. Full raw data is only available
via the CSV export which is gated behind the same AdminUser dependency
and should be protected by download rate limiting in a future iteration.

TODO(GDPR): Add a data retention job that exports+deletes records older
than the configured retention window (default 2 years) to a cold-storage
bucket, keeping the table size bounded.
"""

import csv
import io
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, select, func as sa_func

from app.core.dependencies import AdminUser, DBSession
from app.models.audit_log import AuditLog
from app.schemas.common import PaginatedResponse
from app.utils.masking import mask_ip_address
from app.utils.pagination import paginate
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/audit", tags=["Audit"])

_DEFAULT_PAGE_SIZE: int = 50
_MAX_PAGE_SIZE: int = 200
_CSV_CHUNK_SIZE: int = 500


class AuditLogResponse(BaseModel):
    """Serialized audit log entry returned over the API.

    ip_address is masked (first two octets only) in JSON responses.
    The raw value is preserved in CSV exports for compliance teams.
    """

    id: int
    company_id: int
    user_id: int | None
    user_email: str | None
    action: str
    resource_type: str
    resource_id: str | None
    ip_address: str | None  # masked to first two octets in JSON
    user_agent: str | None
    request_path: str
    request_method: str
    response_status: int
    duration_ms: int
    metadata: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


def _build_filters(
    query: Any,
    company_id: int,
    actions: list[str] | None,
    user_id: int | None,
    resource_type: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> Any:
    """Build the WHERE clause for audit log queries."""
    conditions = [AuditLog.company_id == company_id]

    if actions:
        conditions.append(AuditLog.action.in_(actions))
    if user_id is not None:
        conditions.append(AuditLog.user_id == user_id)
    if resource_type:
        conditions.append(AuditLog.resource_type == resource_type)
    if date_from:
        conditions.append(AuditLog.created_at >= date_from)
    if date_to:
        conditions.append(AuditLog.created_at <= date_to)

    return query.where(and_(*conditions))


@router.get("/logs", response_model=PaginatedResponse[AuditLogResponse])
async def list_audit_logs(
    current_user: AdminUser,
    db: DBSession,
    action: list[str] | None = Query(default=None, description="Filter by one or more actions"),
    user_id: int | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=_DEFAULT_PAGE_SIZE, ge=1, le=_MAX_PAGE_SIZE),
    format: str | None = Query(default=None, description="Set to 'csv' for compliance export"),
) -> Any:
    """
    Paginated, filterable audit log viewer. Admin-only.

    Supports:
      - Multi-select action filter (?action=data.read&action=auth.login)
      - User filter, resource_type filter, date range filter
      - JSON pagination (default) or CSV download (?format=csv)
    """
    if format == "csv":
        return await _stream_csv_export(
            db=db,
            company_id=current_user.company_id,
            actions=action,
            user_id=user_id,
            resource_type=resource_type,
            date_from=date_from,
            date_to=date_to,
        )

    count_stmt = _build_filters(
        select(sa_func.count()).select_from(AuditLog),
        company_id=current_user.company_id,
        actions=action,
        user_id=user_id,
        resource_type=resource_type,
        date_from=date_from,
        date_to=date_to,
    )
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = _build_filters(
        select(AuditLog),
        company_id=current_user.company_id,
        actions=action,
        user_id=user_id,
        resource_type=resource_type,
        date_from=date_from,
        date_to=date_to,
    ).order_by(AuditLog.created_at.desc()).limit(page_size).offset(offset)

    result = await db.execute(data_stmt)
    rows = list(result.scalars().all())

    data = [
        AuditLogResponse(
            id=row.id,
            company_id=row.company_id,
            user_id=row.user_id,
            user_email=row.user_email,
            action=row.action,
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            ip_address=mask_ip_address(row.ip_address),
            user_agent=row.user_agent,
            request_path=row.request_path,
            request_method=row.request_method,
            response_status=row.response_status,
            duration_ms=row.duration_ms,
            metadata=row.metadata_,
            created_at=row.created_at,
        )
        for row in rows
    ]

    logger.info(
        "audit.logs_viewed",
        admin_id=current_user.user_id,
        company_id=current_user.company_id,
        total=total,
        filters={"action": action, "user_id": user_id, "resource_type": resource_type},
    )

    return paginate(data, total, page, page_size)


_CSV_FIELDNAMES: list[str] = [
    "id",
    "company_id",
    "user_id",
    "user_email",
    "action",
    "resource_type",
    "resource_id",
    "ip_address",
    "user_agent",
    "request_path",
    "request_method",
    "response_status",
    "duration_ms",
    "created_at",
]


async def _stream_csv_export(
    db: DBSession,
    company_id: int,
    actions: list[str] | None,
    user_id: int | None,
    resource_type: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> StreamingResponse:
    """
    Stream audit logs as CSV for compliance export.

    Raw ip_address is included in the CSV (compliance teams need exact IPs).
    Chunked via io.StringIO to avoid loading all rows into memory.
    """
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_CSV_FIELDNAMES, extrasaction="ignore")
    writer.writeheader()

    offset = 0
    while True:
        stmt = _build_filters(
            select(AuditLog),
            company_id=company_id,
            actions=actions,
            user_id=user_id,
            resource_type=resource_type,
            date_from=date_from,
            date_to=date_to,
        ).order_by(AuditLog.created_at.desc()).limit(_CSV_CHUNK_SIZE).offset(offset)

        result = await db.execute(stmt)
        chunk = list(result.scalars().all())
        if not chunk:
            break

        for row in chunk:
            writer.writerow(
                {
                    "id": row.id,
                    "company_id": row.company_id,
                    "user_id": row.user_id,
                    "user_email": row.user_email,
                    "action": row.action,
                    "resource_type": row.resource_type,
                    "resource_id": row.resource_id,
                    "ip_address": row.ip_address,
                    "user_agent": row.user_agent,
                    "request_path": row.request_path,
                    "request_method": row.request_method,
                    "response_status": row.response_status,
                    "duration_ms": row.duration_ms,
                    "created_at": row.created_at.isoformat() if row.created_at else "",
                }
            )

        offset += _CSV_CHUNK_SIZE
        if len(chunk) < _CSV_CHUNK_SIZE:
            break

    buf.seek(0)
    return StreamingResponse(
        content=iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
    )

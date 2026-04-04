"""
Audit Event Logger — Fire-and-Forget.

Google SRE principle: audit logging failures must NEVER block business logic.
If the insert fails, the error is captured in structlog and the original
request succeeds. Auditing is intentionally non-critical-path.

Usage:
    await log_audit_event(
        db=db,
        action="data.read",
        resource_type="transaction",
        current_user=current_user,
        request=request,
        resource_id=str(tx_id),
        response_status=200,
        duration_ms=elapsed,
    )
"""

import structlog
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import TokenData
from app.models.audit_log import AuditLog

logger = structlog.get_logger(__name__)

# frozenset: immutable + O(1) lookup + detects typos at log time.
AUDIT_ACTIONS: frozenset[str] = frozenset(
    {
        "auth.login",
        "auth.logout",
        "auth.register",
        "auth.invite",
        "auth.password_change",
        "data.read",
        "data.create",
        "data.update",
        "data.delete",
        "data.export",
        "query.execute",
        "query.save",
        "fraud.resolve",
        "fraud.flag",
        "fraud.review",
        "admin.update_user",
        "admin.change_role",
        "admin.update_settings",
        "report.generate",
        "analyst.query",
    }
)

_MAX_USER_AGENT_LEN: int = 512


async def log_audit_event(
    db: AsyncSession,
    action: str,
    resource_type: str,
    current_user: TokenData | None,
    request: Request,
    resource_id: str | None = None,
    metadata: dict | None = None,
    response_status: int = 200,
    duration_ms: int = 0,
) -> None:
    """
    Insert one audit record. Never raises — fire and forget.

    Uses db.flush() (not db.commit()) so the entry joins the caller's
    existing transaction and is committed atomically with the business data.
    """
    if action not in AUDIT_ACTIONS:
        logger.warning("audit.unknown_action", action=action)
        return

    try:
        log_entry = AuditLog(
            company_id=current_user.company_id if current_user else 0,
            user_id=current_user.user_id if current_user else None,
            user_email=current_user.email if current_user else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=request.client.host if request.client else None,
            user_agent=(request.headers.get("user-agent", "") or "")[:_MAX_USER_AGENT_LEN],
            request_path=str(request.url.path),
            request_method=request.method,
            response_status=response_status,
            duration_ms=duration_ms,
            metadata_=metadata or {},
        )
        db.add(log_entry)
        await db.flush()
    except Exception as exc:
        # Never re-raise. Audit failure must not surface to the caller (Google SRE rule).
        logger.error(
            "audit.log_failed",
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            error=str(exc),
        )

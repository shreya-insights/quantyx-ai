"""Invitation endpoints — token-based user invitations.

All admin endpoints require AdminUser (JWT role=admin, company_id from token).
Public endpoints (validate, accept) are rate-limited by the global IP limiter.

Resend rate limit: Redis key  inv:resend:{invitation_id}  TTL=3600s.
If Redis is unavailable, resend is allowed (fail-open per FAANG pattern).
"""

import time

import structlog
from fastapi import APIRouter, Query, Request
from sqlalchemy import select

from app.core.config import settings
from app.core.dependencies import AdminUser, DBSession
from app.core.exceptions import ConflictError, NotFoundError, QuantyxException, RateLimitError
from app.core.security import create_token_pair, hash_password
from app.models.company import Company
from app.models.user import User, UserRole
from app.repositories.user_repo import UserRepository
from app.schemas.auth import TokenResponse
from app.schemas.invitation import (
    AcceptInviteRequest,
    BulkInviteRequest,
    BulkInviteResponse,
    BulkInviteResult,
    InvitationResponse,
    SendInviteRequest,
    ValidateTokenResponse,
)
from app.services.invitation_service import InvitationService
from app.utils.audit import log_audit_event
from app.utils.cache import get_redis_client

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/invitations", tags=["Invitations"])

# How many minutes must pass before the same email can receive another invite
_INVITE_COOLDOWN_MINUTES: int = 5
# Redis TTL for resend rate limit (1 resend per invitation per hour)
_RESEND_RATE_LIMIT_TTL: int = 3600


async def _check_resend_rate_limit(invitation_id: int) -> None:
    """Raise RateLimitError if this invitation was resent within the last hour.

    Fails open if Redis is unavailable — resend is allowed rather than blocked.
    """
    key = f"inv:resend:{invitation_id}"
    try:
        redis = await get_redis_client()
        existing = await redis.get(key)
        if existing:
            ttl = await redis.ttl(key)
            raise RateLimitError(
                "This invitation was already resent recently. Please wait before sending again.",
                retry_after=max(1, ttl),
                limit=1,
                remaining=0,
                reset_ts=int(time.time()) + max(1, ttl),
            )
        await redis.setex(key, _RESEND_RATE_LIMIT_TTL, "1")
    except RateLimitError:
        raise
    except Exception as exc:
        logger.warning("invitation.resend_rate_limit_redis_error", error=str(exc))


# ─── POST /invitations/send ────────────────────────────────────────────────────


@router.post("/send", response_model=InvitationResponse, status_code=201)
async def send_invite(
    request: Request,
    body: SendInviteRequest,
    current_user: AdminUser,
    db: DBSession,
) -> InvitationResponse:
    """Send a single invitation email. Admin only.

    Rejects if the email is already a registered user in this company.
    Rate-limits repeat invites to the same address (5-minute cooldown).
    """
    svc = InvitationService(db)
    user_repo = UserRepository(db)

    existing_user = await user_repo.get_by_email(body.email)
    if existing_user and existing_user.company_id == current_user.company_id:
        raise ConflictError(f"{body.email} is already a member of this company")

    if await svc.check_recent_invite(body.email, current_user.company_id, _INVITE_COOLDOWN_MINUTES):
        raise QuantyxException(
            status_code=429,
            detail=f"An invitation was already sent to {body.email} in the last {_INVITE_COOLDOWN_MINUTES} minutes",
            error_code="INVITE_COOLDOWN",
        )

    company_result = await db.execute(
        select(Company).where(Company.id == current_user.company_id)
    )
    company = company_result.scalar_one_or_none()
    company_name = company.name if company else "Your Company"

    invitation, raw_token = await svc.create_invitation(
        email=body.email,
        role=body.role,
        company_id=current_user.company_id,
        invited_by=current_user,
        company_name=company_name,
    )
    await db.commit()

    # Enqueue async email delivery — HTTP returns before SMTP handshake
    from app.worker.tasks.email_tasks import send_invitation_task

    send_invitation_task.delay(
        invitation_id=invitation.id,
        to_email=invitation.email,
        inviter_name=current_user.email,
        company_name=company_name,
        role=body.role,
        raw_token=raw_token,
    )

    await log_audit_event(
        db=db,
        action="auth.invite",
        resource_type="invitation",
        current_user=current_user,
        request=request,
        resource_id=str(invitation.id),
    )

    logger.info(
        "invitation.send_queued",
        invitation_id=invitation.id,
        email=body.email,
        company_id=current_user.company_id,
    )

    return InvitationResponse.model_validate(invitation)


# ─── POST /invitations/send-bulk ──────────────────────────────────────────────


@router.post("/send-bulk", response_model=BulkInviteResponse, status_code=201)
async def send_bulk_invites(
    request: Request,
    body: BulkInviteRequest,
    current_user: AdminUser,
    db: DBSession,
) -> BulkInviteResponse:
    """Send up to 10 invitations in a single request. Admin only.

    Partial success is allowed — one failed invite does not block the others.
    Each result carries its own status and error message.
    """
    svc = InvitationService(db)
    user_repo = UserRepository(db)

    company_result = await db.execute(
        select(Company).where(Company.id == current_user.company_id)
    )
    company = company_result.scalar_one_or_none()
    company_name = company.name if company else "Your Company"

    results: list[BulkInviteResult] = []

    from app.worker.tasks.email_tasks import send_invitation_task

    for invite in body.invites:
        try:
            existing_user = await user_repo.get_by_email(invite.email)
            if existing_user and existing_user.company_id == current_user.company_id:
                results.append(BulkInviteResult(
                    email=invite.email,
                    status="error",
                    error="Already a member of this company",
                ))
                continue

            if await svc.check_recent_invite(
                invite.email, current_user.company_id, _INVITE_COOLDOWN_MINUTES
            ):
                results.append(BulkInviteResult(
                    email=invite.email,
                    status="error",
                    error=f"Invite cooldown active — sent within last {_INVITE_COOLDOWN_MINUTES} minutes",
                ))
                continue

            invitation, raw_token = await svc.create_invitation(
                email=invite.email,
                role=invite.role,
                company_id=current_user.company_id,
                invited_by=current_user,
                company_name=company_name,
            )
            await db.flush()

            send_invitation_task.delay(
                invitation_id=invitation.id,
                to_email=invitation.email,
                inviter_name=current_user.email,
                company_name=company_name,
                role=invite.role,
                raw_token=raw_token,
            )

            results.append(BulkInviteResult(
                email=invite.email,
                status="queued",
                invitation_id=invitation.id,
            ))

        except Exception as exc:
            logger.error(
                "invitation.bulk_send_item_failed",
                email=invite.email,
                error=str(exc),
            )
            results.append(BulkInviteResult(
                email=invite.email,
                status="error",
                error="Internal error — please retry this address",
            ))

    await db.commit()

    await log_audit_event(
        db=db,
        action="auth.invite",
        resource_type="invitation",
        current_user=current_user,
        request=request,
        metadata={"count": len(body.invites)},
    )

    sent = sum(1 for r in results if r.status == "queued")
    errors = sum(1 for r in results if r.status == "error")

    return BulkInviteResponse(results=results, sent_count=sent, error_count=errors)


# ─── GET /invitations ─────────────────────────────────────────────────────────


@router.get("", response_model=list[InvitationResponse])
async def list_invitations(
    current_user: AdminUser,
    db: DBSession,
    status: str | None = Query(default=None, pattern=r"^(pending|accepted|expired|revoked)$"),
) -> list[InvitationResponse]:
    """List all invitations for this company. Admin only. Auto-expires stale entries."""
    svc = InvitationService(db)
    invitations = await svc.list_invitations(current_user.company_id, status_filter=status)
    await db.commit()
    return [InvitationResponse.model_validate(inv) for inv in invitations]


# ─── POST /invitations/{id}/resend ────────────────────────────────────────────


@router.post("/{invitation_id}/resend", response_model=InvitationResponse)
async def resend_invitation(
    request: Request,
    invitation_id: int,
    current_user: AdminUser,
    db: DBSession,
) -> InvitationResponse:
    """Revoke old token and send a fresh invite. Rate-limited to 1 resend per hour."""
    await _check_resend_rate_limit(invitation_id)

    svc = InvitationService(db)
    invitation, raw_token = await svc.resend_invitation(invitation_id, current_user.company_id)
    await db.commit()

    from app.worker.tasks.email_tasks import send_invitation_task

    send_invitation_task.delay(
        invitation_id=invitation.id,
        to_email=invitation.email,
        inviter_name=current_user.email,
        company_name=invitation.company_name,
        role=invitation.role,
        raw_token=raw_token,
    )

    logger.info(
        "invitation.resend_queued",
        invitation_id=invitation.id,
        email=invitation.email,
    )

    return InvitationResponse.model_validate(invitation)


# ─── DELETE /invitations/{id} ────────────────────────────────────────────────


@router.delete("/{invitation_id}", status_code=204)
async def revoke_invitation(
    request: Request,
    invitation_id: int,
    current_user: AdminUser,
    db: DBSession,
) -> None:
    """Revoke an invitation. Admin only. Accepted invitations cannot be revoked."""
    svc = InvitationService(db)
    await svc.revoke_invitation(invitation_id, current_user.company_id)
    await db.commit()

    logger.info(
        "invitation.revoked_via_api",
        invitation_id=invitation_id,
        revoked_by=current_user.email,
    )


# ─── GET /invitations/validate ────────────────────────────────────────────────


@router.get("/validate", response_model=ValidateTokenResponse)
async def validate_token(
    db: DBSession,
    token: str = Query(..., min_length=10),
) -> ValidateTokenResponse:
    """Check if an invite token is valid. Public endpoint, rate-limited by IP.

    Returns minimal info for the accept-invite page to pre-fill the form.
    Never returns token_hash or any internal fields.
    """
    svc = InvitationService(db)
    invitation = await svc.validate_token(token)

    if not invitation:
        return ValidateTokenResponse(valid=False)

    return ValidateTokenResponse(
        valid=True,
        email=invitation.email,
        company_name=invitation.company_name,
        role=invitation.role,
        expires_at=invitation.expires_at,
    )


# ─── POST /invitations/accept ────────────────────────────────────────────────


@router.post("/accept", response_model=TokenResponse, status_code=201)
async def accept_invitation(
    request: Request,
    body: AcceptInviteRequest,
    db: DBSession,
) -> TokenResponse:
    """Register a new user from a valid invite token. Public endpoint.

    Validates token → creates user with role from invite → marks accepted → returns JWT pair.
    """
    svc = InvitationService(db)
    user_repo = UserRepository(db)

    invitation = await svc.validate_token(body.token)
    if not invitation:
        raise QuantyxException(
            status_code=400,
            detail="Invitation is invalid, expired, or already used",
            error_code="INVALID_INVITE_TOKEN",
        )

    existing = await user_repo.get_by_email(invitation.email)
    if existing:
        raise ConflictError(f"An account with {invitation.email} already exists. Please log in.")

    new_user = User(
        company_id=invitation.company_id,
        email=invitation.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=UserRole(invitation.role),
        is_active=True,
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)

    await svc.accept_invitation(invitation, new_user.id)
    await db.commit()

    tokens = create_token_pair(
        new_user.id, new_user.company_id, new_user.role.value, new_user.email
    )

    await log_audit_event(
        db=db,
        action="auth.register",
        resource_type="user",
        current_user=None,
        request=request,
        resource_id=str(new_user.id),
        metadata={"via": "invitation", "invitation_id": invitation.id},
    )

    logger.info(
        "invitation.user_registered",
        user_id=new_user.id,
        invitation_id=invitation.id,
        company_id=invitation.company_id,
    )

    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
    )

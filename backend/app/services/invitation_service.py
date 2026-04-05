"""Invitation Service — Secure token management for user invitations.

Token security pattern (same as GitHub password reset / Stripe API keys):
    1. Generate: secrets.token_urlsafe(32) → 256-bit URL-safe raw token
    2. Hash:     hashlib.sha256(raw_token.encode()).hexdigest() → stored in DB
    3. Send:     raw_token embedded in email link — never stored, never logged
    4. Verify:   hash the incoming token, look up hash in DB
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import TokenData
from app.core.exceptions import ConflictError, NotFoundError, QuantyxException
from app.models.invitation import Invitation

logger = structlog.get_logger(__name__)

RESEND_COOLDOWN_SECONDS: int = 3600  # 1 hour between resends per invitation


def _hash_token(raw_token: str) -> str:
    """Return SHA-256 hex digest of a raw token. Never log the input."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


def _new_raw_token() -> str:
    """Generate a 256-bit cryptographically secure URL-safe token."""
    return secrets.token_urlsafe(32)


class InvitationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_invitation(
        self,
        email: str,
        role: str,
        company_id: int,
        invited_by: TokenData,
        company_name: str,
    ) -> tuple[Invitation, str]:
        """Create a new invitation. Revokes any existing pending invite for the same email+company.

        Returns (Invitation ORM object, raw_token_for_email). The raw token is returned
        exactly once — the caller must enqueue the email task immediately. It is never
        persisted to the database.
        """
        normalised_email = email.lower().strip()

        # Revoke any existing pending invite — prevents token accumulation
        await self.session.execute(
            update(Invitation)
            .where(
                Invitation.email == normalised_email,
                Invitation.company_id == company_id,
                Invitation.status == "pending",
            )
            .values(status="revoked")
        )

        raw_token = _new_raw_token()
        token_hash = _hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=settings.INVITE_TOKEN_EXPIRE_HOURS
        )

        invitation = Invitation(
            company_id=company_id,
            email=normalised_email,
            role=role,
            token_hash=token_hash,
            status="pending",
            invited_by_id=invited_by.user_id,
            invited_by_email=invited_by.email,
            company_name=company_name,
            expires_at=expires_at,
        )
        self.session.add(invitation)
        await self.session.flush()
        await self.session.refresh(invitation)

        logger.info(
            "invitation.created",
            invitation_id=invitation.id,
            email=normalised_email,
            company_id=company_id,
            role=role,
        )
        return invitation, raw_token

    async def validate_token(self, raw_token: str) -> Invitation | None:
        """Validate an invite token. Returns the Invitation if valid, None otherwise.

        SECURITY: hashes the incoming token before lookup — raw tokens are never compared directly.
        """
        token_hash = _hash_token(raw_token)
        result = await self.session.execute(
            select(Invitation).where(
                Invitation.token_hash == token_hash,
                Invitation.status == "pending",
                Invitation.expires_at > datetime.now(timezone.utc),
            )
        )
        return result.scalar_one_or_none()

    async def accept_invitation(
        self, invitation: Invitation, new_user_id: int
    ) -> None:
        """Mark an invitation as accepted after the new user is created."""
        invitation.status = "accepted"
        invitation.accepted_at = datetime.now(timezone.utc)
        self.session.add(invitation)

        logger.info(
            "invitation.accepted",
            invitation_id=invitation.id,
            new_user_id=new_user_id,
            company_id=invitation.company_id,
        )

    async def resend_invitation(
        self, invitation_id: int, company_id: int
    ) -> tuple[Invitation, str]:
        """Revoke the old token and issue a fresh one. Returns (invitation, new_raw_token).

        Tenant-isolation: company_id from JWT is verified against the stored invitation.
        """
        invitation = await self.session.get(Invitation, invitation_id)
        if not invitation or invitation.company_id != company_id:
            raise NotFoundError("Invitation")

        if invitation.status == "accepted":
            raise QuantyxException(
                status_code=409,
                detail="Invitation already accepted — cannot resend",
                error_code="INVITATION_ALREADY_ACCEPTED",
            )

        raw_token = _new_raw_token()
        invitation.token_hash = _hash_token(raw_token)
        invitation.expires_at = datetime.now(timezone.utc) + timedelta(
            hours=settings.INVITE_TOKEN_EXPIRE_HOURS
        )
        invitation.status = "pending"
        invitation.resend_count += 1
        self.session.add(invitation)
        await self.session.flush()

        logger.info(
            "invitation.resent",
            invitation_id=invitation.id,
            resend_count=invitation.resend_count,
        )
        return invitation, raw_token

    async def revoke_invitation(self, invitation_id: int, company_id: int) -> None:
        """Set invitation status to revoked. Tenant-isolated."""
        invitation = await self.session.get(Invitation, invitation_id)
        if not invitation or invitation.company_id != company_id:
            raise NotFoundError("Invitation")

        if invitation.status == "accepted":
            raise QuantyxException(
                status_code=409,
                detail="Cannot revoke an already-accepted invitation",
                error_code="INVITATION_ALREADY_ACCEPTED",
            )

        invitation.status = "revoked"
        self.session.add(invitation)

        logger.info(
            "invitation.revoked",
            invitation_id=invitation.id,
            company_id=company_id,
        )

    async def list_invitations(
        self, company_id: int, status_filter: str | None = None
    ) -> list[Invitation]:
        """List all invitations for a company. Auto-expires stale pending ones."""
        # Mark expired pending invitations before returning results
        await self.session.execute(
            update(Invitation)
            .where(
                Invitation.company_id == company_id,
                Invitation.status == "pending",
                Invitation.expires_at <= datetime.now(timezone.utc),
            )
            .values(status="expired")
        )

        query = select(Invitation).where(Invitation.company_id == company_id)
        if status_filter:
            query = query.where(Invitation.status == status_filter)
        query = query.order_by(Invitation.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def mark_email_sent(self, invitation_id: int) -> None:
        """Record the timestamp when the invitation email was delivered."""
        await self.session.execute(
            update(Invitation)
            .where(Invitation.id == invitation_id)
            .values(email_sent_at=datetime.now(timezone.utc))
        )

    async def check_recent_invite(
        self, email: str, company_id: int, cooldown_minutes: int = 5
    ) -> bool:
        """Return True if a pending invite was sent to this email in the last N minutes."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=cooldown_minutes)
        result = await self.session.execute(
            select(Invitation).where(
                Invitation.email == email.lower().strip(),
                Invitation.company_id == company_id,
                Invitation.status == "pending",
                Invitation.created_at >= cutoff,
            )
        )
        return result.scalar_one_or_none() is not None

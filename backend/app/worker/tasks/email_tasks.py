"""Email Celery tasks — non-blocking async SMTP delivery.

FAANG principle: HTTP responses must return immediately (~5ms).
SMTP handshakes take 1–5 seconds — always delegate to background workers.

Security note on raw_token in task args:
    The raw_token is visible in the Celery result backend (Redis).
    result_expires=86400 (24h) is already configured in celery_app.py.
    In production with strict compliance requirements, consider encrypting
    task args or reducing result_expires to 300 seconds (5 minutes).
"""

import asyncio
import logging

import structlog
from celery import shared_task
from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.invitation import Invitation

logger = structlog.get_logger(__name__)

# Max exponential back-off delay: 60s × 2^(retry - 1)  →  60 / 120 / 240 seconds
_BASE_RETRY_DELAY_SECONDS: int = 60
_MAX_RETRIES: int = 3


@shared_task(
    bind=True,
    max_retries=_MAX_RETRIES,
    default_retry_delay=_BASE_RETRY_DELAY_SECONDS,
    name="quantyx.email.send_invitation",
    queue="email",
    acks_late=True,
)
def send_invitation_task(
    self,
    invitation_id: int,
    to_email: str,
    inviter_name: str,
    company_name: str,
    role: str,
    raw_token: str,  # SECURITY: never log this value — only used to build invite URL
) -> dict:
    """Send invitation email via SMTP. Retries up to 3× on transient SMTP failures.

    Uses exponential back-off: 60s → 120s → 240s between retries.
    Idempotency: if email_sent_at is already set, the task exits early to avoid
    duplicate emails on Celery at-least-once redelivery.
    """
    # Idempotency guard: check if already sent before running SMTP
    sync_engine = create_engine(settings.SYNC_DATABASE_URL)
    SyncSession = sessionmaker(sync_engine)

    with SyncSession() as db:
        row = db.get(Invitation, invitation_id)
        if row and row.email_sent_at is not None:
            logger.info(
                "email.invitation_task_skipped_already_sent",
                invitation_id=invitation_id,
            )
            return {"status": "already_sent", "to": to_email}

    # Run the async send in a fresh event loop (Celery workers are sync by default)
    loop = asyncio.new_event_loop()
    try:
        from app.services.email_service import send_invitation_email

        success = loop.run_until_complete(
            send_invitation_email(
                to_email, inviter_name, company_name, role, raw_token, invitation_id
            )
        )
    except Exception as exc:
        logger.error(
            "email.invitation_task_exception",
            invitation_id=invitation_id,
            to=to_email,
            error=str(exc),
        )
        raise self.retry(
            exc=exc,
            countdown=_BASE_RETRY_DELAY_SECONDS * (2 ** self.request.retries),
        )
    finally:
        loop.close()

    if not success:
        exc = Exception("SMTP send returned failure")
        raise self.retry(
            exc=exc,
            countdown=_BASE_RETRY_DELAY_SECONDS * (2 ** self.request.retries),
        )

    # Record delivery timestamp in DB
    with SyncSession() as db:
        from datetime import datetime, timezone

        db.execute(
            update(Invitation)
            .where(Invitation.id == invitation_id)
            .values(email_sent_at=datetime.now(timezone.utc))
        )
        db.commit()

    sync_engine.dispose()

    logger.info(
        "email.invitation_delivered",
        invitation_id=invitation_id,
        to=to_email,
    )
    return {"status": "sent", "to": to_email}

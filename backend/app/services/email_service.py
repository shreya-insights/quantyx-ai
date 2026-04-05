"""Email Service — FastAPI-Mail + Jinja2 HTML templates.

Design principles:
    - Never build HTML with string concatenation (XSS risk)
    - Jinja2 autoescape=True on all HTML templates
    - Plain text alternative included for screen readers and Outlook text-only mode
    - This module is a thin SMTP wrapper — business logic lives in InvitationService
    - Never called directly from HTTP handlers; always via Celery (non-blocking)
"""

from datetime import datetime
from pathlib import Path

import structlog
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Resolve template directory relative to this file so it works regardless of cwd
_TEMPLATE_DIR: Path = Path(__file__).parent.parent / "templates" / "emails"


def get_mail_config() -> ConnectionConfig:
    """Build FastAPI-Mail connection config from application settings."""
    return ConnectionConfig(
        MAIL_USERNAME=settings.MAIL_USERNAME,
        MAIL_PASSWORD=settings.MAIL_PASSWORD,
        MAIL_FROM=settings.MAIL_FROM,
        MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
        MAIL_PORT=settings.MAIL_PORT,
        MAIL_SERVER=settings.MAIL_SERVER,
        MAIL_STARTTLS=settings.MAIL_STARTTLS,
        MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
        TEMPLATE_FOLDER=_TEMPLATE_DIR,
    )


def _get_jinja_env() -> Environment:
    """Return a Jinja2 environment with autoescape enabled for HTML templates."""
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "htm"]),
    )


def render_email_template(template_name: str, context: dict) -> str:
    """Render a Jinja2 template. Autoescape prevents XSS in all rendered values."""
    env = _get_jinja_env()
    template = env.get_template(template_name)
    return template.render(**context)


def render_text_template(template_name: str, context: dict) -> str:
    """Render a plain-text Jinja2 template (no autoescape needed for plain text)."""
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=False,
    )
    template = env.get_template(template_name)
    return template.render(**context)


async def send_invitation_email(
    to_email: str,
    inviter_name: str,
    company_name: str,
    role: str,
    raw_token: str,
    invitation_id: int,
) -> bool:
    """Send an invitation email via SMTP. Returns True on success, False on failure.

    Called from the Celery task (async context). The raw_token is used to build
    the invite URL and is never logged.
    """
    invite_url = f"{settings.FRONTEND_URL}/accept-invite?token={raw_token}"
    current_year = datetime.now().year

    template_context = {
        "inviter_name": inviter_name,
        "company_name": company_name,
        "role": role.capitalize(),
        "invite_url": invite_url,
        "expire_hours": settings.INVITE_TOKEN_EXPIRE_HOURS,
        "current_year": current_year,
        "recipient_email": to_email,
    }

    try:
        html_body = render_email_template("invitation.html", template_context)
        text_body = render_text_template("invitation_text.txt", template_context)
    except Exception as exc:
        logger.error(
            "email.template_render_failed",
            to=to_email,
            invitation_id=invitation_id,
            error=str(exc),
        )
        return False

    message = MessageSchema(
        subject=f"{inviter_name} invited you to join {company_name} on Quantyx AI",
        recipients=[to_email],
        body=html_body,
        alternative_body=text_body,
        subtype=MessageType.html,
    )

    try:
        fm = FastMail(get_mail_config())
        await fm.send_message(message)
        logger.info(
            "email.invitation_sent",
            to=to_email,
            invitation_id=invitation_id,
        )
        return True
    except Exception as exc:
        logger.error(
            "email.send_failed",
            to=to_email,
            invitation_id=invitation_id,
            error=str(exc),
        )
        return False

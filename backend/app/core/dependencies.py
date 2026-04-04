import time
from datetime import datetime, timezone
from typing import Annotated

import structlog
from fastapi import Depends, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RateLimitError,
)
from app.core.security import decode_token
from app.db.session import get_db
from app.services.rate_limit_service import RateLimitService, first_day_next_month_utc
from app.utils.cache import CacheManager, get_redis_client

logger = structlog.get_logger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)

# Read-only subscription routes: still rate-limited per IP/user but do not consume monthly quota.
_SUBSCRIPTION_QUOTA_EXEMPT_PATHS: frozenset[str] = frozenset(
    {
        "/api/v1/subscriptions/usage",
        "/api/v1/subscriptions/plans",
        "/api/v1/subscriptions/current",
    }
)


class TokenData:
    def __init__(self, user_id: int, company_id: int, role: str, email: str):
        self.user_id = user_id
        self.company_id = company_id
        self.role = role
        self.email = email


async def get_current_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> TokenData:
    if not credentials:
        raise AuthenticationError("Authorization header missing")
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise AuthenticationError("Invalid token type")
        return TokenData(
            user_id=int(payload["sub"]),
            company_id=int(payload["company_id"]),
            role=payload["role"],
            email=payload["email"],
        )
    except (JWTError, KeyError, ValueError):
        raise AuthenticationError("Invalid or expired token")


async def require_admin(
    token: Annotated[TokenData, Depends(get_current_token)],
) -> TokenData:
    if token.role != "admin":
        raise AuthorizationError("Admin role required")
    return token


async def require_analyst_or_above(
    token: Annotated[TokenData, Depends(get_current_token)],
) -> TokenData:
    if token.role not in ("admin", "analyst"):
        raise AuthorizationError("Analyst role or above required")
    return token


async def check_rate_limit(
    request: Request,
    response: Response,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Layered limits: per-IP, per-user/plan per minute, monthly quota (metered)."""
    if request.method == "OPTIONS":
        return

    # Developer / admin bypass: skip all limits when the token email is in the
    # RATE_LIMIT_BYPASS_EMAILS set. Email is read from the JWT (server-authoritative),
    # never from the request body.
    if credentials and credentials.credentials and settings.RATE_LIMIT_BYPASS_EMAILS:
        try:
            _bp = decode_token(credentials.credentials)
            if str(_bp.get("email", "")).lower() in settings.RATE_LIMIT_BYPASS_EMAILS:
                logger.debug(
                    "rate_limit.bypassed",
                    email=_bp.get("email"),
                    path=request.url.path,
                )
                return
        except JWTError:
            pass  # fall through to normal enforcement

    forwarded = request.headers.get("x-forwarded-for")
    peer = request.client.host if request.client else None
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = (peer or "unknown").strip() or "unknown"

    redis = await get_redis_client()
    svc = RateLimitService(CacheManager(redis))

    allowed, remaining, limit, reset_ts = await svc.check_ip_limit(ip)
    if not allowed:
        raise RateLimitError(
            "Too many requests from this network. Please retry later.",
            retry_after=settings.API_RATE_LIMIT_WINDOW_SECONDS,
            limit=limit,
            remaining=0,
            reset_ts=reset_ts,
        )

    if not credentials or not credentials.credentials:
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_ts)
        return

    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset_ts)
            return
        company_id = int(payload["company_id"])
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError, TypeError):
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_ts)
        return

    plan_ctx = await svc.fetch_plan_context(company_id, session=db)
    if plan_ctx is None:
        raise NotFoundError("Subscription")

    u_ok, u_rem, u_lim, u_reset = await svc.check_user_limit(
        company_id, user_id, plan_ctx.plan_name
    )
    if not u_ok:
        raise RateLimitError(
            "Rate limit exceeded for your plan. Please slow down or upgrade.",
            retry_after=settings.API_RATE_LIMIT_WINDOW_SECONDS,
            limit=u_lim,
            remaining=0,
            reset_ts=u_reset,
        )

    skip_quota = request.url.path in _SUBSCRIPTION_QUOTA_EXEMPT_PATHS

    q_ok, used = (True, 0) if skip_quota else await svc.check_monthly_quota(
        company_id, plan_ctx.api_calls_limit, plan_ctx.api_calls_used_db
    )
    if (
        not skip_quota
        and not q_ok
        and plan_ctx.api_calls_limit is not None
    ):
        next_day = first_day_next_month_utc()
        reset_epoch = int(
            datetime.combine(next_day, datetime.min.time(), tzinfo=timezone.utc).timestamp()
        )
        retry_after = max(1, min(reset_epoch - int(time.time()), 86400 * 31))
        raise RateLimitError(
            f"Monthly API quota reached ({plan_ctx.api_calls_limit} calls/month). "
            f"Resets on {next_day.isoformat()}.",
            retry_after=retry_after,
            limit=plan_ctx.api_calls_limit,
            remaining=max(0, plan_ctx.api_calls_limit - used),
            reset_ts=reset_epoch,
        )

    response.headers["X-RateLimit-Limit"] = str(u_lim)
    response.headers["X-RateLimit-Remaining"] = str(u_rem)
    response.headers["X-RateLimit-Reset"] = str(u_reset)
    if not skip_quota:
        await svc.increment_usage(company_id, plan_ctx.api_calls_used_db)


async def require_rate_limited_user(
    token: Annotated[TokenData, Depends(get_current_token)],
) -> TokenData:
    """Same as CurrentUser; use when documenting intent (global limit already applied)."""
    return token


# Type aliases for use in route signatures
CurrentUser = Annotated[TokenData, Depends(get_current_token)]
RateLimitedUser = Annotated[TokenData, Depends(require_rate_limited_user)]
AdminUser = Annotated[TokenData, Depends(require_admin)]
AnalystUser = Annotated[TokenData, Depends(require_analyst_or_above)]
DBSession = Annotated[AsyncSession, Depends(get_db)]

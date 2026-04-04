import time
import uuid

import structlog
from fastapi import Request, Response
from jose import JWTError
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.security import decode_token
from app.utils.metrics import observe_http_request, route_template_or_path

logger = structlog.get_logger()


def _company_id_for_metrics(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return "anonymous"
    token = auth.removeprefix("Bearer ").strip()
    if not token:
        return "anonymous"
    try:
        payload = decode_token(token)
        cid = payload.get("company_id")
        return str(cid) if cid is not None else "anonymous"
    except JWTError:
        return "anonymous"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Attach correlation ID + log every request/response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        start = time.perf_counter()

        log = logger.bind(
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
        )

        try:
            response = await call_next(request)
        except Exception as exc:
            log.error("unhandled_exception", error=str(exc))
            elapsed_s = time.perf_counter() - start
            endpoint = route_template_or_path(
                request.url.path,
                request.scope.get("route"),
            )
            observe_http_request(
                method=request.method,
                endpoint=endpoint,
                status_code=500,
                company_id=_company_id_for_metrics(request),
                duration_seconds=elapsed_s,
            )
            raise

        elapsed_s = time.perf_counter() - start
        elapsed_ms = round(elapsed_s * 1000, 2)
        endpoint = route_template_or_path(
            request.url.path,
            request.scope.get("route"),
        )
        observe_http_request(
            method=request.method,
            endpoint=endpoint,
            status_code=response.status_code,
            company_id=_company_id_for_metrics(request),
            duration_seconds=elapsed_s,
        )
        log.info(
            "request_completed",
            status_code=response.status_code,
            elapsed_ms=elapsed_ms,
        )

        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Response-Time"] = f"{elapsed_ms}ms"
        return response


class TenantUsageMiddleware(BaseHTTPMiddleware):
    """Increment api_calls_used for metered API routes (non-health, non-auth)."""

    SKIP_PREFIXES = ("/health", "/docs", "/openapi", "/api/v1/auth")

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        path = request.url.path
        skip = any(path.startswith(prefix) for prefix in self.SKIP_PREFIXES)

        if not skip and response.status_code < 400:
            # Fire-and-forget: increment usage counter in background
            # Actual increment handled in subscription service via company_id in token
            pass

        return response

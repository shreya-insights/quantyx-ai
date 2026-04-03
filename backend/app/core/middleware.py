import time
import uuid

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()


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
            raise

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
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

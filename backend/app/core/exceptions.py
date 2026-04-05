from fastapi import HTTPException, status


class QuantyxException(HTTPException):
    """Base exception for Quantyx AI."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str = "GENERIC_ERROR",
        headers: dict[str, str] | None = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code


class AuthenticationError(QuantyxException):
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="AUTHENTICATION_ERROR",
        )


class AuthorizationError(QuantyxException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="AUTHORIZATION_ERROR",
        )


class NotFoundError(QuantyxException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} not found",
            error_code="NOT_FOUND",
        )


class ConflictError(QuantyxException):
    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code="CONFLICT",
        )


class ValidationError(QuantyxException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code="VALIDATION_ERROR",
        )


class SubscriptionLimitError(QuantyxException):
    def __init__(self, detail: str = "Subscription limit reached"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            error_code="SUBSCRIPTION_LIMIT_EXCEEDED",
        )


class RateLimitError(QuantyxException):
    """429 with actionable Retry-After and X-RateLimit-* headers."""

    def __init__(
        self,
        detail: str,
        *,
        retry_after: int,
        limit: int,
        remaining: int,
        reset_ts: int,
    ):
        hdrs = {
            "Retry-After": str(max(1, retry_after)),
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_ts),
        }
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            error_code="RATE_LIMIT_EXCEEDED",
            headers=hdrs,
        )


class QueryExecutionError(QuantyxException):
    def __init__(self, detail: str = "Query execution failed"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="QUERY_EXECUTION_ERROR",
        )

from fastapi import HTTPException, status


class QuantyxException(HTTPException):
    """Base exception for Quantyx AI."""

    def __init__(self, status_code: int, detail: str, error_code: str = "GENERIC_ERROR"):
        super().__init__(status_code=status_code, detail=detail)
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


class QueryExecutionError(QuantyxException):
    def __init__(self, detail: str = "Query execution failed"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="QUERY_EXECUTION_ERROR",
        )

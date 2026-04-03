from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import decode_token
from app.db.session import get_db

bearer_scheme = HTTPBearer(auto_error=False)


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


# Type aliases for use in route signatures
CurrentUser = Annotated[TokenData, Depends(get_current_token)]
AdminUser = Annotated[TokenData, Depends(require_admin)]
AnalystUser = Annotated[TokenData, Depends(require_analyst_or_above)]
DBSession = Annotated[AsyncSession, Depends(get_db)]

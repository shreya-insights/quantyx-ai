from fastapi import APIRouter

from app.core.dependencies import AdminUser, CurrentUser, DBSession
from app.schemas.auth import (
    CompanyRegisterRequest,
    InviteUserRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserResponse,
)
from app.schemas.common import MessageResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(request: CompanyRegisterRequest, db: DBSession):
    """Register a new company with an admin user. Creates a 14-day trial subscription."""
    service = AuthService(db)
    result = await service.register_company(request)
    return TokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: DBSession):
    """Authenticate and receive JWT access + refresh tokens."""
    service = AuthService(db)
    result = await service.login(request)
    return TokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest, db: DBSession):
    """Exchange a valid refresh token for new access + refresh tokens."""
    service = AuthService(db)
    result = await service.refresh_tokens(request.refresh_token)
    return TokenResponse(**result)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser, db: DBSession):
    """Return the current authenticated user's profile."""
    from app.repositories.user_repo import UserRepository
    repo = UserRepository(db)
    user = await repo.get_by_id(current_user.user_id)
    return user


@router.post("/users/invite", response_model=UserResponse, status_code=201)
async def invite_user(
    request: InviteUserRequest, current_user: AdminUser, db: DBSession
):
    """Invite a new user to the company. Admin only."""
    service = AuthService(db)
    user = await service.invite_user(current_user.company_id, request)
    return user

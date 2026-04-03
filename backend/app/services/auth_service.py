import secrets

from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import (
    create_token_pair,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.company import Company, SubscriptionTier
from app.models.subscription import (
    BillingCycle,
    PlanName,
    Subscription,
    SubscriptionStatus,
)
from app.models.user import User, UserRole
from app.repositories.user_repo import UserRepository
from app.schemas.auth import CompanyRegisterRequest, InviteUserRequest, LoginRequest


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)

    async def register_company(self, request: CompanyRegisterRequest) -> dict:
        # Check email uniqueness
        existing = await self.user_repo.get_by_email(request.admin_email)
        if existing:
            raise ConflictError(f"Email {request.admin_email} is already registered")

        # Check slug uniqueness
        from sqlalchemy import select
        result = await self.session.execute(
            select(Company).where(Company.slug == request.company_slug)
        )
        if result.scalar_one_or_none():
            raise ConflictError(f"Company slug '{request.company_slug}' is already taken")

        # Create company
        company = Company(
            name=request.company_name,
            slug=request.company_slug,
            subscription_tier=SubscriptionTier.STARTER,
            api_key=f"qx_{secrets.token_urlsafe(32)}",
            is_active=True,
        )
        self.session.add(company)
        await self.session.flush()

        # Create admin user
        admin = User(
            company_id=company.id,
            email=request.admin_email,
            hashed_password=hash_password(request.admin_password),
            full_name=request.admin_full_name,
            role=UserRole.ADMIN,
            is_active=True,
        )
        self.session.add(admin)

        # Create starter subscription
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        sub = Subscription(
            company_id=company.id,
            plan_name=PlanName.STARTER,
            status=SubscriptionStatus.TRIAL,
            billing_cycle=BillingCycle.MONTHLY,
            amount=0.0,
            starts_at=now,
            ends_at=now + timedelta(days=14),
            api_calls_limit=1000,
            api_calls_used=0,
            transaction_limit=10_000,
        )
        self.session.add(sub)
        await self.session.flush()
        await self.session.refresh(admin)

        tokens = create_token_pair(admin.id, company.id, admin.role.value, admin.email)
        return {**tokens, "user": admin, "company": company}

    async def login(self, request: LoginRequest) -> dict:
        user = await self.user_repo.get_by_email(request.email)
        if not user or not verify_password(request.password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")
        if not user.is_active:
            raise AuthenticationError("Account is deactivated")

        await self.user_repo.update_last_login(user.id)
        tokens = create_token_pair(user.id, user.company_id, user.role.value, user.email)
        return {**tokens, "user": user}

    async def refresh_tokens(self, refresh_token: str) -> dict:
        try:
            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise AuthenticationError("Invalid token type")
        except (JWTError, KeyError):
            raise AuthenticationError("Invalid or expired refresh token")

        user = await self.user_repo.get_by_id(int(payload["sub"]))
        if not user or not user.is_active:
            raise AuthenticationError("User not found or deactivated")

        return create_token_pair(user.id, user.company_id, user.role.value, user.email)

    async def invite_user(self, company_id: int, request: InviteUserRequest) -> User:
        existing = await self.user_repo.get_by_email(request.email)
        if existing:
            raise ConflictError(f"Email {request.email} is already registered")

        user = User(
            company_id=company_id,
            email=request.email,
            hashed_password=hash_password(request.password),
            full_name=request.full_name,
            role=UserRole(request.role),
            is_active=True,
        )
        return await self.user_repo.create(user)

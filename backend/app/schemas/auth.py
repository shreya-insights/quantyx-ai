from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class CompanyRegisterRequest(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=255)
    company_slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=8, max_length=64)
    admin_full_name: str = Field(..., min_length=2, max_length=255)

    @field_validator("admin_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: int
    company_id: int
    email: str
    full_name: str | None
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class InviteUserRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    role: str = Field(default="viewer", pattern=r"^(admin|analyst|viewer)$")
    password: str = Field(..., min_length=8)

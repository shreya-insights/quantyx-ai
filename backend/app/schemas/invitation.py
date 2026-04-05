"""Pydantic schemas for invitation endpoints."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class SendInviteRequest(BaseModel):
    email: EmailStr
    role: str = Field(default="viewer", pattern=r"^(admin|analyst|viewer)$")


class BulkInviteRequest(BaseModel):
    invites: list[SendInviteRequest] = Field(..., min_length=1, max_length=10)

    @field_validator("invites")
    @classmethod
    def no_duplicate_emails(cls, v: list[SendInviteRequest]) -> list[SendInviteRequest]:
        emails = [i.email.lower() for i in v]
        if len(emails) != len(set(emails)):
            raise ValueError("Duplicate emails in bulk invite request")
        return v


class InvitationResponse(BaseModel):
    id: int
    email: str
    role: str
    status: str
    expires_at: datetime
    invited_by_email: str
    resend_count: int
    email_sent_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class BulkInviteResult(BaseModel):
    email: str
    status: str  # "queued" | "error"
    invitation_id: int | None = None
    error: str | None = None


class BulkInviteResponse(BaseModel):
    results: list[BulkInviteResult]
    sent_count: int
    error_count: int


class ValidateTokenResponse(BaseModel):
    valid: bool
    email: str | None = None
    company_name: str | None = None
    role: str | None = None
    expires_at: datetime | None = None


class AcceptInviteRequest(BaseModel):
    token: str = Field(..., min_length=10)
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=8, max_length=64)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

from datetime import datetime

from pydantic import BaseModel


class PlanFeature(BaseModel):
    name: str
    included: bool


class PlanDetails(BaseModel):
    name: str
    monthly_price: float
    annual_price: float
    user_limit: int | None  # None = unlimited
    transaction_limit: int | None
    api_calls_limit: int | None
    features: list[str]


class SubscribeRequest(BaseModel):
    plan_name: str
    billing_cycle: str = "monthly"


class SubscriptionResponse(BaseModel):
    id: int
    company_id: int
    plan_name: str
    status: str
    billing_cycle: str
    amount: float
    currency: str
    starts_at: datetime
    ends_at: datetime | None
    api_calls_limit: int | None
    api_calls_used: int
    created_at: datetime

    model_config = {"from_attributes": True}


class UsageResponse(BaseModel):
    plan_name: str
    api_calls_used: int
    api_calls_limit: int | None
    api_calls_remaining: int | None
    usage_pct: float | None
    transaction_count_this_month: int
    transaction_limit: int | None

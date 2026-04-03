from datetime import datetime

from pydantic import BaseModel


class FraudAlertResponse(BaseModel):
    id: int
    company_id: int
    transaction_id: int
    alert_type: str
    severity: str
    confidence_score: float | None
    description: str | None
    is_resolved: bool
    resolved_by: int | None
    resolved_at: datetime | None
    rule_metadata: str | None
    created_at: datetime

    # Enriched fields from joins
    transaction_amount: float | None = None
    transaction_ref: str | None = None
    transaction_date: datetime | None = None
    account_number: str | None = None
    user_email: str | None = None

    model_config = {"from_attributes": True}


class FraudResolveRequest(BaseModel):
    resolution_note: str | None = None


class FraudStatsResponse(BaseModel):
    total_alerts: int
    open_alerts: int
    resolved_alerts: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    alerts_by_type: dict[str, int]
    resolution_rate_pct: float
    avg_resolution_time_hours: float | None
    recent_trend: list[dict]  # last 7 days daily counts

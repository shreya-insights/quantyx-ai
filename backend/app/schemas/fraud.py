"""Fraud alert schemas — rule-based and ML SHAP explainability responses."""

from __future__ import annotations

import json
from datetime import datetime

from pydantic import BaseModel, model_validator


class ShapReason(BaseModel):
    feature: str
    shap_value: float
    human_label: str
    direction: str


class MLFraudExplanation(BaseModel):
    fraud_probability: float
    top_reasons: list[ShapReason]
    explanation: str


class FraudAlertResponse(BaseModel):
    model_config = {"from_attributes": True, "protected_namespaces": ()}

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
    model_version: str | None = None
    created_at: datetime

    # Enriched fields from joins
    transaction_amount: float | None = None
    transaction_ref: str | None = None
    transaction_date: datetime | None = None
    account_number: str | None = None
    user_email: str | None = None

    # Parsed from rule_metadata when alert_type == "ml_fraud_score"
    ml_explanation: MLFraudExplanation | None = None


    @model_validator(mode="after")
    def _parse_ml_explanation(self) -> FraudAlertResponse:
        """Inflate SHAP JSON from rule_metadata for ML alerts; leave None for rule alerts."""
        if (
            self.alert_type == "ml_fraud_score"
            and self.rule_metadata
            and self.ml_explanation is None
        ):
            try:
                payload = json.loads(self.rule_metadata)
                self.ml_explanation = MLFraudExplanation(
                    fraud_probability=payload.get("fraud_probability", 0.0),
                    top_reasons=[ShapReason(**r) for r in payload.get("top_reasons", [])],
                    explanation=payload.get("explanation", ""),
                )
            except (json.JSONDecodeError, KeyError, TypeError):
                pass
        return self


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
    recent_trend: list[dict]

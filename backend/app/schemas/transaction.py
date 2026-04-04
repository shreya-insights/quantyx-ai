from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.fraud import FraudAlertResponse
from app.utils.masking import mask_account_number

_FraudPollStatus = Literal[
    "pending",
    "analyzing",
    "clear",
    "flagged",
    "unavailable",
    "not_analyzed",
]


class TransactionCreate(BaseModel):
    account_id: int
    merchant_id: int | None = None
    category_id: int | None = None
    amount: float = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=3)
    transaction_type: str = Field(..., pattern=r"^(debit|credit|transfer|refund)$")
    description: str | None = None
    metadata: dict[str, Any] | None = None
    ip_address: str | None = None
    device_fingerprint: str | None = None
    location_lat: float | None = None
    location_lng: float | None = None
    transaction_date: datetime


class TransactionResponse(BaseModel):
    id: int
    company_id: int
    account_id: int
    merchant_id: int | None
    category_id: int | None
    transaction_ref: str
    amount: float
    currency: str
    transaction_type: str
    status: str
    description: str | None
    transaction_date: datetime
    created_at: datetime
    merchant_name: str | None = None
    category_name: str | None = None
    account_number: str | None = None
    fraud_check_job_id: str | None = None
    fraud_check_status: str | None = None

    model_config = {"from_attributes": True}


class TransactionResponseFull(TransactionResponse):
    """Full transaction payload for admin and analyst roles.

    Adds PII fields (ip_address, device_fingerprint) that are excluded
    from the viewer-facing response. Only returned when role in (admin, analyst).
    """

    ip_address: str | None = None
    device_fingerprint: str | None = None


class TransactionResponseViewer(BaseModel):
    """Viewer-safe transaction payload with PII masked at serialization time.

    - account_number: masked to last 4 digits via mask_account_number()
    - ip_address / device_fingerprint: excluded entirely (not present in schema)

    Masking happens in the model_validator before field assignment so
    raw PII never touches application business logic — only the API boundary.
    """

    id: int
    company_id: int
    account_id: int
    merchant_id: int | None
    category_id: int | None
    transaction_ref: str
    amount: float
    currency: str
    transaction_type: str
    status: str
    description: str | None
    transaction_date: datetime
    created_at: datetime
    merchant_name: str | None = None
    category_name: str | None = None
    account_number: str | None = None
    fraud_check_job_id: str | None = None
    fraud_check_status: str | None = None

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def _mask_pii_fields(cls, data: Any) -> Any:
        """Mask account_number at the serialization boundary before field assignment."""
        if isinstance(data, dict):
            data = dict(data)
            data["account_number"] = mask_account_number(data.get("account_number"))
        return data


class TransactionFraudStatusResponse(BaseModel):
    """Aggregated fraud check state for polling after async Celery analysis."""

    status: _FraudPollStatus
    job_id: str | None = None
    alert: FraudAlertResponse | None = None


class TransactionFilter(BaseModel):
    start_date: datetime | None = None
    end_date: datetime | None = None
    transaction_type: str | None = None
    status: str | None = None
    min_amount: float | None = None
    max_amount: float | None = None
    account_id: int | None = None
    transaction_id: int | None = None
    merchant_id: int | None = None
    category_id: int | None = None


class BulkUploadResponse(BaseModel):
    total_rows: int
    inserted: int
    failed: int
    errors: list[str]


class AccountCreate(BaseModel):
    user_id: int | None = None
    account_number: str = Field(..., min_length=5, max_length=50)
    account_type: str = Field(..., pattern=r"^(checking|savings|credit|investment)$")
    balance: float = Field(default=0.0, ge=0)
    currency: str = Field(default="USD", max_length=3)


class AccountResponse(BaseModel):
    id: int
    company_id: int
    user_id: int | None
    account_number: str
    account_type: str
    balance: float
    currency: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class MerchantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    category_code: str | None = None
    country: str | None = None
    city: str | None = None


class MerchantResponse(BaseModel):
    id: int
    company_id: int
    name: str
    category_code: str | None
    country: str | None
    city: str | None
    is_flagged: bool
    created_at: datetime

    model_config = {"from_attributes": True}

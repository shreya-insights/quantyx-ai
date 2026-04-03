from datetime import date, datetime

from pydantic import BaseModel


class RevenueTrendPoint(BaseModel):
    month: str
    inflow: float
    outflow: float
    net_flow: float
    transaction_count: int
    avg_transaction: float
    mom_growth_pct: float | None


class RevenueTrendResponse(BaseModel):
    data: list[RevenueTrendPoint]
    period_months: int
    total_inflow: float
    total_outflow: float
    avg_monthly_inflow: float


class RFMCustomer(BaseModel):
    account_id: int
    account_number: str | None
    user_email: str | None
    user_name: str | None
    recency_days: int
    frequency: int
    monetary_value: float
    r_score: int
    f_score: int
    m_score: int
    segment: str


class RFMSegmentSummary(BaseModel):
    segment: str
    customer_count: int
    avg_recency_days: float
    avg_frequency: float
    avg_monetary_value: float
    total_revenue: float
    pct_of_total: float


class RFMResponse(BaseModel):
    segments: list[RFMSegmentSummary]
    customers: list[RFMCustomer]
    analysis_date: datetime
    total_customers: int


class CohortRetentionRow(BaseModel):
    cohort_month: str
    cohort_size: int
    period_0: float
    period_1: float | None
    period_2: float | None
    period_3: float | None
    period_6: float | None
    period_12: float | None


class CohortResponse(BaseModel):
    data: list[CohortRetentionRow]
    periods_analyzed: int


class MerchantRanking(BaseModel):
    rank: int
    merchant_id: int
    merchant_name: str
    category_code: str | None
    total_revenue: float
    transaction_count: int
    avg_transaction: float
    revenue_share_pct: float
    rank_in_category: int


class MerchantRankingResponse(BaseModel):
    data: list[MerchantRanking]
    total_merchants: int
    analysis_period_days: int


class KpiSummary(BaseModel):
    period_start: date
    period_end: date
    total_transactions: int
    total_volume: float
    total_inflow: float
    total_outflow: float
    unique_customers: int
    unique_merchants: int
    avg_transaction_value: float
    fraud_alert_count: int
    fraud_alert_rate_pct: float
    top_category: str | None
    mom_volume_growth_pct: float | None
    active_accounts: int


class SpendingByCategory(BaseModel):
    category_name: str
    category_code: str
    total_amount: float
    transaction_count: int
    pct_of_total: float


class TransactionFrequency(BaseModel):
    period: str
    hour_of_day: int
    day_of_week: str
    transaction_count: int
    total_amount: float
    avg_amount: float

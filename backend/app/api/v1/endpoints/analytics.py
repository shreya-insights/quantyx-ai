from datetime import date, timedelta

from fastapi import APIRouter, Query

from app.core.dependencies import AnalystUser, CurrentUser, DBSession
from app.schemas.analytics import (
    CohortResponse,
    KpiSummary,
    MerchantRankingResponse,
    RevenueTrendResponse,
    RFMResponse,
    SpendingByCategory,
    TransactionFrequency,
)
from app.services.analytics_service import AnalyticsService
from app.utils.cache import get_cache_manager

router = APIRouter(prefix="/analytics", tags=["Analytics"])


async def _get_service(db: DBSession) -> AnalyticsService:
    cache = await get_cache_manager()
    return AnalyticsService(db, cache)


@router.get("/revenue-trends", response_model=RevenueTrendResponse)
async def get_revenue_trends(
    current_user: CurrentUser,
    db: DBSession,
    months: int = Query(default=12, ge=1, le=36, description="Number of months to look back"),
):
    """
    Monthly revenue trend analysis with MoM growth percentage.

    Uses window function LAG() to compute month-over-month growth.
    Returns inflow, outflow, net flow, transaction count per month.
    """
    service = await _get_service(db)
    return await service.get_revenue_trend(current_user.company_id, months)


@router.get("/customer-segmentation", response_model=RFMResponse)
async def get_customer_segmentation(
    current_user: AnalystUser,
    db: DBSession,
):
    """
    RFM (Recency, Frequency, Monetary) customer segmentation.

    Uses NTILE(5) window functions to score customers across 3 dimensions.
    Segments: Champions, Loyal Customers, At Risk, Lost Customers, Big Spenders, etc.
    """
    service = await _get_service(db)
    return await service.get_rfm_analysis(current_user.company_id)


@router.get("/cohort", response_model=CohortResponse)
async def get_cohort_analysis(
    current_user: AnalystUser,
    db: DBSession,
):
    """
    Monthly cohort retention matrix.

    Shows what percentage of users from each cohort month
    remained active over 1, 2, 3, 6, and 12 months.
    Uses PERIOD_DIFF for accurate month calculation.
    """
    service = await _get_service(db)
    return await service.get_cohort_retention(current_user.company_id)


@router.get("/top-merchants", response_model=MerchantRankingResponse)
async def get_top_merchants(
    current_user: CurrentUser,
    db: DBSession,
    days: int = Query(default=30, ge=7, le=365),
    top_n: int = Query(default=20, ge=5, le=100),
):
    """
    Top merchants by revenue with category-level ranking.

    Uses RANK() OVER (PARTITION BY category_code) for within-category ranking
    and SUM OVER () for global revenue share percentage.
    """
    service = await _get_service(db)
    return await service.get_top_merchants(current_user.company_id, days, top_n)


@router.get("/kpi-summary", response_model=KpiSummary)
async def get_kpi_summary(
    current_user: CurrentUser,
    db: DBSession,
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
):
    """
    One-shot KPI dashboard summary: total volume, inflow/outflow,
    unique customers, fraud rate, and more.
    """
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    service = await _get_service(db)
    return await service.get_kpi_summary(current_user.company_id, start_date, end_date)


@router.get("/spending-by-category", response_model=list[SpendingByCategory])
async def get_spending_by_category(
    current_user: CurrentUser,
    db: DBSession,
    days: int = Query(default=30, ge=7, le=365),
):
    """Breakdown of debit transactions by merchant category with % share."""
    service = await _get_service(db)
    return await service.get_spending_by_category(current_user.company_id, days)


@router.get("/transaction-heatmap", response_model=list[TransactionFrequency])
async def get_transaction_heatmap(
    current_user: CurrentUser,
    db: DBSession,
    days: int = Query(default=90, ge=7, le=365),
):
    """Hour-of-day × day-of-week transaction frequency heatmap."""
    service = await _get_service(db)
    return await service.get_transaction_frequency_heatmap(current_user.company_id, days)

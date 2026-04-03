from datetime import date, datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.analytics_repo import AnalyticsRepository
from app.schemas.analytics import (
    CohortResponse,
    CohortRetentionRow,
    KpiSummary,
    MerchantRanking,
    MerchantRankingResponse,
    RevenueTrendPoint,
    RevenueTrendResponse,
    RFMCustomer,
    RFMResponse,
    RFMSegmentSummary,
    SpendingByCategory,
    TransactionFrequency,
)
from app.utils.cache import CacheManager


class AnalyticsService:
    def __init__(self, session: AsyncSession, cache: CacheManager | None = None):
        self.repo = AnalyticsRepository(session)
        self.cache = cache

    async def get_revenue_trend(
        self, company_id: int, months: int = 12
    ) -> RevenueTrendResponse:
        cache_key = f"revenue_trend:{company_id}:{months}"
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                return RevenueTrendResponse(**cached)

        rows = await self.repo.get_revenue_trend(company_id, months)
        points = [
            RevenueTrendPoint(
                month=r["month"],
                inflow=float(r["inflow"] or 0),
                outflow=float(r["outflow"] or 0),
                net_flow=float(r["net_flow"] or 0),
                transaction_count=int(r["transaction_count"] or 0),
                avg_transaction=float(r["avg_transaction"] or 0),
                mom_growth_pct=float(r["mom_growth_pct"]) if r["mom_growth_pct"] is not None else None,
            )
            for r in rows
        ]

        total_inflow = sum(p.inflow for p in points)
        total_outflow = sum(p.outflow for p in points)
        avg_monthly = total_inflow / len(points) if points else 0.0

        response = RevenueTrendResponse(
            data=points,
            period_months=months,
            total_inflow=round(total_inflow, 2),
            total_outflow=round(total_outflow, 2),
            avg_monthly_inflow=round(avg_monthly, 2),
        )

        if self.cache:
            from app.core.config import settings
            await self.cache.set(cache_key, response.model_dump(), ttl=settings.CACHE_TTL_REVENUE)

        return response

    async def get_rfm_analysis(self, company_id: int) -> RFMResponse:
        cache_key = f"rfm:{company_id}"
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                return RFMResponse(**cached)

        customers_raw = await self.repo.get_rfm_segmentation(company_id)
        summary_raw = await self.repo.get_rfm_summary(company_id)

        customers = [
            RFMCustomer(
                account_id=r["account_id"],
                account_number=r.get("account_number"),
                user_email=r.get("user_email"),
                user_name=r.get("user_name"),
                recency_days=int(r["recency_days"] or 0),
                frequency=int(r["frequency"] or 0),
                monetary_value=float(r["monetary_value"] or 0),
                r_score=int(r["r_score"] or 0),
                f_score=int(r["f_score"] or 0),
                m_score=int(r["m_score"] or 0),
                segment=r["segment"],
            )
            for r in customers_raw
        ]

        segments = [
            RFMSegmentSummary(
                segment=r["segment"],
                customer_count=int(r["customer_count"] or 0),
                avg_recency_days=float(r["avg_recency_days"] or 0),
                avg_frequency=float(r["avg_frequency"] or 0),
                avg_monetary_value=float(r["avg_monetary_value"] or 0),
                total_revenue=float(r["total_revenue"] or 0),
                pct_of_total=float(r["pct_of_total"] or 0),
            )
            for r in summary_raw
        ]

        response = RFMResponse(
            segments=segments,
            customers=customers[:500],  # limit payload size
            analysis_date=datetime.now(timezone.utc),
            total_customers=len(customers),
        )

        if self.cache:
            from app.core.config import settings
            await self.cache.set(cache_key, response.model_dump(), ttl=settings.CACHE_TTL_SEGMENTATION)

        return response

    async def get_cohort_retention(self, company_id: int) -> CohortResponse:
        cache_key = f"cohort:{company_id}"
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                return CohortResponse(**cached)

        rows = await self.repo.get_cohort_retention(company_id)
        cohort_rows = [
            CohortRetentionRow(
                cohort_month=r["cohort_month"],
                cohort_size=int(r["cohort_size"] or 0),
                period_0=float(r["period_0"] or 0),
                period_1=float(r["period_1"]) if r.get("period_1") is not None else None,
                period_2=float(r["period_2"]) if r.get("period_2") is not None else None,
                period_3=float(r["period_3"]) if r.get("period_3") is not None else None,
                period_6=float(r["period_6"]) if r.get("period_6") is not None else None,
                period_12=float(r["period_12"]) if r.get("period_12") is not None else None,
            )
            for r in rows
        ]

        response = CohortResponse(data=cohort_rows, periods_analyzed=12)

        if self.cache:
            from app.core.config import settings
            await self.cache.set(cache_key, response.model_dump(), ttl=settings.CACHE_TTL_COHORT)

        return response

    async def get_top_merchants(
        self, company_id: int, days: int = 30, top_n: int = 20
    ) -> MerchantRankingResponse:
        cache_key = f"top_merchants:{company_id}:{days}:{top_n}"
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                return MerchantRankingResponse(**cached)

        rows = await self.repo.get_top_merchants(company_id, days, top_n)
        merchants = [
            MerchantRanking(
                rank=int(r["rank"]),
                merchant_id=int(r["merchant_id"]),
                merchant_name=r["merchant_name"],
                category_code=r.get("category_code"),
                total_revenue=float(r["total_revenue"] or 0),
                transaction_count=int(r["transaction_count"] or 0),
                avg_transaction=float(r["avg_transaction"] or 0),
                revenue_share_pct=float(r["revenue_share_pct"] or 0),
                rank_in_category=int(r["rank_in_category"] or 1),
            )
            for r in rows
        ]

        response = MerchantRankingResponse(
            data=merchants,
            total_merchants=len(merchants),
            analysis_period_days=days,
        )

        if self.cache:
            from app.core.config import settings
            await self.cache.set(cache_key, response.model_dump(), ttl=settings.CACHE_TTL_MERCHANT)

        return response

    async def get_kpi_summary(
        self, company_id: int, start_date: date, end_date: date
    ) -> KpiSummary:
        cache_key = f"kpi:{company_id}:{start_date}:{end_date}"
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                return KpiSummary(**cached)

        kpi = await self.repo.get_kpi_summary(
            company_id, str(start_date), str(end_date)
        )
        fraud = await self.repo.get_fraud_kpi(
            company_id, str(start_date), str(end_date)
        )

        total_tx = int(kpi["total_transactions"] or 0)
        fraud_count = int(fraud["fraud_alert_count"] or 0)
        fraud_rate = round(fraud_count / total_tx * 100, 4) if total_tx > 0 else 0.0

        response = KpiSummary(
            period_start=start_date,
            period_end=end_date,
            total_transactions=total_tx,
            total_volume=float(kpi["total_volume"] or 0),
            total_inflow=float(kpi["total_inflow"] or 0),
            total_outflow=float(kpi["total_outflow"] or 0),
            unique_customers=int(kpi["unique_customers"] or 0),
            unique_merchants=int(kpi["unique_merchants"] or 0),
            avg_transaction_value=float(kpi["avg_transaction_value"] or 0),
            fraud_alert_count=fraud_count,
            fraud_alert_rate_pct=fraud_rate,
            top_category=None,
            mom_volume_growth_pct=None,
            active_accounts=int(kpi["unique_customers"] or 0),
        )

        if self.cache:
            from app.core.config import settings
            await self.cache.set(cache_key, response.model_dump(), ttl=settings.CACHE_TTL_KPI)

        return response

    async def get_spending_by_category(
        self, company_id: int, days: int = 30
    ) -> list[SpendingByCategory]:
        rows = await self.repo.get_spending_by_category(company_id, days)
        return [
            SpendingByCategory(
                category_name=r["category_name"],
                category_code=r["category_code"],
                total_amount=float(r["total_amount"] or 0),
                transaction_count=int(r["transaction_count"] or 0),
                pct_of_total=float(r["pct_of_total"] or 0),
            )
            for r in rows
        ]

    async def get_transaction_frequency_heatmap(
        self, company_id: int, days: int = 90
    ) -> list[TransactionFrequency]:
        rows = await self.repo.get_transaction_frequency_heatmap(company_id, days)
        return [
            TransactionFrequency(
                period=f"D{r['dow_num']}H{r['hour_of_day']}",
                hour_of_day=int(r["hour_of_day"]),
                day_of_week=r["day_of_week"],
                transaction_count=int(r["transaction_count"] or 0),
                total_amount=float(r["total_amount"] or 0),
                avg_amount=float(r["avg_amount"] or 0),
            )
            for r in rows
        ]

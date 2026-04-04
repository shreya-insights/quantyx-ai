"""Read/write analytics pre-aggregate cache with MySQL upsert semantics."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal

from sqlalchemy import func, select, text
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.analytics_cache import (
    DailyRevenueSummary,
    KPISummaryCache,
    MerchantRankingCache,
    MonthlyCategorySummary,
)

CacheHeaderStatus = Literal["fresh", "stale", "miss"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _naive_utc(dt: datetime) -> datetime:
    """Normalize DB datetimes for age comparisons."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _classify_refresh(
    refreshed_at: datetime | None,
    snapshot_tx: int | None,
    current_tx: int,
) -> bool:
    """Return True if cache row set should be treated as stale (trigger recompute)."""
    if refreshed_at is None:
        return True
    ref = _naive_utc(refreshed_at)
    age_min = (_utcnow() - ref).total_seconds() / 60.0
    if age_min >= float(settings.ANALYTICS_CACHE_FRESHNESS_MINUTES):
        return True
    if snapshot_tx is not None:
        drift = current_tx - int(snapshot_tx)
        if drift >= settings.ANALYTICS_CACHE_STALE_TX_THRESHOLD:
            return True
    return False


class AnalyticsCacheRepository:
    """Tenant-scoped analytics cache with freshness + transaction-drift checks."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_current_tx_count(self, company_id: int) -> int:
        result = await self.session.execute(
            text(
                "SELECT COUNT(*) AS c FROM transactions WHERE company_id = :company_id"
            ),
            {"company_id": company_id},
        )
        row = result.fetchone()
        return int(row[0] if row and row[0] is not None else 0)

    async def should_skip_idempotent_refresh(
        self, company_id: int, within_minutes: int | None = None
    ) -> bool:
        window = (
            within_minutes
            if within_minutes is not None
            else settings.ANALYTICS_CACHE_IDEMPOTENCY_MINUTES
        )
        stmt = select(func.max(DailyRevenueSummary.refreshed_at)).where(
            DailyRevenueSummary.company_id == company_id
        )
        res = await self.session.execute(stmt)
        last = res.scalar_one_or_none()
        if last is None:
            return False
        delta = _utcnow() - _naive_utc(last)
        return delta.total_seconds() < window * 60

    async def read_revenue_cache(
        self, company_id: int, months: int
    ) -> tuple[list[dict[str, Any]], CacheHeaderStatus]:
        stmt = (
            select(DailyRevenueSummary)
            .where(DailyRevenueSummary.company_id == company_id)
            .order_by(DailyRevenueSummary.summary_month.desc())
            .limit(months)
        )
        res = await self.session.execute(stmt)
        rows_orm = list(res.scalars().all())
        if not rows_orm:
            return [], "miss"
        rows_orm.reverse()
        meta = rows_orm[-1]
        current_tx = await self.get_current_tx_count(company_id)
        stale = _classify_refresh(
            meta.refreshed_at, meta.transaction_snapshot_count, current_tx
        )
        out = [
            {
                "month": r.summary_month,
                "inflow": float(r.inflow),
                "outflow": float(r.outflow),
                "net_flow": float(r.net_flow),
                "transaction_count": int(r.transaction_count),
                "avg_transaction": float(r.avg_transaction),
                "mom_growth_pct": float(r.mom_growth_pct)
                if r.mom_growth_pct is not None
                else None,
            }
            for r in rows_orm
        ]
        status: CacheHeaderStatus = "stale" if stale else "fresh"
        return out, status

    async def read_category_cache(
        self, company_id: int, period_days: int
    ) -> tuple[list[dict[str, Any]], CacheHeaderStatus]:
        stmt = select(MonthlyCategorySummary).where(
            MonthlyCategorySummary.company_id == company_id,
            MonthlyCategorySummary.period_days == period_days,
        )
        res = await self.session.execute(stmt)
        rows_orm = list(res.scalars().all())
        if not rows_orm:
            return [], "miss"
        meta = rows_orm[0]
        current_tx = await self.get_current_tx_count(company_id)
        stale = _classify_refresh(
            meta.refreshed_at, meta.transaction_snapshot_count, current_tx
        )
        out = [
            {
                "category_name": r.category_name,
                "category_code": r.category_code,
                "total_amount": float(r.total_amount),
                "transaction_count": int(r.transaction_count),
                "pct_of_total": float(r.pct_of_total),
            }
            for r in rows_orm
        ]
        return out, ("stale" if stale else "fresh")

    async def read_merchant_cache(
        self, company_id: int, period_days: int, top_n: int
    ) -> tuple[list[dict[str, Any]], CacheHeaderStatus]:
        stmt = (
            select(MerchantRankingCache)
            .where(
                MerchantRankingCache.company_id == company_id,
                MerchantRankingCache.period_days == period_days,
                MerchantRankingCache.rank_position <= top_n,
            )
            .order_by(MerchantRankingCache.rank_position.asc())
        )
        res = await self.session.execute(stmt)
        rows_orm = list(res.scalars().all())
        if not rows_orm:
            return [], "miss"
        meta = rows_orm[0]
        current_tx = await self.get_current_tx_count(company_id)
        stale = _classify_refresh(
            meta.refreshed_at, meta.transaction_snapshot_count, current_tx
        )
        out = [
            {
                "rank": int(r.rank_position),
                "merchant_id": int(r.merchant_id),
                "merchant_name": r.merchant_name,
                "category_code": r.category_code,
                "total_revenue": float(r.total_revenue),
                "transaction_count": int(r.transaction_count),
                "avg_transaction": float(r.avg_transaction),
                "revenue_share_pct": float(r.revenue_share_pct),
                "rank_in_category": int(r.rank_in_category),
            }
            for r in rows_orm
        ]
        return out, ("stale" if stale else "fresh")

    async def read_kpi_cache(
        self, company_id: int, period_type: str
    ) -> tuple[dict[str, Any] | None, CacheHeaderStatus]:
        stmt = select(KPISummaryCache).where(
            KPISummaryCache.company_id == company_id,
            KPISummaryCache.period_type == period_type,
        )
        res = await self.session.execute(stmt)
        row = res.scalar_one_or_none()
        if row is None:
            return None, "miss"
        current_tx = await self.get_current_tx_count(company_id)
        stale = _classify_refresh(
            row.refreshed_at, row.transaction_snapshot_count, current_tx
        )
        payload = {
            "period_start": row.period_start,
            "period_end": row.period_end,
            "total_transactions": int(row.total_transactions),
            "total_volume": float(row.total_volume),
            "total_inflow": float(row.total_inflow),
            "total_outflow": float(row.total_outflow),
            "unique_customers": int(row.unique_customers),
            "unique_merchants": int(row.unique_merchants),
            "avg_transaction_value": float(row.avg_transaction_value),
            "fraud_alert_count": int(row.fraud_alert_count),
            "fraud_alert_rate_pct": float(row.fraud_alert_rate_pct),
            "active_accounts": int(row.active_accounts),
            "top_category": row.top_category,
            "mom_volume_growth_pct": row.mom_volume_growth_pct,
        }
        return payload, ("stale" if stale else "fresh")

    @staticmethod
    def kpi_period_type(start: date, end: date) -> str:
        return f"{start.isoformat()}|{end.isoformat()}"

    async def upsert_revenue_cache(
        self,
        company_id: int,
        rows: list[dict[str, Any]],
        transaction_snapshot_count: int,
    ) -> None:
        refreshed = _utcnow()
        for r in rows:
            stmt = mysql_insert(DailyRevenueSummary).values(
                company_id=company_id,
                summary_month=r["month"],
                inflow=r["inflow"],
                outflow=r["outflow"],
                net_flow=r["net_flow"],
                transaction_count=int(r["transaction_count"] or 0),
                avg_transaction=r["avg_transaction"],
                mom_growth_pct=r.get("mom_growth_pct"),
                transaction_snapshot_count=transaction_snapshot_count,
                refreshed_at=refreshed,
            )
            stmt = stmt.on_duplicate_key_update(
                inflow=stmt.inserted.inflow,
                outflow=stmt.inserted.outflow,
                net_flow=stmt.inserted.net_flow,
                transaction_count=stmt.inserted.transaction_count,
                avg_transaction=stmt.inserted.avg_transaction,
                mom_growth_pct=stmt.inserted.mom_growth_pct,
                transaction_snapshot_count=stmt.inserted.transaction_snapshot_count,
                refreshed_at=stmt.inserted.refreshed_at,
            )
            await self.session.execute(stmt)

    async def upsert_category_cache(
        self,
        company_id: int,
        period_days: int,
        rows: list[dict[str, Any]],
        transaction_snapshot_count: int,
    ) -> None:
        refreshed = _utcnow()
        for r in rows:
            stmt = mysql_insert(MonthlyCategorySummary).values(
                company_id=company_id,
                category_code=r["category_code"],
                category_name=r["category_name"],
                period_days=period_days,
                total_amount=r["total_amount"],
                transaction_count=int(r["transaction_count"] or 0),
                pct_of_total=r["pct_of_total"],
                transaction_snapshot_count=transaction_snapshot_count,
                refreshed_at=refreshed,
            )
            stmt = stmt.on_duplicate_key_update(
                category_name=stmt.inserted.category_name,
                total_amount=stmt.inserted.total_amount,
                transaction_count=stmt.inserted.transaction_count,
                pct_of_total=stmt.inserted.pct_of_total,
                transaction_snapshot_count=stmt.inserted.transaction_snapshot_count,
                refreshed_at=stmt.inserted.refreshed_at,
            )
            await self.session.execute(stmt)

    async def upsert_merchant_cache(
        self,
        company_id: int,
        period_days: int,
        rows: list[dict[str, Any]],
        transaction_snapshot_count: int,
    ) -> None:
        refreshed = _utcnow()
        for r in rows:
            stmt = mysql_insert(MerchantRankingCache).values(
                company_id=company_id,
                merchant_id=int(r["merchant_id"]),
                period_days=period_days,
                merchant_name=r["merchant_name"],
                category_code=r.get("category_code"),
                rank_position=int(r["rank"]),
                total_revenue=r["total_revenue"],
                transaction_count=int(r["transaction_count"] or 0),
                avg_transaction=r["avg_transaction"],
                revenue_share_pct=r["revenue_share_pct"],
                rank_in_category=int(r["rank_in_category"] or 0),
                transaction_snapshot_count=transaction_snapshot_count,
                refreshed_at=refreshed,
            )
            stmt = stmt.on_duplicate_key_update(
                merchant_name=stmt.inserted.merchant_name,
                category_code=stmt.inserted.category_code,
                rank_position=stmt.inserted.rank_position,
                total_revenue=stmt.inserted.total_revenue,
                transaction_count=stmt.inserted.transaction_count,
                avg_transaction=stmt.inserted.avg_transaction,
                revenue_share_pct=stmt.inserted.revenue_share_pct,
                rank_in_category=stmt.inserted.rank_in_category,
                transaction_snapshot_count=stmt.inserted.transaction_snapshot_count,
                refreshed_at=stmt.inserted.refreshed_at,
            )
            await self.session.execute(stmt)

    async def upsert_kpi_cache(
        self,
        company_id: int,
        period_type: str,
        period_start: date,
        period_end: date,
        kpi: dict[str, Any],
        fraud_alert_count: int,
        fraud_rate_pct: float,
        transaction_snapshot_count: int,
    ) -> None:
        refreshed = _utcnow()
        stmt = mysql_insert(KPISummaryCache).values(
            company_id=company_id,
            period_type=period_type,
            period_start=period_start,
            period_end=period_end,
            total_transactions=int(kpi["total_transactions"] or 0),
            total_volume=kpi["total_volume"],
            total_inflow=kpi["total_inflow"],
            total_outflow=kpi["total_outflow"],
            unique_customers=int(kpi["unique_customers"] or 0),
            unique_merchants=int(kpi["unique_merchants"] or 0),
            avg_transaction_value=kpi["avg_transaction_value"],
            fraud_alert_count=fraud_alert_count,
            fraud_alert_rate_pct=fraud_rate_pct,
            active_accounts=int(kpi["unique_customers"] or 0),
            top_category=None,
            mom_volume_growth_pct=None,
            transaction_snapshot_count=transaction_snapshot_count,
            refreshed_at=refreshed,
        )
        stmt = stmt.on_duplicate_key_update(
            period_start=stmt.inserted.period_start,
            period_end=stmt.inserted.period_end,
            total_transactions=stmt.inserted.total_transactions,
            total_volume=stmt.inserted.total_volume,
            total_inflow=stmt.inserted.total_inflow,
            total_outflow=stmt.inserted.total_outflow,
            unique_customers=stmt.inserted.unique_customers,
            unique_merchants=stmt.inserted.unique_merchants,
            avg_transaction_value=stmt.inserted.avg_transaction_value,
            fraud_alert_count=stmt.inserted.fraud_alert_count,
            fraud_alert_rate_pct=stmt.inserted.fraud_alert_rate_pct,
            active_accounts=stmt.inserted.active_accounts,
            top_category=stmt.inserted.top_category,
            mom_volume_growth_pct=stmt.inserted.mom_volume_growth_pct,
            transaction_snapshot_count=stmt.inserted.transaction_snapshot_count,
            refreshed_at=stmt.inserted.refreshed_at,
        )
        await self.session.execute(stmt)


def default_kpi_period_dates() -> tuple[date, date]:
    """Rolling window aligned with analytics API defaults (last 30 days)."""
    end_d = datetime.now(timezone.utc).date()
    start_d = end_d - timedelta(days=30)
    return start_d, end_d

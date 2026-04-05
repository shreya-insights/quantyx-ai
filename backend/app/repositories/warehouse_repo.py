"""Read path for pre-aggregated warehouse tables (tenant-isolated)."""

from typing import Literal, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.warehouse import (
    CohortRetentionMetric,
    HourlyTransactionHeatmap,
    LifetimeValueMetric,
)
from app.schemas.analytics import (
    CohortRetentionCell,
    CohortRetentionGridResponse,
    HeatmapCell,
    HeatmapResponse,
    LTVSegment,
    LTVSegmentsResponse,
)

_LTV_ORDER = ("high", "medium", "low")


class WarehouseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_cohort_retention_grid(
        self, company_id: int
    ) -> CohortRetentionGridResponse:
        result = await self._session.execute(
            select(CohortRetentionMetric)
            .where(CohortRetentionMetric.company_id == company_id)
            .order_by(
                CohortRetentionMetric.cohort_month,
                CohortRetentionMetric.months_since_cohort,
            )
        )
        rows_orm = result.scalars().all()
        cells = [
            CohortRetentionCell(
                cohort_month=r.cohort_month,
                months_since_cohort=r.months_since_cohort,
                retention_rate=float(r.retention_rate),
                user_count=int(r.user_count),
                retained_count=int(r.retained_count),
            )
            for r in rows_orm
        ]
        cohort_months_sorted = sorted({c.cohort_month for c in cells})
        max_months = max((c.months_since_cohort for c in cells), default=0)
        return CohortRetentionGridResponse(
            rows=cells,
            cohort_months=cohort_months_sorted,
            max_months=max_months,
        )

    async def get_ltv_segments(self, company_id: int) -> LTVSegmentsResponse:
        result = await self._session.execute(
            select(LifetimeValueMetric).where(
                LifetimeValueMetric.company_id == company_id
            )
        )
        rows_orm = result.scalars().all()
        total = len(rows_orm)
        if total == 0:
            return LTVSegmentsResponse(segments=[], total_users=0)
        bucket: dict[str, list[float]] = {"high": [], "medium": [], "low": []}
        for r in rows_orm:
            seg = str(r.ltv_segment).lower()
            if seg in bucket:
                bucket[seg].append(float(r.total_spend))
        segments: list[LTVSegment] = []
        for seg in _LTV_ORDER:
            spends = bucket.get(seg, [])
            n = len(spends)
            if n == 0:
                continue
            segments.append(
                LTVSegment(
                    segment=cast(Literal["high", "medium", "low"], seg),
                    user_count=n,
                    pct_of_total=round(n * 100.0 / total, 2),
                    avg_spend=round(sum(spends) / n, 2),
                )
            )
        return LTVSegmentsResponse(segments=segments, total_users=total)

    async def get_hourly_heatmap(self, company_id: int) -> HeatmapResponse:
        result = await self._session.execute(
            select(HourlyTransactionHeatmap).where(
                HourlyTransactionHeatmap.company_id == company_id
            )
        )
        rows_orm = result.scalars().all()
        dense: dict[tuple[int, int], HeatmapCell] = {}
        for r in rows_orm:
            dense[(int(r.day_of_week), int(r.hour_of_day))] = HeatmapCell(
                day_of_week=int(r.day_of_week),
                hour_of_day=int(r.hour_of_day),
                avg_count=float(r.avg_count),
                avg_amount=float(r.avg_amount),
                fraud_rate=float(r.fraud_rate),
            )
        cells: list[HeatmapCell] = []
        for dow in range(7):
            for hod in range(24):
                key = (dow, hod)
                cells.append(
                    dense.get(key)
                    or HeatmapCell(
                        day_of_week=dow,
                        hour_of_day=hod,
                        avg_count=0.0,
                        avg_amount=0.0,
                        fraud_rate=0.0,
                    )
                )
        return HeatmapResponse(cells=cells)

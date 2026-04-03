from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fraud_alert import FraudAlert
from app.repositories.base import BaseRepository


class FraudRepository(BaseRepository[FraudAlert]):
    def __init__(self, session: AsyncSession):
        super().__init__(FraudAlert, session)

    async def get_company_alerts(
        self,
        company_id: int,
        severity: str | None = None,
        is_resolved: bool | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict], int]:
        """Enriched fraud alerts with transaction + account info."""
        where = ["fa.company_id = :company_id"]
        params: dict = {"company_id": company_id}

        if severity:
            where.append("fa.severity = :severity")
            params["severity"] = severity
        if is_resolved is not None:
            where.append("fa.is_resolved = :is_resolved")
            params["is_resolved"] = is_resolved

        where_sql = " AND ".join(where)

        count_sql = f"SELECT COUNT(*) FROM fraud_alerts fa WHERE {where_sql}"
        count_result = await self.session.execute(text(count_sql), params)
        total = count_result.scalar_one()

        data_sql = f"""
            SELECT
                fa.id, fa.company_id, fa.transaction_id, fa.alert_type,
                fa.severity, fa.confidence_score, fa.description,
                fa.is_resolved, fa.resolved_by, fa.resolved_at,
                fa.rule_metadata, fa.created_at,
                t.amount AS transaction_amount,
                t.transaction_ref,
                t.transaction_date,
                a.account_number,
                u.email AS user_email
            FROM fraud_alerts fa
            JOIN transactions t ON fa.transaction_id = t.id
            JOIN accounts a ON t.account_id = a.id
            LEFT JOIN users u ON a.user_id = u.id
            WHERE {where_sql}
            ORDER BY fa.created_at DESC
            LIMIT :limit OFFSET :offset
        """
        params["limit"] = limit
        params["offset"] = offset
        result = await self.session.execute(text(data_sql), params)
        rows = [dict(row._mapping) for row in result.fetchall()]
        return rows, total

    async def get_fraud_stats(self, company_id: int) -> dict:
        sql = text("""
            SELECT
                COUNT(*) AS total_alerts,
                SUM(CASE WHEN is_resolved = 0 THEN 1 ELSE 0 END) AS open_alerts,
                SUM(CASE WHEN is_resolved = 1 THEN 1 ELSE 0 END) AS resolved_alerts,
                SUM(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END) AS critical_count,
                SUM(CASE WHEN severity = 'high'     THEN 1 ELSE 0 END) AS high_count,
                SUM(CASE WHEN severity = 'medium'   THEN 1 ELSE 0 END) AS medium_count,
                SUM(CASE WHEN severity = 'low'      THEN 1 ELSE 0 END) AS low_count,
                ROUND(
                    SUM(CASE WHEN is_resolved=1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0) * 100, 2
                ) AS resolution_rate_pct,
                AVG(
                    CASE WHEN is_resolved = 1 AND resolved_at IS NOT NULL
                         THEN TIMESTAMPDIFF(HOUR, created_at, resolved_at) END
                ) AS avg_resolution_time_hours
            FROM fraud_alerts
            WHERE company_id = :company_id
        """)
        result = await self.session.execute(sql, {"company_id": company_id})
        row = result.fetchone()
        stats = dict(row._mapping)

        # Alerts by type
        type_sql = text("""
            SELECT alert_type, COUNT(*) AS cnt
            FROM fraud_alerts
            WHERE company_id = :company_id
            GROUP BY alert_type
        """)
        type_result = await self.session.execute(type_sql, {"company_id": company_id})
        stats["alerts_by_type"] = {r.alert_type: r.cnt for r in type_result.fetchall()}

        # Last 7 days trend
        trend_sql = text("""
            SELECT DATE(created_at) AS alert_date, COUNT(*) AS alert_count
            FROM fraud_alerts
            WHERE company_id = :company_id
              AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY DATE(created_at)
            ORDER BY alert_date
        """)
        trend_result = await self.session.execute(trend_sql, {"company_id": company_id})
        stats["recent_trend"] = [
            {"date": str(r.alert_date), "count": r.alert_count}
            for r in trend_result.fetchall()
        ]

        return stats

    async def check_velocity(self, company_id: int, account_id: int, threshold: int, window_min: int) -> int:
        """Count recent transactions for velocity rule."""
        result = await self.session.execute(
            text("""
                SELECT COUNT(*) AS tx_count
                FROM transactions
                WHERE company_id = :company_id
                  AND account_id = :account_id
                  AND transaction_date >= DATE_SUB(NOW(), INTERVAL :window_min MINUTE)
                  AND status IN ('completed', 'pending')
            """),
            {"company_id": company_id, "account_id": account_id, "window_min": window_min},
        )
        return result.scalar_one() or 0

    async def check_duplicate(
        self, company_id: int, account_id: int, amount: float, merchant_id: int | None, window_min: int
    ) -> bool:
        """Detect duplicate transaction (same amount + merchant in short window)."""
        if not merchant_id:
            return False
        result = await self.session.execute(
            text("""
                SELECT COUNT(*) AS dup_count
                FROM transactions
                WHERE company_id = :company_id
                  AND account_id = :account_id
                  AND merchant_id = :merchant_id
                  AND amount = :amount
                  AND transaction_date >= DATE_SUB(NOW(), INTERVAL :window_min MINUTE)
                  AND status IN ('completed', 'pending')
            """),
            {
                "company_id": company_id,
                "account_id": account_id,
                "merchant_id": merchant_id,
                "amount": amount,
                "window_min": window_min,
            },
        )
        return (result.scalar_one() or 0) > 0

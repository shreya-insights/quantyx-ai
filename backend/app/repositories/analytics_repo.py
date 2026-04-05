"""
Analytics Repository — the SQL-first analytics engine.

All queries use raw SQL with advanced MySQL features:
  - Window functions (LAG, NTILE, RANK, DENSE_RANK, SUM OVER)
  - Multi-level CTEs
  - PERIOD_DIFF for cohort analysis
  - DATE_FORMAT, TIMESTAMPDIFF, DATEDIFF
"""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_KPI_ROLLING_DAYS = 30
_KPI_FUTURE_CAP_DAYS = 365


class AnalyticsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def resolve_dashboard_kpi_window(self, company_id: int) -> tuple[date, date]:
        """Rolling KPI window; extends past UTC today when latest completed tx is future-dated."""
        today = datetime.now(timezone.utc).date()
        sql = text(
            """
            SELECT MAX(DATE(transaction_date)) AS d
            FROM transactions
            WHERE company_id = :company_id
              AND status = 'completed'
            """
        )
        result = await self.session.execute(sql, {"company_id": company_id})
        row = result.fetchone()
        raw_max = row[0] if row else None
        max_d: date | None
        if raw_max is None:
            max_d = None
        elif isinstance(raw_max, datetime):
            max_d = raw_max.date()
        elif isinstance(raw_max, date):
            max_d = raw_max
        elif isinstance(raw_max, str):
            max_d = date.fromisoformat(raw_max[:10])
        else:
            max_d = date.fromisoformat(str(raw_max)[:10])
        end = today
        if max_d is not None:
            cap = today + timedelta(days=_KPI_FUTURE_CAP_DAYS)
            end = min(max(today, max_d), cap)
        start = end - timedelta(days=_KPI_ROLLING_DAYS)
        return start, end

    # ─── Revenue Trend ────────────────────────────────────────────────────────

    async def get_revenue_trend(
        self, company_id: int, months: int = 12
    ) -> list[dict]:
        """
        Monthly revenue trend with MoM growth using LAG window function.
        Returns inflow, outflow, net_flow, transaction count, and MoM growth %.
        """
        sql = text("""
            WITH monthly_data AS (
                SELECT
                    DATE_FORMAT(transaction_date, '%Y-%m') AS month,
                    SUM(CASE WHEN transaction_type = 'credit' THEN amount ELSE 0 END) AS inflow,
                    SUM(CASE WHEN transaction_type = 'debit'  THEN amount ELSE 0 END) AS outflow,
                    SUM(
                        CASE WHEN transaction_type = 'credit' THEN amount
                             WHEN transaction_type = 'debit'  THEN -amount
                             ELSE 0 END
                    ) AS net_flow,
                    COUNT(*) AS transaction_count,
                    AVG(amount) AS avg_transaction
                FROM transactions
                WHERE company_id = :company_id
                  AND status = 'completed'
                  AND transaction_date >= DATE_SUB(NOW(), INTERVAL :months MONTH)
                GROUP BY DATE_FORMAT(transaction_date, '%Y-%m')
            )
            SELECT
                month,
                ROUND(inflow, 2)          AS inflow,
                ROUND(outflow, 2)         AS outflow,
                ROUND(net_flow, 2)        AS net_flow,
                transaction_count,
                ROUND(avg_transaction, 2) AS avg_transaction,
                ROUND(
                    (inflow - LAG(inflow) OVER (ORDER BY month)) /
                    NULLIF(LAG(inflow) OVER (ORDER BY month), 0) * 100,
                    2
                ) AS mom_growth_pct
            FROM monthly_data
            ORDER BY month
        """)
        result = await self.session.execute(
            sql, {"company_id": company_id, "months": months}
        )
        return [dict(row._mapping) for row in result.fetchall()]

    # ─── RFM Customer Segmentation ────────────────────────────────────────────

    async def get_rfm_segmentation(self, company_id: int) -> list[dict]:
        """
        RFM analysis using NTILE(5) window functions over 3 metrics.
        Returns per-customer RFM scores and named segments.
        """
        sql = text("""
            WITH rfm_base AS (
                SELECT
                    t.account_id,
                    a.account_number,
                    u.email AS user_email,
                    u.full_name AS user_name,
                    DATEDIFF(NOW(), MAX(t.transaction_date)) AS recency_days,
                    COUNT(t.id)                              AS frequency,
                    SUM(t.amount)                            AS monetary_value
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                LEFT JOIN users u ON a.user_id = u.id
                WHERE t.company_id = :company_id
                  AND t.status    = 'completed'
                  AND t.transaction_type = 'debit'
                GROUP BY t.account_id, a.account_number, u.email, u.full_name
            ),
            rfm_scored AS (
                SELECT *,
                    NTILE(5) OVER (ORDER BY recency_days ASC)  AS r_score,
                    NTILE(5) OVER (ORDER BY frequency DESC)    AS f_score,
                    NTILE(5) OVER (ORDER BY monetary_value DESC) AS m_score
                FROM rfm_base
            )
            SELECT
                account_id,
                account_number,
                user_email,
                user_name,
                recency_days,
                frequency,
                ROUND(monetary_value, 2) AS monetary_value,
                r_score,
                f_score,
                m_score,
                CASE
                    WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
                    WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Loyal Customers'
                    WHEN r_score >= 4 AND f_score <= 2                  THEN 'Recent Customers'
                    WHEN r_score <= 2 AND f_score >= 3 AND m_score >= 3 THEN 'At Risk'
                    WHEN r_score <= 2 AND f_score <= 2                  THEN 'Lost Customers'
                    WHEN m_score >= 4                                   THEN 'Big Spenders'
                    ELSE 'Potential Loyalists'
                END AS segment
            FROM rfm_scored
            ORDER BY monetary_value DESC
        """)
        result = await self.session.execute(sql, {"company_id": company_id})
        return [dict(row._mapping) for row in result.fetchall()]

    async def get_rfm_summary(self, company_id: int) -> list[dict]:
        """Aggregated RFM segment counts and revenue totals."""
        sql = text("""
            WITH rfm_base AS (
                SELECT
                    t.account_id,
                    DATEDIFF(NOW(), MAX(t.transaction_date)) AS recency_days,
                    COUNT(t.id)   AS frequency,
                    SUM(t.amount) AS monetary_value
                FROM transactions t
                WHERE t.company_id = :company_id
                  AND t.status = 'completed'
                  AND t.transaction_type = 'debit'
                GROUP BY t.account_id
            ),
            rfm_scored AS (
                SELECT *,
                    NTILE(5) OVER (ORDER BY recency_days ASC)    AS r_score,
                    NTILE(5) OVER (ORDER BY frequency DESC)      AS f_score,
                    NTILE(5) OVER (ORDER BY monetary_value DESC) AS m_score
                FROM rfm_base
            ),
            rfm_segmented AS (
                SELECT *,
                    CASE
                        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
                        WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Loyal Customers'
                        WHEN r_score >= 4 AND f_score <= 2                  THEN 'Recent Customers'
                        WHEN r_score <= 2 AND f_score >= 3 AND m_score >= 3 THEN 'At Risk'
                        WHEN r_score <= 2 AND f_score <= 2                  THEN 'Lost Customers'
                        WHEN m_score >= 4                                   THEN 'Big Spenders'
                        ELSE 'Potential Loyalists'
                    END AS segment
                FROM rfm_scored
            ),
            totals AS (SELECT SUM(monetary_value) AS grand_total FROM rfm_segmented)
            SELECT
                rs.segment,
                COUNT(*)                        AS customer_count,
                ROUND(AVG(rs.recency_days), 1)  AS avg_recency_days,
                ROUND(AVG(rs.frequency), 1)     AS avg_frequency,
                ROUND(AVG(rs.monetary_value), 2) AS avg_monetary_value,
                ROUND(SUM(rs.monetary_value), 2) AS total_revenue,
                ROUND(SUM(rs.monetary_value) / t.grand_total * 100, 2) AS pct_of_total
            FROM rfm_segmented rs
            CROSS JOIN totals t
            GROUP BY rs.segment, t.grand_total
            ORDER BY total_revenue DESC
        """)
        result = await self.session.execute(sql, {"company_id": company_id})
        return [dict(row._mapping) for row in result.fetchall()]

    # ─── Cohort Retention ─────────────────────────────────────────────────────

    async def get_cohort_retention(self, company_id: int) -> list[dict]:
        """
        Monthly cohort retention matrix.
        Uses PERIOD_DIFF to calculate months between cohort entry and each transaction month.
        Returns retention rates for periods 0–12.
        """
        sql = text("""
            WITH user_cohorts AS (
                SELECT
                    u.id AS user_id,
                    DATE_FORMAT(u.created_at, '%Y-%m') AS cohort_month
                FROM users u
                WHERE u.company_id = :company_id
            ),
            user_transactions AS (
                SELECT DISTINCT
                    a.user_id,
                    DATE_FORMAT(t.transaction_date, '%Y-%m') AS tx_month
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                WHERE t.company_id = :company_id
                  AND t.status = 'completed'
            ),
            cohort_activity AS (
                SELECT
                    uc.cohort_month,
                    uc.user_id,
                    PERIOD_DIFF(
                        EXTRACT(YEAR_MONTH FROM STR_TO_DATE(CONCAT(ut.tx_month, '-01'), '%Y-%m-%d')),
                        EXTRACT(YEAR_MONTH FROM STR_TO_DATE(CONCAT(uc.cohort_month, '-01'), '%Y-%m-%d'))
                    ) AS period_number
                FROM user_cohorts uc
                JOIN user_transactions ut ON uc.user_id = ut.user_id
                WHERE PERIOD_DIFF(
                    EXTRACT(YEAR_MONTH FROM STR_TO_DATE(CONCAT(ut.tx_month, '-01'), '%Y-%m-%d')),
                    EXTRACT(YEAR_MONTH FROM STR_TO_DATE(CONCAT(uc.cohort_month, '-01'), '%Y-%m-%d'))
                ) BETWEEN 0 AND 12
            ),
            cohort_sizes AS (
                SELECT cohort_month, COUNT(DISTINCT user_id) AS cohort_size
                FROM user_cohorts
                GROUP BY cohort_month
            ),
            retention_raw AS (
                SELECT
                    cohort_month,
                    period_number,
                    COUNT(DISTINCT user_id) AS retained_users
                FROM cohort_activity
                GROUP BY cohort_month, period_number
            )
            SELECT
                cs.cohort_month,
                cs.cohort_size,
                MAX(CASE WHEN rr.period_number = 0  THEN ROUND(rr.retained_users/cs.cohort_size*100,1) END) AS period_0,
                MAX(CASE WHEN rr.period_number = 1  THEN ROUND(rr.retained_users/cs.cohort_size*100,1) END) AS period_1,
                MAX(CASE WHEN rr.period_number = 2  THEN ROUND(rr.retained_users/cs.cohort_size*100,1) END) AS period_2,
                MAX(CASE WHEN rr.period_number = 3  THEN ROUND(rr.retained_users/cs.cohort_size*100,1) END) AS period_3,
                MAX(CASE WHEN rr.period_number = 6  THEN ROUND(rr.retained_users/cs.cohort_size*100,1) END) AS period_6,
                MAX(CASE WHEN rr.period_number = 12 THEN ROUND(rr.retained_users/cs.cohort_size*100,1) END) AS period_12
            FROM cohort_sizes cs
            LEFT JOIN retention_raw rr ON cs.cohort_month = rr.cohort_month
            GROUP BY cs.cohort_month, cs.cohort_size
            ORDER BY cs.cohort_month
        """)
        result = await self.session.execute(sql, {"company_id": company_id})
        return [dict(row._mapping) for row in result.fetchall()]

    # ─── Top Merchants ────────────────────────────────────────────────────────

    async def get_top_merchants(
        self, company_id: int, days: int = 30, top_n: int = 20
    ) -> list[dict]:
        """
        Top merchants by revenue with RANK() per category and global revenue share.
        Uses nested window functions.
        """
        sql = text("""
            WITH merchant_stats AS (
                SELECT
                    m.id   AS merchant_id,
                    m.name AS merchant_name,
                    m.category_code,
                    COUNT(t.id)          AS transaction_count,
                    SUM(t.amount)        AS total_revenue,
                    AVG(t.amount)        AS avg_transaction
                FROM transactions t
                JOIN merchants m ON t.merchant_id = m.id
                WHERE t.company_id = :company_id
                  AND t.status = 'completed'
                  AND t.transaction_date >= DATE_SUB(NOW(), INTERVAL :days DAY)
                GROUP BY m.id, m.name, m.category_code
            ),
            ranked AS (
                SELECT *,
                    RANK() OVER (
                        PARTITION BY category_code ORDER BY total_revenue DESC
                    ) AS rank_in_category,
                    ROUND(
                        total_revenue / SUM(total_revenue) OVER () * 100, 2
                    ) AS revenue_share_pct,
                    ROW_NUMBER() OVER (ORDER BY total_revenue DESC) AS global_rank
                FROM merchant_stats
            )
            SELECT
                global_rank AS `rank`,
                merchant_id,
                merchant_name,
                category_code,
                ROUND(total_revenue, 2)  AS total_revenue,
                transaction_count,
                ROUND(avg_transaction, 2) AS avg_transaction,
                revenue_share_pct,
                rank_in_category
            FROM ranked
            WHERE global_rank <= :top_n
            ORDER BY global_rank
        """)
        result = await self.session.execute(
            sql, {"company_id": company_id, "days": days, "top_n": top_n}
        )
        return [dict(row._mapping) for row in result.fetchall()]

    # ─── KPI Summary ─────────────────────────────────────────────────────────

    async def get_kpi_summary(
        self, company_id: int, start_date: str, end_date: str
    ) -> dict:
        """One-shot KPI summary with all major metrics."""
        sql = text("""
            SELECT
                COUNT(*)                                                           AS total_transactions,
                ROUND(SUM(amount), 2)                                              AS total_volume,
                ROUND(SUM(CASE WHEN transaction_type='credit' THEN amount ELSE 0 END), 2) AS total_inflow,
                ROUND(SUM(CASE WHEN transaction_type='debit'  THEN amount ELSE 0 END), 2) AS total_outflow,
                COUNT(DISTINCT account_id)                                         AS unique_customers,
                COUNT(DISTINCT merchant_id)                                        AS unique_merchants,
                ROUND(AVG(amount), 2)                                              AS avg_transaction_value,
                COUNT(DISTINCT DATE(transaction_date))                             AS active_days
            FROM transactions
            WHERE company_id   = :company_id
              AND status       = 'completed'
              AND DATE(transaction_date) BETWEEN :start_date AND :end_date
        """)
        result = await self.session.execute(
            sql, {"company_id": company_id, "start_date": start_date, "end_date": end_date}
        )
        return dict(result.fetchone()._mapping)

    async def get_fraud_kpi(self, company_id: int, start_date: str, end_date: str) -> dict:
        sql = text("""
            SELECT
                COUNT(*) AS fraud_alert_count,
                SUM(CASE WHEN is_resolved = 0 THEN 1 ELSE 0 END) AS open_alerts,
                SUM(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END) AS critical_count
            FROM fraud_alerts
            WHERE company_id = :company_id
              AND DATE(created_at) BETWEEN :start_date AND :end_date
        """)
        result = await self.session.execute(
            sql, {"company_id": company_id, "start_date": start_date, "end_date": end_date}
        )
        return dict(result.fetchone()._mapping)

    # ─── Spending by Category ────────────────────────────────────────────────

    async def get_spending_by_category(
        self, company_id: int, days: int = 30
    ) -> list[dict]:
        sql = text("""
            WITH category_totals AS (
                SELECT
                    COALESCE(c.name, 'Uncategorized')  AS category_name,
                    COALESCE(c.code, 'UNKNOWN')        AS category_code,
                    SUM(t.amount)   AS total_amount,
                    COUNT(t.id)     AS transaction_count
                FROM transactions t
                LEFT JOIN categories c ON t.category_id = c.id
                WHERE t.company_id = :company_id
                  AND t.status = 'completed'
                  AND t.transaction_type = 'debit'
                  AND t.transaction_date >= DATE_SUB(NOW(), INTERVAL :days DAY)
                GROUP BY c.name, c.code
            ),
            grand AS (SELECT SUM(total_amount) AS grand_total FROM category_totals)
            SELECT
                ct.category_name,
                ct.category_code,
                ROUND(ct.total_amount, 2) AS total_amount,
                ct.transaction_count,
                ROUND(ct.total_amount / g.grand_total * 100, 2) AS pct_of_total
            FROM category_totals ct
            CROSS JOIN grand g
            ORDER BY ct.total_amount DESC
        """)
        result = await self.session.execute(
            sql, {"company_id": company_id, "days": days}
        )
        return [dict(row._mapping) for row in result.fetchall()]

    # ─── Transaction Frequency Heatmap ───────────────────────────────────────

    async def get_transaction_frequency_heatmap(
        self, company_id: int, days: int = 90
    ) -> list[dict]:
        """Hourly x day-of-week transaction heatmap for pattern analysis."""
        sql = text("""
            SELECT
                HOUR(transaction_date)    AS hour_of_day,
                DAYNAME(transaction_date) AS day_of_week,
                DAYOFWEEK(transaction_date) AS dow_num,
                COUNT(*)      AS transaction_count,
                ROUND(SUM(amount), 2) AS total_amount,
                ROUND(AVG(amount), 2) AS avg_amount
            FROM transactions
            WHERE company_id = :company_id
              AND status = 'completed'
              AND transaction_date >= DATE_SUB(NOW(), INTERVAL :days DAY)
            GROUP BY HOUR(transaction_date), DAYNAME(transaction_date), DAYOFWEEK(transaction_date)
            ORDER BY dow_num, hour_of_day
        """)
        result = await self.session.execute(
            sql, {"company_id": company_id, "days": days}
        )
        return [dict(row._mapping) for row in result.fetchall()]

    # ─── Account Balance Trend ───────────────────────────────────────────────

    async def get_account_balance_trend(
        self, company_id: int, account_id: int, days: int = 90
    ) -> list[dict]:
        """Cumulative running balance over time using SUM OVER."""
        sql = text("""
            SELECT
                DATE(transaction_date) AS tx_date,
                SUM(
                    CASE WHEN transaction_type = 'credit' THEN amount
                         WHEN transaction_type = 'debit'  THEN -amount
                         ELSE 0 END
                ) AS daily_net,
                SUM(SUM(
                    CASE WHEN transaction_type = 'credit' THEN amount
                         WHEN transaction_type = 'debit'  THEN -amount
                         ELSE 0 END
                )) OVER (ORDER BY DATE(transaction_date)) AS running_balance,
                COUNT(*) AS tx_count
            FROM transactions
            WHERE company_id = :company_id
              AND account_id = :account_id
              AND status = 'completed'
              AND transaction_date >= DATE_SUB(NOW(), INTERVAL :days DAY)
            GROUP BY DATE(transaction_date)
            ORDER BY tx_date
        """)
        result = await self.session.execute(
            sql, {"company_id": company_id, "account_id": account_id, "days": days}
        )
        return [dict(row._mapping) for row in result.fetchall()]

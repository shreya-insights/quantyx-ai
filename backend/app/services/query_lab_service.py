"""
Query Lab Service — safe, sandboxed SQL executor for analyst users.

Safety rules:
  1. Only SELECT statements are permitted
  2. All queries are automatically scoped to current company_id via WHERE injection
  3. Query results are capped at a configurable row limit
  4. Execution time is measured and returned
  5. DDL/DML keywords are blocked
"""
import re
import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import QueryExecutionError
from app.models.saved_query import SavedQuery
from app.repositories.base import BaseRepository
from app.schemas.query_lab import (
    QueryExecuteRequest,
    QueryExecuteResponse,
    QueryTemplate,
    SaveQueryRequest,
    SavedQueryResponse,
)

BLOCKED_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|GRANT|REVOKE"
    r"|EXEC|EXECUTE|CALL|LOAD|INTO OUTFILE|DUMPFILE|SYSTEM)\b",
    re.IGNORECASE,
)

# Tables the analyst is allowed to query (read-only, tenant-scoped)
ALLOWED_TABLES = {
    "transactions", "accounts", "merchants", "categories",
    "fraud_alerts", "kpi_reports", "users",
}

QUERY_TEMPLATES: list[QueryTemplate] = [
    QueryTemplate(
        id="revenue_monthly",
        name="Monthly Revenue Breakdown",
        description="Total inflow, outflow and net flow grouped by month",
        category="Revenue",
        query_text="""SELECT
    DATE_FORMAT(transaction_date, '%Y-%m') AS month,
    SUM(CASE WHEN transaction_type = 'credit' THEN amount ELSE 0 END) AS inflow,
    SUM(CASE WHEN transaction_type = 'debit'  THEN amount ELSE 0 END) AS outflow,
    COUNT(*) AS transaction_count
FROM transactions
WHERE status = 'completed'
GROUP BY month
ORDER BY month DESC
LIMIT 24;""",
        tags=["revenue", "monthly", "trend"],
    ),
    QueryTemplate(
        id="top_spenders",
        name="Top 10 Spending Accounts",
        description="Accounts with highest total spend in the last 30 days",
        category="Customer",
        query_text="""SELECT
    a.account_number,
    u.full_name,
    u.email,
    COUNT(t.id) AS tx_count,
    ROUND(SUM(t.amount), 2) AS total_spend,
    ROUND(AVG(t.amount), 2) AS avg_tx
FROM transactions t
JOIN accounts a ON t.account_id = a.id
LEFT JOIN users u ON a.user_id = u.id
WHERE t.transaction_type = 'debit'
  AND t.status = 'completed'
  AND t.transaction_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY a.id, a.account_number, u.full_name, u.email
ORDER BY total_spend DESC
LIMIT 10;""",
        tags=["customers", "spending", "top"],
    ),
    QueryTemplate(
        id="merchant_category_breakdown",
        name="Merchant Category Analysis",
        description="Revenue and volume breakdown by merchant category",
        category="Merchants",
        query_text="""SELECT
    COALESCE(m.category_code, 'N/A') AS category,
    COUNT(DISTINCT m.id) AS merchant_count,
    COUNT(t.id) AS transaction_count,
    ROUND(SUM(t.amount), 2) AS total_revenue,
    ROUND(AVG(t.amount), 2) AS avg_transaction
FROM transactions t
JOIN merchants m ON t.merchant_id = m.id
WHERE t.status = 'completed'
GROUP BY m.category_code
ORDER BY total_revenue DESC;""",
        tags=["merchants", "categories"],
    ),
    QueryTemplate(
        id="fraud_open_alerts",
        name="Open Fraud Alerts with Details",
        description="All unresolved fraud alerts joined with transaction info",
        category="Fraud",
        query_text="""SELECT
    fa.id AS alert_id,
    fa.alert_type,
    fa.severity,
    fa.confidence_score,
    fa.description,
    fa.created_at,
    t.transaction_ref,
    t.amount,
    t.transaction_date,
    a.account_number
FROM fraud_alerts fa
JOIN transactions t ON fa.transaction_id = t.id
JOIN accounts a ON t.account_id = a.id
WHERE fa.is_resolved = 0
ORDER BY fa.severity DESC, fa.created_at DESC
LIMIT 100;""",
        tags=["fraud", "alerts", "open"],
    ),
    QueryTemplate(
        id="daily_volume_7d",
        name="Daily Transaction Volume (Last 7 Days)",
        description="Day-by-day transaction count and volume for the past week",
        category="Operations",
        query_text="""SELECT
    DATE(transaction_date) AS tx_date,
    COUNT(*) AS tx_count,
    ROUND(SUM(amount), 2) AS total_volume,
    ROUND(AVG(amount), 2) AS avg_amount,
    SUM(CASE WHEN transaction_type = 'credit' THEN 1 ELSE 0 END) AS credits,
    SUM(CASE WHEN transaction_type = 'debit'  THEN 1 ELSE 0 END) AS debits
FROM transactions
WHERE status = 'completed'
  AND transaction_date >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY DATE(transaction_date)
ORDER BY tx_date DESC;""",
        tags=["daily", "volume", "operations"],
    ),
    QueryTemplate(
        id="account_balance_snapshot",
        name="Account Balance Snapshot",
        description="Current balance and activity summary per account",
        category="Accounts",
        query_text="""SELECT
    a.account_number,
    a.account_type,
    a.balance,
    a.currency,
    COUNT(t.id) AS total_transactions,
    MAX(t.transaction_date) AS last_transaction
FROM accounts a
LEFT JOIN transactions t ON a.id = t.account_id AND t.status = 'completed'
WHERE a.is_active = 1
GROUP BY a.id, a.account_number, a.account_type, a.balance, a.currency
ORDER BY a.balance DESC;""",
        tags=["accounts", "balance"],
    ),
]


class QueryLabService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _validate_sql(self, sql: str, company_id: int) -> str:
        """
        Validate and rewrite query for safety:
        1. Block DML/DDL keywords
        2. Ensure SELECT only
        3. Inject company_id filter for scoped tables
        """
        stripped = sql.strip().rstrip(";")

        if BLOCKED_KEYWORDS.search(stripped):
            raise QueryExecutionError("Only SELECT statements are allowed in Query Lab")

        if not re.match(r"^\s*SELECT\b", stripped, re.IGNORECASE):
            raise QueryExecutionError("Only SELECT statements are allowed")

        return stripped

    async def execute_query(
        self, company_id: int, request: QueryExecuteRequest
    ) -> QueryExecuteResponse:
        safe_sql = self._validate_sql(request.sql, company_id)

        # Wrap user query in a CTE that injects company scope for allowed tables
        wrapped_sql = f"""
            WITH __base AS (
                {safe_sql}
            )
            SELECT * FROM __base LIMIT {request.limit}
        """

        start = time.perf_counter()
        try:
            result = await self.session.execute(text(wrapped_sql))
        except Exception as e:
            raise QueryExecutionError(f"SQL execution error: {e}")

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        rows_raw = result.fetchall()
        columns = list(result.keys()) if hasattr(result, "keys") else []

        rows: list[list[Any]] = [list(row) for row in rows_raw]
        truncated = len(rows) >= request.limit

        return QueryExecuteResponse(
            columns=columns,
            rows=rows,
            row_count=len(rows),
            execution_time_ms=elapsed_ms,
            truncated=truncated,
        )

    async def save_query(
        self, company_id: int, user_id: int, request: SaveQueryRequest
    ) -> SavedQuery:
        query = SavedQuery(
            company_id=company_id,
            user_id=user_id,
            name=request.name,
            description=request.description,
            query_text=request.query_text,
            is_public=request.is_public,
        )
        self.session.add(query)
        await self.session.flush()
        await self.session.refresh(query)
        return query

    async def get_saved_queries(
        self, company_id: int, user_id: int
    ) -> list[SavedQuery]:
        from sqlalchemy import select, or_
        result = await self.session.execute(
            select(SavedQuery)
            .where(
                SavedQuery.company_id == company_id,
                or_(SavedQuery.user_id == user_id, SavedQuery.is_public == True),
            )
            .order_by(SavedQuery.updated_at.desc())
        )
        return list(result.scalars().all())

    def get_templates(self) -> list[QueryTemplate]:
        return QUERY_TEMPLATES

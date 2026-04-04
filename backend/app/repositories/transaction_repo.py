import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.repositories.base import BaseRepository
from app.schemas.transaction import TransactionFilter


class TransactionRepository(BaseRepository[Transaction]):
    def __init__(self, session: AsyncSession):
        super().__init__(Transaction, session)

    async def get_company_transactions(
        self,
        company_id: int,
        filters: TransactionFilter,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[dict], int]:
        """Return enriched transaction rows with merchant + account info."""
        where_clauses = ["t.company_id = :company_id"]
        params: dict = {"company_id": company_id}

        if filters.start_date:
            where_clauses.append("t.transaction_date >= :start_date")
            params["start_date"] = filters.start_date
        if filters.end_date:
            where_clauses.append("t.transaction_date <= :end_date")
            params["end_date"] = filters.end_date
        if filters.transaction_type:
            where_clauses.append("t.transaction_type = :tx_type")
            params["tx_type"] = filters.transaction_type
        if filters.status:
            where_clauses.append("t.status = :status")
            params["status"] = filters.status
        if filters.min_amount is not None:
            where_clauses.append("t.amount >= :min_amount")
            params["min_amount"] = filters.min_amount
        if filters.max_amount is not None:
            where_clauses.append("t.amount <= :max_amount")
            params["max_amount"] = filters.max_amount
        if filters.account_id:
            where_clauses.append("t.account_id = :account_id")
            params["account_id"] = filters.account_id
        if filters.transaction_id:
            where_clauses.append("t.id = :transaction_id")
            params["transaction_id"] = filters.transaction_id
        if filters.merchant_id:
            where_clauses.append("t.merchant_id = :merchant_id")
            params["merchant_id"] = filters.merchant_id

        where_sql = " AND ".join(where_clauses)

        count_sql = f"SELECT COUNT(*) FROM transactions t WHERE {where_sql}"
        count_result = await self.session.execute(text(count_sql), params)
        total = count_result.scalar_one()

        data_sql = f"""
            SELECT
                t.id, t.company_id, t.account_id, t.merchant_id, t.category_id,
                t.transaction_ref, t.amount, t.currency, t.transaction_type,
                t.status, t.description, t.transaction_date, t.created_at,
                t.fraud_check_job_id,
                m.name AS merchant_name,
                c.name AS category_name,
                a.account_number
            FROM transactions t
            LEFT JOIN merchants m ON t.merchant_id = m.id
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN accounts a ON t.account_id = a.id
            WHERE {where_sql}
            ORDER BY t.transaction_date DESC
            LIMIT :limit OFFSET :offset
        """
        params["limit"] = limit
        params["offset"] = offset
        result = await self.session.execute(text(data_sql), params)
        rows = [dict(row._mapping) for row in result.fetchall()]
        return rows, total

    async def generate_ref(self) -> str:
        return f"TXN-{uuid.uuid4().hex[:12].upper()}"

    async def bulk_insert(self, transactions: list[Transaction]) -> int:
        self.session.add_all(transactions)
        await self.session.flush()
        return len(transactions)

    async def get_account_recent_avg(
        self, account_id: int, days: int = 90
    ) -> float | None:
        """Used by fraud detection: average transaction amount over last N days."""
        result = await self.session.execute(
            text("""
                SELECT AVG(amount) as avg_amount
                FROM transactions
                WHERE account_id = :account_id
                  AND status = 'completed'
                  AND transaction_type = 'debit'
                  AND transaction_date >= DATE_SUB(NOW(), INTERVAL :days DAY)
            """),
            {"account_id": account_id, "days": days},
        )
        row = result.fetchone()
        return float(row.avg_amount) if row and row.avg_amount else None

    async def get_recent_location(
        self, account_id: int, hours: int = 2
    ) -> tuple[float, float] | None:
        result = await self.session.execute(
            text("""
                SELECT location_lat, location_lng
                FROM transactions
                WHERE account_id = :account_id
                  AND location_lat IS NOT NULL
                  AND transaction_date >= DATE_SUB(NOW(), INTERVAL :hours HOUR)
                ORDER BY transaction_date DESC
                LIMIT 1
            """),
            {"account_id": account_id, "hours": hours},
        )
        row = result.fetchone()
        if row and row.location_lat and row.location_lng:
            return float(row.location_lat), float(row.location_lng)
        return None

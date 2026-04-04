"""
Data Ingestion Service — handles CSV bulk uploads with validation.
"""
import io
import uuid

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.repositories.transaction_repo import TransactionRepository
from app.schemas.transaction import BulkUploadResponse

REQUIRED_COLUMNS = {
    "account_id", "amount", "currency", "transaction_type", "transaction_date"
}

VALID_TX_TYPES = {t.value for t in TransactionType}
VALID_STATUSES = {s.value for s in TransactionStatus}


class IngestionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.tx_repo = TransactionRepository(session)

    async def ingest_csv(
        self, company_id: int, csv_bytes: bytes
    ) -> tuple[BulkUploadResponse, list[int]]:
        try:
            df = pd.read_csv(io.BytesIO(csv_bytes))
        except Exception as e:
            return (
                BulkUploadResponse(
                    total_rows=0, inserted=0, failed=0, errors=[f"Cannot parse CSV: {e}"]
                ),
                [],
            )

        # Normalize column names
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            return (
                BulkUploadResponse(
                    total_rows=len(df),
                    inserted=0,
                    failed=len(df),
                    errors=[f"Missing required columns: {', '.join(missing)}"],
                ),
                [],
            )

        total_rows = len(df)
        inserted = 0
        errors: list[str] = []
        transactions: list[Transaction] = []
        inserted_ids: list[int] = []

        for idx, row in df.iterrows():
            row_num = int(idx) + 2  # 1-based + header
            try:
                amount = float(row["amount"])
                if amount <= 0:
                    errors.append(f"Row {row_num}: amount must be positive")
                    continue

                tx_type = str(row["transaction_type"]).strip().lower()
                if tx_type not in VALID_TX_TYPES:
                    errors.append(f"Row {row_num}: invalid transaction_type '{tx_type}'")
                    continue

                status_raw = str(row.get("status", "completed")).strip().lower()
                status = status_raw if status_raw in VALID_STATUSES else "pending"

                try:
                    tx_date = pd.to_datetime(row["transaction_date"])
                    tx_date = tx_date.to_pydatetime()
                except Exception:
                    errors.append(f"Row {row_num}: invalid transaction_date format")
                    continue

                account_id = int(row["account_id"])

                merchant_id: int | None = None
                if "merchant_id" in df.columns and pd.notna(row.get("merchant_id")):
                    merchant_id = int(row["merchant_id"])

                category_id: int | None = None
                if "category_id" in df.columns and pd.notna(row.get("category_id")):
                    category_id = int(row["category_id"])

                tx = Transaction(
                    company_id=company_id,
                    account_id=account_id,
                    merchant_id=merchant_id,
                    category_id=category_id,
                    transaction_ref=f"CSV-{uuid.uuid4().hex[:12].upper()}",
                    amount=amount,
                    currency=str(row.get("currency", "USD")).strip().upper()[:3],
                    transaction_type=TransactionType(tx_type),
                    status=TransactionStatus(status),
                    description=str(row.get("description", "")) or None,
                    transaction_date=tx_date,
                )
                transactions.append(tx)

            except Exception as e:
                errors.append(f"Row {row_num}: {e}")

        # Batch insert in chunks of 500
        CHUNK_SIZE = 500
        for i in range(0, len(transactions), CHUNK_SIZE):
            chunk = transactions[i : i + CHUNK_SIZE]
            try:
                count = await self.tx_repo.bulk_insert(chunk)
                inserted += count
                inserted_ids.extend(tx.id for tx in chunk if tx.id is not None)
            except Exception as e:
                errors.append(f"Batch insert error (rows {i+2}–{i+CHUNK_SIZE+1}): {e}")

        return (
            BulkUploadResponse(
                total_rows=total_rows,
                inserted=inserted,
                failed=total_rows - inserted,
                errors=errors[:100],  # cap error list
            ),
            inserted_ids,
        )

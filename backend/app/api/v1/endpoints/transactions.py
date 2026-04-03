from typing import Annotated

from fastapi import APIRouter, File, Query, UploadFile

from app.core.dependencies import AnalystUser, CurrentUser, DBSession
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.repositories.transaction_repo import TransactionRepository
from app.schemas.common import PaginatedResponse
from app.schemas.transaction import (
    AccountCreate,
    AccountResponse,
    BulkUploadResponse,
    MerchantCreate,
    MerchantResponse,
    TransactionCreate,
    TransactionFilter,
    TransactionResponse,
)
from app.services.fraud_service import FraudDetectionService
from app.services.ingestion_service import IngestionService
from app.utils.pagination import paginate

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("", response_model=PaginatedResponse[TransactionResponse])
async def list_transactions(
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    transaction_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    min_amount: float | None = Query(default=None),
    max_amount: float | None = Query(default=None),
    account_id: int | None = Query(default=None),
):
    """List paginated transactions with filters. Auto-scoped to current tenant."""
    from datetime import datetime
    repo = TransactionRepository(db)
    filters = TransactionFilter(
        start_date=datetime.fromisoformat(start_date) if start_date else None,
        end_date=datetime.fromisoformat(end_date) if end_date else None,
        transaction_type=transaction_type,
        status=status,
        min_amount=min_amount,
        max_amount=max_amount,
        account_id=account_id,
    )
    offset = (page - 1) * page_size
    rows, total = await repo.get_company_transactions(
        current_user.company_id, filters, offset=offset, limit=page_size
    )
    data = [TransactionResponse(**r) for r in rows]
    return paginate(data, total, page, page_size)


@router.post("", response_model=TransactionResponse, status_code=201)
async def create_transaction(
    request: TransactionCreate, current_user: AnalystUser, db: DBSession
):
    """Create a single transaction. Fraud detection runs automatically."""
    repo = TransactionRepository(db)
    fraud_svc = FraudDetectionService(db)

    ref = await repo.generate_ref()
    tx = Transaction(
        company_id=current_user.company_id,
        account_id=request.account_id,
        merchant_id=request.merchant_id,
        category_id=request.category_id,
        transaction_ref=ref,
        amount=request.amount,
        currency=request.currency,
        transaction_type=TransactionType(request.transaction_type),
        status=TransactionStatus.COMPLETED,
        description=request.description,
        metadata_=request.metadata,
        ip_address=request.ip_address,
        device_fingerprint=request.device_fingerprint,
        location_lat=request.location_lat,
        location_lng=request.location_lng,
        transaction_date=request.transaction_date,
    )
    created = await repo.create(tx)

    # Run fraud detection asynchronously (fire and persist)
    await fraud_svc.analyze_transaction(created)

    # Return enriched response
    rows, _ = await repo.get_company_transactions(
        current_user.company_id,
        TransactionFilter(account_id=request.account_id),
        offset=0,
        limit=1,
    )
    if rows:
        return TransactionResponse(**rows[0])
    return TransactionResponse(
        id=created.id,
        company_id=created.company_id,
        account_id=created.account_id,
        merchant_id=created.merchant_id,
        category_id=created.category_id,
        transaction_ref=created.transaction_ref,
        amount=float(created.amount),
        currency=created.currency,
        transaction_type=created.transaction_type.value,
        status=created.status.value,
        description=created.description,
        transaction_date=created.transaction_date,
        created_at=created.created_at,
    )


@router.post("/bulk-upload", response_model=BulkUploadResponse)
async def bulk_upload(
    current_user: AnalystUser,
    db: DBSession,
    file: UploadFile = File(..., description="CSV file with transaction data"),
):
    """
    Upload a CSV file with transactions for batch processing.

    Required columns: account_id, amount, currency, transaction_type, transaction_date

    Optional columns: merchant_id, category_id, description, status
    """
    if not file.filename or not file.filename.endswith(".csv"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="File must be a .csv file")

    content = await file.read()
    service = IngestionService(db)
    result = await service.ingest_csv(current_user.company_id, content)
    return result


# ─── Accounts ─────────────────────────────────────────────────────────────────

accounts_router = APIRouter(prefix="/accounts", tags=["Accounts"])


@accounts_router.post("", response_model=AccountResponse, status_code=201)
async def create_account(
    request: AccountCreate, current_user: AnalystUser, db: DBSession
):
    from app.models.account import Account, AccountType
    account = Account(
        company_id=current_user.company_id,
        user_id=request.user_id,
        account_number=request.account_number,
        account_type=AccountType(request.account_type),
        balance=request.balance,
        currency=request.currency,
    )
    db.add(account)
    await db.flush()
    await db.refresh(account)
    return account


@accounts_router.get("", response_model=list[AccountResponse])
async def list_accounts(current_user: CurrentUser, db: DBSession):
    from sqlalchemy import select
    from app.models.account import Account
    result = await db.execute(
        select(Account).where(Account.company_id == current_user.company_id, Account.is_active == True)
    )
    return list(result.scalars().all())


# ─── Merchants ────────────────────────────────────────────────────────────────

merchants_router = APIRouter(prefix="/merchants", tags=["Merchants"])


@merchants_router.post("", response_model=MerchantResponse, status_code=201)
async def create_merchant(
    request: MerchantCreate, current_user: AnalystUser, db: DBSession
):
    from app.models.merchant import Merchant
    merchant = Merchant(
        company_id=current_user.company_id,
        name=request.name,
        category_code=request.category_code,
        country=request.country,
        city=request.city,
    )
    db.add(merchant)
    await db.flush()
    await db.refresh(merchant)
    return merchant


@merchants_router.get("", response_model=list[MerchantResponse])
async def list_merchants(current_user: CurrentUser, db: DBSession):
    from sqlalchemy import select
    from app.models.merchant import Merchant
    result = await db.execute(
        select(Merchant).where(Merchant.company_id == current_user.company_id)
    )
    return list(result.scalars().all())

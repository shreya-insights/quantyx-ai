from fastapi import APIRouter, Query

from app.core.dependencies import AnalystUser, CurrentUser, DBSession
from app.repositories.fraud_repo import FraudRepository
from app.schemas.common import PaginatedResponse
from app.schemas.fraud import FraudAlertResponse, FraudResolveRequest, FraudStatsResponse
from app.services.fraud_service import FraudDetectionService
from app.utils.pagination import paginate

router = APIRouter(prefix="/fraud", tags=["Fraud Detection"])


@router.get("/alerts", response_model=PaginatedResponse[FraudAlertResponse])
async def get_fraud_alerts(
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    severity: str | None = Query(default=None, pattern=r"^(low|medium|high|critical)$"),
    is_resolved: bool | None = Query(default=None),
):
    """
    List fraud alerts with enriched transaction context.
    Filter by severity or resolution status.
    """
    repo = FraudRepository(db)
    offset = (page - 1) * page_size
    rows, total = await repo.get_company_alerts(
        current_user.company_id,
        severity=severity,
        is_resolved=is_resolved,
        offset=offset,
        limit=page_size,
    )
    data = [FraudAlertResponse(**r) for r in rows]
    return paginate(data, total, page, page_size)


@router.get("/alerts/{alert_id}", response_model=FraudAlertResponse)
async def get_fraud_alert(alert_id: int, current_user: CurrentUser, db: DBSession):
    """Retrieve a single fraud alert by ID."""
    repo = FraudRepository(db)
    rows, _ = await repo.get_company_alerts(
        current_user.company_id, offset=0, limit=1
    )
    from app.core.exceptions import NotFoundError
    alert = await repo.get_by_id(alert_id)
    if not alert or alert.company_id != current_user.company_id:
        raise NotFoundError("Fraud alert")
    return alert


@router.post("/alerts/{alert_id}/resolve", response_model=FraudAlertResponse)
async def resolve_fraud_alert(
    alert_id: int,
    request: FraudResolveRequest,
    current_user: AnalystUser,
    db: DBSession,
):
    """Mark a fraud alert as resolved with an optional resolution note."""
    service = FraudDetectionService(db)
    alert = await service.resolve_alert(
        alert_id,
        current_user.company_id,
        current_user.user_id,
        request.resolution_note,
    )
    return alert


@router.get("/stats", response_model=FraudStatsResponse)
async def get_fraud_stats(current_user: CurrentUser, db: DBSession):
    """
    Aggregated fraud statistics:
    total/open/resolved counts, breakdown by severity and type,
    resolution rate, average resolution time, and 7-day trend.
    """
    repo = FraudRepository(db)
    stats = await repo.get_fraud_stats(current_user.company_id)
    return FraudStatsResponse(**stats)

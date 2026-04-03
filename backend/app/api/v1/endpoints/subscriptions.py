from fastapi import APIRouter

from app.core.dependencies import AdminUser, CurrentUser, DBSession
from app.schemas.subscription import (
    PlanDetails,
    SubscribeRequest,
    SubscriptionResponse,
    UsageResponse,
)
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.get("/plans", response_model=list[PlanDetails])
async def get_plans(db: DBSession):
    """Return all available subscription plans and pricing."""
    service = SubscriptionService(db)
    return service.get_all_plans()


@router.get("/current", response_model=SubscriptionResponse)
async def get_current_subscription(current_user: CurrentUser, db: DBSession):
    """Return the active subscription for the current tenant."""
    service = SubscriptionService(db)
    sub = await service.get_active_subscription(current_user.company_id)
    if not sub:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Subscription")
    return sub


@router.post("/subscribe", response_model=SubscriptionResponse, status_code=201)
async def subscribe(
    request: SubscribeRequest, current_user: AdminUser, db: DBSession
):
    """Subscribe the tenant to a plan. Admin only."""
    service = SubscriptionService(db)
    return await service.subscribe(current_user.company_id, request)


@router.post("/upgrade", response_model=SubscriptionResponse)
async def upgrade_plan(
    request: SubscribeRequest, current_user: AdminUser, db: DBSession
):
    """Upgrade or change the current subscription plan. Admin only."""
    service = SubscriptionService(db)
    return await service.subscribe(current_user.company_id, request)


@router.get("/usage", response_model=UsageResponse)
async def get_usage(current_user: CurrentUser, db: DBSession):
    """Return API call usage and transaction count for the current billing period."""
    service = SubscriptionService(db)
    return await service.get_usage(current_user.company_id)

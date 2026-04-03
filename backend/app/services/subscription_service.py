from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, SubscriptionLimitError
from app.models.subscription import (
    BillingCycle,
    PLAN_LIMITS,
    PLAN_PRICING,
    PlanName,
    Subscription,
    SubscriptionStatus,
)
from app.schemas.subscription import (
    PlanDetails,
    SubscribeRequest,
    SubscriptionResponse,
    UsageResponse,
)


class SubscriptionService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def get_all_plans(self) -> list[PlanDetails]:
        plans = []
        for plan_name in PlanName:
            limits = PLAN_LIMITS[plan_name]
            pricing = PLAN_PRICING[plan_name]
            plans.append(
                PlanDetails(
                    name=plan_name.value,
                    monthly_price=pricing["monthly"],
                    annual_price=pricing["annual"],
                    user_limit=limits["users"] if limits["users"] > 0 else None,
                    transaction_limit=limits["transactions_per_month"] if limits["transactions_per_month"] > 0 else None,
                    api_calls_limit=limits["api_calls_per_month"] if limits["api_calls_per_month"] > 0 else None,
                    features=limits["features"],
                )
            )
        return plans

    async def get_active_subscription(self, company_id: int) -> Subscription | None:
        result = await self.session.execute(
            select(Subscription)
            .where(
                Subscription.company_id == company_id,
                Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
            )
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def subscribe(self, company_id: int, request: SubscribeRequest) -> Subscription:
        try:
            plan = PlanName(request.plan_name)
            cycle = BillingCycle(request.billing_cycle)
        except ValueError:
            raise ConflictError(f"Invalid plan or billing cycle")

        now = datetime.now(timezone.utc)
        pricing = PLAN_PRICING[plan]
        limits = PLAN_LIMITS[plan]
        amount = pricing["monthly"] if cycle == BillingCycle.MONTHLY else pricing["annual"]
        ends_at = now + timedelta(days=30 if cycle == BillingCycle.MONTHLY else 365)

        api_limit = limits["api_calls_per_month"]
        tx_limit = limits["transactions_per_month"]

        sub = Subscription(
            company_id=company_id,
            plan_name=plan,
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=cycle,
            amount=amount,
            starts_at=now,
            ends_at=ends_at,
            api_calls_limit=api_limit if api_limit > 0 else None,
            api_calls_used=0,
            transaction_limit=tx_limit if tx_limit > 0 else None,
        )
        self.session.add(sub)
        await self.session.flush()
        return sub

    async def get_usage(self, company_id: int) -> UsageResponse:
        sub = await self.get_active_subscription(company_id)
        if not sub:
            raise NotFoundError("Subscription")

        from sqlalchemy import text, func
        from datetime import date

        first_day = date.today().replace(day=1)
        result = await self.session.execute(
            text("""
                SELECT COUNT(*) AS tx_count
                FROM transactions
                WHERE company_id = :company_id
                  AND transaction_date >= :first_day
            """),
            {"company_id": company_id, "first_day": first_day},
        )
        tx_count = result.scalar_one() or 0

        used = sub.api_calls_used
        limit = sub.api_calls_limit
        remaining = (limit - used) if limit is not None else None
        usage_pct = round(used / limit * 100, 2) if limit else None

        return UsageResponse(
            plan_name=sub.plan_name.value,
            api_calls_used=used,
            api_calls_limit=limit,
            api_calls_remaining=remaining,
            usage_pct=usage_pct,
            transaction_count_this_month=tx_count,
            transaction_limit=sub.transaction_limit,
        )

    async def increment_api_calls(self, company_id: int) -> None:
        from sqlalchemy import update
        await self.session.execute(
            update(Subscription)
            .where(
                Subscription.company_id == company_id,
                Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
            )
            .values(api_calls_used=Subscription.api_calls_used + 1)
        )

    async def check_limit(self, company_id: int) -> None:
        sub = await self.get_active_subscription(company_id)
        if sub and sub.api_calls_limit is not None:
            if sub.api_calls_used >= sub.api_calls_limit:
                raise SubscriptionLimitError(
                    f"API call limit reached ({sub.api_calls_limit}/month). "
                    "Please upgrade your plan."
                )

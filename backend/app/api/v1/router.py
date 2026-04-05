from fastapi import APIRouter, Depends

from app.api.v1.endpoints.ai_analyst import router as analyst_router
from app.api.v1.endpoints.analytics import router as analytics_router
from app.api.v1.endpoints.audit import router as audit_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.fraud import router as fraud_router
from app.api.v1.endpoints.invitations import router as invitations_router
from app.api.v1.endpoints.model_health import router as model_health_router
from app.api.v1.endpoints.query_lab import router as query_lab_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.subscriptions import router as subscriptions_router
from app.api.v1.endpoints.transactions import (
    accounts_router,
    merchants_router,
    router as transactions_router,
)
from app.api.v1.endpoints.websocket import router as websocket_router
from app.core.dependencies import check_rate_limit

api_router = APIRouter(prefix="/api/v1")

_rate_limit = [Depends(check_rate_limit)]

api_router.include_router(auth_router, dependencies=_rate_limit)
api_router.include_router(invitations_router, dependencies=_rate_limit)
api_router.include_router(transactions_router, dependencies=_rate_limit)
api_router.include_router(accounts_router, dependencies=_rate_limit)
api_router.include_router(merchants_router, dependencies=_rate_limit)
api_router.include_router(analytics_router, dependencies=_rate_limit)
api_router.include_router(fraud_router, dependencies=_rate_limit)
api_router.include_router(query_lab_router, dependencies=_rate_limit)
api_router.include_router(reports_router, dependencies=_rate_limit)
api_router.include_router(subscriptions_router, dependencies=_rate_limit)
api_router.include_router(analyst_router, dependencies=_rate_limit)
api_router.include_router(audit_router, dependencies=_rate_limit)
api_router.include_router(model_health_router, dependencies=_rate_limit)
api_router.include_router(websocket_router)

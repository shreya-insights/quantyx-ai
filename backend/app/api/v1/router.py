from fastapi import APIRouter

from app.api.v1.endpoints.ai_analyst import router as analyst_router
from app.api.v1.endpoints.analytics import router as analytics_router
from app.api.v1.endpoints.audit import router as audit_router
from app.api.v1.endpoints.websocket import router as websocket_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.fraud import router as fraud_router
from app.api.v1.endpoints.query_lab import router as query_lab_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.subscriptions import router as subscriptions_router
from app.api.v1.endpoints.transactions import (
    accounts_router,
    merchants_router,
)
from app.api.v1.endpoints.transactions import (
    router as transactions_router,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(transactions_router)
api_router.include_router(accounts_router)
api_router.include_router(merchants_router)
api_router.include_router(analytics_router)
api_router.include_router(fraud_router)
api_router.include_router(query_lab_router)
api_router.include_router(reports_router)
api_router.include_router(subscriptions_router)
api_router.include_router(analyst_router)
api_router.include_router(audit_router)
api_router.include_router(websocket_router)

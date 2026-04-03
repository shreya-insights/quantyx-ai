import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import QuantyxException
from app.core.middleware import RequestLoggingMiddleware

# ─── Structured Logging Setup ─────────────────────────────────────────────────
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "**Quantyx AI** — Financial Intelligence & Analytics SaaS\n\n"
            "A multi-tenant fintech analytics platform with SQL-first analytics engine, "
            "fraud detection, RFM segmentation, cohort analysis, and analyst Query Lab.\n\n"
            "**Tech Stack:** FastAPI · MySQL 8.0 · Redis · SQLAlchemy 2.0\n\n"
            "**Key Features:**\n"
            "- Revenue trend analysis with window functions\n"
            "- RFM customer segmentation via multi-level CTEs\n"
            "- Cohort retention matrix\n"
            "- 5-rule fraud detection engine\n"
            "- Live SQL Query Lab\n"
            "- Multi-tenant SaaS with subscription tiers\n"
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ─── CORS ─────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ─── Custom Middleware ────────────────────────────────────────────────────
    app.add_middleware(RequestLoggingMiddleware)

    # ─── Exception Handlers ──────────────────────────────────────────────────
    @app.exception_handler(QuantyxException)
    async def quantyx_exception_handler(request: Request, exc: QuantyxException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error_code": exc.error_code, "detail": exc.detail},
        )

    # ─── Routers ─────────────────────────────────────────────────────────────
    app.include_router(api_router)

    # ─── Startup / Shutdown ───────────────────────────────────────────────────
    @app.on_event("startup")
    async def startup():
        logger.info("quantyx_startup", version=settings.APP_VERSION, debug=settings.DEBUG)

    @app.on_event("shutdown")
    async def shutdown():
        from app.utils.cache import _redis_client
        if _redis_client:
            await _redis_client.aclose()
        logger.info("quantyx_shutdown")

    # ─── Health Check ────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"])
    async def health():
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
        }

    return app


app = create_application()

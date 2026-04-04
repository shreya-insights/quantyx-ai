import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import QuantyxException
from app.core.middleware import RequestLoggingMiddleware


# ─── Structured Logging Setup ─────────────────────────────────────────────────
def _rename_level_for_elk(_logger: object, _name: str, event_dict: dict) -> dict:
    raw = event_dict.pop("level", None)
    if raw is None:
        return event_dict
    if isinstance(raw, int):
        event_dict["log_level"] = logging.getLevelName(raw)
    else:
        event_dict["log_level"] = str(raw)
    return event_dict


structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        _rename_level_for_elk,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: load ML model at startup, clean up Redis at shutdown."""
    from app.services.ml_fraud_service import MLFraudService
    from app.utils.metrics import init_metrics_at_startup

    init_metrics_at_startup()

    try:
        await asyncio.to_thread(MLFraudService.load)
        logger.info("ml_model.loaded", model_version=MLFraudService._model_version)
    except FileNotFoundError:
        logger.warning("ml_model.not_found.running_rules_only")
    except Exception as exc:
        logger.error("ml_model.load_failed", error=str(exc), exc_info=True)

    logger.info("quantyx_startup", version=settings.APP_VERSION, debug=settings.DEBUG)

    yield

    from app.utils.cache import _redis_client

    if _redis_client:
        await _redis_client.aclose()
    logger.info("quantyx_shutdown")


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
            "- 5-rule fraud detection engine + XGBoost ML scoring\n"
            "- SHAP explainability for EU AI Act compliance\n"
            "- Live SQL Query Lab\n"
            "- Multi-tenant SaaS with subscription tiers\n"
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
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

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        from app.utils.metrics import refresh_celery_queue_depths

        await asyncio.to_thread(refresh_celery_queue_depths)
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    # ─── Health Check ────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"])
    async def health():
        from app.services.ml_fraud_service import MLFraudService

        t0 = time.monotonic()
        celery_workers: str | None = None
        try:
            from app.worker.celery_app import celery_app

            def _ping_workers() -> dict | None:
                inspect = celery_app.control.inspect(timeout=0.75)
                if inspect is None:
                    return None
                return inspect.ping()

            ping = await asyncio.to_thread(_ping_workers)
            celery_workers = "ok" if ping else "no_workers"
        except Exception as exc:
            logger.warning("health_celery_inspect_failed", error=str(exc))
            celery_workers = "unavailable"

        latency_ms = int((time.monotonic() - t0) * 1000)
        overall = "healthy" if celery_workers == "ok" else "degraded"
        return {
            "status": overall,
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "latency_ms": latency_ms,
            "celery_workers": celery_workers,
            "ml_model": MLFraudService._model_version if MLFraudService.is_loaded() else "not_loaded",
        }

    return app


app = create_application()

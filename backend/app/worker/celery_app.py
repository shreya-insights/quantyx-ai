"""Celery application — broker and result backend share Redis for simplicity.

Design choices:
    task_acks_late: worker crash mid-task requeues work (at-least-once).
    task_reject_on_worker_lost: lost connection returns message to broker.
    result_expires: 24h retention for polling from the API.
    Per-type queues: scale workers by queue (fraud vs ingestion vs reports).
    redbeat: persistent beat schedule in Redis (FastAPI stack; no Django beat).
"""
import time

from celery import Celery
from celery.schedules import crontab
from celery.signals import task_postrun, task_prerun

from app.core.config import settings
from app.utils.metrics import CELERY_TASK_DURATION_SECONDS

CELERY_RESULT_EXPIRE_SECONDS = 86400

celery_app = Celery(
    "quantyx",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=CELERY_RESULT_EXPIRE_SECONDS,
    task_track_started=True,
    redbeat_redis_url=settings.REDIS_URL,
    # Include the `analytics` queue on at least one worker (e.g. -Q fraud,...,analytics)
    # so refresh_analytics_cache runs; otherwise APIs still serve OLTP on cache miss/stale.
    task_routes={
        "quantyx.fraud.*": {"queue": "fraud"},
        "quantyx.reports.*": {"queue": "reports"},
        "quantyx.ingestion.*": {"queue": "ingestion"},
        "quantyx.features.*": {"queue": "features"},
        "quantyx.monitoring.*": {"queue": "features"},
        "quantyx.analytics.*": {"queue": "analytics"},
        "quantyx.warehouse.*": {"queue": "analytics"},
    },
    beat_scheduler="redbeat.RedBeatScheduler",
    beat_schedule={
        "recompute-features-every-6h": {
            "task": "quantyx.features.recompute_all_features",
            "schedule": crontab(minute=0, hour="*/6"),
        },
        "model-health-check-weekly": {
            "task": "quantyx.monitoring.run_model_health_check",
            "schedule": crontab(minute=0, hour=0, day_of_week=1),
        },
        "refresh-analytics-cache-hourly": {
            "task": "quantyx.analytics.refresh_all_analytics_caches",
            "schedule": crontab(minute=0),
        },
        "nightly-warehouse-etl": {
            "task": "quantyx.warehouse.run_nightly_etl",
            "schedule": crontab(minute=0, hour=2),
        },
    },
)


@task_prerun.connect
def _quantyx_celery_prerun(sender: object | None = None, task: object | None = None, **kwargs: object) -> None:
    if task is None or not hasattr(task, "request"):
        return
    setattr(task.request, "_quantyx_t0", time.perf_counter())


@task_postrun.connect
def _quantyx_celery_postrun(
    sender: object | None = None, task: object | None = None, state: str | None = None, **kwargs: object
) -> None:
    if task is None or state is None or not hasattr(task, "request"):
        return
    t0 = getattr(task.request, "_quantyx_t0", None)
    start = float(t0) if t0 is not None else time.perf_counter()
    elapsed = max(0.0, time.perf_counter() - start)
    task_name = getattr(task, "name", "unknown")
    CELERY_TASK_DURATION_SECONDS.labels(task_name=str(task_name), status=str(state)).observe(elapsed)


# Register tasks
from app.worker.tasks import analytics_tasks as _analytics_tasks  # noqa: E402, F401
from app.worker.tasks import feature_tasks as _feature_tasks  # noqa: E402, F401
from app.worker.tasks import fraud_tasks as _fraud_tasks  # noqa: E402, F401
from app.worker.tasks import monitoring_tasks as _monitoring_tasks  # noqa: E402, F401
from app.worker.tasks import warehouse_tasks as _warehouse_tasks  # noqa: E402, F401

__all__ = ["celery_app", "CELERY_RESULT_EXPIRE_SECONDS"]

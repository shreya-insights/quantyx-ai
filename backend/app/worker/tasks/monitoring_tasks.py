"""
Operational monitoring tasks — model / pipeline health hooks.

Design: lightweight stub suitable for weekly cron; expand with real checks later.
"""
import structlog
from celery import shared_task

logger = structlog.get_logger(__name__)

_MODEL_HEALTH_TASK_NAME = "quantyx.monitoring.run_model_health_check"


@shared_task(
    bind=True,
    name=_MODEL_HEALTH_TASK_NAME,
    queue="features",
    max_retries=2,
    default_retry_delay=60,
)
def run_model_health_check(self) -> dict[str, str]:
    """Placeholder health task for future ML artifact checks."""
    logger.info("monitoring.model_health_stub", task_id=self.request.id)
    return {"status": "noop"}

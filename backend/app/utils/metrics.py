"""Prometheus metrics for Quantyx API and workers.

Label cardinality notes (high-cardinality labels explode memory and scrape cost):
- http_requests_total: company_id is bounded by tenant count; do NOT add user_id or path IDs.
- http_request_duration_seconds: method + route template only; omit company_id per histogram series cost.
- fraud_detections_total: severity + alert_type are enums; company_id bounded by tenants.
- ml_fraud_score_distribution: company_id only; never add transaction_id or account_id.
- celery_task_duration_seconds: task_name is stable registered names; status is bounded.
- redis_operations_total: operation + cache_type + hit_or_miss are low-cardinality enums.
- active_websocket_connections: company_id bounded by tenants.
- db_query_duration_seconds: query_type is SELECT/INSERT/UPDATE/DELETE/other — not raw SQL text.
"""
from __future__ import annotations

from typing import Final

from prometheus_client import Counter, Gauge, Histogram

# HTTP latency buckets aligned with p50/p95 SLO review (sub-100ms to multi-second tail).
HTTP_REQUEST_DURATION_BUCKETS: Final[tuple[float, ...]] = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
)

# ML fraud probability (0..1) — fine bins near decision threshold.
ML_FRAUD_SCORE_BUCKETS: Final[tuple[float, ...]] = (
    0.05,
    0.1,
    0.15,
    0.2,
    0.25,
    0.3,
    0.35,
    0.4,
    0.45,
    0.5,
    0.55,
    0.6,
    0.65,
    0.7,
    0.75,
    0.8,
    0.85,
    0.9,
    0.95,
    1.0,
)

# Celery tasks can run from seconds to minutes (ingestion, reports).
CELERY_TASK_DURATION_BUCKETS: Final[tuple[float, ...]] = (
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
    30.0,
    60.0,
    120.0,
    300.0,
)

# DB query latency — same shape as HTTP for comparable SLO dashboards.
DB_QUERY_DURATION_BUCKETS: Final[tuple[float, ...]] = HTTP_REQUEST_DURATION_BUCKETS

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests handled by the API.",
    ["method", "endpoint", "status", "company_id"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds (route template as endpoint label).",
    ["method", "endpoint"],
    buckets=HTTP_REQUEST_DURATION_BUCKETS,
)

FRAUD_DETECTIONS_TOTAL = Counter(
    "fraud_detections_total",
    "Fraud alerts emitted (rule-based or ML).",
    ["severity", "alert_type", "company_id"],
)

ML_FRAUD_SCORE_DISTRIBUTION = Histogram(
    "ml_fraud_score_distribution",
    "Distribution of ML fraud probabilities per score call.",
    ["company_id"],
    buckets=ML_FRAUD_SCORE_BUCKETS,
)

CELERY_TASK_DURATION_SECONDS = Histogram(
    "celery_task_duration_seconds",
    "Wall time spent inside Celery task body.",
    ["task_name", "status"],
    buckets=CELERY_TASK_DURATION_BUCKETS,
)

REDIS_OPERATIONS_TOTAL = Counter(
    "redis_operations_total",
    "Redis cache operations from CacheManager.",
    ["operation", "cache_type", "hit_or_miss"],
)

ACTIVE_WEBSOCKET_CONNECTIONS = Gauge(
    "active_websocket_connections",
    "Active WebSocket connections per company.",
    ["company_id"],
)

DB_QUERY_DURATION_SECONDS = Histogram(
    "db_query_duration_seconds",
    "Async DB cursor execute duration in seconds.",
    ["query_type"],
    buckets=DB_QUERY_DURATION_BUCKETS,
)

WAREHOUSE_ETL_DURATION_SECONDS = Histogram(
    "warehouse_etl_duration_seconds",
    "Nightly warehouse ETL step latency (sync SQL + Python) in seconds.",
    ["step"],
    buckets=CELERY_TASK_DURATION_BUCKETS,
)

# Queue depth is sampled at scrape time (bounded label: known queue names only).
CELERY_QUEUE_DEPTH = Gauge(
    "celery_queue_depth",
    "Approximate Celery queue length from Redis broker (LLEN).",
    ["queue"],
)

_KNOWN_CELERY_QUEUES: Final[tuple[str, ...]] = (
    "celery",
    "fraud",
    "reports",
    "ingestion",
    "features",
    "analytics",
)


def init_metrics_at_startup() -> None:
    """Register zero gauge time-series so Prometheus sees them before first connection."""
    ACTIVE_WEBSOCKET_CONNECTIONS.labels(company_id="_init").set(0)
    for q in _KNOWN_CELERY_QUEUES:
        CELERY_QUEUE_DEPTH.labels(queue=q).set(0)


def refresh_celery_queue_depths() -> None:
    """Update queue depth gauges; safe to call on each /metrics scrape."""
    try:
        import redis as sync_redis

        from app.core.config import settings

        with sync_redis.from_url(settings.REDIS_URL, decode_responses=False) as client:
            for q in _KNOWN_CELERY_QUEUES:
                depth = int(client.llen(q))
                CELERY_QUEUE_DEPTH.labels(queue=q).set(depth)
    except Exception:
        # Fail-open: metrics scrape must not break if Redis is down.
        pass


def observe_http_request(
    *,
    method: str,
    endpoint: str,
    status_code: int,
    company_id: str,
    duration_seconds: float,
) -> None:
    """Record HTTP counter + latency histogram."""
    status = str(status_code)
    HTTP_REQUESTS_TOTAL.labels(
        method=method,
        endpoint=endpoint,
        status=status,
        company_id=company_id,
    ).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(method=method, endpoint=endpoint).observe(duration_seconds)


def route_template_or_path(request_path: str, scope_route: object | None) -> str:
    """Prefer route template (low cardinality) over raw path."""
    if scope_route is not None and hasattr(scope_route, "path"):
        path = getattr(scope_route, "path", None)
        if isinstance(path, str) and path:
            return path
    return request_path

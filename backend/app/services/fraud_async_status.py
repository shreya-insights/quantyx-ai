"""Map DB + Celery result state into a single fraud poll status for the API."""

from typing import Literal

FraudPollStatus = Literal[
    "pending",
    "analyzing",
    "clear",
    "flagged",
    "unavailable",
    "not_analyzed",
]

_CELERY_TERMINAL_SUCCESS = frozenset({"SUCCESS"})
_CELERY_TERMINAL_FAILURE = frozenset({"FAILURE", "REVOKED"})
_CELERY_ANALYZING = frozenset({"STARTED"})
_CELERY_PENDING = frozenset({"PENDING", "RETRY", "RECEIVED"})


def merge_fraud_poll_status(
    *,
    alerts_exist: bool,
    celery_state: str | None,
) -> FraudPollStatus:
    """
    Prefer committed alerts over in-flight Celery state so the UI never misses a flag.

    When ``celery_state`` is None (no job id), only DB truth is used → clear if no alerts.
    """
    if alerts_exist:
        return "flagged"
    if celery_state is None:
        return "clear"
    state = celery_state.upper()
    if state in _CELERY_TERMINAL_SUCCESS:
        return "clear"
    if state in _CELERY_TERMINAL_FAILURE:
        return "unavailable"
    if state in _CELERY_ANALYZING:
        return "analyzing"
    if state in _CELERY_PENDING:
        return "pending"
    return "pending"

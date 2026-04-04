"""Tests for fraud async polling helpers."""

from app.services.fraud_async_status import merge_fraud_poll_status


def test_merge_fraud_poll_status_prefers_alerts_over_celery() -> None:
    out = merge_fraud_poll_status(alerts_exist=True, celery_state="PENDING")
    assert out == "flagged"


def test_merge_fraud_poll_status_clear_when_no_job() -> None:
    out = merge_fraud_poll_status(alerts_exist=False, celery_state=None)
    assert out == "clear"


def test_merge_fraud_poll_status_celery_success_clears() -> None:
    out = merge_fraud_poll_status(alerts_exist=False, celery_state="SUCCESS")
    assert out == "clear"


def test_merge_fraud_poll_status_celery_started_analyzing() -> None:
    out = merge_fraud_poll_status(alerts_exist=False, celery_state="STARTED")
    assert out == "analyzing"


def test_merge_fraud_poll_status_celery_failure_unavailable() -> None:
    out = merge_fraud_poll_status(alerts_exist=False, celery_state="FAILURE")
    assert out == "unavailable"


def test_merge_fraud_poll_status_celery_pending() -> None:
    out = merge_fraud_poll_status(alerts_exist=False, celery_state="PENDING")
    assert out == "pending"

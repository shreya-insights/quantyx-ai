"""Unit tests for feature store helpers and training-serving contract."""

import pytest

from app.services.feature_engineering import (
    FEATURE_COLUMNS,
    FEATURE_EPSILON,
    FeatureEngineeringService,
    _f,
    _i,
)


def test_feature_columns_order_matches_model_contract() -> None:
    assert FEATURE_COLUMNS == [
        "avg_amount_7d",
        "avg_amount_30d",
        "avg_amount_90d",
        "std_amount_30d",
        "tx_count_7d",
        "tx_count_30d",
        "velocity_15min",
        "velocity_60min",
        "unique_merchants_30d",
        "fraud_rate_30d",
        "merchant_fraud_rate",
        "amount",
        "amount_to_avg_ratio",
        "amount_zscore",
        "is_new_merchant",
        "is_night",
        "is_weekend",
        "hour_of_day",
        "day_of_week",
    ]
    assert len(FEATURE_COLUMNS) == 19


def test_coerce_numeric_helpers_handle_none() -> None:
    assert _f(None) == 0.0
    assert _i(None) == 0
    assert _f(3.5) == 3.5
    assert _i(7) == 7


@pytest.mark.asyncio
async def test_get_features_for_transaction_unknown_account_returns_stable_keys(
    db_session,
) -> None:
    svc = FeatureEngineeringService()
    from datetime import datetime, timezone

    out = await svc.get_features_for_transaction(
        account_id=999999999,
        merchant_id=None,
        amount=100.0,
        company_id=1,
        transaction_date=datetime(2026, 4, 1, 14, 30, tzinfo=timezone.utc),
        db=db_session,
    )
    assert list(out.keys()) == FEATURE_COLUMNS
    assert out["amount"] == 100.0
    assert out["amount_to_avg_ratio"] == pytest.approx(100.0 / FEATURE_EPSILON)

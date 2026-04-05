"""
Integration tests for the analytics endpoints.
These tests verify the SQL analytics engine functions correctly.
"""
import os
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

# Revenue / merchants / fraud stats use MySQL-specific SQL (not SQLite).
requires_mysql_analytics_sql = pytest.mark.skipif(
    os.getenv("GITHUB_ACTIONS") != "true" and os.getenv("QUANTYX_TEST_DB") != "mysql",
    reason="MySQL-specific analytics SQL; run in GitHub Actions or set QUANTYX_TEST_DB=mysql",
)


async def _get_token(client: AsyncClient, slug_suffix: str = "") -> str:
    payload = {
        "company_name": f"Analytics Corp {slug_suffix}",
        "company_slug": f"analytics-corp{slug_suffix}",
        "admin_email": f"admin{slug_suffix}@analytics.com",
        "admin_password": "TestPassword1",
        "admin_full_name": "Analytics Admin",
    }
    reg = await client.post("/api/v1/auth/register", json=payload)
    return reg.json()["access_token"]


@pytest.mark.asyncio
async def test_kpi_summary_empty(client: AsyncClient):
    token = await _get_token(client, "-kpi")
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/v1/analytics/kpi-summary", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_transactions" in data
    assert data["total_transactions"] == 0


@pytest.mark.asyncio
async def test_kpi_summary_future_completed_tx_expands_window(client: AsyncClient):
    """Dashboard KPI uses completed-only data; window extends when latest tx is after today."""
    token = await _get_token(client, "-futurek")
    headers = {"Authorization": f"Bearer {token}"}
    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    user_id = me.json()["id"]
    acct = await client.post(
        "/api/v1/accounts",
        headers=headers,
        json={
            "user_id": user_id,
            "account_number": "ACME-FUTURE-001",
            "account_type": "savings",
            "balance": 0,
            "currency": "USD",
        },
    )
    assert acct.status_code == 201
    account_id = acct.json()["id"]
    future = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
    tx = await client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            "account_id": account_id,
            "amount": 100.0,
            "currency": "USD",
            "transaction_type": "debit",
            "transaction_date": future,
        },
    )
    assert tx.status_code == 201
    response = await client.get("/api/v1/analytics/kpi-summary", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_transactions"] >= 1


@requires_mysql_analytics_sql
@pytest.mark.asyncio
async def test_revenue_trends_empty(client: AsyncClient):
    token = await _get_token(client, "-rev")
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get(
        "/api/v1/analytics/revenue-trends?months=6", headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert isinstance(data["data"], list)


@requires_mysql_analytics_sql
@pytest.mark.asyncio
async def test_top_merchants_empty(client: AsyncClient):
    token = await _get_token(client, "-mrc")
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/v1/analytics/top-merchants", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["data"] == []


@requires_mysql_analytics_sql
@pytest.mark.asyncio
async def test_fraud_stats_empty(client: AsyncClient):
    token = await _get_token(client, "-frd")
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/v1/fraud/stats", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_alerts"] == 0


@pytest.mark.asyncio
async def test_query_lab_execute(client: AsyncClient):
    token = await _get_token(client, "-ql")
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post(
        "/api/v1/query-lab/execute",
        json={"sql": "SELECT 1 + 1 AS result", "limit": 10},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["row_count"] == 1
    assert "result" in data["columns"]


@pytest.mark.asyncio
async def test_query_lab_blocks_dml(client: AsyncClient):
    token = await _get_token(client, "-ql2")
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post(
        "/api/v1/query-lab/execute",
        json={"sql": "DROP TABLE users", "limit": 10},
        headers=headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_subscription_plans(client: AsyncClient):
    token = await _get_token(client, "-sub")
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/v1/subscriptions/plans", headers=headers)
    assert response.status_code == 200
    plans = response.json()
    assert len(plans) == 3
    names = [p["name"] for p in plans]
    assert "starter" in names
    assert "growth" in names
    assert "enterprise" in names

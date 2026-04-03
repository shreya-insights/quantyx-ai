"""
Integration tests for the analytics endpoints.
These tests verify the SQL analytics engine functions correctly.
"""
import pytest
from httpx import AsyncClient


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


@pytest.mark.asyncio
async def test_top_merchants_empty(client: AsyncClient):
    token = await _get_token(client, "-mrc")
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/v1/analytics/top-merchants", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["data"] == []


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

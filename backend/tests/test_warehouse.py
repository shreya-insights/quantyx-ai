"""Warehouse ETL helpers and read API (SQLite in default test run)."""

import pytest
from httpx import AsyncClient

from app.schemas.analytics import HeatmapCell, HeatmapResponse
from app.worker.tasks.warehouse_tasks import _ltv_segment_for_spend


def test_ltv_segment_low_medium_high_by_percentile_thresholds() -> None:
    assert _ltv_segment_for_spend(10.0, 33.0, 66.0) == "low"
    assert _ltv_segment_for_spend(50.0, 33.0, 66.0) == "medium"
    assert _ltv_segment_for_spend(99.0, 33.0, 66.0) == "high"


def test_ltv_segment_boundary_inclusive_low_and_medium() -> None:
    assert _ltv_segment_for_spend(33.0, 33.0, 66.0) == "low"
    assert _ltv_segment_for_spend(66.0, 33.0, 66.0) == "medium"


def test_heatmap_response_has_dense_168_cells() -> None:
    cells = [
        HeatmapCell(
            day_of_week=d,
            hour_of_day=h,
            avg_count=0.0,
            avg_amount=0.0,
            fraud_rate=0.0,
        )
        for d in range(7)
        for h in range(24)
    ]
    payload = HeatmapResponse(cells=cells)
    assert len(payload.cells) == 168


async def _warehouse_token(client: AsyncClient, suffix: str) -> str:
    payload = {
        "company_name": f"WH Corp {suffix}",
        "company_slug": f"wh-corp{suffix}",
        "admin_email": f"admin{suffix}@wh.com",
        "admin_password": "TestPassword1",
        "admin_full_name": "WH Admin",
    }
    reg = await client.post("/api/v1/auth/register", json=payload)
    assert reg.status_code in (200, 201), reg.text
    return reg.json()["access_token"]


@pytest.mark.asyncio
async def test_warehouse_cohort_retention_endpoint_empty(client: AsyncClient) -> None:
    token = await _warehouse_token(client, "-cr")
    r = await client.get(
        "/api/v1/analytics/cohort-retention",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["rows"] == []
    assert body["cohort_months"] == []
    assert body["max_months"] == 0


@pytest.mark.asyncio
async def test_warehouse_ltv_and_heatmap_endpoints_empty(client: AsyncClient) -> None:
    token = await _warehouse_token(client, "-lv")
    headers = {"Authorization": f"Bearer {token}"}
    r_ltv = await client.get("/api/v1/analytics/ltv-segments", headers=headers)
    assert r_ltv.status_code == 200
    assert r_ltv.json()["total_users"] == 0
    r_h = await client.get("/api/v1/analytics/heatmap", headers=headers)
    assert r_h.status_code == 200
    assert len(r_h.json()["cells"]) == 168

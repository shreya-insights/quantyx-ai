import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_company(client: AsyncClient, sample_register_payload: dict):
    response = await client.post("/api/v1/auth/register", json=sample_register_payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, sample_register_payload: dict):
    await client.post("/api/v1/auth/register", json=sample_register_payload)
    # Try same email again with different slug
    payload = {**sample_register_payload, "company_slug": "test-corp-2"}
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, sample_register_payload: dict):
    await client.post("/api/v1/auth/register", json=sample_register_payload)
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": sample_register_payload["admin_email"],
            "password": sample_register_payload["admin_password"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, sample_register_payload: dict):
    await client.post("/api/v1/auth/register", json=sample_register_payload)
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": sample_register_payload["admin_email"], "password": "WrongPass1"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, sample_register_payload: dict):
    reg = await client.post("/api/v1/auth/register", json=sample_register_payload)
    token = reg.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == sample_register_payload["admin_email"]
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

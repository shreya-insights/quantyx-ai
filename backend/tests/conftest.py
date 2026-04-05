import asyncio
import os
from collections.abc import AsyncGenerator
from urllib.parse import quote_plus

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db

import app.models  # noqa: F401 — register all models on Base.metadata (must be before `app` name used)
from app.main import app as fastapi_app


def uses_mysql_backend() -> bool:
    """CI and optional local runs use MySQL so MySQL-specific analytics SQL can execute."""
    return os.getenv("GITHUB_ACTIONS") == "true" or os.getenv("QUANTYX_TEST_DB") == "mysql"


def _test_database_url() -> str:
    if uses_mysql_backend():
        user = quote_plus(os.environ["DB_USER"])
        password = quote_plus(os.environ["DB_PASSWORD"])
        host = os.environ.get("DB_HOST", "127.0.0.1")
        port = os.environ.get("DB_PORT", "3306")
        name = os.environ.get("DB_NAME", "quantyx_test")
        return f"mysql+aiomysql://{user}:{password}@{host}:{port}/{name}"
    return "sqlite+aiosqlite:///:memory:"


TEST_DATABASE_URL = _test_database_url()

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)


TestSessionLocal = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app), base_url="http://test"
    ) as ac:
        yield ac
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def sample_register_payload():
    return {
        "company_name": "Test Corp",
        "company_slug": "test-corp",
        "admin_email": "admin@testcorp.com",
        "admin_password": "TestPassword1",
        "admin_full_name": "Test Admin",
    }

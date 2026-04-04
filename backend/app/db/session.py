from collections.abc import AsyncGenerator
from time import perf_counter

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.utils.metrics import DB_QUERY_DURATION_SECONDS


def _classify_query_type(statement: str) -> str:
    if not statement:
        return "other"
    head = statement.lstrip()[:12].upper()
    if head.startswith("SELECT") or head.startswith("WITH"):
        return "select"
    if head.startswith("INSERT"):
        return "insert"
    if head.startswith("UPDATE"):
        return "update"
    if head.startswith("DELETE"):
        return "delete"
    return "other"


engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    echo=settings.DEBUG,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@event.listens_for(engine.sync_engine, "before_cursor_execute")
def _quantyx_before_cursor_execute(
    conn: object,
    _cursor: object,
    _statement: object,
    _parameters: object,
    _context: object,
    _executemany: bool,
) -> None:
    stack = conn.info.setdefault("_quantyx_qt_stack", [])  # type: ignore[attr-defined]
    stack.append(perf_counter())


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def _quantyx_after_cursor_execute(
    conn: object,
    _cursor: object,
    statement: str,
    _parameters: object,
    _context: object,
    _executemany: bool,
) -> None:
    stack = conn.info.get("_quantyx_qt_stack")  # type: ignore[attr-defined]
    if not stack:
        return
    start = stack.pop()
    elapsed = perf_counter() - start
    qtype = _classify_query_type(statement or "")
    DB_QUERY_DURATION_SECONDS.labels(query_type=qtype).observe(elapsed)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

from fastapi import APIRouter

from app.core.dependencies import AnalystUser, CurrentUser, DBSession
from app.schemas.query_lab import (
    QueryExecuteRequest,
    QueryExecuteResponse,
    QueryTemplate,
    SaveQueryRequest,
    SavedQueryResponse,
)
from app.services.query_lab_service import QueryLabService

router = APIRouter(prefix="/query-lab", tags=["Query Lab"])


@router.post("/execute", response_model=QueryExecuteResponse)
async def execute_query(
    request: QueryExecuteRequest,
    current_user: AnalystUser,
    db: DBSession,
):
    """
    Execute a safe SELECT query in the Query Lab sandbox.

    Restrictions:
    - Only SELECT statements are permitted
    - DML/DDL keywords (INSERT, UPDATE, DELETE, DROP, etc.) are blocked
    - Results are capped at the specified limit (max 2000 rows)
    - Execution time is measured and returned
    """
    service = QueryLabService(db)
    return await service.execute_query(current_user.company_id, request)


@router.get("/templates", response_model=list[QueryTemplate])
async def get_templates(current_user: CurrentUser, db: DBSession):
    """Return built-in SQL query templates organized by category."""
    service = QueryLabService(db)
    return service.get_templates()


@router.post("/saved", response_model=SavedQueryResponse, status_code=201)
async def save_query(
    request: SaveQueryRequest,
    current_user: AnalystUser,
    db: DBSession,
):
    """Save a named query for later use. Public queries are shared across the tenant."""
    service = QueryLabService(db)
    query = await service.save_query(current_user.company_id, current_user.user_id, request)
    return query


@router.get("/saved", response_model=list[SavedQueryResponse])
async def list_saved_queries(current_user: CurrentUser, db: DBSession):
    """List all saved queries for the current user + public queries in the tenant."""
    service = QueryLabService(db)
    queries = await service.get_saved_queries(current_user.company_id, current_user.user_id)
    return queries


@router.delete("/saved/{query_id}", status_code=204)
async def delete_saved_query(
    query_id: int,
    current_user: AnalystUser,
    db: DBSession,
):
    """Delete a saved query. Only the owner or admin can delete."""
    from sqlalchemy import select
    from app.models.saved_query import SavedQuery
    from app.core.exceptions import NotFoundError, AuthorizationError

    result = await db.execute(
        select(SavedQuery).where(
            SavedQuery.id == query_id,
            SavedQuery.company_id == current_user.company_id,
        )
    )
    query = result.scalar_one_or_none()
    if not query:
        raise NotFoundError("Saved query")
    if query.user_id != current_user.user_id and current_user.role != "admin":
        raise AuthorizationError("You can only delete your own queries")

    await db.delete(query)

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class QueryExecuteRequest(BaseModel):
    sql: str = Field(..., min_length=1, max_length=10_000)
    limit: int = Field(default=500, ge=1, le=2000)


class QueryExecuteResponse(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    execution_time_ms: float
    truncated: bool


class SaveQueryRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    query_text: str = Field(..., min_length=1, max_length=10_000)
    is_public: bool = False


class SavedQueryResponse(BaseModel):
    id: int
    name: str
    description: str | None
    query_text: str
    is_public: bool
    execution_count: int
    last_executed_at: datetime | None
    created_at: datetime
    user_email: str | None = None

    model_config = {"from_attributes": True}


class QueryTemplate(BaseModel):
    id: str
    name: str
    description: str
    category: str
    query_text: str
    tags: list[str]

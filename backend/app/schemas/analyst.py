"""Pydantic schemas for the AI Analyst Copilot endpoints."""

from __future__ import annotations

from pydantic import BaseModel, field_validator


class AnalystAskRequest(BaseModel):
    """Validated question submitted by the user to the AI Analyst."""

    question: str

    @field_validator("question")
    @classmethod
    def validate_question_length(cls, v: str) -> str:
        stripped = v.strip()
        if len(stripped) < 10:
            raise ValueError("Question must be at least 10 characters.")
        if len(stripped) > 500:
            raise ValueError("Question must not exceed 500 characters.")
        return stripped


class AnalystAskResponse(BaseModel):
    """Structured answer returned by the AI Analyst."""

    answer: str
    confidence: str
    caveats: list[str]
    chart_suggestion: str | None
    provider: str
    model: str
    latency_ms: float
    tools_used: list[str]


class SuggestedQuestion(BaseModel):
    """A single suggested question template."""

    id: str
    text: str
    category: str


class SuggestedQuestionsResponse(BaseModel):
    """List of pre-defined suggested questions."""

    questions: list[SuggestedQuestion]


class ProviderStatusResponse(BaseModel):
    """Current LLM provider configuration status."""

    primary: str
    primary_model: str
    fallback: str
    fallback_model: str
    tertiary: str
    tertiary_model: str
    all_cloud: bool
    local_model: bool

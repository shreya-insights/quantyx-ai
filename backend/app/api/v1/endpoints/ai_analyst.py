"""AI Analyst Copilot endpoints.

Three routes:
  POST /analyst/ask        — submit a question, get a structured AI answer
  GET  /analyst/suggested-questions — pre-defined question templates (cached 6h)
  GET  /analyst/provider-status     — debug which LLM provider chain is active

Rate limiting (sliding window via Redis) is applied per user_id to prevent
free-tier exhaustion. All queries are structlog-audited with a question hash.
"""

from __future__ import annotations

import hashlib
from http import HTTPStatus

import structlog
from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.core.dependencies import AdminUser, AnalystUser, DBSession
from app.schemas.analyst import (
    AnalystAskRequest,
    AnalystAskResponse,
    ProviderStatusResponse,
    SuggestedQuestion,
    SuggestedQuestionsResponse,
)
from app.services.ai_analyst_service import ask
from app.utils.cache import get_cache_manager

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/analyst", tags=["AI Analyst"])

_SUGGESTIONS_TTL_SECONDS = 21_600  # 6 hours
_SUGGESTIONS_CACHE_KEY_PREFIX = "analyst:suggestions"

_SUGGESTED_QUESTIONS: list[SuggestedQuestion] = [
    SuggestedQuestion(
        id="sq_revenue_trend",
        text="What has our revenue trend looked like over the past 6 months?",
        category="Revenue",
    ),
    SuggestedQuestion(
        id="sq_fraud_summary",
        text="Give me a summary of our current fraud alert situation.",
        category="Fraud",
    ),
    SuggestedQuestion(
        id="sq_top_merchants",
        text="Which merchants generated the most revenue in the last 30 days?",
        category="Merchants",
    ),
    SuggestedQuestion(
        id="sq_category_breakdown",
        text="What does our spending look like broken down by category this month?",
        category="Spending",
    ),
    SuggestedQuestion(
        id="sq_kpi_last_quarter",
        text="What were our key KPIs for the last quarter?",
        category="KPIs",
    ),
]


@router.post("/ask", response_model=AnalystAskResponse, status_code=HTTPStatus.OK)
async def ask_analyst(
    body: AnalystAskRequest,
    current_user: AnalystUser,
    db: DBSession,
) -> AnalystAskResponse:
    """Submit a natural-language question to the AI Analyst.

    Applies a sliding-window rate limit of 20 requests per hour per user.
    Logs an audit record (question SHA-256) before calling the LLM so the
    access trail exists even if the LLM call fails downstream.
    """
    cache = await get_cache_manager()
    rate_key = f"analyst:{current_user.user_id}"
    allowed, remaining = await cache.rate_limit_check(
        identifier=rate_key,
        max_requests=settings.AI_ANALYST_RATE_LIMIT_PER_HOUR,
        window_seconds=3600,
    )
    if not allowed:
        raise HTTPException(
            status_code=HTTPStatus.TOO_MANY_REQUESTS,
            detail={
                "error_code": "ANALYST_RATE_LIMIT_EXCEEDED",
                "message": "Rate limit reached. You may ask up to 20 questions per hour.",
            },
        )

    question_hash = hashlib.sha256(body.question.encode()).hexdigest()
    logger.info(
        "analyst.query.received",
        user_id=current_user.user_id,
        company_id=current_user.company_id,
        question_hash=question_hash,
        remaining_quota=remaining,
    )

    try:
        result = await ask(
            question=body.question,
            company_id=current_user.company_id,
            db=db,
        )
        logger.info(
            "analyst.query.completed",
            user_id=current_user.user_id,
            company_id=current_user.company_id,
            question_hash=question_hash,
            provider=result.provider,
            confidence=result.confidence,
            tools_used=result.tools_used,
        )
        return result
    except RuntimeError as exc:
        logger.error(
            "analyst.query.llm_failure",
            user_id=current_user.user_id,
            company_id=current_user.company_id,
            error=str(exc),
        )
        raise HTTPException(
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            detail={
                "error_code": "LLM_UNAVAILABLE",
                "message": (
                    "No AI provider is currently available. "
                    "Please check that at least one LLM API key is configured."
                ),
            },
        )


@router.get(
    "/suggested-questions",
    response_model=SuggestedQuestionsResponse,
    status_code=HTTPStatus.OK,
)
async def get_suggested_questions(
    current_user: AnalystUser,
) -> SuggestedQuestionsResponse:
    """Return pre-defined question templates for the AI Analyst.

    Results are served from a per-company Redis cache (6h TTL) to avoid
    unnecessary computation. The templates themselves are static — the cache
    exists to support future dynamic personalisation without changing the API.
    """
    cache = await get_cache_manager()
    cache_key = f"{_SUGGESTIONS_CACHE_KEY_PREFIX}:{current_user.company_id}"
    cached = await cache.get(cache_key)
    if cached:
        return SuggestedQuestionsResponse(
            questions=[SuggestedQuestion(**q) for q in cached]
        )

    await cache.set(
        cache_key,
        [q.model_dump() for q in _SUGGESTED_QUESTIONS],
        ttl=_SUGGESTIONS_TTL_SECONDS,
    )
    return SuggestedQuestionsResponse(questions=_SUGGESTED_QUESTIONS)


@router.get(
    "/provider-status",
    response_model=ProviderStatusResponse,
    status_code=HTTPStatus.OK,
)
async def get_provider_status(
    current_user: AdminUser,
) -> ProviderStatusResponse:
    """Return the active LLM provider chain configuration.

    Admin-only. Useful for ops debugging to confirm which provider and model
    will be used for requests. Always reports all_cloud=True and
    local_model=False — this application never runs local inference.
    """
    return ProviderStatusResponse(
        primary=settings.LLM_PRIMARY_PROVIDER,
        primary_model=settings.GROQ_MODEL,
        fallback=settings.LLM_FALLBACK_PROVIDER,
        fallback_model=settings.GEMINI_MODEL,
        tertiary=settings.LLM_TERTIARY_PROVIDER,
        tertiary_model=settings.OPENROUTER_MODEL,
        all_cloud=True,
        local_model=False,
    )

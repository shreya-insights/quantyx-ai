"""AI Analyst Copilot — multi-turn LLM orchestration service.

Coordinates the LLMProvider, tool execution loop, and JSON response parsing.
The LLM is instructed to ONLY use tools and NEVER invent financial numbers.
All tool calls enforce company_id isolation regardless of LLM-provided input.
"""

from __future__ import annotations

import json
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.schemas.analyst import AnalystAskResponse
from app.services.analyst_tools import TOOL_SCHEMAS, execute_tool
from app.services.llm_provider import LLMMessage, LLMProvider

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = """You are Quantyx AI Analyst, a financial data assistant for a fintech SaaS platform.

STRICT RULES:
1. NEVER invent, estimate, or guess financial numbers. Only use data returned by tools.
2. ALWAYS call the appropriate tool(s) before answering any question about data.
3. Respond ONLY in the following JSON format (no markdown, no extra text):
{
  "answer": "Your complete answer here",
  "confidence": "high|medium|low",
  "caveats": ["optional caveat 1", "optional caveat 2"],
  "chart_suggestion": "bar_chart|line_chart|pie_chart|table|null"
}

4. Set confidence to:
   - "high" when the tool returned data that directly answers the question
   - "medium" when the answer requires interpretation or the data is partial
   - "low" when the question cannot be fully answered with available tools

5. chart_suggestion should be the most appropriate visualisation type for the answer,
   or null if no chart is appropriate.

6. caveats should list any data limitations, date range restrictions, or important caveats.
   Use an empty array [] if there are none.
"""

_FENCE_MARKER = "```"
_JSON_PREFIX = "json"


def _strip_json_fence(text: str) -> str:
    """Remove markdown code fences from LLM output.

    Handles both ```json ... ``` and plain ``` ... ``` variants.
    Returns the raw content between the fences, or the original string if
    no fence is detected.
    """
    stripped = text.strip()
    if not stripped.startswith(_FENCE_MARKER):
        return stripped
    parts = stripped.split(_FENCE_MARKER)
    if len(parts) < 3:
        return stripped
    inner = parts[1]
    if inner.startswith(_JSON_PREFIX):
        inner = inner[len(_JSON_PREFIX):]
    return inner.strip()


def _parse_llm_response(text: str) -> dict[str, Any]:
    """Parse the LLM JSON response with graceful degradation.

    On parse failure returns a minimal valid structure with confidence=low
    so the UI can still display something meaningful.
    """
    cleaned = _strip_json_fence(text)
    try:
        data = json.loads(cleaned)
        return {
            "answer": str(data.get("answer", cleaned)),
            "confidence": str(data.get("confidence", "low")),
            "caveats": list(data.get("caveats", [])),
            "chart_suggestion": data.get("chart_suggestion"),
        }
    except (json.JSONDecodeError, ValueError):
        logger.warning("ai_analyst.parse.failed", raw_text=text[:200])
        return {
            "answer": text,
            "confidence": "low",
            "caveats": ["Response could not be parsed as structured JSON."],
            "chart_suggestion": None,
        }


async def ask(
    question: str,
    company_id: int,
    db: AsyncSession,
) -> AnalystAskResponse:
    """Run the multi-turn analyst loop and return a structured answer.

    Flow:
      1. Build initial user message.
      2. Call LLM — if it requests tools, execute them and append results.
      3. Repeat up to AI_ANALYST_MAX_TOOL_ROUNDS.
      4. Parse final JSON response and return AnalystAskResponse.
    """
    provider = LLMProvider()
    messages: list[LLMMessage] = [LLMMessage(role="user", content=question)]
    tools_used: list[str] = []
    final_text = ""

    for round_num in range(settings.AI_ANALYST_MAX_TOOL_ROUNDS):
        response = await provider.chat(
            messages=messages,
            tools=TOOL_SCHEMAS,
            system_prompt=SYSTEM_PROMPT,
        )

        logger.info(
            "ai_analyst.round",
            round=round_num,
            stop_reason=response.stop_reason,
            tool_calls=len(response.tool_calls),
            company_id=company_id,
        )

        if response.stop_reason == "end_turn" or not response.tool_calls:
            final_text = response.text
            break

        # Append assistant message with tool_calls so providers can reconstruct
        # the proper conversation format (Groq/OpenRouter require the tool_calls
        # array on the assistant turn, and each tool reply needs the matching id).
        messages.append(
            LLMMessage(
                role="assistant",
                content=response.text or "",
                tool_calls=response.tool_calls,
            )
        )

        for tool_call in response.tool_calls:
            tools_used.append(tool_call.tool_name)
            result = await execute_tool(
                tool_name=tool_call.tool_name,
                tool_input=tool_call.tool_input,
                company_id=company_id,
                db=db,
            )
            # One tool message per call — tool_call_id ties it back to the request.
            messages.append(
                LLMMessage(
                    role="tool",
                    content=json.dumps(result, default=str),
                    tool_call_id=tool_call.call_id,
                )
            )
    else:
        final_text = response.text if response.text else (
            "I was unable to fully answer your question within the allowed tool rounds."
        )

    parsed = _parse_llm_response(final_text)

    return AnalystAskResponse(
        answer=parsed["answer"],
        confidence=parsed["confidence"],
        caveats=parsed["caveats"],
        chart_suggestion=parsed.get("chart_suggestion"),
        provider=response.provider,
        model=response.model,
        latency_ms=response.latency_ms,
        tools_used=list(dict.fromkeys(tools_used)),
    )

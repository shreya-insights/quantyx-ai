"""Vendor-agnostic LLM provider with automatic fallback chain.

Abstracts Groq, Gemini, and OpenRouter behind a single interface so that
swapping providers is a one-line settings change. The chain is built
dynamically from environment keys — providers with empty keys are silently
skipped. All providers run as cloud APIs; no local inference is ever used.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

_PROVIDER_GROQ = "groq"
_PROVIDER_GEMINI = "gemini"
_PROVIDER_OPENROUTER = "openrouter"


@dataclass
class LLMToolCall:
    """A single tool invocation requested by the model."""

    tool_name: str
    tool_input: dict[str, Any]
    call_id: str


@dataclass
class LLMMessage:
    """A single message in the conversation history.

    tool_calls is populated on assistant messages when the model requested tools.
    tool_call_id is populated on tool-result messages and must match the
    call_id from the LLMToolCall that triggered this result.
    """

    role: str
    content: str | list[Any]
    tool_calls: list["LLMToolCall"] | None = None
    tool_call_id: str | None = None


@dataclass
class LLMResponse:
    """Normalised response from any provider."""

    text: str
    tool_calls: list[LLMToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"
    provider: str = ""
    model: str = ""
    latency_ms: float = 0.0


class LLMProvider:
    """Cloud-only LLM provider with Groq → Gemini → OpenRouter fallback.

    Builds a priority chain from settings at construction time. Any provider
    whose API key is absent or blank is excluded so the chain gracefully
    degrades to available providers without raising on startup.
    """

    def __init__(self) -> None:
        ordered = [
            settings.LLM_PRIMARY_PROVIDER,
            settings.LLM_FALLBACK_PROVIDER,
            settings.LLM_TERTIARY_PROVIDER,
        ]
        self._chain: list[str] = [p for p in ordered if self._has_key(p)]

        if not self._chain:
            raise RuntimeError(
                "No LLM provider keys are configured. "
                "Set at least one of GROQ_API_KEY, GEMINI_API_KEY, or "
                "OPENROUTER_API_KEY in your environment or .env file."
            )

        logger.info(
            "llm_provider.initialized",
            chain=self._chain,
            primary=self._chain[0],
        )

    def _has_key(self, provider: str) -> bool:
        """Return True only when the provider key exists and is non-empty."""
        key_map = {
            _PROVIDER_GROQ: settings.GROQ_API_KEY,
            _PROVIDER_GEMINI: settings.GEMINI_API_KEY,
            _PROVIDER_OPENROUTER: settings.OPENROUTER_API_KEY,
        }
        value = key_map.get(provider, "")
        return bool(value and value.strip())

    async def chat(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Send messages to the first available provider in the chain.

        Tries each provider in order; on any exception logs a warning and
        advances to the next. Raises RuntimeError only when all providers fail.
        """
        last_error: Exception | None = None
        for provider in self._chain:
            start = time.monotonic()
            try:
                response = await self._dispatch(provider, messages, tools, system_prompt)
                response.latency_ms = round((time.monotonic() - start) * 1000, 2)
                logger.info(
                    "llm_provider.call.success",
                    provider=provider,
                    model=response.model,
                    latency_ms=response.latency_ms,
                    tool_calls=len(response.tool_calls),
                    stop_reason=response.stop_reason,
                )
                return response
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "llm_provider.call.failed",
                    provider=provider,
                    error=str(exc),
                )

        tried = ", ".join(self._chain)
        raise RuntimeError(
            f"All LLM providers failed ({tried}). Last error: {last_error}"
        )

    async def _dispatch(
        self,
        provider: str,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None,
        system_prompt: str | None,
    ) -> LLMResponse:
        """Route to the correct provider implementation."""
        if provider == _PROVIDER_GROQ:
            return await self._call_groq(messages, tools, system_prompt)
        if provider == _PROVIDER_GEMINI:
            return await self._call_gemini(messages, tools, system_prompt)
        if provider == _PROVIDER_OPENROUTER:
            return await self._call_openrouter(messages, tools, system_prompt)
        raise ValueError(f"Unknown provider: {provider}")

    async def _call_groq(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None,
        system_prompt: str | None,
    ) -> LLMResponse:
        """Call Groq cloud API (OpenAI-compatible interface)."""
        from groq import AsyncGroq  # type: ignore[import-untyped]

        client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        model = settings.GROQ_MODEL

        msgs: list[dict[str, Any]] = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        for m in messages:
            if m.role == "assistant" and m.tool_calls:
                msgs.append({
                    "role": "assistant",
                    "content": m.content or None,
                    "tool_calls": [
                        {
                            "id": tc.call_id,
                            "type": "function",
                            "function": {
                                "name": tc.tool_name,
                                "arguments": json.dumps(tc.tool_input),
                            },
                        }
                        for tc in m.tool_calls
                    ],
                })
            elif m.role == "tool":
                msgs.append({
                    "role": "tool",
                    "tool_call_id": m.tool_call_id or "",
                    "content": str(m.content),
                })
            else:
                msgs.append({"role": m.role, "content": m.content})

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": msgs,
            "max_tokens": settings.AI_ANALYST_MAX_TOKENS,
            "temperature": 0.1,
        }
        if tools:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t["input_schema"],
                    },
                }
                for t in tools
            ]
            kwargs["tool_choice"] = "auto"

        completion = await client.chat.completions.create(**kwargs)
        choice = completion.choices[0]
        message = choice.message

        tool_calls: list[LLMToolCall] = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(
                    LLMToolCall(
                        tool_name=tc.function.name,
                        tool_input=json.loads(tc.function.arguments),
                        call_id=tc.id,
                    )
                )

        stop_reason = "tool_use" if tool_calls else "end_turn"
        return LLMResponse(
            text=message.content or "",
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            provider=_PROVIDER_GROQ,
            model=model,
        )

    async def _call_gemini(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None,
        system_prompt: str | None,
    ) -> LLMResponse:
        """Call Google Gemini cloud API using the current google-genai SDK."""
        import google.genai as genai  # type: ignore[import-untyped]
        from google.genai import types  # type: ignore[import-untyped]

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        model_name = settings.GEMINI_MODEL

        gemini_tools: list[Any] | None = None
        if tools:
            declarations = [
                types.FunctionDeclaration(
                    name=t["name"],
                    description=t["description"],
                    parameters=t["input_schema"],
                )
                for t in tools
            ]
            gemini_tools = [types.Tool(function_declarations=declarations)]

        contents: list[Any] = []
        for m in messages:
            if m.role == "assistant" and m.tool_calls:
                # Model turn: function call parts
                parts = [
                    types.Part(
                        function_call=types.FunctionCall(
                            name=tc.tool_name,
                            args=tc.tool_input,
                        )
                    )
                    for tc in m.tool_calls
                ]
                contents.append(types.Content(role="model", parts=parts))
            elif m.role == "tool":
                # User turn: function response part (Gemini expects role="user")
                try:
                    response_data = json.loads(str(m.content))
                except (json.JSONDecodeError, ValueError):
                    response_data = {"result": str(m.content)}
                contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                function_response=types.FunctionResponse(
                                    name=m.tool_call_id or "tool",
                                    response=response_data,
                                )
                            )
                        ],
                    )
                )
            else:
                gemini_role = "model" if m.role == "assistant" else "user"
                contents.append(
                    types.Content(
                        role=gemini_role,
                        parts=[types.Part(text=str(m.content))],
                    )
                )

        config = types.GenerateContentConfig(
            system_instruction=system_prompt or "",
            tools=gemini_tools,
            temperature=0.1,
            max_output_tokens=settings.AI_ANALYST_MAX_TOKENS,
        )

        response = await client.aio.models.generate_content(
            model=model_name,
            contents=contents,
            config=config,
        )

        tool_calls: list[LLMToolCall] = []
        text_parts: list[str] = []

        candidate = response.candidates[0] if response.candidates else None
        if candidate:
            for part in candidate.content.parts:
                if part.function_call and part.function_call.name:
                    fc = part.function_call
                    tool_calls.append(
                        LLMToolCall(
                            tool_name=fc.name,
                            tool_input=dict(fc.args) if fc.args else {},
                            call_id=fc.name,
                        )
                    )
                elif part.text:
                    text_parts.append(part.text)

        stop_reason = "tool_use" if tool_calls else "end_turn"
        return LLMResponse(
            text="".join(text_parts),
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            provider=_PROVIDER_GEMINI,
            model=model_name,
        )

    async def _call_openrouter(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None,
        system_prompt: str | None,
    ) -> LLMResponse:
        """Call OpenRouter cloud API (OpenAI-compatible interface)."""
        import httpx

        model = settings.OPENROUTER_MODEL
        url = settings.OPENROUTER_BASE_URL + "/chat/completions"

        msgs: list[dict[str, Any]] = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        for m in messages:
            if m.role == "assistant" and m.tool_calls:
                msgs.append({
                    "role": "assistant",
                    "content": m.content or None,
                    "tool_calls": [
                        {
                            "id": tc.call_id,
                            "type": "function",
                            "function": {
                                "name": tc.tool_name,
                                "arguments": json.dumps(tc.tool_input),
                            },
                        }
                        for tc in m.tool_calls
                    ],
                })
            elif m.role == "tool":
                msgs.append({
                    "role": "tool",
                    "tool_call_id": m.tool_call_id or "",
                    "content": str(m.content),
                })
            else:
                msgs.append({"role": m.role, "content": m.content})

        payload: dict[str, Any] = {
            "model": model,
            "messages": msgs,
            "max_tokens": settings.AI_ANALYST_MAX_TOKENS,
            "temperature": 0.1,
        }
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t["input_schema"],
                    },
                }
                for t in tools
            ]
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://quantyx.ai",
            "X-Title": "Quantyx AI Analyst",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        choice = data["choices"][0]
        message = choice["message"]

        tool_calls: list[LLMToolCall] = []
        if message.get("tool_calls"):
            for tc in message["tool_calls"]:
                tool_calls.append(
                    LLMToolCall(
                        tool_name=tc["function"]["name"],
                        tool_input=json.loads(tc["function"]["arguments"]),
                        call_id=tc["id"],
                    )
                )

        stop_reason = "tool_use" if tool_calls else "end_turn"
        return LLMResponse(
            text=message.get("content") or "",
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            provider=_PROVIDER_OPENROUTER,
            model=model,
        )

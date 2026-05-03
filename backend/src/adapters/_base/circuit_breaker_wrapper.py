"""
File: backend/src/adapters/_base/circuit_breaker_wrapper.py
Purpose: ChatClient wrapper that integrates Cat 8 CircuitBreaker.
Category: Adapters / 範疇 8 integration point
Scope: Phase 53.2 / Sprint 53.2

Description:
    Transparent middleware that wraps any concrete ChatClient and adds
    per-resource circuit-breaker protection:

      Before chat() / stream():
        if breaker.is_open(resource): raise CircuitOpenError

      After chat() / stream() success: breaker.record(success=True, resource=...)
      After failure:                    breaker.record(success=False, resource=...)

    Why a wrapper (not modifying ChatClient ABC)?
      - Keeps adapters/_base/chat_client.py free of Cat 8 concerns
        (per category-boundaries.md: Cat 8 is owner of CircuitBreaker)
      - Concrete adapters (azure_openai/anthropic/openai) stay unchanged
      - Composition over inheritance: any future ChatClient gets
        breaker integration "for free" by wrapping at construction site

    Composition: typically constructed by the AgentLoop / DI factory:

        breaker = DefaultCircuitBreaker(threshold=5, recovery_timeout_seconds=60)
        azure = AzureOpenAIAdapter(...)
        protected_client = CircuitBreakerWrapper(
            inner=azure, breaker=breaker, resource="azure_openai"
        )
        loop = AgentLoop(chat_client=protected_client, ...)

Key Components:
    - CircuitBreakerWrapper: implements ChatClient ABC by delegation;
      adds breaker pre-check + post-record around chat()/stream()

Owner: Adapter layer + Cat 8 integration
Created: 2026-05-03 (Sprint 53.2 Day 2)

Modification History (newest-first):
    - 2026-05-03: Initial creation (Sprint 53.2 Day 2) — US-3 adapter integration
"""

from __future__ import annotations

from typing import AsyncIterator, Literal

from adapters._base.chat_client import ChatClient
from adapters._base.pricing import PricingInfo
from adapters._base.types import ModelInfo, StreamEvent
from agent_harness._contracts import (
    CacheBreakpoint,
    ChatRequest,
    ChatResponse,
    Message,
    ToolSpec,
    TraceContext,
)
from agent_harness.error_handling._abc import CircuitBreaker
from agent_harness.error_handling.circuit_breaker import CircuitOpenError


class CircuitBreakerWrapper(ChatClient):
    """ChatClient decorator that gates calls behind a CircuitBreaker.

    The wrapper is itself a ChatClient (implements all abstract methods).
    Pure-metadata methods (`get_pricing` / `supports_feature` / `model_info`)
    delegate without protection — they don't hit the provider API and have
    no failure mode worth circuit-breaking.

    Args:
        inner: the concrete adapter to protect.
        breaker: shared CircuitBreaker (per-resource state inside).
        resource: resource key — typically the provider name. Use the
            same key across adapter instances of the same provider so
            their failures count toward one circuit.
    """

    def __init__(
        self,
        *,
        inner: ChatClient,
        breaker: CircuitBreaker,
        resource: str,
    ) -> None:
        self._inner = inner
        self._breaker = breaker
        self._resource = resource

    # === core (protected) ===================================================

    async def chat(
        self,
        request: ChatRequest,
        *,
        cache_breakpoints: list[CacheBreakpoint] | None = None,
        trace_context: TraceContext | None = None,
    ) -> ChatResponse:
        if await self._breaker.is_open(self._resource):
            raise CircuitOpenError(f"Circuit OPEN for resource={self._resource}; refusing chat()")
        try:
            response = await self._inner.chat(
                request,
                cache_breakpoints=cache_breakpoints,
                trace_context=trace_context,
            )
        except BaseException:
            await self._breaker.record(success=False, resource=self._resource)
            raise
        await self._breaker.record(success=True, resource=self._resource)
        return response

    def stream(
        self,
        request: ChatRequest,
        *,
        cache_breakpoints: list[CacheBreakpoint] | None = None,
        trace_context: TraceContext | None = None,
    ) -> AsyncIterator[StreamEvent]:
        # stream() must remain a regular method (not async def) so that
        # callers can iterate the returned AsyncIterator. We wrap with a
        # generator that does pre-check + record around the inner stream.
        return self._wrap_stream(request, cache_breakpoints, trace_context)

    async def _wrap_stream(
        self,
        request: ChatRequest,
        cache_breakpoints: list[CacheBreakpoint] | None,
        trace_context: TraceContext | None,
    ) -> AsyncIterator[StreamEvent]:
        if await self._breaker.is_open(self._resource):
            raise CircuitOpenError(f"Circuit OPEN for resource={self._resource}; refusing stream()")
        try:
            async for event in self._inner.stream(
                request,
                cache_breakpoints=cache_breakpoints,
                trace_context=trace_context,
            ):
                yield event
        except BaseException:
            await self._breaker.record(success=False, resource=self._resource)
            raise
        await self._breaker.record(success=True, resource=self._resource)

    # === token (protected — failures here count too) =======================

    async def count_tokens(
        self,
        *,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
    ) -> int:
        # count_tokens may hit a provider API for non-tiktoken providers.
        # Still gate with breaker (cheap pre-check) and record the result.
        if await self._breaker.is_open(self._resource):
            raise CircuitOpenError(
                f"Circuit OPEN for resource={self._resource}; refusing count_tokens()"
            )
        try:
            count = await self._inner.count_tokens(messages=messages, tools=tools)
        except BaseException:
            await self._breaker.record(success=False, resource=self._resource)
            raise
        await self._breaker.record(success=True, resource=self._resource)
        return count

    # === pure-metadata (delegate, no protection) ===========================

    def get_pricing(self) -> PricingInfo:
        return self._inner.get_pricing()

    def supports_feature(
        self,
        feature: Literal[
            "thinking",
            "caching",
            "vision",
            "audio",
            "computer_use",
            "structured_output",
            "parallel_tool_calls",
        ],
    ) -> bool:
        return self._inner.supports_feature(feature)

    def model_info(self) -> ModelInfo:
        return self._inner.model_info()

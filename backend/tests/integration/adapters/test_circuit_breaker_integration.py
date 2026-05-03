"""
File: backend/tests/integration/adapters/test_circuit_breaker_integration.py
Purpose: Integration tests for CircuitBreakerWrapper around a fake ChatClient (Cat 8 US-3).
Category: Tests / Adapters integration
Scope: Phase 53.2 / Sprint 53.2

Created: 2026-05-03 (Sprint 53.2 Day 2)
"""

from __future__ import annotations

from typing import AsyncIterator, Literal
from unittest.mock import MagicMock

import pytest

from adapters._base.chat_client import ChatClient
from adapters._base.circuit_breaker_wrapper import CircuitBreakerWrapper
from adapters._base.pricing import PricingInfo
from adapters._base.types import ModelInfo, StopReason, StreamEvent
from agent_harness._contracts import (
    CacheBreakpoint,
    ChatRequest,
    ChatResponse,
    Message,
    TokenUsage,
    ToolSpec,
    TraceContext,
)
from agent_harness.error_handling.circuit_breaker import (
    CircuitOpenError,
    CircuitState,
    DefaultCircuitBreaker,
)

# === Fake ChatClient =========================================================
# We don't depend on a real provider for this integration test; a hand-built
# fake exercises every code path we care about.


class FakeChatClient(ChatClient):
    """ChatClient stub used to drive the wrapper.

    Configurable to either return a canned response or raise an exception
    on each chat() call. count_tokens() / pure-metadata methods are
    no-ops returning sensible defaults.
    """

    def __init__(self) -> None:
        self.fail_with: BaseException | None = None
        self.chat_call_count = 0

    def make_response(self) -> ChatResponse:
        return ChatResponse(
            model="fake-model",
            content="ok",
            tool_calls=None,
            stop_reason=StopReason.END_TURN,
            usage=TokenUsage(prompt_tokens=1, completion_tokens=1),
        )

    async def chat(
        self,
        request: ChatRequest,
        *,
        cache_breakpoints: list[CacheBreakpoint] | None = None,
        trace_context: TraceContext | None = None,
    ) -> ChatResponse:
        self.chat_call_count += 1
        if self.fail_with is not None:
            raise self.fail_with
        return self.make_response()

    def stream(
        self,
        request: ChatRequest,
        *,
        cache_breakpoints: list[CacheBreakpoint] | None = None,
        trace_context: TraceContext | None = None,
    ) -> AsyncIterator[StreamEvent]:
        return self._stream_impl()

    async def _stream_impl(self) -> AsyncIterator[StreamEvent]:
        if self.fail_with is not None:
            raise self.fail_with
        # Yield a single end-of-turn event for completion.
        yield StreamEvent(type="content_delta", text_delta="ok")  # type: ignore[call-arg]

    async def count_tokens(
        self,
        *,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
    ) -> int:
        if self.fail_with is not None:
            raise self.fail_with
        return 1

    def get_pricing(self) -> PricingInfo:
        return MagicMock(spec=PricingInfo)

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
        return False

    def model_info(self) -> ModelInfo:
        return MagicMock(spec=ModelInfo)


# === fixtures ================================================================


@pytest.fixture
def request_obj() -> ChatRequest:
    return ChatRequest(messages=[Message(role="user", content="hi")])


# === tests ===================================================================


class TestSuccessPath:
    @pytest.mark.asyncio
    async def test_chat_passes_through_in_closed_state(self, request_obj: ChatRequest) -> None:
        inner = FakeChatClient()
        breaker = DefaultCircuitBreaker(threshold=2)
        wrapped = CircuitBreakerWrapper(inner=inner, breaker=breaker, resource="azure_openai")

        response = await wrapped.chat(request_obj)

        assert response.content == "ok"
        assert inner.chat_call_count == 1
        assert breaker.state_of("azure_openai") == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_count_tokens_passes_through(self, request_obj: ChatRequest) -> None:
        inner = FakeChatClient()
        breaker = DefaultCircuitBreaker(threshold=2)
        wrapped = CircuitBreakerWrapper(inner=inner, breaker=breaker, resource="azure_openai")

        count = await wrapped.count_tokens(messages=[Message(role="user", content="x")])

        assert count == 1


class TestFailureRecording:
    @pytest.mark.asyncio
    async def test_chat_failure_records_with_breaker(self, request_obj: ChatRequest) -> None:
        inner = FakeChatClient()
        inner.fail_with = ConnectionError("simulated 503")
        breaker = DefaultCircuitBreaker(threshold=3)
        wrapped = CircuitBreakerWrapper(inner=inner, breaker=breaker, resource="azure_openai")

        with pytest.raises(ConnectionError):
            await wrapped.chat(request_obj)
        assert breaker.consecutive_failures_of("azure_openai") == 1
        assert breaker.state_of("azure_openai") == CircuitState.CLOSED  # not yet at threshold

    @pytest.mark.asyncio
    async def test_threshold_failures_open_circuit(self, request_obj: ChatRequest) -> None:
        inner = FakeChatClient()
        inner.fail_with = ConnectionError("simulated 503")
        breaker = DefaultCircuitBreaker(threshold=2)
        wrapped = CircuitBreakerWrapper(inner=inner, breaker=breaker, resource="azure_openai")

        for _ in range(2):
            with pytest.raises(ConnectionError):
                await wrapped.chat(request_obj)
        assert breaker.state_of("azure_openai") == CircuitState.OPEN


class TestCircuitOpenShortCircuit:
    @pytest.mark.asyncio
    async def test_chat_raises_circuit_open_when_breaker_open(
        self, request_obj: ChatRequest
    ) -> None:
        inner = FakeChatClient()
        inner.fail_with = ConnectionError("simulated 503")
        breaker = DefaultCircuitBreaker(threshold=2)
        wrapped = CircuitBreakerWrapper(inner=inner, breaker=breaker, resource="azure_openai")

        # Trip the circuit
        for _ in range(2):
            with pytest.raises(ConnectionError):
                await wrapped.chat(request_obj)

        # Switch fake to "would succeed" but circuit OPEN should short-circuit
        inner.fail_with = None
        prev_count = inner.chat_call_count
        with pytest.raises(CircuitOpenError):
            await wrapped.chat(request_obj)
        # Inner was NOT called (short-circuited at wrapper)
        assert inner.chat_call_count == prev_count

    @pytest.mark.asyncio
    async def test_count_tokens_raises_circuit_open_when_breaker_open(
        self, request_obj: ChatRequest
    ) -> None:
        inner = FakeChatClient()
        inner.fail_with = ConnectionError("boom")
        breaker = DefaultCircuitBreaker(threshold=2)
        wrapped = CircuitBreakerWrapper(inner=inner, breaker=breaker, resource="azure_openai")

        for _ in range(2):
            with pytest.raises(ConnectionError):
                await wrapped.chat(request_obj)
        # Now circuit OPEN — count_tokens also short-circuits
        with pytest.raises(CircuitOpenError):
            await wrapped.count_tokens(messages=[Message(role="user", content="x")])

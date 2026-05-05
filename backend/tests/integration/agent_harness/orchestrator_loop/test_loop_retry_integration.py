"""
File: backend/tests/integration/agent_harness/orchestrator_loop/test_loop_retry_integration.py
Purpose: Integration test for AgentLoopImpl retry loop wrap (Sprint 55.6 AD-Cat8-2 Option H).
Category: Tests / Integration / 範疇 1 + 範疇 8
Scope: Phase 55 / Sprint 55.6 Day 2

Description:
    End-to-end exercise of the Sprint 55.6 retry loop wrap at L1024-L1140
    (`_stream_loop_events`). Drives the full AgentLoop with:

      - A FakeChatClient issuing a tool_use call then end_turn
      - A flaky tool handler that fails ``fail_count`` times then succeeds
      - A custom ErrorPolicy classifying FlakyTransientError as TRANSIENT
        via ``classify_by_string`` (Sprint 55.4 AD-Cat8-3 narrow Option C
        soft-failure path)
      - Zero-backoff RetryPolicyMatrix (jitter=False, base=0.0) to keep
        the test fast (~ms not seconds)

    Asserts:
      - ErrorRetried event yielded once per failed attempt (fail_count == 1)
      - Tool handler called fail_count + 1 times (1 fail + 1 success)
      - Loop completes with stop_reason="end_turn" (no LoopTerminated)
      - attempt_num counter increments correctly (visible via ErrorRetried.attempt)

    Helper unit tests live in
    `tests/unit/agent_harness/orchestrator_loop/test_retry_policy_wire.py`.

Created: 2026-05-05 (Sprint 55.6 Day 2)

Modification History (newest-first):
    - 2026-05-05: Initial creation (Sprint 55.6 Day 2) — close AD-Cat8-2 integration test
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Literal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from adapters._base.chat_client import ChatClient
from adapters._base.pricing import PricingInfo
from adapters._base.types import ModelInfo, StopReason, StreamEvent
from agent_harness._contracts import (
    CacheBreakpoint,
    ChatRequest,
    ChatResponse,
    ErrorRetried,
    ExecutionContext,
    LoopCompleted,
    LoopEvent,
    LoopTerminated,
    Message,
    TokenUsage,
    ToolCall,
    ToolSpec,
    TraceContext,
)
from agent_harness.error_handling import RetryPolicyMatrix
from agent_harness.error_handling._abc import ErrorClass
from agent_harness.error_handling.policy import DefaultErrorPolicy
from agent_harness.error_handling.retry import RetryConfig
from agent_harness.orchestrator_loop.loop import AgentLoopImpl
from agent_harness.output_parser import OutputParserImpl
from agent_harness.tools import ToolExecutorImpl, ToolRegistryImpl

# === Test fixtures =========================================================


class FlakyTransientError(Exception):
    """Test exception classifying as TRANSIENT for retry path coverage."""


class _FlakyPolicy(DefaultErrorPolicy):
    """Test policy that classifies FlakyTransientError as TRANSIENT.

    Soft-failure path uses classify_by_string (per AD-Cat8-3 narrow Option C)
    so we override that method to recognize FlakyTransientError suffix.
    """

    def classify_by_string(self, class_str: str) -> ErrorClass:
        if "FlakyTransientError" in class_str:
            return ErrorClass.TRANSIENT
        return super().classify_by_string(class_str)

    def classify(self, error: BaseException) -> ErrorClass:
        if isinstance(error, FlakyTransientError):
            return ErrorClass.TRANSIENT
        return super().classify(error)


class _FlakyChatClient(ChatClient):
    """Returns tool_use(flaky_tool) on first call, end_turn on second.

    Mirrors the FakeChatClient pattern from test_loop_error_handling.py
    but with `flaky_tool` as the canned tool name.
    """

    def __init__(self, tool_name: str = "flaky_tool") -> None:
        self._tool_name = tool_name
        self._call_count = 0

    async def chat(
        self,
        request: ChatRequest,
        *,
        cache_breakpoints: list[CacheBreakpoint] | None = None,
        trace_context: TraceContext | None = None,
    ) -> ChatResponse:
        self._call_count += 1
        if self._call_count == 1:
            return ChatResponse(
                model="fake-model",
                content="Calling flaky tool",
                tool_calls=[ToolCall(id="call_1", name=self._tool_name, arguments={})],
                stop_reason=StopReason.TOOL_USE,
                usage=TokenUsage(prompt_tokens=10, completion_tokens=5),
            )
        return ChatResponse(
            model="fake-model",
            content="Tool succeeded after retry; finishing.",
            tool_calls=None,
            stop_reason=StopReason.END_TURN,
            usage=TokenUsage(prompt_tokens=12, completion_tokens=4),
        )

    def stream(
        self,
        request: ChatRequest,
        *,
        cache_breakpoints: list[CacheBreakpoint] | None = None,
        trace_context: TraceContext | None = None,
    ) -> AsyncIterator[StreamEvent]:
        return self._dummy_stream()

    async def _dummy_stream(self) -> AsyncIterator[StreamEvent]:
        if False:
            yield  # type: ignore[unreachable]

    async def count_tokens(
        self,
        *,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
    ) -> int:
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
        return ModelInfo(
            model_name="fake-model",
            model_family="fake",
            provider="fake-provider",
            context_window=8192,
            max_output_tokens=4096,
        )


class _FlakyToolHandler:
    """Tool handler that fails ``fail_count`` times then succeeds.

    Tracks ``attempts`` for assertion. Uses FlakyTransientError so the
    soft-failure path's classify_by_string flow yields TRANSIENT (via
    _FlakyPolicy.classify_by_string).
    """

    def __init__(self, fail_count: int = 1) -> None:
        self.attempts = 0
        self.fail_count = fail_count

    async def __call__(self, call: ToolCall, context: ExecutionContext) -> Any:
        self.attempts += 1
        if self.attempts <= self.fail_count:
            raise FlakyTransientError(f"flaky failure {self.attempts}")
        return {"ok": True, "attempt": self.attempts}


def _make_flaky_components(
    fail_count: int,
) -> tuple[ToolRegistryImpl, ToolExecutorImpl, _FlakyToolHandler]:
    """Build a registry+executor where 'flaky_tool' fails N times then succeeds."""
    registry = ToolRegistryImpl()
    spec = ToolSpec(
        name="flaky_tool",
        description="A tool that flakes for retry-loop testing.",
        input_schema={"type": "object", "properties": {}},
    )
    registry.register(spec)
    handler = _FlakyToolHandler(fail_count=fail_count)
    executor = ToolExecutorImpl(registry=registry, handlers={"flaky_tool": handler})
    return registry, executor, handler


def _make_zero_backoff_matrix() -> RetryPolicyMatrix:
    """RetryPolicyMatrix with zero backoff for fast tests (no asyncio.sleep delay)."""
    return RetryPolicyMatrix(
        matrix={
            (None, ErrorClass.TRANSIENT): RetryConfig(
                max_attempts=3,
                backoff_base=0.0,
                backoff_max=0.0,
                jitter=False,
            ),
        }
    )


# === Tests ==================================================================


@pytest.mark.asyncio
async def test_full_agent_loop_retry_with_flaky_tool_succeeds_after_one_retry() -> None:
    """End-to-end retry loop test: tool fails once, retries, then succeeds.

    Validates Sprint 55.6 AD-Cat8-2 Option H:
      - retry loop wrap at L1044+L1092 fires on soft-failure
      - _should_retry_tool_error returns (True, 0.0) for TRANSIENT @ attempt=1
      - ErrorRetried event yielded with attempt=1, error_class="transient"
      - asyncio.sleep(0.0) doesn't block (zero backoff matrix)
      - attempt_num increments to 2; tool retry succeeds
      - Loop continues to next turn (chat() #2 returns end_turn)
      - LoopCompleted yielded; no LoopTerminated
    """
    session_id = uuid4()
    trace_ctx = TraceContext.create_root()

    registry, executor, handler = _make_flaky_components(fail_count=1)
    loop = AgentLoopImpl(
        chat_client=_FlakyChatClient(),
        output_parser=OutputParserImpl(),
        tool_executor=executor,
        tool_registry=registry,
        error_policy=_FlakyPolicy(max_attempts=3),
        retry_policy=_make_zero_backoff_matrix(),
    )

    events: list[LoopEvent] = []
    async for ev in loop.run(
        session_id=session_id,
        user_input="please call flaky_tool",
        trace_context=trace_ctx,
    ):
        events.append(ev)

    # Assert 1: ErrorRetried event observed exactly once (1 fail = 1 retry)
    error_retried = [e for e in events if isinstance(e, ErrorRetried)]
    assert len(error_retried) == 1
    assert error_retried[0].attempt == 1  # First retry attempt was attempt_num=1 (the failed one)
    assert error_retried[0].error_class == "transient"
    assert error_retried[0].backoff_ms == 0.0  # zero backoff matrix

    # Assert 2: Handler called exactly fail_count + 1 times (1 fail + 1 success)
    assert handler.attempts == 2

    # Assert 3: Loop completed normally (LLM saw success result; end_turn)
    completes = [e for e in events if isinstance(e, LoopCompleted)]
    assert len(completes) == 1
    assert completes[0].stop_reason == "end_turn"

    # Assert 4: No LoopTerminated (success path)
    assert not any(isinstance(e, LoopTerminated) for e in events)

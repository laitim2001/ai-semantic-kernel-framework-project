"""
File: backend/tests/integration/agent_harness/orchestrator_loop/test_loop_error_handling.py
Purpose: Integration tests for AgentLoop Cat 8 chain wiring (Sprint 53.2 US-6).
Category: Tests / Integration / 範疇 1 + 範疇 8
Scope: Phase 53.2 / Sprint 53.2

Created: 2026-05-03 (Sprint 53.2 Day 4)
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
from agent_harness.error_handling import (
    DefaultErrorPolicy,
    DefaultErrorTerminator,
    InMemoryBudgetStore,
    TenantErrorBudget,
    TerminationReason,
)
from agent_harness.orchestrator_loop.loop import AgentLoopImpl
from agent_harness.output_parser import OutputParserImpl
from agent_harness.tools import ToolExecutorImpl, ToolRegistryImpl

# === Fakes =================================================================


class FakeChatClient(ChatClient):
    """Returns a canned tool_use response then end_turn."""

    def __init__(self, tool_name: str = "fake_tool") -> None:
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
                content="Calling tool",
                tool_calls=[ToolCall(id="call_1", name=self._tool_name, arguments={"x": 1})],
                stop_reason=StopReason.TOOL_USE,
                usage=TokenUsage(prompt_tokens=10, completion_tokens=5),
            )
        return ChatResponse(
            model="fake-model",
            content="acknowledged the failure; stopping",
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


def _make_failing_loop_components(
    exc_type: type[BaseException],
) -> tuple[ToolRegistryImpl, ToolExecutorImpl]:
    """Build a registry+executor where 'fake_tool' raises exc_type."""
    registry = ToolRegistryImpl()
    spec = ToolSpec(
        name="fake_tool",
        description="A tool that raises for Cat 8 testing.",
        input_schema={"type": "object", "properties": {"x": {"type": "integer"}}},
    )
    registry.register(spec)

    async def _fail(call: ToolCall, context: ExecutionContext) -> Any:
        raise exc_type("simulated tool failure")

    executor = ToolExecutorImpl(registry=registry, handlers={"fake_tool": _fail})
    return registry, executor


# === fixtures ==============================================================


@pytest.fixture
def session_id():
    return uuid4()


@pytest.fixture
def trace_ctx():
    return TraceContext.create_root()


# === tests =================================================================


class TestLLMRecoverable:
    @pytest.mark.asyncio
    async def test_uncaught_tool_exception_becomes_llm_recoverable(
        self, session_id, trace_ctx
    ) -> None:
        registry, executor = _make_failing_loop_components(ConnectionError)
        loop = AgentLoopImpl(
            chat_client=FakeChatClient(),
            output_parser=OutputParserImpl(),
            tool_executor=executor,
            tool_registry=registry,
            error_policy=DefaultErrorPolicy(),
            # No terminator → never terminates
        )
        events: list[LoopEvent] = []
        async for ev in loop.run(
            session_id=session_id,
            user_input="please call fake_tool",
            trace_context=trace_ctx,
        ):
            events.append(ev)

        completes = [e for e in events if isinstance(e, LoopCompleted)]
        assert len(completes) == 1
        assert completes[0].stop_reason == "end_turn"
        assert not any(isinstance(e, LoopTerminated) for e in events)


class TestFatalTermination:
    @pytest.mark.asyncio
    async def test_fatal_exception_terminates_loop(self, session_id, trace_ctx) -> None:
        class MyMysteryBug(Exception):
            pass

        registry, executor = _make_failing_loop_components(MyMysteryBug)
        loop = AgentLoopImpl(
            chat_client=FakeChatClient(),
            output_parser=OutputParserImpl(),
            tool_executor=executor,
            tool_registry=registry,
            tenant_id=uuid4(),
            error_policy=DefaultErrorPolicy(),
            error_terminator=DefaultErrorTerminator(),
        )
        events: list[LoopEvent] = []
        async for ev in loop.run(
            session_id=session_id,
            user_input="please call fake_tool",
            trace_context=trace_ctx,
        ):
            events.append(ev)

        terminated = [e for e in events if isinstance(e, LoopTerminated)]
        assert len(terminated) == 1
        assert terminated[0].reason == TerminationReason.FATAL_EXCEPTION.value


class TestBudgetTermination:
    @pytest.mark.asyncio
    async def test_budget_pre_exceeded_terminates_loop(self, session_id, trace_ctx) -> None:
        """Tenant pre-exceeded their daily error budget; the next tool failure
        is intercepted by ErrorTerminator BEFORE the loop continues."""
        store = InMemoryBudgetStore()
        budget = TenantErrorBudget(store, max_per_day=2, max_per_month=100)
        tenant = uuid4()
        # Pre-exceed budget out-of-band (simulates earlier requests this day)
        from agent_harness.error_handling import ErrorClass

        for _ in range(3):  # 3 > 2 → exceeded
            await budget.record(tenant, ErrorClass.TRANSIENT)

        registry, executor = _make_failing_loop_components(ConnectionError)
        loop = AgentLoopImpl(
            chat_client=FakeChatClient(),
            output_parser=OutputParserImpl(),
            tool_executor=executor,
            tool_registry=registry,
            tenant_id=tenant,
            error_policy=DefaultErrorPolicy(),
            error_budget=budget,
            error_terminator=DefaultErrorTerminator(error_budget=budget),
        )
        events: list[LoopEvent] = []
        async for ev in loop.run(
            session_id=session_id,
            user_input="please call fake_tool",
            trace_context=trace_ctx,
        ):
            events.append(ev)

        terminated = [e for e in events if isinstance(e, LoopTerminated)]
        assert len(terminated) == 1
        assert terminated[0].reason == TerminationReason.BUDGET_EXCEEDED.value


class TestOptOut:
    @pytest.mark.asyncio
    async def test_no_cat8_deps_propagates_failure_via_tool_result(
        self, session_id, trace_ctx
    ) -> None:
        """Without Cat 8 deps, ToolExecutorImpl already catches and returns
        ToolResult(success=False); loop continues to end_turn (53.1 baseline)."""
        registry, executor = _make_failing_loop_components(ConnectionError)
        loop = AgentLoopImpl(
            chat_client=FakeChatClient(),
            output_parser=OutputParserImpl(),
            tool_executor=executor,
            tool_registry=registry,
            # No error_policy → opt-out
        )
        events: list[LoopEvent] = []
        async for ev in loop.run(
            session_id=session_id,
            user_input="please call fake_tool",
            trace_context=trace_ctx,
        ):
            events.append(ev)

        # 53.1 baseline: ToolExecutor catches; soft-failure; loop ends normally
        completes = [e for e in events if isinstance(e, LoopCompleted)]
        assert len(completes) == 1
        assert not any(isinstance(e, LoopTerminated) for e in events)

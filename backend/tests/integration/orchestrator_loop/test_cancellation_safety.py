"""
File: backend/tests/integration/orchestrator_loop/test_cancellation_safety.py
Purpose: Cancellation safety edge cases beyond the Day 2 unit test
         (test_loop.test_cancellation_during_tool_yields_cancelled).
Category: Integration tests
Scope: Phase 50 / Sprint 50.1 (Day 4.3)

Description:
    Day 2 verified mid-tool cancellation. This integration suite extends
    coverage:
        a) Cancellation during a slow chat() call (LLM hangs, not the tool)
        b) Consumer-driven generator closure (break out of `async for`)
           — Loop must clean up without leaking unfinished state.
        c) State integrity post-cancel — the chat client's last_request
           shows messages frozen at the safe checkpoint, not partially built.

Created: 2026-04-30 (Sprint 50.1 Day 4.3)
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, Literal
from uuid import uuid4

import pytest

from adapters._base.chat_client import ChatClient
from adapters._base.pricing import PricingInfo
from adapters._base.types import ModelInfo, StreamEvent
from agent_harness._contracts import (
    CacheBreakpoint,
    ChatRequest,
    ChatResponse,
    LoopCompleted,
    Message,
    StopReason,
    ToolSpec,
    TraceContext,
)
from agent_harness.orchestrator_loop import AgentLoopImpl
from agent_harness.output_parser import OutputParserImpl
from agent_harness.tools import make_echo_executor


class SlowChatClient(ChatClient):
    """ChatClient that sleeps before responding — mimics LLM hang."""

    def __init__(self, *, sleep_seconds: float = 10.0) -> None:
        self.sleep_seconds = sleep_seconds
        self.chat_call_count = 0
        self.last_request: ChatRequest | None = None

    async def chat(
        self,
        request: ChatRequest,
        *,
        cache_breakpoints: list[CacheBreakpoint] | None = None,
        trace_context: TraceContext | None = None,
    ) -> ChatResponse:
        self.chat_call_count += 1
        self.last_request = request
        await asyncio.sleep(self.sleep_seconds)
        return ChatResponse(model="slow", content="never reached", stop_reason=StopReason.END_TURN)

    def stream(
        self,
        request: ChatRequest,
        *,
        cache_breakpoints: list[CacheBreakpoint] | None = None,
        trace_context: TraceContext | None = None,
    ) -> AsyncIterator[StreamEvent]:
        return self._stream()

    async def _stream(self) -> AsyncIterator[StreamEvent]:
        if False:
            yield StreamEvent()  # type: ignore[abstract]

    async def count_tokens(
        self,
        *,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
    ) -> int:
        return 0

    def get_pricing(self) -> PricingInfo:
        return PricingInfo(
            input_per_million=0.0,
            output_per_million=0.0,
            cached_input_per_million=None,
        )

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
            model_name="slow",
            model_family="slow",
            provider="test",
            context_window=8_192,
            max_output_tokens=2_048,
        )


@pytest.mark.asyncio
async def test_cancel_during_slow_chat_yields_cancelled() -> None:
    """Cancellation while awaiting chat() — Loop catches CancelledError,
    yields LoopCompleted(cancelled), and re-raises."""
    chat = SlowChatClient(sleep_seconds=10.0)
    registry, executor = make_echo_executor()
    loop = AgentLoopImpl(
        chat_client=chat,
        output_parser=OutputParserImpl(),
        tool_executor=executor,
        tool_registry=registry,
    )

    async def consume() -> list:
        return [ev async for ev in loop.run(session_id=uuid4(), user_input="x")]

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    # chat() was reached but never returned (slept 10s; cancelled in 0.05s).
    assert chat.chat_call_count == 1


@pytest.mark.asyncio
async def test_consumer_break_closes_generator_cleanly() -> None:
    """Consumer breaks out of `async for` early — async generator is closed
    by Python; no orphaned tasks remain. We assert no exception leaks past
    the consumer."""
    from adapters._testing.mock_clients import MockChatClient

    # Multi-turn pre-programmed so the loop will keep going after each turn.
    chat = MockChatClient(
        responses=[
            ChatResponse(
                model="m",
                content="t1",
                stop_reason=StopReason.TOOL_USE,
                tool_calls=[
                    __import__("agent_harness._contracts", fromlist=["ToolCall"]).ToolCall(
                        id=f"c{i}", name="echo_tool", arguments={"text": "x"}
                    )
                    for i in range(1)
                ],
            )
            for _ in range(5)
        ]
    )
    registry, executor = make_echo_executor()
    loop = AgentLoopImpl(
        chat_client=chat,
        output_parser=OutputParserImpl(),
        tool_executor=executor,
        tool_registry=registry,
        max_turns=10,
    )

    collected = []
    async for ev in loop.run(session_id=uuid4(), user_input="break-test"):
        collected.append(ev)
        if len(collected) >= 2:
            break  # consumer stops; generator closes cleanly via aclose()

    # We collected exactly 2 events; loop has not run to LoopCompleted.
    assert len(collected) == 2
    assert not any(isinstance(e, LoopCompleted) for e in collected)


@pytest.mark.asyncio
async def test_post_cancel_message_state_consistent() -> None:
    """After mid-tool cancellation, messages seen by chat() up to the
    cancellation point form a coherent prefix (no half-tool-message)."""
    from adapters._testing.mock_clients import MockChatClient
    from agent_harness._contracts import ToolCall
    from agent_harness.tools._abc import ToolExecutor

    class HangingToolExecutor(ToolExecutor):
        async def execute(self, call, *, trace_context=None):
            await asyncio.sleep(10)
            raise RuntimeError("never reached")

        async def execute_batch(self, calls, *, trace_context=None):
            return [await self.execute(c, trace_context=trace_context) for c in calls]

    chat = MockChatClient(
        responses=[
            ChatResponse(
                model="m",
                content="calling slow",
                tool_calls=[ToolCall(id="c1", name="slow_tool", arguments={"text": "x"})],
                stop_reason=StopReason.TOOL_USE,
            ),
        ]
    )
    registry, _ = make_echo_executor()
    loop = AgentLoopImpl(
        chat_client=chat,
        output_parser=OutputParserImpl(),
        tool_executor=HangingToolExecutor(),
        tool_registry=registry,
    )

    async def consume() -> list:
        return [ev async for ev in loop.run(session_id=uuid4(), user_input="hang test")]

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    # chat() was called exactly once (turn 1). The Loop's messages list is
    # shared-by-reference into ChatRequest, so last_request.messages reflects
    # state at cancellation time, not at the original chat() call. Critical
    # invariant: no `tool` role present — we cancelled BEFORE tool execute
    # could feed back its result; the tool Message was never appended.
    assert chat.chat_call_count == 1
    assert chat.last_request is not None
    roles = [m.role for m in chat.last_request.messages]
    assert "tool" not in roles  # core invariant: tool message NOT prematurely appended
    # Allowed roles at cancel point: user (seed) + assistant (turn 1 response).
    assert roles == ["user", "assistant"]

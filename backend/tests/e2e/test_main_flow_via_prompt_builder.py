"""Sprint 52.2 Day 4.3 — main-flow e2e via PromptBuilder.

End-to-end: drives multi-turn AgentLoop with DefaultPromptBuilder injected;
asserts the AP-8 invariant that every chat() call is preceded by a
PromptBuilt event in the same turn, and that artifact.cache_breakpoints
flows to the adapter on every call.

Stays SDK-free (MockChatClient, mocked MemoryRetrieval, InMemoryCacheManager,
TiktokenCounter).
"""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from adapters._testing.mock_clients import MockChatClient
from agent_harness._contracts import (
    ChatResponse,
    LLMRequested,
    PromptBuilt,
    StopReason,
    TokenUsage,
    ToolCall,
    ToolResult,
    TraceContext,
)
from agent_harness._contracts.tools import ToolSpec
from agent_harness.context_mgmt.cache_manager import InMemoryCacheManager
from agent_harness.context_mgmt.token_counter.tiktoken_counter import (
    TiktokenCounter,
)
from agent_harness.memory.retrieval import MemoryRetrieval
from agent_harness.orchestrator_loop.loop import AgentLoopImpl
from agent_harness.output_parser import OutputParserImpl
from agent_harness.prompt_builder.builder import DefaultPromptBuilder
from agent_harness.tools._abc import ExecutionContext, ToolExecutor, ToolRegistry


class _StubRegistry(ToolRegistry):
    def register(self, spec: ToolSpec) -> None:
        return None

    def get(self, name: str) -> ToolSpec | None:
        return None

    def list(self) -> list[ToolSpec]:
        return []

    def by_tag(self, tag: str) -> list[ToolSpec]:
        return []


class _NoopExecutor(ToolExecutor):
    async def execute(
        self,
        call: ToolCall,
        *,
        trace_context: TraceContext | None = None,
        context: ExecutionContext | None = None,
    ) -> ToolResult:
        return ToolResult(
            tool_call_id=call.id,
            tool_name=call.name,
            success=True,
            content="noop",
        )

    async def execute_batch(
        self,
        calls: list[ToolCall],
        *,
        trace_context: TraceContext | None = None,
        context: ExecutionContext | None = None,
    ) -> list[ToolResult]:
        return [await self.execute(c, trace_context=trace_context, context=context) for c in calls]


def _final(text: str) -> ChatResponse:
    return ChatResponse(
        model="mock",
        content=text,
        stop_reason=StopReason.END_TURN,
        usage=TokenUsage(prompt_tokens=10, completion_tokens=2, total_tokens=12),
    )


def _build_loop(
    chat_client: MockChatClient,
    retrieval: MemoryRetrieval,
) -> AgentLoopImpl:
    builder = DefaultPromptBuilder(
        memory_retrieval=retrieval,
        cache_manager=InMemoryCacheManager(),
        token_counter=TiktokenCounter(model="gpt-4o"),
    )
    return AgentLoopImpl(
        chat_client=chat_client,
        output_parser=OutputParserImpl(),
        tool_executor=_NoopExecutor(),
        tool_registry=_StubRegistry(),
        prompt_builder=builder,
    )


@pytest.mark.asyncio
async def test_every_chat_preceded_by_prompt_built() -> None:
    """AP-8 invariant: each LLM call has a PromptBuilt event before it."""
    chat_client = MockChatClient(responses=[_final("ok")])
    retrieval = MemoryRetrieval(layers={})
    retrieval.search = AsyncMock(return_value=[])  # type: ignore[method-assign]
    loop = _build_loop(chat_client, retrieval)

    events = [ev async for ev in loop.run(session_id=uuid4(), user_input="hello")]

    pending_prompt_built = False
    pairings = 0
    for ev in events:
        if isinstance(ev, PromptBuilt):
            pending_prompt_built = True
        elif isinstance(ev, LLMRequested):
            assert pending_prompt_built, (
                "LLMRequested emitted without a preceding PromptBuilt — " "AP-8 main-flow violation"
            )
            pending_prompt_built = False
            pairings += 1

    assert pairings >= 1
    assert chat_client.chat_call_count == pairings


@pytest.mark.asyncio
async def test_cache_breakpoints_reach_adapter() -> None:
    """artifact.cache_breakpoints arrives at the adapter on each chat()."""
    chat_client = MockChatClient(responses=[_final("ok")])
    retrieval = MemoryRetrieval(layers={})
    retrieval.search = AsyncMock(return_value=[])  # type: ignore[method-assign]
    loop = _build_loop(chat_client, retrieval)

    events = [ev async for ev in loop.run(session_id=uuid4(), user_input="hello")]
    prompt_built = cast(list[PromptBuilt], [ev for ev in events if isinstance(ev, PromptBuilt)])

    assert len(prompt_built) == 1
    advertised = prompt_built[0].cache_breakpoints_count
    received = chat_client.last_call_cache_breakpoints
    if advertised > 0:
        assert received is not None
        assert len(received) == advertised
    else:
        assert received is None or len(received) == 0


@pytest.mark.asyncio
async def test_messages_count_matches_artifact() -> None:
    """MockChatClient.last_request.messages length equals artifact.messages length."""
    chat_client = MockChatClient(responses=[_final("ok")])
    retrieval = MemoryRetrieval(layers={})
    retrieval.search = AsyncMock(return_value=[])  # type: ignore[method-assign]
    loop = _build_loop(chat_client, retrieval)

    events = [ev async for ev in loop.run(session_id=uuid4(), user_input="probe")]
    prompt_built = cast(list[PromptBuilt], [ev for ev in events if isinstance(ev, PromptBuilt)])

    assert len(prompt_built) == 1
    advertised = prompt_built[0].messages_count
    assert chat_client.last_request is not None
    assert len(chat_client.last_request.messages) == advertised

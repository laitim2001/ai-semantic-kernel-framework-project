"""
File: tests/unit/agent_harness/context_mgmt/test_compactor_semantic.py
Purpose: Unit tests for SemanticCompactor (impl: compactor/semantic.py).
Category: Tests / 範疇 4 (Context Management)
Scope: Sprint 52.1 Day 2.4

4 tests:
  - test_summarize_old_turns_via_mock_client
  - test_preserves_recent_n_turns
  - test_handles_llm_failure_raises
  - test_summary_metadata_marker

LLM neutrality: tests must use MockChatClient injection; no openai/anthropic SDK imports.
"""

from __future__ import annotations

from datetime import datetime
from typing import AsyncIterator
from uuid import uuid4

import pytest

from adapters._base.chat_client import ChatClient
from adapters._base.pricing import PricingInfo
from adapters._base.types import ModelInfo, StreamEvent
from adapters._testing.mock_clients import MockChatClient
from agent_harness._contracts import (
    CacheBreakpoint,
    ChatRequest,
    ChatResponse,
    CompactionStrategy,
    DurableState,
    LoopState,
    Message,
    StateVersion,
    StopReason,
    ToolSpec,
    TraceContext,
    TransientState,
)
from agent_harness.context_mgmt.compactor.semantic import (
    SemanticCompactionFailedError,
    SemanticCompactor,
)


def _make_state(
    messages: list[Message],
    *,
    token_used: int = 95_000,
    turn_count: int = 35,
) -> LoopState:
    return LoopState(
        transient=TransientState(
            messages=messages,
            current_turn=turn_count,
            token_usage_so_far=token_used,
        ),
        durable=DurableState(session_id=uuid4(), tenant_id=uuid4()),
        version=StateVersion(
            version=1,
            parent_version=None,
            created_at=datetime.now(),
            created_by_category="orchestrator_loop",
        ),
    )


def _make_long_history(num_turns: int = 12) -> list[Message]:
    msgs: list[Message] = [Message(role="system", content="You are an assistant.")]
    for i in range(num_turns):
        msgs.append(Message(role="user", content=f"User question {i}"))
        msgs.append(Message(role="assistant", content=f"Assistant answer {i}"))
    return msgs


class _FailingChatClient(ChatClient):
    """ChatClient that always raises on chat() — for failure-path test."""

    def __init__(self) -> None:
        self.call_count = 0

    async def chat(
        self,
        request: ChatRequest,
        *,
        cache_breakpoints: list[CacheBreakpoint] | None = None,
        trace_context: TraceContext | None = None,
    ) -> ChatResponse:
        self.call_count += 1
        raise RuntimeError("simulated provider error")

    def stream(
        self,
        request: ChatRequest,
        *,
        cache_breakpoints: list[CacheBreakpoint] | None = None,
        trace_context: TraceContext | None = None,
    ) -> AsyncIterator[StreamEvent]:
        return self._empty()

    async def _empty(self) -> AsyncIterator[StreamEvent]:
        if False:
            yield  # pragma: no cover

    async def count_tokens(
        self,
        *,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
    ) -> int:
        return 0

    def get_pricing(self) -> PricingInfo:
        return PricingInfo(
            input_per_million=0.0, output_per_million=0.0, cached_input_per_million=None
        )

    def supports_feature(self, feature: str) -> bool:  # type: ignore[override]
        return False

    def model_info(self) -> ModelInfo:
        return ModelInfo(
            model_name="failing",
            model_family="test",
            provider="test",
            context_window=8_192,
            max_output_tokens=2_048,
        )


@pytest.mark.asyncio
async def test_summarize_old_turns_via_mock_client() -> None:
    """Mock returns fixed summary; old turns are replaced with one summary message."""
    summary_text = "Summary: user asked things; assistant answered things; nothing pending."
    mock = MockChatClient(
        responses=[
            ChatResponse(model="mock", content=summary_text, stop_reason=StopReason.END_TURN)
        ]
    )
    compactor = SemanticCompactor(
        chat_client=mock,
        keep_recent_turns=3,
        token_budget=10_000,
    )
    state = _make_state(_make_long_history(num_turns=12))

    result = await compactor.compact_if_needed(state)

    assert result.triggered is True
    assert result.strategy_used == CompactionStrategy.SEMANTIC
    assert mock.chat_call_count == 1
    assert result.compacted_state is not None
    kept = result.compacted_state.transient.messages
    summary_msgs = [m for m in kept if m.metadata.get("compacted_summary") is True]
    assert len(summary_msgs) == 1
    assert summary_msgs[0].content == summary_text


@pytest.mark.asyncio
async def test_preserves_recent_n_turns() -> None:
    """Most recent keep_recent_turns user/assistant turns must survive verbatim."""
    summary = "summary"
    mock = MockChatClient(
        responses=[ChatResponse(model="mock", content=summary, stop_reason=StopReason.END_TURN)]
    )
    keep_recent = 3
    compactor = SemanticCompactor(
        chat_client=mock,
        keep_recent_turns=keep_recent,
        token_budget=10_000,
    )

    history = _make_long_history(num_turns=10)
    state = _make_state(history)

    result = await compactor.compact_if_needed(state)
    assert result.triggered is True
    assert result.compacted_state is not None
    kept = result.compacted_state.transient.messages

    # Tail of kept must contain the last 'keep_recent' assistant messages of the original history
    last_assistant_contents = [
        m.content for m in history if m.role == "assistant"
    ][-keep_recent:]
    kept_assistant_contents = [
        m.content for m in kept if m.role == "assistant" and not m.metadata.get("compacted_summary")
    ]
    for c in last_assistant_contents:
        assert c in kept_assistant_contents


@pytest.mark.asyncio
async def test_handles_llm_failure_raises() -> None:
    """Provider error after retries must raise SemanticCompactionFailedError."""
    failing = _FailingChatClient()
    compactor = SemanticCompactor(
        chat_client=failing,
        keep_recent_turns=2,
        token_budget=10_000,
        retry_count=1,
    )
    state = _make_state(_make_long_history(num_turns=8))

    with pytest.raises(SemanticCompactionFailedError):
        await compactor.compact_if_needed(state)

    # retry_count=1 means initial attempt + 1 retry = 2 calls
    assert failing.call_count == 2


@pytest.mark.asyncio
async def test_summary_metadata_marker() -> None:
    """The replacement summary message must carry metadata['compacted_summary']=True."""
    summary = "compact summary text"
    mock = MockChatClient(
        responses=[ChatResponse(model="mock", content=summary, stop_reason=StopReason.END_TURN)]
    )
    compactor = SemanticCompactor(
        chat_client=mock,
        keep_recent_turns=2,
        token_budget=10_000,
    )
    state = _make_state(_make_long_history(num_turns=10))

    result = await compactor.compact_if_needed(state)
    assert result.triggered is True
    assert result.compacted_state is not None

    summary_msgs = [
        m for m in result.compacted_state.transient.messages
        if m.metadata.get("compacted_summary") is True
    ]
    assert len(summary_msgs) == 1
    assert summary_msgs[0].role == "assistant"
    assert summary_msgs[0].content == summary

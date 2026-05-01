"""
File: tests/unit/agent_harness/context_mgmt/test_compactor_structural.py
Purpose: Unit tests for StructuralCompactor (impl: compactor/structural.py).
Category: Tests / 範疇 4 (Context Management)
Scope: Sprint 52.1 Day 2.2

6 tests:
  - test_not_triggered_below_threshold
  - test_triggered_by_token_threshold
  - test_triggered_by_turn_count
  - test_preserves_system_message
  - test_preserves_hitl_decisions
  - test_drops_redundant_tool_retry
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from agent_harness._contracts import (
    CompactionStrategy,
    DurableState,
    LoopState,
    Message,
    StateVersion,
    ToolCall,
    TransientState,
)
from agent_harness.context_mgmt.compactor.structural import StructuralCompactor


def _make_state(
    messages: list[Message],
    *,
    token_used: int = 0,
    turn_count: int = 0,
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


@pytest.mark.asyncio
async def test_not_triggered_below_threshold() -> None:
    """token < 75% of budget AND turn < 30 → no compaction."""
    compactor = StructuralCompactor(token_budget=100_000)
    state = _make_state(
        messages=[Message(role="user", content="hi")],
        token_used=50_000,
        turn_count=5,
    )

    result = await compactor.compact_if_needed(state)

    assert result.triggered is False
    assert result.strategy_used is None
    assert result.compacted_state is None
    assert result.messages_compacted == 0
    assert result.tokens_after == result.tokens_before


@pytest.mark.asyncio
async def test_triggered_by_token_threshold() -> None:
    """token > 75% of budget triggers compaction."""
    compactor = StructuralCompactor(token_budget=10_000, token_threshold_ratio=0.75)
    state = _make_state(
        messages=[Message(role="user", content=f"q{i}") for i in range(10)],
        token_used=8_000,
        turn_count=3,
    )

    result = await compactor.compact_if_needed(state)

    assert result.triggered is True
    assert result.strategy_used == CompactionStrategy.STRUCTURAL
    assert result.compacted_state is not None
    assert result.duration_ms >= 0


@pytest.mark.asyncio
async def test_triggered_by_turn_count() -> None:
    """turn > 30 triggers even when token usage is low."""
    compactor = StructuralCompactor(token_budget=1_000_000, turn_threshold=30)
    state = _make_state(
        messages=[Message(role="user", content=f"u{i}") for i in range(40)],
        token_used=10_000,
        turn_count=35,
    )

    result = await compactor.compact_if_needed(state)

    assert result.triggered is True
    assert result.strategy_used == CompactionStrategy.STRUCTURAL


@pytest.mark.asyncio
async def test_preserves_system_message() -> None:
    """role=system messages must always survive compaction."""
    sys_msg = Message(role="system", content="You are a helpful assistant.")
    other = [Message(role="user", content=f"q{i}") for i in range(20)]
    compactor = StructuralCompactor(token_budget=1_000, keep_recent_turns=3)
    state = _make_state(
        messages=[sys_msg, *other],
        token_used=900,
        turn_count=20,
    )

    result = await compactor.compact_if_needed(state)

    assert result.triggered is True
    assert result.compacted_state is not None
    kept = result.compacted_state.transient.messages
    assert any(m.role == "system" and m.content == sys_msg.content for m in kept)


@pytest.mark.asyncio
async def test_preserves_hitl_decisions() -> None:
    """metadata['hitl']=True messages must survive compaction."""
    hitl_msg = Message(
        role="assistant",
        content="approval recorded",
        metadata={"hitl": True},
    )
    other = [Message(role="user", content=f"u{i}") for i in range(40)]
    compactor = StructuralCompactor(token_budget=1_000, preserve_hitl=True)
    state = _make_state(
        messages=[*other[:20], hitl_msg, *other[20:]],
        token_used=950,
        turn_count=41,
    )

    result = await compactor.compact_if_needed(state)

    assert result.triggered is True
    assert result.compacted_state is not None
    kept = result.compacted_state.transient.messages
    assert any(m.metadata.get("hitl") is True for m in kept)


@pytest.mark.asyncio
async def test_drops_redundant_tool_retry() -> None:
    """Same (tool_name, args_hash) appearing twice → only the latest pair survives."""
    compactor = StructuralCompactor(token_budget=1_000, turn_threshold=0)

    tool_call_args = {"q": "select 1"}
    msgs = [
        Message(role="user", content="please query"),
        Message(
            role="assistant",
            content="",
            tool_calls=[ToolCall(id="c1", name="db_query", arguments=tool_call_args)],
        ),
        Message(role="tool", content="error: timeout", tool_call_id="c1", name="db_query"),
        Message(
            role="assistant",
            content="",
            tool_calls=[ToolCall(id="c2", name="db_query", arguments=tool_call_args)],
        ),
        Message(role="tool", content="ok: [1]", tool_call_id="c2", name="db_query"),
        Message(role="assistant", content="result is 1"),
    ]
    state = _make_state(messages=msgs, token_used=900, turn_count=4)

    result = await compactor.compact_if_needed(state)

    assert result.triggered is True
    assert result.compacted_state is not None
    kept = result.compacted_state.transient.messages

    db_query_calls = [
        m for m in kept if m.tool_calls and any(tc.name == "db_query" for tc in m.tool_calls)
    ]
    assert len(db_query_calls) == 1
    assert db_query_calls[0].tool_calls is not None
    assert db_query_calls[0].tool_calls[0].id == "c2"

"""
File: tests/integration/agent_harness/context_mgmt/test_observation_masker_keep_recent.py
Purpose: Integration test — StructuralCompactor + injected ObservationMasker on a real LoopState.
Category: Tests / Integration / 範疇 4 (Context Management)
Scope: Sprint 52.1 Day 4.4

Differs from the unit test (test_observation_masker.py) by exercising the
masker through the StructuralCompactor pipeline rather than calling it
directly. Confirms the Day 3.3 dependency-injection wiring.
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
from agent_harness.context_mgmt.observation_masker import DefaultObservationMasker


def _build_history(num_turns: int) -> list[Message]:
    msgs: list[Message] = [Message(role="system", content="sys prompt")]
    for i in range(num_turns):
        msgs.append(Message(role="user", content=f"user q{i}"))
        msgs.append(
            Message(
                role="assistant",
                content="",
                tool_calls=[ToolCall(id=f"c{i}", name="db_query", arguments={"i": i})],
            )
        )
        msgs.append(
            Message(
                role="tool",
                content=f"large tool result body for turn {i}" * 10,
                tool_call_id=f"c{i}",
                name="db_query",
            )
        )
    return msgs


def _make_state(messages: list[Message]) -> LoopState:
    return LoopState(
        transient=TransientState(
            messages=messages,
            current_turn=len([m for m in messages if m.role == "user"]),
            token_usage_so_far=95_000,
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
async def test_structural_compactor_pipes_through_injected_masker() -> None:
    """12-turn history + StructuralCompactor (keep_recent_turns=4) → old tool bodies redacted."""
    masker = DefaultObservationMasker()
    compactor = StructuralCompactor(
        keep_recent_turns=4,
        token_budget=100_000,
        token_threshold_ratio=0.75,
        masker=masker,
    )
    msgs = _build_history(12)
    state = _make_state(msgs)

    result = await compactor.compact_if_needed(state)

    assert result.triggered is True
    assert result.strategy_used == CompactionStrategy.STRUCTURAL
    assert result.compacted_state is not None
    kept = result.compacted_state.transient.messages

    # System message survives
    assert any(m.role == "system" for m in kept)

    # Recent 4 user→assistant turns: their tool results stay verbatim
    tool_msgs = [m for m in kept if m.role == "tool"]
    intact_tail = tool_msgs[-4:]
    for m in intact_tail:
        assert not (
            isinstance(m.content, str) and m.content.startswith("[REDACTED:")
        ), "Recent tool result was redacted; should remain intact."

    # Earlier tool results: redacted (at least one)
    redacted = [
        m for m in tool_msgs if isinstance(m.content, str) and m.content.startswith("[REDACTED:")
    ]
    assert len(redacted) >= 1, "Expected at least one old tool result to be redacted"


@pytest.mark.asyncio
async def test_structural_compactor_default_masker_works_without_explicit_injection() -> None:
    """Constructor without `masker=` arg uses DefaultObservationMasker; same redaction effect."""
    compactor = StructuralCompactor(
        keep_recent_turns=3,
        token_budget=100_000,
        token_threshold_ratio=0.75,
        # No masker passed — should fall back to DefaultObservationMasker.
    )
    msgs = _build_history(10)
    state = _make_state(msgs)

    result = await compactor.compact_if_needed(state)

    assert result.triggered is True
    assert result.compacted_state is not None
    tool_msgs = [m for m in result.compacted_state.transient.messages if m.role == "tool"]
    redacted = [
        m for m in tool_msgs if isinstance(m.content, str) and m.content.startswith("[REDACTED:")
    ]
    assert len(redacted) >= 1

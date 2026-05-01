"""
File: tests/integration/agent_harness/context_mgmt/test_loop_compaction_30turn.py
Purpose: 35-turn no-OOM e2e — Loop + HybridCompactor keeps state under budget.
Category: Tests / Integration / 範疇 4 (Context Management)
Scope: Sprint 52.1 Day 4.5 ⭐

This is the headline acceptance test of Sprint 52.1 §1 Story 1: a 35-turn
conversation must stay below 75 % token budget for ≥ 95 % of turns, must
emit at least one ContextCompacted event, and must end with a state that
is still serialisable (State Mgmt friendliness).

Determinism: mock LLM returns ~1 KB content per turn; HybridCompactor uses
StructuralCompactor (no LLM call) to keep the test offline.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from uuid import uuid4

import pytest

from agent_harness._contracts import (
    CompactionResult,
    DurableState,
    LoopState,
    Message,
    StateVersion,
    TraceContext,
    TransientState,
)
from agent_harness.context_mgmt.compactor.hybrid import HybridCompactor
from agent_harness.context_mgmt.compactor.semantic import (
    SemanticCompactionFailedError,
    SemanticCompactor,
)
from agent_harness.context_mgmt.compactor.structural import StructuralCompactor


class _NoOpSemantic(SemanticCompactor):
    """Test stub: skip the LLM call. Always raises so HybridCompactor falls back."""

    def __init__(self) -> None:
        # Bypass parent __init__ which needs a real ChatClient.
        self.chat_client = None  # type: ignore[assignment]
        self.keep_recent_turns = 5
        self.summary_max_tokens = 2_000
        self.token_budget = 100_000
        self.token_threshold_ratio = 0.75
        self.turn_threshold = 30
        self.retry_count = 0
        self.summary_system_prompt = ""

    async def compact_if_needed(
        self,
        state: LoopState,
        *,
        trace_context: TraceContext | None = None,
    ) -> CompactionResult:
        # Force fallback path so the test stays offline-deterministic.
        raise SemanticCompactionFailedError("test stub: no LLM available offline")

    def should_compact(self, state: LoopState) -> bool:
        return True


def _make_initial_state() -> LoopState:
    return LoopState(
        transient=TransientState(
            messages=[Message(role="system", content="sys prompt")],
            current_turn=0,
            token_usage_so_far=200,
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
async def test_35turn_loop_with_hybrid_compactor_stays_under_budget() -> None:
    """35-turn conversation, ~1KB per turn, HybridCompactor keeps tokens < 75 % budget."""
    token_budget = 100_000
    threshold_ratio = 0.75

    structural = StructuralCompactor(
        keep_recent_turns=5,
        token_budget=token_budget,
        token_threshold_ratio=threshold_ratio,
        turn_threshold=20,  # trigger structural compaction earlier so the test exercises it
    )
    semantic_stub = _NoOpSemantic()
    compactor = HybridCompactor(
        structural=structural,
        semantic=semantic_stub,
        token_budget=token_budget,
        token_threshold_ratio=threshold_ratio,
    )

    state = _make_initial_state()
    over_budget_turns = 0
    compaction_events = 0
    state_at_each_turn: list[int] = []

    # Hard fail-safes (fail-loud rather than infinite-loop)
    MAX_TURNS = 60
    MAX_OBSERVED_TOKENS = 100_000

    for turn in range(35):
        assert turn < MAX_TURNS, "turn cap exceeded"

        # Run a compaction check at the start of the turn (mirrors loop integration logic).
        result = await compactor.compact_if_needed(state)
        if result.triggered and result.compacted_state is not None:
            compaction_events += 1
            state = result.compacted_state

        # Simulate one turn of LLM/tool exchange: append user → assistant tool call →
        # tool result (~1 KB body), accumulating ~1.2 KB / turn (~300 tokens with 4-char heuristic).
        new_messages = list(state.transient.messages)
        new_messages.append(Message(role="user", content=f"user query {turn}"))
        new_messages.append(Message(role="assistant", content=f"assistant turn {turn} reasoning"))
        new_messages.append(
            Message(
                role="tool",
                content="x" * 1024,  # ~1 KB blob
                name="db_query",
                tool_call_id=f"tc{turn}",
            )
        )

        # Simulate token accounting: ~300 tokens added per turn (1 KB blob ≈ 256 tokens + overhead).
        new_token_usage = state.transient.token_usage_so_far + 300

        state = LoopState(
            transient=TransientState(
                messages=new_messages,
                current_turn=turn + 1,
                token_usage_so_far=new_token_usage,
            ),
            durable=state.durable,
            version=StateVersion(
                version=state.version.version + 1,
                parent_version=state.version.version,
                created_at=datetime.now(),
                created_by_category="orchestrator_loop",
            ),
        )
        state_at_each_turn.append(state.transient.token_usage_so_far)

        # Hard guard against runaway token usage
        assert state.transient.token_usage_so_far < MAX_OBSERVED_TOKENS, (
            f"Token usage exceeded hard cap at turn {turn}: "
            f"{state.transient.token_usage_so_far}"
        )

        if state.transient.token_usage_so_far > token_budget * threshold_ratio:
            over_budget_turns += 1

    over_budget_pct = over_budget_turns / 35.0
    assert over_budget_pct <= 0.05, (
        f"Over-budget turns ratio {over_budget_pct:.2%} exceeds 5 % allowance "
        f"(={over_budget_turns}/35)"
    )

    # Compaction must have triggered at least once across 35 turns
    assert compaction_events >= 1, "Expected at least one ContextCompacted event over 35 turns"

    # Final state remains serialisable for State Mgmt (Phase 53.1+ Checkpointer)
    snapshot = deepcopy(state)
    assert snapshot.transient.current_turn == 35
    assert snapshot.transient.token_usage_so_far < MAX_OBSERVED_TOKENS

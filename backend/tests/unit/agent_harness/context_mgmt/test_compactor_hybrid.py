"""
File: tests/unit/agent_harness/context_mgmt/test_compactor_hybrid.py
Purpose: Unit tests for HybridCompactor (impl: compactor/hybrid.py).
Category: Tests / 範疇 4 (Context Management)
Scope: Sprint 52.1 Day 2.6

5 tests:
  - test_structural_sufficient
  - test_structural_insufficient_runs_semantic
  - test_semantic_failure_fallback_structural
  - test_both_fail_emit_warning
  - test_preserves_message_order
"""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import uuid4

import pytest

from agent_harness._contracts import (
    CompactionResult,
    CompactionStrategy,
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


class _StubCompactor(StructuralCompactor):
    """Test stub: returns a configurable CompactionResult and counts calls."""

    def __init__(
        self, *, fixed_result: CompactionResult, raise_exc: Exception | None = None
    ) -> None:
        super().__init__()
        self.fixed_result = fixed_result
        self.raise_exc = raise_exc
        self.call_count = 0

    async def compact_if_needed(
        self,
        state: LoopState,
        *,
        trace_context: TraceContext | None = None,
    ) -> CompactionResult:
        self.call_count += 1
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.fixed_result

    def should_compact(self, state: LoopState) -> bool:
        return True


class _StubSemantic(SemanticCompactor):
    """Test stub for SemanticCompactor."""

    def __init__(
        self,
        *,
        fixed_result: CompactionResult | None = None,
        raise_exc: Exception | None = None,
    ) -> None:
        # We bypass __init__ of parent because we don't need a real ChatClient
        self.chat_client = None  # type: ignore[assignment]
        self.keep_recent_turns = 5
        self.summary_max_tokens = 2_000
        self.token_budget = 100_000
        self.token_threshold_ratio = 0.75
        self.turn_threshold = 30
        self.retry_count = 1
        self.summary_system_prompt = ""
        self.fixed_result = fixed_result
        self.raise_exc = raise_exc
        self.call_count = 0

    async def compact_if_needed(
        self,
        state: LoopState,
        *,
        trace_context: TraceContext | None = None,
    ) -> CompactionResult:
        self.call_count += 1
        if self.raise_exc is not None:
            raise self.raise_exc
        if self.fixed_result is None:
            return CompactionResult(
                triggered=False,
                strategy_used=None,
                tokens_before=state.transient.token_usage_so_far,
                tokens_after=state.transient.token_usage_so_far,
                messages_compacted=0,
                duration_ms=0.0,
                compacted_state=None,
            )
        return self.fixed_result

    def should_compact(self, state: LoopState) -> bool:
        return True


def _make_result(
    *,
    triggered: bool,
    tokens_before: int,
    tokens_after: int,
    messages_compacted: int = 0,
    compacted_state: LoopState | None = None,
    strategy: CompactionStrategy | None = None,
) -> CompactionResult:
    return CompactionResult(
        triggered=triggered,
        strategy_used=strategy,
        tokens_before=tokens_before,
        tokens_after=tokens_after,
        messages_compacted=messages_compacted,
        duration_ms=0.0,
        compacted_state=compacted_state,
    )


@pytest.mark.asyncio
async def test_structural_sufficient() -> None:
    """Structural drops tokens below threshold → semantic NOT called."""
    state = _make_state(
        [Message(role="user", content="hi"), Message(role="assistant", content="ok")]
    )
    post_structural_state = _make_state(
        [Message(role="user", content="hi")],
        token_used=5_000,
    )
    structural_stub = _StubCompactor(
        fixed_result=_make_result(
            triggered=True,
            tokens_before=95_000,
            tokens_after=5_000,
            messages_compacted=10,
            compacted_state=post_structural_state,
        )
    )
    semantic_stub = _StubSemantic()
    hybrid = HybridCompactor(
        structural=structural_stub,
        semantic=semantic_stub,
        token_budget=100_000,
    )

    result = await hybrid.compact_if_needed(state)

    assert result.triggered is True
    assert result.strategy_used == CompactionStrategy.HYBRID
    assert structural_stub.call_count == 1
    assert semantic_stub.call_count == 0
    assert result.tokens_after == 5_000


@pytest.mark.asyncio
async def test_structural_insufficient_runs_semantic() -> None:
    """Structural still over threshold → semantic runs and lowers further."""
    state = _make_state([Message(role="user", content=f"q{i}") for i in range(20)])
    post_structural_state = _make_state(
        [Message(role="user", content="q19")],
        token_used=85_000,
    )
    post_semantic_state = _make_state(
        [Message(role="assistant", content="summary", metadata={"compacted_summary": True})],
        token_used=10_000,
    )
    structural_stub = _StubCompactor(
        fixed_result=_make_result(
            triggered=True,
            tokens_before=95_000,
            tokens_after=85_000,
            messages_compacted=5,
            compacted_state=post_structural_state,
        )
    )
    semantic_stub = _StubSemantic(
        fixed_result=_make_result(
            triggered=True,
            tokens_before=85_000,
            tokens_after=10_000,
            messages_compacted=15,
            compacted_state=post_semantic_state,
        )
    )
    hybrid = HybridCompactor(
        structural=structural_stub,
        semantic=semantic_stub,
        token_budget=100_000,
    )

    result = await hybrid.compact_if_needed(state)

    assert result.triggered is True
    assert result.strategy_used == CompactionStrategy.HYBRID
    assert structural_stub.call_count == 1
    assert semantic_stub.call_count == 1
    assert result.tokens_after == 10_000
    assert result.messages_compacted == 5 + 15


@pytest.mark.asyncio
async def test_semantic_failure_fallback_structural() -> None:
    """Semantic raises → return structural result tagged HYBRID."""
    state = _make_state([Message(role="user", content=f"q{i}") for i in range(20)])
    post_structural_state = _make_state(
        [Message(role="user", content="q19")],
        token_used=85_000,
    )
    structural_stub = _StubCompactor(
        fixed_result=_make_result(
            triggered=True,
            tokens_before=95_000,
            tokens_after=85_000,
            messages_compacted=5,
            compacted_state=post_structural_state,
        )
    )
    semantic_stub = _StubSemantic(raise_exc=SemanticCompactionFailedError("simulated failure"))
    hybrid = HybridCompactor(
        structural=structural_stub,
        semantic=semantic_stub,
        token_budget=100_000,
    )

    result = await hybrid.compact_if_needed(state)

    assert result.triggered is True
    assert result.strategy_used == CompactionStrategy.HYBRID
    assert result.tokens_after == 85_000  # structural's value (semantic failed)
    assert result.compacted_state is post_structural_state
    assert semantic_stub.call_count == 1


@pytest.mark.asyncio
async def test_both_fail_emit_warning(caplog: pytest.LogCaptureFixture) -> None:
    """Structural triggered=False AND semantic raises → warning + passthrough."""
    state = _make_state([Message(role="user", content=f"q{i}") for i in range(20)])
    structural_stub = _StubCompactor(
        fixed_result=_make_result(
            triggered=False,
            tokens_before=95_000,
            tokens_after=95_000,
        )
    )
    semantic_stub = _StubSemantic(raise_exc=SemanticCompactionFailedError("semantic failed"))
    hybrid = HybridCompactor(
        structural=structural_stub,
        semantic=semantic_stub,
        token_budget=100_000,
    )

    with caplog.at_level(logging.WARNING):
        result = await hybrid.compact_if_needed(state)

    # Structural triggered=False but semantic was still attempted (token over threshold)
    assert any("semantic stage failed" in rec.message.lower() for rec in caplog.records)
    # Returns triggered=False because both failed to do work
    assert result.triggered is False
    assert result.strategy_used is None


@pytest.mark.asyncio
async def test_preserves_message_order() -> None:
    """Message order in compacted_state must follow the structural→semantic chain."""
    msgs = [
        Message(role="system", content="sys"),
        Message(role="user", content="q0"),
        Message(role="assistant", content="a0"),
        Message(role="user", content="q1"),
    ]
    final_state = _make_state(msgs, token_used=5_000)
    structural_stub = _StubCompactor(
        fixed_result=_make_result(
            triggered=True,
            tokens_before=95_000,
            tokens_after=5_000,
            messages_compacted=10,
            compacted_state=final_state,
        )
    )
    semantic_stub = _StubSemantic()
    hybrid = HybridCompactor(
        structural=structural_stub,
        semantic=semantic_stub,
        token_budget=100_000,
    )

    state = _make_state(msgs)
    result = await hybrid.compact_if_needed(state)

    assert result.triggered is True
    assert result.compacted_state is not None
    kept = result.compacted_state.transient.messages
    assert [m.role for m in kept] == ["system", "user", "assistant", "user"]
    assert [m.content for m in kept] == ["sys", "q0", "a0", "q1"]

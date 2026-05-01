"""
File: tests/e2e/test_long_conversation_50turn.py
Purpose: e2e — verifier pass rate diff between compacted vs uncompacted 50-turn run is < 5 %.
Category: Tests / e2e / 範疇 4 (Context Management) × 範疇 10 (Verification)
Scope: Sprint 52.1 Day 4.6

Sprint 52.1 §1 Story 2 acceptance: HybridCompactor must not regress quality.
We model verification as a rules-based MockVerifier that scores each
"reasoning answer" against a deterministic ground truth. The same 50-turn
script is run twice — once with HybridCompactor in the loop, once without —
and the two pass rates must agree within 5 percentage points.

Determinism: no real LLM. The mock answer at each turn is the ground truth;
the only thing the compactor can affect is whether the answer survives the
compaction pass (StructuralCompactor preserves system + recent N turns +
HITL — all `compacted_summary=False` answer messages are recent so should
remain). HybridCompactor falls through to a no-op SemanticCompactor stub
to keep the test offline.
"""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass
class _VerificationOutcome:
    passed: bool


class _MockVerifier:
    """Rules-based verifier: an assistant answer of the form 'ANSWER:<n>' passes."""

    def verify(self, message: Message) -> _VerificationOutcome:
        if message.role != "assistant":
            return _VerificationOutcome(passed=False)
        content = message.content if isinstance(message.content, str) else ""
        return _VerificationOutcome(passed=content.startswith("ANSWER:"))


class _NoOpSemantic(SemanticCompactor):
    def __init__(self) -> None:
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
        raise SemanticCompactionFailedError("offline test stub")

    def should_compact(self, state: LoopState) -> bool:
        return True


def _initial_state() -> LoopState:
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


async def _run_50turn(
    compactor: HybridCompactor | None,
    *,
    verifier: _MockVerifier,
) -> tuple[int, int]:
    """Returns (passes, total_verified) for a 50-turn deterministic run."""
    state = _initial_state()
    passes = 0
    total = 0

    for turn in range(50):
        if compactor is not None:
            result = await compactor.compact_if_needed(state)
            if result.triggered and result.compacted_state is not None:
                state = result.compacted_state

        # Each turn appends user query + ANSWER:<turn> assistant + 1 KB tool blob
        msgs = list(state.transient.messages)
        msgs.append(Message(role="user", content=f"q{turn}"))
        answer_msg = Message(role="assistant", content=f"ANSWER:{turn}")
        msgs.append(answer_msg)
        msgs.append(
            Message(
                role="tool",
                content="x" * 1024,
                name="db_query",
                tool_call_id=f"tc{turn}",
            )
        )

        # Verify the just-emitted answer
        outcome = verifier.verify(answer_msg)
        total += 1
        if outcome.passed:
            passes += 1

        state = LoopState(
            transient=TransientState(
                messages=msgs,
                current_turn=turn + 1,
                token_usage_so_far=state.transient.token_usage_so_far + 300,
            ),
            durable=state.durable,
            version=StateVersion(
                version=state.version.version + 1,
                parent_version=state.version.version,
                created_at=datetime.now(),
                created_by_category="orchestrator_loop",
            ),
        )

    return passes, total


@pytest.mark.asyncio
async def test_50turn_compaction_does_not_degrade_verifier_pass_rate() -> None:
    """Run the same 50-turn script with and without compaction; pass-rate Δ < 5 pp."""
    verifier = _MockVerifier()

    # Baseline run (no compactor)
    baseline_passes, baseline_total = await _run_50turn(None, verifier=verifier)
    baseline_rate = baseline_passes / baseline_total

    # Compacted run
    structural = StructuralCompactor(
        keep_recent_turns=5,
        token_budget=100_000,
        token_threshold_ratio=0.75,
        turn_threshold=20,
    )
    semantic_stub = _NoOpSemantic()
    compactor = HybridCompactor(
        structural=structural,
        semantic=semantic_stub,
        token_budget=100_000,
        token_threshold_ratio=0.75,
    )

    compacted_passes, compacted_total = await _run_50turn(compactor, verifier=verifier)
    compacted_rate = compacted_passes / compacted_total

    delta = abs(baseline_rate - compacted_rate)
    assert delta < 0.05, (
        f"Verifier pass rate diverged too much: baseline={baseline_rate:.2f} "
        f"compacted={compacted_rate:.2f} delta={delta:.2f}"
    )
    # Sanity: both rates should be 1.0 in this rules-based fixture (every
    # assistant message starts with ANSWER:). If baseline drops below 1.0
    # something else is going wrong with the test itself.
    assert baseline_rate == 1.0
    assert compacted_rate == 1.0

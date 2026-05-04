"""
File: backend/tests/unit/agent_harness/verification/test_correction_loop.py
Purpose: Unit tests for run_with_verification — wrapper / verifier hook / self-correction.
Category: Tests / Unit / 範疇 10
Scope: Sprint 54.1 US-3

Description:
    Covers (using a stub AgentLoop fixture):
    - No registry → pass-through (no behavior change)
    - Passing verifier → VerificationPassed + original LoopCompleted
    - Failing verifier → VerificationFailed + correction-augmented re-run
    - Max attempts exhausted → LoopCompleted(verification_failed)
    - Non-end_turn completion (e.g. max_turns) → skip verifier (output may be partial)

    Stub AgentLoop yields pre-configured event sequences per call so tests
    can drive deterministic re-run scenarios without booting AgentLoopImpl.

Created: 2026-05-04 (Sprint 54.1 Day 3)

Related:
    - backend/src/agent_harness/verification/correction_loop.py
"""

from __future__ import annotations

from typing import AsyncIterator, cast
from uuid import uuid4

import pytest

from agent_harness._contracts import (
    LoopState,
    TraceContext,
    VerificationResult,
)
from agent_harness._contracts.events import (
    LLMResponded,
    LoopCompleted,
    LoopEvent,
    LoopStarted,
    VerificationFailed,
    VerificationPassed,
)
from agent_harness.orchestrator_loop import AgentLoop
from agent_harness.verification import (
    VERIFICATION_FAILED_STOP_REASON,
    Verifier,
    VerifierRegistry,
    run_with_verification,
)

# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class _StubAgentLoop(AgentLoop):
    """Minimal AgentLoop that yields canned event sequences per call."""

    def __init__(self, responses_per_call: list[list[LoopEvent]]) -> None:
        self._responses = list(responses_per_call)
        self.user_inputs_received: list[str] = []

    async def run(
        self,
        *,
        session_id: object,
        user_input: str,
        trace_context: TraceContext | None = None,
    ) -> AsyncIterator[LoopEvent]:
        self.user_inputs_received.append(user_input)
        if not self._responses:
            return
        events = self._responses.pop(0)
        for ev in events:
            yield ev

    async def resume(
        self, *, state: LoopState, trace_context: TraceContext | None = None
    ) -> AsyncIterator[LoopEvent]:
        """Not used by these tests; raises if called."""
        raise NotImplementedError("Stub does not implement resume()")
        yield  # pragma: no cover  # noqa: E501 (unreachable; satisfy async generator typing)


class _PassingVerifier(Verifier):
    def __init__(self, name: str = "passing") -> None:
        self.name = name
        self.calls = 0

    async def verify(
        self,
        *,
        output: str,
        state: LoopState,
        trace_context: TraceContext | None = None,
    ) -> VerificationResult:
        self.calls += 1
        return VerificationResult(
            passed=True,
            verifier_name=self.name,
            verifier_type="rules_based",
            score=0.95,
        )


class _FailingVerifier(Verifier):
    def __init__(
        self,
        name: str = "failing",
        reason: str = "test failure",
        correction: str | None = "Please retry differently",
    ) -> None:
        self.name = name
        self._reason = reason
        self._correction = correction
        self.calls = 0

    async def verify(
        self,
        *,
        output: str,
        state: LoopState,
        trace_context: TraceContext | None = None,
    ) -> VerificationResult:
        self.calls += 1
        return VerificationResult(
            passed=False,
            verifier_name=self.name,
            verifier_type="rules_based",
            reason=self._reason,
            suggested_correction=self._correction,
        )


class _ToggleVerifier(Verifier):
    """Fails on first call, passes on subsequent calls — simulates self-correction success."""

    def __init__(self, name: str = "toggle") -> None:
        self.name = name
        self.calls = 0

    async def verify(
        self,
        *,
        output: str,
        state: LoopState,
        trace_context: TraceContext | None = None,
    ) -> VerificationResult:
        self.calls += 1
        if self.calls == 1:
            return VerificationResult(
                passed=False,
                verifier_name=self.name,
                verifier_type="rules_based",
                reason="first attempt bad",
                suggested_correction="Be more specific",
            )
        return VerificationResult(
            passed=True,
            verifier_name=self.name,
            verifier_type="rules_based",
            score=0.9,
        )


def _seq(content: str = "answer", stop: str = "end_turn") -> list[LoopEvent]:
    """Helper: a minimal LoopStarted -> LLMResponded -> LoopCompleted sequence."""
    sid = uuid4()
    return [
        LoopStarted(session_id=sid),
        LLMResponded(content=content),
        LoopCompleted(stop_reason=stop, total_turns=1),
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_registry_passes_through_unchanged() -> None:
    stub = _StubAgentLoop(responses_per_call=[_seq()])
    events: list[LoopEvent] = []
    async for ev in run_with_verification(
        agent_loop=stub,
        session_id=uuid4(),
        user_input="What is 2+2?",
        verifier_registry=None,
    ):
        events.append(ev)

    # Pass-through: should match the stub's sequence exactly
    assert len(events) == 3
    assert isinstance(events[0], LoopStarted)
    assert isinstance(events[1], LLMResponded)
    assert isinstance(events[2], LoopCompleted)
    assert events[2].stop_reason == "end_turn"
    # Stub called exactly once with original user_input
    assert len(stub.user_inputs_received) == 1
    assert stub.user_inputs_received[0] == "What is 2+2?"


@pytest.mark.asyncio
async def test_empty_registry_passes_through_unchanged() -> None:
    stub = _StubAgentLoop(responses_per_call=[_seq()])
    registry = VerifierRegistry()  # empty

    events: list[LoopEvent] = []
    async for ev in run_with_verification(
        agent_loop=stub,
        session_id=uuid4(),
        user_input="hi",
        verifier_registry=registry,
    ):
        events.append(ev)

    # Empty registry should NOT introduce VerificationPassed/Failed
    assert all(not isinstance(ev, (VerificationPassed, VerificationFailed)) for ev in events)


@pytest.mark.asyncio
async def test_passing_verifier_yields_passed_event_then_completion() -> None:
    stub = _StubAgentLoop(responses_per_call=[_seq(content="The answer is 4.")])
    registry = VerifierRegistry()
    verifier = _PassingVerifier()
    registry.register(verifier)

    events: list[LoopEvent] = []
    async for ev in run_with_verification(
        agent_loop=stub,
        session_id=uuid4(),
        user_input="What is 2+2?",
        verifier_registry=registry,
    ):
        events.append(ev)

    # Sequence: LoopStarted, LLMResponded, VerificationPassed, LoopCompleted
    assert len(events) == 4
    assert isinstance(events[2], VerificationPassed)
    assert events[2].verifier == "passing"
    assert events[2].score == 0.95
    assert isinstance(events[3], LoopCompleted)
    assert events[3].stop_reason == "end_turn"
    # Verifier called exactly once
    assert verifier.calls == 1
    # No re-run
    assert len(stub.user_inputs_received) == 1


@pytest.mark.asyncio
async def test_failing_verifier_with_correction_retries_then_passes() -> None:
    """First attempt fails → wrapper rebuilds user_input → second attempt passes."""
    stub = _StubAgentLoop(
        responses_per_call=[
            _seq(content="bad answer"),
            _seq(content="good answer"),
        ]
    )
    registry = VerifierRegistry()
    toggle = _ToggleVerifier()
    registry.register(toggle)

    events: list[LoopEvent] = []
    async for ev in run_with_verification(
        agent_loop=stub,
        session_id=uuid4(),
        user_input="Original question.",
        verifier_registry=registry,
        max_correction_attempts=2,
    ):
        events.append(ev)

    # Should have:
    #   Run 1 events (LoopStarted + LLMResponded) + VerificationFailed
    #   Run 2 events (LoopStarted + LLMResponded) + VerificationPassed + LoopCompleted
    types = [type(ev).__name__ for ev in events]
    assert types.count("VerificationFailed") == 1
    assert types.count("VerificationPassed") == 1
    assert types.count("LoopCompleted") == 1
    last_completion = [ev for ev in events if isinstance(ev, LoopCompleted)][-1]
    assert last_completion.stop_reason == "end_turn"

    # Verifier called twice (once per attempt)
    assert toggle.calls == 2

    # Stub called twice — first with original, second with correction-augmented
    assert len(stub.user_inputs_received) == 2
    assert stub.user_inputs_received[0] == "Original question."
    assert stub.user_inputs_received[1].startswith("Original question.")
    assert "Previous attempt failed verification" in stub.user_inputs_received[1]
    assert "Be more specific" in stub.user_inputs_received[1]


@pytest.mark.asyncio
async def test_max_attempts_exhausted_yields_verification_failed_completion() -> None:
    """All 3 attempts (initial + 2 corrections) fail → wrapper emits verification_failed."""
    stub = _StubAgentLoop(
        responses_per_call=[
            _seq(content="bad 1"),
            _seq(content="bad 2"),
            _seq(content="bad 3"),
        ]
    )
    registry = VerifierRegistry()
    failing = _FailingVerifier()
    registry.register(failing)

    events: list[LoopEvent] = []
    async for ev in run_with_verification(
        agent_loop=stub,
        session_id=uuid4(),
        user_input="Q",
        verifier_registry=registry,
        max_correction_attempts=2,
    ):
        events.append(ev)

    # 3 VerificationFailed (one per attempt) + 1 LoopCompleted(verification_failed)
    failures = [ev for ev in events if isinstance(ev, VerificationFailed)]
    completions = [ev for ev in events if isinstance(ev, LoopCompleted)]
    assert len(failures) == 3
    assert len(completions) == 1
    assert completions[0].stop_reason == VERIFICATION_FAILED_STOP_REASON

    # No VerificationPassed
    passes = [ev for ev in events if isinstance(ev, VerificationPassed)]
    assert len(passes) == 0

    # Stub called 3 times (initial + 2 corrections)
    assert len(stub.user_inputs_received) == 3
    assert failing.calls == 3


@pytest.mark.asyncio
async def test_non_end_turn_completion_skips_verifier() -> None:
    """LoopCompleted with stop_reason like max_turns should NOT trigger verifier."""
    stub = _StubAgentLoop(responses_per_call=[_seq(content="partial", stop="max_turns")])
    registry = VerifierRegistry()
    verifier = _PassingVerifier()
    registry.register(verifier)

    events: list[LoopEvent] = []
    async for ev in run_with_verification(
        agent_loop=stub,
        session_id=uuid4(),
        user_input="x",
        verifier_registry=registry,
    ):
        events.append(ev)

    # Verifier should NOT have been called
    assert verifier.calls == 0
    # No VerificationPassed/Failed events
    assert all(not isinstance(ev, (VerificationPassed, VerificationFailed)) for ev in events)
    # Original LoopCompleted preserved
    completion = [ev for ev in events if isinstance(ev, LoopCompleted)]
    assert len(completion) == 1
    assert completion[0].stop_reason == "max_turns"


# Reference unused import to pacify flake8 (cast / LoopState used by test fixtures)
_ = cast(LoopState, None) if False else None

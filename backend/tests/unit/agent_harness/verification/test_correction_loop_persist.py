"""
File: backend/tests/unit/agent_harness/verification/test_correction_loop_persist.py
Purpose: Unit tests for correction_loop verification_log write hook (Sprint 57.11 US-2).
Category: Tests / Unit / 範疇 10 / persistence
Scope: Sprint 57.11 Day 1 / US-2

Description:
    Verifies the best-effort write hook in correction_loop.py:
    - Passed verifier → repository.insert called with passed=True
    - Failed verifier → repository.insert called with passed=False + reason
    - DB raise → loop continues (event stream NOT broken)

    Mocks `_persist_verification_event` (the helper that wraps the
    session_factory + RLS SET LOCAL + repo.insert chain) rather than
    VerificationLogRepository directly. This isolates the verifier→hook
    invocation contract from DB-layer concerns; the DB-layer is covered by
    integration tests in tests/integration/api/test_verification.py.

Created: 2026-05-10 (Sprint 57.11 Day 1 / US-2)

Related:
    - agent_harness/verification/correction_loop.py (_persist_verification_event)
    - infrastructure/db/repositories/verification_log.py
    - sprint-57-11-plan.md §US-2
"""

from __future__ import annotations

from typing import AsyncIterator, cast
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

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
    VerificationFailed,
    VerificationPassed,
)
from agent_harness.orchestrator_loop import AgentLoop
from agent_harness.verification import (
    Verifier,
    VerifierRegistry,
    run_with_verification,
)


class _StubAgentLoop(AgentLoop):
    """Single-shot stub yielding LLMResponded → LoopCompleted(end_turn)."""

    def __init__(self, content: str = "stub-output") -> None:
        self._content = content

    async def run(
        self,
        *,
        session_id: object,
        user_input: str,
        trace_context: TraceContext | None = None,
    ) -> AsyncIterator[LoopEvent]:
        yield LLMResponded(content=self._content)
        yield LoopCompleted(stop_reason="end_turn", total_turns=1)

    async def resume(
        self, *, state: LoopState, trace_context: TraceContext | None = None
    ) -> AsyncIterator[LoopEvent]:
        raise NotImplementedError
        yield  # pragma: no cover


class _PassingVerifier(Verifier):
    def __init__(self, name: str = "v_pass") -> None:
        self.name = name

    async def verify(
        self,
        *,
        output: str,
        state: LoopState,
        trace_context: TraceContext | None = None,
    ) -> VerificationResult:
        return VerificationResult(
            passed=True,
            verifier_name=self.name,
            verifier_type="rules_based",
            score=0.95,
        )


class _FailingVerifier(Verifier):
    def __init__(self, name: str = "v_fail") -> None:
        self.name = name

    async def verify(
        self,
        *,
        output: str,
        state: LoopState,
        trace_context: TraceContext | None = None,
    ) -> VerificationResult:
        return VerificationResult(
            passed=False,
            verifier_name=self.name,
            verifier_type="llm_judge",
            reason="contains forbidden token",
            suggested_correction="redact and retry",
        )


def _make_trace_with_tenant(tenant_id: UUID) -> TraceContext:
    """TraceContext with tenant_id populated (D-PRE-4)."""
    base = TraceContext.create_root()
    return TraceContext(
        trace_id=base.trace_id,
        span_id=base.span_id,
        parent_span_id=base.parent_span_id,
        tenant_id=tenant_id,
        user_id=base.user_id,
        session_id=base.session_id,
        baggage=base.baggage,
    )


@pytest.mark.asyncio
async def test_persist_passed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Passing verifier → _persist_verification_event called with passed=True."""
    persist_mock = AsyncMock()
    monkeypatch.setattr(
        "agent_harness.verification.correction_loop._persist_verification_event",
        persist_mock,
    )

    tenant_id = uuid4()
    session_id = uuid4()
    trace = _make_trace_with_tenant(tenant_id)
    registry = VerifierRegistry()
    registry.register(_PassingVerifier("v1"))

    events: list[LoopEvent] = []
    async for ev in run_with_verification(
        agent_loop=cast(AgentLoop, _StubAgentLoop()),
        session_id=session_id,
        user_input="hello",
        trace_context=trace,
        verifier_registry=registry,
        max_correction_attempts=2,
    ):
        events.append(ev)

    # Persist hook called once for the single passing verifier
    assert persist_mock.await_count == 1
    call_kwargs = persist_mock.await_args.kwargs
    assert call_kwargs["tenant_id"] == tenant_id
    assert call_kwargs["session_id"] == session_id
    assert call_kwargs["passed"] is True
    assert call_kwargs["verifier_name"] == "v1"
    assert call_kwargs["verifier_type"] == "rules_based"
    assert call_kwargs["score"] == 0.95
    assert call_kwargs["correction_attempt"] == 0

    # Event stream still emits VerificationPassed + LoopCompleted
    assert any(isinstance(e, VerificationPassed) for e in events)
    assert any(isinstance(e, LoopCompleted) for e in events)


@pytest.mark.asyncio
async def test_persist_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Failing verifier → _persist_verification_event called with passed=False + reason."""
    persist_mock = AsyncMock()
    monkeypatch.setattr(
        "agent_harness.verification.correction_loop._persist_verification_event",
        persist_mock,
    )

    tenant_id = uuid4()
    session_id = uuid4()
    trace = _make_trace_with_tenant(tenant_id)
    # Use only a failing verifier; max_correction_attempts=0 → 1 verify, no re-run
    registry = VerifierRegistry()
    registry.register(_FailingVerifier("vF"))

    events: list[LoopEvent] = []
    async for ev in run_with_verification(
        agent_loop=cast(AgentLoop, _StubAgentLoop()),
        session_id=session_id,
        user_input="hello",
        trace_context=trace,
        verifier_registry=registry,
        max_correction_attempts=0,  # exhaust immediately
    ):
        events.append(ev)

    # Persist hook called once for the single failing verifier
    assert persist_mock.await_count == 1
    call_kwargs = persist_mock.await_args.kwargs
    assert call_kwargs["passed"] is False
    assert call_kwargs["reason"] == "contains forbidden token"
    assert call_kwargs["suggested_correction"] == "redact and retry"
    assert call_kwargs["verifier_type"] == "llm_judge"

    assert any(isinstance(e, VerificationFailed) for e in events)


@pytest.mark.asyncio
async def test_persist_failure_silent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Persist hook DB error → loop continues, event stream unbroken.

    Real `_persist_verification_event` is exercised; we make the inner
    `get_session_factory` raise so the helper's try/except path triggers.
    The hook must swallow + log warning + return None; the surrounding
    loop must NOT see the exception.
    """

    def _raise_factory() -> object:  # called like factory = get_session_factory()
        raise RuntimeError("simulated DB outage")

    monkeypatch.setattr(
        "agent_harness.verification.correction_loop.get_session_factory",
        _raise_factory,
    )

    tenant_id = uuid4()
    session_id = uuid4()
    trace = _make_trace_with_tenant(tenant_id)
    registry = VerifierRegistry()
    registry.register(_PassingVerifier("v_silent"))

    events: list[LoopEvent] = []
    async for ev in run_with_verification(
        agent_loop=cast(AgentLoop, _StubAgentLoop()),
        session_id=session_id,
        user_input="hello",
        trace_context=trace,
        verifier_registry=registry,
        max_correction_attempts=2,
    ):
        events.append(ev)

    # Despite simulated DB outage, loop completes successfully:
    assert any(isinstance(e, VerificationPassed) for e in events)
    assert any(isinstance(e, LoopCompleted) for e in events)

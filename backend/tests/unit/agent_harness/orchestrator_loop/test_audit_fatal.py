"""
File: backend/tests/unit/agent_harness/orchestrator_loop/test_audit_fatal.py
Purpose: Verify Sprint 53.7 AD-Cat9-7 closure — _audit_log_safe propagates
    WORM append failures to AgentLoop's top-level handler instead of
    silently swallowing.
Category: Tests / Unit / 範疇 1 + 範疇 9 boundary
Scope: Sprint 53.7 US-4 / closes AD-Cat9-7

Description:
    Sprint 53.3 introduced AgentLoopImpl._audit_log_safe with a try/except
    that silently swallowed exceptions ("best-effort"). The 53.3 retrospective
    Q6 logged AD-Cat9-7: WORM audit log failure must escalate to FATAL because
    compliance forbids continuing without an audit record.

    Sprint 53.7 removes the swallow. This file pins:
      1. _audit_log_safe with audit_log=None is a no-op (regression sanity)
      2. _audit_log_safe propagates AuditAppendError when the underlying
         WORM append raises (the FATAL escalation path)
      3. _audit_log_safe propagates other exceptions too (defensive — no
         silent swallow of unexpected errors either)

Created: 2026-05-04 (Sprint 53.7 Day 3)

Related:
    - backend/src/agent_harness/orchestrator_loop/loop.py::_audit_log_safe
    - backend/src/agent_harness/guardrails/audit/worm_log.py::AuditAppendError
    - 53.3 retrospective Q6 AD-Cat9-7 origin
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from agent_harness._contracts import TraceContext
from agent_harness.guardrails import AuditAppendError
from agent_harness.orchestrator_loop.loop import AgentLoopImpl


def _make_loop(audit_log: object | None = None) -> AgentLoopImpl:
    """Minimal AgentLoopImpl with only the args _audit_log_safe touches."""
    loop = AgentLoopImpl.__new__(AgentLoopImpl)
    # Set just the attributes _audit_log_safe references; full construction
    # would pull in chat_client / parser / etc. which this test does not need.
    loop._audit_log = audit_log
    loop._tenant_id = uuid4() if audit_log is not None else None
    return loop


def _ctx() -> TraceContext:
    return TraceContext.create_root()


@pytest.mark.asyncio
async def test_audit_log_safe_noop_when_audit_log_is_none() -> None:
    """No audit_log → no-op (no exception)."""
    loop = _make_loop(audit_log=None)
    # Should not raise.
    await loop._audit_log_safe(
        event_type="test.event",
        content={"k": "v"},
        ctx=_ctx(),
    )


@pytest.mark.asyncio
async def test_audit_log_safe_propagates_audit_append_error() -> None:
    """AuditAppendError from WORM append must propagate (53.7 AD-Cat9-7 fix)."""
    mock_audit = AsyncMock()
    mock_audit.append.side_effect = AuditAppendError("simulated WORM write failure")
    loop = _make_loop(audit_log=mock_audit)

    with pytest.raises(AuditAppendError) as exc_info:
        await loop._audit_log_safe(
            event_type="guardrail.input.block",
            content={"reason": "test"},
            ctx=_ctx(),
        )
    assert "simulated WORM write failure" in str(exc_info.value)
    mock_audit.append.assert_awaited_once()


@pytest.mark.asyncio
async def test_audit_log_safe_propagates_arbitrary_exceptions() -> None:
    """Any exception from append (not just AuditAppendError) must propagate.

    Defensive: 53.3's broad ``except Exception`` was the bug; 53.7 removes
    the catch entirely so unexpected errors don't get silently lost either.
    """
    mock_audit = AsyncMock()
    mock_audit.append.side_effect = RuntimeError("unexpected DB driver error")
    loop = _make_loop(audit_log=mock_audit)

    with pytest.raises(RuntimeError) as exc_info:
        await loop._audit_log_safe(
            event_type="guardrail.tool.escalate",
            content={"tool": "x"},
            ctx=_ctx(),
        )
    assert "unexpected DB driver error" in str(exc_info.value)

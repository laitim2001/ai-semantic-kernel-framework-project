"""
File: backend/tests/integration/platform_layer/governance/hitl/test_manager.py
Purpose: Integration tests for DefaultHITLManager — request_approval / decide /
         get_pending / wait_for_decision / expire_overdue / escalate.
Category: Tests / Platform / Governance / HITL
Scope: Phase 53 / Sprint 53.4 US-2 Day 2

Created: 2026-05-03 (Sprint 53.4 Day 2)

Note: tests use the shared `db_session` fixture; we monkey-patch `session.commit`
to `session.flush` so HITLManager's commits become flushes that the fixture's
outer rollback can unwind. This keeps tests hermetic.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from agent_harness._contracts.hitl import (
    ApprovalDecision,
    ApprovalRequest,
    DecisionType,
    RiskLevel,
)
from infrastructure.db.models import Tenant, User
from infrastructure.db.models.sessions import Session as SessionModel
from platform_layer.governance.hitl.manager import DefaultHITLManager
from platform_layer.governance.hitl.state_machine import InvalidTransitionError
from tests.conftest import seed_tenant, seed_user

pytestmark = pytest.mark.asyncio


# --------------- Helpers --------------------------------------------------


async def _seed_session(db: AsyncSession, tenant: Tenant, user: User) -> SessionModel:
    s = SessionModel(
        tenant_id=tenant.id,
        user_id=user.id,
        title="hitl-test-session",
        status="active",
    )
    db.add(s)
    await db.flush()
    await db.refresh(s)
    return s


def _make_request(
    *,
    request_id=None,
    tenant_id,
    session_id,
    risk: RiskLevel = RiskLevel.MEDIUM,
    sla_hours: int = 4,
) -> ApprovalRequest:
    return ApprovalRequest(
        request_id=request_id or uuid4(),
        tenant_id=tenant_id,
        session_id=session_id,
        requester="tools",
        risk_level=risk,
        payload={"summary": "test action", "tool": "test_tool"},
        sla_deadline=datetime.now(timezone.utc) + timedelta(hours=sla_hours),
        context_snapshot={},
    )


@pytest_asyncio.fixture
async def hitl_setup(db_session: AsyncSession, monkeypatch):
    """Seed tenant + user + session; build HITLManager using the test session.

    HITLManager's commits are routed through session.flush() so that the
    fixture's outer rollback unwinds them.
    """
    tenant = await seed_tenant(db_session, code="HITL_TEST")
    user = await seed_user(db_session, tenant, email="hitl@test.com")
    session_row = await _seed_session(db_session, tenant, user)

    # Make HITLManager's commit() a no-op flush so outer rollback unwinds.
    async def _flush_only() -> None:
        await db_session.flush()

    monkeypatch.setattr(db_session, "commit", _flush_only)

    @asynccontextmanager
    async def factory():
        yield db_session

    manager = DefaultHITLManager(
        session_factory=factory,
        wait_poll_interval_s=0.05,
    )
    return manager, tenant, user, session_row


# --------------- Tests -----------------------------------------------------


async def test_request_approval_persists_pending(hitl_setup) -> None:
    manager, tenant, _, session_row = hitl_setup
    req = _make_request(tenant_id=tenant.id, session_id=session_row.id)
    rid = await manager.request_approval(req)
    assert rid == req.request_id

    pending = await manager.get_pending(tenant.id)
    assert len(pending) == 1
    assert pending[0].request_id == req.request_id
    assert pending[0].risk_level == RiskLevel.MEDIUM


async def test_decide_approved_transitions_state(hitl_setup) -> None:
    manager, tenant, _, session_row = hitl_setup
    req = _make_request(tenant_id=tenant.id, session_id=session_row.id)
    await manager.request_approval(req)

    decision = ApprovalDecision(
        request_id=req.request_id,
        decision=DecisionType.APPROVED,
        reviewer="alice@test.com",
        decided_at=datetime.now(timezone.utc),
        reason="looks fine",
    )
    await manager.decide(request_id=req.request_id, decision=decision)

    pending_after = await manager.get_pending(tenant.id)
    assert pending_after == []  # no longer pending


async def test_decide_rejected_terminal(hitl_setup) -> None:
    manager, tenant, _, session_row = hitl_setup
    req = _make_request(tenant_id=tenant.id, session_id=session_row.id)
    await manager.request_approval(req)

    decision = ApprovalDecision(
        request_id=req.request_id,
        decision=DecisionType.REJECTED,
        reviewer="bob@test.com",
        decided_at=datetime.now(timezone.utc),
        reason="risk too high",
    )
    await manager.decide(request_id=req.request_id, decision=decision)

    # Cannot transition again from rejected (terminal).
    second = ApprovalDecision(
        request_id=req.request_id,
        decision=DecisionType.APPROVED,
        reviewer="alice@test.com",
        decided_at=datetime.now(timezone.utc),
        reason="changed mind",
    )
    with pytest.raises(InvalidTransitionError):
        await manager.decide(request_id=req.request_id, decision=second)


async def test_decide_unknown_request_raises(hitl_setup) -> None:
    manager, _, _, _ = hitl_setup
    decision = ApprovalDecision(
        request_id=uuid4(),
        decision=DecisionType.APPROVED,
        reviewer="alice@test.com",
        decided_at=datetime.now(timezone.utc),
        reason=None,
    )
    with pytest.raises(LookupError):
        await manager.decide(request_id=decision.request_id, decision=decision)


async def test_tenant_isolation_get_pending(db_session: AsyncSession, monkeypatch) -> None:
    """Tenant A's reviewer cannot see tenant B's pending."""
    tenant_a = await seed_tenant(db_session, code="TENANT_A")
    tenant_b = await seed_tenant(db_session, code="TENANT_B")
    user_a = await seed_user(db_session, tenant_a, email="a@a.com")
    user_b = await seed_user(db_session, tenant_b, email="b@b.com")
    sess_a = await _seed_session(db_session, tenant_a, user_a)
    sess_b = await _seed_session(db_session, tenant_b, user_b)

    async def _flush_only() -> None:
        await db_session.flush()

    monkeypatch.setattr(db_session, "commit", _flush_only)

    @asynccontextmanager
    async def factory():
        yield db_session

    manager = DefaultHITLManager(session_factory=factory)
    await manager.request_approval(_make_request(tenant_id=tenant_a.id, session_id=sess_a.id))
    await manager.request_approval(_make_request(tenant_id=tenant_b.id, session_id=sess_b.id))

    pending_a = await manager.get_pending(tenant_a.id)
    pending_b = await manager.get_pending(tenant_b.id)
    assert len(pending_a) == 1
    assert len(pending_b) == 1
    assert pending_a[0].request_id != pending_b[0].request_id


async def test_expire_overdue_transitions_pending_to_expired(
    hitl_setup,
) -> None:
    manager, tenant, _, session_row = hitl_setup
    # Create approval already past deadline
    req = _make_request(tenant_id=tenant.id, session_id=session_row.id, sla_hours=-1)
    await manager.request_approval(req)

    count = await manager.expire_overdue()
    assert count >= 1

    # No longer pending; wait_for_decision returns REJECTED (expired fallback)
    decision = await manager.wait_for_decision(req.request_id, timeout_s=1)
    assert decision.decision == DecisionType.REJECTED


async def test_wait_for_decision_returns_after_decide(hitl_setup) -> None:
    manager, tenant, _, session_row = hitl_setup
    req = _make_request(tenant_id=tenant.id, session_id=session_row.id)
    await manager.request_approval(req)

    # Pre-decide so wait_for_decision finds it on first poll
    decision_in = ApprovalDecision(
        request_id=req.request_id,
        decision=DecisionType.APPROVED,
        reviewer="alice@test.com",
        decided_at=datetime.now(timezone.utc),
        reason="ok",
    )
    await manager.decide(request_id=req.request_id, decision=decision_in)

    decision_out = await manager.wait_for_decision(req.request_id, timeout_s=2)
    assert decision_out.decision == DecisionType.APPROVED


async def test_wait_for_decision_timeout(hitl_setup) -> None:
    manager, tenant, _, session_row = hitl_setup
    req = _make_request(tenant_id=tenant.id, session_id=session_row.id)
    await manager.request_approval(req)

    with pytest.raises(TimeoutError):
        await manager.wait_for_decision(req.request_id, timeout_s=1)


async def test_get_policy_returns_default(hitl_setup) -> None:
    manager, tenant, _, _ = hitl_setup
    policy = await manager.get_policy(tenant.id)
    assert policy.tenant_id == tenant.id
    assert policy.auto_approve_max_risk == RiskLevel.LOW


async def test_escalate_creates_new_pending_under_higher_role(
    hitl_setup,
) -> None:
    manager, tenant, _, session_row = hitl_setup
    req = _make_request(tenant_id=tenant.id, session_id=session_row.id)
    await manager.request_approval(req)

    new_id = await manager.escalate(
        request_id=req.request_id,
        new_role="senior_reviewer",
        reason="needs deeper review",
    )

    # Original is no longer pending; new one IS
    pending = await manager.get_pending(tenant.id)
    pending_ids = {p.request_id for p in pending}
    assert req.request_id not in pending_ids
    assert new_id in pending_ids


async def test_notifier_called_best_effort(db_session: AsyncSession, monkeypatch) -> None:
    """Notifier is invoked after persistence; raised exception does not block."""
    tenant = await seed_tenant(db_session, code="NOTIFY_TEST")
    user = await seed_user(db_session, tenant, email="x@x.com")
    sess = await _seed_session(db_session, tenant, user)

    async def _flush_only() -> None:
        await db_session.flush()

    monkeypatch.setattr(db_session, "commit", _flush_only)

    @asynccontextmanager
    async def factory():
        yield db_session

    notify_calls: list[ApprovalRequest] = []

    async def notifier(req: ApprovalRequest) -> None:
        notify_calls.append(req)
        raise RuntimeError("simulated webhook failure")  # must not propagate

    manager = DefaultHITLManager(
        session_factory=factory,
        notifier=notifier,
    )
    req = _make_request(tenant_id=tenant.id, session_id=sess.id)
    rid = await manager.request_approval(req)

    assert rid == req.request_id
    assert len(notify_calls) == 1  # called even though it raised

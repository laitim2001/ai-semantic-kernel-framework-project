"""
File: backend/tests/unit/infrastructure/db/test_governance_models_crud.py
Purpose: governance 3 表 CRUD + state machine + cross-tenant via session chain.
Category: Tests / Infrastructure / DB / Governance schema
Scope: Sprint 49.3 Day 3.5

Tests:
    1. test_approval_state_machine_pending_to_approved
    2. test_approval_state_machine_pending_to_rejected
    3. test_approval_pending_query_uses_partial_index
    4. test_risk_assessment_create_with_score
    5. test_guardrail_event_three_action_types
    6. test_governance_cross_tenant_via_session_chain — JOIN sessions to scope

NOTE: governance tables have NO direct tenant_id (junction via session).
Cross-tenant isolation must JOIN sessions on session_id and filter
sessions.tenant_id. RLS-level enforcement (any direct query missing the
JOIN) is tested in test_rls_enforcement.py at Day 4.

Created: 2026-04-29 (Sprint 49.3 Day 3.5)
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import Approval, GuardrailEvent, RiskAssessment, Session
from tests.conftest import seed_tenant, seed_user


@pytest.mark.asyncio
async def test_approval_state_machine_pending_to_approved(
    db_session: AsyncSession,
) -> None:
    """pending → approved: actor_user_id + decided_at populated."""
    t = await seed_tenant(db_session, code="APV_OK")
    u = await seed_user(db_session, t, email="apv_ok@gov.test")
    s = Session(tenant_id=t.id, user_id=u.id)
    db_session.add(s)
    await db_session.flush()

    a = Approval(
        session_id=s.id,
        action_type="tool_call",
        action_summary="Send mass email to all customers",
        action_payload={"tool": "send_email", "recipients": "all"},
        risk_level="high",
        risk_score=Decimal("0.85"),
        risk_reasoning="External communication; bulk audience",
        required_approver_role="ops_lead",
    )
    db_session.add(a)
    await db_session.flush()
    assert a.status == "pending"
    assert a.decided_at is None

    # Approve
    a.status = "approved"
    a.approver_user_id = u.id
    a.decided_at = datetime.now(timezone.utc)
    a.decision_reason = "Verified with customer success team."
    await db_session.flush()

    assert a.status == "approved"
    assert a.approver_user_id == u.id
    assert a.decided_at is not None


@pytest.mark.asyncio
async def test_approval_state_machine_pending_to_rejected(
    db_session: AsyncSession,
) -> None:
    """pending → rejected: decision_reason captures rationale."""
    t = await seed_tenant(db_session, code="APV_NO")
    u = await seed_user(db_session, t, email="apv_no@gov.test")
    s = Session(tenant_id=t.id, user_id=u.id)
    db_session.add(s)
    await db_session.flush()

    a = Approval(
        session_id=s.id,
        action_type="modify_data",
        action_summary="Bulk update customer records",
        action_payload={"table": "customers", "where": {"region": "EU"}},
        risk_level="critical",
    )
    db_session.add(a)
    await db_session.flush()

    a.status = "rejected"
    a.approver_user_id = u.id
    a.decided_at = datetime.now(timezone.utc)
    a.decision_reason = "GDPR compliance check failed."
    await db_session.flush()

    assert a.status == "rejected"
    assert "GDPR" in (a.decision_reason or "")


@pytest.mark.asyncio
async def test_approval_pending_query_uses_partial_index(
    db_session: AsyncSession,
) -> None:
    """idx_approvals_pending is partial WHERE status='pending';
    decided rows do NOT appear in pending queue."""
    t = await seed_tenant(db_session, code="APV_PQ")
    u = await seed_user(db_session, t, email="apv_pq@gov.test")
    s = Session(tenant_id=t.id, user_id=u.id)
    db_session.add(s)
    await db_session.flush()

    pending_a = Approval(
        session_id=s.id,
        action_type="send_email",
        action_summary="Send",
        action_payload={},
        risk_level="medium",
    )
    decided_a = Approval(
        session_id=s.id,
        action_type="send_email",
        action_summary="Send 2",
        action_payload={},
        risk_level="medium",
        status="approved",
        approver_user_id=u.id,
        decided_at=datetime.now(timezone.utc),
    )
    db_session.add_all([pending_a, decided_a])
    await db_session.flush()

    result = await db_session.execute(select(Approval).where(Approval.status == "pending"))
    pending_rows = list(result.scalars().all())
    assert len(pending_rows) == 1
    assert pending_rows[0].id == pending_a.id


@pytest.mark.asyncio
async def test_risk_assessment_create_with_score(db_session: AsyncSession) -> None:
    """RiskAssessment: score Numeric(3,2) + level + triggered_rules JSONB + requires_approval."""
    t = await seed_tenant(db_session, code="RSK_OK")
    u = await seed_user(db_session, t, email="rsk@gov.test")
    s = Session(tenant_id=t.id, user_id=u.id)
    db_session.add(s)
    await db_session.flush()

    r = RiskAssessment(
        session_id=s.id,
        risk_level="high",
        risk_score=Decimal("0.78"),
        triggered_rules=[
            {"rule": "outbound_email_to_external", "weight": 0.4},
            {"rule": "bulk_recipients", "weight": 0.38},
        ],
        reasoning="Aggregate of 2 policy hits exceeded threshold.",
        requires_approval=True,
    )
    db_session.add(r)
    await db_session.flush()
    assert r.id is not None
    assert r.risk_score == Decimal("0.78")
    assert r.requires_approval is True
    assert len(r.triggered_rules) == 2


@pytest.mark.asyncio
async def test_guardrail_event_three_action_types(db_session: AsyncSession) -> None:
    """GuardrailEvent: allow/block/tripwire_fired all writable; passed flag aligned."""
    t = await seed_tenant(db_session, code="GRD_3A")
    u = await seed_user(db_session, t, email="grd@gov.test")
    s = Session(tenant_id=t.id, user_id=u.id)
    db_session.add(s)
    await db_session.flush()

    events = [
        GuardrailEvent(
            session_id=s.id,
            layer="input",
            check_type="pii",
            passed=True,
            severity="info",
            action_taken="allow",
        ),
        GuardrailEvent(
            session_id=s.id,
            layer="output",
            check_type="toxicity",
            passed=False,
            severity="error",
            detected_pattern="Toxic phrase detected",
            action_taken="block",
        ),
        GuardrailEvent(
            session_id=None,  # pre-session input check
            layer="input",
            check_type="jailbreak",
            passed=False,
            severity="critical",
            detected_pattern="Prompt injection attempt",
            action_taken="tripwire_fired",
        ),
    ]
    db_session.add_all(events)
    await db_session.flush()

    # Partial idx_guardrail_events_failed only includes passed=FALSE rows
    failed = await db_session.execute(
        select(GuardrailEvent).where(GuardrailEvent.passed.is_(False))
    )
    failed_rows = list(failed.scalars().all())
    assert len(failed_rows) == 2
    actions = {r.action_taken for r in failed_rows}
    assert actions == {"block", "tripwire_fired"}


@pytest.mark.asyncio
async def test_governance_cross_tenant_via_session_chain(
    db_session: AsyncSession,
) -> None:
    """No direct tenant_id; cross-tenant scoping requires JOIN sessions.

    Tenant A's approval query (JOIN sessions WHERE tenant_id = A) does NOT
    return Tenant B's approvals.
    """
    t_a = await seed_tenant(db_session, code="GOV_X_A")
    t_b = await seed_tenant(db_session, code="GOV_X_B")
    u_a = await seed_user(db_session, t_a, email="a@gov_x.test")
    u_b = await seed_user(db_session, t_b, email="b@gov_x.test")
    s_a = Session(tenant_id=t_a.id, user_id=u_a.id)
    s_b = Session(tenant_id=t_b.id, user_id=u_b.id)
    db_session.add_all([s_a, s_b])
    await db_session.flush()

    db_session.add_all(
        [
            Approval(
                session_id=s_a.id,
                action_type="tool_call",
                action_summary="A action",
                action_payload={},
                risk_level="low",
            ),
            Approval(
                session_id=s_b.id,
                action_type="tool_call",
                action_summary="B action",
                action_payload={},
                risk_level="low",
            ),
        ]
    )
    await db_session.flush()

    # Tenant A scope: JOIN approvals → sessions WHERE tenant_id = A
    result = await db_session.execute(
        select(Approval)
        .join(Session, Approval.session_id == Session.id)
        .where(Session.tenant_id == t_a.id)
    )
    rows = list(result.scalars().all())
    assert len(rows) == 1
    assert rows[0].action_summary == "A action"

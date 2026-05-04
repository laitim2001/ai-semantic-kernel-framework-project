"""
File: backend/tests/integration/infrastructure/db/test_approval_status_constraint.py
Purpose: Verify that migration 0011 enforces the five-value CHECK constraint
    on approvals.status -- escalated (added 53.4) and expired (state-machine
    end state) must be accepted; arbitrary strings must be rejected at the
    DB layer.
Category: Tests / Integration / Infrastructure DB schema
Scope: Sprint 53.7 US-2 / closes AD-Hitl-8

Description:
    Migration 0011_approvals_status_check adds a CHECK constraint on
    approvals.status restricting values to one of:
        ('pending', 'approved', 'rejected', 'escalated').

    Sprint 53.4 added 'escalated' to the application enum (ApprovalDecision)
    but the DB column was a plain String(32) with no CHECK -- the schema
    accepted any string. This test pins the schema-level enforcement so a
    future regression (e.g. accidental constraint drop) fails CI.

    Pre-requisite: alembic upgrade head has been run after this test was
    added; that's already documented in backend/tests/conftest.py header.

Created: 2026-05-04 (Sprint 53.7 Day 2)

Related:
    - backend/src/infrastructure/db/migrations/versions/0011_approvals_status_check.py
    - backend/src/infrastructure/db/models/governance.py (Approval ORM)
    - 09-db-schema-design.md §approvals
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import Approval
from infrastructure.db.models import Session as SessionModel
from infrastructure.db.models import Tenant, User
from tests.conftest import seed_tenant, seed_user


async def _seed_session(db: AsyncSession, tenant: Tenant, user: User) -> SessionModel:
    s = SessionModel(
        tenant_id=tenant.id,
        user_id=user.id,
        title="status-check-test",
        status="active",
    )
    db.add(s)
    await db.flush()
    await db.refresh(s)
    return s


def _make_approval(session_id: UUID, *, status: str) -> Approval:
    """Build an Approval row with the four required-non-null columns + given status."""
    return Approval(
        id=uuid4(),
        session_id=session_id,
        action_type="test_action",
        action_summary="status-check test",
        action_payload={"summary": "test", "tool": "test_tool"},
        risk_level="MEDIUM",
        status=status,
    )


@pytest_asyncio.fixture
async def seeded_session(db_session: AsyncSession) -> SessionModel:
    tenant = await seed_tenant(db_session, code="STATUS_CHECK_TEST")
    user = await seed_user(db_session, tenant, email="status-check@test.com")
    return await _seed_session(db_session, tenant, user)


@pytest.mark.asyncio
async def test_status_escalated_is_accepted(
    db_session: AsyncSession, seeded_session: SessionModel
) -> None:
    """status='escalated' must be accepted by the new CHECK constraint."""
    approval = _make_approval(seeded_session.id, status="escalated")
    db_session.add(approval)
    await db_session.flush()  # Triggers INSERT; raises IntegrityError on CHECK fail.

    # Re-read confirms the value persisted.
    await db_session.refresh(approval)
    assert approval.status == "escalated"


@pytest.mark.asyncio
@pytest.mark.parametrize("good_status", ["pending", "approved", "rejected", "expired"])
async def test_status_existing_values_still_accepted(
    db_session: AsyncSession, seeded_session: SessionModel, good_status: str
) -> None:
    """All non-'escalated' valid values stay accepted after the migration."""
    approval = _make_approval(seeded_session.id, status=good_status)
    db_session.add(approval)
    await db_session.flush()
    await db_session.refresh(approval)
    assert approval.status == good_status


@pytest.mark.asyncio
async def test_status_unknown_string_is_rejected(
    db_session: AsyncSession, seeded_session: SessionModel
) -> None:
    """Any value outside the five-state enum must fail at the DB layer."""
    approval = _make_approval(seeded_session.id, status="unknown")
    db_session.add(approval)
    with pytest.raises(IntegrityError) as exc_info:
        await db_session.flush()
    # Confirm it's the named CHECK constraint, not e.g. an FK or NOT NULL.
    assert "approvals_status_check" in str(exc_info.value).lower()

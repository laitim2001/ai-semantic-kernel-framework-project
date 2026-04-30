"""
File: backend/tests/unit/infrastructure/db/test_memory_models_crud.py
Purpose: 5-layer memory CRUD + tenant isolation (memory_user via TenantScopedMixin).
Category: Tests / Infrastructure / DB / Memory schema
Scope: Sprint 49.3 Day 2.6

Tests:
    1. test_memory_system_global       — Layer 1: no tenant; UNIQUE(key)
    2. test_memory_tenant_scoped       — Layer 2: TenantScopedMixin; UNIQUE(tenant,key)
    3. test_memory_role_via_role       — Layer 3: junction via role_id; UNIQUE(role,key)
    4. test_memory_user_with_provenance — Layer 4: user_id + tenant + source/confidence
    5. test_memory_session_summary_unique — Layer 5: session_id UNIQUE
    6. test_memory_user_cross_tenant_via_filter — query-by-tenant_id excludes other tenant

NOTE on test 6: Sprint 49.3 Day 4 ships RLS policies + per-request
SET LOCAL middleware. Day 2 here only verifies that explicit
tenant_id filtering returns the right rows — RLS-level enforcement is
tested in test_rls_enforcement.py later.

Created: 2026-04-29 (Sprint 49.3 Day 2.6)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import (MemoryRole, MemorySessionSummary,
                                      MemorySystem, MemoryTenant, MemoryUser,
                                      Role, Session)
from tests.conftest import seed_tenant, seed_user


@pytest.mark.asyncio
async def test_memory_system_global(db_session: AsyncSession) -> None:
    """Layer 1: global; no tenant_id; UNIQUE on key."""
    m = MemorySystem(
        key="safety.no_pii_in_logs",
        category="safety",
        content="Never log raw email/phone/SSN; redact via PIIRedactor.",
        version=1,
    )
    db_session.add(m)
    await db_session.flush()

    found = await db_session.execute(
        select(MemorySystem).where(MemorySystem.key == "safety.no_pii_in_logs")
    )
    row = found.scalar_one()
    assert row.category == "safety"
    assert row.version == 1


@pytest.mark.asyncio
async def test_memory_tenant_scoped(db_session: AsyncSession) -> None:
    """Layer 2: TenantScopedMixin + UNIQUE(tenant_id, key)."""
    t = await seed_tenant(db_session, code="MEM_TEN")
    mt = MemoryTenant(
        tenant_id=t.id,
        key="playbook.incident_severity_p0",
        category="playbook",
        content="P0: customer-impacting outage; immediate page + war-room.",
        vector_id=None,
    )
    db_session.add(mt)
    await db_session.flush()

    result = await db_session.execute(
        select(MemoryTenant).where(
            (MemoryTenant.tenant_id == t.id)
            & (MemoryTenant.key == "playbook.incident_severity_p0")
        )
    )
    row = result.scalar_one()
    assert row.category == "playbook"


@pytest.mark.asyncio
async def test_memory_role_via_role(db_session: AsyncSession) -> None:
    """Layer 3: junction-style via role_id; tenant resolved via role chain."""
    t = await seed_tenant(db_session, code="MEM_ROLE")
    r = Role(
        tenant_id=t.id,
        code="ops_engineer",
        display_name="Ops Engineer",
        description="Operations engineer role",
    )
    db_session.add(r)
    await db_session.flush()

    mr = MemoryRole(
        role_id=r.id,
        key="workflow.daily_standup",
        category="workflow",
        content="Standup at 09:00; report blockers + ETA.",
    )
    db_session.add(mr)
    await db_session.flush()

    result = await db_session.execute(
        select(MemoryRole).where(MemoryRole.role_id == r.id)
    )
    row = result.scalar_one()
    assert row.category == "workflow"


@pytest.mark.asyncio
async def test_memory_user_with_provenance(db_session: AsyncSession) -> None:
    """Layer 4: TenantScopedMixin + user_id + provenance fields (source/confidence/expires)."""
    t = await seed_tenant(db_session, code="MEM_USR")
    u = await seed_user(db_session, t, email="prov@user.test")

    mu = MemoryUser(
        tenant_id=t.id,
        user_id=u.id,
        category="preference",
        content="Prefers morning briefings before 10am.",
        source="extracted",
        confidence=Decimal("0.85"),
        expires_at=datetime.now(timezone.utc) + timedelta(days=90),
    )
    db_session.add(mu)
    await db_session.flush()

    found = await db_session.execute(
        select(MemoryUser).where(
            (MemoryUser.tenant_id == t.id) & (MemoryUser.user_id == u.id)
        )
    )
    row = found.scalar_one()
    assert row.source == "extracted"
    assert row.confidence == Decimal("0.85")
    assert row.expires_at is not None


@pytest.mark.asyncio
async def test_memory_session_summary_unique(db_session: AsyncSession) -> None:
    """Layer 5: junction via session_id; UNIQUE on session_id."""
    t = await seed_tenant(db_session, code="MEM_SESS")
    u = await seed_user(db_session, t, email="ses@summary.test")
    s = Session(tenant_id=t.id, user_id=u.id)
    db_session.add(s)
    await db_session.flush()

    summary = MemorySessionSummary(
        session_id=s.id,
        summary="User asked X, agent did Y, decided Z.",
        key_decisions=[{"decision": "Z", "rationale": "..."}],
        unresolved_issues=[],
    )
    db_session.add(summary)
    await db_session.flush()

    result = await db_session.execute(
        select(MemorySessionSummary).where(MemorySessionSummary.session_id == s.id)
    )
    row = result.scalar_one()
    assert row.extracted_to_user_memory is False
    assert row.key_decisions == [{"decision": "Z", "rationale": "..."}]


@pytest.mark.asyncio
async def test_memory_user_cross_tenant_via_filter(
    db_session: AsyncSession,
) -> None:
    """Tenant-A query (with explicit tenant filter) does not see Tenant-B's
    memory_user rows. This verifies application-layer multi-tenant rule 2
    (all queries by tenant_id); RLS-level enforcement is in Day 4 tests.
    """
    t_a = await seed_tenant(db_session, code="MEM_X_A")
    t_b = await seed_tenant(db_session, code="MEM_X_B")
    u_a = await seed_user(db_session, t_a, email="a@cross.test")
    u_b = await seed_user(db_session, t_b, email="b@cross.test")

    # Tenant B writes a memory
    db_session.add(
        MemoryUser(
            tenant_id=t_b.id,
            user_id=u_b.id,
            category="fact",
            content="Tenant B secret note.",
        )
    )
    db_session.add(
        MemoryUser(
            tenant_id=t_a.id,
            user_id=u_a.id,
            category="fact",
            content="Tenant A note.",
        )
    )
    await db_session.flush()

    # Tenant A's tenant-filtered query sees only its own
    result = await db_session.execute(
        select(MemoryUser).where(MemoryUser.tenant_id == t_a.id)
    )
    rows = list(result.scalars().all())
    assert len(rows) == 1
    assert rows[0].content == "Tenant A note."
    assert rows[0].tenant_id == t_a.id

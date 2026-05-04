"""
File: backend/tests/unit/infrastructure/db/test_incident_model.py
Purpose: Incident ORM CRUD + multi-tenant isolation + CHECK constraint validation.
Category: Tests / Infrastructure / DB / Business domain
Scope: Sprint 55.1 / Day 1.4

Tests (5):
    1. test_incident_create — INSERT row + verify all columns populated
    2. test_incident_tenant_filter — 2 tenants, query each → only own incidents
    3. test_incident_severity_check_constraint — invalid severity → IntegrityError
    4. test_incident_status_default_open — no status passed → defaults to "open"
    5. test_incident_tenant_cascade_delete — DELETE tenant → CASCADE deletes incidents

Created: 2026-05-04 (Sprint 55.1 Day 1)
"""

from __future__ import annotations

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import Incident, Tenant
from tests.conftest import seed_tenant, seed_user


@pytest.mark.asyncio
async def test_incident_create(db_session: AsyncSession) -> None:
    """INSERT incident; verify all columns + server defaults populated."""
    t = await seed_tenant(db_session, code="INC_CR")
    u = await seed_user(db_session, t, email="creator@inc.test")

    inc = Incident(
        tenant_id=t.id,
        user_id=u.id,
        title="Production DB outage at us-east-1",
        severity="critical",
        alert_ids=["alert-101", "alert-102"],
    )
    db_session.add(inc)
    await db_session.flush()

    assert inc.id is not None
    assert inc.tenant_id == t.id
    assert inc.user_id == u.id
    assert inc.title == "Production DB outage at us-east-1"
    assert inc.severity == "critical"
    assert inc.status == "open"  # server_default
    assert inc.alert_ids == ["alert-101", "alert-102"]
    assert inc.resolution is None
    assert inc.created_at is not None
    assert inc.updated_at is not None
    assert inc.closed_at is None


@pytest.mark.asyncio
async def test_incident_tenant_filter(db_session: AsyncSession) -> None:
    """2 tenants, each creates 1 incident; per-tenant query returns only own row."""
    t_a = await seed_tenant(db_session, code="INC_A")
    t_b = await seed_tenant(db_session, code="INC_B")

    inc_a = Incident(tenant_id=t_a.id, title="A's outage", severity="high")
    inc_b = Incident(tenant_id=t_b.id, title="B's outage", severity="medium")
    db_session.add_all([inc_a, inc_b])
    await db_session.flush()

    # Tenant A perspective
    rows_a = (
        (await db_session.execute(select(Incident).where(Incident.tenant_id == t_a.id)))
        .scalars()
        .all()
    )
    assert len(rows_a) == 1
    assert rows_a[0].title == "A's outage"

    # Tenant B perspective
    rows_b = (
        (await db_session.execute(select(Incident).where(Incident.tenant_id == t_b.id)))
        .scalars()
        .all()
    )
    assert len(rows_b) == 1
    assert rows_b[0].title == "B's outage"


@pytest.mark.asyncio
async def test_incident_severity_check_constraint(
    db_session: AsyncSession,
) -> None:
    """severity='extreme' (not in CHECK list) → IntegrityError on flush."""
    t = await seed_tenant(db_session, code="INC_BAD")

    inc = Incident(
        tenant_id=t.id,
        title="Bad severity",
        severity="extreme",  # not allowed
    )
    db_session.add(inc)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_incident_status_default_open(db_session: AsyncSession) -> None:
    """No status passed → server_default 'open' applies."""
    t = await seed_tenant(db_session, code="INC_DEF")

    inc = Incident(tenant_id=t.id, title="Status default test")
    db_session.add(inc)
    await db_session.flush()

    # Refresh to reload server_default
    await db_session.refresh(inc)
    assert inc.status == "open"
    assert inc.severity == "high"  # also server_default


@pytest.mark.asyncio
async def test_incident_tenant_cascade_delete(db_session: AsyncSession) -> None:
    """DELETE tenant → CASCADE deletes its incidents."""
    t = await seed_tenant(db_session, code="INC_CAS")

    inc = Incident(tenant_id=t.id, title="To be cascaded", severity="low")
    db_session.add(inc)
    await db_session.flush()
    incident_id = inc.id

    # DELETE tenant → cascade
    await db_session.execute(delete(Tenant).where(Tenant.id == t.id))
    await db_session.flush()

    remaining = (
        (await db_session.execute(select(Incident).where(Incident.id == incident_id)))
        .scalars()
        .all()
    )
    assert remaining == [], "Incident should have been cascade-deleted"

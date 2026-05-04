"""
File: backend/tests/unit/business_domain/incident/test_service.py
Purpose: IncidentService — 12 unit tests covering CRUD + tenant isolation + 422 + audit.
Category: Tests / Business Domain / incident
Scope: Sprint 55.1 / Day 2.4

Tests:
    1.  test_create_returns_incident
    2.  test_create_default_severity_high
    3.  test_create_emits_audit
    4.  test_list_filters_by_severity
    5.  test_list_filters_by_status
    6.  test_list_pagination_limit
    7.  test_get_returns_none_when_not_found
    8.  test_get_cross_tenant_returns_none
    9.  test_update_status_transitions
    10. test_update_status_cross_tenant_raises
    11. test_close_sets_closed_at_now
    12. test_close_empty_resolution_raises_value_error

Created: 2026-05-04 (Sprint 55.1 Day 2)
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from business_domain.incident.service import IncidentService
from infrastructure.db.models import AuditLog
from tests.conftest import seed_tenant, seed_user

# ===== create =========================================================


@pytest.mark.asyncio
async def test_create_returns_incident(db_session: AsyncSession) -> None:
    t = await seed_tenant(db_session, code="INC_S_C1")
    svc = IncidentService(db=db_session, tenant_id=t.id)

    inc = await svc.create(title="DB outage", severity="critical", alert_ids=["a1", "a2"])

    assert inc.id is not None
    assert inc.tenant_id == t.id
    assert inc.title == "DB outage"
    assert inc.severity == "critical"
    assert inc.status == "open"
    assert inc.alert_ids == ["a1", "a2"]


@pytest.mark.asyncio
async def test_create_default_severity_high(db_session: AsyncSession) -> None:
    t = await seed_tenant(db_session, code="INC_S_C2")
    svc = IncidentService(db=db_session, tenant_id=t.id)

    inc = await svc.create(title="Default sev")
    assert inc.severity == "high"


@pytest.mark.asyncio
async def test_create_emits_audit(db_session: AsyncSession) -> None:
    t = await seed_tenant(db_session, code="INC_S_C3")
    u = await seed_user(db_session, t, email="auditor@inc.test")
    svc = IncidentService(db=db_session, tenant_id=t.id)

    inc = await svc.create(title="Audited create", user_id=u.id)

    audits = (
        (
            await db_session.execute(
                select(AuditLog).where(
                    AuditLog.tenant_id == t.id,
                    AuditLog.operation == "incident_create",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(audits) == 1
    assert audits[0].resource_id == str(inc.id)
    assert audits[0].user_id == u.id


# ===== list ===========================================================


@pytest.mark.asyncio
async def test_list_filters_by_severity(db_session: AsyncSession) -> None:
    t = await seed_tenant(db_session, code="INC_S_L1")
    svc = IncidentService(db=db_session, tenant_id=t.id)

    await svc.create(title="A high", severity="high")
    await svc.create(title="B low", severity="low")
    await svc.create(title="C high", severity="high")

    result = await svc.list(severity="high")
    assert len(result) == 2
    assert {r.title for r in result} == {"A high", "C high"}


@pytest.mark.asyncio
async def test_list_filters_by_status(db_session: AsyncSession) -> None:
    t = await seed_tenant(db_session, code="INC_S_L2")
    svc = IncidentService(db=db_session, tenant_id=t.id)

    inc1 = await svc.create(title="open one", severity="medium")
    inc2 = await svc.create(title="will-close", severity="medium")
    await svc.update_status(incident_id=inc2.id, status="investigating")

    open_list = await svc.list(status="open")
    invest_list = await svc.list(status="investigating")
    assert len(open_list) == 1 and open_list[0].id == inc1.id
    assert len(invest_list) == 1 and invest_list[0].id == inc2.id


@pytest.mark.asyncio
async def test_list_pagination_limit(db_session: AsyncSession) -> None:
    t = await seed_tenant(db_session, code="INC_S_L3")
    svc = IncidentService(db=db_session, tenant_id=t.id)

    for i in range(7):
        await svc.create(title=f"#{i}", severity="low")

    result = await svc.list(limit=3)
    assert len(result) == 3


# ===== get ============================================================


@pytest.mark.asyncio
async def test_get_returns_none_when_not_found(db_session: AsyncSession) -> None:
    t = await seed_tenant(db_session, code="INC_S_G1")
    svc = IncidentService(db=db_session, tenant_id=t.id)

    result = await svc.get(incident_id=uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_get_cross_tenant_returns_none(db_session: AsyncSession) -> None:
    """Tenant A creates incident; Tenant B's service.get() returns None (hide existence)."""
    t_a = await seed_tenant(db_session, code="INC_S_GA")
    t_b = await seed_tenant(db_session, code="INC_S_GB")
    svc_a = IncidentService(db=db_session, tenant_id=t_a.id)
    svc_b = IncidentService(db=db_session, tenant_id=t_b.id)

    inc_a = await svc_a.create(title="A's secret", severity="high")
    result = await svc_b.get(incident_id=inc_a.id)
    assert result is None


# ===== update_status ==================================================


@pytest.mark.asyncio
async def test_update_status_transitions(db_session: AsyncSession) -> None:
    t = await seed_tenant(db_session, code="INC_S_U1")
    svc = IncidentService(db=db_session, tenant_id=t.id)

    inc = await svc.create(title="To investigate", severity="medium")
    updated = await svc.update_status(incident_id=inc.id, status="investigating")
    assert updated.status == "investigating"

    updated2 = await svc.update_status(incident_id=inc.id, status="resolved")
    assert updated2.status == "resolved"


@pytest.mark.asyncio
async def test_update_status_cross_tenant_raises(db_session: AsyncSession) -> None:
    t_a = await seed_tenant(db_session, code="INC_S_UA")
    t_b = await seed_tenant(db_session, code="INC_S_UB")
    svc_a = IncidentService(db=db_session, tenant_id=t_a.id)
    svc_b = IncidentService(db=db_session, tenant_id=t_b.id)

    inc_a = await svc_a.create(title="A's incident", severity="high")
    with pytest.raises(ValueError, match="not found in tenant scope"):
        await svc_b.update_status(incident_id=inc_a.id, status="resolved")


# ===== close ==========================================================


@pytest.mark.asyncio
async def test_close_sets_closed_at_now(db_session: AsyncSession) -> None:
    t = await seed_tenant(db_session, code="INC_S_CL1")
    svc = IncidentService(db=db_session, tenant_id=t.id)

    inc = await svc.create(title="To close", severity="low")
    closed = await svc.close(incident_id=inc.id, resolution="Replaced cert; service restored.")
    assert closed.status == "closed"
    assert closed.closed_at is not None
    assert closed.resolution == "Replaced cert; service restored."


@pytest.mark.asyncio
async def test_close_empty_resolution_raises_value_error(
    db_session: AsyncSession,
) -> None:
    t = await seed_tenant(db_session, code="INC_S_CL2")
    svc = IncidentService(db=db_session, tenant_id=t.id)

    inc = await svc.create(title="No resolution attempt", severity="low")
    with pytest.raises(ValueError, match="resolution must be non-empty"):
        await svc.close(incident_id=inc.id, resolution="   ")  # whitespace only

    # Verify state unchanged
    fresh = await svc.get(incident_id=inc.id)
    assert fresh is not None
    assert fresh.status == "open"
    assert fresh.closed_at is None

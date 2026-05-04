"""
File: backend/tests/unit/business_domain/test_readonly_services.py
Purpose: 8 unit tests for the 4 read-only domain services (Sprint 55.1 US-3).
Category: Tests / Business Domain / 4 read-only services
Scope: Sprint 55.1 / Day 3.2

Tests:
    Patrol (2):       get_results / get_results_deterministic
    Correlation (2):  get_related / get_related_invalid_depth_raises
    RootCause (2):    diagnose / diagnose_cross_tenant_raises
    Audit (2):        query_logs_filters / query_logs_empty_when_no_match

Created: 2026-05-04 (Sprint 55.1 Day 3)
"""

from __future__ import annotations

import time
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from business_domain.audit_domain.service import AuditService
from business_domain.correlation.service import CorrelationService
from business_domain.incident.service import IncidentService
from business_domain.patrol.service import PatrolService
from business_domain.rootcause.service import RootCauseService
from infrastructure.db.audit_helper import append_audit
from tests.conftest import seed_tenant

# ===== Patrol =========================================================


@pytest.mark.asyncio
async def test_patrol_get_results(db_session: AsyncSession) -> None:
    t = await seed_tenant(db_session, code="P_1")
    svc = PatrolService(db=db_session, tenant_id=t.id)
    result = await svc.get_results(patrol_id="patrol-001")
    assert result["patrol_id"] == "patrol-001"
    assert result["health"] in ("healthy", "degraded")
    assert isinstance(result["servers_checked"], list)


@pytest.mark.asyncio
async def test_patrol_get_results_deterministic(db_session: AsyncSession) -> None:
    """Same patrol_id → same result (deterministic stub)."""
    t = await seed_tenant(db_session, code="P_2")
    svc = PatrolService(db=db_session, tenant_id=t.id)
    r1 = await svc.get_results(patrol_id="patrol-X")
    r2 = await svc.get_results(patrol_id="patrol-X")
    assert r1 == r2


# ===== Correlation =====================================================


@pytest.mark.asyncio
async def test_correlation_get_related(db_session: AsyncSession) -> None:
    t = await seed_tenant(db_session, code="C_1")
    svc = CorrelationService(db=db_session, tenant_id=t.id)
    result = await svc.get_related(alert_id="alert-A", depth=2)
    assert len(result) == 4  # depth=2 → 4 related
    assert all(r["tenant_id"] == str(t.id) for r in result)


@pytest.mark.asyncio
async def test_correlation_get_related_invalid_depth_raises(
    db_session: AsyncSession,
) -> None:
    t = await seed_tenant(db_session, code="C_2")
    svc = CorrelationService(db=db_session, tenant_id=t.id)
    with pytest.raises(ValueError, match="Invalid depth"):
        await svc.get_related(alert_id="alert-Y", depth=99)


# ===== RootCause =======================================================


@pytest.mark.asyncio
async def test_rootcause_diagnose(db_session: AsyncSession) -> None:
    t = await seed_tenant(db_session, code="R_1")
    inc_svc = IncidentService(db=db_session, tenant_id=t.id)
    inc = await inc_svc.create(title="Diagnostic test", severity="high")

    rc_svc = RootCauseService(db=db_session, tenant_id=t.id)
    result = await rc_svc.diagnose(incident_id=inc.id)
    assert result["incident_id"] == str(inc.id)
    assert result["status"] == "open"
    assert result["stage"] == "triage_required"


@pytest.mark.asyncio
async def test_rootcause_diagnose_cross_tenant_raises(
    db_session: AsyncSession,
) -> None:
    t_a = await seed_tenant(db_session, code="R_A")
    t_b = await seed_tenant(db_session, code="R_B")

    inc_svc_a = IncidentService(db=db_session, tenant_id=t_a.id)
    inc_a = await inc_svc_a.create(title="A's incident", severity="medium")

    rc_svc_b = RootCauseService(db=db_session, tenant_id=t_b.id)
    with pytest.raises(ValueError, match="not found in tenant scope"):
        await rc_svc_b.diagnose(incident_id=inc_a.id)


# ===== Audit ===========================================================


@pytest.mark.asyncio
async def test_audit_query_logs_filters(db_session: AsyncSession) -> None:
    t = await seed_tenant(db_session, code="A_1")
    now_ms = int(time.time() * 1000)
    await append_audit(
        session=db_session,
        tenant_id=t.id,
        operation="custom_op_alpha",
        resource_type="dummy",
        operation_data={"foo": "bar"},
        timestamp_ms=now_ms,
    )
    await append_audit(
        session=db_session,
        tenant_id=t.id,
        operation="custom_op_beta",
        resource_type="dummy",
        operation_data={"baz": 1},
        timestamp_ms=now_ms + 1000,
    )

    svc = AuditService(db=db_session, tenant_id=t.id)
    rows = await svc.query_logs(operation="custom_op_alpha")
    assert len(rows) == 1
    assert rows[0]["operation"] == "custom_op_alpha"


@pytest.mark.asyncio
async def test_audit_query_logs_empty_when_no_match(
    db_session: AsyncSession,
) -> None:
    t = await seed_tenant(db_session, code="A_2")
    svc = AuditService(db=db_session, tenant_id=t.id)
    rows = await svc.query_logs(operation=f"never-existed-{uuid4().hex}")
    assert rows == []

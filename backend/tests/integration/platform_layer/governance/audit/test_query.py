"""
File: backend/tests/integration/platform_layer/governance/audit/test_query.py
Purpose: Integration tests for AuditQuery — paginated read with tenant isolation + filters.
Category: Tests / Platform / Governance / Audit
Scope: Phase 53 / Sprint 53.4 US-4

Created: 2026-05-03 (Sprint 53.4 Day 4)
"""

from __future__ import annotations

import time

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import Tenant, User
from infrastructure.db.models.audit import AuditLog
from platform_layer.governance.audit.query import AuditQuery, AuditQueryFilter
from tests.conftest import seed_tenant, seed_user

pytestmark = pytest.mark.asyncio


async def _seed_audit_row(
    db: AsyncSession,
    *,
    tenant: Tenant,
    user: User,
    operation: str,
    resource_type: str = "test",
    timestamp_ms: int | None = None,
) -> AuditLog:
    row = AuditLog(
        tenant_id=tenant.id,
        user_id=user.id,
        operation=operation,
        resource_type=resource_type,
        resource_id=None,
        operation_data={"detail": operation},
        operation_result="ok",
        previous_log_hash="0" * 64,
        current_log_hash="1" * 64,
        timestamp_ms=timestamp_ms or int(time.time() * 1000),
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def test_list_filters_by_tenant_isolation(db_session: AsyncSession) -> None:
    """Tenant A query MUST NOT see tenant B audit rows."""
    tenant_a = await seed_tenant(db_session, code="AQ_A")
    tenant_b = await seed_tenant(db_session, code="AQ_B")
    user_a = await seed_user(db_session, tenant_a, email="a@aq.com")
    user_b = await seed_user(db_session, tenant_b, email="b@aq.com")

    await _seed_audit_row(db_session, tenant=tenant_a, user=user_a, operation="opA1")
    await _seed_audit_row(db_session, tenant=tenant_a, user=user_a, operation="opA2")
    await _seed_audit_row(db_session, tenant=tenant_b, user=user_b, operation="opB1")

    aq = AuditQuery(db_session)
    res_a = await aq.list(AuditQueryFilter(tenant_id=tenant_a.id))
    res_b = await aq.list(AuditQueryFilter(tenant_id=tenant_b.id))

    assert {r.operation for r in res_a} == {"opA1", "opA2"}
    assert {r.operation for r in res_b} == {"opB1"}


async def test_list_filters_by_operation(db_session: AsyncSession) -> None:
    tenant = await seed_tenant(db_session, code="AQ_OP")
    user = await seed_user(db_session, tenant, email="op@aq.com")

    await _seed_audit_row(db_session, tenant=tenant, user=user, operation="hitl.requested")
    await _seed_audit_row(db_session, tenant=tenant, user=user, operation="hitl.decided")
    await _seed_audit_row(db_session, tenant=tenant, user=user, operation="guardrail.tool.escalate")

    aq = AuditQuery(db_session)
    res = await aq.list(AuditQueryFilter(tenant_id=tenant.id, operation="hitl.requested"))
    assert len(res) == 1
    assert res[0].operation == "hitl.requested"


async def test_list_pagination(db_session: AsyncSession) -> None:
    tenant = await seed_tenant(db_session, code="AQ_PAGE")
    user = await seed_user(db_session, tenant, email="page@aq.com")

    base_ts = int(time.time() * 1000)
    for i in range(5):
        await _seed_audit_row(
            db_session,
            tenant=tenant,
            user=user,
            operation=f"op{i}",
            timestamp_ms=base_ts + i,
        )

    aq = AuditQuery(db_session)
    page1 = await aq.list(AuditQueryFilter(tenant_id=tenant.id, limit=2, offset=0))
    page2 = await aq.list(AuditQueryFilter(tenant_id=tenant.id, limit=2, offset=2))

    assert len(page1) == 2
    assert len(page2) == 2
    # Sorted desc on timestamp_ms; page1 should have highest timestamps
    assert page1[0].timestamp_ms > page2[0].timestamp_ms


async def test_list_filters_by_time_range(db_session: AsyncSession) -> None:
    tenant = await seed_tenant(db_session, code="AQ_TIME")
    user = await seed_user(db_session, tenant, email="time@aq.com")

    base_ts = 1_700_000_000_000
    await _seed_audit_row(
        db_session, tenant=tenant, user=user, operation="early", timestamp_ms=base_ts
    )
    await _seed_audit_row(
        db_session,
        tenant=tenant,
        user=user,
        operation="middle",
        timestamp_ms=base_ts + 1000,
    )
    await _seed_audit_row(
        db_session,
        tenant=tenant,
        user=user,
        operation="late",
        timestamp_ms=base_ts + 2000,
    )

    aq = AuditQuery(db_session)
    res = await aq.list(
        AuditQueryFilter(
            tenant_id=tenant.id,
            from_ts_ms=base_ts + 500,
            to_ts_ms=base_ts + 1500,
        )
    )
    assert len(res) == 1
    assert res[0].operation == "middle"


async def test_list_filter_unknown_operation_returns_empty(
    db_session: AsyncSession,
) -> None:
    tenant = await seed_tenant(db_session, code="AQ_EMPTY")
    user = await seed_user(db_session, tenant, email="e@aq.com")
    await _seed_audit_row(db_session, tenant=tenant, user=user, operation="real_op")

    aq = AuditQuery(db_session)
    res = await aq.list(AuditQueryFilter(tenant_id=tenant.id, operation="never_logged"))
    assert res == []


async def test_limit_capped_at_1000(db_session: AsyncSession) -> None:
    """Defensive: requested limit > 1000 is capped."""
    tenant = await seed_tenant(db_session, code="AQ_CAP")
    user = await seed_user(db_session, tenant, email="cap@aq.com")
    await _seed_audit_row(db_session, tenant=tenant, user=user, operation="x")

    aq = AuditQuery(db_session)
    # Insufficient rows to expose the cap, but verifies the SQL still runs.
    res = await aq.list(AuditQueryFilter(tenant_id=tenant.id, limit=100_000))
    assert len(res) == 1

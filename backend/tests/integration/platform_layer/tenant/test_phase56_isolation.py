"""
File: backend/tests/integration/platform_layer/tenant/test_phase56_isolation.py
Purpose: Phase 56.1 multi-tenant isolation regression tests (RLS + cross-domain).
Category: Tests / Integration / Platform Layer / Tenant
Scope: Sprint 56.1 / Day 4 / US-5 RLS Hardening + cross-domain isolation

Description:
    Two test groups (5 tests total):

    A. RLS smoke regression (3 tests):
        Verifies that the existing RLS pattern (SET LOCAL app.tenant_id)
        still enforces tenant isolation on `memory_user` (canonical
        TenantScopedMixin table) after Phase 56.1 schema changes (0014
        tenant state Enum + 0015 feature_flags). Phase 56.1 did NOT touch
        any RLS table; these tests are the regression baseline.

    B. Cross-domain isolation (2 tests):
        Tenant A and Tenant B exercise the full Phase 56.1 lifecycle in
        parallel; quota counters, onboarding progress, and feature flag
        overrides remain independent. Audit chain rows for tenant
        lifecycle ops preserve hash chain integrity.

Pattern reuse:
    - RLS helpers from `tests/unit/infrastructure/db/test_rls_enforcement.py`
      (re-implemented locally since they're private to that file)
    - QuotaEnforcer fakeredis pattern from Day 2 `test_quota.py`

Created: 2026-05-06 (Sprint 56.1 Day 4)
"""

from __future__ import annotations

from uuid import UUID

import pytest
from fakeredis.aioredis import FakeRedis
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.audit_helper import append_audit
from infrastructure.db.models import AuditLog, MemoryUser
from infrastructure.db.models.identity import Tenant, TenantState
from platform_layer.tenant.lifecycle import TenantLifecycle
from platform_layer.tenant.onboarding import OnboardingTracker
from platform_layer.tenant.plans import PlanLoader, reset_plan_loader
from platform_layer.tenant.quota import QuotaEnforcer
from tests.conftest import seed_tenant, seed_user

pytestmark = pytest.mark.asyncio


# Tables that rls_app_role needs to query (subset of 0009 RLS bootstrap).
_RLS_TEST_TABLES = (
    "users",
    "roles",
    "sessions",
    "messages",
    "message_events",
    "tool_calls",
    "state_snapshots",
    "loop_states",
    "api_keys",
    "rate_limits",
    "audit_log",
    "memory_tenant",
    "memory_user",
    "tenants",
    "tool_results",
    "user_roles",
    "role_permissions",
)


async def _ensure_rls_app_role(session: AsyncSession) -> None:
    """Create rls_app_role NOLOGIN (no superuser, no BYPASSRLS) if absent."""
    await session.execute(text("""
            DO $$
            BEGIN
                CREATE ROLE rls_app_role NOLOGIN;
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END
            $$;
            """))
    grants = ", ".join(_RLS_TEST_TABLES)
    await session.execute(text(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {grants} TO rls_app_role"))
    await session.execute(text("GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO rls_app_role"))


async def _set_app_tenant(session: AsyncSession, tenant_id: UUID) -> None:
    await session.execute(
        text("SELECT set_config('app.tenant_id', :tid, true)"),
        {"tid": str(tenant_id)},
    )


# ---------------------------------------------------------------------
# A. RLS smoke regression (3 tests) — Phase 56.1 schema changes do not
#    break the canonical RLS enforcement path.
# ---------------------------------------------------------------------


async def test_rls_phase56_no_tenant_set_blocks_select(
    db_session: AsyncSession,
) -> None:
    """rls_app_role with no app.tenant_id → SELECT returns 0 rows."""
    await _ensure_rls_app_role(db_session)

    t = await seed_tenant(db_session, code="P56_NS")
    u = await seed_user(db_session, t, email="ns@p56.test")
    db_session.add(MemoryUser(tenant_id=t.id, user_id=u.id, category="fact", content="hidden"))
    await db_session.flush()

    await db_session.execute(text("SET LOCAL ROLE rls_app_role"))

    rows = (await db_session.execute(select(MemoryUser))).scalars().all()
    assert rows == []


async def test_rls_phase56_correct_tenant_set_returns_own_rows(
    db_session: AsyncSession,
) -> None:
    """rls_app_role with app.tenant_id=A → only tenant A rows visible."""
    await _ensure_rls_app_role(db_session)

    t_a = await seed_tenant(db_session, code="P56_A")
    t_b = await seed_tenant(db_session, code="P56_B")
    u_a = await seed_user(db_session, t_a, email="a@p56.test")
    u_b = await seed_user(db_session, t_b, email="b@p56.test")
    db_session.add_all(
        [
            MemoryUser(tenant_id=t_a.id, user_id=u_a.id, category="fact", content="A"),
            MemoryUser(tenant_id=t_b.id, user_id=u_b.id, category="fact", content="B"),
        ]
    )
    await db_session.flush()

    await db_session.execute(text("SET LOCAL ROLE rls_app_role"))
    await _set_app_tenant(db_session, t_a.id)

    rows = (await db_session.execute(select(MemoryUser))).scalars().all()
    assert len(rows) == 1
    assert rows[0].tenant_id == t_a.id


async def test_rls_phase56_cross_tenant_invisible(db_session: AsyncSession) -> None:
    """Tenant A SET LOCAL → tenant B's rows invisible."""
    await _ensure_rls_app_role(db_session)

    t_a = await seed_tenant(db_session, code="P56_X_A")
    t_b = await seed_tenant(db_session, code="P56_X_B")
    u_b = await seed_user(db_session, t_b, email="xb@p56.test")
    db_session.add(
        MemoryUser(tenant_id=t_b.id, user_id=u_b.id, category="fact", content="B-secret")
    )
    await db_session.flush()

    await db_session.execute(text("SET LOCAL ROLE rls_app_role"))
    await _set_app_tenant(db_session, t_a.id)

    rows = (await db_session.execute(select(MemoryUser))).scalars().all()
    assert rows == []  # Tenant B row invisible to A.


# ---------------------------------------------------------------------
# B. Cross-domain isolation (2 tests) — Phase 56.1 lifecycle operations
#    on parallel tenants do not interfere across quota / onboarding /
#    audit chain.
# ---------------------------------------------------------------------


@pytest.fixture
async def fake_redis():  # type: ignore[no-untyped-def]
    client = FakeRedis(decode_responses=False)
    yield client
    await client.aclose()


async def test_full_lifecycle_multi_tenant_isolation(
    db_session: AsyncSession, fake_redis  # type: ignore[no-untyped-def]
) -> None:
    """A and B exercise lifecycle in parallel; quota + onboarding stay independent."""
    reset_plan_loader()
    plan_loader = PlanLoader()

    tenant_a = await seed_tenant(db_session, code="iso-a")
    tenant_a.state = TenantState.PROVISIONING
    tenant_b = await seed_tenant(db_session, code="iso-b")
    tenant_b.state = TenantState.PROVISIONING
    await db_session.flush()

    quota = QuotaEnforcer(client=fake_redis, plan_loader=plan_loader)

    # A reserves 5_000; B reserves 2_000 — independent counters.
    await quota.check_and_reserve(
        tenant_id=tenant_a.id, plan_name="enterprise", estimated_tokens=5_000
    )
    await quota.check_and_reserve(
        tenant_id=tenant_b.id, plan_name="enterprise", estimated_tokens=2_000
    )
    assert await quota.get_usage(tenant_a.id) == 5_000
    assert await quota.get_usage(tenant_b.id) == 2_000

    # A advances 3 onboarding steps; B advances 1. Progress JSONB isolated.
    tracker = OnboardingTracker(db_session)
    for step in ("company_info", "plan_selected", "memory_uploaded"):
        await tracker.advance(tenant_a.id, step)
    await tracker.advance(tenant_b.id, "company_info")

    snap_a = await tracker.get_progress(tenant_a.id)
    snap_b = await tracker.get_progress(tenant_b.id)
    assert sorted(snap_a["completed_steps"]) == [
        "company_info",
        "memory_uploaded",
        "plan_selected",
    ]
    assert snap_b["completed_steps"] == ["company_info"]

    # State transitions are also isolated.
    lifecycle = TenantLifecycle(db_session)
    await lifecycle.transition(tenant_a.id, TenantState.PROVISION_FAILED)
    refreshed_a = (
        await db_session.execute(select(Tenant).where(Tenant.id == tenant_a.id))
    ).scalar_one()
    refreshed_b = (
        await db_session.execute(select(Tenant).where(Tenant.id == tenant_b.id))
    ).scalar_one()
    assert refreshed_a.state == TenantState.PROVISION_FAILED
    assert refreshed_b.state == TenantState.PROVISIONING  # untouched


async def test_audit_chain_after_lifecycle_ops(db_session: AsyncSession) -> None:
    """Audit chain integrity preserved across tenant lifecycle ops."""
    tenant_a = await seed_tenant(db_session, code="aud-a")
    tenant_b = await seed_tenant(db_session, code="aud-b")

    # Append 2 audit rows for A; 1 for B. Each tenant's chain is independent.
    await append_audit(
        db_session,
        tenant_id=tenant_a.id,
        operation="lifecycle_transition",
        resource_type="tenant",
        resource_id=str(tenant_a.id),
        operation_data={"to_state": "active"},
        operation_result="success",
    )
    await append_audit(
        db_session,
        tenant_id=tenant_a.id,
        operation="onboarding_advance",
        resource_type="tenant",
        resource_id=str(tenant_a.id),
        operation_data={"step": "company_info"},
        operation_result="success",
    )
    await append_audit(
        db_session,
        tenant_id=tenant_b.id,
        operation="lifecycle_transition",
        resource_type="tenant",
        resource_id=str(tenant_b.id),
        operation_data={"to_state": "active"},
        operation_result="success",
    )

    # A has 2 rows in chain; B has 1; chains are linked within tenant.
    a_rows = (
        (
            await db_session.execute(
                select(AuditLog)
                .where(AuditLog.tenant_id == tenant_a.id)
                .order_by(AuditLog.id.asc())
            )
        )
        .scalars()
        .all()
    )
    b_rows = (
        (
            await db_session.execute(
                select(AuditLog)
                .where(AuditLog.tenant_id == tenant_b.id)
                .order_by(AuditLog.id.asc())
            )
        )
        .scalars()
        .all()
    )
    assert len(a_rows) == 2
    assert len(b_rows) == 1

    # A's chain: row[1].previous_log_hash == row[0].current_log_hash.
    assert a_rows[1].previous_log_hash == a_rows[0].current_log_hash
    # B's chain stands alone — no cross-tenant linkage.
    assert b_rows[0].previous_log_hash != a_rows[1].current_log_hash

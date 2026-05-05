"""TenantHealthChecker tests (Sprint 56.1 Day 3 / US-3 part 2)."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models.api_keys import ApiKey
from infrastructure.db.models.identity import Role, User, UserRole
from platform_layer.tenant.health_check import TenantHealthChecker
from tests.conftest import seed_tenant


@pytest.mark.asyncio
async def test_health_check_db_probe_passes(db_session: AsyncSession) -> None:
    """SELECT 1 always succeeds → db_connection probe passes."""
    tenant = await seed_tenant(db_session, code="hc-db-1")
    checker = TenantHealthChecker(db_session)

    report = await checker.run(tenant.id)

    db_probe = next(p for p in report.probe_results if p.name == "db_connection")
    assert db_probe.passed is True


@pytest.mark.asyncio
async def test_health_check_missing_admin_user_fails(db_session: AsyncSession) -> None:
    """No admin user for tenant → first_admin_user probe fails."""
    tenant = await seed_tenant(db_session, code="hc-noadmin")
    checker = TenantHealthChecker(db_session)

    report = await checker.run(tenant.id)

    admin_probe = next(p for p in report.probe_results if p.name == "first_admin_user")
    assert admin_probe.passed is False
    assert "no admin user" in admin_probe.reason
    # Aggregate should also be False because admin probe failed.
    assert report.all_passed is False


@pytest.mark.asyncio
async def test_health_check_seeded_admin_and_apikey_pass(
    db_session: AsyncSession,
) -> None:
    """Seed admin role + active api_key → both probes pass."""
    tenant = await seed_tenant(db_session, code="hc-full")
    user = User(tenant_id=tenant.id, email="admin@hc-full.test", display_name="A")
    role = Role(
        tenant_id=tenant.id,
        code="admin",
        display_name="Admin",
        description="Admin role",
    )
    db_session.add_all([user, role])
    await db_session.flush()
    db_session.add(UserRole(user_id=user.id, role_id=role.id))
    db_session.add(
        ApiKey(
            tenant_id=tenant.id,
            name="primary",
            key_hash="x" * 60,
            key_prefix="ipa_test",
            permissions=["read"],
            status="active",
        )
    )
    await db_session.flush()

    checker = TenantHealthChecker(db_session)
    report = await checker.run(tenant.id)

    admin_probe = next(p for p in report.probe_results if p.name == "first_admin_user")
    apikey_probe = next(p for p in report.probe_results if p.name == "api_key_valid")
    assert admin_probe.passed is True
    assert apikey_probe.passed is True

"""TenantLifecycle state machine tests (Sprint 56.1 Day 1 / US-1)."""

from __future__ import annotations

import pytest

from infrastructure.db.models.identity import TenantState
from platform_layer.tenant.lifecycle import IllegalTransitionError, TenantLifecycle
from tests.conftest import seed_tenant


@pytest.mark.asyncio
async def test_lifecycle_requested_to_provisioning_valid(db_session) -> None:
    tenant = await seed_tenant(db_session, code="t-rp")
    lifecycle = TenantLifecycle(db_session)

    result = await lifecycle.transition(tenant.id, TenantState.PROVISIONING)

    assert result.state == TenantState.PROVISIONING


@pytest.mark.asyncio
async def test_lifecycle_provisioning_to_active_valid(db_session) -> None:
    tenant = await seed_tenant(db_session, code="t-pa")
    tenant.state = TenantState.PROVISIONING
    await db_session.flush()
    lifecycle = TenantLifecycle(db_session)

    result = await lifecycle.transition(tenant.id, TenantState.ACTIVE)

    assert result.state == TenantState.ACTIVE


@pytest.mark.asyncio
async def test_lifecycle_active_to_suspended_valid(db_session) -> None:
    tenant = await seed_tenant(db_session, code="t-as")
    tenant.state = TenantState.ACTIVE
    await db_session.flush()
    lifecycle = TenantLifecycle(db_session)

    result = await lifecycle.transition(tenant.id, TenantState.SUSPENDED)

    assert result.state == TenantState.SUSPENDED


@pytest.mark.asyncio
async def test_lifecycle_suspended_to_active_valid(db_session) -> None:
    tenant = await seed_tenant(db_session, code="t-sa")
    tenant.state = TenantState.SUSPENDED
    await db_session.flush()
    lifecycle = TenantLifecycle(db_session)

    result = await lifecycle.transition(tenant.id, TenantState.ACTIVE)

    assert result.state == TenantState.ACTIVE


@pytest.mark.asyncio
async def test_lifecycle_active_to_archived_valid(db_session) -> None:
    tenant = await seed_tenant(db_session, code="t-aa")
    tenant.state = TenantState.ACTIVE
    await db_session.flush()
    lifecycle = TenantLifecycle(db_session)

    result = await lifecycle.transition(tenant.id, TenantState.ARCHIVED)

    assert result.state == TenantState.ARCHIVED


@pytest.mark.asyncio
async def test_lifecycle_provisioning_to_provision_failed_valid(db_session) -> None:
    tenant = await seed_tenant(db_session, code="t-pf")
    tenant.state = TenantState.PROVISIONING
    await db_session.flush()
    lifecycle = TenantLifecycle(db_session)

    result = await lifecycle.transition(tenant.id, TenantState.PROVISION_FAILED)

    assert result.state == TenantState.PROVISION_FAILED


@pytest.mark.asyncio
async def test_lifecycle_archived_to_active_illegal(db_session) -> None:
    tenant = await seed_tenant(db_session, code="t-arc-a")
    tenant.state = TenantState.ARCHIVED
    await db_session.flush()
    lifecycle = TenantLifecycle(db_session)

    with pytest.raises(IllegalTransitionError) as exc_info:
        await lifecycle.transition(tenant.id, TenantState.ACTIVE)

    assert exc_info.value.current == TenantState.ARCHIVED
    assert exc_info.value.target == TenantState.ACTIVE


@pytest.mark.asyncio
async def test_lifecycle_active_to_requested_illegal(db_session) -> None:
    tenant = await seed_tenant(db_session, code="t-act-r")
    tenant.state = TenantState.ACTIVE
    await db_session.flush()
    lifecycle = TenantLifecycle(db_session)

    with pytest.raises(IllegalTransitionError):
        await lifecycle.transition(tenant.id, TenantState.REQUESTED)

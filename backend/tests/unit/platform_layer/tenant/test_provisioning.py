"""ProvisioningWorkflow tests (Sprint 56.1 Day 1 / US-1)."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from infrastructure.db.models.identity import Tenant, TenantState
from platform_layer.tenant.provisioning import (
    PROVISIONING_STEPS,
    ProvisioningError,
    ProvisioningWorkflow,
)
from tests.conftest import seed_tenant


@pytest.mark.asyncio
async def test_provisioning_full_happy_path(db_session) -> None:
    tenant = await seed_tenant(db_session, code="t-happy")
    workflow = ProvisioningWorkflow(db_session)

    result = await workflow.run(tenant.id)

    assert result.state == TenantState.PROVISIONING
    for step in PROVISIONING_STEPS:
        assert step in result.provisioning_progress


@pytest.mark.asyncio
async def test_provisioning_step_failure_transitions_to_provision_failed(
    db_session, monkeypatch
) -> None:
    tenant = await seed_tenant(db_session, code="t-fail")

    async def boom(self, t, step: str) -> None:
        if step == "generate_api_key":
            raise RuntimeError("simulated step failure")

    monkeypatch.setattr(ProvisioningWorkflow, "_run_step", boom)
    workflow = ProvisioningWorkflow(db_session)

    with pytest.raises(ProvisioningError) as exc_info:
        await workflow.run(tenant.id)

    assert exc_info.value.step == "generate_api_key"

    refreshed = (
        await db_session.execute(select(Tenant).where(Tenant.id == tenant.id))
    ).scalar_one()
    assert refreshed.state == TenantState.PROVISION_FAILED
    assert "seed_default_roles" in refreshed.provisioning_progress
    assert "generate_api_key" not in refreshed.provisioning_progress


@pytest.mark.asyncio
async def test_provisioning_retry_from_provision_failed(db_session) -> None:
    tenant = await seed_tenant(db_session, code="t-retry")
    tenant.state = TenantState.PROVISION_FAILED
    tenant.provisioning_progress = {"seed_default_roles": "2026-05-06T00:00:00+00:00"}
    await db_session.flush()
    workflow = ProvisioningWorkflow(db_session)

    result = await workflow.run(tenant.id)

    assert result.state == TenantState.PROVISIONING
    for step in PROVISIONING_STEPS:
        assert step in result.provisioning_progress


@pytest.mark.asyncio
async def test_provisioning_archived_tenant_cannot_reactivate_directly(db_session) -> None:
    tenant = await seed_tenant(db_session, code="t-arc")
    tenant.state = TenantState.ARCHIVED
    await db_session.flush()
    workflow = ProvisioningWorkflow(db_session)

    with pytest.raises(ValueError, match="cannot enter provisioning"):
        await workflow.run(tenant.id)

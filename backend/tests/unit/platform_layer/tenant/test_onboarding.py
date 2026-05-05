"""OnboardingTracker tests (Sprint 56.1 Day 2 / US-3 part 1)."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from platform_layer.tenant.onboarding import (
    VALID_STEPS,
    InvalidOnboardingStepError,
    OnboardingTracker,
)
from tests.conftest import seed_tenant


@pytest.mark.asyncio
async def test_onboarding_tracker_advance_step(db_session: AsyncSession) -> None:
    tenant = await seed_tenant(db_session, code="t-onb-1")
    tracker = OnboardingTracker(db_session)

    progress = await tracker.advance(
        tenant.id, "company_info", payload={"company_name": "ACME Corp"}
    )

    assert "company_info" in progress
    assert progress["company_info"]["payload"]["company_name"] == "ACME Corp"
    assert "completed_at" in progress["company_info"]


@pytest.mark.asyncio
async def test_onboarding_tracker_invalid_step_raises(
    db_session: AsyncSession,
) -> None:
    tenant = await seed_tenant(db_session, code="t-onb-2")
    tracker = OnboardingTracker(db_session)

    with pytest.raises(InvalidOnboardingStepError) as exc_info:
        await tracker.advance(tenant.id, "unknown_step")

    assert exc_info.value.step == "unknown_step"


@pytest.mark.asyncio
async def test_onboarding_tracker_is_complete_after_six_steps(
    db_session: AsyncSession,
) -> None:
    tenant = await seed_tenant(db_session, code="t-onb-3")
    tracker = OnboardingTracker(db_session)

    assert await tracker.is_complete(tenant.id) is False

    for step in VALID_STEPS:
        await tracker.advance(tenant.id, step, payload={})

    assert await tracker.is_complete(tenant.id) is True


@pytest.mark.asyncio
async def test_onboarding_tracker_get_progress_partition(
    db_session: AsyncSession,
) -> None:
    tenant = await seed_tenant(db_session, code="t-onb-4")
    tracker = OnboardingTracker(db_session)

    await tracker.advance(tenant.id, "company_info", payload={})
    await tracker.advance(tenant.id, "plan_selected", payload={"plan": "enterprise"})

    snapshot = await tracker.get_progress(tenant.id)

    assert snapshot["completed_steps"] == ["company_info", "plan_selected"]
    assert set(snapshot["pending_steps"]) == set(VALID_STEPS) - {
        "company_info",
        "plan_selected",
    }
    assert "company_info" in snapshot["step_records"]

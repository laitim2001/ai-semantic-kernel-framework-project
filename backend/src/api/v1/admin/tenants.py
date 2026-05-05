"""
File: backend/src/api/v1/admin/tenants.py
Purpose: System-admin tenant lifecycle endpoints — provisioning + onboarding API surface.
Category: API Layer / Admin (Sprint 56.1 SaaS Stage 1)
Scope: Sprint 56.1 Day 1 (US-1) + Day 3 (US-3 part 2 onboarding endpoints)
Owner: api/v1/admin owner

Description:
    Day 1 (US-1):
        POST /api/v1/admin/tenants — create new tenant + run ProvisioningWorkflow.

    Day 3 (US-3 part 2):
        GET  /api/v1/admin/tenants/{id}/onboarding-status — snapshot
        POST /api/v1/admin/tenants/{id}/onboarding/{step} — advance step
            with auto-transition to ACTIVE when all 6 steps complete + health
            check passes.

    D13 (Sprint 56.1 Day 1 discovery): plan §US-1 acceptance said "reuse 53.x
    admin role check" but no such dep exists in V2 codebase. Sprint 56.1 uses
    a stub `require_admin_token` (X-Admin-Token header against env var) to
    gate the endpoint; real RBAC role check deferred to Phase 56.x when
    identity infrastructure exposes admin role enumeration.

    D11 (carryover): no Cat 12 obs span — structured logging only (consistent
    with provisioning.py D11 / chat router L121 D4).

Key Components:
    - TenantCreateRequest / TenantCreateResponse Pydantic schemas
    - OnboardingStatusResponse / OnboardingAdvanceRequest schemas (Day 3)
    - require_admin_token: stub admin auth dependency
    - router: APIRouter prefix /admin/tenants
    - create_tenant / get_onboarding_status / advance_onboarding_step

Created: 2026-05-06 (Sprint 56.1 Day 1)
Last Modified: 2026-05-06

Modification History:
    - 2026-05-06: Sprint 56.1 Day 4 CI — replace EmailStr with regex (avoid email-validator dep)
    - 2026-05-06: Sprint 56.1 Day 3 — onboarding-status GET + onboarding/{step} POST (US-3 part 2)
    - 2026-05-06: Initial creation (Sprint 56.1 Day 1 / US-1)

Related:
    - platform_layer/tenant/provisioning.py — ProvisioningWorkflow
    - platform_layer/tenant/lifecycle.py — TenantLifecycle
    - platform_layer/tenant/onboarding.py — OnboardingTracker (Day 2)
    - platform_layer/tenant/health_check.py — TenantHealthChecker (Day 3)
    - infrastructure/db/models/identity.py — Tenant ORM
    - sprint-56-1-plan.md §US-1 + §US-3 + §Architecture
"""

from __future__ import annotations

import os
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models.identity import Tenant, TenantPlan, TenantState
from infrastructure.db.session import get_db_session
from platform_layer.tenant.health_check import TenantHealthChecker
from platform_layer.tenant.lifecycle import IllegalTransitionError, TenantLifecycle
from platform_layer.tenant.onboarding import (
    VALID_STEPS,
    InvalidOnboardingStepError,
    OnboardingTracker,
)
from platform_layer.tenant.provisioning import ProvisioningError, ProvisioningWorkflow

router = APIRouter(prefix="/admin/tenants", tags=["admin", "tenants"])

# Cheap email regex (RFC 5322-lite). We avoid pydantic's `EmailStr` so we
# don't need the optional `email-validator` extra in CI / lean prod images.
_EMAIL_PATTERN = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"


# Stub admin auth (D13). Phase 56.x will replace with RBAC role check.
_ADMIN_TOKEN_ENV = "PLATFORM_ADMIN_TOKEN"


async def require_admin_token(
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> None:
    expected = os.environ.get(_ADMIN_TOKEN_ENV)
    if not expected or x_admin_token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="admin authentication required",
        )


class TenantCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    display_name: str = Field(min_length=1, max_length=256)
    plan: TenantPlan = TenantPlan.ENTERPRISE
    admin_email: str = Field(pattern=_EMAIL_PATTERN, max_length=320)


class TenantCreateResponse(BaseModel):
    tenant_id: UUID
    code: str
    state: TenantState
    estimated_ready_in_seconds: int


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=TenantCreateResponse,
    dependencies=[Depends(require_admin_token)],
)
async def create_tenant(
    payload: TenantCreateRequest,
    db: AsyncSession = Depends(get_db_session),
) -> TenantCreateResponse:
    """Create new tenant + run ProvisioningWorkflow synchronously.

    Returns 201 with tenant_id once all 7 stub steps complete (state=PROVISIONING).
    Tenant transitions to ACTIVE only after onboarding 6-step + health check
    (Sprint 56.1 US-3 endpoints; Day 3 additions).
    """
    # admin_email is captured into metadata for the create_first_admin_user
    # step (deferred to Phase 56.x per D12).
    tenant = Tenant(
        code=payload.code,
        display_name=payload.display_name,
        plan=payload.plan,
        meta_data={"admin_email": str(payload.admin_email)},
    )
    db.add(tenant)
    await db.flush()

    workflow = ProvisioningWorkflow(db)
    try:
        await workflow.run(tenant.id)
    except ProvisioningError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"provisioning failed at step {exc.step}: {exc.original}",
        ) from exc

    return TenantCreateResponse(
        tenant_id=tenant.id,
        code=tenant.code,
        state=tenant.state,
        estimated_ready_in_seconds=60,
    )


# ---------------------------------------------------------------------
# Day 3 (US-3 part 2): Onboarding endpoints
# ---------------------------------------------------------------------


class OnboardingStatusResponse(BaseModel):
    tenant_id: UUID
    state: TenantState
    completed_steps: list[str]
    pending_steps: list[str]
    step_records: dict[str, Any]
    is_complete: bool


class OnboardingAdvanceRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)


class OnboardingAdvanceResponse(BaseModel):
    tenant_id: UUID
    step: str
    state: TenantState
    is_complete: bool
    health_check: dict[str, Any] | None = None
    transitioned_to_active: bool = False


async def _load_tenant_or_404(db: AsyncSession, tenant_id: UUID) -> Tenant:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"tenant {tenant_id} not found"
        )
    return tenant


@router.get(
    "/{tenant_id}/onboarding-status",
    response_model=OnboardingStatusResponse,
    dependencies=[Depends(require_admin_token)],
)
async def get_onboarding_status(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> OnboardingStatusResponse:
    """Snapshot of completed + pending steps + tenant state."""
    tenant = await _load_tenant_or_404(db, tenant_id)
    tracker = OnboardingTracker(db)
    snapshot = await tracker.get_progress(tenant_id)
    is_complete = await tracker.is_complete(tenant_id)
    return OnboardingStatusResponse(
        tenant_id=tenant_id,
        state=tenant.state,
        completed_steps=snapshot["completed_steps"],
        pending_steps=snapshot["pending_steps"],
        step_records=snapshot["step_records"],
        is_complete=is_complete,
    )


@router.post(
    "/{tenant_id}/onboarding/{step}",
    response_model=OnboardingAdvanceResponse,
    dependencies=[Depends(require_admin_token)],
)
async def advance_onboarding_step(
    tenant_id: UUID,
    step: str,
    body: OnboardingAdvanceRequest,
    db: AsyncSession = Depends(get_db_session),
) -> OnboardingAdvanceResponse:
    """Advance a single onboarding step.

    When the final step (`health_check`) completes AND the
    `TenantHealthChecker` 6-point probe passes, auto-transitions the tenant
    from PROVISIONING → ACTIVE via `TenantLifecycle.transition`. Other steps
    just record progress + return current state.

    Step name in path is validated against `VALID_STEPS`; unknown steps
    return 400 (not 422 — keeps the FastAPI validation surface for body).
    """
    if step not in VALID_STEPS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unknown onboarding step '{step}'; valid: {list(VALID_STEPS)}",
        )

    tenant = await _load_tenant_or_404(db, tenant_id)
    tracker = OnboardingTracker(db)

    try:
        await tracker.advance(tenant_id, step, payload=body.payload)
    except InvalidOnboardingStepError as exc:
        # Defensive — should already have been caught by the path-level
        # check above; re-map for safety.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    is_complete = await tracker.is_complete(tenant_id)

    health_report_dict: dict[str, Any] | None = None
    transitioned = False

    if is_complete:
        # Run the 6-point health probe; auto-transition only when all green.
        # D24: chat_call / redis_client injection deferred to production
        # wiring (Phase 56.x); test paths inject mocks directly.
        checker = TenantHealthChecker(db)
        report = await checker.run(tenant_id)
        health_report_dict = report.as_dict()
        if report.all_passed and tenant.state == TenantState.PROVISIONING:
            lifecycle = TenantLifecycle(db)
            try:
                await lifecycle.transition(tenant_id, TenantState.ACTIVE)
                transitioned = True
                # Refresh state for response.
                await db.refresh(tenant)
            except IllegalTransitionError:
                # Already moved on — leave state as-is.
                transitioned = False

    return OnboardingAdvanceResponse(
        tenant_id=tenant_id,
        step=step,
        state=tenant.state,
        is_complete=is_complete,
        health_check=health_report_dict,
        transitioned_to_active=transitioned,
    )

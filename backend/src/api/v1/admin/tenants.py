"""
File: backend/src/api/v1/admin/tenants.py
Purpose: System-admin tenant lifecycle endpoints — provisioning + onboarding API surface.
Category: API Layer / Admin (Sprint 56.1 SaaS Stage 1)
Scope: Sprint 56.1 Day 1 (US-1) + Day 3 (US-3 onboarding endpoints — added later)
Owner: api/v1/admin owner

Description:
    POST /api/v1/admin/tenants — create new tenant + run ProvisioningWorkflow.

    D13 (Sprint 56.1 Day 1 discovery): plan §US-1 acceptance said "reuse 53.x
    admin role check" but no such dep exists in V2 codebase. Sprint 56.1 uses
    a stub `require_admin_token` (X-Admin-Token header against env var) to
    gate the endpoint; real RBAC role check deferred to Phase 56.x when
    identity infrastructure exposes admin role enumeration.

    D11 (carryover): no Cat 12 obs span — structured logging only (consistent
    with provisioning.py D11 / chat router L121 D4).

Key Components:
    - TenantCreateRequest / TenantCreateResponse Pydantic schemas
    - require_admin_token: stub admin auth dependency
    - router: APIRouter prefix /admin/tenants
    - create_tenant: POST handler

Created: 2026-05-06 (Sprint 56.1 Day 1)
Last Modified: 2026-05-06

Modification History:
    - 2026-05-06: Initial creation (Sprint 56.1 Day 1 / US-1)

Related:
    - platform_layer/tenant/provisioning.py — ProvisioningWorkflow
    - platform_layer/tenant/lifecycle.py — TenantLifecycle
    - infrastructure/db/models/identity.py — Tenant ORM
    - sprint-56-1-plan.md §US-1 + §Architecture
"""

from __future__ import annotations

import os
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models.identity import Tenant, TenantPlan, TenantState
from infrastructure.db.session import get_db_session
from platform_layer.tenant.provisioning import ProvisioningError, ProvisioningWorkflow

router = APIRouter(prefix="/admin/tenants", tags=["admin", "tenants"])


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
    admin_email: EmailStr


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

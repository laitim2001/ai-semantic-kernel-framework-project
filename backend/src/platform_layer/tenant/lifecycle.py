"""
File: backend/src/platform_layer/tenant/lifecycle.py
Purpose: TenantLifecycle state machine for SaaS Stage 1 tenant lifecycle (Phase 56.1).
Category: Platform Layer / Tenant (Sprint 56.1 SaaS Stage 1)
Scope: Sprint 56.1 Day 1 (US-1)
Owner: platform_layer/tenant owner

Description:
    Validates tenant state transitions per 15-saas-readiness §State Machine.

    Allowed transitions (8 total):
        requested        -> provisioning       (POST /admin/tenants triggers)
        provisioning     -> provision_failed   (sub-step fails)
        provisioning     -> active             (onboarding 6-step + health check pass)
        provision_failed -> provisioning       (retry from provision_failed)
        active           -> suspended          (admin suspend endpoint)
        suspended        -> active             (admin reactivate endpoint)
        active           -> archived           (admin archive endpoint)
        suspended        -> archived           (admin archive while suspended)

    D10 (Sprint 56.1 Day 1 discovery): plan §US-1 said "6 valid transitions";
    minimal set to support ProvisioningWorkflow retry path (per §Acceptance
    "Idempotent retry from PROVISION_FAILED") is 8. Plan figure was approximate.

Key Components:
    - TenantLifecycle: async transition(tenant_id, new_state) -> Tenant
    - IllegalTransitionError: raised when transition not in VALID_TRANSITIONS
    - VALID_TRANSITIONS: frozenset of (from, to) state pairs

Created: 2026-05-06 (Sprint 56.1 Day 1)
Last Modified: 2026-05-06

Modification History:
    - 2026-05-06: Initial creation (Sprint 56.1 Day 1 / part of US-1)

Related:
    - infrastructure/db/models/identity.py:Tenant + TenantState
    - 15-saas-readiness.md §Tenant State Machine (L73-77)
    - sprint-56-1-plan.md §US-1 + §Architecture
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models.identity import Tenant, TenantState


class IllegalTransitionError(Exception):
    """Raised when a state transition is not in VALID_TRANSITIONS."""

    def __init__(self, current: TenantState, target: TenantState):
        self.current = current
        self.target = target
        super().__init__(f"Illegal tenant state transition: {current.value} -> {target.value}")


# (from_state, to_state) pairs allowed per 15-saas-readiness §State Machine
# + ProvisioningWorkflow retry path (D10 minimal set).
VALID_TRANSITIONS: frozenset[tuple[TenantState, TenantState]] = frozenset(
    {
        (TenantState.REQUESTED, TenantState.PROVISIONING),
        (TenantState.PROVISIONING, TenantState.PROVISION_FAILED),
        (TenantState.PROVISIONING, TenantState.ACTIVE),
        (TenantState.PROVISION_FAILED, TenantState.PROVISIONING),
        (TenantState.ACTIVE, TenantState.SUSPENDED),
        (TenantState.SUSPENDED, TenantState.ACTIVE),
        (TenantState.ACTIVE, TenantState.ARCHIVED),
        (TenantState.SUSPENDED, TenantState.ARCHIVED),
    }
)


class TenantLifecycle:
    """Per-request TenantLifecycle service for state transitions."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def transition(self, tenant_id: UUID, new_state: TenantState) -> Tenant:
        """Transition tenant to new_state if (current, new_state) in VALID_TRANSITIONS.

        Raises:
            ValueError: tenant_id not found
            IllegalTransitionError: transition not allowed from current state
        """
        result = await self._db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if tenant is None:
            raise ValueError(f"Tenant {tenant_id} not found")

        if (tenant.state, new_state) not in VALID_TRANSITIONS:
            raise IllegalTransitionError(tenant.state, new_state)

        tenant.state = new_state
        await self._db.flush()
        return tenant

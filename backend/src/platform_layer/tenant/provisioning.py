"""
File: backend/src/platform_layer/tenant/provisioning.py
Purpose: ProvisioningWorkflow — 8-step async tenant provisioning per 15-saas-readiness §Step 2.
Category: Platform Layer / Tenant (Sprint 56.1 SaaS Stage 1)
Scope: Sprint 56.1 Day 1 (US-1)
Owner: platform_layer/tenant owner

Description:
    Idempotent 8-step provisioning workflow. Tenant moves REQUESTED → PROVISIONING
    on workflow.run() entry; remains in PROVISIONING after all 8 steps complete
    (waits for OnboardingTracker to transition to ACTIVE).

    Per-step semantics:
    - Each step recorded in `tenant.provisioning_progress` JSONB as {step_name: timestamp}
    - Idempotent retry: re-running run() from PROVISION_FAILED skips already-completed steps
    - Failure: transitions to PROVISION_FAILED + logs structured audit + raises

    Steps (per 15-saas-readiness L51-58):
        1. seed_default_roles               (real DB write Phase 56.x; stub now)
        2. seed_default_policies            (real DB write Phase 56.x; stub now)
        3. qdrant_namespace_stub            (Phase 56.x — Vector DB integration)
        4. seed_system_memory_stub          (Phase 56.x — Memory Layer 1 seeding)
        5. create_first_admin_user          (real DB write Phase 56.x; stub now)
        6. generate_api_key                 (real DB write Phase 56.x; stub now)
        7. emit_welcome_notification_stub   (Phase 56.3 — Teams integration)

    D11 (Sprint 56.1 Day 1 discovery): plan §US-1 acceptance specified Cat 12
    obs span per step. SpanCategory enum (17.md §1.1) has no `PLATFORM_TENANT`
    or similar; adding crosses single-source ownership. Sprint 56.1 uses
    structured logging only; Cat 12 span integration deferred (consistent
    with D4 / AD-Cat12-BusinessObs Phase 56.x carryover).

    D12 (Sprint 56.1 Day 1 discovery): plan §US-1 acceptance asserted real DB
    writes for steps 2.2 / 2.3 / 2.6 / 2.7 (seed_roles / seed_policies /
    create_user / api_key). Implementing real ORM writes for 4 different model
    families in Day 1 exceeds scope; all 8 steps are stub-style markers in
    `provisioning_progress` JSONB for Sprint 56.1. Real per-step DB writes
    deferred to Phase 56.x integration sprints.

Key Components:
    - ProvisioningWorkflow: async run(tenant_id) -> Tenant
    - PROVISIONING_STEPS: ordered tuple of 7 step names (step 0 = create_tenant_record
      done by API endpoint before workflow.run() is invoked)
    - StepResult / ProvisioningError exceptions

Created: 2026-05-06 (Sprint 56.1 Day 1)
Last Modified: 2026-05-06

Modification History:
    - 2026-05-06: Initial creation (Sprint 56.1 Day 1 / part of US-1)

Related:
    - platform_layer/tenant/lifecycle.py — TenantLifecycle.transition()
    - infrastructure/db/models/identity.py — Tenant ORM
    - 15-saas-readiness.md §Tenant Provisioning (L40-69)
    - sprint-56-1-plan.md §US-1 + §Architecture
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models.identity import Tenant, TenantState
from platform_layer.tenant.lifecycle import TenantLifecycle

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("audit.tenant_provisioning")


# Ordered step names; step 0 (create_tenant_record) is API endpoint responsibility.
PROVISIONING_STEPS: tuple[str, ...] = (
    "seed_default_roles",
    "seed_default_policies",
    "qdrant_namespace_stub",
    "seed_system_memory_stub",
    "create_first_admin_user",
    "generate_api_key",
    "emit_welcome_notification_stub",
)


class ProvisioningError(RuntimeError):
    """Raised when a provisioning sub-step fails irrecoverably."""

    def __init__(self, step: str, original: Exception):
        self.step = step
        self.original = original
        super().__init__(f"Provisioning step '{step}' failed: {original}")


class ProvisioningWorkflow:
    """8-step tenant provisioning workflow (D12: all stubs in Sprint 56.1)."""

    def __init__(self, db: AsyncSession):
        self._db = db
        self._lifecycle = TenantLifecycle(db)

    async def run(self, tenant_id: UUID) -> Tenant:
        """Execute provisioning workflow; idempotent across retries from PROVISION_FAILED.

        Raises:
            ValueError: tenant_id not found
            ProvisioningError: a sub-step raised; tenant transitioned to PROVISION_FAILED
        """
        tenant = await self._load(tenant_id)

        if tenant.state == TenantState.REQUESTED:
            tenant = await self._lifecycle.transition(tenant_id, TenantState.PROVISIONING)
        elif tenant.state == TenantState.PROVISION_FAILED:
            tenant = await self._lifecycle.transition(tenant_id, TenantState.PROVISIONING)
        elif tenant.state != TenantState.PROVISIONING:
            raise ValueError(
                f"Tenant {tenant_id} state {tenant.state.value} cannot enter provisioning"
            )

        for step in PROVISIONING_STEPS:
            if self._step_done(tenant, step):
                continue
            try:
                await self._run_step(tenant, step)
                self._mark_done(tenant, step)
                await self._db.flush()
            except Exception as exc:  # noqa: BLE001
                audit_logger.error(
                    "provisioning_step_failed",
                    extra={
                        "tenant_id": str(tenant_id),
                        "step": step,
                        "error": str(exc),
                    },
                )
                await self._lifecycle.transition(tenant_id, TenantState.PROVISION_FAILED)
                raise ProvisioningError(step, exc) from exc

        audit_logger.info(
            "provisioning_completed",
            extra={"tenant_id": str(tenant_id)},
        )
        return tenant

    async def _load(self, tenant_id: UUID) -> Tenant:
        result = await self._db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if tenant is None:
            raise ValueError(f"Tenant {tenant_id} not found")
        return tenant

    @staticmethod
    def _step_done(tenant: Tenant, step: str) -> bool:
        return step in tenant.provisioning_progress

    @staticmethod
    def _mark_done(tenant: Tenant, step: str) -> None:
        # SQLAlchemy JSONB requires reassignment for change detection.
        progress = dict(tenant.provisioning_progress)
        progress[step] = datetime.now(timezone.utc).isoformat()
        tenant.provisioning_progress = progress

    async def _run_step(self, tenant: Tenant, step: str) -> None:
        """Stub all 8 steps for Sprint 56.1 (D12); Phase 56.x implements real DB ops."""
        logger.info(
            "provisioning_step_stub_executed",
            extra={"tenant_id": str(tenant.id), "step": step},
        )

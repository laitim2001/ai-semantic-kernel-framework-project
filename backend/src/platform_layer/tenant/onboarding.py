"""
File: backend/src/platform_layer/tenant/onboarding.py
Purpose: OnboardingTracker — 6-step tenant onboarding state on tenants.onboarding_progress.
Category: Phase 56 SaaS Stage 1 (platform_layer.tenant)
Scope: Sprint 56.1 / Day 2 / US-3 part 1 (backend logic)

Description:
    Tracks per-tenant onboarding progress in the `tenants.onboarding_progress`
    JSONB column added by Alembic 0014 (Day 1). Steps are advanced via
    `advance(step, payload)` which writes a per-step record and timestamp.
    `is_complete()` returns True once all 6 steps are present.

    Day 2 ships ONLY the backend tracker logic. US-3 part 2 (Day 3) will
    add the admin API endpoints + 6-point health check + auto-transition
    to ACTIVE on completion.

    Steps (per 15-saas-readiness §Onboarding Wizard L312-335):
      1. company_info       — basic tenant metadata
      2. plan_selected      — confirm Enterprise tier
      3. memory_uploaded    — system_memory seed (Day 1 stub'd)
      4. sso_configured     — SAML/OIDC settings
      5. users_invited      — at least 1 admin user invited
      6. health_check       — Day 3 6-point health probe gates ACTIVE

Key Components:
    - OnboardingTracker: advance / is_complete / get_progress
    - InvalidOnboardingStepError: raised on unknown step name
    - VALID_STEPS: ordered tuple — single source for step names

Modification History (newest-first):
    - 2026-05-06: Initial creation (Sprint 56.1 Day 2 / US-3 part 1)

Related:
    - sprint-56-1-plan.md §US-3 Onboarding Wizard
    - 15-saas-readiness.md §Onboarding Wizard L312-335
    - identity.py — Tenant.onboarding_progress JSONB column
    - lifecycle.py — Day 3 will trigger PROVISIONING → ACTIVE on complete
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models.identity import Tenant

VALID_STEPS: tuple[str, ...] = (
    "company_info",
    "plan_selected",
    "memory_uploaded",
    "sso_configured",
    "users_invited",
    "health_check",
)


class InvalidOnboardingStepError(ValueError):
    """Raised when `step` is not in VALID_STEPS."""

    def __init__(self, step: str) -> None:
        self.step = step
        super().__init__(f"unknown onboarding step '{step}'; valid: {list(VALID_STEPS)}")


class OnboardingTracker:
    """Stateless service over `tenants.onboarding_progress` JSONB."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _load_tenant(self, tenant_id: UUID) -> Tenant:
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        result = await self._session.execute(stmt)
        tenant = result.scalar_one_or_none()
        if tenant is None:
            raise LookupError(f"tenant {tenant_id} not found")
        return tenant

    async def advance(
        self,
        tenant_id: UUID,
        step: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Mark `step` complete with `payload` and timestamp.

        Idempotent — re-advancing a completed step overwrites the record
        (allows correction without re-provisioning).
        """
        if step not in VALID_STEPS:
            raise InvalidOnboardingStepError(step)
        tenant = await self._load_tenant(tenant_id)
        progress: dict[str, Any] = dict(tenant.onboarding_progress or {})
        progress[step] = {
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload or {},
        }
        tenant.onboarding_progress = progress
        await self._session.flush()
        return progress

    async def is_complete(self, tenant_id: UUID) -> bool:
        """All 6 steps present in onboarding_progress?"""
        tenant = await self._load_tenant(tenant_id)
        progress = tenant.onboarding_progress or {}
        return all(step in progress for step in VALID_STEPS)

    async def get_progress(self, tenant_id: UUID) -> dict[str, Any]:
        """Snapshot of completed + pending steps for status endpoint."""
        tenant = await self._load_tenant(tenant_id)
        progress = dict(tenant.onboarding_progress or {})
        completed = [s for s in VALID_STEPS if s in progress]
        pending = [s for s in VALID_STEPS if s not in progress]
        return {
            "tenant_id": str(tenant_id),
            "completed_steps": completed,
            "pending_steps": pending,
            "step_records": progress,
        }

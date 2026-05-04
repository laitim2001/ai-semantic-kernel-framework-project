"""
File: backend/src/business_domain/rootcause/service.py
Purpose: RootCauseService — diagnose against incident table (08b §Domain 3).
Category: Business Domain / rootcause — service layer
Scope: Sprint 55.1 US-3 / Day 3.1c

Description:
    diagnose() reads the Incident row (Sprint 55.1 Day 1 schema; tenant-filtered)
    and returns a canned analysis dict keyed off incident.status and severity.
    The actual root-cause inference engine is out of scope for Phase 55.1; this
    service demonstrates real DB lookup + tenant isolation + deterministic
    output shape so Cat 2 ToolHandler can swap mock → service cleanly.

Created: 2026-05-04 (Sprint 55.1 Day 3)
Last Modified: 2026-05-04

Modification History:
    - 2026-05-04: Initial creation (Sprint 55.1 Day 3.1c)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select

from business_domain._base import BusinessServiceBase
from business_domain._obs import business_service_span
from infrastructure.db.models.business import Incident

# Canned analyses keyed by incident.status (deterministic stub).
_ANALYSIS_BY_STATUS: dict[str, dict[str, Any]] = {
    "open": {
        "stage": "triage_required",
        "candidate_root_causes": ["unverified — pending diagnostics"],
        "confidence": 0.3,
    },
    "investigating": {
        "stage": "investigation_in_progress",
        "candidate_root_causes": ["misconfiguration", "infrastructure_failure"],
        "confidence": 0.6,
    },
    "resolved": {
        "stage": "resolved_pending_postmortem",
        "candidate_root_causes": ["application_bug"],
        "confidence": 0.8,
    },
    "closed": {
        "stage": "closed",
        "candidate_root_causes": ["see resolution"],
        "confidence": 1.0,
    },
}


class RootCauseService(BusinessServiceBase):
    """Diagnose service backed by real Incident table reads."""

    SERVICE_NAME = "rootcause"

    async def diagnose(self, *, incident_id: UUID) -> dict[str, Any]:
        """Return canned root-cause analysis for an incident in tenant scope.

        Raises:
            ValueError: incident not in tenant scope.
        """
        async with business_service_span(
            self.tracer, service_name=self.SERVICE_NAME, method="diagnose"
        ):
            stmt = select(Incident).where(
                Incident.id == incident_id,
                Incident.tenant_id == self.tenant_id,
            )
            inc = (await self.db.execute(stmt)).scalars().first()
            if inc is None:
                raise ValueError(f"Incident {incident_id} not found in tenant scope")

            base = _ANALYSIS_BY_STATUS.get(inc.status, _ANALYSIS_BY_STATUS["open"])
            return {
                "incident_id": str(inc.id),
                "tenant_id": str(self.tenant_id),
                "status": inc.status,
                "severity": inc.severity,
                "title": inc.title,
                **base,
            }


__all__ = ["RootCauseService"]

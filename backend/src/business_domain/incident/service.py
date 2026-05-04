"""
File: backend/src/business_domain/incident/service.py
Purpose: IncidentService — production CRUD for incident lifecycle (08b §Domain 5).
Category: Business Domain / incident — service layer
Scope: Sprint 55.1 US-2 / Day 2.3
Owner: business_domain/incident owner

Description:
    Production service replacing the HTTP-based mock_executor when
    `BUSINESS_DOMAIN_MODE=service`. Backed by the `incidents` table created
    in Sprint 55.1 Day 1 (migration 0012, ORM Incident).

    Multi-tenant rule (per .claude/rules/multi-tenant-data.md 鐵律 1+2):
        - Every query filters `WHERE tenant_id = self.tenant_id`
        - Cross-tenant `get()` returns None (404 hides existence)
        - `update_status()` and `close()` raise ValueError when row not in
          tenant scope
        - Destructive operations (create / update_status / close) emit a
          hash-chained audit_log entry via BusinessServiceBase.audit_event()

    Validation:
        - severity ∈ {low, medium, high, critical} — enforced both at
          Python layer (IncidentSeverity enum coercion) and DB layer (CHECK)
        - status ∈ {open, investigating, resolved, closed} — same dual layer
        - close() requires non-empty resolution (≥ 1 char)

    Observability:
        - Each method wrapped with business_service_span(...) for span
          emission under SpanCategory.TOOLS

Created: 2026-05-04 (Sprint 55.1 Day 2)
Last Modified: 2026-05-04

Modification History:
    - 2026-05-04: Initial creation (Sprint 55.1 Day 2.3)

Related:
    - 08b-business-tools-spec.md §Domain 5 Incident
    - infrastructure/db/models/business/incident.py — Incident ORM
    - business_domain/_base.py — BusinessServiceBase
    - business_domain/_obs.py — business_service_span
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from business_domain._base import BusinessServiceBase
from business_domain._obs import business_service_span
from infrastructure.db.models.business import (
    Incident,
    IncidentSeverity,
    IncidentStatus,
)


class IncidentService(BusinessServiceBase):
    """Production CRUD for the `incidents` table (08b §Domain 5)."""

    SERVICE_NAME = "incident"

    # ===== create =========================================================
    async def create(
        self,
        *,
        title: str,
        severity: str = "high",
        alert_ids: list[str] | None = None,
        user_id: UUID | None = None,
    ) -> Incident:
        """Create a new incident (status defaults to 'open' via DB server_default)."""
        async with business_service_span(
            self.tracer, service_name=self.SERVICE_NAME, method="create"
        ):
            # Python-layer validation; DB CHECK is the second wall.
            self._validate_severity(severity)

            inc = Incident(
                tenant_id=self.tenant_id,
                user_id=user_id,
                title=title,
                severity=severity,
                alert_ids=list(alert_ids or []),
            )
            self.db.add(inc)
            await self.db.flush()
            await self.db.refresh(inc)

            await self.audit_event(
                operation="incident_create",
                resource_type="incident",
                resource_id=str(inc.id),
                actor_user_id=user_id,
                payload={"title": title, "severity": severity},
            )
            return inc

    # ===== list ===========================================================
    async def list(
        self,
        *,
        severity: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> list[Incident]:
        """List incidents in tenant scope; optional severity/status filters."""
        async with business_service_span(
            self.tracer, service_name=self.SERVICE_NAME, method="list"
        ):
            if severity is not None:
                self._validate_severity(severity)
            if status is not None:
                self._validate_status(status)

            stmt = select(Incident).where(Incident.tenant_id == self.tenant_id)
            if severity is not None:
                stmt = stmt.where(Incident.severity == severity)
            if status is not None:
                stmt = stmt.where(Incident.status == status)
            stmt = stmt.order_by(Incident.created_at.desc()).limit(limit)

            rows = (await self.db.execute(stmt)).scalars().all()
            return list(rows)

    # ===== get ============================================================
    async def get(self, *, incident_id: UUID) -> Incident | None:
        """Fetch single incident by id; cross-tenant returns None (hide existence)."""
        async with business_service_span(self.tracer, service_name=self.SERVICE_NAME, method="get"):
            stmt = select(Incident).where(
                Incident.id == incident_id,
                Incident.tenant_id == self.tenant_id,
            )
            return (await self.db.execute(stmt)).scalars().first()

    # ===== update_status ==================================================
    async def update_status(
        self,
        *,
        incident_id: UUID,
        status: str,
        actor_user_id: UUID | None = None,
    ) -> Incident:
        """Update incident.status; raises ValueError if not found in tenant scope."""
        async with business_service_span(
            self.tracer, service_name=self.SERVICE_NAME, method="update_status"
        ):
            self._validate_status(status)

            inc = await self.get(incident_id=incident_id)
            if inc is None:
                raise ValueError(f"Incident {incident_id} not found in tenant scope")
            inc.status = status
            await self.db.flush()
            await self.db.refresh(inc)

            await self.audit_event(
                operation="incident_update_status",
                resource_type="incident",
                resource_id=str(inc.id),
                actor_user_id=actor_user_id,
                payload={"new_status": status},
            )
            return inc

    # ===== close ==========================================================
    async def close(
        self,
        *,
        incident_id: UUID,
        resolution: str,
        actor_user_id: UUID | None = None,
    ) -> Incident:
        """Close an incident: set status='closed' + closed_at=NOW + resolution NN.

        Raises:
            ValueError: if incident not in tenant scope OR resolution empty.
        """
        async with business_service_span(
            self.tracer, service_name=self.SERVICE_NAME, method="close"
        ):
            if not resolution or not resolution.strip():
                raise ValueError("resolution must be non-empty when closing an incident")

            inc = await self.get(incident_id=incident_id)
            if inc is None:
                raise ValueError(f"Incident {incident_id} not found in tenant scope")
            inc.status = IncidentStatus.CLOSED.value
            inc.resolution = resolution
            inc.closed_at = datetime.now(timezone.utc)
            await self.db.flush()
            await self.db.refresh(inc)

            await self.audit_event(
                operation="incident_close",
                resource_type="incident",
                resource_id=str(inc.id),
                actor_user_id=actor_user_id,
                payload={"resolution": resolution},
            )
            return inc

    # ===== validation helpers ============================================
    @staticmethod
    def _validate_severity(severity: str) -> None:
        try:
            IncidentSeverity(severity)
        except ValueError as exc:
            raise ValueError(
                f"Invalid severity {severity!r}; must be one of "
                f"{[s.value for s in IncidentSeverity]}"
            ) from exc

    @staticmethod
    def _validate_status(status: str) -> None:
        try:
            IncidentStatus(status)
        except ValueError as exc:
            raise ValueError(
                f"Invalid status {status!r}; must be one of " f"{[s.value for s in IncidentStatus]}"
            ) from exc


__all__ = ["IncidentService"]

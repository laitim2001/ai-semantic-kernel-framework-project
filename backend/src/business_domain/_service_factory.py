"""
File: backend/src/business_domain/_service_factory.py
Purpose: BusinessServiceFactory — per-domain service builders + reset hook.
Category: Business Domain — shared infrastructure
Scope: Sprint 55.1 US-4 / Day 3.6

Description:
    Sprint 55.1 introduces a separate factory for business-domain services
    so we don't mix concerns into the existing
    `platform_layer.governance.ServiceFactory` (which scope is governance:
    HITL / RiskPolicy / Audit). Per .claude/rules/category-boundaries.md
    AP-3 (Cross-Directory Scattering), business_domain owns its own factory.

    The 5 service classes (IncidentService / PatrolService / CorrelationService
    / RootCauseService / AuditService) all subclass BusinessServiceBase and
    accept (db, tenant_id, tracer) — the factory provides typed builders.

    No process-singleton instances are cached: each request gets a fresh
    service bound to its (db_session, tenant_id) pair. This is correct
    semantics — services are stateless wrappers over (db, tenant_id) and
    must NOT be cached because db sessions are per-request scoped.

    The module-level `_factory` ref is provided so that tests can extend
    `reset_service_factory()` semantics if needed; today it's an idempotent
    no-op since no shared state is held.

Created: 2026-05-04 (Sprint 55.1 Day 3.6)
Last Modified: 2026-05-04

Modification History:
    - 2026-05-04: Initial creation (Sprint 55.1 Day 3.6)

Related:
    - .claude/rules/testing.md §Module-level Singleton Reset Pattern (53.6)
    - business_domain/{incident,patrol,correlation,rootcause,audit_domain}/service.py
    - business_domain/_base.py — BusinessServiceBase
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from agent_harness.observability import Tracer
from business_domain.audit_domain.service import AuditService
from business_domain.correlation.service import CorrelationService
from business_domain.incident.service import IncidentService
from business_domain.patrol.service import PatrolService
from business_domain.rootcause.service import RootCauseService


class BusinessServiceFactory:
    """Per-request builder for the 5 business-domain services.

    Args:
        db: AsyncSession bound to the current request.
        tenant_id: tenant scope for all built services.
        tracer: optional Tracer (None → obs no-op).
    """

    def __init__(
        self,
        *,
        db: AsyncSession,
        tenant_id: UUID,
        tracer: Tracer | None = None,
    ) -> None:
        self._db = db
        self._tenant_id = tenant_id
        self._tracer = tracer

    def get_incident_service(self) -> IncidentService:
        return IncidentService(db=self._db, tenant_id=self._tenant_id, tracer=self._tracer)

    def get_patrol_service(self) -> PatrolService:
        return PatrolService(db=self._db, tenant_id=self._tenant_id, tracer=self._tracer)

    def get_correlation_service(self) -> CorrelationService:
        return CorrelationService(db=self._db, tenant_id=self._tenant_id, tracer=self._tracer)

    def get_rootcause_service(self) -> RootCauseService:
        return RootCauseService(db=self._db, tenant_id=self._tenant_id, tracer=self._tracer)

    def get_audit_service(self) -> AuditService:
        return AuditService(db=self._db, tenant_id=self._tenant_id, tracer=self._tracer)


__all__ = ["BusinessServiceFactory"]

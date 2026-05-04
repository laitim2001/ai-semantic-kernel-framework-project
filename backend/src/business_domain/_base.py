"""
File: backend/src/business_domain/_base.py
Purpose: BusinessServiceBase — shared base for all 5 domain service classes.
Category: Business Domain — shared infrastructure
Scope: Sprint 55.1 US-2 / Day 2.1

Description:
    Common foundation for IncidentService / PatrolService / CorrelationService
    / RootCauseService / AuditService. Holds the 3 collaborators each service
    needs (db / tenant_id / tracer) and provides a single audit-log entrypoint
    so destructive ops emit a hash-chained AuditLog row consistently.

    Sprint 55.1 keeps this minimal — concrete service methods own their own
    SQL + business validation. The base class contract:
        - __init__(*, db, tenant_id, tracer)
        - audit_event(*, operation, resource_type, resource_id, payload)
            → wraps audit_helper.append_audit() with the service's tenant_id
              already bound.

Created: 2026-05-04 (Sprint 55.1 Day 2)
Last Modified: 2026-05-04

Modification History:
    - 2026-05-04: Initial creation (Sprint 55.1 Day 2.1)

Related:
    - .claude/rules/multi-tenant-data.md 鐵律 1 + 鐵律 3 (audit log for destructive)
    - infrastructure/db/audit_helper.py (append_audit + hash chain)
    - business_domain/_obs.py (business_service_span ctx mgr)
    - 14-security-deep-dive.md §Audit hash chain
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from agent_harness.observability import Tracer
from infrastructure.db.audit_helper import append_audit


class BusinessServiceBase:
    """Shared foundation for all business-domain services.

    Subclasses get:
        - self.db          AsyncSession
        - self.tenant_id   UUID (multi-tenant scope; required for every query)
        - self.tracer      Tracer | None (None → obs no-op)
        - self.audit_event(...) helper for destructive ops
    """

    def __init__(
        self,
        *,
        db: AsyncSession,
        tenant_id: UUID,
        tracer: Tracer | None = None,
    ) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.tracer = tracer

    async def audit_event(
        self,
        *,
        operation: str,
        resource_type: str,
        resource_id: str | None,
        payload: dict[str, Any] | None = None,
        actor_user_id: UUID | None = None,
        operation_result: str | None = "success",
    ) -> None:
        """Append a hash-chained AuditLog row scoped to self.tenant_id.

        Wraps `infrastructure.db.audit_helper.append_audit` with the
        service's tenant_id already bound. Caller manages transaction.
        """
        await append_audit(
            session=self.db,
            tenant_id=self.tenant_id,
            user_id=actor_user_id,
            operation=operation,
            resource_type=resource_type,
            resource_id=resource_id,
            operation_data=payload or {},
            operation_result=operation_result,
        )


__all__ = ["BusinessServiceBase"]

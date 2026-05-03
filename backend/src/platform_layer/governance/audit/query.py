"""
File: backend/src/platform_layer/governance/audit/query.py
Purpose: AuditQuery service — paginated read-only views over the WORM audit_log table.
Category: Platform / Governance / Audit
Scope: Phase 53 / Sprint 53.4 US-4

Description:
    Read-only access to the append-only audit_log (Sprint 49.3 hash chain).
    Tenant isolation strictly enforced via WHERE tenant_id = current_tenant.
    Filters: user_id / operation / resource_type / time range. Paginated.

Created: 2026-05-03 (Sprint 53.4 Day 4)

Modification History:
    - 2026-05-03: Initial creation (Sprint 53.4 Day 4 US-4)

Related:
    - infrastructure/db/models/audit.py (AuditLog ORM)
    - 09-db-schema-design.md Group 7 (audit_log)
    - 17-cross-category-interfaces.md §5
    - sprint-53-4-plan.md §US-4
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models.audit import AuditLog


@dataclass(frozen=True)
class AuditLogEntry:
    """Read-only DTO returned by AuditQuery."""

    id: int
    tenant_id: UUID
    user_id: UUID | None
    session_id: UUID | None
    operation: str
    resource_type: str
    resource_id: str | None
    operation_data: dict[str, Any]
    operation_result: str | None
    previous_log_hash: str
    current_log_hash: str
    timestamp_ms: int
    created_at: datetime


@dataclass(frozen=True)
class AuditQueryFilter:
    """Filter input for AuditQuery.list()."""

    tenant_id: UUID
    user_id: UUID | None = None
    operation: str | None = None
    resource_type: str | None = None
    from_ts_ms: int | None = None
    to_ts_ms: int | None = None
    limit: int = 100
    offset: int = 0


class AuditQuery:
    """Paginated read-only access to audit_log with tenant isolation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, query: AuditQueryFilter) -> list[AuditLogEntry]:
        stmt = select(AuditLog).where(AuditLog.tenant_id == query.tenant_id)
        if query.user_id is not None:
            stmt = stmt.where(AuditLog.user_id == query.user_id)
        if query.operation is not None:
            stmt = stmt.where(AuditLog.operation == query.operation)
        if query.resource_type is not None:
            stmt = stmt.where(AuditLog.resource_type == query.resource_type)
        if query.from_ts_ms is not None:
            stmt = stmt.where(AuditLog.timestamp_ms >= query.from_ts_ms)
        if query.to_ts_ms is not None:
            stmt = stmt.where(AuditLog.timestamp_ms < query.to_ts_ms)

        # Cap limit defensively to prevent runaway queries
        limit = max(1, min(query.limit, 1000))
        stmt = stmt.order_by(AuditLog.timestamp_ms.desc()).limit(limit).offset(query.offset)

        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._row_to_entry(row) for row in rows]

    @staticmethod
    def _row_to_entry(row: AuditLog) -> AuditLogEntry:
        return AuditLogEntry(
            id=row.id,
            tenant_id=row.tenant_id,
            user_id=row.user_id,
            session_id=row.session_id,
            operation=row.operation,
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            operation_data=dict(row.operation_data or {}),
            operation_result=row.operation_result,
            previous_log_hash=row.previous_log_hash,
            current_log_hash=row.current_log_hash,
            timestamp_ms=row.timestamp_ms,
            created_at=row.created_at,
        )

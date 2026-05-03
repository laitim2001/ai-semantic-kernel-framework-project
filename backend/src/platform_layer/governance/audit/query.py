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
    - 2026-05-04: Add verify_chain() method (Sprint 53.5 US-6) — wraps existing
        agent_harness/guardrails/audit/chain_verifier.verify_chain so the API
        layer doesn't reach into Cat 9 directly.
    - 2026-05-03: Initial creation (Sprint 53.4 Day 4 US-4)

Related:
    - infrastructure/db/models/audit.py (AuditLog ORM)
    - agent_harness/guardrails/audit/chain_verifier.py (underlying verify_chain)
    - 09-db-schema-design.md Group 7 (audit_log)
    - 17-cross-category-interfaces.md §5
    - sprint-53-4-plan.md §US-4 / sprint-53-5-plan.md §US-6
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_harness.guardrails.audit import (
    ChainVerificationResult,
)
from agent_harness.guardrails.audit import verify_chain as _verify_chain_impl
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


SessionFactory = Callable[[], AsyncSession] | Callable[[], Awaitable[AsyncSession]]


class AuditQuery:
    """Paginated read-only access to audit_log with tenant isolation."""

    def __init__(
        self,
        session: AsyncSession | None = None,
        session_factory: SessionFactory | None = None,
    ) -> None:
        """session: bound to current tenant for list(); required for list().
        session_factory: optional fresh-session factory used by verify_chain
            (chain walk needs paginated independent sessions to avoid holding
            one transaction open for tens of thousands of rows). Required for
            verify_chain. The two methods are independent — callers may pass
            only the one they need.
        """
        self._session = session
        self._session_factory = session_factory

    async def verify_chain(
        self,
        *,
        tenant_id: UUID,
        from_id: int | None = None,
        to_id: int | None = None,
        page_size: int = 100,
    ) -> ChainVerificationResult:
        """Walk the tenant's audit_log chain and recompute hashes.

        Wraps agent_harness.guardrails.audit.verify_chain (Cat 9 single-source
        per 17.md §5) so api/v1/audit doesn't import Cat 9 directly. Tenant
        isolation enforced at the chain_verifier layer (WHERE tenant_id = ...).

        Raises:
            RuntimeError: when session_factory was not supplied at construction.
        """
        if self._session_factory is None:
            raise RuntimeError(
                "AuditQuery.verify_chain requires session_factory; "
                "construct with session_factory= for chain verification."
            )
        return await _verify_chain_impl(
            self._session_factory,
            tenant_id,
            from_id=from_id,
            to_id=to_id,
            page_size=page_size,
        )

    async def list(self, query: AuditQueryFilter) -> list[AuditLogEntry]:
        if self._session is None:
            raise RuntimeError(
                "AuditQuery.list requires session; "
                "construct with session= for paginated listing."
            )
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

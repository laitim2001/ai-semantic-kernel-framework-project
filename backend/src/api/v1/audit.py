"""
File: backend/src/api/v1/audit.py
Purpose: HTTP endpoints for audit_log read + chain verification — auditor RBAC + tenant isolation.
Category: api/v1
Scope: Phase 53 / Sprint 53.5 US-5 + US-6

Description:
    Two endpoints, both gated by `Depends(require_audit_role)` (allows
    auditor / admin / compliance) and `Depends(get_current_tenant)`:

    - GET /api/v1/audit/log
        Paginated read of audit_log entries scoped to the JWT tenant.
        Filters: operation, resource_type, user_id, from_ts_ms, to_ts_ms.
        Pagination uses cursor-style offset+has_more (no `total` count —
        AuditQuery service does not compute count and we don't want to add
        a second COUNT query for unbounded chains; cursors are sufficient).

    - GET /api/v1/audit/verify-chain
        Walks the tenant's chain and returns ChainVerifyResult. Uses
        AuditQuery.verify_chain which wraps agent_harness/guardrails/audit
        (Cat 9 single-source per 17.md §5). Heavy operation — not for hot
        path; caller should treat as scheduled audit job.

    All requests outside the JWT tenant → 404 (per multi-tenant-data.md
    鐵律 — never reveal cross-tenant existence).

Created: 2026-05-04 (Sprint 53.5 Day 1)

Modification History (newest-first):
    - 2026-05-04: Initial creation (Sprint 53.5 US-5 + US-6) — paginated read +
        chain verify; cursor-based pagination; require_audit_role RBAC dep.

Related:
    - platform_layer/governance/audit/query.py (AuditQuery + ChainVerificationResult)
    - platform_layer/identity/auth.py (get_current_tenant + require_audit_role)
    - infrastructure/db/__init__.py (get_session_factory)
    - sprint-53-5-plan.md §US-5 / §US-6
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db import get_session_factory
from platform_layer.governance.audit.query import AuditLogEntry, AuditQueryFilter
from platform_layer.governance.service_factory import (
    ServiceFactory,
    get_service_factory,
)
from platform_layer.identity.auth import get_current_tenant, require_audit_role

router = APIRouter(prefix="/audit", tags=["audit"])

# Hard cap on page size; service caps at 1000 but exposing 1000 over HTTP
# is excessive — 200 is the published contract per sprint-53-5-plan.md.
_MAX_PAGE_SIZE = 200


class AuditLogEntryDTO(BaseModel):
    """Pydantic DTO for AuditLogEntry — JSON-serializable for HTTP."""

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

    @classmethod
    def from_entry(cls, entry: AuditLogEntry) -> AuditLogEntryDTO:
        return cls(
            id=entry.id,
            tenant_id=entry.tenant_id,
            user_id=entry.user_id,
            session_id=entry.session_id,
            operation=entry.operation,
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
            operation_data=entry.operation_data,
            operation_result=entry.operation_result,
            previous_log_hash=entry.previous_log_hash,
            current_log_hash=entry.current_log_hash,
            timestamp_ms=entry.timestamp_ms,
        )


class AuditLogPage(BaseModel):
    """Cursor-style page: items + has_more + next_offset."""

    items: list[AuditLogEntryDTO]
    has_more: bool
    next_offset: int | None
    page_size: int


class ChainVerifyResult(BaseModel):
    """Pydantic mirror of ChainVerificationResult for HTTP."""

    valid: bool = Field(description="True iff every recomputed hash matches stored.")
    broken_at_id: int | None = Field(description="First broken row id; null when valid.")
    total_entries: int = Field(description="Rows examined.")


async def _get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield a fresh AsyncSession bound to the request context."""
    factory = get_session_factory()
    async with factory() as session:
        yield session


@router.get("/log", response_model=AuditLogPage)
async def get_audit_log(
    current_tenant: UUID = Depends(get_current_tenant),
    _user_id: UUID = Depends(require_audit_role),
    session: AsyncSession = Depends(_get_db_session),
    factory: ServiceFactory = Depends(get_service_factory),
    operation: str | None = Query(default=None, description="Exact operation name filter."),
    resource_type: str | None = Query(default=None, description="Resource type filter."),
    user_id: UUID | None = Query(default=None, description="User id filter."),
    from_ts_ms: int | None = Query(
        default=None, description="Inclusive start timestamp (epoch ms)."
    ),
    to_ts_ms: int | None = Query(default=None, description="Exclusive end timestamp (epoch ms)."),
    offset: int = Query(default=0, ge=0, description="Cursor offset (default 0)."),
    page_size: int = Query(default=50, ge=1, le=_MAX_PAGE_SIZE, description="Items per page."),
) -> AuditLogPage:
    """Paginated read of audit_log scoped to JWT tenant.

    Cross-tenant attempts are silently filtered (the WHERE clause restricts
    by JWT tenant; rows from other tenants never appear).
    """
    # Fetch page_size + 1 to detect has_more without a second query.
    fetch_limit = page_size + 1
    query = AuditQueryFilter(
        tenant_id=current_tenant,
        user_id=user_id,
        operation=operation,
        resource_type=resource_type,
        from_ts_ms=from_ts_ms,
        to_ts_ms=to_ts_ms,
        limit=fetch_limit,
        offset=offset,
    )
    audit_query = factory.build_audit_query(session=session)
    rows = await audit_query.list(query)
    has_more = len(rows) > page_size
    page_rows = rows[:page_size]
    return AuditLogPage(
        items=[AuditLogEntryDTO.from_entry(r) for r in page_rows],
        has_more=has_more,
        next_offset=(offset + page_size) if has_more else None,
        page_size=page_size,
    )


@router.get("/verify-chain", response_model=ChainVerifyResult)
async def get_verify_chain(
    current_tenant: UUID = Depends(get_current_tenant),
    _user_id: UUID = Depends(require_audit_role),
    factory: ServiceFactory = Depends(get_service_factory),
    from_id: int | None = Query(
        default=None, ge=1, description="Inclusive start row id (default: chain head)."
    ),
    to_id: int | None = Query(
        default=None, ge=1, description="Inclusive end row id (default: chain tail)."
    ),
    page_size: int = Query(default=100, ge=10, le=1000, description="Walk batch size."),
) -> ChainVerifyResult:
    """Walk the tenant's audit_log chain and recompute hashes.

    Heavy operation — not for hot path. Caller should treat as a scheduled
    audit job. Tenant isolation enforced inside the chain walker.
    """
    # verify_chain needs a session factory (it walks paginated independent
    # sessions to avoid holding a single long transaction open). ServiceFactory
    # exposes the session_factory via build_audit_query() (Sprint 53.6 US-5).
    audit_query = factory.build_audit_query()
    try:
        result = await audit_query.verify_chain(
            tenant_id=current_tenant,
            from_id=from_id,
            to_id=to_id,
            page_size=page_size,
        )
    except RuntimeError as exc:
        # Defensive — shouldn't fire because we set session_factory above.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    return ChainVerifyResult(
        valid=result.valid,
        broken_at_id=result.broken_at_id,
        total_entries=result.total_entries,
    )


__all__ = ["router"]

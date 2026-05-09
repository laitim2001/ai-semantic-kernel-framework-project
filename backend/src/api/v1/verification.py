"""
File: backend/src/api/v1/verification.py
Purpose: HTTP endpoints for verification_log read — auditor RBAC + tenant isolation.
Category: api/v1
Scope: Phase 57 / Sprint 57.11 Day 1 / US-2

Description:
    Two endpoints, both gated by `Depends(require_audit_role)` (allows
    auditor / admin / compliance) and `Depends(get_current_tenant)`:

    - GET /api/v1/verification/recent
        Paginated read of verification_log entries scoped to the JWT tenant.
        Filters: session_id, verifier_type, passed.
        Returns VerificationLogPage (items / total / has_more / next_offset).

    - GET /api/v1/verification/{session_id}/correction-trace
        Full chronologically-sorted trace of verifier executions for one
        session. 404 if no entries. Used by chat-v2 inline panel (US-5) +
        admin page detail drill-down (US-4).

    All requests outside the JWT tenant → empty / 404 (per multi-tenant-data.md
    鐵律 — never reveal cross-tenant existence). RLS enforces at storage layer
    via `get_db_session_with_tenant` SET LOCAL app.tenant_id.

Created: 2026-05-10 (Sprint 57.11 Day 1 / US-2)

Modification History (newest-first):
    - 2026-05-10: Initial creation (Sprint 57.11 Day 1 / US-2) — paginated
      list + correction trace; RBAC + RLS dual-layer tenant isolation.

Related:
    - infrastructure/db/repositories/verification_log.py (VerificationLogRepository)
    - infrastructure/db/models/verification_log.py (VerificationLog ORM)
    - platform_layer/middleware/tenant_context.py (get_db_session_with_tenant — RLS)
    - platform_layer/identity/auth.py (get_current_tenant + require_audit_role)
    - sprint-57-11-plan.md §US-2 (REST endpoint spec)
    - api/v1/audit.py (sibling pattern reference)
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models.verification_log import VerificationLog
from infrastructure.db.repositories.verification_log import VerificationLogRepository
from platform_layer.identity.auth import get_current_tenant, require_audit_role
from platform_layer.middleware.tenant_context import get_db_session_with_tenant

router = APIRouter(prefix="/verification", tags=["verification"])

# Hard cap on page size; service caps at 1000 but exposing 1000 over HTTP
# is excessive — 200 is the published contract per sprint-57-11-plan.md §US-2.
_MAX_PAGE_SIZE = 200


class VerificationLogItem(BaseModel):
    """Pydantic DTO for VerificationLog — JSON-serializable for HTTP."""

    id: int
    tenant_id: UUID
    session_id: UUID
    turn_index: int
    verifier_name: str
    verifier_type: str
    passed: bool
    score: float | None
    reason: str | None
    suggested_correction: str | None
    correction_attempt: int
    created_at_ms: int = Field(
        description="Unix epoch milliseconds (created_at converted for JS Date interop)."
    )

    @classmethod
    def from_row(cls, row: VerificationLog) -> VerificationLogItem:
        return cls(
            id=row.id,
            tenant_id=row.tenant_id,
            session_id=row.session_id,
            turn_index=row.turn_index,
            verifier_name=row.verifier_name,
            verifier_type=row.verifier_type,
            passed=row.passed,
            score=row.score,
            reason=row.reason,
            suggested_correction=row.suggested_correction,
            correction_attempt=row.correction_attempt,
            created_at_ms=int(row.created_at.timestamp() * 1000),
        )


class VerificationLogPage(BaseModel):
    """Cursor-style page: items + total + has_more + next_offset."""

    items: list[VerificationLogItem]
    total: int = Field(description="Total matching rows (for UI pagination display).")
    has_more: bool
    next_offset: int | None
    page_size: int


class CorrectionTraceResponse(BaseModel):
    """Full sorted trace for one session."""

    session_id: UUID
    entries: list[VerificationLogItem]


@router.get("/recent", response_model=VerificationLogPage)
async def get_verification_recent(
    current_tenant: UUID = Depends(get_current_tenant),
    _user_id: UUID = Depends(require_audit_role),
    db: AsyncSession = Depends(get_db_session_with_tenant),
    session_id: UUID | None = Query(default=None, description="Filter to one session."),
    verifier_type: str | None = Query(
        default=None,
        description="Filter to one verifier kind (rules_based / llm_judge / external).",
    ),
    passed: bool | None = Query(
        default=None, description="Filter on outcome (true=passed, false=failed)."
    ),
    limit: int = Query(default=50, ge=1, le=_MAX_PAGE_SIZE, description="Page size."),
    offset: int = Query(default=0, ge=0, description="Cursor offset (default 0)."),
) -> VerificationLogPage:
    """Paginated verification_log read scoped to JWT tenant.

    Cross-tenant attempts are silently filtered (RLS + WHERE both enforce).
    """
    repo = VerificationLogRepository(db)
    items, total, has_more = await repo.list_recent(
        tenant_id=current_tenant,
        session_id_filter=session_id,
        verifier_type_filter=verifier_type,
        passed_filter=passed,
        limit=limit,
        offset=offset,
    )
    return VerificationLogPage(
        items=[VerificationLogItem.from_row(r) for r in items],
        total=total,
        has_more=has_more,
        next_offset=(offset + limit) if has_more else None,
        page_size=limit,
    )


@router.get(
    "/{session_id}/correction-trace",
    response_model=CorrectionTraceResponse,
)
async def get_correction_trace(
    session_id: UUID,
    current_tenant: UUID = Depends(get_current_tenant),
    _user_id: UUID = Depends(require_audit_role),
    db: AsyncSession = Depends(get_db_session_with_tenant),
) -> CorrectionTraceResponse:
    """Full sorted verification trace for one session.

    Sort: turn_index ASC, correction_attempt ASC, created_at ASC, id ASC.
    Returns 404 if no entries (no cross-tenant existence reveal).
    """
    repo = VerificationLogRepository(db)
    entries = await repo.list_correction_trace(
        tenant_id=current_tenant,
        session_id=session_id,
    )
    if not entries:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No verification entries for this session.",
        )
    return CorrectionTraceResponse(
        session_id=session_id,
        entries=[VerificationLogItem.from_row(r) for r in entries],
    )


__all__ = ["router"]

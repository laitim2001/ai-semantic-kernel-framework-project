"""
File: backend/src/api/v1/governance/router.py
Purpose: HTTP endpoints for HITL approval review (list pending + decide).
Category: api/v1
Scope: Phase 53 / Sprint 53.5 US-1

Description:
    Two endpoints for human reviewers to act on HITL approval requests.
    Both gated by `Depends(require_approver_role)` (approver / admin / manager)
    and `Depends(get_current_tenant)` so cross-tenant attempts return 404.

    - GET /api/v1/governance/approvals
        Lists pending approvals scoped to the JWT tenant.
        Returns rich DTOs (request_id, tool_name, requested_by_user_id, risk_level,
        reason, created_at, expires_at, payload).

    - POST /api/v1/governance/approvals/{request_id}/decide
        Apply reviewer decision (approved / rejected / escalated) with optional
        reason. Validates the request belongs to the JWT tenant before delegating
        to HITLManager.decide.

    Constructs a fresh DefaultHITLManager per request from get_session_factory.
    Notifier is intentionally NoopNotifier here — notifications fire at the
    request_approval site (orchestrator), not on decisions.

    All cross-tenant attempts return 404 (per multi-tenant-data.md 鐵律).

Created: 2026-05-04 (Sprint 53.5 Day 3 US-1)

Modification History (newest-first):
    - 2026-05-04: Initial creation (Sprint 53.5 US-1) — list pending + decide.

Related:
    - platform_layer/governance/hitl/manager.py (DefaultHITLManager)
    - platform_layer/identity/auth.py (require_approver_role, get_current_tenant)
    - infrastructure/db/__init__.py (get_session_factory)
    - sprint-53-5-plan.md §US-1
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from agent_harness._contracts.hitl import (
    ApprovalDecision,
    ApprovalRequest,
    DecisionType,
)
from infrastructure.db import get_session_factory
from platform_layer.governance.hitl.manager import DefaultHITLManager
from platform_layer.identity.auth import (
    get_current_tenant,
    require_approver_role,
)

router = APIRouter(prefix="/governance", tags=["governance"])


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


class ApprovalSummaryDTO(BaseModel):
    """JSON-serializable view of an ApprovalRequest for the reviewer UI."""

    request_id: UUID
    tenant_id: UUID
    session_id: UUID
    requester: str
    risk_level: str
    payload: dict[str, Any]
    sla_deadline: datetime
    context_snapshot: dict[str, Any]

    @classmethod
    def from_request(cls, req: ApprovalRequest) -> "ApprovalSummaryDTO":
        return cls(
            request_id=req.request_id,
            tenant_id=req.tenant_id,
            session_id=req.session_id,
            requester=req.requester,
            risk_level=req.risk_level.value,
            payload=req.payload,
            sla_deadline=req.sla_deadline,
            context_snapshot=req.context_snapshot,
        )


class PendingListResponse(BaseModel):
    items: list[ApprovalSummaryDTO]
    count: int


class DecisionRequestBody(BaseModel):
    decision: Literal["approved", "rejected", "escalated"] = Field(
        description="Reviewer's decision (case-insensitive accepted; normalized to upper)."
    )
    reason: str | None = Field(default=None, max_length=4096)


class DecisionResponse(BaseModel):
    request_id: UUID
    decision: str
    reviewer: str  # user_id from JWT (UUID stringified)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_manager() -> DefaultHITLManager:
    """Construct a fresh DefaultHITLManager per request.

    Notifier is None — the API layer doesn't fire notifications; the orchestrator
    (which calls request_approval) is the notifier site.
    """
    factory = get_session_factory()
    return DefaultHITLManager(session_factory=factory, notifier=None)


def _decision_to_enum(label: str) -> DecisionType:
    return DecisionType[label.upper()]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/approvals", response_model=PendingListResponse)
async def list_pending_approvals(
    current_tenant: UUID = Depends(get_current_tenant),
    _user_id: UUID = Depends(require_approver_role),
) -> PendingListResponse:
    """List pending approval requests for the JWT tenant.

    Cross-tenant rows are filtered at the HITLManager layer (sessions JOIN
    enforces tenant isolation).
    """
    manager = _build_manager()
    pending = await manager.get_pending(current_tenant)
    items = [ApprovalSummaryDTO.from_request(r) for r in pending]
    return PendingListResponse(items=items, count=len(items))


@router.post(
    "/approvals/{request_id}/decide",
    response_model=DecisionResponse,
)
async def decide_approval(
    request_id: UUID,
    body: DecisionRequestBody,
    current_tenant: UUID = Depends(get_current_tenant),
    user_id: UUID = Depends(require_approver_role),
) -> DecisionResponse:
    """Apply a reviewer decision; cross-tenant attempts return 404.

    Validates the approval belongs to the current tenant by fetching pending
    list first. (DefaultHITLManager.decide doesn't verify tenant, so we
    enforce it here at the HTTP boundary.)
    """
    manager = _build_manager()

    # Tenant validation: only let reviewer decide on requests they can see.
    # get_pending() returns only this tenant's pending rows; if request_id
    # isn't in the list, treat it as 404 (don't reveal cross-tenant existence).
    pending = await manager.get_pending(current_tenant)
    pending_ids = {p.request_id for p in pending}
    if request_id not in pending_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="approval not found",
        )

    decision = ApprovalDecision(
        request_id=request_id,
        decision=_decision_to_enum(body.decision),
        reviewer=str(user_id),
        decided_at=datetime.now(timezone.utc),
        reason=body.reason,
    )

    try:
        await manager.decide(request_id=request_id, decision=decision)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:  # state machine rejection
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return DecisionResponse(
        request_id=request_id,
        decision=decision.decision.value,
        reviewer=str(user_id),
    )


__all__ = ["router"]

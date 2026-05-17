"""
File: backend/src/api/v1/sessions.py
Purpose: Cat 7 State Snapshot REST facade for State Inspector UI (Sprint 57.19 US-B3).
Category: api/v1
Scope: Phase 57 / Sprint 57.19 Day 2 / US-B3

Description:
    Single GET endpoint, gated by `Depends(get_current_tenant)` + RLS via
    `Depends(get_db_session_with_tenant)`:

    - GET /api/v1/sessions/{session_id}/state
        Returns the LATEST state snapshot for the given session within the
        current tenant. Cross-tenant lookup returns 404 (not 403) per
        multi-tenant 鐵律 — never reveal cross-tenant existence.

    Per Sprint 57.19 Day 0 三-prong drift D-PRE-7 pivot:
    - state_mgmt/repository.py does NOT exist. Module contains _abc.py +
      checkpointer.py + reducer.py + decision_reducers.py. State persistence
      lives in `infrastructure/db/models/state.py` via StateSnapshot ORM
      (append-only, one row per turn) + LoopState pointer cache.
    - Implementation uses direct ORM `select(StateSnapshot)` ordered by
      version DESC LIMIT 1 (matches existing checkpointer.py read pattern).

    Multi-tenant: RLS enforced + redundant app-layer tenant_id filter for
    defence-in-depth per `.claude/rules/multi-tenant-data.md` 鐵律.

Created: 2026-05-17 (Sprint 57.19 Day 2 / US-B3)

Modification History (newest-first):
    - 2026-05-17: Initial creation (Sprint 57.19 Day 2 / US-B3) — StateSnapshot direct query

Related:
    - infrastructure/db/models/state.py:75 (StateSnapshot ORM)
    - infrastructure/db/models/sessions.py:73 (Session ORM — for tenant ownership cross-check)
    - platform_layer/middleware/tenant_context.py (get_db_session_with_tenant — RLS)
    - sprint-57-19-plan.md §US-B3
    - api/v1/loops.py (sibling sprint pattern)
    - 17-cross-category-interfaces.md §7 Cat 7 (no NEW ABC method this sprint)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models.state import StateSnapshot
from platform_layer.identity.auth import get_current_tenant
from platform_layer.middleware.tenant_context import get_db_session_with_tenant

router = APIRouter(prefix="/sessions", tags=["sessions"])


class StateSnapshotResponse(BaseModel):
    """Latest StateSnapshot for a session (Sprint 57.19 US-B3)."""

    session_id: UUID
    tenant_id: UUID
    version: int
    turn_num: int
    state_data: dict[str, Any]
    state_hash: str
    reason: str
    captured_at_ms: int


def _to_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


@router.get("/{session_id}/state", response_model=StateSnapshotResponse)
async def get_state_snapshot(
    session_id: UUID,
    current_tenant: UUID = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db_session_with_tenant),
) -> StateSnapshotResponse:
    """Return the latest StateSnapshot for `session_id` within current tenant.

    Cross-tenant requests return 404 (not 403) per multi-tenant 鐵律.
    Session not found also returns 404 (so non-existent and cross-tenant
    are indistinguishable to the caller).
    """
    stmt = (
        select(StateSnapshot)
        .where(StateSnapshot.session_id == session_id)
        .where(StateSnapshot.tenant_id == current_tenant)
        .order_by(desc(StateSnapshot.version))
        .limit(1)
    )
    snapshot = (await db.execute(stmt)).scalars().first()
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="session state not found",
        )
    return StateSnapshotResponse(
        session_id=snapshot.session_id,
        tenant_id=snapshot.tenant_id,
        version=snapshot.version,
        turn_num=snapshot.turn_num,
        state_data=snapshot.state_data,
        state_hash=snapshot.state_hash,
        reason=snapshot.reason,
        captured_at_ms=_to_ms(snapshot.created_at),
    )

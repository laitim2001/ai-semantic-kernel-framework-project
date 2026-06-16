"""
File: backend/src/api/v1/sessions.py
Purpose: Cat 7 State Snapshot REST facade for State Inspector UI (Sprint 57.19 US-B3).
Category: api/v1
Scope: Phase 57 / Sprint 57.19 Day 2 / US-B3

Description:
    GET endpoints, gated by `Depends(get_current_tenant)` + RLS via
    `Depends(get_db_session_with_tenant)`:

    - GET /api/v1/sessions
        Sprint 57.107 (B3): top-level session list for the current tenant,
        newest-first, with handoff lineage fields (handoff_parent_id +
        meta_data agent_role). Sidechain rows (subagent transcripts) are
        excluded. This closed the chat-v2 fixture SessionList backend gap
        (AD-ChatV2-SessionList-Backend) — the session LIST. The separate
        history-REPLAY gap (clicking a session to reload its conversation) is
        AD-ChatV2-Session-History-Replay-Phase58 → GET /{id}/events below.

    - GET /api/v1/sessions/{session_id}/events
        Sprint 57.125 (history replay, arc slice 1/2): the session's persisted
        SSE event stream, ordered by sequence_num, for the chat-v2 frontend
        (57.126) to replay through the live mergeEvent reducer. Rows are written
        by the main-session transcript observer (router._persist_main_event).
        A cross-tenant / unknown / event-less session returns 200 + [] (never
        404 — zero events is valid + cross-tenant existence must stay hidden).

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
    - 2026-06-16: Sprint 57.125 — GET /{id}/events replay endpoint (main transcript history)
    - 2026-06-12: Sprint 57.107 B3 — GET /sessions list (lineage fields, sidechain-excluded)
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

from infrastructure.db.models.sessions import MessageEvent
from infrastructure.db.models.state import StateSnapshot
from infrastructure.db.repositories.session_repository import SessionRepository
from platform_layer.identity.auth import get_current_tenant
from platform_layer.middleware.tenant_context import get_db_session_with_tenant

router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionListItem(BaseModel):
    """One top-level session row with handoff lineage (Sprint 57.107 B3)."""

    id: UUID
    title: str | None
    status: str
    agent_role: str | None
    handoff_parent_id: UUID | None
    started_at_ms: int
    total_turns: int


class SessionListResponse(BaseModel):
    """Top-level session list, newest-first (sidechains excluded)."""

    sessions: list[SessionListItem]


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    current_tenant: UUID = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db_session_with_tenant),
) -> SessionListResponse:
    """List the current tenant's top-level sessions, newest-first.

    Lineage: a handoff-booted child carries `handoff_parent_id` + its target
    persona in `agent_role` (from meta_data) so the FE can render the chain.
    Sidechain rows (subagent transcripts, Sprint 57.107 US-4) are excluded —
    they are nested under their parent, not top-level conversations.
    """
    rows = await SessionRepository(db).list_sessions(tenant_id=current_tenant)
    return SessionListResponse(
        sessions=[
            SessionListItem(
                id=row.id,
                title=row.title,
                status=row.status,
                agent_role=(row.meta_data or {}).get("agent_role"),
                handoff_parent_id=row.handoff_parent_id,
                started_at_ms=_to_ms(row.started_at),
                total_turns=row.total_turns,
            )
            for row in rows
        ]
    )


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


class SessionEventItem(BaseModel):
    """One persisted SSE event from a session's transcript (Sprint 57.125).

    Shape == the live SSE frame (serialize_loop_event output): the 57.126
    frontend feeds these through the same mergeEvent reducer it uses for the
    live stream → pixel-identical historical turns.
    """

    type: str
    data: dict[str, Any]
    sequence_num: int
    timestamp_ms: int


class SessionEventsResponse(BaseModel):
    """A session's persisted SSE event stream, ordered by sequence_num.

    Empty for a brand-new session (no events yet) AND for a cross-tenant /
    unknown session id (RLS + tenant filter yield 0 rows) — the two are
    indistinguishable, which satisfies the multi-tenant 鐵律 (never reveal
    cross-tenant existence). Unlike GET /{id}/state (which 404s on a missing
    snapshot), zero events is a VALID state here → 200 + [].
    """

    events: list[SessionEventItem]


@router.get("/{session_id}/events", response_model=SessionEventsResponse)
async def list_session_events(
    session_id: UUID,
    current_tenant: UUID = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db_session_with_tenant),
) -> SessionEventsResponse:
    """Return `session_id`'s persisted SSE event stream, ordered by sequence_num.

    The chat-v2 frontend (Sprint 57.126) replays these events through the live
    mergeEvent reducer to reconstruct a historical conversation. Rows are written
    by the main-session transcript observer (Sprint 57.125,
    router._persist_main_event). Tenant-scoped + RLS + a redundant app-layer
    tenant_id filter (defence-in-depth). A cross-tenant / unknown / event-less
    session returns 200 + [] (never 404 — zero events is a valid state and
    cross-tenant existence must not be revealed).
    """
    stmt = (
        select(MessageEvent)
        .where(MessageEvent.session_id == session_id)
        .where(MessageEvent.tenant_id == current_tenant)
        .order_by(MessageEvent.sequence_num)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return SessionEventsResponse(
        events=[
            SessionEventItem(
                type=row.event_type,
                data=row.event_data,
                sequence_num=row.sequence_num,
                timestamp_ms=row.timestamp_ms,
            )
            for row in rows
        ]
    )

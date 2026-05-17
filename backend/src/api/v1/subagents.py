"""
File: backend/src/api/v1/subagents.py
Purpose: Cat 11 Subagent Registry REST facade (Sprint 57.19 US-B4 — stub w/ carryover).
Category: api/v1
Scope: Phase 57 / Sprint 57.19 Day 2 / US-B4

Description:
    GET endpoint, gated by `Depends(get_current_tenant)`:

    - GET /api/v1/subagents?mode=X&cursor=B64&limit=50
        Lists subagent invocations for the current tenant.

    ⚠️ Sprint 57.19 implementation note (per Day 0 三-prong drift D-PRE-SCHEMA-3):

    There is NO persisted Subagent ORM table. Confirmed via:
    1. `grep -rn "class Subagent\\|__tablename__.*subagent" backend/src/infrastructure/db/`
       → 0 matches.
    2. SubagentSpawned / SubagentCompleted are in-memory LoopEvent dataclasses
       emitted by `agent_harness/subagent/dispatcher.py` to the SSE stream;
       they are NOT inserted into `audit_log` (grep confirms 0 matches for
       `audit.*subagent` / `action.*subagent` in backend/src).

    Therefore this endpoint returns an EMPTY items array + a documented
    `not_implemented_reason` field flagging the gap. The endpoint shape
    exists so frontend Subagents Registry page (US-C3 Day 4) can wire
    against a stable contract; backend will land real persistence in a
    follow-up sprint per AD-Subagent-RealList-Phase58 carryover.

    Acceptable alternatives considered (all out of Sprint 57.19 scope):
    - (a) Wire dispatcher.spawn / .completed to write audit_log rows with
      operation="subagent_spawned" / "subagent_completed" + read-side
      projection here. Cost: backend Cat 11 + Cat 12 wiring + new audit
      operation vocabulary. Defer to AD-Subagent-RealList-Phase58.
    - (b) Add new ORM model `SubagentInvocation` + Alembic migration 0018
      + dispatcher.spawn persist hook. Cost: schema change + migration
      review + cross-category integration. Defer.
    - (c) Live in-memory query via singleton SubagentRegistry. Cost:
      breaks request-scoped pattern + multi-replica deployments
      lose ephemeral state on instance reschedule. Rejected.

    Multi-tenant: when real persistence lands, RLS via
    `get_db_session_with_tenant` will enforce isolation per other Cat APIs.

Created: 2026-05-17 (Sprint 57.19 Day 2 / US-B4)

Modification History (newest-first):
    - 2026-05-17: Initial creation (Sprint 57.19 Day 2 / US-B4) — empty-list stub
      pending AD-Subagent-RealList-Phase58 carryover

Related:
    - agent_harness/subagent/dispatcher.py (live event source — emits Spawned/Completed)
    - agent_harness/_contracts/subagent.py (event dataclass definitions)
    - sprint-57-19-plan.md §US-B4
    - 17-cross-category-interfaces.md §11 Cat 11 (no NEW ABC method this sprint)
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from platform_layer.identity.auth import get_current_tenant

router = APIRouter(prefix="/subagents", tags=["subagents"])

_MAX_PAGE_SIZE = 200
_DEFAULT_PAGE_SIZE = 50


SubagentMode = Literal["code", "research", "architect", "review"]


class SubagentItem(BaseModel):
    """Subagent invocation row (response contract; populated when persistence lands)."""

    invocation_id: UUID
    mode: SubagentMode
    parent_session_id: UUID
    status: str
    total_tokens: int
    started_at_ms: int
    ended_at_ms: int | None


class SubagentsPage(BaseModel):
    items: list[SubagentItem]
    next_cursor: str | None
    page_size: int
    not_implemented_reason: str | None = None


@router.get("", response_model=SubagentsPage)
async def list_subagents(
    mode: SubagentMode | None = Query(
        None, description="Filter by subagent mode (code/research/architect/review)"
    ),
    cursor: str | None = Query(
        None, description="Opaque pagination cursor (unused until real listing)"
    ),
    limit: int = Query(_DEFAULT_PAGE_SIZE, ge=1, le=_MAX_PAGE_SIZE),
    current_tenant: UUID = Depends(get_current_tenant),  # noqa: ARG001 — wired for future use
) -> SubagentsPage:
    """List subagent invocations for current tenant.

    Sprint 57.19 returns empty list + AD-Subagent-RealList-Phase58 carryover
    note. Frontend can render "No subagent invocations yet" empty-state plus
    the carryover banner when `not_implemented_reason` is non-null.
    """
    return SubagentsPage(
        items=[],
        next_cursor=None,
        page_size=limit,
        not_implemented_reason=(
            "Subagent invocations are not yet persisted (per Sprint 57.19 D-PRE-SCHEMA-3). "
            "SubagentSpawned/Completed are in-memory LoopEvents only. "
            "Real listing pending AD-Subagent-RealList-Phase58 carryover."
        ),
    )

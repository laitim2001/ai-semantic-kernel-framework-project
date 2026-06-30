"""
File: backend/src/agent_harness/memory/session_summary_store.py
Purpose: Persist + read per-session rolling conversation summaries (Layer 5 persisted).
Category: 範疇 3 (Memory) / Layer 5 session summary
Scope: Phase 57 / Sprint 57.151

Description:
    DBSessionSummaryStore fills the designed-but-unwired `memory_session_summary`
    table (Layer 5 persisted summary; created in 0007, ORM MemorySessionSummary).
    Closes AD-Memory-Formation-Session-Recall (缺口 2): the memory-formation arc
    (57.148/149/150) recalls discrete USER FACTS but not what was discussed /
    decided in a prior session. This store is the底座 for cross-session
    conversation recall:

    - upsert_summary(): a rolling summary keyed on the table's `session_id UNIQUE`
      — a second write for the same session UPDATEs the one row (mirrors the
      57.150 UserLayer.write upsert), so the summary stays current as the
      conversation grows (the SessionSummarizer calls it after every send).
    - recent_for_user(): the cross-session recall read — JOINs `sessions` to scope
      by tenant + user, excludes the current session, orders by updated_at DESC.

    Multi-tenant: `memory_session_summary` is junction-style (NO direct tenant_id /
    NO direct RLS — 09.md L481 + 0009 docstring; tenant via the session FK). So:
    - upsert writes only to the non-RLS table keyed by an authoritative session_id
      (a session belongs to exactly one tenant via FK) → no set_config needed.
    - recent_for_user JOINs `sessions`, which IS FORCE RLS (0009), so it opens its
      own session with set_config('app.tenant_id', …) AND filters s.tenant_id +
      s.user_id explicitly (defense-in-depth).

    Best-effort: the caller (a post-send BackgroundTask) swallows failures —
    summary formation must never surface to the user.

Key Components:
    - DBSessionSummaryStore: upsert_summary + recent_for_user
    - _SummaryRow: frozen recall row (avoids detached-ORM-instance)

Created: 2026-06-30 (Sprint 57.151)
Last Modified: 2026-06-30

Modification History:
    - 2026-06-30: Initial creation (Sprint 57.151) — session-summary store (upsert + recall read)

Related:
    - infrastructure/db/models/memory.py:MemorySessionSummary — the ORM (+ updated_at, 0033)
    - infrastructure/db/models/sessions.py:Session — JOIN target (tenant_id + user_id, FORCE RLS)
    - agent_harness/memory/layers/user_layer.py:170-199 — the 57.150 upsert pattern mirrored here
    - agent_harness/state_mgmt/message_store.py:111-122 — own-session set_config FORCE-RLS pattern
    - agent_harness/memory/session_summarizer.py — the writer (cheap-tier summary → upsert)
    - agent_harness/memory/retrieval.py:recent_sessions — the reader (→ MemoryHint)
    - 09-db-schema-design.md L481-498 — the designed memory_session_summary schema
    - sprint-57-151-plan.md §3.2
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from infrastructure.db.models.memory import MemorySessionSummary
from infrastructure.db.models.sessions import Session as SessionRow

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _SummaryRow:
    """A recalled prior-session summary (frozen — not a live ORM instance)."""

    session_id: UUID
    summary: str
    unresolved_issues: list[object]
    updated_at: datetime


# === DBSessionSummaryStore: per-session rolling summary persistence ===
# Why: the 5-layer memory recalls discrete user facts but not the conversation
# arc of a prior session. The designed memory_session_summary table (0007) was
# never wired; this store fills it (rolling upsert) + reads it cross-session
# (JOIN sessions for tenant+user scope).
# Alternative considered:
#   - A new `memory_session` table — rejected: memory_session_summary already
#     exists + is designed for exactly this (Check-Existing 鐵律; Day-0 catch).
#   - Store the summary in memory_user with a category — rejected: would dilute
#     profile()'s identity top-k (the exact 57.150 dilution).
# Reference: AD-Memory-Formation-Session-Recall; sprint-57-151-plan.md §3.2.
class DBSessionSummaryStore:
    """Upsert + cross-session read of per-session conversation summaries.

    Holds a session FACTORY (not a request session): each call opens its own
    short-lived session. recent_for_user sets the RLS tenant context (the
    `sessions` JOIN target is FORCE RLS); upsert_summary writes only to the
    non-RLS memory_session_summary table keyed by the authoritative session_id.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def _set_tenant(self, db: AsyncSession, tenant_id: UUID) -> None:
        """SET LOCAL app.tenant_id for this txn — the `sessions` JOIN target is FORCE RLS.

        set_config(..., is_local=true) is the bind-param form of SET LOCAL (txn-scoped).
        Without it, the policy current_setting('app.tenant_id', true) is NULL → every
        SELECT on `sessions` returns nothing → recent_for_user would always be empty.
        Mirrors state_mgmt/message_store.py:_set_tenant.
        """
        await db.execute(
            text("SELECT set_config('app.tenant_id', :tid, true)"),
            {"tid": str(tenant_id)},
        )

    async def upsert_summary(
        self,
        *,
        session_id: UUID,
        summary: str,
        key_decisions: list[str],
        unresolved_issues: list[str],
    ) -> UUID:
        """Insert-or-update the one summary row for a session; return its id.

        Keyed on the table's `session_id UNIQUE` (designed: one summary per
        session). A repeat write (the rolling per-send summary) UPDATEs the row
        — summary / key_decisions / unresolved_issues refresh, updated_at bumps,
        created_at stays. Mirrors the 57.150 UserLayer.write upsert. No set_config:
        memory_session_summary is junction (no RLS) and session_id is authoritative.
        """
        async with self._factory() as db:
            stmt = (
                pg_insert(MemorySessionSummary)
                .values(
                    id=uuid4(),
                    session_id=session_id,
                    summary=summary,
                    key_decisions=key_decisions,
                    unresolved_issues=unresolved_issues,
                )
                .on_conflict_do_update(
                    index_elements=[MemorySessionSummary.session_id],
                    set_={
                        "summary": summary,
                        "key_decisions": key_decisions,
                        "unresolved_issues": unresolved_issues,
                        "updated_at": func.now(),
                    },
                )
                .returning(MemorySessionSummary.id)
            )
            row_id: UUID = (await db.execute(stmt)).scalar_one()
            await db.commit()
        return row_id

    async def recent_for_user(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        exclude_session_id: UUID | None,
        limit: int = 3,
    ) -> list[_SummaryRow]:
        """The user's most-recently-active prior-session summaries (best-effort).

        JOINs `sessions` to scope by tenant + user (the junction table has no
        tenant_id of its own); excludes the current session (its live transcript
        is already in context); orders by updated_at DESC. set_config first —
        `sessions` is FORCE RLS. Returns [] on any failure (recall degrades to
        no prior-session context, never breaks the build).
        """
        try:
            async with self._factory() as db:
                await self._set_tenant(db, tenant_id)
                stmt = (
                    select(
                        MemorySessionSummary.session_id,
                        MemorySessionSummary.summary,
                        MemorySessionSummary.unresolved_issues,
                        MemorySessionSummary.updated_at,
                    )
                    .join(SessionRow, SessionRow.id == MemorySessionSummary.session_id)
                    .where(
                        SessionRow.tenant_id == tenant_id,
                        SessionRow.user_id == user_id,
                    )
                    .order_by(MemorySessionSummary.updated_at.desc())
                    .limit(limit)
                )
                if exclude_session_id is not None:
                    stmt = stmt.where(MemorySessionSummary.session_id != exclude_session_id)
                rows = (await db.execute(stmt)).all()
            return [
                _SummaryRow(
                    session_id=r.session_id,
                    summary=r.summary,
                    unresolved_issues=list(r.unresolved_issues or []),
                    updated_at=r.updated_at,
                )
                for r in rows
            ]
        except Exception:  # noqa: BLE001 — recall is best-effort; never break the build
            logger.exception(
                "DBSessionSummaryStore.recent_for_user failed (best-effort; degrading to none)"
            )
            return []


__all__ = ["DBSessionSummaryStore"]

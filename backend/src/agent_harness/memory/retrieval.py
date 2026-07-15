"""
File: backend/src/agent_harness/memory/retrieval.py
Purpose: Cross-layer memory search coordinator (multi-axis: scope x time_scale).
Category: 範疇 3 (Memory) / Retrieval
Scope: Phase 51 / Sprint 51.2 Day 3

Description:
    MemoryRetrieval is the entry point for cross-layer memory search. It
    takes a query plus axis filters (scopes, time_scales) and dispatches
    to the corresponding MemoryLayer instances in parallel, then merges
    their results into a top-k list ranked by relevance_score * confidence.

    Multi-tenant safety:
    - tenant_id required (returns empty if None)
    - Each layer enforces its own tenant filter at storage level

    SessionLayer special case:
    - SessionLayer's ABC overloads user_id slot for session_id (per its
      docstring). This coordinator hides that detail: it accepts
      session_id explicitly and routes correctly per scope.

    Time scales:
    - "semantic" axis is a stub in 51.2; concrete layers return empty
      until CARRY-026 ships Qdrant integration.

    Always-on profile (Sprint 57.148):
    - profile() pulls a user's STANDING durable facts (user-scope long_term)
      regardless of the query — the always-injected identity path the
      PromptBuilder uses so a "who am I?" question recalls facts even when it
      shares no keyword with them. search() stays query-gated (ILIKE).

    Cross-session recall (Sprint 57.151):
    - recent_sessions() pulls a user's recent PRIOR-session summaries (the rolling
      memory_session_summary rows) excluding the current session — the cross-session
      conversation recall the PromptBuilder injects every turn (mirrors profile()).

Owner: 01-eleven-categories-spec.md §範疇 3 (Memory)
Created: 2026-04-30 (Sprint 51.2 Day 3.1)
Last Modified: 2026-06-30

Modification History (newest-first):
    - 2026-06-30: Sprint 57.151 — add recent_sessions() cross-session recall (缺口 2)
    - 2026-06-27: Sprint 57.148 — add profile() always-on user-scope pull (memory-formation Slice 1)
"""

from __future__ import annotations

import asyncio
from typing import Any, Literal, Protocol
from uuid import UUID

from agent_harness._contracts import MemoryHint, TraceContext
from agent_harness.memory._abc import MemoryLayer

_TimeScale = Literal["short_term", "long_term", "semantic"]
_Scope = Literal["system", "tenant", "role", "user", "session"]


class SessionSummaryReader(Protocol):
    """Structural type for the cross-session summary read (Sprint 57.151).

    DBSessionSummaryStore satisfies this; declared as a Protocol so MemoryRetrieval
    stays decoupled from the concrete DB store (and unit tests can pass a fake).
    """

    async def recent_for_user(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        exclude_session_id: UUID | None,
        limit: int,
    ) -> list[Any]:
        """Return the user's recent prior-session summary rows (see DBSessionSummaryStore)."""
        ...


class MemoryRetrieval:
    """Cross-layer search coordinator.

    Construct with a mapping of scope name -> MemoryLayer instance.
    Layers absent from the mapping are silently skipped (allows partial
    deployments, e.g., 51.2 9/15 cell scope).
    """

    def __init__(
        self,
        layers: dict[str, MemoryLayer],
        *,
        session_summary_store: SessionSummaryReader | None = None,
    ) -> None:
        self._layers = layers
        # Sprint 57.151 (AD-Memory-Formation-Session-Recall): the cross-session
        # summary read for recent_sessions(). None (the default) preserves every
        # existing construction + makes recent_sessions() a no-op (byte-identical).
        self._session_summary_store = session_summary_store

    async def search(
        self,
        *,
        query: str,
        tenant_id: UUID | None = None,
        user_id: UUID | None = None,
        session_id: UUID | None = None,
        scopes: tuple[_Scope, ...] = ("session", "user", "tenant"),
        time_scales: tuple[_TimeScale, ...] = ("long_term",),
        top_k: int = 5,
        trace_context: TraceContext | None = None,
    ) -> list[MemoryHint]:
        """Dispatch to relevant layers in parallel; merge + sort + top_k."""
        if tenant_id is None:
            return []

        tasks: list[asyncio.Task[list[MemoryHint]]] = []
        for scope in scopes:
            layer = self._layers.get(scope)
            if layer is None:
                continue

            # SessionLayer overloads user_id slot for session_id
            if scope == "session":
                read_user = session_id
            else:
                read_user = user_id

            tasks.append(
                asyncio.create_task(
                    layer.read(
                        query=query,
                        tenant_id=tenant_id,
                        user_id=read_user,
                        time_scales=time_scales,
                        max_hints=top_k * 2,  # over-fetch then re-rank
                        trace_context=trace_context,
                    )
                )
            )

        if not tasks:
            return []

        results = await asyncio.gather(*tasks, return_exceptions=True)
        merged: list[MemoryHint] = []
        for r in results:
            if isinstance(r, BaseException):
                # Layer failure is non-fatal: log via observability hook
                # (CARRY hook for 51.2 -> just skip silently)
                continue
            merged.extend(r)

        # Sort: relevance_score * confidence desc; ties broken by recency
        merged.sort(
            key=lambda h: (
                h.relevance_score * h.confidence,
                h.timestamp,
            ),
            reverse=True,
        )
        return merged[:top_k]

    async def profile(
        self,
        *,
        tenant_id: UUID | None = None,
        user_id: UUID | None = None,
        top_k: int = 5,
        trace_context: TraceContext | None = None,
    ) -> list[MemoryHint]:
        """Always-on user-scope durable-fact pull (NOT query-gated).

        Unlike search(), which ILIKE-matches hints against the current user
        message, profile() retrieves a user's STANDING identity / preference
        facts regardless of the message — the equivalent of Claude Code's
        always-injected memory. The PromptBuilder calls it every turn so a
        "who am I?" question recalls the facts even when the question shares no
        keyword with them.

        Scope: user layer, long_term axis only (the durable facts). Returns []
        when tenant_id / user_id is None (zero-trust) or the user layer is
        absent. Hints come back confidence-ordered (UserLayer.read), capped at
        top_k. The wildcard empty query relies on UserLayer.read's ILIKE '%%'
        matching all of the user's rows — search()'s caller-side empty-query
        guard (PromptBuilder._inject_memory_layers) is intentionally bypassed.
        """
        if tenant_id is None or user_id is None:
            return []
        layer = self._layers.get("user")
        if layer is None:
            return []
        return await layer.read(
            query="",
            tenant_id=tenant_id,
            user_id=user_id,
            time_scales=("long_term",),
            max_hints=top_k,
            trace_context=trace_context,
        )

    async def recent_sessions(
        self,
        *,
        tenant_id: UUID | None = None,
        user_id: UUID | None = None,
        exclude_session_id: UUID | None = None,
        top_k: int = 3,
        trace_context: TraceContext | None = None,
    ) -> list[MemoryHint]:
        """Always-on cross-session conversation recall (NOT query-gated).

        Mirrors profile(): pulls the user's recent prior-session summaries from the
        session_summary_store (the rolling memory_session_summary rows), EXCLUDING
        the current session (its live transcript is already in context). The
        PromptBuilder prepends these as layer="session" hints every turn so a NEW
        session answers "what were we working on last time?" with the real
        prior-session content. Closes AD-Memory-Formation-Session-Recall (缺口 2).

        Returns [] when tenant/user is None (zero-trust) or no store is wired (the
        chat_session_summary flag is off → byte-identical to pre-57.151). The store
        read is best-effort (returns [] on failure) so recall never crashes build.
        """
        if tenant_id is None or user_id is None or self._session_summary_store is None:
            return []
        rows = await self._session_summary_store.recent_for_user(
            tenant_id=tenant_id,
            user_id=user_id,
            exclude_session_id=exclude_session_id,
            limit=top_k,
        )
        hints: list[MemoryHint] = []
        for row in rows:
            summary_text = str(row.summary)
            unresolved = list(getattr(row, "unresolved_issues", None) or [])
            if unresolved:
                joined = "; ".join(str(u) for u in unresolved)
                summary_text = f"{summary_text} (open: {joined})"
            summary_text = summary_text[:200]
            # AD-Chat-Default-Persona-Demo-Leak (2026-07-15): prefix a dated
            # PRIOR-session marker so the agent distinguishes a prior session from the
            # current one — the drive-through saw the agent read a prior-session INC as
            # happening "in this session". updated_at is the rolling summary's last-touch.
            ts = getattr(row, "updated_at", None)
            if ts is not None:
                summary_text = f"[Prior session, {ts:%Y-%m-%d}] {summary_text}"
            hints.append(
                MemoryHint(
                    hint_id=row.session_id,
                    layer="session",
                    time_scale="long_term",
                    summary=summary_text,
                    confidence=0.6,
                    relevance_score=0.6,
                    full_content_pointer=f"memory_session_summary:{row.session_id}",
                    timestamp=row.updated_at,
                    tenant_id=tenant_id,
                )
            )
        return hints


__all__ = ["MemoryRetrieval", "SessionSummaryReader"]

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

Owner: 01-eleven-categories-spec.md §範疇 3 (Memory)
Created: 2026-04-30 (Sprint 51.2 Day 3.1)
"""

from __future__ import annotations

import asyncio
from typing import Literal
from uuid import UUID

from agent_harness._contracts import MemoryHint, TraceContext
from agent_harness.memory._abc import MemoryLayer

_TimeScale = Literal["short_term", "long_term", "semantic"]
_Scope = Literal["system", "tenant", "role", "user", "session"]


class MemoryRetrieval:
    """Cross-layer search coordinator.

    Construct with a mapping of scope name -> MemoryLayer instance.
    Layers absent from the mapping are silently skipped (allows partial
    deployments, e.g., 51.2 9/15 cell scope).
    """

    def __init__(self, layers: dict[str, MemoryLayer]) -> None:
        self._layers = layers

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


__all__ = ["MemoryRetrieval"]

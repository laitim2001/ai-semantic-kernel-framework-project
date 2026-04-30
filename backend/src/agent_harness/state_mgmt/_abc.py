"""
File: backend/src/agent_harness/state_mgmt/_abc.py
Purpose: Category 7 ABCs — Checkpointer + Reducer.
Category: 範疇 7 (State Management)
Scope: Phase 49 / Sprint 49.1 (stub; impl in Phase 53.1)

Description:
    State is split transient (in-memory) / durable (DB). Checkpointer
    snapshots durable state at safe points (after tool, after verify,
    on HITL pause). Reducer is the ONLY mutator of LoopState — all
    other categories read state, produce updates, and Reducer merges
    them with monotonic versioning.

    Time-travel: load any past version via Checkpointer.

Owner: 01-eleven-categories-spec.md §範疇 7
Single-source: 17.md §2.1

Created: 2026-04-29 (Sprint 49.1)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from agent_harness._contracts import LoopState, StateVersion, TraceContext


class Checkpointer(ABC):
    """Persists LoopState snapshots; supports time-travel."""

    @abstractmethod
    async def save(
        self,
        state: LoopState,
        *,
        trace_context: TraceContext | None = None,
    ) -> StateVersion: ...

    @abstractmethod
    async def load(
        self,
        *,
        version: int,
        trace_context: TraceContext | None = None,
    ) -> LoopState: ...

    @abstractmethod
    async def time_travel(
        self,
        *,
        target_version: int,
        trace_context: TraceContext | None = None,
    ) -> LoopState:
        """Reload state at a past version. Used for debugging + replay."""
        ...


class Reducer(ABC):
    """The ONLY mutator of LoopState. Categories submit updates here."""

    @abstractmethod
    async def merge(
        self,
        state: LoopState,
        update: dict[str, Any],
        *,
        source_category: str,
        trace_context: TraceContext | None = None,
    ) -> LoopState:
        """Apply update with monotonic version increment + audit trail."""
        ...

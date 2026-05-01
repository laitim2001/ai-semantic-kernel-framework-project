"""
File: backend/src/agent_harness/context_mgmt/compactor/_abc.py
Purpose: Compactor ABC — context compaction strategy abstraction.
Category: 範疇 4 (Context Management)
Scope: Phase 52 / Sprint 52.1

Description:
    Compactor decides whether to compact (should_compact) and runs the
    compaction (compact_if_needed). Concrete strategies: Structural / Semantic
    / Hybrid (Day 2 of Sprint 52.1). Cat 1 AgentLoop calls compact_if_needed
    once per turn (per Sprint 52.1 Story 1).

    Threshold defaults (per plan §1.5):
      - state.token_used > window * 0.75   OR
      - state.turn_count > 30
    Concrete impls may override should_compact() to use different heuristics.

    LLM neutrality: Compactor itself does NOT import LLM SDKs. SemanticCompactor
    receives a ChatClient instance via constructor injection (per
    10-server-side-philosophy.md §原則 2).

Owner: 01-eleven-categories-spec.md §範疇 4
Single-source: 17-cross-category-interfaces.md §2.1

Related:
    - _contracts/compaction.py (CompactionResult / CompactionStrategy)
    - _contracts/state.py (LoopState — input)
    - 04-anti-patterns.md AP-7 (Context Rot Ignored — root motivation)

Created: 2026-05-01 (Sprint 52.1, Day 1)

Modification History:
    - 2026-05-01: Initial creation (Sprint 52.1 Day 1) — Compactor ABC with should_compact + compact_if_needed  # noqa: E501
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from agent_harness._contracts import (
    CompactionResult,
    LoopState,
    TraceContext,
)


class Compactor(ABC):
    """Compacts loop state when token budget threshold exceeded.

    Concrete implementations:
        - StructuralCompactor (Day 2.1) — rule-based, < 100ms p95
        - SemanticCompactor (Day 2.3)   — LLM-driven summarisation, < 2s p95
        - HybridCompactor (Day 2.5)     — structural -> semantic fallback
    """

    # Default heuristic constants (concrete impls may override should_compact())
    DEFAULT_TOKEN_THRESHOLD_RATIO: float = 0.75
    DEFAULT_TURN_THRESHOLD: int = 30

    def should_compact(self, state: LoopState) -> bool:
        """Decide whether compact_if_needed() should do work.

        Default: trigger when token usage > 75% of window OR turn_count > 30.
        Concrete impls may override (e.g. HybridCompactor inspects sub-results).
        """
        token_window = getattr(state, "token_window", None)
        token_used = getattr(state, "token_used", 0)
        turn_count = getattr(state, "turn_count", 0)

        if token_window and token_used > token_window * self.DEFAULT_TOKEN_THRESHOLD_RATIO:
            return True
        if turn_count > self.DEFAULT_TURN_THRESHOLD:
            return True
        return False

    @abstractmethod
    async def compact_if_needed(
        self,
        state: LoopState,
        *,
        trace_context: TraceContext | None = None,
    ) -> CompactionResult:
        """Run compaction if should_compact() is True; else return passthrough.

        Returns CompactionResult with triggered=False (and compacted_state=None) when
        no work was done; otherwise triggered=True with the new compacted_state.
        Caller (Cat 1 loop) replaces state only if result.triggered.
        """
        ...

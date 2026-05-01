"""
File: backend/src/agent_harness/context_mgmt/compactor/hybrid.py
Purpose: HybridCompactor — structural first, semantic fallback when budget still over.
Category: 範疇 4 (Context Management)
Scope: Phase 52 / Sprint 52.1 Day 2

Description:
    HybridCompactor combines StructuralCompactor (cheap rule-based) with
    SemanticCompactor (LLM-driven) in a sequential fallback chain:

      1. Run StructuralCompactor.
      2. If structural's tokens_after still exceeds the threshold (75% of
         token_budget by default) AND there's still room to summarise,
         feed the structurally-compacted state into SemanticCompactor.
      3. If SemanticCompactor raises SemanticCompactionFailedError, log
         and return the structural result (graceful degradation).
      4. If structural returns triggered=False AND we still want to try
         semantic (e.g. token_used > threshold), call semantic directly.
      5. If both return triggered=False, return passthrough.

    Target p95 < 2.5s (per Sprint 52.1 §1 Story 2 acceptance).

Owner: 01-eleven-categories-spec.md §範疇 4
Single-source: 17-cross-category-interfaces.md §2.1 (Compactor row)

Related:
    - compactor/structural.py (sub-strategy 1)
    - compactor/semantic.py (sub-strategy 2; SemanticCompactionFailedError)
    - sprint-52-1-plan.md §1 Story 2 (3-strategy switchable)

Created: 2026-05-01 (Sprint 52.1 Day 2.5)

Modification History:
    - 2026-05-01: Initial creation (Sprint 52.1 Day 2.5) — sequential fallback
"""

from __future__ import annotations

import logging
import time
from dataclasses import replace

from agent_harness._contracts import (
    CompactionResult,
    CompactionStrategy,
    LoopState,
    TraceContext,
)
from agent_harness.context_mgmt.compactor._abc import Compactor
from agent_harness.context_mgmt.compactor.semantic import (
    SemanticCompactionFailedError,
    SemanticCompactor,
)
from agent_harness.context_mgmt.compactor.structural import StructuralCompactor

logger = logging.getLogger(__name__)


class HybridCompactor(Compactor):
    """Structural-then-semantic fallback compactor."""

    def __init__(
        self,
        *,
        structural: StructuralCompactor,
        semantic: SemanticCompactor,
        token_budget: int = 100_000,
        token_threshold_ratio: float = 0.75,
    ) -> None:
        self.structural = structural
        self.semantic = semantic
        self.token_budget = token_budget
        self.token_threshold_ratio = token_threshold_ratio

    def should_compact(self, state: LoopState) -> bool:
        """Hybrid triggers if either sub-strategy would trigger."""
        return self.structural.should_compact(state) or self.semantic.should_compact(state)

    async def compact_if_needed(
        self,
        state: LoopState,
        *,
        trace_context: TraceContext | None = None,
    ) -> CompactionResult:
        start = time.perf_counter()
        tokens_before = state.transient.token_usage_so_far

        if not self.should_compact(state):
            return CompactionResult(
                triggered=False,
                strategy_used=None,
                tokens_before=tokens_before,
                tokens_after=tokens_before,
                messages_compacted=0,
                duration_ms=(time.perf_counter() - start) * 1000.0,
                compacted_state=None,
            )

        # Step 1: structural pass
        structural_result = await self.structural.compact_if_needed(
            state, trace_context=trace_context
        )

        # Determine the post-structural state and whether semantic is still needed
        post_structural_state = (
            structural_result.compacted_state
            if structural_result.triggered and structural_result.compacted_state is not None
            else state
        )
        post_structural_tokens = (
            structural_result.tokens_after if structural_result.triggered else tokens_before
        )

        threshold = self.token_budget * self.token_threshold_ratio
        needs_semantic = post_structural_tokens > threshold

        if not needs_semantic:
            # Structural was sufficient (or both passthrough)
            return replace(
                structural_result,
                strategy_used=(CompactionStrategy.HYBRID if structural_result.triggered else None),
                duration_ms=(time.perf_counter() - start) * 1000.0,
            )

        # Step 2: semantic pass on the post-structural state
        try:
            semantic_result = await self.semantic.compact_if_needed(
                post_structural_state, trace_context=trace_context
            )
        except SemanticCompactionFailedError as err:
            logger.warning(
                "HybridCompactor: semantic stage failed; degrading to structural-only result: %s",
                err,
            )
            # Fallback: return structural result tagged as HYBRID (so callers see the strategy)
            return replace(
                structural_result,
                strategy_used=(CompactionStrategy.HYBRID if structural_result.triggered else None),
                duration_ms=(time.perf_counter() - start) * 1000.0,
            )

        if not semantic_result.triggered:
            # Semantic decided no work needed (e.g. nothing left to summarise)
            if not structural_result.triggered:
                # Neither stage did work
                logger.debug("HybridCompactor: both structural and semantic returned passthrough")
                return CompactionResult(
                    triggered=False,
                    strategy_used=None,
                    tokens_before=tokens_before,
                    tokens_after=tokens_before,
                    messages_compacted=0,
                    duration_ms=(time.perf_counter() - start) * 1000.0,
                    compacted_state=None,
                )
            return replace(
                structural_result,
                strategy_used=CompactionStrategy.HYBRID,
                duration_ms=(time.perf_counter() - start) * 1000.0,
            )

        # Both stages did work (or only semantic did)
        total_messages_compacted = (
            structural_result.messages_compacted if structural_result.triggered else 0
        ) + semantic_result.messages_compacted
        return CompactionResult(
            triggered=True,
            strategy_used=CompactionStrategy.HYBRID,
            tokens_before=tokens_before,
            tokens_after=semantic_result.tokens_after,
            messages_compacted=total_messages_compacted,
            duration_ms=(time.perf_counter() - start) * 1000.0,
            compacted_state=semantic_result.compacted_state,
        )

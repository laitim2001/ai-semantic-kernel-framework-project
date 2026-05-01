"""
File: backend/src/agent_harness/prompt_builder/_abc.py
Purpose: Category 5 ABC — PromptBuilder (layered prompt assembly).
Category: 範疇 5 (Prompt Construction)
Scope: Phase 49 / Sprint 49.1 (stub) + Phase 52 / Sprint 52.2 Day 1.2 (signature upgrade)

Description:
    PromptBuilder is the SINGLE entry point for assembling messages
    sent to LLM. It layers system → tenant memory → role memory →
    user memory → session history → user input + injects cache
    breakpoints.

    Anti-pattern AP-8 (No Centralized PromptBuilder) — V1 had prompt
    assembly scattered across LLM call sites. V2 forbids ad-hoc
    `messages = [{...}]` construction; everything goes through here.

Owner: 01-eleven-categories-spec.md §範疇 5
Single-source: 17.md §2.1

Created: 2026-04-29 (Sprint 49.1)
Last Modified: 2026-05-01

Modification History (newest-first):
    - 2026-05-01: Sprint 52.2 Day 1.2 — Add cache_policy + position_strategy
      kwargs (both default=None → builder uses its own defaults). 0 callers
      at upgrade time (stub stage), so no breakage. Per W3-2 audit carryover,
      trace_context is preserved as required cross-cutting parameter.
    - 2026-04-29: Initial creation (Sprint 49.1)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from agent_harness._contracts import (
    CachePolicy,
    LoopState,
    PromptArtifact,
    ToolSpec,
    TraceContext,
)
from agent_harness.prompt_builder.strategies import PositionStrategy


class PromptBuilder(ABC):
    """The single entry point for LLM prompt assembly."""

    @abstractmethod
    async def build(
        self,
        *,
        state: LoopState,
        tenant_id: UUID,
        user_id: UUID | None = None,
        tools: list[ToolSpec] | None = None,
        cache_policy: CachePolicy | None = None,
        position_strategy: PositionStrategy | None = None,
        trace_context: TraceContext | None = None,
    ) -> PromptArtifact:
        """Assemble all layers + cache breakpoints into PromptArtifact.

        Args:
            state: Current loop state (provides messages, tools, last user msg).
            tenant_id: Multi-tenant scope (REQUIRED; all memory queries filter
                by this; per multi-tenant-data.md tri-rule).
            user_id: User scope for user-layer memory; None = no user-scoped memory.
            tools: Tool schemas to make available this turn (Loop passes through
                its tool registry per turn). None or empty = no tools.
            cache_policy: Cache policy override; None = builder default.
            position_strategy: Position strategy override; None = builder default
                (typically LostInMiddleStrategy).
            trace_context: Cat 12 cross-cutting trace context. If provided,
                builder MUST emit a child span and propagate the context to
                memory_retrieval / cache_manager (per W3-2 audit carryover —
                trace_context cannot break mid-chain).

        Returns:
            PromptArtifact with messages + cache_breakpoints + token estimate
            + layer_metadata (records memory_layers_used, position_strategy
            class name, cache_sections, trace_id for SSE event linking).
        """
        ...

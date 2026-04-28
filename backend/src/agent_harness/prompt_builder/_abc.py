"""
File: backend/src/agent_harness/prompt_builder/_abc.py
Purpose: Category 5 ABC — PromptBuilder (layered prompt assembly).
Category: 範疇 5 (Prompt Construction)
Scope: Phase 49 / Sprint 49.1 (stub; impl in Phase 52.2)

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
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from agent_harness._contracts import LoopState, PromptArtifact, TraceContext


class PromptBuilder(ABC):
    """The single entry point for LLM prompt assembly."""

    @abstractmethod
    async def build(
        self,
        *,
        state: LoopState,
        tenant_id: UUID,
        user_id: UUID | None = None,
        trace_context: TraceContext | None = None,
    ) -> PromptArtifact:
        """Assemble all layers + cache breakpoints into PromptArtifact."""
        ...

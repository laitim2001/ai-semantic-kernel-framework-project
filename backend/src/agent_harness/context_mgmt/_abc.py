"""
File: backend/src/agent_harness/context_mgmt/_abc.py
Purpose: Category 4 ABCs — Compactor + TokenCounter + PromptCacheManager.
Category: 範疇 4 (Context Management)
Scope: Phase 49 / Sprint 49.1 (stub; impl in Phase 52.1)

Description:
    Context management addresses context rot. When token usage exceeds
    threshold, Compactor summarizes oldest observations + applies
    observation masking. TokenCounter abstracts per-provider tokenizers
    (tiktoken / claude-tokenizer / o200k_base).

    Compactor does NOT directly call subagent (range 11). It emits
    prompt hint suggesting delegation; LLM decides via task_spawn tool.

Owner: 01-eleven-categories-spec.md §範疇 4
Single-source: 17.md §2.1

Created: 2026-04-29 (Sprint 49.1)
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from agent_harness._contracts import (
    CacheBreakpoint,
    LoopState,
    Message,
    ToolSpec,
    TraceContext,
)


class TokenCounter(ABC):
    """Per-provider tokenizer abstraction. Lives at adapter boundary."""

    @abstractmethod
    def count(
        self,
        *,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
    ) -> int: ...


class Compactor(ABC):
    """Compacts loop state when token budget threshold exceeded."""

    @abstractmethod
    async def compact_if_needed(
        self,
        state: LoopState,
        *,
        trace_context: TraceContext | None = None,
    ) -> LoopState:
        """Returns compacted state (or original if no compaction needed)."""
        ...


class PromptCacheManager(ABC):
    """Decides cache breakpoint placement for prompt caching."""

    @abstractmethod
    def plan_breakpoints(
        self,
        messages: list[Message],
        *,
        provider_supports_caching: bool,
    ) -> list[CacheBreakpoint]: ...

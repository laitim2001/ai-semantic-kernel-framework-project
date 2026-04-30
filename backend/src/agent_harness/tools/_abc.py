"""
File: backend/src/agent_harness/tools/_abc.py
Purpose: Category 2 ABC — ToolRegistry + ToolExecutor.
Category: 範疇 2 (Tools)
Scope: Phase 49 / Sprint 49.1 (stub; impl in Phase 51.1)

Description:
    ToolRegistry holds registered ToolSpecs (built-in + cross-category-owned).
    ToolExecutor executes tool calls in a sandbox with concurrency control
    based on ToolAnnotations + ConcurrencyPolicy.

    Built-in tools (web_search / python_sandbox / etc.) live here.
    Cross-category tools (memory_*, task_spawn, request_approval, verify)
    are owned by their respective categories per 17.md §3.1 and registered
    via category-provided register_*() helpers.

Owner: 01-eleven-categories-spec.md §範疇 2
Single-source: 17.md §2.1

Created: 2026-04-29 (Sprint 49.1)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial ABC stub (Sprint 49.1)
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from agent_harness._contracts import (
    ExecutionContext,
    ToolCall,
    ToolResult,
    ToolSpec,
    TraceContext,
)


class ToolRegistry(ABC):
    """Registry of ToolSpecs available to LLM. Cross-category tools register here."""

    @abstractmethod
    def register(self, spec: ToolSpec) -> None: ...

    @abstractmethod
    def get(self, name: str) -> ToolSpec | None: ...

    @abstractmethod
    def list(self) -> list[ToolSpec]: ...


class ToolExecutor(ABC):
    """Executes ToolCalls per registry; respects concurrency policy + sandbox."""

    @abstractmethod
    async def execute(
        self,
        call: ToolCall,
        *,
        trace_context: TraceContext | None = None,
        context: ExecutionContext | None = None,
    ) -> ToolResult: ...

    @abstractmethod
    async def execute_batch(
        self,
        calls: list[ToolCall],
        *,
        trace_context: TraceContext | None = None,
        context: ExecutionContext | None = None,
    ) -> list[ToolResult]:
        """Honors ConcurrencyPolicy from each ToolSpec."""
        ...

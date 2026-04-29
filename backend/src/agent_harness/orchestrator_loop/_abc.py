"""
File: backend/src/agent_harness/orchestrator_loop/_abc.py
Purpose: Category 1 ABC — AgentLoop (TAO/ReAct loop entry point).
Category: 範疇 1 (Orchestrator Loop)
Scope: Phase 49 / Sprint 49.1 (stub only; implementation in Phase 50.1)

Description:
    The AgentLoop runs Think-Act-Observe (TAO) iterations until stop_reason
    indicates termination. It composes other categories (output parser,
    tools, guardrails, compactor, verifier, state, hitl) but owns only
    the loop control flow.

Key design points:
    - run() yields AsyncIterator[LoopEvent] (NOT sync callbacks; per 17.md §4.2)
    - while-True driven by stop_reason (NOT for-loop pipeline; per 04-anti-patterns AP-1)
    - tool results MUST be appended back to messages and re-sent to LLM

Owner: 01-eleven-categories-spec.md §範疇 1
Single-source: 17.md §2.1

Created: 2026-04-29 (Sprint 49.1)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial ABC stub (Sprint 49.1)

Related:
    - 01-eleven-categories-spec.md §範疇 1
    - 04-anti-patterns.md AP-1 (Pipeline disguised as Loop)
    - Phase 50.1 will implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator
from uuid import UUID

from agent_harness._contracts import LoopEvent, LoopState, TraceContext


class AgentLoop(ABC):
    """The TAO/ReAct loop. Phase 50.1 implements; this is the contract."""

    @abstractmethod
    async def run(
        self,
        *,
        session_id: UUID,
        user_input: str,
        trace_context: TraceContext | None = None,
    ) -> AsyncIterator[LoopEvent]:
        """Run the TAO loop until stop_reason terminates.

        Yields LoopEvent stream consumed by API / SSE handlers.
        Implementations MUST be while-true driven (not pipeline).
        """
        raise NotImplementedError("Phase 50.1 will implement")
        # required to make this an async generator at type level:
        yield

    @abstractmethod
    async def resume(
        self,
        *,
        state: LoopState,
        trace_context: TraceContext | None = None,
    ) -> AsyncIterator[LoopEvent]:
        """Resume from a checkpointed state (e.g. after HITL approval)."""
        raise NotImplementedError("Phase 50.1 will implement")
        yield

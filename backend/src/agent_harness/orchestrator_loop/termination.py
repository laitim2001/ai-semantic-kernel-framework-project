"""
File: backend/src/agent_harness/orchestrator_loop/termination.py
Purpose: Cat 1 termination conditions — pure predicates + reason enum.
Category: 範疇 1 (Orchestrator Loop)
Scope: Phase 50 / Sprint 50.1 (Day 2)

Description:
    Pure termination predicates consumed by `AgentLoopImpl.run()`. Each
    terminator returns a bool; the Loop checks all four at the top of every
    while-iteration and exits via `LoopCompleted` with the matching
    `TerminationReason`.

    `TripwireTerminator` ABC stub is reserved for Cat 9 (Guardrails) to plug
    in at Phase 53.3 — Cat 1 must NOT implement tripwire logic itself.

Decision rules:
    - END_TURN     → response.stop_reason == StopReason.END_TURN
    - MAX_TURNS    → turn_count >= max_turns (configured per run)
    - TOKEN_BUDGET → tokens_used >= token_budget
    - CANCELLED    → asyncio.current_task() has been cancelled (or external
                     CancelledError caught at boundary)

Key Components:
    - TerminationReason: enum carried into LoopCompleted.stop_reason (str
      value via .value to match 49.1 events.py LoopCompleted.stop_reason: str)
    - 4 terminator pure functions
    - TripwireTerminator: ABC stub for Cat 9 (Phase 53.3)

Created: 2026-04-30 (Sprint 50.1 Day 2.1)
Last Modified: 2026-04-30

Modification History (newest-first):
    - 2026-04-30: Initial creation (Sprint 50.1 Day 2.1) — 4 pure terminators +
        TerminationReason enum + TripwireTerminator ABC stub.

Related:
    - 01-eleven-categories-spec.md §範疇 1 — termination conditions list
    - 17-cross-category-interfaces.md §6 — Tripwire boundary (Cat 8 vs Cat 9)
    - 04-anti-patterns.md AP-1 — termination MUST be while-driven not for-counted
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from enum import Enum

from agent_harness._contracts import ChatResponse, LoopState, StopReason


class TerminationReason(Enum):
    """Why the Loop exited. Stored verbatim into LoopCompleted.stop_reason."""

    END_TURN = "end_turn"
    MAX_TURNS = "max_turns"
    TOKEN_BUDGET = "token_budget"
    CANCELLED = "cancelled"
    TRIPWIRE = "tripwire"  # Cat 9 — wired in Phase 53.3
    GUARDRAIL_BLOCKED = "guardrail_blocked"  # Cat 9 — non-tripwire BLOCK / ESCALATE
    ERROR = "error"  # Cat 8 — wired in Phase 53.2
    HANDOFF_NOT_IMPLEMENTED = "handoff_not_implemented"  # 50.1 stub for Cat 11


def should_terminate_by_stop_reason(response: ChatResponse) -> bool:
    """Terminate if the LLM signaled end_turn (final answer)."""
    return response.stop_reason == StopReason.END_TURN


def should_terminate_by_turns(turn_count: int, max_turns: int) -> bool:
    """Terminate if we've reached/exceeded the per-run turn cap."""
    return turn_count >= max_turns


def should_terminate_by_tokens(tokens_used: int, token_budget: int) -> bool:
    """Terminate if cumulative token usage hit the budget."""
    return tokens_used >= token_budget


def should_terminate_by_cancellation() -> bool:
    """True if the current asyncio task has been cancelled (external interrupt).

    Use inside the Loop to detect cancellation at safe checkpoints (between
    turns) without awaiting. The Loop ALSO catches `asyncio.CancelledError`
    around the chat() / execute() awaits as a hard boundary.
    """
    try:
        task = asyncio.current_task()
    except RuntimeError:
        return False
    return task is not None and task.cancelling() > 0


class TripwireTerminator(ABC):
    """Cat 9 plug-in point. Phase 53.3 implements; 50.1 only stubs the ABC.

    Loop calls `should_trigger(state)` between turns; if any registered
    tripwire returns True, the Loop exits with TerminationReason.TRIPWIRE
    immediately (no further chat / tool calls).
    """

    @abstractmethod
    async def should_trigger(self, state: LoopState) -> bool:
        """Return True to terminate the loop with TRIPWIRE reason."""
        ...

"""
File: backend/src/agent_harness/verification/_abc.py
Purpose: Category 10 ABC — Verifier (output verification + self-correction).
Category: 範疇 10 (Verification Loops)
Scope: Phase 49 / Sprint 49.1 (stub; impl in Phase 54.1)

Description:
    Verifier checks LLM output before it leaves the loop.
    Implementations may be rules-based (regex / schema check),
    LLM-judge (subagent verifies), or external (call to API).

    On failure, the loop may trigger self-correction (max 2 attempts
    per spec) by feeding suggested_correction back to LLM.

Owner: 01-eleven-categories-spec.md §範疇 10
Single-source: 17.md §2.1

Created: 2026-04-29 (Sprint 49.1)
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from agent_harness._contracts import LoopState, TraceContext, VerificationResult


class Verifier(ABC):
    """Verify LLM output before completing the loop."""

    @abstractmethod
    async def verify(
        self,
        *,
        output: str,
        state: LoopState,
        trace_context: TraceContext | None = None,
    ) -> VerificationResult: ...

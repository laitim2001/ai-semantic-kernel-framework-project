"""
File: backend/src/agent_harness/verification/correction_loop.py
Purpose: run_with_verification — wraps AgentLoop with verifier + self-correction (max 2).
Category: 範疇 10 (Verification Loops; Cat 1 wrapper)
Scope: Sprint 54.1 US-3

Description:
    Async generator that wraps `AgentLoop.run()` and adds:
    1. Post-completion verification (runs all verifiers in registry on the
       final LLM output).
    2. Self-correction loop (max N attempts): on failure, re-runs the loop
       with a correction-augmented user_input.
    3. VerificationPassed / VerificationFailed LoopEvent emission.
    4. LoopCompleted(stop_reason="verification_failed") when attempts exhausted.

    **Why a wrapper, not method on AgentLoopImpl (Drift D2 / D13 from 探勘)**:
    AgentLoopImpl.run() yields LoopCompleted at 17+ different exit points
    (turn limits / tripwire / cancelled / etc.). Centralizing verification
    via post-completion wrapping is cleaner than adding hooks to every exit.
    Additionally, AgentLoopImpl.run() takes `user_input: str` (not pre-built
    state.messages), so re-running with appended correction requires only
    string concatenation — no internal state mutation.

    **Self-correction strategy** (Drift D13 — user_input concatenation):
    On verification failure, the next attempt's `user_input` becomes:
        original_user_input + "\\n\\n[Previous attempt failed verification:
        <reason>. Suggested: <correction>. Please retry.]"
    This is consistent with the spec's "feed verification result back as user
    message" but adapted to AgentLoopImpl's stateless run() interface.

    **Cancellation safety**: The wrapper propagates asyncio.CancelledError
    from the inner agent_loop.run() and yields no further events.

Owner: 範疇 10 (verification/) — composed over Cat 1 AgentLoop ABC

Created: 2026-05-04 (Sprint 54.1 Day 3)
Last Modified: 2026-05-04

Modification History:
    - 2026-05-04: Initial (Sprint 54.1 US-3) — wrapper pattern per D2 / D13

Related:
    - agent_harness/orchestrator_loop/loop.py — AgentLoopImpl.run() wrapped
    - agent_harness/_contracts/events.py — VerificationPassed/Failed, LoopCompleted
    - 01-eleven-categories-spec.md §範疇 10 — self-correction loop spec
"""

from __future__ import annotations

from typing import AsyncIterator
from uuid import UUID

from agent_harness._contracts import LoopState, TraceContext, VerificationResult
from agent_harness._contracts.events import (
    LLMResponded,
    LoopCompleted,
    LoopEvent,
    VerificationFailed,
    VerificationPassed,
)
from agent_harness.orchestrator_loop import AgentLoop
from agent_harness.verification.registry import VerifierRegistry

# Stop-reason string for LoopCompleted when self-correction attempts exhausted.
# Kept as a plain string (not a TerminationReason enum value) to avoid an
# upstream Cat 8 enum extension; the SSE client treats it as opaque.
VERIFICATION_FAILED_STOP_REASON = "verification_failed"


async def run_with_verification(
    *,
    agent_loop: AgentLoop,
    session_id: UUID,
    user_input: str,
    trace_context: TraceContext | None = None,
    verifier_registry: VerifierRegistry | None = None,
    max_correction_attempts: int = 2,
) -> AsyncIterator[LoopEvent]:
    """Wrap AgentLoop.run() with verification + self-correction.

    If `verifier_registry` is None or empty, this delegates to `agent_loop.run()`
    transparently (no behavior change). Otherwise, after each agent_loop.run()
    completes, runs all registered verifiers on the final LLM output:
      - All pass → emit VerificationPassed(s) + the original LoopCompleted
      - Any fail → emit VerificationFailed(s); if attempts remain, augment
        user_input with correction guidance and re-run; else emit
        LoopCompleted(stop_reason="verification_failed")

    Args:
        agent_loop: Cat 1 AgentLoop ABC (typically AgentLoopImpl).
        session_id: Session identifier for the run.
        user_input: Initial user message text.
        trace_context: Optional Cat 12 trace context.
        verifier_registry: Cat 10 registry; None or empty = no verification.
        max_correction_attempts: How many CORRECTION re-runs after the
            initial attempt (so total runs = max_correction_attempts + 1).
            Spec mandates max 2 corrections (so up to 3 total runs).
    """
    if verifier_registry is None or len(verifier_registry) == 0:
        async for event in agent_loop.run(
            session_id=session_id,
            user_input=user_input,
            trace_context=trace_context,
        ):
            yield event
        return

    current_input = user_input
    attempt = 0  # 0 = first run; increment per correction
    while True:
        # Run inner loop; capture final completion + LLM output
        captured_completion: LoopCompleted | None = None
        latest_llm_content: str = ""

        async for event in agent_loop.run(
            session_id=session_id,
            user_input=current_input,
            trace_context=trace_context,
        ):
            if isinstance(event, LoopCompleted):
                # Don't yield yet — verify first
                captured_completion = event
                continue
            yield event
            if isinstance(event, LLMResponded) and event.content:
                latest_llm_content = event.content

        if captured_completion is None:
            # Inner ran to exhaustion without LoopCompleted (defensive — should not happen)
            return

        # If completion was a non-end_turn (max_turns / token_budget / tripwire / cancelled),
        # don't run verifiers — those exit reasons are independent of output quality.
        if captured_completion.stop_reason != "end_turn":
            yield captured_completion
            return

        # Run verifiers on the latest LLM output
        verifier_failures: list[VerificationResult] = []
        for verifier in verifier_registry.get_all():
            from typing import cast

            result = await verifier.verify(
                output=latest_llm_content,
                state=cast(LoopState, None),
                trace_context=trace_context,
            )
            if result.passed:
                yield VerificationPassed(
                    verifier=result.verifier_name,
                    score=result.score,
                    verifier_type=result.verifier_type,
                    trace_context=trace_context or TraceContext.create_root(),
                )
            else:
                yield VerificationFailed(
                    verifier=result.verifier_name,
                    reason=result.reason,
                    suggested_correction=result.suggested_correction,
                    verifier_type=result.verifier_type,
                    trace_context=trace_context or TraceContext.create_root(),
                )
                verifier_failures.append(result)

        if not verifier_failures:
            # All verifiers passed → forward original LoopCompleted
            yield captured_completion
            return

        # At least one verifier failed
        if attempt >= max_correction_attempts:
            # Out of correction budget; emit verification_failed completion
            yield LoopCompleted(
                stop_reason=VERIFICATION_FAILED_STOP_REASON,
                total_turns=captured_completion.total_turns,
                trace_context=trace_context or TraceContext.create_root(),
            )
            return

        # Attempt a correction: rebuild user_input with verifier feedback
        attempt += 1
        current_input = _build_correction_input(user_input, verifier_failures)


def _build_correction_input(original_input: str, failures: list[VerificationResult]) -> str:
    """Augment user_input with verification failure context for re-run.

    Format:
        <original>
        <blank line>
        [Previous attempt failed verification: <reason1>; <reason2>.
         Suggested: <correction1> / <correction2>. Please retry.]
    """
    reasons = [f.reason or "unspecified" for f in failures]
    corrections = [f.suggested_correction for f in failures if f.suggested_correction]
    parts = [f"Previous attempt failed verification: {'; '.join(reasons)}"]
    if corrections:
        parts.append(f"Suggested: {' / '.join(corrections)}")
    parts.append("Please retry.")
    correction_block = "[" + ". ".join(parts) + "]"
    return f"{original_input}\n\n{correction_block}"

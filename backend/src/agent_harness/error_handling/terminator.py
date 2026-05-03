"""
File: backend/src/agent_harness/error_handling/terminator.py
Purpose: DefaultErrorTerminator — Cat-8-owned loop termination decision.
Category: 範疇 8 (Error Handling)
Scope: Phase 53.2 / Sprint 53.2

Description:
    Concrete impl of `ErrorTerminator` ABC (defined in `_abc.py`).

    Per 17.md §6 boundary裁定: Tripwire violations belong to range 9
    (Guardrails). Cat 8's terminator handles operational failures only:

      BUDGET_EXCEEDED       per-tenant ErrorBudget exhausted (US-4)
      CIRCUIT_OPEN          provider CircuitBreaker open (US-3)
      FATAL_EXCEPTION       FATAL ErrorClass (bug / unrecognized)
      MAX_RETRIES_EXHAUSTED hard global retry cap (default 5)

    Caller (AgentLoop, Day 3-4 US-6) consults `should_terminate()` after
    each tool failure. If TerminationDecision.terminate is True, the loop:
      1. Emits LoopTerminated event with reason + detail
      2. Asks Checkpointer to save final state (Cat 7 integration)
      3. Returns to caller with stop_reason="loop_terminated"

    Why an enum (not strings)?
      - Type safety in pattern-matching at consumers.
      - Distinct from Cat 9 Tripwire reasons — collision-free
        observability (different metric labels).

Key Components:
    - TerminationReason: enum (4 reasons; non-Tripwire)
    - TerminationDecision: frozen dataclass (terminate / reason / detail)
    - DefaultErrorTerminator: implements ErrorTerminator ABC

Owner: 01-eleven-categories-spec.md §Cat 8 + 17.md §6 boundary
Created: 2026-05-03 (Sprint 53.2 Day 3)

Modification History (newest-first):
    - 2026-05-03: Initial creation (Sprint 53.2 Day 3) — US-5 production impl
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from agent_harness._contracts.errors import ErrorContext
from agent_harness.error_handling._abc import ErrorClass, ErrorTerminator
from agent_harness.error_handling.budget import TenantErrorBudget
from agent_harness.error_handling.circuit_breaker import DefaultCircuitBreaker


class TerminationReason(Enum):
    """Cat-8-owned termination reasons. NOT Tripwire (per 17.md §6)."""

    BUDGET_EXCEEDED = "budget_exceeded"
    CIRCUIT_OPEN = "circuit_open"
    FATAL_EXCEPTION = "fatal_exception"
    MAX_RETRIES_EXHAUSTED = "max_retries_exhausted"


@dataclass(frozen=True)
class TerminationDecision:
    terminate: bool
    reason: TerminationReason | None = None
    detail: str | None = None


class DefaultErrorTerminator(ErrorTerminator):
    """Composes Cat 8 building blocks (budget + circuit) + global retry cap.

    Args:
        circuit_breaker: optional DefaultCircuitBreaker for CIRCUIT_OPEN
            check. If None, that reason never fires.
        error_budget: optional TenantErrorBudget for BUDGET_EXCEEDED check.
            If None, that reason never fires.
        max_retry_attempts: global hard cap. When `context.attempt_num >=
            max_retry_attempts`, MAX_RETRIES_EXHAUSTED fires regardless
            of per-tool RetryPolicy. Default 5 (matches Cat 8 spec
            conservative overall cap).
    """

    def __init__(
        self,
        *,
        circuit_breaker: DefaultCircuitBreaker | None = None,
        error_budget: TenantErrorBudget | None = None,
        max_retry_attempts: int = 5,
    ) -> None:
        self._circuit_breaker = circuit_breaker
        self._error_budget = error_budget
        self._max_retry_attempts = max_retry_attempts

    # === ABC compatibility (sync, threshold-based) =========================
    # Stub `ErrorTerminator.should_terminate(consecutive_errors,
    # budget_exhausted, circuit_open) -> bool` — preserved for callers
    # that have already computed those flags inline.

    def should_terminate(
        self,
        *,
        consecutive_errors: int,
        budget_exhausted: bool,
        circuit_open: bool,
    ) -> bool:
        if budget_exhausted or circuit_open:
            return True
        if consecutive_errors >= self._max_retry_attempts:
            return True
        return False

    # === Rich async decision (Day 3-4 AgentLoop integration consumer) ======

    async def evaluate(
        self,
        *,
        error: BaseException,
        error_class: ErrorClass,
        context: ErrorContext,
        tenant_id: UUID,
    ) -> TerminationDecision:
        """Compose budget + circuit + classification into a single decision.

        Order of checks (precedence high → low):
            1. Budget exceeded → BUDGET_EXCEEDED (cheapest, highest impact)
            2. Circuit open → CIRCUIT_OPEN
            3. FATAL classification → FATAL_EXCEPTION
            4. Hard retry cap reached → MAX_RETRIES_EXHAUSTED
            5. otherwise: do not terminate
        """
        # 1. Budget
        if self._error_budget is not None:
            exceeded, detail = await self._error_budget.is_exceeded(tenant_id)
            if exceeded:
                return TerminationDecision(
                    terminate=True,
                    reason=TerminationReason.BUDGET_EXCEEDED,
                    detail=detail,
                )

        # 2. Circuit
        if self._circuit_breaker is not None and context.provider:
            if await self._circuit_breaker.is_open(context.provider):
                return TerminationDecision(
                    terminate=True,
                    reason=TerminationReason.CIRCUIT_OPEN,
                    detail=f"provider={context.provider}",
                )

        # 3. Fatal classification
        if error_class == ErrorClass.FATAL:
            return TerminationDecision(
                terminate=True,
                reason=TerminationReason.FATAL_EXCEPTION,
                detail=repr(error),
            )

        # 4. Hard cap
        if context.attempt_num >= self._max_retry_attempts:
            return TerminationDecision(
                terminate=True,
                reason=TerminationReason.MAX_RETRIES_EXHAUSTED,
                detail=f"attempt={context.attempt_num}",
            )

        return TerminationDecision(terminate=False)

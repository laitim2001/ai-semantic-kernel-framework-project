"""
File: backend/src/agent_harness/error_handling/circuit_breaker.py
Purpose: Production-grade DefaultCircuitBreaker (per-resource 3-state).
Category: 範疇 8 (Error Handling)
Scope: Phase 53.2 / Sprint 53.2

Description:
    Concrete impl of `CircuitBreaker` ABC (defined in `_abc.py`):
      - record(*, success: bool, resource: str)
      - is_open(resource: str) -> bool

    Per-resource state machine (CLOSED → OPEN → HALF_OPEN → CLOSED):

      CLOSED      Normal operation. Each `record(success=False)` increments
                  consecutive_failures; reaching `threshold` opens the
                  circuit.

      OPEN        All callers see `is_open(resource) == True` and short
                  circuit. After `recovery_timeout_seconds` since the last
                  failure, the next is_open() probe transitions to HALF_OPEN
                  and returns False (allows ONE trial call).

      HALF_OPEN   Trial state. The next `record()` decides:
                    success=True → CLOSED (reset failure counter)
                    success=False → OPEN (re-open with full timeout)

    Adapter integration (Day 2.3):
      - `adapters/_base/chat_client.py` consults `is_open(provider)` before
        each chat() call. If open → raise CircuitOpenError; never hit the
        provider API.
      - On call completion, adapter calls `record(success=..., resource=
        provider)`.

    Concurrency: asyncio.Lock guards state transitions. Per-resource state
    isolation means independent locking by resource key (single shared
    Lock for simplicity; per-resource Lock may be added in 54.x if
    contention measurable).

Key Components:
    - CircuitState: enum (CLOSED / OPEN / HALF_OPEN)
    - CircuitBreakerStats: per-resource state tuple
    - DefaultCircuitBreaker: implements CircuitBreaker ABC
    - CircuitOpenError: raised by adapter when is_open returns True

Owner: 01-eleven-categories-spec.md §Cat 8 + 17.md §1.1
Created: 2026-05-03 (Sprint 53.2 Day 2)

Modification History (newest-first):
    - 2026-05-03: Initial creation (Sprint 53.2 Day 2) — US-3 production impl
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

from agent_harness.error_handling._abc import CircuitBreaker


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerStats:
    """Per-resource mutable state."""

    state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    last_failure_at: datetime | None = None
    half_open_call_count: int = 0


class CircuitOpenError(Exception):
    """Raised by adapter integration when caller tries a call while the
    circuit for that resource is OPEN. Cat 8 ErrorPolicy classifies this
    as TRANSIENT (retry policy decides whether to wait or give up)."""


class DefaultCircuitBreaker(CircuitBreaker):
    """Per-resource 3-state circuit breaker.

    Args:
        threshold: consecutive failures needed to transition CLOSED→OPEN.
            Default 5 (Stripe-pattern conservative).
        recovery_timeout_seconds: how long to wait in OPEN before allowing
            one HALF_OPEN trial. Default 60s.
        half_open_max_calls: how many concurrent HALF_OPEN trial calls
            allowed. Default 1 (strictly one at a time).
    """

    def __init__(
        self,
        *,
        threshold: int = 5,
        recovery_timeout_seconds: float = 60.0,
        half_open_max_calls: int = 1,
    ) -> None:
        if threshold < 1:
            raise ValueError("threshold must be >= 1")
        if recovery_timeout_seconds <= 0:
            raise ValueError("recovery_timeout_seconds must be > 0")
        self._threshold = threshold
        self._recovery_timeout_seconds = recovery_timeout_seconds
        self._half_open_max_calls = half_open_max_calls
        self._states: dict[str, CircuitBreakerStats] = {}
        self._lock = asyncio.Lock()

    def _stats(self, resource: str) -> CircuitBreakerStats:
        if resource not in self._states:
            self._states[resource] = CircuitBreakerStats()
        return self._states[resource]

    async def is_open(self, resource: str) -> bool:
        """Return True if the circuit blocks new calls for this resource."""
        async with self._lock:
            s = self._stats(resource)
            now = datetime.now(timezone.utc)

            if s.state == CircuitState.OPEN:
                # Time-elapsed check: transition to HALF_OPEN when timeout passed.
                if s.last_failure_at is not None and now - s.last_failure_at >= timedelta(
                    seconds=self._recovery_timeout_seconds
                ):
                    s.state = CircuitState.HALF_OPEN
                    s.half_open_call_count = 0
                    # Permit this caller as the trial.
                    s.half_open_call_count += 1
                    return False
                return True

            if s.state == CircuitState.HALF_OPEN:
                # Already in trial; only `half_open_max_calls` allowed concurrently.
                if s.half_open_call_count >= self._half_open_max_calls:
                    return True  # short circuit; another caller is the trial
                s.half_open_call_count += 1
                return False

            # CLOSED: pass through.
            return False

    async def record(
        self,
        *,
        success: bool,
        resource: str,
    ) -> None:
        """Update per-resource state from a completed call result."""
        async with self._lock:
            s = self._stats(resource)
            now = datetime.now(timezone.utc)

            if success:
                if s.state in (CircuitState.HALF_OPEN, CircuitState.OPEN):
                    # Trial passed → close.
                    s.state = CircuitState.CLOSED
                s.consecutive_failures = 0
                s.half_open_call_count = max(0, s.half_open_call_count - 1)
                return

            # Failure path
            s.consecutive_failures += 1
            s.last_failure_at = now
            s.half_open_call_count = max(0, s.half_open_call_count - 1)

            if s.state == CircuitState.HALF_OPEN:
                # Trial failed → re-open with fresh timeout window.
                s.state = CircuitState.OPEN
                return

            if s.state == CircuitState.CLOSED and s.consecutive_failures >= self._threshold:
                s.state = CircuitState.OPEN

    # ---- introspection helpers (used by tests + observability) ----

    def state_of(self, resource: str) -> CircuitState:
        """Read-only state view (no lock — eventually-consistent read)."""
        return self._stats(resource).state

    def consecutive_failures_of(self, resource: str) -> int:
        return self._stats(resource).consecutive_failures

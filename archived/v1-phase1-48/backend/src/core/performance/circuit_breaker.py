"""Circuit Breaker — LLM API failure protection and graceful degradation.

Implements the circuit-breaker pattern for LLM API calls:
  - CLOSED: Normal operation, requests pass through
  - OPEN: Too many failures, requests short-circuit with fallback
  - HALF_OPEN: Probe mode, one request allowed to test recovery

Sprint 116 — Phase 37 E2E Assembly B.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"        # Normal — requests pass through
    OPEN = "open"            # Tripped — requests short-circuit
    HALF_OPEN = "half_open"  # Probe — one request allowed


class CircuitBreaker:
    """Circuit breaker for protecting LLM API calls.

    Args:
        failure_threshold: Failures before opening circuit.
        recovery_timeout: Seconds before trying half-open probe.
        success_threshold: Successes in half-open to close circuit.
        name: Identifier for logging.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2,
        name: str = "llm",
    ) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._success_threshold = success_threshold
        self._name = name

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float = 0.0
        self._lock = asyncio.Lock()

        # Metrics
        self._total_calls = 0
        self._total_failures = 0
        self._total_short_circuits = 0

    @property
    def state(self) -> CircuitState:
        """Current circuit state."""
        return self._state

    @property
    def is_open(self) -> bool:
        return self._state == CircuitState.OPEN

    def get_stats(self) -> dict:
        """Return circuit breaker statistics."""
        return {
            "name": self._name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "total_calls": self._total_calls,
            "total_failures": self._total_failures,
            "total_short_circuits": self._total_short_circuits,
            "failure_threshold": self._failure_threshold,
            "recovery_timeout": self._recovery_timeout,
        }

    async def call(
        self,
        func: Callable[..., Any],
        *args: Any,
        fallback: Optional[Callable[..., Any]] = None,
        **kwargs: Any,
    ) -> Any:
        """Execute a function through the circuit breaker.

        Args:
            func: Async callable to protect.
            fallback: Optional fallback when circuit is open.

        Returns:
            Result of func or fallback.

        Raises:
            CircuitOpenError: When circuit is open and no fallback.
        """
        async with self._lock:
            self._total_calls += 1
            should_allow = self._should_allow_request()

        if not should_allow:
            self._total_short_circuits += 1
            logger.warning(
                "Circuit breaker '%s' is OPEN — short-circuiting request",
                self._name,
            )
            if fallback:
                return await fallback(*args, **kwargs) if asyncio.iscoroutinefunction(fallback) else fallback(*args, **kwargs)
            raise CircuitOpenError(
                f"Circuit breaker '{self._name}' is open "
                f"(failures={self._failure_count}/{self._failure_threshold})"
            )

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise

    def _should_allow_request(self) -> bool:
        """Determine if a request should be allowed through."""
        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self._recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
                logger.info(
                    "Circuit breaker '%s': OPEN → HALF_OPEN (%.1fs elapsed)",
                    self._name, elapsed,
                )
                return True
            return False

        # HALF_OPEN — allow probe requests
        return True

    async def _on_success(self) -> None:
        """Handle a successful call."""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self._success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    logger.info(
                        "Circuit breaker '%s': HALF_OPEN → CLOSED (recovered)",
                        self._name,
                    )
            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                if self._failure_count > 0:
                    self._failure_count = max(0, self._failure_count - 1)

    async def _on_failure(self) -> None:
        """Handle a failed call."""
        async with self._lock:
            self._failure_count += 1
            self._total_failures += 1
            self._last_failure_time = time.monotonic()

            if self._state == CircuitState.HALF_OPEN:
                # Probe failed — reopen circuit
                self._state = CircuitState.OPEN
                logger.warning(
                    "Circuit breaker '%s': HALF_OPEN → OPEN (probe failed)",
                    self._name,
                )
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self._failure_threshold:
                    self._state = CircuitState.OPEN
                    logger.warning(
                        "Circuit breaker '%s': CLOSED → OPEN "
                        "(failures=%d/%d)",
                        self._name,
                        self._failure_count,
                        self._failure_threshold,
                    )

    async def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        async with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            logger.info("Circuit breaker '%s': manually reset to CLOSED", self._name)


class CircuitOpenError(Exception):
    """Raised when a request is rejected by an open circuit breaker."""

    pass


# ---------------------------------------------------------------------------
# Global singleton for LLM circuit breaker
# ---------------------------------------------------------------------------
_llm_circuit_breaker: Optional[CircuitBreaker] = None


def get_llm_circuit_breaker() -> CircuitBreaker:
    """Return the global LLM circuit breaker singleton."""
    global _llm_circuit_breaker
    if _llm_circuit_breaker is None:
        _llm_circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0,
            success_threshold=2,
            name="llm_api",
        )
    return _llm_circuit_breaker

"""
File: backend/tests/unit/agent_harness/error_handling/test_circuit_breaker.py
Purpose: Unit tests for DefaultCircuitBreaker (Cat 8 US-3).
Category: Tests / 範疇 8
Scope: Phase 53.2 / Sprint 53.2

Created: 2026-05-03 (Sprint 53.2 Day 2)
"""

from __future__ import annotations

import asyncio

import pytest

from agent_harness.error_handling.circuit_breaker import (
    CircuitOpenError,
    CircuitState,
    DefaultCircuitBreaker,
)

# === construction ============================================================


class TestConstruction:
    def test_default_thresholds(self) -> None:
        cb = DefaultCircuitBreaker()
        assert cb._threshold == 5
        assert cb._recovery_timeout_seconds == 60.0
        assert cb._half_open_max_calls == 1

    def test_invalid_threshold_raises(self) -> None:
        with pytest.raises(ValueError, match="threshold"):
            DefaultCircuitBreaker(threshold=0)

    def test_invalid_recovery_timeout_raises(self) -> None:
        with pytest.raises(ValueError, match="recovery_timeout"):
            DefaultCircuitBreaker(recovery_timeout_seconds=0)


# === closed → open transition ================================================


class TestClosedToOpen:
    @pytest.mark.asyncio
    async def test_initial_state_is_closed(self) -> None:
        cb = DefaultCircuitBreaker()
        assert cb.state_of("azure_openai") == CircuitState.CLOSED
        assert await cb.is_open("azure_openai") is False

    @pytest.mark.asyncio
    async def test_consecutive_failures_open_circuit(self) -> None:
        cb = DefaultCircuitBreaker(threshold=3)
        for _ in range(3):
            await cb.record(success=False, resource="azure_openai")
        assert cb.state_of("azure_openai") == CircuitState.OPEN
        assert await cb.is_open("azure_openai") is True

    @pytest.mark.asyncio
    async def test_success_resets_failure_counter(self) -> None:
        cb = DefaultCircuitBreaker(threshold=3)
        for _ in range(2):
            await cb.record(success=False, resource="azure_openai")
        await cb.record(success=True, resource="azure_openai")
        assert cb.consecutive_failures_of("azure_openai") == 0
        assert cb.state_of("azure_openai") == CircuitState.CLOSED


# === open → half_open → closed transition ====================================


class TestRecoveryFlow:
    @pytest.mark.asyncio
    async def test_open_to_half_open_after_recovery_timeout(self) -> None:
        # very short timeout for test speed
        cb = DefaultCircuitBreaker(threshold=2, recovery_timeout_seconds=0.05)
        for _ in range(2):
            await cb.record(success=False, resource="r")
        assert cb.state_of("r") == CircuitState.OPEN

        await asyncio.sleep(0.06)
        # is_open returns False (this caller is the trial), state transitions
        assert await cb.is_open("r") is False
        assert cb.state_of("r") == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_success_closes_circuit(self) -> None:
        cb = DefaultCircuitBreaker(threshold=2, recovery_timeout_seconds=0.05)
        for _ in range(2):
            await cb.record(success=False, resource="r")
        await asyncio.sleep(0.06)
        await cb.is_open("r")  # transitions to HALF_OPEN
        await cb.record(success=True, resource="r")
        assert cb.state_of("r") == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens_circuit(self) -> None:
        cb = DefaultCircuitBreaker(threshold=2, recovery_timeout_seconds=0.05)
        for _ in range(2):
            await cb.record(success=False, resource="r")
        await asyncio.sleep(0.06)
        await cb.is_open("r")  # transitions to HALF_OPEN
        await cb.record(success=False, resource="r")
        assert cb.state_of("r") == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_half_open_blocks_concurrent_trial(self) -> None:
        cb = DefaultCircuitBreaker(
            threshold=2, recovery_timeout_seconds=0.05, half_open_max_calls=1
        )
        for _ in range(2):
            await cb.record(success=False, resource="r")
        await asyncio.sleep(0.06)
        # First caller becomes the trial — gets through
        first_blocked = await cb.is_open("r")
        # Second caller: should be blocked since trial in flight
        second_blocked = await cb.is_open("r")
        assert first_blocked is False
        assert second_blocked is True


# === per-resource isolation ==================================================


class TestPerResourceIsolation:
    @pytest.mark.asyncio
    async def test_two_providers_independent_state(self) -> None:
        cb = DefaultCircuitBreaker(threshold=2)
        for _ in range(2):
            await cb.record(success=False, resource="azure_openai")
        # azure circuit open; anthropic still closed
        assert cb.state_of("azure_openai") == CircuitState.OPEN
        assert cb.state_of("anthropic") == CircuitState.CLOSED
        assert await cb.is_open("azure_openai") is True
        assert await cb.is_open("anthropic") is False


# === concurrency ============================================================


class TestConcurrency:
    @pytest.mark.asyncio
    async def test_parallel_record_under_lock(self) -> None:
        cb = DefaultCircuitBreaker(threshold=10)
        await asyncio.gather(*[cb.record(success=False, resource="r") for _ in range(10)])
        # exactly 10 failures recorded; circuit OPEN
        assert cb.consecutive_failures_of("r") == 10
        assert cb.state_of("r") == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_parallel_is_open_under_lock(self) -> None:
        cb = DefaultCircuitBreaker(threshold=2)
        for _ in range(2):
            await cb.record(success=False, resource="r")
        # all parallel callers see OPEN
        results = await asyncio.gather(*[cb.is_open("r") for _ in range(20)])
        assert all(r is True for r in results)


# === smoke ==================================================================


def test_circuit_open_error_is_exception() -> None:
    """CircuitOpenError is an Exception subclass."""
    assert issubclass(CircuitOpenError, Exception)


def test_state_enum_values() -> None:
    assert CircuitState.CLOSED.value == "closed"
    assert CircuitState.OPEN.value == "open"
    assert CircuitState.HALF_OPEN.value == "half_open"

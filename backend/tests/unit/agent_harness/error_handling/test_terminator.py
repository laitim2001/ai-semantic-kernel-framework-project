"""
File: backend/tests/unit/agent_harness/error_handling/test_terminator.py
Purpose: Unit tests for DefaultErrorTerminator (Cat 8 US-5).
Category: Tests / 範疇 8
Scope: Phase 53.2 / Sprint 53.2

Created: 2026-05-03 (Sprint 53.2 Day 3)
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from agent_harness._contracts.errors import ErrorContext
from agent_harness.error_handling import (
    DefaultCircuitBreaker,
    DefaultErrorTerminator,
    ErrorClass,
    InMemoryBudgetStore,
    TenantErrorBudget,
    TerminationReason,
)

# === sync ABC compatibility ================================================


class TestSyncShouldTerminate:
    def test_budget_exhausted_terminates(self) -> None:
        t = DefaultErrorTerminator()
        assert (
            t.should_terminate(consecutive_errors=0, budget_exhausted=True, circuit_open=False)
            is True
        )

    def test_circuit_open_terminates(self) -> None:
        t = DefaultErrorTerminator()
        assert (
            t.should_terminate(consecutive_errors=0, budget_exhausted=False, circuit_open=True)
            is True
        )

    def test_below_max_retries_does_not_terminate(self) -> None:
        t = DefaultErrorTerminator(max_retry_attempts=5)
        assert (
            t.should_terminate(consecutive_errors=3, budget_exhausted=False, circuit_open=False)
            is False
        )

    def test_at_max_retries_terminates(self) -> None:
        t = DefaultErrorTerminator(max_retry_attempts=5)
        assert (
            t.should_terminate(consecutive_errors=5, budget_exhausted=False, circuit_open=False)
            is True
        )


# === async evaluate (production path) =====================================


class TestEvaluateBudget:
    @pytest.mark.asyncio
    async def test_budget_exceeded_returns_budget_exceeded(self) -> None:
        store = InMemoryBudgetStore()
        budget = TenantErrorBudget(store, max_per_day=1, max_per_month=100)
        terminator = DefaultErrorTerminator(error_budget=budget)
        tid = uuid4()

        # exhaust budget by recording 2 errors (cap=1)
        for _ in range(2):
            await budget.record(tid, ErrorClass.TRANSIENT)

        decision = await terminator.evaluate(
            error=ConnectionError("net"),
            error_class=ErrorClass.TRANSIENT,
            context=ErrorContext(source_category="tools"),
            tenant_id=tid,
        )
        assert decision.terminate is True
        assert decision.reason == TerminationReason.BUDGET_EXCEEDED
        assert decision.detail is not None
        assert "daily" in decision.detail


class TestEvaluateCircuit:
    @pytest.mark.asyncio
    async def test_circuit_open_returns_circuit_open(self) -> None:
        cb = DefaultCircuitBreaker(threshold=2)
        terminator = DefaultErrorTerminator(circuit_breaker=cb)
        # trip the circuit for 'azure_openai'
        for _ in range(2):
            await cb.record(success=False, resource="azure_openai")

        decision = await terminator.evaluate(
            error=ConnectionError("net"),
            error_class=ErrorClass.TRANSIENT,
            context=ErrorContext(source_category="adapters", provider="azure_openai"),
            tenant_id=uuid4(),
        )
        assert decision.terminate is True
        assert decision.reason == TerminationReason.CIRCUIT_OPEN
        assert decision.detail is not None
        assert "azure_openai" in decision.detail

    @pytest.mark.asyncio
    async def test_circuit_closed_does_not_terminate_for_circuit_reason(self) -> None:
        cb = DefaultCircuitBreaker(threshold=10)
        terminator = DefaultErrorTerminator(circuit_breaker=cb)
        decision = await terminator.evaluate(
            error=ConnectionError("net"),
            error_class=ErrorClass.TRANSIENT,
            context=ErrorContext(source_category="adapters", provider="azure_openai"),
            tenant_id=uuid4(),
        )
        # Closed circuit + within retry cap → do not terminate
        assert decision.terminate is False


class TestEvaluateFatal:
    @pytest.mark.asyncio
    async def test_fatal_class_returns_fatal_exception(self) -> None:
        terminator = DefaultErrorTerminator()
        decision = await terminator.evaluate(
            error=RuntimeError("boom"),
            error_class=ErrorClass.FATAL,
            context=ErrorContext(source_category="tools"),
            tenant_id=uuid4(),
        )
        assert decision.terminate is True
        assert decision.reason == TerminationReason.FATAL_EXCEPTION
        assert decision.detail is not None
        assert "RuntimeError" in decision.detail


class TestEvaluateMaxRetries:
    @pytest.mark.asyncio
    async def test_attempt_at_or_above_cap_returns_max_retries(self) -> None:
        terminator = DefaultErrorTerminator(max_retry_attempts=3)
        decision = await terminator.evaluate(
            error=ConnectionError("net"),
            error_class=ErrorClass.TRANSIENT,
            context=ErrorContext(source_category="tools", attempt_num=3),
            tenant_id=uuid4(),
        )
        assert decision.terminate is True
        assert decision.reason == TerminationReason.MAX_RETRIES_EXHAUSTED


class TestEvaluateNonTermination:
    @pytest.mark.asyncio
    async def test_transient_within_caps_does_not_terminate(self) -> None:
        terminator = DefaultErrorTerminator(max_retry_attempts=5)
        decision = await terminator.evaluate(
            error=ConnectionError("net"),
            error_class=ErrorClass.TRANSIENT,
            context=ErrorContext(source_category="tools", attempt_num=1),
            tenant_id=uuid4(),
        )
        assert decision.terminate is False
        assert decision.reason is None

    @pytest.mark.asyncio
    async def test_llm_recoverable_does_not_terminate(self) -> None:
        terminator = DefaultErrorTerminator()
        decision = await terminator.evaluate(
            error=Exception("tool fail"),
            error_class=ErrorClass.LLM_RECOVERABLE,
            context=ErrorContext(source_category="tools", attempt_num=1),
            tenant_id=uuid4(),
        )
        assert decision.terminate is False


# === enum / boundary smoke =================================================


def test_termination_reason_values() -> None:
    assert TerminationReason.BUDGET_EXCEEDED.value == "budget_exceeded"
    assert TerminationReason.CIRCUIT_OPEN.value == "circuit_open"
    assert TerminationReason.FATAL_EXCEPTION.value == "fatal_exception"
    assert TerminationReason.MAX_RETRIES_EXHAUSTED.value == "max_retries_exhausted"


def test_no_tripwire_in_termination_reasons() -> None:
    """Cat 8 vs Cat 9 boundary守門 (per 17.md §6)."""
    for r in TerminationReason:
        assert "tripwire" not in r.value.lower()

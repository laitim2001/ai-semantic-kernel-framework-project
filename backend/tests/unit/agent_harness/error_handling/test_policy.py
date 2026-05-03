"""
File: backend/tests/unit/agent_harness/error_handling/test_policy.py
Purpose: Unit tests for DefaultErrorPolicy (Cat 8 US-1).
Category: Tests / 範疇 8
Scope: Phase 53.2 / Sprint 53.2

Created: 2026-05-03 (Sprint 53.2 Day 1)
"""

from __future__ import annotations

import asyncio

from agent_harness._contracts.errors import (
    AuthenticationError,
    MissingDataError,
    ToolExecutionError,
)
from agent_harness.error_handling import DefaultErrorPolicy, ErrorClass

# === classify ===============================================================


class TestClassify:
    def test_classify_connection_error_is_transient(self) -> None:
        p = DefaultErrorPolicy()
        assert p.classify(ConnectionError("net down")) == ErrorClass.TRANSIENT

    def test_classify_os_error_is_transient(self) -> None:
        p = DefaultErrorPolicy()
        assert p.classify(OSError("disk")) == ErrorClass.TRANSIENT

    def test_classify_asyncio_timeout_is_transient(self) -> None:
        p = DefaultErrorPolicy()
        assert p.classify(asyncio.TimeoutError()) == ErrorClass.TRANSIENT

    def test_classify_tool_execution_error_is_llm_recoverable(self) -> None:
        p = DefaultErrorPolicy()
        assert p.classify(ToolExecutionError("bad shape")) == ErrorClass.LLM_RECOVERABLE

    def test_classify_authentication_error_is_hitl_recoverable(self) -> None:
        p = DefaultErrorPolicy()
        assert p.classify(AuthenticationError("401")) == ErrorClass.HITL_RECOVERABLE

    def test_classify_missing_data_error_is_hitl_recoverable(self) -> None:
        p = DefaultErrorPolicy()
        assert p.classify(MissingDataError("missing field")) == ErrorClass.HITL_RECOVERABLE

    def test_classify_unregistered_falls_back_to_fatal(self) -> None:
        p = DefaultErrorPolicy()

        class WeirdError(Exception):
            pass

        assert p.classify(WeirdError("?")) == ErrorClass.FATAL

    def test_classify_walks_mro_for_subclass(self) -> None:
        p = DefaultErrorPolicy()

        class SalesforceConnectionError(ToolExecutionError):
            pass

        # subclass inherits parent's category via MRO walk
        assert p.classify(SalesforceConnectionError("sf 503")) == ErrorClass.LLM_RECOVERABLE

    def test_register_overrides_default(self) -> None:
        p = DefaultErrorPolicy()

        # Custom adapter exception
        class ProviderRateLimit(Exception):
            pass

        p.register(ProviderRateLimit, ErrorClass.TRANSIENT)
        assert p.classify(ProviderRateLimit("429")) == ErrorClass.TRANSIENT

    def test_register_idempotent(self) -> None:
        p = DefaultErrorPolicy()

        class Foo(Exception):
            pass

        p.register(Foo, ErrorClass.TRANSIENT)
        p.register(Foo, ErrorClass.LLM_RECOVERABLE)  # second wins
        assert p.classify(Foo()) == ErrorClass.LLM_RECOVERABLE


# === should_retry ===========================================================


class TestShouldRetry:
    def test_transient_retries_within_cap(self) -> None:
        p = DefaultErrorPolicy(max_attempts=3)
        err = ConnectionError()
        assert p.should_retry(err, attempt=1) is True
        assert p.should_retry(err, attempt=2) is True
        assert p.should_retry(err, attempt=3) is False

    def test_llm_recoverable_retries_within_cap(self) -> None:
        p = DefaultErrorPolicy(max_attempts=2)
        err = ToolExecutionError("...")
        assert p.should_retry(err, attempt=1) is True
        assert p.should_retry(err, attempt=2) is False

    def test_hitl_recoverable_does_not_retry(self) -> None:
        p = DefaultErrorPolicy()
        assert p.should_retry(AuthenticationError("..."), attempt=1) is False
        assert p.should_retry(MissingDataError("..."), attempt=1) is False

    def test_fatal_does_not_retry(self) -> None:
        p = DefaultErrorPolicy()

        class Bug(Exception):
            pass

        assert p.should_retry(Bug(), attempt=1) is False


# === backoff_seconds ========================================================


class TestBackoffSeconds:
    def test_zero_or_negative_attempt_returns_zero(self) -> None:
        p = DefaultErrorPolicy(jitter=False)
        assert p.backoff_seconds(0) == 0.0
        assert p.backoff_seconds(-1) == 0.0

    def test_exponential_growth_no_jitter(self) -> None:
        p = DefaultErrorPolicy(backoff_base=1.0, backoff_max=100.0, jitter=False)
        assert p.backoff_seconds(1) == 1.0  # 1.0 * 2^0
        assert p.backoff_seconds(2) == 2.0  # 1.0 * 2^1
        assert p.backoff_seconds(3) == 4.0  # 1.0 * 2^2
        assert p.backoff_seconds(4) == 8.0  # 1.0 * 2^3

    def test_capped_at_max(self) -> None:
        p = DefaultErrorPolicy(backoff_base=1.0, backoff_max=5.0, jitter=False)
        assert p.backoff_seconds(10) == 5.0  # capped

    def test_jitter_within_10_percent(self) -> None:
        p = DefaultErrorPolicy(backoff_base=10.0, backoff_max=100.0, jitter=True)
        # 100 trials all within ±10% of 10.0 (attempt=1 → base 10.0)
        for _ in range(100):
            v = p.backoff_seconds(1)
            assert 9.0 <= v <= 11.0


# === module-level smoke ====================================================


def test_imports_from_package_init() -> None:
    """DefaultErrorPolicy importable from package root."""
    from agent_harness.error_handling import DefaultErrorPolicy as Imp

    assert Imp is DefaultErrorPolicy

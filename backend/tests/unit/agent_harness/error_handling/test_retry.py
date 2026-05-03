"""
File: backend/tests/unit/agent_harness/error_handling/test_retry.py
Purpose: Unit tests for RetryPolicyMatrix + compute_backoff (Cat 8 US-2).
Category: Tests / 範疇 8
Scope: Phase 53.2 / Sprint 53.2

Created: 2026-05-03 (Sprint 53.2 Day 1)
"""

from __future__ import annotations

from pathlib import Path

from agent_harness.error_handling._abc import ErrorClass
from agent_harness.error_handling.retry import (
    RetryConfig,
    RetryPolicyMatrix,
    compute_backoff,
)

# === defaults match Cat 8 spec =============================================


class TestDefaults:
    def test_default_transient(self) -> None:
        m = RetryPolicyMatrix()
        c = m.get_policy(None, ErrorClass.TRANSIENT)
        assert c.max_attempts == 3
        assert c.backoff_base == 1.0
        assert c.backoff_max == 30.0
        assert c.jitter is True

    def test_default_llm_recoverable(self) -> None:
        m = RetryPolicyMatrix()
        c = m.get_policy(None, ErrorClass.LLM_RECOVERABLE)
        assert c.max_attempts == 2
        assert c.jitter is False

    def test_default_hitl_recoverable_no_retry(self) -> None:
        m = RetryPolicyMatrix()
        c = m.get_policy(None, ErrorClass.HITL_RECOVERABLE)
        assert c.max_attempts == 0

    def test_default_fatal_no_retry(self) -> None:
        m = RetryPolicyMatrix()
        c = m.get_policy(None, ErrorClass.FATAL)
        assert c.max_attempts == 0


# === resolution order ======================================================


class TestResolutionOrder:
    def test_per_tool_overrides_default(self) -> None:
        custom = RetryConfig(max_attempts=99, backoff_max=600.0)
        m = RetryPolicyMatrix(matrix={("salesforce_query", ErrorClass.TRANSIENT): custom})
        c = m.get_policy("salesforce_query", ErrorClass.TRANSIENT)
        assert c.max_attempts == 99
        assert c.backoff_max == 600.0

    def test_global_override_falls_through_when_no_per_tool(self) -> None:
        custom = RetryConfig(max_attempts=10)
        m = RetryPolicyMatrix(matrix={(None, ErrorClass.TRANSIENT): custom})
        # tool_name miss → falls to (None, TRANSIENT) global override
        assert m.get_policy("some_tool", ErrorClass.TRANSIENT).max_attempts == 10

    def test_falls_through_to_spec_default(self) -> None:
        m = RetryPolicyMatrix()
        # No matrix entries → falls to baked-in _DEFAULTS
        assert m.get_policy("unknown_tool", ErrorClass.TRANSIENT).max_attempts == 3


# === from_yaml =============================================================


class TestFromYaml:
    def test_loads_repo_config(self) -> None:
        # parents[4] = backend/ (file at backend/tests/unit/agent_harness/error_handling/)
        path = Path(__file__).resolve().parents[4] / "config" / "retry_policies.yaml"
        assert path.is_file(), f"missing: {path}"

        m = RetryPolicyMatrix.from_yaml(path)
        # defaults loaded
        assert m.get_policy(None, ErrorClass.TRANSIENT).max_attempts == 3
        # salesforce_query per-tool override loaded
        sf = m.get_policy("salesforce_query", ErrorClass.TRANSIENT)
        assert sf.max_attempts == 5
        assert sf.backoff_max == 60.0

    def test_loads_minimal_yaml(self, tmp_path: Path) -> None:
        p = tmp_path / "tiny.yaml"
        p.write_text(
            "defaults:\n" "  transient: {max_attempts: 7}\n",
            encoding="utf-8",
        )
        m = RetryPolicyMatrix.from_yaml(p)
        assert m.get_policy(None, ErrorClass.TRANSIENT).max_attempts == 7

    def test_handles_empty_yaml(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.yaml"
        p.write_text("", encoding="utf-8")
        m = RetryPolicyMatrix.from_yaml(p)
        # falls through to spec defaults
        assert m.get_policy(None, ErrorClass.TRANSIENT).max_attempts == 3


# === compute_backoff =======================================================


class TestComputeBackoff:
    def test_zero_or_negative_attempt_returns_zero(self) -> None:
        c = RetryConfig(max_attempts=3, backoff_base=1.0, backoff_max=30.0, jitter=False)
        assert compute_backoff(c, 0) == 0.0
        assert compute_backoff(c, -1) == 0.0

    def test_zero_max_attempts_returns_zero(self) -> None:
        c = RetryConfig(max_attempts=0)
        assert compute_backoff(c, 1) == 0.0

    def test_exponential_growth_no_jitter(self) -> None:
        c = RetryConfig(max_attempts=5, backoff_base=1.0, backoff_max=100.0, jitter=False)
        assert compute_backoff(c, 1) == 1.0
        assert compute_backoff(c, 2) == 2.0
        assert compute_backoff(c, 3) == 4.0
        assert compute_backoff(c, 4) == 8.0

    def test_capped_at_max(self) -> None:
        c = RetryConfig(max_attempts=10, backoff_base=1.0, backoff_max=5.0, jitter=False)
        assert compute_backoff(c, 10) == 5.0

    def test_jitter_within_10_percent(self) -> None:
        c = RetryConfig(max_attempts=3, backoff_base=10.0, backoff_max=100.0, jitter=True)
        for _ in range(100):
            v = compute_backoff(c, 1)
            assert 9.0 <= v <= 11.0

"""
File: backend/tests/unit/agent_harness/verification/test_rules_based.py
Purpose: Unit tests for RulesBasedVerifier + 3 Rule types (Regex / Schema / Format).
Category: Tests / Unit / 範疇 10
Scope: Sprint 54.1 US-1

Description:
    Covers:
    - RegexRule: match / no-match cases
    - SchemaRule: valid JSON / missing required field
    - FormatRule: callable pass / fail
    - Verifier behavior: fail-fast (returns first failure)
    - Performance SLO: p95 < 200ms over 10 iterations

    RulesBasedVerifier doesn't dereference `state` so tests cast None to
    LoopState. The Verifier ABC requires the kwarg for cross-verifier
    consistency (LLMJudgeVerifier in US-2 will use state).

Created: 2026-05-04 (Sprint 54.1 Day 1)

Related:
    - backend/src/agent_harness/verification/rules_based.py
    - backend/src/agent_harness/verification/types.py
"""

from __future__ import annotations

import time
from typing import cast

import pytest

from agent_harness._contracts import LoopState
from agent_harness.verification import (
    FormatRule,
    RegexRule,
    RulesBasedVerifier,
    SchemaRule,
)


def _state() -> LoopState:
    """RulesBasedVerifier doesn't read state; cast None to satisfy ABC type."""
    return cast(LoopState, None)


@pytest.mark.asyncio
async def test_regex_rule_match_pass() -> None:
    rule = RegexRule(pattern=r"^[A-Z]", expected_match=True)
    verifier = RulesBasedVerifier(rules=[rule])
    result = await verifier.verify(output="Hello world", state=_state())
    assert result.passed is True
    assert result.verifier_type == "rules_based"


@pytest.mark.asyncio
async def test_regex_rule_no_match_fail() -> None:
    rule = RegexRule(pattern=r"^[A-Z]", expected_match=True, suggestion="Capitalize first letter")
    verifier = RulesBasedVerifier(rules=[rule])
    result = await verifier.verify(output="hello world", state=_state())
    assert result.passed is False
    assert result.reason is not None
    assert "did not match" in result.reason
    assert result.suggested_correction == "Capitalize first letter"


@pytest.mark.asyncio
async def test_schema_rule_valid_json_pass() -> None:
    schema = {
        "type": "object",
        "required": ["name"],
        "properties": {"name": {"type": "string"}},
    }
    rule = SchemaRule(schema=schema)
    verifier = RulesBasedVerifier(rules=[rule])
    result = await verifier.verify(output='{"name": "Alice"}', state=_state())
    assert result.passed is True


@pytest.mark.asyncio
async def test_schema_rule_missing_field_fail() -> None:
    schema = {
        "type": "object",
        "required": ["name"],
        "properties": {"name": {"type": "string"}},
    }
    rule = SchemaRule(schema=schema, suggestion="Add 'name' field to JSON output")
    verifier = RulesBasedVerifier(rules=[rule])
    result = await verifier.verify(output='{"age": 30}', state=_state())
    assert result.passed is False
    assert result.reason is not None
    assert "schema_rule" in result.reason
    assert result.suggested_correction == "Add 'name' field to JSON output"


@pytest.mark.asyncio
async def test_format_rule_callable_pass() -> None:
    rule = FormatRule(check_fn=lambda s: (s.startswith("OK"), None))
    verifier = RulesBasedVerifier(rules=[rule])
    result = await verifier.verify(output="OK: done", state=_state())
    assert result.passed is True


@pytest.mark.asyncio
async def test_format_rule_callable_fail() -> None:
    rule = FormatRule(check_fn=lambda s: (False, "bad format"), suggestion="Use markdown bullets")
    verifier = RulesBasedVerifier(rules=[rule])
    result = await verifier.verify(output="anything", state=_state())
    assert result.passed is False
    assert result.reason == "bad format"
    assert result.suggested_correction == "Use markdown bullets"


@pytest.mark.asyncio
async def test_verifier_runs_all_rules_returns_first_failure() -> None:
    """Fail-fast: the first failing rule short-circuits; later rules don't run."""
    calls: list[str] = []

    def make_check_fn(name: str, passed: bool) -> "object":
        def fn(s: str) -> tuple[bool, str | None]:
            calls.append(name)
            return (passed, None if passed else f"{name} failed")

        return fn

    rule_a = FormatRule(check_fn=make_check_fn("a", True), name="rule_a")  # type: ignore[arg-type]
    rule_b = FormatRule(check_fn=make_check_fn("b", False), name="rule_b")  # type: ignore[arg-type]
    rule_c = FormatRule(check_fn=make_check_fn("c", True), name="rule_c")  # type: ignore[arg-type]

    verifier = RulesBasedVerifier(rules=[rule_a, rule_b, rule_c])
    result = await verifier.verify(output="x", state=_state())

    assert result.passed is False
    assert result.reason == "b failed"
    # rule_c must NOT have been called (fail-fast)
    assert calls == ["a", "b"]


@pytest.mark.asyncio
async def test_verifier_p95_under_200ms() -> None:
    """SLO from 01-eleven-categories-spec.md §範疇 10: rules-based p95 < 200ms."""
    rule = RegexRule(pattern=r"\d+", expected_match=True)
    verifier = RulesBasedVerifier(rules=[rule] * 5)  # 5 rules to be representative
    output = "x" * 1024 + "1234"  # 1KB output

    durations: list[float] = []
    for _ in range(10):
        t0 = time.perf_counter()
        await verifier.verify(output=output, state=_state())
        durations.append(time.perf_counter() - t0)

    durations.sort()
    # p95 of 10 = index 9 (highest); use index 8 (90th-95th band) for stability
    p95 = durations[-1]
    assert p95 < 0.200, f"p95 {p95 * 1000:.1f}ms exceeds 200ms SLO"

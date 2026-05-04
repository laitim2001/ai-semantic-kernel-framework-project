"""
File: backend/tests/unit/agent_harness/verification/test_verify_tool.py
Purpose: Unit tests for make_verify_tool factory (US-5).
Category: Tests / Unit / 範疇 10
Scope: Sprint 54.1 US-5

Description:
    Covers:
    - make_verify_tool returns (ToolSpec, handler) with correct metadata
    - Handler runs all registered verifiers and aggregates verdicts
    - Handler returns passed=False when ANY verifier fails

Created: 2026-05-04 (Sprint 54.1 Day 4)

Related:
    - backend/src/agent_harness/verification/tools.py
"""

from __future__ import annotations

import pytest

from agent_harness._contracts.tools import ConcurrencyPolicy, ToolHITLPolicy
from agent_harness.verification import (
    FormatRule,
    RegexRule,
    RulesBasedVerifier,
    VerifierRegistry,
    make_verify_tool,
)


def test_make_verify_tool_returns_correct_spec_metadata() -> None:
    registry = VerifierRegistry()
    spec, _handler = make_verify_tool(registry)

    assert spec.name == "verify"
    assert "verifier" in spec.description.lower()
    assert spec.input_schema["required"] == ["output"]
    assert "output" in spec.input_schema["properties"]
    assert spec.concurrency_policy == ConcurrencyPolicy.READ_ONLY_PARALLEL
    assert spec.hitl_policy == ToolHITLPolicy.AUTO
    assert spec.annotations.read_only is True
    assert "verification" in spec.tags
    assert "category_10" in spec.tags


@pytest.mark.asyncio
async def test_verify_tool_handler_returns_all_passed_when_no_verifiers() -> None:
    registry = VerifierRegistry()
    _spec, handler = make_verify_tool(registry)

    result = await handler({"output": "anything"})
    assert result["passed"] is True
    assert result["results"] == []


@pytest.mark.asyncio
async def test_verify_tool_handler_runs_all_verifiers_aggregates_results() -> None:
    registry = VerifierRegistry()
    # Two verifiers: one passes (matches \w+), one fails (requires capital start)
    registry.register(RulesBasedVerifier(rules=[RegexRule(pattern=r"\w+")], name="word_match"))
    registry.register(
        RulesBasedVerifier(
            rules=[RegexRule(pattern=r"^[A-Z]")],
            name="cap_start",
        )
    )

    _spec, handler = make_verify_tool(registry)
    result = await handler({"output": "lowercase output"})

    assert result["passed"] is False  # second verifier fails
    assert len(result["results"]) == 2
    assert result["results"][0]["verifier"] == "word_match"
    assert result["results"][0]["passed"] is True
    assert result["results"][1]["verifier"] == "cap_start"
    assert result["results"][1]["passed"] is False
    assert "did not match" in (result["results"][1]["reason"] or "")


@pytest.mark.asyncio
async def test_verify_tool_handler_passes_when_all_verifiers_pass() -> None:
    registry = VerifierRegistry()
    registry.register(RulesBasedVerifier(rules=[RegexRule(pattern=r".+")], name="any"))
    registry.register(
        RulesBasedVerifier(
            rules=[FormatRule(check_fn=lambda s: (len(s) > 0, None))],
            name="non_empty",
        )
    )

    _spec, handler = make_verify_tool(registry)
    result = await handler({"output": "Hello world"})

    assert result["passed"] is True
    assert all(r["passed"] for r in result["results"])

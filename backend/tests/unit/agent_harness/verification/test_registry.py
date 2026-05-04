"""
File: backend/tests/unit/agent_harness/verification/test_registry.py
Purpose: Unit tests for VerifierRegistry — register / get_all (insertion order) / clear.
Category: Tests / Unit / 範疇 10
Scope: Sprint 54.1 US-1

Description:
    Covers:
    - register() appends in insertion order
    - get_all() returns defensive copy in insertion order
    - clear() removes all entries

Created: 2026-05-04 (Sprint 54.1 Day 1)

Related:
    - backend/src/agent_harness/verification/registry.py
"""

from __future__ import annotations

from agent_harness._contracts import LoopState, TraceContext, VerificationResult
from agent_harness.verification import (
    RegexRule,
    RulesBasedVerifier,
    Verifier,
    VerifierRegistry,
)


class _StubVerifier(Verifier):
    """Lightweight Verifier subclass for registry-only tests."""

    def __init__(self, name: str) -> None:
        self.name = name

    async def verify(
        self,
        *,
        output: str,
        state: LoopState,
        trace_context: TraceContext | None = None,
    ) -> VerificationResult:
        return VerificationResult(passed=True, verifier_name=self.name, verifier_type="rules_based")


def test_register_verifier() -> None:
    registry = VerifierRegistry()
    assert len(registry) == 0
    v = RulesBasedVerifier(rules=[RegexRule(pattern=r".+")])
    registry.register(v)
    assert len(registry) == 1
    assert registry.get_all() == [v]


def test_get_all_returns_in_order() -> None:
    registry = VerifierRegistry()
    v1 = _StubVerifier(name="first")
    v2 = _StubVerifier(name="second")
    v3 = _StubVerifier(name="third")
    registry.register(v1)
    registry.register(v2)
    registry.register(v3)

    all_verifiers = registry.get_all()
    assert len(all_verifiers) == 3
    assert all_verifiers[0] is v1
    assert all_verifiers[1] is v2
    assert all_verifiers[2] is v3

    # get_all() returns a defensive copy — mutating result doesn't affect registry
    all_verifiers.append(_StubVerifier(name="extra"))
    assert len(registry) == 3


def test_clear() -> None:
    registry = VerifierRegistry()
    registry.register(_StubVerifier(name="a"))
    registry.register(_StubVerifier(name="b"))
    assert len(registry) == 2
    registry.clear()
    assert len(registry) == 0
    assert registry.get_all() == []

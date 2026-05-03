"""
File: backend/tests/unit/agent_harness/guardrails/test_engine.py
Purpose: Unit tests for GuardrailEngine (Cat 9 US-1).
Category: Tests / 範疇 9
Scope: Phase 53.3 / Sprint 53.3 Day 1

Created: 2026-05-03 (Sprint 53.3 Day 1)
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from agent_harness.guardrails import (
    Guardrail,
    GuardrailAction,
    GuardrailResult,
    GuardrailType,
)
from agent_harness.guardrails.engine import GuardrailEngine

# === Test fixtures: tiny mock guardrails ====================================


class _PassGuardrail(Guardrail):
    """Always PASS — confirms chain falls through."""

    def __init__(self, gtype: GuardrailType, name: str = "pass") -> None:
        self.guardrail_type = gtype
        self.name = name
        self.calls: list[Any] = []

    async def check(self, *, content: Any, trace_context: Any = None) -> GuardrailResult:
        self.calls.append(content)
        return GuardrailResult(action=GuardrailAction.PASS)


class _BlockGuardrail(Guardrail):
    """Always BLOCK — confirms fail-fast short-circuits."""

    def __init__(self, gtype: GuardrailType, reason: str = "blocked") -> None:
        self.guardrail_type = gtype
        self.reason = reason
        self.calls: list[Any] = []

    async def check(self, *, content: Any, trace_context: Any = None) -> GuardrailResult:
        self.calls.append(content)
        return GuardrailResult(
            action=GuardrailAction.BLOCK,
            reason=self.reason,
            risk_level="HIGH",
        )


class _SanitizeGuardrail(Guardrail):
    """Always SANITIZE — confirms non-PASS variants short-circuit."""

    def __init__(self, gtype: GuardrailType) -> None:
        self.guardrail_type = gtype

    async def check(self, *, content: Any, trace_context: Any = None) -> GuardrailResult:
        return GuardrailResult(
            action=GuardrailAction.SANITIZE,
            sanitized_content=f"[redacted from: {content}]",
            risk_level="MEDIUM",
        )


# === Empty chain tests =====================================================


@pytest.mark.asyncio
async def test_empty_input_chain_returns_pass() -> None:
    engine = GuardrailEngine()
    result = await engine.check_input("hello")
    assert result.action == GuardrailAction.PASS


@pytest.mark.asyncio
async def test_empty_output_chain_returns_pass() -> None:
    engine = GuardrailEngine()
    result = await engine.check_output("response")
    assert result.action == GuardrailAction.PASS


@pytest.mark.asyncio
async def test_empty_tool_chain_returns_pass() -> None:
    engine = GuardrailEngine()
    result = await engine.check_tool_call({"name": "search"})
    assert result.action == GuardrailAction.PASS


# === Registration + priority order =========================================


@pytest.mark.asyncio
async def test_priority_lower_runs_first() -> None:
    """priority 10 runs before priority 20 (ascending = highest first)."""
    engine = GuardrailEngine()
    first = _PassGuardrail(GuardrailType.INPUT, name="first")
    second = _PassGuardrail(GuardrailType.INPUT, name="second")

    # Register out-of-order; engine sorts internally.
    engine.register(second, priority=20)
    engine.register(first, priority=10)

    await engine.check_input("hi")
    # Both ran (since both PASS), but verify chain is sorted.
    chain = engine._registered_for(GuardrailType.INPUT)  # type: ignore[reportPrivateUsage]
    assert chain == [first, second]


@pytest.mark.asyncio
async def test_default_priority_is_100() -> None:
    """Plan §US-1: register(g, priority=100) is the default."""
    engine = GuardrailEngine()
    g = _PassGuardrail(GuardrailType.INPUT)
    engine.register(g)  # use default
    high = _PassGuardrail(GuardrailType.INPUT)
    engine.register(high, priority=10)
    chain = engine._registered_for(GuardrailType.INPUT)  # type: ignore[reportPrivateUsage]
    # priority 10 first; default 100 second
    assert chain == [high, g]


# === Fail-fast short-circuit ===============================================


@pytest.mark.asyncio
async def test_block_short_circuits_chain() -> None:
    """First non-PASS result returns; later guardrails do NOT run."""
    engine = GuardrailEngine()
    blocker = _BlockGuardrail(GuardrailType.INPUT)
    after = _PassGuardrail(GuardrailType.INPUT)
    engine.register(blocker, priority=10)
    engine.register(after, priority=20)

    result = await engine.check_input("danger")
    assert result.action == GuardrailAction.BLOCK
    assert result.reason == "blocked"
    # Confirm `after` never ran
    assert after.calls == []
    assert blocker.calls == ["danger"]


@pytest.mark.asyncio
async def test_sanitize_also_short_circuits() -> None:
    """Any non-PASS action stops the chain — not just BLOCK."""
    engine = GuardrailEngine()
    sanitizer = _SanitizeGuardrail(GuardrailType.OUTPUT)
    after = _PassGuardrail(GuardrailType.OUTPUT)
    engine.register(sanitizer, priority=10)
    engine.register(after, priority=20)

    result = await engine.check_output("toxic content")
    assert result.action == GuardrailAction.SANITIZE
    assert result.sanitized_content == "[redacted from: toxic content]"
    assert after.calls == []


# === Type isolation ========================================================


@pytest.mark.asyncio
async def test_type_chains_isolated() -> None:
    """Registering an INPUT guardrail does not affect OUTPUT or TOOL."""
    engine = GuardrailEngine()
    input_blocker = _BlockGuardrail(GuardrailType.INPUT)
    engine.register(input_blocker, priority=10)

    # OUTPUT + TOOL chains untouched → still pass.
    assert (await engine.check_output("anything")).action == GuardrailAction.PASS
    assert (await engine.check_tool_call({})).action == GuardrailAction.PASS
    # INPUT blocks
    assert (await engine.check_input("x")).action == GuardrailAction.BLOCK


# === batch_check_tool_calls (parallel fan-out) ============================


@pytest.mark.asyncio
async def test_batch_empty_returns_empty() -> None:
    engine = GuardrailEngine()
    assert await engine.batch_check_tool_calls([]) == []


@pytest.mark.asyncio
async def test_batch_runs_parallel_for_many_calls() -> None:
    """N tool_calls fan out via asyncio.gather; total time ~= max single,
    not sum (verifies the gather is in fact parallel).
    """

    class _SlowPass(Guardrail):
        guardrail_type = GuardrailType.TOOL

        async def check(self, *, content: Any, trace_context: Any = None) -> GuardrailResult:
            await asyncio.sleep(0.05)  # 50ms each
            return GuardrailResult(action=GuardrailAction.PASS)

    engine = GuardrailEngine()
    engine.register(_SlowPass(), priority=10)

    import time

    t0 = time.monotonic()
    results = await engine.batch_check_tool_calls([{"i": i} for i in range(5)])
    elapsed = time.monotonic() - t0

    assert len(results) == 5
    assert all(r.action == GuardrailAction.PASS for r in results)
    # Sequential would be ~250ms; parallel should be ~50-100ms.
    assert elapsed < 0.20, f"batch took {elapsed:.3f}s — looks sequential"


@pytest.mark.asyncio
async def test_batch_propagates_block_per_call() -> None:
    """Each call's chain is independent; one BLOCK doesn't shortcut others."""

    class _PerCallBlock(Guardrail):
        """BLOCK only when content has 'bad' key."""

        guardrail_type = GuardrailType.TOOL

        async def check(self, *, content: Any, trace_context: Any = None) -> GuardrailResult:
            if isinstance(content, dict) and content.get("bad"):
                return GuardrailResult(action=GuardrailAction.BLOCK, reason="bad flag")
            return GuardrailResult(action=GuardrailAction.PASS)

    engine = GuardrailEngine()
    engine.register(_PerCallBlock(), priority=10)

    contents = [
        {"name": "tool_a"},
        {"name": "tool_b", "bad": True},
        {"name": "tool_c"},
    ]
    results = await engine.batch_check_tool_calls(contents)
    assert results[0].action == GuardrailAction.PASS
    assert results[1].action == GuardrailAction.BLOCK
    assert results[2].action == GuardrailAction.PASS


# === Registration of same guardrail across types ==========================


@pytest.mark.asyncio
async def test_guardrail_registered_in_its_declared_type_only() -> None:
    """A Guardrail's `guardrail_type` attribute determines which chain it
    joins — engine doesn't allow registering across types."""
    engine = GuardrailEngine()
    g = _BlockGuardrail(GuardrailType.INPUT, reason="input-only")
    engine.register(g, priority=10)

    # Confirms it's in INPUT chain
    assert g in engine._registered_for(GuardrailType.INPUT)  # type: ignore[reportPrivateUsage]
    # Not in OUTPUT or TOOL
    assert g not in engine._registered_for(GuardrailType.OUTPUT)  # type: ignore[reportPrivateUsage]
    assert g not in engine._registered_for(GuardrailType.TOOL)  # type: ignore[reportPrivateUsage]

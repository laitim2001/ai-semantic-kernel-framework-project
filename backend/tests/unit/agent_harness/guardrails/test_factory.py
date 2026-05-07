"""
File: backend/tests/unit/agent_harness/guardrails/test_factory.py
Purpose: Unit tests for build_default_guardrail_engine() (Sprint 57.2 closes AD-Cat9-1-WireDetectors).
Category: Tests
Created: 2026-05-07 (Sprint 57.2 Day 4)
"""

from __future__ import annotations

from agent_harness.guardrails import (
    GuardrailEngine,
    GuardrailType,
    JailbreakDetector,
    PIIDetector,
    SensitiveInfoDetector,
    ToxicityDetector,
    build_default_guardrail_engine,
)


def test_factory_returns_guardrail_engine() -> None:
    """Factory returns a GuardrailEngine instance ready for AgentLoop wiring."""
    engine = build_default_guardrail_engine()
    assert isinstance(engine, GuardrailEngine)


def test_factory_registers_input_chain_pii_then_jailbreak() -> None:
    """Input chain: PIIDetector (priority 10) before JailbreakDetector (20)."""
    engine = build_default_guardrail_engine()
    input_chain = engine._registered_for(GuardrailType.INPUT)  # noqa: SLF001
    assert len(input_chain) == 2
    assert isinstance(input_chain[0], PIIDetector)
    assert isinstance(input_chain[1], JailbreakDetector)


def test_factory_registers_output_chain_toxicity_then_sensitive_info() -> None:
    """Output chain: ToxicityDetector (priority 10) before SensitiveInfo (20)."""
    engine = build_default_guardrail_engine()
    output_chain = engine._registered_for(GuardrailType.OUTPUT)  # noqa: SLF001
    assert len(output_chain) == 2
    assert isinstance(output_chain[0], ToxicityDetector)
    assert isinstance(output_chain[1], SensitiveInfoDetector)


def test_factory_does_not_register_tool_chain_by_default() -> None:
    """Tool chain stays empty — ToolGuardrail requires per-tenant CapabilityMatrix."""
    engine = build_default_guardrail_engine()
    tool_chain = engine._registered_for(GuardrailType.TOOL)  # noqa: SLF001
    assert tool_chain == []


def test_factory_each_call_returns_fresh_engine() -> None:
    """Two calls yield independent engines (no shared state)."""
    engine_a = build_default_guardrail_engine()
    engine_b = build_default_guardrail_engine()
    assert engine_a is not engine_b

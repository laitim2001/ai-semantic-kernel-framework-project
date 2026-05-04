"""
File: backend/tests/integration/agent_harness/guardrails/test_llm_judge_fallback.py
Purpose: Integration tests for LLMJudgeFallbackGuardrail — closes AD-Cat9-1.
Category: Tests / Integration / 範疇 9 ↔ 範疇 10 boundary
Scope: Sprint 54.1 US-2

Description:
    Verifies the wrapper pattern (Drift D8): a Cat 9 Guardrail wrapped by
    LLMJudgeFallbackGuardrail produces correct defense-in-depth behavior.

    3 integration cases:
    1. Wrapped detector BLOCK → propagates without calling judge (cost optimization)
    2. Wrapped detector PASS + judge BLOCK → returns BLOCK with judge reason
    3. Wrapped detector PASS + judge PASS → returns PASS (defense-in-depth confirmed clean)

    These cases exercise the registered-via-engine path so AD-Cat9-1 closure
    is verified end-to-end (not just unit-level).

Created: 2026-05-04 (Sprint 54.1 Day 2)

Related:
    - backend/src/agent_harness/verification/cat9_fallback.py
    - backend/src/agent_harness/guardrails/engine.py
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from adapters._testing.mock_clients import MockChatClient
from agent_harness._contracts import TraceContext
from agent_harness._contracts.chat import ChatResponse, StopReason
from agent_harness.guardrails._abc import (
    Guardrail,
    GuardrailAction,
    GuardrailResult,
    GuardrailType,
)
from agent_harness.guardrails.engine import GuardrailEngine
from agent_harness.verification import LLMJudgeFallbackGuardrail, LLMJudgeVerifier


class _AlwaysPassDetector(Guardrail):
    """Stub detector that always returns PASS. Counts calls for assertions."""

    guardrail_type = GuardrailType.OUTPUT

    def __init__(self) -> None:
        self.call_count = 0

    async def check(
        self,
        *,
        content: Any,
        trace_context: TraceContext | None = None,
    ) -> GuardrailResult:
        self.call_count += 1
        return GuardrailResult(action=GuardrailAction.PASS)


class _AlwaysBlockDetector(Guardrail):
    """Stub detector that always BLOCKs. Counts calls for assertions."""

    guardrail_type = GuardrailType.OUTPUT

    def __init__(self) -> None:
        self.call_count = 0

    async def check(
        self,
        *,
        content: Any,
        trace_context: TraceContext | None = None,
    ) -> GuardrailResult:
        self.call_count += 1
        return GuardrailResult(
            action=GuardrailAction.BLOCK,
            reason="deterministic_block",
            risk_level="HIGH",
        )


def _judge_response(*, passed: bool, reason: str = "") -> ChatResponse:
    return ChatResponse(
        model="mock-judge",
        content=json.dumps(
            {
                "passed": passed,
                "score": 0.9,
                "reason": reason,
                "suggested_correction": None,
            }
        ),
        stop_reason=StopReason.END_TURN,
    )


@pytest.mark.asyncio
async def test_wrapped_detector_blocks_propagates_without_calling_judge() -> None:
    """When wrapped detector BLOCKs, judge MUST NOT be called (cost optimization)."""
    detector = _AlwaysBlockDetector()
    chat = MockChatClient()  # no responses; if judge is called, will return mock empty
    judge = LLMJudgeVerifier(chat_client=chat, judge_template="Judge: {output}")
    wrapper = LLMJudgeFallbackGuardrail(wrapped=detector, judge=judge)

    engine = GuardrailEngine()
    engine.register(wrapper)

    result = await engine.check_output("any content")

    assert result.action == GuardrailAction.BLOCK
    assert result.reason == "deterministic_block"
    assert detector.call_count == 1
    # Critical: judge was NOT invoked (saves LLM cost on deterministic blocks)
    assert chat.chat_call_count == 0


@pytest.mark.asyncio
async def test_wrapped_detector_passes_judge_blocks_returns_block() -> None:
    """When wrapped detector PASSes but judge flags it, return BLOCK with judge reason."""
    detector = _AlwaysPassDetector()
    chat = MockChatClient(responses=[_judge_response(passed=False, reason="contains hidden PII")])
    judge = LLMJudgeVerifier(chat_client=chat, judge_template="pii_leak_check", name="pii_judge")
    wrapper = LLMJudgeFallbackGuardrail(wrapped=detector, judge=judge, name="pii_with_judge")

    engine = GuardrailEngine()
    engine.register(wrapper)

    result = await engine.check_output(
        "Looks clean to regex but contains an email john@example.com"
    )

    assert result.action == GuardrailAction.BLOCK
    assert result.reason is not None
    assert "pii_with_judge" in result.reason
    assert "contains hidden PII" in result.reason
    assert detector.call_count == 1
    assert chat.chat_call_count == 1  # judge WAS called (defense-in-depth path)


@pytest.mark.asyncio
async def test_wrapped_detector_passes_judge_passes_returns_pass() -> None:
    """Defense-in-depth confirmed clean: both wrapped detector AND judge approve."""
    detector = _AlwaysPassDetector()
    chat = MockChatClient(responses=[_judge_response(passed=True, reason="no PII detected")])
    judge = LLMJudgeVerifier(chat_client=chat, judge_template="pii_leak_check")
    wrapper = LLMJudgeFallbackGuardrail(wrapped=detector, judge=judge)

    engine = GuardrailEngine()
    engine.register(wrapper)

    result = await engine.check_output("Hello world, perfectly safe content.")

    assert result.action == GuardrailAction.PASS
    assert detector.call_count == 1
    assert chat.chat_call_count == 1  # judge confirmed clean


@pytest.mark.asyncio
async def test_judge_fallback_inherits_guardrail_type_from_wrapped() -> None:
    """Wrapper's guardrail_type must mirror wrapped's so engine routes correctly."""
    detector = _AlwaysPassDetector()
    chat = MockChatClient(responses=[_judge_response(passed=True)])
    judge = LLMJudgeVerifier(chat_client=chat, judge_template="Judge: {output}")
    wrapper = LLMJudgeFallbackGuardrail(wrapped=detector, judge=judge)

    assert wrapper.guardrail_type == GuardrailType.OUTPUT  # from _AlwaysPassDetector

    # Test that engine routes wrapper into OUTPUT chain (not INPUT/TOOL)
    engine = GuardrailEngine()
    engine.register(wrapper)
    output_chain = engine._registered_for(
        GuardrailType.OUTPUT
    )  # noqa: SLF001 — read-only inspection
    assert any(g is wrapper for g in output_chain)
    input_chain = engine._registered_for(GuardrailType.INPUT)  # noqa: SLF001
    assert wrapper not in input_chain

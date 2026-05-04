"""
File: backend/tests/integration/agent_harness/guardrails/test_sanitize_mutation.py
Purpose: Integration tests for LLMVerifyMutateGuardrail — closes AD-Cat9-2.
Category: Tests / Integration / 範疇 9 ↔ 範疇 10 boundary
Scope: Sprint 54.1 US-4

Description:
    Verifies the SANITIZE mutation pattern: a Cat 9 Guardrail wrapped by
    LLMVerifyMutateGuardrail produces SANITIZE action with judge-suggested
    sanitized_content (not just a stub action enum).

    4 cases:
    1. Wrapped BLOCK propagates (judge skipped)
    2. Wrapped PASS + judge approves → PASS (no mutation)
    3. Wrapped PASS + judge fails WITH correction → SANITIZE with mutation
    4. Wrapped PASS + judge fails WITHOUT correction → BLOCK (fail-safe)

Created: 2026-05-04 (Sprint 54.1 Day 4)

Related:
    - backend/src/agent_harness/verification/cat9_mutator.py
    - guardrails/_abc.py
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from adapters._testing.mock_clients import MockChatClient
from agent_harness._contracts import TraceContext
from agent_harness._contracts.chat import ChatResponse, StopReason
from agent_harness.guardrails import (
    Guardrail,
    GuardrailAction,
    GuardrailResult,
    GuardrailType,
)
from agent_harness.guardrails.engine import GuardrailEngine
from agent_harness.verification import LLMJudgeVerifier, LLMVerifyMutateGuardrail


class _PassDetector(Guardrail):
    guardrail_type = GuardrailType.OUTPUT

    async def check(
        self,
        *,
        content: Any,
        trace_context: TraceContext | None = None,
    ) -> GuardrailResult:
        return GuardrailResult(action=GuardrailAction.PASS)


class _BlockDetector(Guardrail):
    guardrail_type = GuardrailType.OUTPUT

    async def check(
        self,
        *,
        content: Any,
        trace_context: TraceContext | None = None,
    ) -> GuardrailResult:
        return GuardrailResult(
            action=GuardrailAction.BLOCK,
            reason="deterministic block",
            risk_level="HIGH",
        )


def _judge_resp(*, passed: bool, correction: str | None = None, reason: str = "") -> ChatResponse:
    return ChatResponse(
        model="mock",
        content=json.dumps(
            {
                "passed": passed,
                "score": 0.9,
                "reason": reason,
                "suggested_correction": correction,
            }
        ),
        stop_reason=StopReason.END_TURN,
    )


@pytest.mark.asyncio
async def test_wrapped_block_propagates_skipping_judge() -> None:
    chat = MockChatClient()  # no responses; judge call would fail if invoked
    judge = LLMJudgeVerifier(chat_client=chat, judge_template="Judge: {output}")
    wrapper = LLMVerifyMutateGuardrail(wrapped=_BlockDetector(), judge=judge)

    engine = GuardrailEngine()
    engine.register(wrapper)

    result = await engine.check_output("dirty content")
    assert result.action == GuardrailAction.BLOCK
    assert result.reason == "deterministic block"
    assert chat.chat_call_count == 0  # judge skipped


@pytest.mark.asyncio
async def test_wrapped_pass_judge_approves_returns_pass_no_mutation() -> None:
    chat = MockChatClient(responses=[_judge_resp(passed=True)])
    judge = LLMJudgeVerifier(chat_client=chat, judge_template="Judge: {output}")
    wrapper = LLMVerifyMutateGuardrail(wrapped=_PassDetector(), judge=judge)

    engine = GuardrailEngine()
    engine.register(wrapper)

    result = await engine.check_output("clean content")
    assert result.action == GuardrailAction.PASS
    # No sanitized_content (PASS doesn't mutate)
    assert result.sanitized_content is None
    assert chat.chat_call_count == 1


@pytest.mark.asyncio
async def test_wrapped_pass_judge_fails_with_correction_returns_sanitize() -> None:
    """The key AD-Cat9-2 closure: SANITIZE actually carries a mutation."""
    chat = MockChatClient(
        responses=[
            _judge_resp(
                passed=False,
                correction="My phone is [REDACTED].",
                reason="contains phone number",
            )
        ]
    )
    judge = LLMJudgeVerifier(chat_client=chat, judge_template="pii_leak_check", name="pii_judge")
    wrapper = LLMVerifyMutateGuardrail(wrapped=_PassDetector(), judge=judge, name="pii_mutate")

    engine = GuardrailEngine()
    engine.register(wrapper)

    result = await engine.check_output("My phone is 555-1234.")

    # Critical assertion (the AD-Cat9-2 fix): SANITIZE comes with a real mutation
    assert result.action == GuardrailAction.SANITIZE
    assert result.sanitized_content == "My phone is [REDACTED]."
    assert result.sanitized_content != "My phone is 555-1234."
    assert result.reason is not None
    assert "pii_mutate" in result.reason
    assert "contains phone number" in result.reason


@pytest.mark.asyncio
async def test_wrapped_pass_judge_fails_no_correction_falls_back_to_block() -> None:
    """Fail-safe: judge says bad but offers no correction → BLOCK (don't ship known-bad output)."""
    chat = MockChatClient(
        responses=[
            _judge_resp(
                passed=False,
                correction=None,
                reason="vaguely bad",
            )
        ]
    )
    judge = LLMJudgeVerifier(chat_client=chat, judge_template="Judge: {output}")
    wrapper = LLMVerifyMutateGuardrail(wrapped=_PassDetector(), judge=judge)

    engine = GuardrailEngine()
    engine.register(wrapper)

    result = await engine.check_output("bad content")
    assert result.action == GuardrailAction.BLOCK
    assert result.reason is not None
    # Wrapper propagates judge's reason verbatim; no sanitized_content for fail-safe BLOCK
    assert "vaguely bad" in result.reason
    assert result.sanitized_content is None

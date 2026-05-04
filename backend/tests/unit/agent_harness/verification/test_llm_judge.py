"""
File: backend/tests/unit/agent_harness/verification/test_llm_judge.py
Purpose: Unit tests for LLMJudgeVerifier — judge call, fail-closed semantics, performance SLO.
Category: Tests / Unit / 範疇 10
Scope: Sprint 54.1 US-2

Description:
    Covers:
    - judge returns pass for consistent output (mock ChatClient)
    - judge returns fail for inconsistent output (mock ChatClient)
    - chat client exception → fail-closed (passed=False with judge_error reason)
    - malformed JSON response → fail-closed
    - template loading by name (factual_consistency)
    - p95 < 5s SLO with mock chat client (0.5s per call x 10 iters)

    Uses MockChatClient from adapters/_testing — NOT real LLM.

Created: 2026-05-04 (Sprint 54.1 Day 2)

Related:
    - backend/src/agent_harness/verification/llm_judge.py
    - backend/src/adapters/_testing/mock_clients.py
"""

from __future__ import annotations

import asyncio
import time
from typing import cast

import pytest

from adapters._testing.mock_clients import MockChatClient
from agent_harness._contracts import LoopState, VerificationResult
from agent_harness._contracts.chat import ChatRequest, ChatResponse, StopReason
from agent_harness.verification import LLMJudgeVerifier


def _state() -> LoopState:
    """LLMJudgeVerifier doesn't read state attributes; cast None to satisfy ABC."""
    return cast(LoopState, None)


def _judge_response(
    *, passed: bool, score: float = 0.95, reason: str = "ok", correction: str | None = None
) -> ChatResponse:
    """Build a ChatResponse whose JSON content the judge can parse."""
    import json

    payload = {
        "passed": passed,
        "score": score,
        "reason": reason,
        "suggested_correction": correction,
    }
    return ChatResponse(
        model="mock-judge",
        content=json.dumps(payload),
        stop_reason=StopReason.END_TURN,
    )


@pytest.mark.asyncio
async def test_judge_returns_pass_for_consistent_output() -> None:
    chat = MockChatClient(responses=[_judge_response(passed=True, score=0.92)])
    verifier = LLMJudgeVerifier(
        chat_client=chat,
        judge_template="Judge this: {output}\nReply JSON.",
    )
    result = await verifier.verify(output="The sky is blue.", state=_state())

    assert result.passed is True
    assert result.verifier_type == "llm_judge"
    assert result.score == 0.92
    assert chat.chat_call_count == 1


@pytest.mark.asyncio
async def test_judge_returns_fail_for_inconsistent_output() -> None:
    chat = MockChatClient(
        responses=[
            _judge_response(
                passed=False,
                score=0.15,
                reason="contradicts source",
                correction="The sky is blue, not green.",
            )
        ]
    )
    verifier = LLMJudgeVerifier(
        chat_client=chat,
        judge_template="Judge: {output}",
    )
    result = await verifier.verify(output="The sky is green.", state=_state())

    assert result.passed is False
    assert result.reason == "contradicts source"
    assert result.suggested_correction == "The sky is blue, not green."


@pytest.mark.asyncio
async def test_judge_chat_client_exception_fail_closed() -> None:
    """Per fail-closed semantics: chat client raises → passed=False (do NOT swallow)."""

    class _RaisingChatClient(MockChatClient):
        async def chat(self, request: ChatRequest, **kwargs: object) -> ChatResponse:
            raise RuntimeError("simulated network failure")

    chat = _RaisingChatClient()
    verifier = LLMJudgeVerifier(chat_client=chat, judge_template="Judge: {output}")
    result = await verifier.verify(output="anything", state=_state())

    assert result.passed is False
    assert result.reason is not None
    assert "judge_error" in result.reason
    assert "RuntimeError" in result.reason
    assert "simulated network failure" in result.reason


@pytest.mark.asyncio
async def test_judge_malformed_response_fail_closed() -> None:
    """Per fail-closed semantics: malformed JSON → passed=False."""
    chat = MockChatClient(
        responses=[
            ChatResponse(
                model="mock-judge",
                content="not valid json at all",
                stop_reason=StopReason.END_TURN,
            )
        ]
    )
    verifier = LLMJudgeVerifier(chat_client=chat, judge_template="Judge: {output}")
    result = await verifier.verify(output="x", state=_state())

    assert result.passed is False
    assert result.reason is not None
    assert "malformed_judge_response" in result.reason


@pytest.mark.asyncio
async def test_judge_missing_passed_key_fail_closed() -> None:
    """JSON object missing required 'passed' key → fail-closed."""
    import json

    chat = MockChatClient(
        responses=[
            ChatResponse(
                model="mock-judge",
                content=json.dumps({"score": 0.5, "reason": "no verdict"}),
                stop_reason=StopReason.END_TURN,
            )
        ]
    )
    verifier = LLMJudgeVerifier(chat_client=chat, judge_template="Judge: {output}")
    result = await verifier.verify(output="x", state=_state())

    assert result.passed is False
    assert result.reason is not None
    assert "missing 'passed' key" in result.reason


@pytest.mark.asyncio
async def test_judge_loads_factual_consistency_template_by_name() -> None:
    """When judge_template is a name (no {output} substring), load it from templates/."""
    chat = MockChatClient(responses=[_judge_response(passed=True)])
    # "factual_consistency" is a template name (US-2 ships 4 default templates)
    verifier = LLMJudgeVerifier(chat_client=chat, judge_template="factual_consistency")
    result = await verifier.verify(output="The Eiffel Tower is in Paris.", state=_state())

    assert result.passed is True
    # The mock recorded the request; verify the prompt includes the template + output
    assert chat.last_request is not None
    sent_prompt = chat.last_request.messages[0].content
    assert isinstance(sent_prompt, str)
    assert "fact-checking judge" in sent_prompt  # template content
    assert "The Eiffel Tower is in Paris." in sent_prompt  # output substituted


@pytest.mark.asyncio
async def test_judge_p95_under_5s() -> None:
    """SLO from 01-eleven-categories-spec.md §範疇 10: LLM-judge p95 < 5s.

    Uses mock with 50ms artificial delay × 10 iterations. Real LLM SLO verified manually.
    """

    class _SlowChatClient(MockChatClient):
        async def chat(self, request: ChatRequest, **kwargs: object) -> ChatResponse:
            await asyncio.sleep(0.05)  # 50ms simulated LLM latency
            return _judge_response(passed=True)

    chat = _SlowChatClient()
    verifier = LLMJudgeVerifier(chat_client=chat, judge_template="Judge: {output}")

    durations: list[float] = []
    for _ in range(10):
        t0 = time.perf_counter()
        await verifier.verify(output="test", state=_state())
        durations.append(time.perf_counter() - t0)

    durations.sort()
    p95 = durations[-1]
    assert p95 < 5.0, f"p95 {p95 * 1000:.1f}ms exceeds 5s SLO"


def test_verification_result_is_dataclass() -> None:
    """Sanity: VerificationResult contract import works (regression guard for D3 drift)."""
    result = VerificationResult(passed=True, verifier_name="x", verifier_type="llm_judge")
    assert result.verifier_type == "llm_judge"

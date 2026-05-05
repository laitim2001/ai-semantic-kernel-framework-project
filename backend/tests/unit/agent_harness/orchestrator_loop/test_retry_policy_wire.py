"""
File: backend/tests/unit/agent_harness/orchestrator_loop/test_retry_policy_wire.py
Purpose: Unit tests for _should_retry_tool_error helper (Sprint 55.6 AD-Cat8-2 Option H).
Category: Tests / 範疇 1 + 範疇 8 boundary
Scope: Phase 55 / Sprint 55.6 Day 2

Description:
    Sprint 55.6 closes AD-Cat8-2 via Option H: NEW helper
    `_should_retry_tool_error` consults Cat 8 deps per 53.2 spec docstring
    steps 2-4 (should_retry → get_policy → compute_backoff). Strictly
    additive — no ABC change, no _handle_tool_error signature change.

    These tests verify:
      - Helper correctness for retryable / non-retryable ErrorClass
      - Backwards-compat baseline when Cat 8 deps are None (False, 0.0)
      - Defensive guard against None error_class
      - Attempts-exhausted short-circuit before compute_backoff
      - HITL_RECOVERABLE / FATAL enforce max_attempts=0 (never retry)

    Retry loop wrap end-to-end behavior (event emission / attempt_num
    increment / fall-through) is exercised in the integration test
    `tests/integration/agent_harness/orchestrator_loop/test_loop_error_handling.py`.

Created: 2026-05-05 (Sprint 55.6 Day 2)

Modification History (newest-first):
    - 2026-05-05: Initial creation (Sprint 55.6 Day 2) — close AD-Cat8-2 helper unit tests
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from agent_harness.error_handling._abc import ErrorClass, ErrorPolicy
from agent_harness.error_handling.retry import RetryPolicyMatrix
from agent_harness.orchestrator_loop.loop import AgentLoopImpl


@pytest.fixture
def policy() -> MagicMock:
    """Mocked ErrorPolicy with should_retry returning True (override per-test).

    Unit isolation: the helper consults ``error_policy.should_retry`` as a
    Step 2 gate; the gate's classification logic is tested separately in
    test_policy.py. Mocking here keeps the unit focused on the helper's
    decision flow (gate True → consult retry_matrix; gate False → short-circuit).
    """
    p = MagicMock(spec=ErrorPolicy)
    p.should_retry.return_value = True
    return p


@pytest.fixture
def retry_matrix() -> RetryPolicyMatrix:
    """RetryPolicyMatrix with Cat 8 spec defaults (TRANSIENT max=3, FATAL max=0)."""
    return RetryPolicyMatrix()


@pytest.fixture
def loop_with_retry(
    policy: MagicMock,
    retry_matrix: RetryPolicyMatrix,
) -> AgentLoopImpl:
    """AgentLoopImpl with both error_policy + retry_policy wired (full Cat 8 retry path)."""
    return AgentLoopImpl(
        chat_client=MagicMock(),
        output_parser=MagicMock(),
        tool_executor=MagicMock(),
        tool_registry=MagicMock(),
        tenant_id=uuid4(),
        error_policy=policy,
        retry_policy=retry_matrix,
    )


# === Test 1: TRANSIENT with attempts left → retry ===
@pytest.mark.asyncio
async def test_should_retry_tool_error_returns_true_for_transient_with_attempts_left(
    loop_with_retry: AgentLoopImpl,
) -> None:
    """TRANSIENT class + attempt=1 (below default max_attempts=3) → (True, backoff > 0).

    Validates Step 2 (should_retry gate True) + Step 3 (get_policy → RetryConfig
    with max_attempts=3) + Step 4 (compute_backoff returns positive value).
    """
    should_retry, backoff = await loop_with_retry._should_retry_tool_error(
        error=Exception("network timeout"),
        error_class=ErrorClass.TRANSIENT,
        tool_name="tool_a",
        attempt=1,
    )
    assert should_retry is True
    assert backoff > 0.0


# === Test 2: TRANSIENT at max_attempts → no retry (defensive short-circuit) ===
@pytest.mark.asyncio
async def test_should_retry_tool_error_returns_false_when_attempts_exhausted(
    loop_with_retry: AgentLoopImpl,
) -> None:
    """attempt >= max_attempts (3 default for TRANSIENT) → (False, 0.0).

    Defensive short-circuit before compute_backoff avoids unnecessary call
    when at cap. This is the loop terminator path: max_attempts hit →
    fall through to LLM-recoverable synthesis at caller site.
    """
    should_retry, backoff = await loop_with_retry._should_retry_tool_error(
        error=Exception("network timeout"),
        error_class=ErrorClass.TRANSIENT,
        tool_name="tool_a",
        attempt=3,  # at cap
    )
    assert should_retry is False
    assert backoff == 0.0


# === Test 3: error_policy=None → baseline (53.1 preserved) ===
@pytest.mark.asyncio
async def test_should_retry_tool_error_returns_false_when_error_policy_is_none(
    retry_matrix: RetryPolicyMatrix,
) -> None:
    """Cat 8 dep None → helper short-circuits (False, 0.0); 53.1 baseline preserved."""
    loop = AgentLoopImpl(
        chat_client=MagicMock(),
        output_parser=MagicMock(),
        tool_executor=MagicMock(),
        tool_registry=MagicMock(),
        # error_policy NOT set => None
        retry_policy=retry_matrix,
    )
    should_retry, backoff = await loop._should_retry_tool_error(
        error=Exception("any"),
        error_class=ErrorClass.TRANSIENT,
        tool_name="tool_a",
        attempt=1,
    )
    assert should_retry is False
    assert backoff == 0.0


# === Test 4: retry_policy=None → baseline (53.1 preserved) ===
@pytest.mark.asyncio
async def test_should_retry_tool_error_returns_false_when_retry_policy_is_none(
    policy: MagicMock,
) -> None:
    """Cat 8 dep None => helper short-circuits (False, 0.0); 53.1 baseline preserved."""
    loop = AgentLoopImpl(
        chat_client=MagicMock(),
        output_parser=MagicMock(),
        tool_executor=MagicMock(),
        tool_registry=MagicMock(),
        error_policy=policy,
        # retry_policy NOT set => None
    )
    should_retry, backoff = await loop._should_retry_tool_error(
        error=Exception("any"),
        error_class=ErrorClass.TRANSIENT,
        tool_name="tool_a",
        attempt=1,
    )
    assert should_retry is False
    assert backoff == 0.0


# === Test 5: error_class=None defensive guard ===
@pytest.mark.asyncio
async def test_should_retry_tool_error_returns_false_when_error_class_is_none(
    loop_with_retry: AgentLoopImpl,
) -> None:
    """error_class=None (caller couldn't classify) → defensive (False, 0.0).

    This guards against the rare path where _handle_tool_error returns
    err_class=None despite both deps being present (shouldn't happen in
    practice but defensive coding).
    """
    should_retry, backoff = await loop_with_retry._should_retry_tool_error(
        error=Exception("any"),
        error_class=None,
        tool_name="tool_a",
        attempt=1,
    )
    assert should_retry is False
    assert backoff == 0.0


# === Test 6: HITL_RECOVERABLE never retries (max_attempts=0 default) ===
@pytest.mark.asyncio
async def test_should_retry_tool_error_returns_false_for_hitl_recoverable(
    loop_with_retry: AgentLoopImpl,
) -> None:
    """HITL_RECOVERABLE has max_attempts=0 in Cat 8 spec defaults → no retry.

    Per Cat 8 §HITL-recoverable taxonomy: humans must intervene; loop
    cannot self-correct via retry. This test enforces the contract.
    """
    should_retry, backoff = await loop_with_retry._should_retry_tool_error(
        error=Exception("hitl required"),
        error_class=ErrorClass.HITL_RECOVERABLE,
        tool_name="tool_a",
        attempt=1,
    )
    assert should_retry is False
    assert backoff == 0.0


# === Test 7: FATAL never retries (max_attempts=0 default) ===
@pytest.mark.asyncio
async def test_should_retry_tool_error_returns_false_for_fatal(
    loop_with_retry: AgentLoopImpl,
) -> None:
    """FATAL has max_attempts=0 in Cat 8 spec defaults → no retry.

    Per Cat 8 §Fatal taxonomy: bug or unrecoverable; loop must terminate.
    Retry would mask root cause.
    """
    should_retry, backoff = await loop_with_retry._should_retry_tool_error(
        error=Exception("fatal bug"),
        error_class=ErrorClass.FATAL,
        tool_name="tool_a",
        attempt=1,
    )
    assert should_retry is False
    assert backoff == 0.0


# === Test 8: helper trusts error_class param (soft-failure path correctness) ===
@pytest.mark.asyncio
async def test_should_retry_tool_error_uses_error_class_param_not_re_classify(
    loop_with_retry: AgentLoopImpl,
) -> None:
    """Sprint 55.6 D10: helper trusts caller's error_class param, NOT
    re-classification via error_policy.classify(error).

    This is essential for the soft-failure path: the synthetic Exception
    has generic MRO (would classify as FATAL via DefaultErrorPolicy), but
    caller's error_class came from classify_by_string(result.error_class)
    per AD-Cat8-3 narrow Option C (Sprint 55.4). Helper must respect the
    param to honor both hard-exception and soft-failure paths uniformly.
    """
    # error_class param is TRANSIENT, but the actual `error` is generic
    # Exception (which DefaultErrorPolicy.classify() would label as FATAL
    # via MRO walk). Helper must use error_class param, not re-classify.
    should_retry, backoff = await loop_with_retry._should_retry_tool_error(
        error=Exception("synthetic from soft-failure path"),
        error_class=ErrorClass.TRANSIENT,
        tool_name="tool_a",
        attempt=1,
    )
    assert should_retry is True
    assert backoff > 0.0

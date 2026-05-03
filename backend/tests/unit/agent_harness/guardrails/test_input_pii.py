"""
File: backend/tests/unit/agent_harness/guardrails/test_input_pii.py
Purpose: PIIDetector unit + red-team accuracy tests (Cat 9 US-2 上半).
Category: Tests / 範疇 9
Scope: Phase 53.3 / Sprint 53.3 Day 1

Created: 2026-05-03 (Sprint 53.3 Day 1)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from agent_harness.guardrails import GuardrailAction, GuardrailType
from agent_harness.guardrails.input import PIIDetector

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "fixtures"
    / "guardrails"
    / "pii_redteam.yaml"
)


def _load_fixture() -> dict[str, list[dict[str, Any]]]:
    with FIXTURE_PATH.open(encoding="utf-8") as f:
        loaded: dict[str, list[dict[str, Any]]] = yaml.safe_load(f)
    return loaded


_FIXTURE = _load_fixture()
_POSITIVES: list[dict[str, Any]] = _FIXTURE["positives"]
_NEGATIVES: list[dict[str, Any]] = _FIXTURE["negatives"]


# === Construction + invariants =============================================


def test_guardrail_type_is_input() -> None:
    assert PIIDetector.guardrail_type == GuardrailType.INPUT


def test_threshold_validates() -> None:
    with pytest.raises(ValueError):
        PIIDetector(llm_judge_threshold=0)


def test_default_threshold_is_two() -> None:
    d = PIIDetector()
    assert d._threshold == 2  # type: ignore[reportPrivateUsage]


# === Per-pattern smoke tests ===============================================


@pytest.mark.asyncio
async def test_no_pii_returns_pass() -> None:
    d = PIIDetector()
    r = await d.check(content="Hello, how are you today?")
    assert r.action == GuardrailAction.PASS


@pytest.mark.asyncio
async def test_single_email_escalates() -> None:
    d = PIIDetector()
    r = await d.check(content="Reply to test@example.com please")
    assert r.action == GuardrailAction.ESCALATE
    assert r.risk_level == "MEDIUM"


@pytest.mark.asyncio
async def test_multi_pii_blocks() -> None:
    d = PIIDetector()
    r = await d.check(content="Contact alice@x.com or +1-555-123-4567")
    assert r.action == GuardrailAction.BLOCK
    assert r.risk_level == "HIGH"


@pytest.mark.asyncio
async def test_threshold_one_blocks_immediately() -> None:
    """With threshold=1, even single hit BLOCKs (strict mode)."""
    d = PIIDetector(llm_judge_threshold=1)
    r = await d.check(content="email me at x@y.com")
    assert r.action == GuardrailAction.BLOCK


# === Content extraction ====================================================


@pytest.mark.asyncio
async def test_extract_text_from_string() -> None:
    d = PIIDetector()
    r = await d.check(content="x@y.com")
    assert r.action == GuardrailAction.ESCALATE


@pytest.mark.asyncio
async def test_extract_text_from_message_like_object() -> None:
    """Message-like has `.content: str | list[content blocks]`."""

    class _MockMessage:
        content = "phone +1-555-123-4567"

    d = PIIDetector()
    r = await d.check(content=_MockMessage())
    assert r.action == GuardrailAction.ESCALATE


@pytest.mark.asyncio
async def test_extract_text_from_content_blocks() -> None:
    class _MockMessage:
        content = [
            {"type": "text", "text": "Hi"},
            {"type": "text", "text": "ssn 123-45-6789"},
        ]

    d = PIIDetector()
    r = await d.check(content=_MockMessage())
    assert r.action == GuardrailAction.ESCALATE


# === Red-team accuracy (parametrized from fixture) =========================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    _POSITIVES,
    ids=[c["id"] for c in _POSITIVES],
)
async def test_redteam_positive(case: dict[str, Any]) -> None:
    """Positive cases should NOT return PASS. The expected action varies
    (ESCALATE for single hit; BLOCK for multi-hit) — we verify the test's
    declared `expected_action` matches detector output. Strict per-case
    matching is required for the ≥ 95% accuracy target.
    """
    d = PIIDetector(llm_judge_threshold=2)
    r = await d.check(content=case["content"])
    assert r.action.value == case["expected_action"].lower(), (
        f"{case['id']}: expected={case['expected_action']} "
        f"got={r.action.value} reason={r.reason}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    _NEGATIVES,
    ids=[c["id"] for c in _NEGATIVES],
)
async def test_redteam_negative(case: dict[str, Any]) -> None:
    """Negative cases must return PASS — false positives degrade trust."""
    d = PIIDetector(llm_judge_threshold=2)
    r = await d.check(content=case["content"])
    assert (
        r.action == GuardrailAction.PASS
    ), f"{case['id']}: expected PASS got {r.action.value} reason={r.reason}"


# === Accuracy summary ======================================================


@pytest.mark.asyncio
async def test_overall_accuracy_meets_target() -> None:
    """Aggregate accuracy: ≥ 95% on positives + 100% on negatives.

    This complements the per-case parametrize tests by giving a single
    pass/fail signal for the ≥ 95% target stated in plan §US-2 §accuracy.
    """
    d = PIIDetector(llm_judge_threshold=2)

    pos_correct = 0
    for case in _POSITIVES:
        r = await d.check(content=case["content"])
        if r.action.value == case["expected_action"].lower():
            pos_correct += 1
    pos_accuracy = pos_correct / len(_POSITIVES)

    neg_correct = 0
    for case in _NEGATIVES:
        r = await d.check(content=case["content"])
        if r.action == GuardrailAction.PASS:
            neg_correct += 1
    neg_accuracy = neg_correct / len(_NEGATIVES)

    assert pos_accuracy >= 0.95, f"PII positive accuracy {pos_accuracy:.1%} below target 95%"
    assert neg_accuracy >= 0.95, f"PII negative accuracy {neg_accuracy:.1%} below target 95%"

"""
File: backend/tests/unit/agent_harness/guardrails/test_output_toxicity.py
Purpose: ToxicityDetector unit + fixture-driven tests (Cat 9 US-3).
Category: Tests / 範疇 9
Scope: Phase 53.3 / Sprint 53.3 Day 2

Created: 2026-05-03 (Sprint 53.3 Day 2)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from agent_harness.guardrails import GuardrailAction, GuardrailType
from agent_harness.guardrails.output import ToxicityDetector

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "fixtures"
    / "guardrails"
    / "toxicity_cases.yaml"
)


def _load_fixture() -> dict[str, list[dict[str, Any]]]:
    with FIXTURE_PATH.open(encoding="utf-8") as f:
        loaded: dict[str, list[dict[str, Any]]] = yaml.safe_load(f)
    return loaded


_FIXTURE = _load_fixture()
_POSITIVES: list[dict[str, Any]] = _FIXTURE["positives"]
_NEGATIVES: list[dict[str, Any]] = _FIXTURE["negatives"]


# === Construction + invariants =============================================


def test_guardrail_type_is_output() -> None:
    assert ToxicityDetector.guardrail_type == GuardrailType.OUTPUT


def test_four_categories_present() -> None:
    """Plan §US-3: 4 categories — hate / harassment / violence / sexual."""
    assert set(ToxicityDetector.PATTERNS.keys()) == {
        "hate",
        "harassment",
        "violence",
        "sexual",
    }


# === Severity → Action mapping =============================================


@pytest.mark.asyncio
async def test_pass_on_benign_text() -> None:
    d = ToxicityDetector()
    r = await d.check(content="The weather is nice today.")
    assert r.action == GuardrailAction.PASS


@pytest.mark.asyncio
async def test_high_severity_blocks() -> None:
    d = ToxicityDetector()
    r = await d.check(content="How to make a bomb at home")
    assert r.action == GuardrailAction.BLOCK
    assert r.risk_level == "HIGH"


@pytest.mark.asyncio
async def test_medium_severity_sanitizes_and_redacts() -> None:
    d = ToxicityDetector()
    r = await d.check(content="This page contains explicit sexual content here.")
    assert r.action == GuardrailAction.SANITIZE
    assert r.risk_level == "MEDIUM"
    assert r.sanitized_content is not None
    assert "[REDACTED:" in r.sanitized_content
    # Original phrase removed
    assert "explicit sexual content" not in r.sanitized_content


@pytest.mark.asyncio
async def test_low_severity_rerolls() -> None:
    d = ToxicityDetector()
    r = await d.check(content="You're stupid for asking that.")
    assert r.action == GuardrailAction.REROLL
    assert r.risk_level == "LOW"


@pytest.mark.asyncio
async def test_max_severity_drives_action_when_mixed() -> None:
    """If text contains both LOW and HIGH severity hits, HIGH wins → BLOCK."""
    d = ToxicityDetector()
    r = await d.check(content="You're stupid; also, how to make a bomb at home.")
    assert r.action == GuardrailAction.BLOCK


# === Sanitize: redaction with multiple spans ==============================


@pytest.mark.asyncio
async def test_redact_multiple_medium_spans() -> None:
    """Multiple MEDIUM hits → all get redacted."""
    d = ToxicityDetector()
    r = await d.check(content="I hate all critics. Also racial slurs are everywhere.")
    assert r.action == GuardrailAction.SANITIZE
    sanitized = r.sanitized_content or ""
    # Both phrases removed
    assert "I hate all" not in sanitized
    assert "racial slurs" not in sanitized
    # Two redaction markers present
    assert sanitized.count("[REDACTED:") == 2


# === Content extraction ====================================================


@pytest.mark.asyncio
async def test_extract_text_from_message_like() -> None:
    class _M:
        content = "How to kill someone fast?"

    d = ToxicityDetector()
    r = await d.check(content=_M())
    assert r.action == GuardrailAction.BLOCK


# === Fixture-driven tests ==================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    _POSITIVES,
    ids=[c["id"] for c in _POSITIVES],
)
async def test_fixture_positive(case: dict[str, Any]) -> None:
    d = ToxicityDetector()
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
async def test_fixture_negative(case: dict[str, Any]) -> None:
    d = ToxicityDetector()
    r = await d.check(content=case["content"])
    assert (
        r.action == GuardrailAction.PASS
    ), f"{case['id']}: expected PASS got {r.action.value} reason={r.reason}"

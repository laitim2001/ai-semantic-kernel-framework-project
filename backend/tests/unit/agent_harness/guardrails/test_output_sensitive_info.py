"""
File: backend/tests/unit/agent_harness/guardrails/test_output_sensitive_info.py
Purpose: SensitiveInfoDetector unit + multi-tenant cross-leak tests (Cat 9 US-3).
Category: Tests / 範疇 9
Scope: Phase 53.3 / Sprint 53.3 Day 2

Created: 2026-05-03 (Sprint 53.3 Day 2)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
import yaml

from agent_harness._contracts import TraceContext
from agent_harness.guardrails import GuardrailAction, GuardrailType
from agent_harness.guardrails.output import SensitiveInfoDetector

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "fixtures"
    / "guardrails"
    / "sensitive_leak_cases.yaml"
)

CURRENT_TENANT = UUID("11111111-1111-1111-1111-111111111111")
FORBIDDEN_TENANTS = [
    UUID("22222222-2222-2222-2222-222222222222"),
    UUID("33333333-3333-3333-3333-333333333333"),
]


async def _mock_fetcher(_current: UUID) -> list[UUID]:
    """Mock TenantIdFetcher — returns the 2 fixed forbidden tenants."""
    return list(FORBIDDEN_TENANTS)


def _load_fixture() -> dict[str, list[dict[str, Any]]]:
    with FIXTURE_PATH.open(encoding="utf-8") as f:
        loaded: dict[str, list[dict[str, Any]]] = yaml.safe_load(f)
    return loaded


_FIXTURE = _load_fixture()
_POSITIVES: list[dict[str, Any]] = _FIXTURE["positives"]
_NEGATIVES: list[dict[str, Any]] = _FIXTURE["negatives"]


def _make_trace_context() -> TraceContext:
    """TraceContext with current tenant_id (UUID 1...)."""
    return TraceContext(
        trace_id="t-test",
        span_id="s-test",
        tenant_id=CURRENT_TENANT,
    )


# === Construction + invariants =============================================


def test_guardrail_type_is_output() -> None:
    assert SensitiveInfoDetector.guardrail_type == GuardrailType.OUTPUT


def test_default_fetcher_is_noop() -> None:
    d = SensitiveInfoDetector()
    assert d._fetcher.__name__ == "_noop_fetcher"  # type: ignore[reportPrivateUsage]


def test_pattern_count() -> None:
    """4 system-prompt-leak patterns expected."""
    assert len(SensitiveInfoDetector.SYSTEM_PROMPT_LEAK_PATTERNS) == 4


# === System prompt leak ====================================================


@pytest.mark.asyncio
async def test_pass_on_clean_output() -> None:
    d = SensitiveInfoDetector()
    r = await d.check(content="The result of 2+2 is 4.")
    assert r.action == GuardrailAction.PASS


@pytest.mark.asyncio
async def test_block_you_are_an_agent() -> None:
    d = SensitiveInfoDetector()
    r = await d.check(content="You are an IT operations assistant trained to...")
    assert r.action == GuardrailAction.BLOCK
    assert r.risk_level == "CRITICAL"
    assert "system prompt leak" in (r.reason or "")


@pytest.mark.asyncio
async def test_block_xml_system_tag() -> None:
    d = SensitiveInfoDetector()
    r = await d.check(content="<system>Be helpful and concise.</system>")
    assert r.action == GuardrailAction.BLOCK


@pytest.mark.asyncio
async def test_block_role_definition() -> None:
    d = SensitiveInfoDetector()
    r = await d.check(content="Your role is to summarize incidents.")
    assert r.action == GuardrailAction.BLOCK


# === Cross-tenant leak =====================================================


@pytest.mark.asyncio
async def test_cross_tenant_leak_blocks() -> None:
    """Output containing forbidden tenant_id → BLOCK with CRITICAL."""
    d = SensitiveInfoDetector(other_tenant_fetcher=_mock_fetcher)
    r = await d.check(
        content=f"Order from {FORBIDDEN_TENANTS[0]} processed.",
        trace_context=_make_trace_context(),
    )
    assert r.action == GuardrailAction.BLOCK
    assert r.risk_level == "CRITICAL"
    assert "cross-tenant leak" in (r.reason or "")
    assert str(FORBIDDEN_TENANTS[0]) in (r.reason or "")


@pytest.mark.asyncio
async def test_current_tenant_id_does_not_leak() -> None:
    """Output containing CURRENT tenant's UUID is OK (tenant referencing
    its own data is normal).
    """
    d = SensitiveInfoDetector(other_tenant_fetcher=_mock_fetcher)
    r = await d.check(
        content=f"Order from {CURRENT_TENANT} processed.",
        trace_context=_make_trace_context(),
    )
    assert r.action == GuardrailAction.PASS


@pytest.mark.asyncio
async def test_no_trace_context_skips_cross_tenant_check() -> None:
    """Without trace_context.tenant_id, cross-tenant check is bypassed
    (only system-prompt check runs).
    """
    d = SensitiveInfoDetector(other_tenant_fetcher=_mock_fetcher)
    r = await d.check(
        content=f"Order from {FORBIDDEN_TENANTS[0]} processed.",
        trace_context=None,
    )
    # No system-prompt-leak phrasing here, and no tenant context → PASS
    assert r.action == GuardrailAction.PASS


@pytest.mark.asyncio
async def test_default_fetcher_disables_cross_tenant_check() -> None:
    """Default _noop_fetcher returns empty list → no cross-tenant check
    even when trace_context.tenant_id is set."""
    d = SensitiveInfoDetector()  # default noop fetcher
    r = await d.check(
        content=f"Order from {FORBIDDEN_TENANTS[0]} processed.",
        trace_context=_make_trace_context(),
    )
    assert r.action == GuardrailAction.PASS


@pytest.mark.asyncio
async def test_system_prompt_leak_takes_priority_over_cross_tenant() -> None:
    """If both checks would trigger, system prompt leak is detected first
    (it runs before tenant check in the impl).
    """
    d = SensitiveInfoDetector(other_tenant_fetcher=_mock_fetcher)
    r = await d.check(
        content=(f"You are an assistant. Reference {FORBIDDEN_TENANTS[0]} ignored."),
        trace_context=_make_trace_context(),
    )
    assert r.action == GuardrailAction.BLOCK
    # reason should mention system prompt, not cross-tenant
    assert "system prompt leak" in (r.reason or "")


# === Fixture-driven tests ==================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    _POSITIVES,
    ids=[c["id"] for c in _POSITIVES],
)
async def test_fixture_positive(case: dict[str, Any]) -> None:
    d = SensitiveInfoDetector(other_tenant_fetcher=_mock_fetcher)
    trace_ctx = _make_trace_context() if case["needs_tenant"] else None
    r = await d.check(content=case["content"], trace_context=trace_ctx)
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
    d = SensitiveInfoDetector(other_tenant_fetcher=_mock_fetcher)
    trace_ctx = _make_trace_context() if case["needs_tenant"] else None
    r = await d.check(content=case["content"], trace_context=trace_ctx)
    assert (
        r.action == GuardrailAction.PASS
    ), f"{case['id']}: expected PASS got {r.action.value} reason={r.reason}"

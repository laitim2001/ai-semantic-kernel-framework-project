"""
File: backend/tests/unit/platform_layer/governance/risk/test_policy.py
Purpose: Unit tests for DefaultRiskPolicy YAML-driven risk evaluation.
Category: Tests / Platform / Governance / Risk
Scope: Phase 53 / Sprint 53.4 US-1

Created: 2026-05-03 (Sprint 53.4 Day 1)
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from agent_harness._contracts.hitl import RiskLevel
from platform_layer.governance.risk.policy import DefaultRiskPolicy

# --------------- Fixtures --------------------------------------------------


@pytest.fixture
def yaml_path(tmp_path: Path) -> Path:
    """Write a minimal but exhaustive risk_policy.yaml for tests."""
    content = """\
version: "1.0"
default_risk: medium

tool_overrides:
  - pattern: "salesforce_*"
    risk: high
  - pattern: "delete_*"
    risk: critical
  - pattern: "read_*"
    risk: low

per_tenant_overlays:
  strict_tenant_id:
    "salesforce_delete_*": critical
"""
    cfg = tmp_path / "risk_policy.yaml"
    cfg.write_text(content, encoding="utf-8")
    return cfg


@pytest.fixture
def policy(yaml_path: Path) -> DefaultRiskPolicy:
    return DefaultRiskPolicy(config_path=yaml_path)


# --------------- Tests -----------------------------------------------------


def test_default_risk_for_unmatched_tool(policy: DefaultRiskPolicy) -> None:
    """Unknown tool name returns default_risk (medium)."""
    assert policy.evaluate("unknown_tool", {}, uuid4()) == RiskLevel.MEDIUM


def test_pattern_matching_returns_configured_risk(
    policy: DefaultRiskPolicy,
) -> None:
    """salesforce_* pattern matches → HIGH."""
    assert policy.evaluate("salesforce_query", {}, uuid4()) == RiskLevel.HIGH


def test_critical_pattern_takes_priority(policy: DefaultRiskPolicy) -> None:
    """delete_* matches → CRITICAL (highest priority)."""
    assert policy.evaluate("delete_user", {}, uuid4()) == RiskLevel.CRITICAL


def test_low_risk_pattern(policy: DefaultRiskPolicy) -> None:
    """read_* → LOW."""
    assert policy.evaluate("read_inventory", {}, uuid4()) == RiskLevel.LOW


def test_per_tenant_overlay_uplift(policy: DefaultRiskPolicy) -> None:
    """For strict_tenant_id, salesforce_delete_* uplifts to CRITICAL.

    Without overlay, salesforce_delete_record matches salesforce_* (HIGH).
    With overlay, also matches salesforce_delete_* (CRITICAL) → CRITICAL wins.
    """

    # Use a tenant_id whose str() equals the overlay key
    class FakeUUID:
        def __str__(self) -> str:
            return "strict_tenant_id"

    result = policy.evaluate("salesforce_delete_record", {}, FakeUUID())  # type: ignore[arg-type]
    assert result == RiskLevel.CRITICAL


def test_other_tenant_no_overlay(policy: DefaultRiskPolicy) -> None:
    """Different tenant gets only global pattern (HIGH for salesforce_*).

    salesforce_delete_record matches salesforce_* (HIGH) globally;
    delete_* pattern requires literal "delete_" prefix and does not match.
    No overlay for arbitrary tenant → HIGH.
    """
    result = policy.evaluate("salesforce_delete_record", {}, uuid4())
    assert result == RiskLevel.HIGH


def test_missing_config_raises(tmp_path: Path) -> None:
    """Non-existent config path raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        DefaultRiskPolicy(config_path=tmp_path / "nope.yaml")


def test_empty_config_uses_default_medium(tmp_path: Path) -> None:
    """Empty YAML uses default_risk fallback of MEDIUM."""
    cfg = tmp_path / "empty.yaml"
    cfg.write_text("", encoding="utf-8")
    policy = DefaultRiskPolicy(config_path=cfg)
    assert policy.evaluate("any_tool", {}, uuid4()) == RiskLevel.MEDIUM

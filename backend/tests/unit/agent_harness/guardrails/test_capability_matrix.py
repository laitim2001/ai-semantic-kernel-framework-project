"""
File: backend/tests/unit/agent_harness/guardrails/test_capability_matrix.py
Purpose: Unit tests for CapabilityMatrix + PermissionRule + from_yaml (Cat 9 US-4).
Category: Tests / 範疇 9
Scope: Phase 53.3 / Sprint 53.3 Day 3

Created: 2026-05-03 (Sprint 53.3 Day 3)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_harness.guardrails.tool import (
    Capability,
    CapabilityMatrix,
    PermissionRule,
)

PROD_YAML = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "config"
    / "capability_matrix.yaml"
)


# === Capability enum invariants =============================================


def test_capability_has_eight_baseline_values() -> None:
    """Plan §US-4 says ≥ 8 capabilities. Lock the baseline."""
    assert len(Capability) == 8
    assert {c.name for c in Capability} == {
        "READ_KB",
        "WRITE_KB",
        "EXECUTE_QUERY",
        "MODIFY_TICKET",
        "SEND_NOTIFICATION",
        "READ_PII",
        "EXECUTE_SHELL",
        "CALL_EXTERNAL_API",
    }


# === PermissionRule defaults ================================================


def test_permission_rule_defaults_are_open() -> None:
    """Default rule = unrestricted, no approval. Concrete rules tighten."""
    r = PermissionRule()
    assert r.role_required == "any"
    assert r.tenant_scope == "any"
    assert r.max_calls_per_session == 0
    assert r.requires_approval is False


# === CapabilityMatrix construction =========================================


def test_explicit_construction() -> None:
    matrix = CapabilityMatrix(
        capability_to_tools={
            Capability.READ_KB: ["search_kb"],
            Capability.WRITE_KB: ["create_doc", "delete_doc"],
        },
        permission_rules={
            "search_kb": PermissionRule(role_required="any"),
            "delete_doc": PermissionRule(role_required="admin", requires_approval=True),
        },
    )
    assert matrix.get_capability("search_kb") == Capability.READ_KB
    assert matrix.get_capability("delete_doc") == Capability.WRITE_KB
    assert matrix.get_capability("unknown") is None


def test_get_rule_returns_none_for_unknown_tool() -> None:
    matrix = CapabilityMatrix(capability_to_tools={}, permission_rules={})
    assert matrix.get_rule("nonexistent") is None


def test_list_tools_for_capability() -> None:
    matrix = CapabilityMatrix(
        capability_to_tools={Capability.WRITE_KB: ["create_doc", "update_doc"]},
        permission_rules={},
    )
    assert sorted(matrix.list_tools_for(Capability.WRITE_KB)) == [
        "create_doc",
        "update_doc",
    ]
    assert matrix.list_tools_for(Capability.EXECUTE_SHELL) == []  # missing → []


# === from_yaml roundtrip ===================================================


def test_from_yaml_loads_production_config() -> None:
    """Production config should load and have all 8 capabilities mapped."""
    matrix = CapabilityMatrix.from_yaml(PROD_YAML)
    # All 8 capabilities present
    for cap in Capability:
        tools = matrix.list_tools_for(cap)
        assert len(tools) > 0, f"No tools mapped to {cap}"
    # Sample lookups
    assert matrix.get_capability("search_kb") == Capability.READ_KB
    assert matrix.get_capability("delete_doc") == Capability.WRITE_KB
    assert matrix.get_capability("run_command") == Capability.EXECUTE_SHELL


def test_from_yaml_high_risk_tools_require_approval() -> None:
    matrix = CapabilityMatrix.from_yaml(PROD_YAML)
    # delete_doc + run_command + send_email are documented HIGH-risk
    for tool in ("delete_doc", "run_command", "send_email"):
        rule = matrix.get_rule(tool)
        assert rule is not None
        assert rule.requires_approval is True, f"{tool} should require approval"


def test_from_yaml_low_risk_tools_do_not_require_approval() -> None:
    matrix = CapabilityMatrix.from_yaml(PROD_YAML)
    for tool in ("search_kb", "get_doc", "salesforce_query"):
        rule = matrix.get_rule(tool)
        assert rule is not None
        assert rule.requires_approval is False, f"{tool} should NOT require approval"


def test_from_yaml_role_constraints() -> None:
    matrix = CapabilityMatrix.from_yaml(PROD_YAML)
    # admin-only tools
    rule_delete = matrix.get_rule("delete_doc")
    assert rule_delete is not None
    assert rule_delete.role_required == "admin"
    # ops-only tools
    rule_shell = matrix.get_rule("run_command")
    assert rule_shell is not None
    assert rule_shell.role_required == "ops"
    # any-role tools
    rule_search = matrix.get_rule("search_kb")
    assert rule_search is not None
    assert rule_search.role_required == "any"


def test_from_yaml_tenant_scope_defaults_to_own_only_for_tenant_data(
    tmp_path: Path,
) -> None:
    """Verify own_only is the explicit majority for enterprise data tools."""
    matrix = CapabilityMatrix.from_yaml(PROD_YAML)
    # tenant-data tools are own_only
    for tool in ("search_kb", "salesforce_query", "delete_doc"):
        rule = matrix.get_rule(tool)
        assert rule is not None
        assert rule.tenant_scope == "own_only", f"{tool} must be own_only"
    # external API tools may be "any" since not tenant-bound
    rule_http = matrix.get_rule("http_get")
    assert rule_http is not None
    assert rule_http.tenant_scope == "any"


# === from_yaml edge cases ==================================================


def test_from_yaml_missing_capabilities_section(tmp_path: Path) -> None:
    """File with only permission_rules and no capabilities should still parse."""
    cfg = tmp_path / "minimal.yaml"
    cfg.write_text(
        "permission_rules:\n" "  alpha:\n" "    role_required: any\n",
        encoding="utf-8",
    )
    matrix = CapabilityMatrix.from_yaml(cfg)
    assert matrix.get_capability("alpha") is None  # no cap mapping
    rule = matrix.get_rule("alpha")
    assert rule is not None
    assert rule.role_required == "any"


def test_from_yaml_invalid_capability_raises(tmp_path: Path) -> None:
    """Unknown capability name in YAML → ValueError."""
    cfg = tmp_path / "bad.yaml"
    cfg.write_text(
        "capabilities:\n" "  not_a_real_capability: []\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        CapabilityMatrix.from_yaml(cfg)

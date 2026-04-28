"""Unit tests for domain-specific tool schemas and validation.

Sprint 160 — Phase 46 Agent Expert Registry.
"""

import logging

import pytest

from src.integrations.orchestration.experts.domain_tools import (
    ALL_KNOWN_TOOLS,
    DOMAIN_TOOLS,
    TEAM_TOOLS,
    get_domain_tools,
    resolve_tools,
)
from src.integrations.orchestration.experts.registry import (
    AgentExpertDefinition,
    reset_registry,
)
from src.integrations.orchestration.experts.tool_validator import validate_expert_tools


@pytest.fixture(autouse=True)
def _reset():
    reset_registry()
    yield
    reset_registry()


# ------------------------------------------------------------------
# resolve_tools
# ------------------------------------------------------------------


class TestResolveToolsExplicit:
    def test_explicit_list_unchanged(self):
        """Explicit tool names should be returned as-is."""
        tools = ["assess_risk", "search_knowledge"]
        result = resolve_tools(tools, "network")
        assert result == ["assess_risk", "search_knowledge"]

    def test_explicit_with_unknown_tool(self):
        """Unknown tool names should still be returned (no filtering)."""
        tools = ["assess_risk", "future_tool_xyz"]
        result = resolve_tools(tools, "general")
        assert "future_tool_xyz" in result


class TestResolveToolsWildcard:
    def test_wildcard_returns_all(self):
        """["*"] should return all known tools sorted."""
        result = resolve_tools(["*"], "network")
        assert set(result) == ALL_KNOWN_TOOLS
        assert result == sorted(result)

    def test_wildcard_includes_team_tools(self):
        """Wildcard should include team tools."""
        result = resolve_tools(["*"], "general")
        for team_tool in TEAM_TOOLS:
            assert team_tool in result


class TestResolveToolsDomainRef:
    def test_domain_ref_resolves(self):
        """["@domain"] should resolve to domain-specific + team tools."""
        result = resolve_tools(["@domain"], "network")
        # Should include network core tools
        assert "assess_risk" in result
        assert "search_knowledge" in result
        # Should include team tools
        assert "send_team_message" in result
        assert "report_task_result" in result

    def test_domain_ref_varies_by_domain(self):
        """Different domains should resolve to different tool sets."""
        network_tools = resolve_tools(["@domain"], "network")
        database_tools = resolve_tools(["@domain"], "database")
        # database has create_task, network doesn't
        assert "create_task" in database_tools
        assert "create_task" not in network_tools


class TestResolveToolsMixed:
    def test_mixed_domain_and_explicit(self):
        """Mix of @domain + explicit tool should merge without duplicates."""
        result = resolve_tools(["@domain", "extra_custom_tool"], "security")
        assert "assess_risk" in result
        assert "extra_custom_tool" in result
        # No duplicates
        assert len(result) == len(set(result))


# ------------------------------------------------------------------
# get_domain_tools
# ------------------------------------------------------------------


class TestGetDomainTools:
    def test_all_domains_defined(self):
        """All valid domains should have entries in DOMAIN_TOOLS."""
        valid_domains = {"network", "database", "application", "security", "cloud", "general", "custom"}
        for domain in valid_domains:
            tools = get_domain_tools(domain)
            assert isinstance(tools, list)
            assert len(tools) > 0

    def test_unknown_domain_falls_back_to_general(self):
        """Unknown domain should fall back to general tools."""
        unknown = get_domain_tools("nonexistent_domain")
        general = get_domain_tools("general")
        assert unknown == general

    def test_includes_team_tools(self):
        """Every domain should include team tools."""
        for domain in DOMAIN_TOOLS:
            tools = get_domain_tools(domain)
            assert "send_team_message" in tools

    def test_no_duplicates(self):
        """Domain tools should not have duplicates."""
        for domain in DOMAIN_TOOLS:
            tools = get_domain_tools(domain)
            assert len(tools) == len(set(tools))


# ------------------------------------------------------------------
# validate_expert_tools
# ------------------------------------------------------------------


class TestValidateToolsValid:
    def test_valid_tools_no_warnings(self):
        """Known tools should produce no warnings."""
        expert = AgentExpertDefinition(
            name="test",
            display_name="Test",
            display_name_zh="測試",
            description="",
            domain="general",
            capabilities=[],
            model=None,
            max_iterations=5,
            system_prompt="test",
            tools=["assess_risk", "search_knowledge", "send_team_message"],
            enabled=True,
            metadata={},
        )
        warnings = validate_expert_tools(expert)
        assert warnings == []

    def test_wildcard_no_warnings(self):
        """Wildcard token should not produce warnings."""
        expert = AgentExpertDefinition(
            name="test",
            display_name="Test",
            display_name_zh="測試",
            description="",
            domain="general",
            capabilities=[],
            model=None,
            max_iterations=5,
            system_prompt="test",
            tools=["*"],
            enabled=True,
            metadata={},
        )
        warnings = validate_expert_tools(expert)
        assert warnings == []

    def test_domain_ref_no_warnings(self):
        """@domain token should not produce warnings."""
        expert = AgentExpertDefinition(
            name="test",
            display_name="Test",
            display_name_zh="測試",
            description="",
            domain="general",
            capabilities=[],
            model=None,
            max_iterations=5,
            system_prompt="test",
            tools=["@domain"],
            enabled=True,
            metadata={},
        )
        warnings = validate_expert_tools(expert)
        assert warnings == []


class TestValidateToolsWarnsUnknown:
    def test_unknown_tool_warns(self, caplog):
        """Unknown tool names should produce warnings."""
        expert = AgentExpertDefinition(
            name="test_expert",
            display_name="Test",
            display_name_zh="測試",
            description="",
            domain="general",
            capabilities=[],
            model=None,
            max_iterations=5,
            system_prompt="test",
            tools=["assess_risk", "totally_fake_tool"],
            enabled=True,
            metadata={},
        )
        with caplog.at_level(logging.WARNING):
            warnings = validate_expert_tools(expert)
        assert len(warnings) == 1
        assert "totally_fake_tool" in warnings[0]

    def test_empty_tools_no_warnings(self):
        """Empty tools list should produce no warnings."""
        expert = AgentExpertDefinition(
            name="test",
            display_name="Test",
            display_name_zh="測試",
            description="",
            domain="general",
            capabilities=[],
            model=None,
            max_iterations=5,
            system_prompt="test",
            tools=[],
            enabled=True,
            metadata={},
        )
        warnings = validate_expert_tools(expert)
        assert warnings == []


# ------------------------------------------------------------------
# Integration: registry loads with resolved tools
# ------------------------------------------------------------------


class TestRegistryIntegration:
    def test_builtin_experts_tools_resolved(self):
        """Built-in expert YAML tools should be resolved (no @domain tokens remaining)."""
        from src.integrations.orchestration.experts.registry import get_registry

        registry = get_registry()
        for expert in registry.list_all():
            assert "@domain" not in expert.tools
            assert "*" not in expert.tools
            # All tools should be concrete names
            for tool in expert.tools:
                assert isinstance(tool, str)
                assert len(tool) > 0

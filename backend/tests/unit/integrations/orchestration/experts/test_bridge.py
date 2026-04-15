"""Unit tests for the expert registry bridge adapter.

Sprint 159 — Phase 46 Agent Expert Registry.
"""

from pathlib import Path

import pytest

from src.integrations.orchestration.experts.bridge import (
    get_expert_descriptions,
    get_expert_role,
    get_expert_role_names,
)
from src.integrations.orchestration.experts.registry import (
    AgentExpertRegistry,
    reset_registry,
)


@pytest.fixture(autouse=True)
def _reset():
    """Reset the global singleton before each test."""
    reset_registry()
    yield
    reset_registry()


# ------------------------------------------------------------------
# get_expert_role
# ------------------------------------------------------------------


class TestGetExpertRole:
    def test_returns_dict_with_expected_keys(self):
        """get_expert_role() should return a dict compatible with SwarmWorkerExecutor."""
        role = get_expert_role("network_expert")
        assert isinstance(role, dict)
        for key in ("name", "display_name", "system_prompt", "tools", "model", "domain"):
            assert key in role, f"Missing key: {key}"

    def test_returns_correct_values(self):
        """Returned dict should reflect the YAML definition."""
        role = get_expert_role("network_expert")
        assert role["name"] == "Network Expert"
        assert role["display_name"] == "網路專家"
        assert role["domain"] == "network"
        assert "assess_risk" in role["tools"]
        assert len(role["system_prompt"]) > 50

    def test_fallback_to_general(self):
        """Unknown expert names should fall back to the general expert."""
        role = get_expert_role("completely_nonexistent_role")
        assert role["domain"] == "general"
        assert role["name"] == "General Assistant"

    def test_model_field_present(self):
        """model key should be present (None for default experts)."""
        role = get_expert_role("cloud_expert")
        assert "model" in role
        # Built-in experts use model=null → None
        assert role["model"] is None

    def test_capabilities_field_present(self):
        """capabilities key should be present as a list."""
        role = get_expert_role("security_expert")
        assert isinstance(role["capabilities"], list)
        assert len(role["capabilities"]) > 0


# ------------------------------------------------------------------
# get_expert_role_names
# ------------------------------------------------------------------


class TestGetExpertRoleNames:
    def test_includes_all_registry_experts(self):
        """Should include all 6 built-in YAML experts."""
        names = get_expert_role_names()
        expected = {
            "application_expert",
            "cloud_expert",
            "database_expert",
            "general",
            "network_expert",
            "security_expert",
        }
        assert expected.issubset(set(names))

    def test_includes_legacy_worker_roles(self):
        """Should also include legacy worker_roles names (db_expert, app_expert)."""
        names = get_expert_role_names()
        # These exist in worker_roles.py but not as YAML files
        assert "db_expert" in names
        assert "app_expert" in names

    def test_returns_sorted_list(self):
        """Names should be sorted alphabetically."""
        names = get_expert_role_names()
        assert names == sorted(names)

    def test_no_duplicates(self):
        """Should not contain duplicate entries."""
        names = get_expert_role_names()
        assert len(names) == len(set(names))


# ------------------------------------------------------------------
# get_expert_descriptions
# ------------------------------------------------------------------


class TestGetExpertDescriptions:
    def test_returns_formatted_string(self):
        """Should return a non-empty markdown-formatted string."""
        desc = get_expert_descriptions()
        assert isinstance(desc, str)
        assert len(desc) > 100

    def test_includes_all_experts(self):
        """Each registered expert should appear in the descriptions."""
        desc = get_expert_descriptions()
        assert "network_expert" in desc
        assert "database_expert" in desc
        assert "security_expert" in desc
        assert "cloud_expert" in desc
        assert "application_expert" in desc
        assert "general" in desc

    def test_includes_capabilities(self):
        """Expert capabilities should be mentioned."""
        desc = get_expert_descriptions()
        assert "network_troubleshooting" in desc
        assert "cloud_architecture" in desc

    def test_includes_domain(self):
        """Domain info should be mentioned."""
        desc = get_expert_descriptions()
        assert "domain: network" in desc
        assert "domain: security" in desc


# ------------------------------------------------------------------
# Integration: TaskDecomposer compatibility
# ------------------------------------------------------------------


class TestDecomposerCompatibility:
    def test_role_names_usable_in_prompt(self):
        """Role names should be joinable for the decomposer prompt."""
        names = get_expert_role_names()
        roles_text = ", ".join(names)
        assert "network_expert" in roles_text
        assert "general" in roles_text

    def test_descriptions_injectable_in_prompt(self):
        """Expert descriptions should be safe for prompt injection."""
        desc = get_expert_descriptions()
        # Should not contain any prompt-breaking patterns
        assert "```" not in desc
        assert "{" not in desc


# ------------------------------------------------------------------
# Integration: WorkerExecutor compatibility
# ------------------------------------------------------------------


class TestExecutorCompatibility:
    def test_role_dict_get_pattern(self):
        """Executor uses role_def.get('key', default) — verify all patterns work."""
        role = get_expert_role("database_expert")

        # These are the exact .get() patterns used in worker_executor.py
        assert role.get("name", "Worker") != "Worker"
        assert role.get("display_name", "Worker") != "Worker"
        assert role.get("system_prompt", "") != ""
        assert isinstance(role.get("tools", []), list)
        assert len(role.get("tools", [])) > 0

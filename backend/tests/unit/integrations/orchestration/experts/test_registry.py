"""Unit tests for AgentExpertRegistry.

Sprint 158 — Phase 46 Agent Expert Registry.
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from src.integrations.orchestration.experts.exceptions import (
    ExpertNotFoundError,
    ExpertSchemaValidationError,
)
from src.integrations.orchestration.experts.registry import (
    AgentExpertDefinition,
    AgentExpertRegistry,
    reset_registry,
)

# Path to the real built-in definitions
_BUILTIN_DEFS = Path(__file__).resolve().parents[5] / "src" / "integrations" / "orchestration" / "experts" / "definitions"


@pytest.fixture()
def registry():
    """Return a fresh registry pointing at the real built-in definitions."""
    r = AgentExpertRegistry(definitions_dir=_BUILTIN_DEFS)
    r.load()
    return r


@pytest.fixture()
def tmp_defs(tmp_path):
    """Return a temporary definitions directory for isolation tests."""
    return tmp_path


def _write_yaml(directory: Path, name: str, data: dict) -> Path:
    """Helper to write a YAML expert definition to a directory."""
    path = directory / f"{name}.yaml"
    with open(path, "w", encoding="utf-8") as fh:
        yaml.dump(data, fh, allow_unicode=True)
    return path


# ------------------------------------------------------------------
# Test: load built-in definitions
# ------------------------------------------------------------------


class TestLoadBuiltinDefinitions:
    def test_load_builtin_definitions(self, registry):
        """All 6 built-in YAMLs should load without error."""
        names = registry.list_names()
        assert len(names) == 6
        expected = {
            "application_expert",
            "cloud_expert",
            "database_expert",
            "general",
            "network_expert",
            "security_expert",
        }
        assert set(names) == expected

    def test_all_experts_have_required_fields(self, registry):
        """Every loaded expert should have all essential attributes populated."""
        for expert in registry.list_all():
            assert expert.name
            assert expert.display_name
            assert expert.domain
            assert expert.system_prompt


# ------------------------------------------------------------------
# Test: get returns correct expert
# ------------------------------------------------------------------


class TestGetReturnsCorrectExpert:
    def test_get_returns_correct_expert(self, registry):
        """get() should return the exact expert matching the name."""
        expert = registry.get("network_expert")
        assert expert is not None
        assert expert.name == "network_expert"
        assert expert.domain == "network"
        assert expert.display_name == "Network Expert"
        assert expert.display_name_zh == "網路專家"
        assert len(expert.tools) > 0

    def test_get_unknown_returns_none(self, registry):
        """get() should return None for unknown experts."""
        assert registry.get("nonexistent_expert") is None


# ------------------------------------------------------------------
# Test: fallback to worker_roles
# ------------------------------------------------------------------


class TestFallbackToWorkerRole:
    def test_get_unknown_falls_back_to_worker_role(self, registry):
        """get_or_fallback() should fall back to worker_roles.py for known roles."""
        # db_expert exists in worker_roles but not as a YAML (YAML uses database_expert)
        worker_roles_mock = {
            "legacy_role": {
                "name": "Legacy Role",
                "display_name": "舊角色",
                "system_prompt": "You are a legacy role.",
                "tools": ["assess_risk"],
            }
        }
        with patch(
            "src.integrations.orchestration.experts.registry.AgentExpertRegistry._load_worker_role_fallback"
        ) as mock_fallback:
            mock_fallback.return_value = AgentExpertDefinition(
                name="legacy_role",
                display_name="Legacy Role",
                display_name_zh="舊角色",
                description="",
                domain="general",
                capabilities=[],
                model=None,
                max_iterations=5,
                system_prompt="You are a legacy role.",
                tools=["assess_risk"],
                enabled=True,
                metadata={"source": "worker_roles_fallback"},
            )
            result = registry.get_or_fallback("legacy_role")
            assert result.name == "legacy_role"
            assert result.metadata.get("source") == "worker_roles_fallback"


# ------------------------------------------------------------------
# Test: fallback to general
# ------------------------------------------------------------------


class TestFallbackToGeneral:
    def test_get_completely_unknown_falls_back_to_general(self, registry):
        """get_or_fallback() should return general for completely unknown names."""
        result = registry.get_or_fallback("absolutely_unknown_xyz")
        assert result.name == "general"
        assert result.domain == "general"


# ------------------------------------------------------------------
# Test: reload hot-reloads
# ------------------------------------------------------------------


class TestReloadHotReloads:
    def test_reload_hot_reloads(self, tmp_defs):
        """reload() should pick up new definitions added to disk."""
        # Start with one expert
        _write_yaml(tmp_defs, "expert_a", {
            "version": "1.0",
            "name": "expert_a",
            "display_name": "Expert A",
            "domain": "general",
            "system_prompt": "You are expert A.",
            "enabled": True,
        })

        r = AgentExpertRegistry(definitions_dir=tmp_defs)
        r.load()
        assert len(r.list_names()) == 1

        # Add a second expert on disk
        _write_yaml(tmp_defs, "expert_b", {
            "version": "1.0",
            "name": "expert_b",
            "display_name": "Expert B",
            "domain": "custom",
            "system_prompt": "You are expert B.",
            "enabled": True,
        })

        r.reload()
        assert len(r.list_names()) == 2
        assert "expert_b" in r.list_names()


# ------------------------------------------------------------------
# Test: validate rejects missing fields
# ------------------------------------------------------------------


class TestValidateRejectsMissingFields:
    def test_validate_rejects_missing_fields(self, tmp_defs):
        """Loading a YAML missing required fields should raise ExpertSchemaValidationError."""
        _write_yaml(tmp_defs, "bad_expert", {
            "version": "1.0",
            "name": "bad_expert",
            # missing: display_name, domain, system_prompt
        })

        r = AgentExpertRegistry(definitions_dir=tmp_defs)
        with pytest.raises(ExpertSchemaValidationError, match="Missing required fields"):
            r.load()

    def test_validate_rejects_invalid_domain(self, tmp_defs):
        """Loading a YAML with invalid domain should raise ExpertSchemaValidationError."""
        _write_yaml(tmp_defs, "bad_domain", {
            "version": "1.0",
            "name": "bad_domain",
            "display_name": "Bad Domain",
            "domain": "invalid_domain",
            "system_prompt": "test",
        })

        r = AgentExpertRegistry(definitions_dir=tmp_defs)
        with pytest.raises(ExpertSchemaValidationError, match="Invalid domain"):
            r.load()


# ------------------------------------------------------------------
# Test: list by domain
# ------------------------------------------------------------------


class TestListByDomain:
    def test_list_by_domain(self, registry):
        """list_by_domain() should return only experts matching the domain."""
        network_experts = registry.list_by_domain("network")
        assert len(network_experts) == 1
        assert network_experts[0].name == "network_expert"

        general_experts = registry.list_by_domain("general")
        assert len(general_experts) == 1
        assert general_experts[0].name == "general"

    def test_list_by_domain_empty(self, registry):
        """list_by_domain() should return empty list for unused domains."""
        assert registry.list_by_domain("custom") == []


# ------------------------------------------------------------------
# Test: disabled expert not loaded
# ------------------------------------------------------------------


class TestDisabledExpertNotLoaded:
    def test_disabled_expert_not_loaded(self, tmp_defs):
        """Experts with enabled: false should not appear in the registry."""
        _write_yaml(tmp_defs, "active_expert", {
            "version": "1.0",
            "name": "active_expert",
            "display_name": "Active",
            "domain": "general",
            "system_prompt": "Active expert.",
            "enabled": True,
        })
        _write_yaml(tmp_defs, "disabled_expert", {
            "version": "1.0",
            "name": "disabled_expert",
            "display_name": "Disabled",
            "domain": "general",
            "system_prompt": "Disabled expert.",
            "enabled": False,
        })

        r = AgentExpertRegistry(definitions_dir=tmp_defs)
        r.load()
        assert len(r.list_names()) == 1
        assert "active_expert" in r.list_names()
        assert "disabled_expert" not in r.list_names()


# ------------------------------------------------------------------
# Test: to_dict serialization
# ------------------------------------------------------------------


class TestSerialization:
    def test_to_dict(self, registry):
        """to_dict() should return a complete plain dictionary."""
        expert = registry.get("network_expert")
        d = expert.to_dict()
        assert d["name"] == "network_expert"
        assert d["domain"] == "network"
        assert isinstance(d["tools"], list)
        assert isinstance(d["metadata"], dict)

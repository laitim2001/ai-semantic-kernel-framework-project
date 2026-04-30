"""Agent Expert Registry — loads and manages YAML-based expert definitions.

Provides a singleton registry that auto-discovers expert YAML files from the
``definitions/`` directory, validates their schema, and exposes lookup methods
with a three-tier fallback: YAML expert -> worker_roles.py -> general.

Sprint 158 — Phase 46 Agent Expert Registry.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .domain_tools import resolve_tools
from .exceptions import ExpertNotFoundError, ExpertSchemaValidationError
from .tool_validator import validate_expert_tools

logger = logging.getLogger(__name__)

# Directory containing YAML expert definitions (sibling to this module)
_DEFINITIONS_DIR = Path(__file__).parent / "definitions"

# Valid domain values
VALID_DOMAINS = frozenset(
    {"network", "database", "application", "security", "cloud", "general", "custom"}
)

# Required fields in every YAML expert file
_REQUIRED_FIELDS = frozenset(
    {"name", "display_name", "domain", "system_prompt"}
)


@dataclass
class AgentExpertDefinition:
    """Represents a single expert agent definition loaded from YAML."""

    name: str
    display_name: str
    display_name_zh: str
    description: str
    domain: str
    capabilities: list[str]
    model: str | None
    max_iterations: int
    system_prompt: str
    tools: list[str]
    enabled: bool
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "display_name_zh": self.display_name_zh,
            "description": self.description,
            "domain": self.domain,
            "capabilities": list(self.capabilities),
            "model": self.model,
            "max_iterations": self.max_iterations,
            "system_prompt": self.system_prompt,
            "tools": list(self.tools),
            "enabled": self.enabled,
            "metadata": dict(self.metadata),
        }


class AgentExpertRegistry:
    """Registry that loads, validates, and queries expert definitions.

    Usage::

        registry = AgentExpertRegistry()
        registry.load()
        expert = registry.get("network_expert")
    """

    def __init__(self, definitions_dir: Path | None = None) -> None:
        self._definitions_dir = definitions_dir or _DEFINITIONS_DIR
        self._experts: dict[str, AgentExpertDefinition] = {}
        self._loaded = False

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load all YAML expert definitions from the definitions directory."""
        self._experts.clear()

        if not self._definitions_dir.is_dir():
            logger.warning("Definitions directory not found: %s", self._definitions_dir)
            self._loaded = True
            return

        yaml_files = sorted(self._definitions_dir.glob("*.yaml"))
        for yaml_path in yaml_files:
            try:
                expert = self._load_one(yaml_path)
                if expert.enabled:
                    self._experts[expert.name] = expert
                    validate_expert_tools(expert)
                    logger.debug("Loaded expert: %s (domain=%s)", expert.name, expert.domain)
                else:
                    logger.debug("Skipped disabled expert: %s", expert.name)
            except ExpertSchemaValidationError:
                raise
            except Exception as exc:
                raise ExpertSchemaValidationError(
                    str(yaml_path), f"Failed to parse YAML: {exc}"
                ) from exc

        self._loaded = True
        logger.info(
            "Expert registry loaded: %d experts from %s",
            len(self._experts),
            self._definitions_dir,
        )

    def reload(self) -> None:
        """Hot-reload all definitions from disk."""
        logger.info("Reloading expert registry...")
        self.load()

    def _load_one(self, yaml_path: Path) -> AgentExpertDefinition:
        """Load and validate a single YAML file into an ``AgentExpertDefinition``."""
        with open(yaml_path, "r", encoding="utf-8") as fh:
            data: dict[str, Any] = yaml.safe_load(fh)

        if not isinstance(data, dict):
            raise ExpertSchemaValidationError(str(yaml_path), "Root must be a mapping")

        self._validate(data, yaml_path)

        return AgentExpertDefinition(
            name=data["name"],
            display_name=data["display_name"],
            display_name_zh=data.get("display_name_zh", data["display_name"]),
            description=data.get("description", ""),
            domain=data["domain"],
            capabilities=data.get("capabilities", []),
            model=data.get("model"),
            max_iterations=data.get("max_iterations", 5),
            system_prompt=data["system_prompt"].strip(),
            tools=resolve_tools(data.get("tools", ["*"]), data["domain"]),
            enabled=data.get("enabled", True),
            metadata=data.get("metadata", {}),
        )

    def _validate(self, data: dict[str, Any], yaml_path: Path) -> None:
        """Validate required fields and domain value."""
        missing = _REQUIRED_FIELDS - set(data.keys())
        if missing:
            raise ExpertSchemaValidationError(
                str(yaml_path), f"Missing required fields: {sorted(missing)}"
            )

        domain = data.get("domain", "")
        if domain not in VALID_DOMAINS:
            raise ExpertSchemaValidationError(
                str(yaml_path),
                f"Invalid domain '{domain}'. Must be one of: {sorted(VALID_DOMAINS)}",
            )

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, name: str) -> AgentExpertDefinition | None:
        """Return an expert by name, or ``None`` if not found."""
        self._ensure_loaded()
        return self._experts.get(name)

    def get_or_fallback(self, name: str) -> AgentExpertDefinition:
        """Three-tier fallback: YAML expert -> worker_roles.py -> general.

        1. Look up in loaded YAML experts.
        2. Fall back to ``worker_roles.py`` and wrap as ``AgentExpertDefinition``.
        3. Fall back to the ``general`` expert definition.

        Raises ``ExpertNotFoundError`` only if even ``general`` is missing.
        """
        self._ensure_loaded()

        # Tier 1: YAML expert
        expert = self._experts.get(name)
        if expert is not None:
            return expert

        # Tier 2: worker_roles.py fallback
        fallback = self._load_worker_role_fallback(name)
        if fallback is not None:
            return fallback

        # Tier 3: general expert
        general = self._experts.get("general")
        if general is not None:
            return general

        raise ExpertNotFoundError(name)

    def _load_worker_role_fallback(self, name: str) -> AgentExpertDefinition | None:
        """Attempt to load a role from ``worker_roles.py`` as fallback."""
        try:
            from ..swarm.worker_roles import WORKER_ROLES
        except ImportError:
            return None

        role = WORKER_ROLES.get(name)
        if role is None:
            return None

        return AgentExpertDefinition(
            name=name,
            display_name=role.get("name", name),
            display_name_zh=role.get("display_name", role.get("name", name)),
            description="",
            domain="general",
            capabilities=[],
            model=None,
            max_iterations=5,
            system_prompt=role.get("system_prompt", ""),
            tools=role.get("tools", ["*"]),
            enabled=True,
            metadata={"source": "worker_roles_fallback"},
        )

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def list_names(self) -> list[str]:
        """Return sorted list of all loaded expert names."""
        self._ensure_loaded()
        return sorted(self._experts.keys())

    def list_all(self) -> list[AgentExpertDefinition]:
        """Return all loaded expert definitions."""
        self._ensure_loaded()
        return list(self._experts.values())

    def list_by_domain(self, domain: str) -> list[AgentExpertDefinition]:
        """Return experts filtered by domain."""
        self._ensure_loaded()
        return [e for e in self._experts.values() if e.domain == domain]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        """Auto-load on first access if not yet loaded."""
        if not self._loaded:
            self.load()

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def __len__(self) -> int:
        self._ensure_loaded()
        return len(self._experts)

    def __repr__(self) -> str:
        return f"<AgentExpertRegistry experts={len(self._experts)} loaded={self._loaded}>"


# ------------------------------------------------------------------
# Singleton factory
# ------------------------------------------------------------------

_registry_instance: AgentExpertRegistry | None = None


def get_registry() -> AgentExpertRegistry:
    """Return the global singleton registry instance (auto-loads on first call)."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = AgentExpertRegistry()
        _registry_instance.load()
    return _registry_instance


def reset_registry() -> None:
    """Reset the singleton (for testing only)."""
    global _registry_instance
    _registry_instance = None

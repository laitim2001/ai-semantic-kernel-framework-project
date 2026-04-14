"""Agent Expert Registry — YAML-based expert definition system.

Sprint 158 — Phase 46 Agent Expert Registry.
"""

from .exceptions import (
    ExpertDefinitionError,
    ExpertNotFoundError,
    ExpertSchemaValidationError,
)
from .bridge import get_expert_descriptions, get_expert_role, get_expert_role_names
from .domain_tools import get_domain_tools, resolve_tools
from .registry import AgentExpertDefinition, AgentExpertRegistry, get_registry
from .tool_validator import validate_expert_tools

__all__ = [
    "AgentExpertDefinition",
    "AgentExpertRegistry",
    "ExpertDefinitionError",
    "ExpertNotFoundError",
    "ExpertSchemaValidationError",
    "get_domain_tools",
    "get_expert_descriptions",
    "get_expert_role",
    "get_expert_role_names",
    "get_registry",
    "resolve_tools",
    "validate_expert_tools",
]

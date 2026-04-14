"""Tool validation for expert YAML definitions.

Validates that tool names referenced in expert definitions are known
tools.  Unknown tools emit a warning but do **not** block loading —
this allows forward-referencing tools that will be registered later.

Sprint 160 — Phase 46 Agent Expert Registry.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .domain_tools import ALL_KNOWN_TOOLS

if TYPE_CHECKING:
    from .registry import AgentExpertDefinition

logger = logging.getLogger(__name__)


def validate_expert_tools(expert: "AgentExpertDefinition") -> list[str]:
    """Validate tool names in an expert definition.

    Returns a list of warning messages (empty if all tools are valid).
    Does **not** raise — unknown tools are logged as warnings only.
    """
    warnings: list[str] = []

    # Skip validation for wildcard or domain-reference tokens
    if not expert.tools:
        return warnings

    for tool in expert.tools:
        if tool in ("*", "@domain"):
            continue
        if tool not in ALL_KNOWN_TOOLS:
            msg = (
                f"Expert '{expert.name}': unknown tool '{tool}' "
                f"(not in ALL_KNOWN_TOOLS). It may be registered at runtime."
            )
            warnings.append(msg)
            logger.warning(msg)

    return warnings

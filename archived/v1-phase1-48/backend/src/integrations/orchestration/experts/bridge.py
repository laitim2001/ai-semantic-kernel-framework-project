"""Bridge adapter — drop-in replacements for worker_roles functions.

Provides the same API surface as ``worker_roles.get_role`` /
``get_role_names`` but queries the AgentExpertRegistry first, falling
back to worker_roles for backward compatibility.

Sprint 159 — Phase 46 Agent Expert Registry.
"""

import logging
from typing import Any

from .registry import get_registry

logger = logging.getLogger(__name__)


def get_expert_role(name: str) -> dict[str, Any]:
    """Drop-in replacement for ``worker_roles.get_role()``.

    Looks up *name* in the expert registry (three-tier fallback:
    YAML expert -> worker_roles -> general) and returns a dict with
    the keys expected by ``SwarmWorkerExecutor``.

    Returned keys::

        name, display_name, system_prompt, tools,
        model, capabilities, max_iterations, domain
    """
    registry = get_registry()
    expert = registry.get_or_fallback(name)

    return {
        "name": expert.display_name,
        "display_name": expert.display_name_zh,
        "system_prompt": expert.system_prompt,
        "tools": expert.tools,
        "model": expert.model,
        "capabilities": expert.capabilities,
        "max_iterations": expert.max_iterations,
        "domain": expert.domain,
    }


def get_expert_role_names() -> list[str]:
    """Drop-in replacement for ``worker_roles.get_role_names()``.

    Returns the union of registry expert names and legacy worker_roles
    names (deduplicated, sorted).
    """
    registry = get_registry()
    names = set(registry.list_names())

    # Merge legacy worker_roles names for backward compatibility
    try:
        from ...swarm.worker_roles import get_role_names as _legacy_names

        names.update(_legacy_names())
    except ImportError:
        pass

    return sorted(names)


def get_expert_descriptions() -> str:
    """Return a formatted block describing every loaded expert.

    Designed for injection into the TaskDecomposer LLM prompt so the
    model can make better role-assignment decisions.
    """
    registry = get_registry()
    lines: list[str] = []

    for expert in registry.list_all():
        caps = ", ".join(expert.capabilities) if expert.capabilities else "general"
        lines.append(
            f"- **{expert.name}** ({expert.display_name_zh}): "
            f"{expert.description}  "
            f"[domain: {expert.domain}, capabilities: {caps}]"
        )

    return "\n".join(sorted(lines))

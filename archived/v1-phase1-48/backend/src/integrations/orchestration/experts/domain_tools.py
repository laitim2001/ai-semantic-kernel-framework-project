"""Domain-specific tool mappings for the Agent Expert Registry.

Each expert domain has a curated set of *core* tools (available today)
and *specialized* tools (reserved for future domain-specific MCP/tool
extensions).  Shared team-collaboration tools are appended automatically.

Sprint 160 — Phase 46 Agent Expert Registry.
"""

from __future__ import annotations

TEAM_TOOLS: list[str] = [
    "send_team_message",
    "check_my_inbox",
    "read_team_messages",
    "view_team_status",
    "claim_next_task",
    "report_task_result",
]

DOMAIN_TOOLS: dict[str, dict[str, list[str]]] = {
    "network": {
        "core": ["assess_risk", "search_knowledge", "search_memory"],
        "specialized": [],  # future: ping, traceroute, nslookup
    },
    "database": {
        "core": ["assess_risk", "search_knowledge", "search_memory", "create_task"],
        "specialized": [],  # future: query_db, explain_plan
    },
    "application": {
        "core": ["assess_risk", "search_knowledge", "create_task", "search_memory"],
        "specialized": [],  # future: check_logs, restart_service
    },
    "security": {
        "core": ["assess_risk", "search_knowledge"],
        "specialized": [],  # future: scan_vulnerability, check_compliance
    },
    "cloud": {
        "core": ["assess_risk", "search_knowledge", "search_memory", "create_task"],
        "specialized": [],  # future: check_cost, list_resources
    },
    "general": {
        "core": ["assess_risk", "search_memory", "search_knowledge"],
        "specialized": [],
    },
    "custom": {
        "core": ["assess_risk", "search_knowledge"],
        "specialized": [],
    },
}

# Aggregated set of every tool name mentioned anywhere
ALL_KNOWN_TOOLS: frozenset[str] = frozenset(
    tool
    for domain_def in DOMAIN_TOOLS.values()
    for tool_list in domain_def.values()
    for tool in tool_list
) | frozenset(TEAM_TOOLS)


def get_domain_tools(domain: str) -> list[str]:
    """Return the full tool list for *domain* (core + specialized + team).

    Unknown domains fall back to the ``general`` definition.
    """
    entry = DOMAIN_TOOLS.get(domain, DOMAIN_TOOLS["general"])
    tools = list(entry["core"]) + list(entry["specialized"]) + list(TEAM_TOOLS)
    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for t in tools:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result


def resolve_tools(tools: list[str], domain: str) -> list[str]:
    """Resolve a YAML ``tools`` list into concrete tool names.

    Special tokens
    --------------
    * ``["*"]``        — all known tools
    * ``["@domain"]``  — domain core + specialized + team tools
    * explicit names   — returned unchanged

    Tokens can be mixed: ``["@domain", "extra_tool"]``
    """
    resolved: list[str] = []

    for item in tools:
        if item == "*":
            return sorted(ALL_KNOWN_TOOLS)
        elif item == "@domain":
            resolved.extend(get_domain_tools(domain))
        else:
            resolved.append(item)

    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for t in resolved:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result

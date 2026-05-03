"""
File: backend/src/agent_harness/guardrails/tool/capability_matrix.py
Purpose: Capability → tool list mapping + per-tool PermissionRule registry.
Category: 範疇 9 (Guardrails & Safety)
Scope: Phase 53.3 / Sprint 53.3 Day 3 (US-4)

Description:
    Two-tier permission model:
      1. Capability enum (≥ 8 distinct capabilities) — coarse-grained
         authorization scope (e.g. READ_KB, EXECUTE_SHELL).
      2. PermissionRule per tool name — fine-grained policy (role required,
         tenant scope, max calls per session, requires approval).

    Aligned with Anthropic's permission/reasoning separation principle
    (per 01-eleven-categories-spec.md §範疇 9):
        Agent decides "what to attempt" (LLM reasoning layer)
        Tool system decides "what's allowed" (this matrix + ToolGuardrail)
    The two layers stay architecturally independent.

    `from_yaml(path)` loads declarative configuration:
        capabilities:
          read_kb: [search_kb, get_doc]
          ...
        permission_rules:
          search_kb:
            role_required: any
            ...

    Tool → Capability resolution uses the inverse map (built once on
    construction); O(1) lookup at request time keeps SLO `tool guardrail
    p95 < 50ms per call` easily achievable.

Key Components:
    - Capability(Enum): 8 baseline capabilities
    - PermissionRule(dataclass): role / scope / max_calls / requires_approval
    - CapabilityMatrix: get_capability / get_rule / from_yaml

Owner: 01-eleven-categories-spec.md §範疇 9
Single-source: 17.md §1.1 (no Capability dataclass yet — first introduced 53.3)

Created: 2026-05-03 (Sprint 53.3 Day 3)

Modification History (newest-first):
    - 2026-05-03: Initial creation (Sprint 53.3 US-4)

Related:
    - guardrails/tool/tool_guardrail.py — consumes this matrix
    - backend/config/capability_matrix.yaml — declarative config
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import yaml  # type: ignore[import-untyped, unused-ignore]


class Capability(Enum):
    """Coarse-grained authorization scope — 8 baseline capabilities.

    Add new capabilities here as new business domains land (Phase 55+);
    existing values are stable for forward-compat.
    """

    READ_KB = "read_kb"
    WRITE_KB = "write_kb"
    EXECUTE_QUERY = "execute_query"
    MODIFY_TICKET = "modify_ticket"
    SEND_NOTIFICATION = "send_notification"
    READ_PII = "read_pii"
    EXECUTE_SHELL = "execute_shell"
    CALL_EXTERNAL_API = "call_external_api"


@dataclass(frozen=True)
class PermissionRule:
    """Per-tool authorization policy.

    Fields:
        role_required: required user role; "any" disables role check
        tenant_scope: "any" or "own_only" (caller's tenant only)
        max_calls_per_session: hard cap (0 = unlimited)
        requires_approval: trigger HITL stage 3 (53.4 wires Teams/UI)
    """

    role_required: str = "any"
    tenant_scope: str = "any"
    max_calls_per_session: int = 0
    requires_approval: bool = False


class CapabilityMatrix:
    """Maps Capability ↔ tools + per-tool PermissionRule lookup.

    Construct directly with explicit dicts, or load from YAML config:

        matrix = CapabilityMatrix.from_yaml("backend/config/capability_matrix.yaml")
        rule = matrix.get_rule("delete_doc")
        cap = matrix.get_capability("search_kb")
    """

    def __init__(
        self,
        *,
        capability_to_tools: dict[Capability, list[str]],
        permission_rules: dict[str, PermissionRule],
    ) -> None:
        self._capability_to_tools = dict(capability_to_tools)
        self._permission_rules = dict(permission_rules)
        # Inverse map: tool_name → capability (built once, O(1) lookup)
        self._tool_to_capability: dict[str, Capability] = {}
        for cap, tools in capability_to_tools.items():
            for tool_name in tools:
                self._tool_to_capability[tool_name] = cap

    def get_capability(self, tool_name: str) -> Capability | None:
        """Returns the capability owning this tool, or None if unmapped."""
        return self._tool_to_capability.get(tool_name)

    def get_rule(self, tool_name: str) -> PermissionRule | None:
        """Returns the per-tool permission rule, or None if no rule defined.

        None means "tool not registered" — ToolGuardrail interprets as
        BLOCK with reason 'unknown tool'.
        """
        return self._permission_rules.get(tool_name)

    def list_tools_for(self, cap: Capability) -> list[str]:
        """List all tools mapped to a given capability."""
        return list(self._capability_to_tools.get(cap, []))

    @classmethod
    def from_yaml(cls, path: str | Path) -> "CapabilityMatrix":
        """Load matrix from a YAML config file.

        Schema:
            capabilities:
              <capability_name>: [tool_a, tool_b, ...]
            permission_rules:
              <tool_name>:
                role_required: any | <role>
                tenant_scope: any | own_only
                max_calls_per_session: <int>
                requires_approval: <bool>
        """
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        cap_to_tools: dict[Capability, list[str]] = {}
        for cap_name, tools in (data.get("capabilities") or {}).items():
            cap = Capability(cap_name)
            cap_to_tools[cap] = list(tools or [])

        rules: dict[str, PermissionRule] = {}
        for tool_name, raw_rule in (data.get("permission_rules") or {}).items():
            rules[tool_name] = PermissionRule(
                role_required=raw_rule.get("role_required", "any"),
                tenant_scope=raw_rule.get("tenant_scope", "any"),
                max_calls_per_session=int(raw_rule.get("max_calls_per_session", 0)),
                requires_approval=bool(raw_rule.get("requires_approval", False)),
            )

        return cls(capability_to_tools=cap_to_tools, permission_rules=rules)

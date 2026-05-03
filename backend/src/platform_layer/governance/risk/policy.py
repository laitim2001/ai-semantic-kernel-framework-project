"""
File: backend/src/platform_layer/governance/risk/policy.py
Purpose: RiskPolicy ABC + DefaultRiskPolicy (YAML-driven) for tool/operation risk evaluation.
Category: Platform / Governance / Risk
Scope: Phase 53 / Sprint 53.4

Description:
    Per Sprint 53.4 plan §US-1, this module provides the RiskPolicy ABC + a
    default YAML-driven implementation that evaluates the risk level of a
    tool call given the tool name, arguments, and tenant context.

    RiskLevel enum is single-sourced at `_contracts/hitl.py` per 17.md §1 —
    we import it here, NOT redefine.

    Cat 9 ToolGuardrail consults RiskPolicy when deciding stage escalation
    (Stage 3 ESCALATE → HITLManager).

Key Components:
    - RiskPolicy: ABC with `evaluate(tool_name, arguments, tenant_id) -> RiskLevel`
    - DefaultRiskPolicy: YAML-config-driven impl with per-tenant overlays

Created: 2026-05-03 (Sprint 53.4 Day 1)
Last Modified: 2026-05-03

Modification History:
    - 2026-05-03: Initial creation (Sprint 53.4) — V1 risk concepts as inspiration;
                  new V2 ABC structure

Related:
    - 01-eleven-categories-spec.md §HITL Centralization
    - 17-cross-category-interfaces.md §1 (RiskLevel single-source)
    - sprint-53-4-plan.md §US-1
"""

from __future__ import annotations

import fnmatch
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from uuid import UUID

import yaml  # type: ignore[import-untyped, unused-ignore]

from agent_harness._contracts.hitl import RiskLevel

# === DefaultRiskPolicy YAML-driven evaluation ===
# Why: V1 had hybrid orchestrator-coupled risk engine (560 lines); V2 simplifies
# to YAML + ABC for testability + per-tenant overlay support. Tool patterns
# matched in priority: critical > high > medium > low.


class RiskPolicy(ABC):
    """ABC for risk evaluation policies; consumed by Cat 9 ToolGuardrail."""

    @abstractmethod
    def evaluate(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        tenant_id: UUID,
    ) -> RiskLevel:
        """Return the risk level for a tool call in a tenant context."""
        ...


class DefaultRiskPolicy(RiskPolicy):
    """YAML-config-driven default risk policy with per-tenant overlays.

    Config schema (risk_policy.yaml):
        version: "1.0"
        default_risk: medium
        tool_overrides:
          - pattern: "salesforce_*"
            risk: high
        per_tenant_overlays:
          tenant_uuid_or_alias:
            "delete_*": critical
    """

    _RISK_PRIORITY = {
        RiskLevel.CRITICAL: 4,
        RiskLevel.HIGH: 3,
        RiskLevel.MEDIUM: 2,
        RiskLevel.LOW: 1,
    }

    def __init__(self, config_path: str | Path) -> None:
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"risk policy config not found: {path}")
        with path.open("r", encoding="utf-8") as f:
            self._config: dict[str, Any] = yaml.safe_load(f) or {}

        default_str = str(self._config.get("default_risk", "medium")).upper()
        self._default = RiskLevel[default_str]

        self._global_overrides: list[tuple[str, RiskLevel]] = []
        for entry in self._config.get("tool_overrides", []) or []:
            pattern = entry.get("pattern")
            risk_str = str(entry.get("risk", "medium")).upper()
            if pattern:
                self._global_overrides.append((pattern, RiskLevel[risk_str]))

        self._tenant_overlays: dict[str, dict[str, RiskLevel]] = {}
        for tenant_key, overlay in (self._config.get("per_tenant_overlays", {}) or {}).items():
            mapped: dict[str, RiskLevel] = {}
            for pattern, risk_str in overlay.items():
                mapped[pattern] = RiskLevel[str(risk_str).upper()]
            self._tenant_overlays[str(tenant_key)] = mapped

    def evaluate(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        tenant_id: UUID,
    ) -> RiskLevel:
        """Evaluate risk: per-tenant overlay overrides global; highest match wins."""
        candidates: list[RiskLevel] = []

        tenant_key = str(tenant_id)
        overlay = self._tenant_overlays.get(tenant_key, {})
        for pattern, risk in overlay.items():
            if fnmatch.fnmatchcase(tool_name, pattern):
                candidates.append(risk)

        for pattern, risk in self._global_overrides:
            if fnmatch.fnmatchcase(tool_name, pattern):
                candidates.append(risk)

        if not candidates:
            return self._default

        return max(candidates, key=lambda r: self._RISK_PRIORITY[r])

"""
File: backend/src/platform_layer/tenant/plans.py
Purpose: PlanLoader — reads tenant_plans.yml + exposes typed Plan objects.
Category: Phase 56 SaaS Stage 1 (platform_layer.tenant)
Scope: Sprint 56.1 / Day 2 / US-2 Plan Template Enforcement

Description:
    Loads `config/tenant_plans.yml` (single-source plan registry) into
    typed Pydantic models. Provides synchronous `get_plan(name)` lookup
    with in-memory cache (loaded once, idempotent reload via `reload()`).

    Phase 56.1 ships only `enterprise` tier per user decision 2026-05-05.
    `PlanNotFoundError` raised for unknown plan name.

Key Components:
    - PlanQuota / PlanFeatures / Plan: Pydantic models
    - PlanLoader: cached YAML loader with `get_plan()` + `reload()`
    - PlanNotFoundError: raised when name absent from registry
    - load_default_plans() / get_plan_loader(): module-level singleton
      accessor used by FastAPI Depends + tests reset hook (per
      .claude/rules/testing.md §Module-level Singleton Reset Pattern)

Modification History (newest-first):
    - 2026-05-06: Initial creation (Sprint 56.1 Day 2 / US-2)

Related:
    - config/tenant_plans.yml — single-source registry
    - sprint-56-1-plan.md §Plan Template (L358-378)
    - 15-saas-readiness.md §Tenant 配置範本
    - quota.py — consumes PlanQuota.tokens_per_day
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped, unused-ignore]
from pydantic import BaseModel, Field


class PlanQuota(BaseModel):
    """Per-day quota caps for a plan tier."""

    tokens_per_day: int = Field(..., gt=0)
    cost_usd_per_day: float = Field(..., gt=0)
    sessions_per_user_concurrent: int = Field(..., gt=0)
    api_keys_max: int = Field(..., gt=0)


class PlanFeatures(BaseModel):
    """Feature toggles attached to a plan tier."""

    verification: bool
    thinking: bool
    subagents: bool
    mcp_servers: str  # "*" means all; future tiers may use list
    custom_tools: bool
    dedicated_support: bool


class Plan(BaseModel):
    """Typed plan record (one tier)."""

    name: str
    quota: PlanQuota
    features: PlanFeatures


class PlanNotFoundError(KeyError):
    """Raised when a plan name is not present in tenant_plans.yml."""


def _resolve_default_path() -> Path:
    # backend/src/platform_layer/tenant/plans.py
    #   parents[0]: tenant/  parents[1]: platform_layer/
    #   parents[2]: src/     parents[3]: backend/
    return Path(__file__).resolve().parents[3] / "config" / "tenant_plans.yml"


class PlanLoader:
    """YAML-backed plan registry with idempotent in-memory cache."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._config_path = config_path or _resolve_default_path()
        self._plans: dict[str, Plan] = {}
        self._loaded = False

    def _load(self) -> None:
        if not self._config_path.exists():
            raise FileNotFoundError(f"tenant_plans.yml not found at {self._config_path}")
        raw: Any = yaml.safe_load(self._config_path.read_text(encoding="utf-8"))
        plans_dict = (raw or {}).get("plans", {})
        if not isinstance(plans_dict, dict) or not plans_dict:
            raise ValueError(f"tenant_plans.yml at {self._config_path} has no 'plans' map")
        out: dict[str, Plan] = {}
        for name, body in plans_dict.items():
            quota = PlanQuota.model_validate(body.get("quota", {}))
            features = PlanFeatures.model_validate(body.get("features", {}))
            out[name] = Plan(name=name, quota=quota, features=features)
        self._plans = out
        self._loaded = True

    def get_plan(self, name: str = "enterprise") -> Plan:
        """Return Plan record by tier name; load on first call."""
        if not self._loaded:
            self._load()
        try:
            return self._plans[name]
        except KeyError as exc:
            raise PlanNotFoundError(
                f"plan '{name}' not in registry; known: {sorted(self._plans)}"
            ) from exc

    def reload(self) -> None:
        """Force re-read of YAML (test fixture / hot-reload hook)."""
        self._loaded = False
        self._plans = {}
        self._load()

    @property
    def known_plans(self) -> list[str]:
        if not self._loaded:
            self._load()
        return sorted(self._plans)


# Module-level singleton — reset hook per testing.md §Module-level Singleton Reset Pattern.
_loader: PlanLoader | None = None


def get_plan_loader() -> PlanLoader:
    """FastAPI Depends-friendly accessor + tests reset target."""
    global _loader
    if _loader is None:
        _loader = PlanLoader()
    return _loader


def reset_plan_loader() -> None:
    """Test isolation hook (per testing.md §Module-level Singleton Reset Pattern)."""
    global _loader
    _loader = None

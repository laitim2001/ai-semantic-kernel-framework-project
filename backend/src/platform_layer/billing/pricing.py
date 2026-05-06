"""
File: backend/src/platform_layer/billing/pricing.py
Purpose: PricingLoader — load LLM + tool pricing from yaml config.
Category: Phase 56 SaaS Stage 1 (platform_layer.billing)
Scope: Sprint 56.3 / Day 2 / US-3 Cost Ledger.

Description:
    Reads `config/llm_pricing.yml` (or path passed at construction) into
    typed dataclasses. CostLedgerService (US-3) consumes
    `get_llm_pricing(provider, model)` and `get_tool_pricing(tool_name)` to
    compute `unit_cost_usd` + `total_cost_usd` for ledger entries.

    Pricing is config-driven (not LLM SDK API calls) — this maintains
    LLM Provider Neutrality (no `import openai` / `import anthropic`).

Key Components:
    - LLMPricing: dataclass (input / output / cached_input per million)
    - ToolPricing: dataclass (per_call USD)
    - PricingLoader: yaml parser + accessors
    - set_pricing_loader / get_pricing_loader / reset_pricing_loader: hooks

Created: 2026-05-06 (Sprint 56.3 Day 2)

Modification History:
    - 2026-05-06: Initial creation (Sprint 56.3 Day 2 / US-3)

Related:
    - sprint-56-3-plan.md §US-3
    - 15-saas-readiness.md §Billing - Cost Ledger 整合
    - config/llm_pricing.yml
    - .claude/rules/llm-provider-neutrality.md
    - .claude/rules/testing.md §Module-level Singleton Reset Pattern
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml  # type: ignore[import-untyped, unused-ignore]


@dataclass(frozen=True)
class LLMPricing:
    """USD per 1M tokens — input / output / cached_input split."""

    input_per_million: float
    output_per_million: float
    cached_input_per_million: float


@dataclass(frozen=True)
class ToolPricing:
    """USD per tool call."""

    per_call: float


class PricingLoader:
    """Load + lookup LLM + tool pricing from yaml.

    Pattern: instance owns parsed dict; lookups are sync (yaml is in-memory
    after `load_from_yaml`). Cost ledger callers go via FastAPI Depends —
    process-wide singleton + reset hook for test isolation.
    """

    def __init__(self) -> None:
        self._llm: dict[str, dict[str, LLMPricing]] = {}
        self._tools_default: ToolPricing = ToolPricing(per_call=0.0)
        self._tools_overrides: dict[str, ToolPricing] = {}
        self._loaded_path: Path | None = None
        self.last_updated: str = ""

    def load_from_yaml(self, path: str | Path) -> None:
        """Load pricing config from yaml file.

        Raises FileNotFoundError if path missing; ValueError if yaml malformed
        or required sections absent.
        """
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"pricing yaml not found: {p}")
        with p.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict):
            raise ValueError(f"pricing yaml root must be a mapping: {p}")

        self.last_updated = str(data.get("last_updated", ""))

        # LLM pricing
        providers = data.get("providers", {})
        if not isinstance(providers, dict):
            raise ValueError("pricing yaml 'providers' must be a mapping")
        for provider, models in providers.items():
            if not isinstance(models, dict):
                continue
            self._llm[provider] = {}
            for model, fields in models.items():
                if not isinstance(fields, dict):
                    continue
                self._llm[provider][model] = LLMPricing(
                    input_per_million=float(fields.get("input_per_million", 0.0)),
                    output_per_million=float(fields.get("output_per_million", 0.0)),
                    cached_input_per_million=float(fields.get("cached_input_per_million", 0.0)),
                )

        # Tool pricing
        tools = data.get("tools", {})
        if isinstance(tools, dict):
            self._tools_default = ToolPricing(per_call=float(tools.get("default_per_call", 0.0)))
            for tool_name, value in tools.items():
                if tool_name == "default_per_call":
                    continue
                if isinstance(value, (int, float)):
                    self._tools_overrides[tool_name] = ToolPricing(per_call=float(value))

        self._loaded_path = p

    def get_llm_pricing(self, provider: str, model: str) -> LLMPricing | None:
        """Return per-million pricing for (provider, model);None if unknown."""
        return self._llm.get(provider, {}).get(model)

    def get_tool_pricing(self, tool_name: str) -> ToolPricing:
        """Return per-call pricing for tool;defaults to default_per_call."""
        return self._tools_overrides.get(tool_name, self._tools_default)


# Module-level singleton — reset hook per testing.md §Module-level Singleton Reset Pattern.
_loader: PricingLoader | None = None


def get_pricing_loader() -> PricingLoader:
    """FastAPI Depends accessor (strict — raises if uninitialised)."""
    if _loader is None:
        raise RuntimeError(
            "PricingLoader not initialised; call set_pricing_loader() at "
            "app startup or in test fixture"
        )
    return _loader


def maybe_get_pricing_loader() -> PricingLoader | None:
    """FastAPI Depends accessor (lenient — returns None if uninitialised)."""
    return _loader


def set_pricing_loader(loader: PricingLoader | None) -> None:
    """Install singleton (app startup or tests fixture)."""
    global _loader
    _loader = loader


def reset_pricing_loader() -> None:
    """Test isolation hook (per testing.md §Module-level Singleton Reset Pattern)."""
    global _loader
    _loader = None


__all__ = [
    "LLMPricing",
    "PricingLoader",
    "ToolPricing",
    "get_pricing_loader",
    "maybe_get_pricing_loader",
    "reset_pricing_loader",
    "set_pricing_loader",
]

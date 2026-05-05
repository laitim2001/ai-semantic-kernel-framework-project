"""PlanLoader tests (Sprint 56.1 Day 2 / US-2)."""

from __future__ import annotations

import pytest

from platform_layer.tenant.plans import (
    Plan,
    PlanLoader,
    PlanNotFoundError,
    get_plan_loader,
    reset_plan_loader,
)


def test_plan_loader_loads_enterprise_tier() -> None:
    """Default-path loader returns enterprise tier with quota + features."""
    reset_plan_loader()
    loader = PlanLoader()
    plan = loader.get_plan("enterprise")

    assert isinstance(plan, Plan)
    assert plan.name == "enterprise"
    assert plan.quota.tokens_per_day == 10_000_000
    assert plan.quota.cost_usd_per_day == 500
    assert plan.features.verification is True
    assert plan.features.thinking is True
    assert plan.features.mcp_servers == "*"


def test_plan_loader_unknown_plan_raises() -> None:
    """get_plan('basic') raises PlanNotFoundError until Stage 2 ships it."""
    reset_plan_loader()
    loader = PlanLoader()

    with pytest.raises(PlanNotFoundError):
        loader.get_plan("basic")


def test_plan_loader_singleton_returns_same_instance() -> None:
    """get_plan_loader() caches loader between calls."""
    reset_plan_loader()
    a = get_plan_loader()
    b = get_plan_loader()
    assert a is b


def test_plan_loader_reload_idempotent() -> None:
    """reload() re-reads YAML without state divergence."""
    reset_plan_loader()
    loader = PlanLoader()
    p1 = loader.get_plan("enterprise")
    loader.reload()
    p2 = loader.get_plan("enterprise")
    assert p1 == p2

"""
File: backend/tests/unit/agent_harness/subagent/test_budget.py
Purpose: Unit tests for BudgetEnforcer (Cat 11 budget guards).
Category: Tests / 範疇 11 (Subagent Orchestration)
Scope: Sprint 54.2 US-1

Created: 2026-05-04 (Sprint 54.2)
"""

from __future__ import annotations

import pytest

from agent_harness._contracts import SubagentBudget
from agent_harness.subagent.budget import BudgetEnforcer
from agent_harness.subagent.exceptions import BudgetExceededError


@pytest.fixture
def enforcer() -> BudgetEnforcer:
    return BudgetEnforcer()


@pytest.fixture
def budget() -> SubagentBudget:
    # Defaults: max_tokens=10_000, max_duration_s=300, max_concurrent=5,
    # max_subagent_depth=3.
    return SubagentBudget()


# === check_concurrent ========================================================


def test_check_concurrent_pass_under_cap(enforcer: BudgetEnforcer, budget: SubagentBudget) -> None:
    """active < max_concurrent → no raise."""
    enforcer.check_concurrent(active_count=4, budget=budget)  # 4 < 5


def test_check_concurrent_exceeds_raises(enforcer: BudgetEnforcer, budget: SubagentBudget) -> None:
    """active >= max_concurrent → BudgetExceededError."""
    with pytest.raises(BudgetExceededError, match="max_concurrent=5"):
        enforcer.check_concurrent(active_count=5, budget=budget)  # equal triggers


# === check_tokens ============================================================


def test_check_tokens_pass_under_cap(enforcer: BudgetEnforcer, budget: SubagentBudget) -> None:
    """used <= max_tokens → no raise."""
    enforcer.check_tokens(used=10_000, budget=budget)  # at cap, not over


def test_check_tokens_exceeds_raises(enforcer: BudgetEnforcer, budget: SubagentBudget) -> None:
    """used > max_tokens → BudgetExceededError."""
    with pytest.raises(BudgetExceededError, match="token_used=10001"):
        enforcer.check_tokens(used=10_001, budget=budget)


# === check_duration ==========================================================


def test_check_duration_pass_under_cap(enforcer: BudgetEnforcer, budget: SubagentBudget) -> None:
    """elapsed <= max_duration_s → no raise."""
    enforcer.check_duration(elapsed_s=300.0, budget=budget)  # at cap


def test_check_duration_exceeds_raises(enforcer: BudgetEnforcer, budget: SubagentBudget) -> None:
    """elapsed > max_duration_s → BudgetExceededError."""
    with pytest.raises(BudgetExceededError, match="elapsed=300.5s"):
        enforcer.check_duration(elapsed_s=300.5, budget=budget)


# === truncate_summary ========================================================


def test_truncate_summary_under_cap_no_truncation(enforcer: BudgetEnforcer) -> None:
    """text words <= cap → returned unchanged + was_truncated=False."""
    text = "short summary text"  # 3 words
    out, was = enforcer.truncate_summary(text, cap_words=500)
    assert out == text
    assert was is False


def test_truncate_summary_over_cap_returns_truncated_flag(
    enforcer: BudgetEnforcer,
) -> None:
    """text words > cap → truncated + suffix + was_truncated=True."""
    text = " ".join(["word"] * 10)  # 10 words
    out, was = enforcer.truncate_summary(text, cap_words=3)
    assert was is True
    assert out.startswith("word word word")
    assert out.endswith("[...truncated]")
    # Truncated word count should be exactly 3 (the cap)
    assert len(out.split()) == 4  # 3 words + "[...truncated]"


# === Empty / edge case (bonus) ==============================================


def test_truncate_summary_empty_string_returns_empty(enforcer: BudgetEnforcer) -> None:
    """Empty input: short-circuit; no truncation marker."""
    out, was = enforcer.truncate_summary("", cap_words=500)
    assert out == ""
    assert was is False


# === check_depth (depth guard) ==============================================


def test_check_depth_pass_under_cap(enforcer: BudgetEnforcer, budget: SubagentBudget) -> None:
    """current_depth < max_subagent_depth → no raise."""
    enforcer.check_depth(current_depth=2, budget=budget)  # 2 < 3


def test_check_depth_exceeds_raises(enforcer: BudgetEnforcer, budget: SubagentBudget) -> None:
    """current_depth >= max_subagent_depth → BudgetExceededError (recursive guard)."""
    with pytest.raises(BudgetExceededError, match="depth=3"):
        enforcer.check_depth(current_depth=3, budget=budget)

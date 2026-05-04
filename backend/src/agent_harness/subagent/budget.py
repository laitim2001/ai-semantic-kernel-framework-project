"""
File: backend/src/agent_harness/subagent/budget.py
Purpose: BudgetEnforcer — guard 4 SubagentBudget cap dimensions + summary truncation.
Category: 範疇 11 (Subagent Orchestration)
Scope: Sprint 54.2 US-1

Description:
    SubagentBudget defines 4 cap dimensions (max_tokens / max_duration_s /
    max_concurrent / max_subagent_depth). BudgetEnforcer provides 4 check_*()
    methods each raising BudgetExceededError on breach, plus truncate_summary()
    enforcing the SubagentResult.summary "≤ 500 tokens" convention.

    Per Day 0 探勘 D9: SubagentBudget is frozen=True (immutable). To adjust
    a budget for a child invocation, callers use dataclasses.replace().

    Truncation strategy: word-based (split on whitespace) for simplicity; if
    production needs token-accurate truncation later, adapter can plug a
    ChatClient.count_tokens()-based variant (range owner: Cat 4 token counter).

Created: 2026-05-04 (Sprint 54.2)

Modification History:
    - 2026-05-04: Initial creation (Sprint 54.2 US-1)

Related:
    - _contracts/subagent.py — SubagentBudget single-source
    - 01-eleven-categories-spec.md §範疇 11
"""

from __future__ import annotations

from agent_harness._contracts import SubagentBudget
from agent_harness.subagent.exceptions import BudgetExceededError


class BudgetEnforcer:
    """Pure-function budget guard; raises BudgetExceededError on cap breach."""

    def check_concurrent(self, active_count: int, budget: SubagentBudget) -> None:
        """Raise if `active_count >= budget.max_concurrent`.

        Note: uses `>=` not `>` because the candidate slot would push active
        over cap; check before incrementing the in-flight count.
        """
        if active_count >= budget.max_concurrent:
            raise BudgetExceededError(
                f"max_concurrent={budget.max_concurrent} reached " f"(active={active_count})"
            )

    def check_tokens(self, used: int, budget: SubagentBudget) -> None:
        """Raise if `used > budget.max_tokens`."""
        if used > budget.max_tokens:
            raise BudgetExceededError(f"token_used={used} > max_tokens={budget.max_tokens}")

    def check_duration(self, elapsed_s: float, budget: SubagentBudget) -> None:
        """Raise if `elapsed_s > budget.max_duration_s`."""
        if elapsed_s > budget.max_duration_s:
            raise BudgetExceededError(
                f"elapsed={elapsed_s:.1f}s > max_duration={budget.max_duration_s}s"
            )

    def check_depth(self, current_depth: int, budget: SubagentBudget) -> None:
        """Raise if `current_depth >= budget.max_subagent_depth`.

        Prevents recursive spawn explosion (a forked child spawning more
        children indefinitely). Caller increments depth before each spawn.
        """
        if current_depth >= budget.max_subagent_depth:
            raise BudgetExceededError(
                f"depth={current_depth} >= max_subagent_depth={budget.max_subagent_depth}"
            )

    def truncate_summary(self, text: str, cap_words: int = 500) -> tuple[str, bool]:
        """Truncate summary to <= cap_words; returns (text, was_truncated).

        Word-based, NOT token-based. The "≤ 500 tokens" convention from
        SubagentResult.summary docstring is approximated as "≤ 500 words" —
        good enough for English text where 1 word ~ 1.3 tokens. Token-accurate
        truncation can be added later by injecting a TokenCounter (Cat 4 owner).
        """
        if not text:
            return "", False
        words = text.split()
        if len(words) <= cap_words:
            return text, False
        truncated = " ".join(words[:cap_words]) + " [...truncated]"
        return truncated, True

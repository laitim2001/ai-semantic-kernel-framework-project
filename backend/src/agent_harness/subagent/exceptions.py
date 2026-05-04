"""
File: backend/src/agent_harness/subagent/exceptions.py
Purpose: Cat 11 Subagent exceptions; raised when budget caps breached or launch fails.
Category: 範疇 11 (Subagent Orchestration)
Scope: Sprint 54.2 US-1

Description:
    Two exception classes for the dispatcher to raise when budget enforcement
    or launch path fails. BudgetExceededError is caught by spawn() / wait_for()
    callers and converted to SubagentResult(success=False, error=...).
    SubagentLaunchError indicates a programming / configuration fault and
    propagates up.

Created: 2026-05-04 (Sprint 54.2)

Modification History:
    - 2026-05-04: Initial creation (Sprint 54.2 US-1)

Related:
    - 01-eleven-categories-spec.md §範疇 11 (Subagent Orchestration)
    - 17-cross-category-interfaces.md §1.1 (SubagentBudget owner)
"""

from __future__ import annotations


class BudgetExceededError(Exception):
    """Raised when SubagentBudget cap (tokens / duration / concurrency / depth) breached.

    Caller (spawn / wait_for) MUST catch and translate to
    SubagentResult(success=False, error=str(exc)) so that fail-closed semantics
    propagate to the parent loop without crashing the harness.
    """


class SubagentLaunchError(Exception):
    """Raised on programming / configuration faults during subagent launch.

    Examples: unknown SubagentMode value; missing required executor; mailbox
    not provided for TEAMMATE mode. Propagates up the stack — these are NOT
    expected runtime conditions and indicate a code bug.
    """

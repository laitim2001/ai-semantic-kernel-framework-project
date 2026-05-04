"""Category 11: Subagent Orchestration (4 modes, no worktree). See README.md.

Sprint 54.2 US-1 adds DefaultSubagentDispatcher + BudgetEnforcer +
BudgetExceededError. US-2/3/4 will add Fork / Teammate / Handoff / AsTool
mode executors + Mailbox.
"""

from agent_harness.subagent._abc import SubagentDispatcher
from agent_harness.subagent.budget import BudgetEnforcer
from agent_harness.subagent.dispatcher import DefaultSubagentDispatcher
from agent_harness.subagent.exceptions import (
    BudgetExceededError,
    SubagentLaunchError,
)
from agent_harness.subagent.modes.as_tool import AsToolWrapper
from agent_harness.subagent.modes.fork import ForkExecutor

__all__ = [
    "SubagentDispatcher",
    "DefaultSubagentDispatcher",
    "BudgetEnforcer",
    "BudgetExceededError",
    "SubagentLaunchError",
    "ForkExecutor",
    "AsToolWrapper",
]

"""
File: backend/src/agent_harness/subagent/dispatcher.py
Purpose: DefaultSubagentDispatcher — production class implementing SubagentDispatcher ABC.
Category: 範疇 11 (Subagent Orchestration)
Scope: Sprint 54.2 US-1 (skeleton); US-2/3/4 fill in mode executors

Description:
    DefaultSubagentDispatcher implements the 3-method ABC (spawn /
    wait_for / handoff) using a fire-and-forget asyncio pattern:

    - spawn(mode=FORK|TEAMMATE, task, parent_session_id, budget) -> UUID
        Launches an asyncio.Task in the background; returns subagent_id
        immediately. Future is stored in self._in_flight for retrieval.
    - wait_for(subagent_id, timeout_s) -> SubagentResult
        Blocks until the future resolves (or timeout). Returns
        success=False / error=... on BudgetExceededError or timeout.
    - handoff(target_agent, context) -> UUID (new session_id)
        Synchronous transfer; returns new session_id directly.

    AS_TOOL mode is NOT routed through spawn(). It uses the separate
    `as_tool_factory(agent_role)` method (Option A from Day 0 D1-followup),
    which returns a ToolSpec for Cat 2 ToolRegistry. spawn(mode=AS_TOOL)
    raises SubagentLaunchError.

    US-1 (this commit) ships skeleton only: spawn() raises NotImplementedError
    for FORK / TEAMMATE; wait_for() / handoff() / as_tool_factory() also
    NotImplementedError. US-2 fills FORK + AS_TOOL; US-3 fills TEAMMATE; US-4
    fills HANDOFF.

Created: 2026-05-04 (Sprint 54.2)

Modification History:
    - 2026-05-04: Initial skeleton creation (Sprint 54.2 US-1)

Related:
    - subagent/_abc.py — SubagentDispatcher ABC (3 methods)
    - _contracts/subagent.py — SubagentBudget / SubagentResult / SubagentMode
    - 17-cross-category-interfaces.md §2.1 (SubagentDispatcher owner)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from agent_harness._contracts import (
    SubagentBudget,
    SubagentMode,
    SubagentResult,
    TraceContext,
)
from agent_harness.subagent._abc import SubagentDispatcher
from agent_harness.subagent.budget import BudgetEnforcer
from agent_harness.subagent.exceptions import SubagentLaunchError

if TYPE_CHECKING:
    # Avoid circular import; ToolSpec only used in as_tool_factory() return type.
    from agent_harness._contracts.tools import ToolSpec


class DefaultSubagentDispatcher(SubagentDispatcher):
    """Production dispatcher; routes by SubagentMode to mode executors.

    Per Day 0 D1: 3-method ABC (spawn / wait_for / handoff) + 1 extra method
    (as_tool_factory) for AS_TOOL wrapping. Mode executors (Fork / Teammate /
    Handoff) injected via __init__ in US-2/3/4; US-1 ships skeleton with
    NotImplementedError raises.

    Per AD-Test-1 (53.6) lesson: this class is per-request DI, NOT
    module-level singleton. AgentLoop holds a fresh instance per request.
    """

    def __init__(self) -> None:
        self._enforcer = BudgetEnforcer()
        # In-flight subagent futures for wait_for() lookup.
        # Populated by spawn() (US-2/3); read by wait_for() (US-2/3).
        self._in_flight: dict[UUID, Any] = {}

    async def spawn(
        self,
        *,
        mode: SubagentMode,
        task: str,
        parent_session_id: UUID,
        budget: SubagentBudget | None = None,
        trace_context: TraceContext | None = None,
    ) -> UUID:
        """Launch a subagent in FORK or TEAMMATE mode; return subagent_id.

        AS_TOOL mode raises SubagentLaunchError — use as_tool_factory() instead.
        HANDOFF mode raises SubagentLaunchError — use handoff() method instead.

        US-1 skeleton raises NotImplementedError; US-2 fills FORK; US-3 fills
        TEAMMATE.
        """
        if mode == SubagentMode.AS_TOOL:
            raise SubagentLaunchError(
                "AS_TOOL mode does not use spawn(); call as_tool_factory(agent_role) "
                "to get a ToolSpec for Cat 2 ToolRegistry."
            )
        if mode == SubagentMode.HANDOFF:
            raise SubagentLaunchError(
                "HANDOFF mode does not use spawn(); call handoff(target_agent, context) "
                "directly — it returns a new session_id."
            )
        # FORK / TEAMMATE — implementations come in US-2 / US-3.
        raise NotImplementedError(
            f"spawn(mode={mode.value}) skeleton; impl in Sprint 54.2 US-2 (FORK) / US-3 (TEAMMATE)."
        )

    async def wait_for(
        self,
        subagent_id: UUID,
        *,
        timeout_s: int | None = None,
        trace_context: TraceContext | None = None,
    ) -> SubagentResult:
        """Block until subagent completes; return SubagentResult.

        US-1 skeleton raises NotImplementedError; US-2 fills (shared with FORK).
        """
        raise NotImplementedError(
            "wait_for() skeleton; impl in Sprint 54.2 US-2 (FORK) — shared "
            "in-flight future retrieval."
        )

    async def handoff(
        self,
        *,
        target_agent: str,
        context: dict[str, object],
        trace_context: TraceContext | None = None,
    ) -> UUID:
        """Transfer control to target_agent; return new session_id.

        US-1 skeleton raises NotImplementedError; US-4 fills.
        """
        raise NotImplementedError("handoff() skeleton; impl in Sprint 54.2 US-4.")

    def as_tool_factory(self, agent_role: str) -> "ToolSpec":
        """Wrap a subagent role as a ToolSpec for Cat 2 ToolRegistry.

        Per Day 0 D1-followup Option A: AS_TOOL is OUT-OF-BAND from spawn()
        because it returns a ToolSpec (not a SubagentResult). LLM calls the
        wrapped tool like any other; handler internally invokes spawn(FORK)
        with bounded budget.

        US-1 skeleton raises NotImplementedError; US-2 fills.
        """
        raise NotImplementedError(
            f"as_tool_factory(role={agent_role!r}) skeleton; impl in Sprint 54.2 US-2."
        )

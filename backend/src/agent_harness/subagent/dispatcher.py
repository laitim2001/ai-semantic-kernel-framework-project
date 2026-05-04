"""
File: backend/src/agent_harness/subagent/dispatcher.py
Purpose: DefaultSubagentDispatcher — production class implementing SubagentDispatcher ABC.
Category: 範疇 11 (Subagent Orchestration)
Scope: Sprint 54.2 US-1 → US-2 (FORK + AsTool) → US-3 (TEAMMATE); US-4 HANDOFF

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
        Synchronous transfer; returns new session_id directly. (US-4)

    AS_TOOL mode is NOT routed through spawn(). It uses the separate
    `as_tool_factory(spec)` method (Option A from Day 0 D1-followup),
    which returns (ToolSpec, handler) for Cat 2 ToolRegistry. spawn(mode=AS_TOOL)
    raises SubagentLaunchError.

    Concurrency: spawn() pre-checks budget.max_concurrent against the count
    of in-flight subagents (per AD-Test-1 53.6: per-request DI; not module
    singleton). Depth check is left to the caller (parent loop tracks current
    depth; passes via context).

US-2 deliverable (this file): wires FORK via ForkExecutor + as_tool_factory
    via AsToolWrapper. TEAMMATE / HANDOFF still raise NotImplementedError.

Created: 2026-05-04 (Sprint 54.2)

Modification History:
    - 2026-05-04: Wire HANDOFF via HandoffExecutor (US-4)
    - 2026-05-04: Wire TEAMMATE via TeammateExecutor + MailboxStore injection (US-3)
    - 2026-05-04: Wire FORK via ForkExecutor + as_tool_factory via AsToolWrapper (US-2)
    - 2026-05-04: Initial skeleton creation (Sprint 54.2 US-1)

Related:
    - subagent/_abc.py — SubagentDispatcher ABC (3 methods)
    - subagent/modes/fork.py — ForkExecutor (US-2)
    - subagent/modes/as_tool.py — AsToolWrapper (US-2)
    - _contracts/subagent.py — SubagentBudget / SubagentResult / SubagentMode / AgentSpec
    - 17-cross-category-interfaces.md §2.1 (SubagentDispatcher owner)
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from adapters._base.chat_client import ChatClient
from agent_harness._contracts import (
    AgentSpec,
    SubagentBudget,
    SubagentMode,
    SubagentResult,
    TraceContext,
)
from agent_harness.subagent._abc import SubagentDispatcher
from agent_harness.subagent.budget import BudgetEnforcer
from agent_harness.subagent.exceptions import (
    BudgetExceededError,
    SubagentLaunchError,
)
from agent_harness.subagent.mailbox import MailboxStore
from agent_harness.subagent.modes.as_tool import AsToolWrapper
from agent_harness.subagent.modes.fork import ForkExecutor
from agent_harness.subagent.modes.handoff import HandoffExecutor
from agent_harness.subagent.modes.teammate import TeammateExecutor

if TYPE_CHECKING:
    # Tool handler return type — see modes/as_tool.py for ToolHandler alias.
    from agent_harness._contracts import ToolSpec
    from agent_harness.subagent.modes.as_tool import ToolHandler


class DefaultSubagentDispatcher(SubagentDispatcher):
    """Production dispatcher; routes by SubagentMode to mode executors.

    Per Day 0 D1 / D10: 3-method ABC (spawn / wait_for / handoff) + 1 extra
    method (as_tool_factory) for AS_TOOL wrapping. Mode executors (Fork in
    US-2, Teammate in US-3, Handoff in US-4) injected via __init__.

    Per AD-Test-1 (53.6) lesson: this class is per-request DI, NOT
    module-level singleton. AgentLoop holds a fresh instance per request.
    """

    def __init__(
        self,
        *,
        chat_client: ChatClient,
        mailbox: MailboxStore | None = None,
    ) -> None:
        self._chat = chat_client
        self._enforcer = BudgetEnforcer()
        # Mailbox is per-request DI (NOT module-level singleton; AD-Test-1 53.6).
        # If caller does not inject one, create a fresh instance scoped to this dispatcher.
        self._mailbox = mailbox or MailboxStore()
        self._fork = ForkExecutor(chat_client=chat_client, enforcer=self._enforcer)
        self._teammate = TeammateExecutor(
            chat_client=chat_client,
            mailbox=self._mailbox,
            enforcer=self._enforcer,
        )
        self._handoff = HandoffExecutor()
        self._as_tool_wrapper = AsToolWrapper(fork_executor=self._fork)
        # In-flight subagent tasks for wait_for() lookup. Per-instance state;
        # NOT module-level — fresh dispatcher per request.
        self._in_flight: dict[UUID, asyncio.Task[SubagentResult]] = {}

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

        US-2 fills FORK; US-3 fills TEAMMATE.
        """
        if mode == SubagentMode.AS_TOOL:
            raise SubagentLaunchError(
                "AS_TOOL mode does not use spawn(); call as_tool_factory(spec) "
                "to get (ToolSpec, handler) for Cat 2 ToolRegistry."
            )
        if mode == SubagentMode.HANDOFF:
            raise SubagentLaunchError(
                "HANDOFF mode does not use spawn(); call handoff(target_agent, context) "
                "directly — it returns a new session_id."
            )

        budget = budget or SubagentBudget()
        # Concurrency guard — count active futures (not yet done).
        active = sum(1 for t in self._in_flight.values() if not t.done())
        try:
            self._enforcer.check_concurrent(active_count=active, budget=budget)
        except BudgetExceededError as exc:
            # Budget exceeded surfaces as a synchronous launch failure (no
            # subagent_id allocated). Caller catches SubagentLaunchError and
            # converts to its own error path.
            raise SubagentLaunchError(f"spawn rejected: {exc}") from exc

        subagent_id = uuid4()

        if mode == SubagentMode.FORK:
            coro = self._fork.execute(
                subagent_id=subagent_id,
                task=task,
                budget=budget,
                trace_context=trace_context,
            )
        elif mode == SubagentMode.TEAMMATE:
            # Per Day 3 D15: role defaults to "teammate"; ABC has no role kwarg.
            # Phase 55+ may extend ABC or thread role via trace_context.
            coro = self._teammate.execute(
                subagent_id=subagent_id,
                parent_session_id=parent_session_id,
                role="teammate",
                task=task,
                budget=budget,
                trace_context=trace_context,
            )
        else:  # pragma: no cover — Enum exhausted by branches above
            raise SubagentLaunchError(f"Unknown mode: {mode}")

        self._in_flight[subagent_id] = asyncio.create_task(coro)
        return subagent_id

    async def wait_for(
        self,
        subagent_id: UUID,
        *,
        timeout_s: int | None = None,
        trace_context: TraceContext | None = None,
    ) -> SubagentResult:
        """Block until subagent completes; return SubagentResult (fail-closed)."""
        task = self._in_flight.get(subagent_id)
        if task is None:
            return SubagentResult(
                subagent_id=subagent_id,
                mode=SubagentMode.FORK,  # placeholder — unknown
                success=False,
                summary="",
                error=f"unknown_subagent_id: {subagent_id}",
            )
        try:
            if timeout_s is None:
                return await task
            return await asyncio.wait_for(asyncio.shield(task), timeout=timeout_s)
        except asyncio.TimeoutError:
            # Don't cancel — caller may still want to retrieve later via wait_for again.
            return SubagentResult(
                subagent_id=subagent_id,
                mode=SubagentMode.FORK,
                success=False,
                summary="",
                error=f"wait_for_timeout: {timeout_s}s",
            )

    async def handoff(
        self,
        *,
        target_agent: str,
        context: dict[str, object],
        trace_context: TraceContext | None = None,
    ) -> UUID:
        """Transfer control to target_agent; return new session_id.

        Per Day 4 D18 simplification: delegates to HandoffExecutor (stateless;
        allocates UUID + validates target_agent). Phase 55+ may add per-tenant
        target_agent allowlist + audit event emission here.
        """
        return await self._handoff.execute(
            target_agent=target_agent,
            context=context,
            trace_context=trace_context,
        )

    def as_tool_factory(self, spec: AgentSpec) -> tuple["ToolSpec", "ToolHandler"]:
        """Wrap AgentSpec into a Cat 2 ToolSpec + handler pair.

        Per Day 0 D1-followup Option A: AS_TOOL is OUT-OF-BAND from spawn()
        because it returns a ToolSpec (not a SubagentResult). Callers register
        the returned (ToolSpec, handler) with Cat 2 ToolRegistry; the LLM then
        invokes the wrapped subagent like any tool.

        US-2 wires this to AsToolWrapper.
        """
        return self._as_tool_wrapper.wrap(spec)

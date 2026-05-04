"""
File: backend/src/agent_harness/subagent/tools.py
Purpose: LLM-callable tool factories for Cat 11 — task_spawn + handoff (per 17.md §3.1).
Category: 範疇 11 (Subagent Orchestration)
Scope: Sprint 54.2 US-5

Description:
    17-cross-category-interfaces.md §3.1 lists `task_spawn` and `handoff` as
    Cat 11 LLM-callable tools (the LLM decides when to invoke them). This
    module provides factories that wrap a SubagentDispatcher into Cat 2
    ToolSpec + handler pairs ready for ToolRegistry registration.

    Per Day 4 D18 design decision: AgentLoop is NOT modified. Tools auto-route
    through the existing `tool_executor.execute(tc)` path (loop.py:1018) once
    registered. The chat router (or any AgentLoop owner) calls this module's
    factories before constructing the loop, attaches the (ToolSpec, handler)
    pair to its ToolRegistry, and the LLM can invoke them like any tool.

    AgentLoop integration (Phase 55+): if SSE event emission for SubagentSpawned
    / SubagentCompleted is required, that's a separate concern handled by
    extending serialize_loop_event in api/v1/chat/sse.py and emitting the
    events from the tool handlers themselves (or a dispatcher hook). The 49.1
    stub events are wire-ready; emission is a Phase 55+ refinement.

Created: 2026-05-04 (Sprint 54.2)

Modification History:
    - 2026-05-04: Initial creation (Sprint 54.2 US-5)

Related:
    - subagent/dispatcher.py — DefaultSubagentDispatcher
    - 17-cross-category-interfaces.md §3.1 (task_spawn / handoff)
    - tools/registry.py — ToolRegistry consumer
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable
from uuid import UUID

from agent_harness._contracts import (
    SubagentBudget,
    SubagentMode,
    ToolSpec,
)
from agent_harness.subagent._abc import SubagentDispatcher

ToolHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


def make_task_spawn_tool(
    *,
    dispatcher: SubagentDispatcher,
    parent_session_id: UUID,
) -> tuple[ToolSpec, ToolHandler]:
    """Factory: returns (ToolSpec, handler) for the `task_spawn` Cat 11 tool.

    LLM input schema: `{task: str, mode?: "fork"|"teammate"}`. Mode defaults
    to "fork" when LLM omits it.

    The handler synchronously waits for the subagent (uses dispatcher.wait_for
    internally). LLM caller blocks per turn — for fire-and-forget patterns
    callers can extend the schema to accept `wait: bool` in Phase 55+.
    """
    tool_spec = ToolSpec(
        name="task_spawn",
        description=(
            "Spawn a subagent to execute a delegated sub-task in fork (independent "
            "context) or teammate (mailbox-connected peer) mode. Returns subagent_id, "
            "success flag, and short summary of the subagent's response."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Sub-task description for the subagent.",
                },
                "mode": {
                    "type": "string",
                    "enum": ["fork", "teammate"],
                    "default": "fork",
                    "description": (
                        "Dispatch mode: 'fork' for independent exploration; "
                        "'teammate' for peer with mailbox communication."
                    ),
                },
            },
            "required": ["task"],
        },
    )

    async def handler(args: dict[str, Any]) -> dict[str, Any]:
        task = str(args.get("task", "")).strip()
        if not task:
            return {"success": False, "error": "missing_task"}
        mode_str = str(args.get("mode", "fork")).lower()
        try:
            mode = SubagentMode(mode_str)
        except ValueError:
            return {"success": False, "error": f"unknown_mode: {mode_str!r}"}
        if mode not in (SubagentMode.FORK, SubagentMode.TEAMMATE):
            return {
                "success": False,
                "error": f"task_spawn supports fork/teammate only, got {mode.value}",
            }
        try:
            subagent_id = await dispatcher.spawn(
                mode=mode,
                task=task,
                parent_session_id=parent_session_id,
                budget=SubagentBudget(),
            )
        except Exception as exc:  # noqa: BLE001 — surface as tool error
            return {"success": False, "error": f"spawn_failed: {type(exc).__name__}: {exc}"}
        result = await dispatcher.wait_for(subagent_id)
        return {
            "subagent_id": str(result.subagent_id),
            "success": result.success,
            "summary": result.summary,
            "tokens_used": result.tokens_used,
            "error": result.error,
        }

    return tool_spec, handler


def make_handoff_tool(
    *,
    dispatcher: SubagentDispatcher,
) -> tuple[ToolSpec, ToolHandler]:
    """Factory: returns (ToolSpec, handler) for the `handoff` Cat 11 tool.

    LLM input schema: `{target_agent: str, context: dict}`. Returns the new
    session_id; the chat router is expected to detect this in the tool result
    and pivot the session to the new agent identity.
    """
    tool_spec = ToolSpec(
        name="handoff",
        description=(
            "Transfer complete control to a target agent identity. Returns the "
            "new session_id; the platform router will boot the target_agent "
            "under that session. Use sparingly — this ENDS the current agent's "
            "responsibility for the conversation."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "target_agent": {
                    "type": "string",
                    "description": "Identifier of the target agent role.",
                },
                "context": {
                    "type": "object",
                    "description": "Hand-over context payload (free-form).",
                },
            },
            "required": ["target_agent"],
        },
    )

    async def handler(args: dict[str, Any]) -> dict[str, Any]:
        target_agent = str(args.get("target_agent", "")).strip()
        if not target_agent:
            return {"handoff_initiated": False, "error": "missing_target_agent"}
        context = args.get("context") or {}
        if not isinstance(context, dict):
            return {"handoff_initiated": False, "error": "context_must_be_object"}
        try:
            new_session_id = await dispatcher.handoff(
                target_agent=target_agent,
                context=context,
            )
        except Exception as exc:  # noqa: BLE001 — surface as tool error
            return {
                "handoff_initiated": False,
                "error": f"handoff_failed: {type(exc).__name__}: {exc}",
            }
        return {
            "handoff_initiated": True,
            "target_agent": target_agent,
            "new_session_id": str(new_session_id),
        }

    return tool_spec, handler

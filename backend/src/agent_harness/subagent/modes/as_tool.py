"""
File: backend/src/agent_harness/subagent/modes/as_tool.py
Purpose: AsToolWrapper — wraps an AgentSpec into a Cat 2 ToolSpec for LLM-callable subagents.
Category: 範疇 11 (Subagent Orchestration)
Scope: Sprint 54.2 US-2

Description:
    AS_TOOL mode (per OpenAI agents-as-tools pattern): the parent LLM treats
    a subagent as if it were a normal tool. Calling the tool with `{"task": ...}`
    invokes ForkExecutor under bounded budget; result.summary becomes the
    tool's return value (fed back to parent LLM as a tool message).

    Per Day 0 D1-followup Option A: AS_TOOL is OUT-OF-BAND from spawn() because
    it returns a ToolSpec (not a SubagentResult). Caller invokes
    `dispatcher.as_tool_factory(role)` to get a ToolSpec for Cat 2 ToolRegistry.

Created: 2026-05-04 (Sprint 54.2)

Modification History:
    - 2026-05-04: Initial creation (Sprint 54.2 US-2)

Related:
    - subagent/modes/fork.py — ForkExecutor (delegated by handler)
    - _contracts/subagent.py — AgentSpec (54.2 US-2 addition)
    - _contracts/tools.py — ToolSpec
    - 17-cross-category-interfaces.md §3.1 (subagent_query / agents-as-tools)
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable
from uuid import UUID, uuid4

from agent_harness._contracts import (
    AgentSpec,
    SubagentBudget,
    ToolSpec,
)
from agent_harness.subagent.modes.fork import ForkExecutor

# Tool handler signature: takes the tool input dict, returns dict result.
# Caller (Cat 2 ToolExecutor) feeds the dict back to the LLM as a tool message.
ToolHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


class AsToolWrapper:
    """Factory for ToolSpec wrapping a subagent role.

    Each call to `wrap(spec)` returns a fresh (ToolSpec, handler) pair. The
    handler is a closure capturing `spec` and `default_budget`, suitable for
    registration with Cat 2 ToolRegistry alongside its handler.
    """

    def __init__(
        self,
        *,
        fork_executor: ForkExecutor,
        default_budget: SubagentBudget | None = None,
    ) -> None:
        self._fork = fork_executor
        # Default bounded budget for tool-mode subagents — narrower than parent's
        # since LLM may chain multiple tool calls per turn.
        self._default_budget = default_budget or SubagentBudget(
            max_tokens=4_000,
            max_duration_s=60,
            max_concurrent=2,
            max_subagent_depth=2,
        )

    def wrap(self, spec: AgentSpec) -> tuple[ToolSpec, ToolHandler]:
        """Return (ToolSpec, handler) for a subagent role.

        Tool name is `agent_{spec.role}` (snake-case role assumed).
        """
        tool_spec = ToolSpec(
            name=f"agent_{spec.role}",
            description=(
                f"Invoke {spec.role!r} subagent on a sub-task. "
                f"Returns a short summary of the subagent's response."
                + (f" Role prompt: {spec.prompt[:80]}..." if spec.prompt else "")
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The sub-task description for the subagent.",
                    }
                },
                "required": ["task"],
            },
        )

        async def handler(args: dict[str, Any]) -> dict[str, Any]:
            task = str(args.get("task", "")).strip()
            if not task:
                return {"success": False, "summary": "", "error": "missing_task"}
            # Compose role prompt with task for the FORK call.
            full_task = f"{spec.prompt}\n\nTask: {task}" if spec.prompt else task
            subagent_id: UUID = uuid4()
            result = await self._fork.execute(
                subagent_id=subagent_id,
                task=full_task,
                budget=self._default_budget,
            )
            return {
                "subagent_id": str(result.subagent_id),
                "success": result.success,
                "summary": result.summary,
                "tokens_used": result.tokens_used,
                "error": result.error,
            }

        return tool_spec, handler

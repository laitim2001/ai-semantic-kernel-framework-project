"""
TeamToolRegistry — Bridges PoC team collaboration tools to SwarmWorkerExecutor.

Wraps SharedTaskList + team communication tools (send_team_message,
check_my_inbox, claim_next_task, etc.) in the tool_registry interface
expected by SwarmWorkerExecutor:
  - get_openai_tool_schemas(role) → List[Dict]
  - execute(tool_name, params, user_id, role) → ToolExecutionResult

Phase 45: Agent Team Visualization — PoC tool integration.
"""

import inspect
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.integrations.poc.shared_task_list import SharedTaskList

logger = logging.getLogger(__name__)


@dataclass
class ToolExecutionResult:
    """Result from tool execution."""
    success: bool
    data: Any = None
    error: Optional[str] = None


# OpenAI function schemas for team tools
TEAM_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "send_team_message",
            "description": (
                "Send a message to the team or a specific teammate. "
                "Use this to share findings, request help, or coordinate."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "from_agent": {
                        "type": "string",
                        "description": "Your agent name",
                    },
                    "message": {
                        "type": "string",
                        "description": "The message to send",
                    },
                    "to_agent": {
                        "type": "string",
                        "description": "Target agent name (empty for broadcast)",
                        "default": "",
                    },
                },
                "required": ["from_agent", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_my_inbox",
            "description": (
                "Check for messages directed specifically to you from other agents. "
                "Check this regularly to see if teammates have sent you findings or requests."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "Your agent name",
                    },
                },
                "required": ["agent_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_team_messages",
            "description": (
                "Read recent broadcast messages from other team members. "
                "Use this to see if teammates have shared important findings."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "view_team_status",
            "description": (
                "View the current status of all tasks and which teammate is working on what."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "claim_next_task",
            "description": (
                "Claim the next highest-priority pending task from the shared task list."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "Your agent name",
                    },
                },
                "required": ["agent_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "report_task_result",
            "description": (
                "Report the result of a completed task with your findings."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The task ID to report on",
                    },
                    "result": {
                        "type": "string",
                        "description": "Your analysis/findings for this task",
                    },
                },
                "required": ["task_id", "result"],
            },
        },
    },
]


class TeamToolRegistry:
    """Tool registry providing team collaboration tools to SwarmWorkerExecutor.

    Wraps PoC SharedTaskList + team tools in the interface expected by
    SwarmWorkerExecutor._execute_tool() and _get_filtered_tool_schemas().

    Also supports merging with an external base registry (e.g.,
    OrchestratorToolRegistry) so agents get both team + knowledge tools.
    """

    def __init__(
        self,
        shared_task_list: Optional[SharedTaskList] = None,
        base_registry: Optional[Any] = None,
    ) -> None:
        self._shared = shared_task_list or SharedTaskList()
        self._base_registry = base_registry
        self._tool_handlers = self._build_tool_handlers()

    def _build_tool_handlers(self) -> Dict[str, Any]:
        """Build callable handlers for each team tool."""
        shared = self._shared
        return {
            "send_team_message": lambda **kwargs: shared.add_message(
                kwargs["from_agent"],
                kwargs["message"],
                to_agent=kwargs.get("to_agent") or None,
            ) or f"Message sent: {kwargs['message'][:100]}",
            "check_my_inbox": lambda **kwargs: (
                shared.get_inbox(kwargs["agent_name"], unread_only=True)
                or "No new directed messages for you."
            ),
            "read_team_messages": lambda **kwargs: (
                shared.get_messages() or "No team messages yet."
            ),
            "view_team_status": lambda **kwargs: (
                shared.get_status() or "No tasks in the list."
            ),
            "claim_next_task": lambda **kwargs: (
                (lambda t: (
                    f"Claimed task {t.task_id}: {t.description} (priority: {t.priority})"
                    if t else "No pending tasks available."
                ))(shared.claim_task(kwargs["agent_name"]))
            ),
            "report_task_result": lambda **kwargs: (
                f"Task {kwargs['task_id']} completed."
                if shared.complete_task(kwargs["task_id"], kwargs["result"])
                else f"Task {kwargs['task_id']} not found."
            ),
        }

    def get_openai_tool_schemas(self, role: str = "admin") -> List[Dict[str, Any]]:
        """Return OpenAI function calling schemas for team tools.

        Merges base registry schemas (if available) with team tool schemas.
        """
        schemas = list(TEAM_TOOL_SCHEMAS)

        if self._base_registry and hasattr(self._base_registry, "get_openai_tool_schemas"):
            try:
                base_schemas = self._base_registry.get_openai_tool_schemas(role=role)
                schemas.extend(base_schemas)
            except Exception as e:
                logger.warning("Failed to get base registry schemas: %s", str(e)[:100])

        return schemas

    async def execute(
        self,
        tool_name: str,
        params: Dict[str, Any],
        user_id: str = "",
        role: str = "admin",
    ) -> ToolExecutionResult:
        """Execute a team tool by name.

        Falls back to base registry if tool is not a team tool.
        """
        handler = self._tool_handlers.get(tool_name)

        if handler:
            try:
                result = handler(**params)
                logger.info("TeamTool %s executed: %s", tool_name, str(result)[:100])
                return ToolExecutionResult(success=True, data=result)
            except Exception as e:
                logger.warning("TeamTool %s failed: %s", tool_name, str(e)[:100])
                return ToolExecutionResult(success=False, error=str(e))

        # Fallback to base registry
        if self._base_registry and hasattr(self._base_registry, "execute"):
            try:
                return await self._base_registry.execute(
                    tool_name=tool_name, params=params, user_id=user_id, role=role
                )
            except Exception as e:
                return ToolExecutionResult(success=False, error=str(e))

        return ToolExecutionResult(
            success=False, error=f"Unknown tool: {tool_name}"
        )

    @property
    def shared_task_list(self) -> SharedTaskList:
        """Access the underlying SharedTaskList for inspection."""
        return self._shared

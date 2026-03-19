"""
Orchestrator Agent Tools — function tools available to the Orchestrator.

Each tool wraps existing platform functionality as a callable that the
AgentHandler can invoke based on LLM decisions.

Tool Categories:
- Synchronous Tools (< 5s): assess_risk, search_memory, respond_to_user
- Async Dispatch Tools (return task_id): dispatch_workflow, dispatch_swarm

Sprint 112 — Phase 36 Orchestrator completeness.
"""

import logging
import uuid
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ToolType(str, Enum):
    """Classification of tool execution behaviour."""

    SYNC = "sync"  # < 5s, await result
    ASYNC_DISPATCH = "async"  # returns task_id, runs in background


@dataclass
class ToolDefinition:
    """Schema describing a single orchestrator tool."""

    name: str
    description: str
    tool_type: ToolType
    parameters: Dict[str, Any] = field(default_factory=dict)
    required_role: str = "operator"  # minimum role to use


@dataclass
class ToolResult:
    """Outcome of a tool execution."""

    tool_name: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    task_id: Optional[str] = None  # for async tools


class OrchestratorToolRegistry:
    """Registry of tools available to the Orchestrator Agent.

    Maintains a catalogue of ``ToolDefinition`` objects and optional handler
    callables.  When ``execute()`` is called the registry delegates to the
    registered handler; if no handler exists a stub result is returned so that
    the pipeline remains functional before handlers are wired in Phase 37.

    Sprint 137: ToolSecurityGateway integration — all tool calls pass through
    security checks before execution.
    """

    def __init__(self, security_gateway: Any = None) -> None:
        self._tools: Dict[str, ToolDefinition] = {}
        self._handlers: Dict[str, Callable[..., Any]] = {}  # tool_name -> callable
        self._security_gateway = security_gateway  # Sprint 137
        self._register_builtin_tools()

    # ------------------------------------------------------------------
    # Built-in tool catalogue
    # ------------------------------------------------------------------

    def _register_builtin_tools(self) -> None:
        """Register the built-in orchestrator tools."""
        builtins: List[ToolDefinition] = [
            ToolDefinition(
                name="assess_risk",
                description="評估操作的風險等級（7 維度風險評估）",
                tool_type=ToolType.SYNC,
                parameters={"content": "str", "intent_category": "str"},
                required_role="operator",
            ),
            ToolDefinition(
                name="search_memory",
                description="搜尋用戶的歷史對話記錄和任務處理經驗",
                tool_type=ToolType.SYNC,
                parameters={
                    "query": "str",
                    "user_id": "Optional[str]",
                    "limit": "int",
                },
                required_role="viewer",
            ),
            ToolDefinition(
                name="request_approval",
                description="請求人工審批（用於高風險操作）",
                tool_type=ToolType.ASYNC_DISPATCH,
                parameters={
                    "title": "str",
                    "description": "str",
                    "risk_level": "str",
                },
                required_role="operator",
            ),
            ToolDefinition(
                name="create_task",
                description="建立長期任務記錄（跨 session 追蹤）",
                tool_type=ToolType.ASYNC_DISPATCH,
                parameters={
                    "title": "str",
                    "task_type": "str",
                    "description": "str",
                },
                required_role="operator",
            ),
            ToolDefinition(
                name="dispatch_workflow",
                description="啟動 MAF 結構化工作流（多步驟任務）",
                tool_type=ToolType.ASYNC_DISPATCH,
                parameters={"workflow_type": "str", "input_data": "dict"},
                required_role="admin",
            ),
            ToolDefinition(
                name="dispatch_swarm",
                description="啟動多 Agent 並行協作群集",
                tool_type=ToolType.ASYNC_DISPATCH,
                parameters={"task_description": "str", "worker_count": "int"},
                required_role="admin",
            ),
            ToolDefinition(
                name="update_task_status",
                description="更新任務狀態和進度",
                tool_type=ToolType.SYNC,
                parameters={
                    "task_id": "str",
                    "status": "str",
                    "progress": "Optional[float]",
                },
                required_role="operator",
            ),
            ToolDefinition(
                name="search_knowledge",
                description="搜尋企業知識庫（ITIL SOP、技術文檔、最佳實踐）",
                tool_type=ToolType.SYNC,
                parameters={
                    "query": "str",
                    "collection": "Optional[str]",
                    "limit": "int",
                },
                required_role="viewer",
            ),
        ]
        for tool in builtins:
            self._tools[tool.name] = tool

    # ------------------------------------------------------------------
    # Query API
    # ------------------------------------------------------------------

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Return a tool definition by name, or ``None``."""
        return self._tools.get(name)

    def list_tools(self, role: str = "viewer") -> List[ToolDefinition]:
        """List tools available to the given role.

        The role hierarchy is ``admin > operator > viewer``.  A user with a
        higher role can access all tools available to lower roles.
        """
        role_hierarchy: Dict[str, int] = {"admin": 3, "operator": 2, "viewer": 1}
        user_level = role_hierarchy.get(role, 0)
        return [
            t
            for t in self._tools.values()
            if role_hierarchy.get(t.required_role, 0) <= user_level
        ]

    def get_tools_prompt(self, role: str = "operator") -> str:
        """Generate a tools description section for the system prompt.

        Returns a multi-line string listing every tool the given *role* has
        access to, annotated with sync/async labels.
        """
        tools = self.list_tools(role)
        if not tools:
            return "No tools available."

        lines: List[str] = ["Available tools:"]
        for t in tools:
            sync_label = "[同步]" if t.tool_type == ToolType.SYNC else "[非同步]"
            params_str = ", ".join(f"{k}: {v}" for k, v in t.parameters.items())
            lines.append(f"- {t.name} {sync_label}: {t.description}")
            if params_str:
                lines.append(f"  Parameters: {params_str}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Handler registration & execution
    # ------------------------------------------------------------------

    def register_handler(self, tool_name: str, handler: Callable[..., Any]) -> None:
        """Register a callable handler for a tool.

        The handler will be invoked with the tool parameters as keyword
        arguments when ``execute()`` is called.
        """
        if tool_name not in self._tools:
            logger.warning(
                "Registering handler for unknown tool '%s'; "
                "consider adding a ToolDefinition first",
                tool_name,
            )
        self._handlers[tool_name] = handler

    async def execute(
        self,
        tool_name: str,
        params: Dict[str, Any],
        user_id: Optional[str] = None,
        role: str = "operator",
    ) -> ToolResult:
        """Execute a tool by name.

        If no handler has been registered for the tool a stub result is
        returned.  This allows the pipeline to function in Sprint 112 before
        real handlers are connected in Phase 37.

        Args:
            tool_name: The name of the tool to execute.
            params: Keyword arguments forwarded to the handler.
            user_id: The calling user (for future audit logging).
            role: The caller's role — used for access-control validation.

        Returns:
            A ``ToolResult`` describing the outcome.
        """
        tool_def = self._tools.get(tool_name)
        if not tool_def:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Unknown tool: {tool_name}",
            )

        # Role check
        role_hierarchy: Dict[str, int] = {"admin": 3, "operator": 2, "viewer": 1}
        if role_hierarchy.get(role, 0) < role_hierarchy.get(tool_def.required_role, 0):
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=(
                    f"Insufficient permissions: role '{role}' cannot execute "
                    f"tool '{tool_name}' (requires '{tool_def.required_role}')"
                ),
            )

        # Sprint 137: ToolSecurityGateway check
        if self._security_gateway:
            try:
                security_result = await self._run_security_check(
                    tool_name, params, user_id, role
                )
                if security_result and not security_result.get("allowed", True):
                    logger.warning(
                        "Tool '%s' blocked by SecurityGateway: %s",
                        tool_name, security_result.get("reason", "unknown"),
                    )
                    return ToolResult(
                        tool_name=tool_name,
                        success=False,
                        error=f"Security check failed: {security_result.get('reason', 'blocked')}",
                    )
            except Exception as e:
                logger.warning("SecurityGateway check error (non-blocking): %s", e)

        handler = self._handlers.get(tool_name)
        if not handler:
            # No handler registered yet — return stub for Sprint 112
            logger.warning(
                "No handler registered for tool '%s', returning stub result",
                tool_name,
            )
            return ToolResult(
                tool_name=tool_name,
                success=True,
                data={
                    "message": (
                        f"Tool '{tool_name}' acknowledged "
                        f"(handler not yet connected)"
                    ),
                },
                task_id=(
                    str(uuid.uuid4())
                    if tool_def.tool_type == ToolType.ASYNC_DISPATCH
                    else None
                ),
            )

        try:
            result = await handler(**params)
            return ToolResult(tool_name=tool_name, success=True, data=result)
        except Exception as e:
            logger.error(
                "Tool '%s' execution failed: %s", tool_name, e, exc_info=True
            )
            return ToolResult(tool_name=tool_name, success=False, error=str(e))

    async def _run_security_check(
        self,
        tool_name: str,
        params: Dict[str, Any],
        user_id: Optional[str],
        role: str,
    ) -> Optional[Dict[str, Any]]:
        """Run ToolSecurityGateway validation (Sprint 137)."""
        if self._security_gateway is None:
            return None
        try:
            if hasattr(self._security_gateway, "validate_tool_call"):
                result = await self._security_gateway.validate_tool_call(
                    tool_name=tool_name,
                    params=params,
                    user_id=user_id,
                    role=role,
                )
                return result if isinstance(result, dict) else {"allowed": bool(result)}
            if hasattr(self._security_gateway, "check"):
                result = self._security_gateway.check(
                    tool_name=tool_name,
                    params=params,
                    user_id=user_id,
                )
                return result if isinstance(result, dict) else {"allowed": bool(result)}
        except Exception as e:
            logger.warning("SecurityGateway check error: %s", e)
        return None

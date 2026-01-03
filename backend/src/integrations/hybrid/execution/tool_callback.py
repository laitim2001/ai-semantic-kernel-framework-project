# =============================================================================
# IPA Platform - MAF Tool Callback
# =============================================================================
# Sprint 54: HybridOrchestrator Refactor - S54-2
#
# MAF Tool Callback for intercepting tool calls from Microsoft Agent Framework
# and routing them through the Unified Tool Executor.
#
# This callback bridges MAF tool execution with the Claude SDK tool system,
# enabling unified tool management across both frameworks.
#
# Dependencies:
#   - UnifiedToolExecutor (src.integrations.hybrid.execution)
#   - ContextBridge (src.integrations.hybrid.context)
# =============================================================================

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Protocol, Union

from .unified_executor import (
    ToolExecutionResult,
    ToolSource,
    UnifiedToolExecutor,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Protocols and Types
# =============================================================================


class MAFToolRequest(Protocol):
    """Protocol for MAF tool request objects."""

    @property
    def function_name(self) -> str:
        """Get function/tool name."""
        ...

    @property
    def arguments(self) -> Dict[str, Any]:
        """Get tool arguments."""
        ...


@dataclass
class MAFToolResult:
    """
    Result format expected by MAF.

    Attributes:
        function_name: Name of the executed function
        output: Execution output (if successful)
        error: Error message (if failed)
        success: Whether execution succeeded
        metadata: Additional execution metadata
    """

    function_name: str
    output: Optional[str] = None
    error: Optional[str] = None
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "function_name": self.function_name,
            "output": self.output,
            "error": self.error,
            "success": self.success,
            "metadata": self.metadata,
        }


@dataclass
class CallbackConfig:
    """
    Configuration for MAFToolCallback.

    Attributes:
        intercept_all: Whether to intercept all tool calls
        allowed_tools: List of tools to intercept (if not intercept_all)
        blocked_tools: List of tools to NOT intercept
        require_approval: Tools that require human approval
        default_approval_timeout: Default timeout for approval in seconds
        enable_metrics: Whether to collect execution metrics
        fallback_on_error: Whether to fall back to MAF execution on error
    """

    intercept_all: bool = True
    allowed_tools: List[str] = field(default_factory=list)
    blocked_tools: List[str] = field(default_factory=list)
    require_approval: List[str] = field(default_factory=list)
    default_approval_timeout: int = 300  # 5 minutes
    enable_metrics: bool = True
    fallback_on_error: bool = False


class MAFToolCallback:
    """
    Callback for intercepting MAF tool calls.

    Intercepts tool execution requests from Microsoft Agent Framework
    adapters and routes them through the Unified Tool Executor.

    This enables:
    - Unified hook execution (pre/post hooks)
    - Consistent tool result format
    - Cross-framework context synchronization
    - Centralized metrics collection

    Example:
        >>> callback = MAFToolCallback(unified_executor)
        >>>
        >>> # In MAF adapter
        >>> async def execute_function(request):
        ...     result = await callback.handle(request)
        ...     return result.to_dict()
    """

    def __init__(
        self,
        unified_executor: UnifiedToolExecutor,
        config: Optional[CallbackConfig] = None,
        original_handler: Optional[Callable] = None,
    ):
        """
        Initialize MAFToolCallback.

        Args:
            unified_executor: Unified tool executor instance
            config: Callback configuration
            original_handler: Original MAF tool handler for fallback
        """
        self._executor = unified_executor
        self._config = config or CallbackConfig()
        self._original_handler = original_handler

        # Metrics
        self._call_count = 0
        self._intercept_count = 0
        self._error_count = 0
        self._fallback_count = 0

        # Execution history
        self._history: List[Dict[str, Any]] = []
        self._max_history_size = 1000

    async def handle(
        self,
        request: Union[MAFToolRequest, Dict[str, Any]],
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> MAFToolResult:
        """
        Handle a MAF tool call request.

        Args:
            request: MAF tool request (object or dict)
            session_id: Optional session identifier
            context: Optional additional context

        Returns:
            MAFToolResult with execution outcome
        """
        self._call_count += 1
        start_time = datetime.utcnow()

        # Extract request info
        if isinstance(request, dict):
            function_name = request.get("function_name", request.get("name", ""))
            arguments = request.get("arguments", request.get("params", {}))
        else:
            function_name = request.function_name
            arguments = request.arguments

        # Check if we should intercept
        if not self._should_intercept(function_name):
            return await self._passthrough(function_name, arguments)

        self._intercept_count += 1
        logger.info(f"Intercepting MAF tool call: {function_name}")

        try:
            # Check if approval required
            require_approval = function_name in self._config.require_approval

            # Execute through unified executor
            result = await self._executor.execute(
                tool_name=function_name,
                arguments=arguments,
                source=ToolSource.MAF,
                session_id=session_id,
                approval_required=require_approval,
            )

            # Convert to MAF result format
            maf_result = self._to_maf_result(result)

            # Record history
            self._record_history(
                function_name=function_name,
                arguments=arguments,
                result=maf_result,
                duration_ms=int(
                    (datetime.utcnow() - start_time).total_seconds() * 1000
                ),
                intercepted=True,
            )

            return maf_result

        except Exception as e:
            self._error_count += 1
            logger.error(f"Error in MAF tool callback: {e}", exc_info=True)

            # Fallback to original handler if configured
            if self._config.fallback_on_error and self._original_handler:
                return await self._fallback(function_name, arguments)

            # Return error result
            return MAFToolResult(
                function_name=function_name,
                output=None,
                error=str(e),
                success=False,
                metadata={"error_type": type(e).__name__},
            )

    def _should_intercept(self, function_name: str) -> bool:
        """
        Determine if a tool call should be intercepted.

        Args:
            function_name: Name of the function being called

        Returns:
            True if should intercept, False otherwise
        """
        # Check blocked list first
        if function_name in self._config.blocked_tools:
            return False

        # If intercept_all is True, intercept unless blocked
        if self._config.intercept_all:
            return True

        # Otherwise, only intercept if in allowed list
        return function_name in self._config.allowed_tools

    async def _passthrough(
        self,
        function_name: str,
        arguments: Dict[str, Any],
    ) -> MAFToolResult:
        """
        Pass through to original handler without interception.

        Args:
            function_name: Function name
            arguments: Function arguments

        Returns:
            MAFToolResult from original handler
        """
        if self._original_handler:
            try:
                result = await self._original_handler(function_name, arguments)
                if isinstance(result, dict):
                    return MAFToolResult(
                        function_name=function_name,
                        output=result.get("output"),
                        error=result.get("error"),
                        success=result.get("success", True),
                        metadata=result.get("metadata", {}),
                    )
                return result
            except Exception as e:
                return MAFToolResult(
                    function_name=function_name,
                    error=str(e),
                    success=False,
                )

        # No original handler - return error
        return MAFToolResult(
            function_name=function_name,
            error="No handler available (tool not intercepted and no fallback)",
            success=False,
        )

    async def _fallback(
        self,
        function_name: str,
        arguments: Dict[str, Any],
    ) -> MAFToolResult:
        """
        Fall back to original handler after error.

        Args:
            function_name: Function name
            arguments: Function arguments

        Returns:
            MAFToolResult from fallback execution
        """
        self._fallback_count += 1
        logger.warning(
            f"Falling back to original handler for: {function_name}"
        )

        try:
            result = await self._original_handler(function_name, arguments)
            if isinstance(result, dict):
                return MAFToolResult(
                    function_name=function_name,
                    output=result.get("output"),
                    error=result.get("error"),
                    success=result.get("success", True),
                    metadata={
                        **result.get("metadata", {}),
                        "fallback": True,
                    },
                )
            return result
        except Exception as e:
            return MAFToolResult(
                function_name=function_name,
                error=f"Fallback also failed: {e}",
                success=False,
                metadata={"fallback": True, "fallback_error": str(e)},
            )

    def _to_maf_result(self, result: ToolExecutionResult) -> MAFToolResult:
        """
        Convert ToolExecutionResult to MAFToolResult.

        Args:
            result: Unified execution result

        Returns:
            MAF-formatted result
        """
        return MAFToolResult(
            function_name=result.tool_name,
            output=result.content if result.success else None,
            error=result.error,
            success=result.success,
            metadata={
                "execution_id": result.execution_id,
                "source": result.source.value,
                "duration_ms": result.duration_ms,
                "blocked_by_hook": result.blocked_by_hook,
                "approval_denied": result.approval_denied,
                **(result.metadata or {}),
            },
        )

    def _record_history(
        self,
        function_name: str,
        arguments: Dict[str, Any],
        result: MAFToolResult,
        duration_ms: int,
        intercepted: bool,
    ) -> None:
        """Record execution in history."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "function_name": function_name,
            "arguments": arguments,
            "success": result.success,
            "duration_ms": duration_ms,
            "intercepted": intercepted,
        }

        self._history.append(entry)

        # Limit history size
        if len(self._history) > self._max_history_size:
            self._history = self._history[-self._max_history_size:]

    def get_stats(self) -> Dict[str, Any]:
        """
        Get callback statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "call_count": self._call_count,
            "intercept_count": self._intercept_count,
            "passthrough_count": self._call_count - self._intercept_count,
            "error_count": self._error_count,
            "fallback_count": self._fallback_count,
            "intercept_rate": (
                self._intercept_count / self._call_count
                if self._call_count > 0
                else 0
            ),
            "error_rate": (
                self._error_count / self._call_count
                if self._call_count > 0
                else 0
            ),
        }

    def get_history(
        self,
        limit: int = 100,
        function_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get execution history.

        Args:
            limit: Maximum number of entries to return
            function_name: Filter by function name

        Returns:
            List of history entries
        """
        history = self._history

        if function_name:
            history = [h for h in history if h["function_name"] == function_name]

        return history[-limit:]

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        self._call_count = 0
        self._intercept_count = 0
        self._error_count = 0
        self._fallback_count = 0

    def clear_history(self) -> int:
        """
        Clear execution history.

        Returns:
            Number of entries cleared
        """
        count = len(self._history)
        self._history = []
        return count


# =============================================================================
# Factory Functions
# =============================================================================


def create_maf_callback(
    unified_executor: UnifiedToolExecutor,
    intercept_all: bool = True,
    fallback_on_error: bool = False,
) -> MAFToolCallback:
    """
    Create a MAFToolCallback with common configuration.

    Args:
        unified_executor: Unified tool executor instance
        intercept_all: Whether to intercept all tools
        fallback_on_error: Whether to fall back on error

    Returns:
        Configured MAFToolCallback
    """
    config = CallbackConfig(
        intercept_all=intercept_all,
        fallback_on_error=fallback_on_error,
        enable_metrics=True,
    )

    return MAFToolCallback(
        unified_executor=unified_executor,
        config=config,
    )


def create_selective_callback(
    unified_executor: UnifiedToolExecutor,
    allowed_tools: List[str],
    require_approval: Optional[List[str]] = None,
) -> MAFToolCallback:
    """
    Create a MAFToolCallback that only intercepts specific tools.

    Args:
        unified_executor: Unified tool executor instance
        allowed_tools: List of tools to intercept
        require_approval: Tools requiring human approval

    Returns:
        Configured MAFToolCallback
    """
    config = CallbackConfig(
        intercept_all=False,
        allowed_tools=allowed_tools,
        require_approval=require_approval or [],
        enable_metrics=True,
    )

    return MAFToolCallback(
        unified_executor=unified_executor,
        config=config,
    )

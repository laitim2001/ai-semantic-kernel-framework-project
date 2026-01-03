# =============================================================================
# IPA Platform - Unified Tool Executor
# =============================================================================
# Sprint 54: HybridOrchestrator Refactor - S54-1
#
# Central tool execution layer that routes all tool calls through Claude SDK.
# Supports tools from both MAF Workflow and Claude Session.
#
# Key Features:
#   - Pre/Post hook pipeline
#   - Human approval integration
#   - Result synchronization back to source framework
#   - Metrics collection
#
# Dependencies:
#   - ContextBridge for cross-framework sync
#   - ToolRegistry for tool lookup
#   - HookChain for interception
# =============================================================================

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Types
# =============================================================================


class ToolSource(Enum):
    """Source framework of the tool call."""
    MAF = "maf"           # From MAF Workflow
    CLAUDE = "claude"     # From Claude Session
    HYBRID = "hybrid"     # From Hybrid Mode


@dataclass
class ToolExecutionResult:
    """
    Result of tool execution.

    Attributes:
        success: Whether execution succeeded
        content: Result content (if successful)
        error: Error message (if failed)
        tool_name: Name of executed tool
        execution_id: Unique execution identifier
        source: Source framework of the call
        duration_ms: Execution duration in milliseconds
        blocked_by_hook: Whether execution was blocked by a hook
        approval_denied: Whether human approval was denied
        metadata: Additional result metadata
    """
    success: bool
    content: str = ""
    error: Optional[str] = None
    tool_name: str = ""
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: ToolSource = ToolSource.CLAUDE
    duration_ms: int = 0
    blocked_by_hook: bool = False
    approval_denied: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "content": self.content,
            "error": self.error,
            "tool_name": self.tool_name,
            "execution_id": self.execution_id,
            "source": self.source.value,
            "duration_ms": self.duration_ms,
            "blocked_by_hook": self.blocked_by_hook,
            "approval_denied": self.approval_denied,
            "metadata": self.metadata,
        }


@dataclass
class HookExecutionResult:
    """Result of hook pipeline execution."""
    allowed: bool = True
    blocked: bool = False
    reason: Optional[str] = None
    requires_approval: bool = False
    modified_args: Optional[Dict[str, Any]] = None


# =============================================================================
# Exceptions
# =============================================================================


class ToolNotFoundError(Exception):
    """Raised when a requested tool is not found."""

    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        super().__init__(f"Tool '{tool_name}' not found in registry")


class ToolExecutionError(Exception):
    """Raised when tool execution fails."""

    def __init__(self, tool_name: str, error: str):
        self.tool_name = tool_name
        self.error = error
        super().__init__(f"Tool '{tool_name}' execution failed: {error}")


# =============================================================================
# Protocol Definitions
# =============================================================================


class ToolRegistryProtocol(Protocol):
    """Protocol for tool registry."""

    def get_tool_instance(self, name: str, **kwargs) -> Optional[Any]:
        """Get a tool instance by name."""
        ...

    def get_available_tools(self) -> List[str]:
        """Get list of available tool names."""
        ...


class HookChainProtocol(Protocol):
    """Protocol for hook chain."""

    async def run_tool_call(self, context: Any) -> Any:
        """Run pre-tool hooks."""
        ...

    async def run_tool_result(self, context: Any) -> None:
        """Run post-tool hooks."""
        ...


class ContextBridgeProtocol(Protocol):
    """Protocol for context bridge."""

    async def get_hybrid_context(self, session_id: str) -> Optional[Any]:
        """Get hybrid context by session ID."""
        ...


class MetricsCollectorProtocol(Protocol):
    """Protocol for metrics collection."""

    def record_tool_execution(
        self,
        tool_name: str,
        source: ToolSource,
        success: bool,
        duration: float,
    ) -> None:
        """Record tool execution metrics."""
        ...


class ApprovalServiceProtocol(Protocol):
    """Protocol for human approval service."""

    async def request_approval(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Any,
    ) -> bool:
        """Request human approval for tool execution."""
        ...


# =============================================================================
# Default Implementations
# =============================================================================


class DefaultMetricsCollector:
    """Default metrics collector (no-op implementation)."""

    def __init__(self):
        self._metrics: List[Dict[str, Any]] = []

    def record_tool_execution(
        self,
        tool_name: str,
        source: ToolSource,
        success: bool,
        duration: float,
    ) -> None:
        """Record tool execution metrics."""
        self._metrics.append({
            "tool_name": tool_name,
            "source": source.value,
            "success": success,
            "duration": duration,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def get_metrics(self) -> List[Dict[str, Any]]:
        """Get all recorded metrics."""
        return list(self._metrics)

    def clear_metrics(self) -> None:
        """Clear all metrics."""
        self._metrics.clear()


class DefaultApprovalService:
    """Default approval service (auto-approve)."""

    def __init__(self, auto_approve: bool = True):
        self._auto_approve = auto_approve
        self._pending_approvals: Dict[str, Dict[str, Any]] = {}

    async def request_approval(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Any,
    ) -> bool:
        """Request human approval for tool execution."""
        if self._auto_approve:
            return True

        approval_id = str(uuid.uuid4())
        self._pending_approvals[approval_id] = {
            "tool_name": tool_name,
            "arguments": arguments,
            "requested_at": datetime.utcnow(),
        }
        # In production, this would wait for human approval
        return True

    def get_pending_approvals(self) -> Dict[str, Dict[str, Any]]:
        """Get pending approval requests."""
        return dict(self._pending_approvals)


# =============================================================================
# UnifiedToolExecutor
# =============================================================================


class UnifiedToolExecutor:
    """
    統一 Tool 執行層

    核心設計:
    - 所有 Tool 執行通過 Claude (或直接執行)
    - MAF Workflow 的 Tool 調用被攔截並路由到這裡
    - 結果自動同步回源框架

    流程:
    1. 接收 Tool 調用請求 (來自 MAF 或 Claude)
    2. 執行 pre-hooks (Approval, Audit, Sandbox)
    3. 執行 Tool
    4. 執行 post-hooks (Logging, Result Transform)
    5. 同步結果回源框架

    Usage:
        executor = UnifiedToolExecutor(
            tool_registry=registry,
            hook_chain=hooks,
            context_bridge=bridge,
        )
        result = await executor.execute(
            tool_name="Read",
            arguments={"file_path": "/path/to/file"},
            source=ToolSource.MAF,
            session_id="session-123",
        )
    """

    def __init__(
        self,
        tool_registry: Optional[ToolRegistryProtocol] = None,
        hook_chain: Optional[HookChainProtocol] = None,
        context_bridge: Optional[ContextBridgeProtocol] = None,
        metrics_collector: Optional[MetricsCollectorProtocol] = None,
        approval_service: Optional[ApprovalServiceProtocol] = None,
    ):
        """
        Initialize UnifiedToolExecutor.

        Args:
            tool_registry: Registry for tool lookup
            hook_chain: Hook chain for pre/post processing
            context_bridge: Bridge for cross-framework sync
            metrics_collector: Collector for execution metrics
            approval_service: Service for human approvals
        """
        self._tool_registry = tool_registry
        self._hook_chain = hook_chain
        self._context_bridge = context_bridge
        self._metrics = metrics_collector or DefaultMetricsCollector()
        self._approval_service = approval_service or DefaultApprovalService()
        self._execution_log: List[Dict[str, Any]] = []

    # =========================================================================
    # Public Properties
    # =========================================================================

    @property
    def tool_registry(self) -> Optional[ToolRegistryProtocol]:
        """Get tool registry."""
        return self._tool_registry

    @property
    def hook_chain(self) -> Optional[HookChainProtocol]:
        """Get hook chain."""
        return self._hook_chain

    @property
    def context_bridge(self) -> Optional[ContextBridgeProtocol]:
        """Get context bridge."""
        return self._context_bridge

    @property
    def metrics(self) -> MetricsCollectorProtocol:
        """Get metrics collector."""
        return self._metrics

    # =========================================================================
    # Main Execution Method
    # =========================================================================

    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        source: ToolSource = ToolSource.CLAUDE,
        session_id: Optional[str] = None,
        approval_required: bool = False,
        working_directory: Optional[str] = None,
    ) -> ToolExecutionResult:
        """
        統一執行 Tool

        Args:
            tool_name: Tool 名稱
            arguments: Tool 參數
            source: 調用來源 (maf/claude/hybrid)
            session_id: 會話 ID (用於上下文獲取)
            approval_required: 是否需要人工審批
            working_directory: 工作目錄 (用於檔案操作)

        Returns:
            ToolExecutionResult: 執行結果
        """
        execution_id = str(uuid.uuid4())
        start_time = time.time()

        logger.info(
            f"Starting tool execution: tool={tool_name}, "
            f"source={source.value}, execution_id={execution_id}"
        )

        try:
            # 1. 獲取混合上下文
            hybrid_context = None
            if session_id and self._context_bridge:
                hybrid_context = await self._context_bridge.get_hybrid_context(
                    session_id
                )

            # 2. 執行 pre-hooks
            hook_result = await self._run_pre_hooks(
                tool_name, arguments, source, hybrid_context
            )
            if hook_result.blocked:
                return ToolExecutionResult(
                    success=False,
                    error=hook_result.reason or "Blocked by hook",
                    tool_name=tool_name,
                    execution_id=execution_id,
                    source=source,
                    blocked_by_hook=True,
                    duration_ms=int((time.time() - start_time) * 1000),
                )

            # 使用修改後的參數
            final_args = hook_result.modified_args or arguments

            # 3. 人工審批檢查
            if approval_required or hook_result.requires_approval:
                approved = await self._request_approval(
                    tool_name, final_args, hybrid_context
                )
                if not approved:
                    return ToolExecutionResult(
                        success=False,
                        error="Human approval denied",
                        tool_name=tool_name,
                        execution_id=execution_id,
                        source=source,
                        approval_denied=True,
                        duration_ms=int((time.time() - start_time) * 1000),
                    )

            # 4. 執行 Tool
            result = await self._execute_tool(
                tool_name, final_args, working_directory
            )

            execution_time = time.time() - start_time

            # 5. 執行 post-hooks
            await self._run_post_hooks(
                tool_name, final_args, result, source, hybrid_context
            )

            # 6. 同步結果回源框架
            if hybrid_context:
                await self._sync_result_to_source(
                    result, source, hybrid_context, session_id
                )

            # 7. 收集指標
            self._metrics.record_tool_execution(
                tool_name=tool_name,
                source=source,
                success=result.success,
                duration=execution_time,
            )

            # 8. 記錄執行日誌
            self._log_execution(
                execution_id=execution_id,
                tool_name=tool_name,
                arguments=final_args,
                source=source,
                result=result,
                duration=execution_time,
            )

            result.execution_id = execution_id
            result.duration_ms = int(execution_time * 1000)
            result.source = source  # Set source from parameter
            return result

        except ToolNotFoundError as e:
            logger.warning(f"Tool not found: {e.tool_name}")
            return ToolExecutionResult(
                success=False,
                error=str(e),
                tool_name=tool_name,
                execution_id=execution_id,
                source=source,
                duration_ms=int((time.time() - start_time) * 1000),
            )

        except Exception as e:
            logger.error(f"Tool execution failed: {e}", exc_info=True)
            return ToolExecutionResult(
                success=False,
                error=str(e),
                tool_name=tool_name,
                execution_id=execution_id,
                source=source,
                duration_ms=int((time.time() - start_time) * 1000),
            )

    async def execute_batch(
        self,
        tool_calls: List[Dict[str, Any]],
        source: ToolSource = ToolSource.CLAUDE,
        session_id: Optional[str] = None,
    ) -> List[ToolExecutionResult]:
        """
        批量執行多個 Tool

        Args:
            tool_calls: Tool 調用列表，每個包含 tool_name 和 arguments
            source: 調用來源
            session_id: 會話 ID

        Returns:
            List[ToolExecutionResult]: 執行結果列表
        """
        results = []
        for call in tool_calls:
            result = await self.execute(
                tool_name=call.get("tool_name", ""),
                arguments=call.get("arguments", {}),
                source=source,
                session_id=session_id,
                approval_required=call.get("approval_required", False),
                working_directory=call.get("working_directory"),
            )
            results.append(result)
        return results

    # =========================================================================
    # Hook Pipeline
    # =========================================================================

    async def _run_pre_hooks(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        source: ToolSource,
        hybrid_context: Optional[Any],
    ) -> HookExecutionResult:
        """
        執行 pre-hooks

        Args:
            tool_name: Tool 名稱
            arguments: Tool 參數
            source: 調用來源
            hybrid_context: 混合上下文

        Returns:
            HookExecutionResult: Hook 執行結果
        """
        if not self._hook_chain:
            return HookExecutionResult(allowed=True)

        try:
            # 建立 ToolCallContext (模擬)
            context = _ToolCallContextAdapter(
                tool_name=tool_name,
                args=arguments,
                session_id=hybrid_context.get_session_id() if hybrid_context else None,
                tool_source=source.value,
            )

            result = await self._hook_chain.run_tool_call(context)

            # 解析 HookResult
            if hasattr(result, 'is_rejected') and result.is_rejected:
                return HookExecutionResult(
                    allowed=False,
                    blocked=True,
                    reason=getattr(result, 'rejection_reason', 'Rejected by hook'),
                )

            if hasattr(result, 'is_modified') and result.is_modified:
                return HookExecutionResult(
                    allowed=True,
                    modified_args=getattr(result, 'modified_args', None),
                )

            # 檢查是否需要審批
            if hasattr(result, 'requires_approval') and result.requires_approval:
                return HookExecutionResult(
                    allowed=True,
                    requires_approval=True,
                )

            return HookExecutionResult(allowed=True)

        except Exception as e:
            logger.error(f"Pre-hook execution failed: {e}")
            return HookExecutionResult(allowed=True)

    async def _run_post_hooks(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: "ToolExecutionResult",
        source: ToolSource,
        hybrid_context: Optional[Any],
    ) -> None:
        """
        執行 post-hooks

        Args:
            tool_name: Tool 名稱
            arguments: Tool 參數
            result: 執行結果
            source: 調用來源
            hybrid_context: 混合上下文
        """
        if not self._hook_chain:
            return

        try:
            # 建立 ToolResultContext (模擬)
            context = _ToolResultContextAdapter(
                tool_name=tool_name,
                args=arguments,
                result=result.content if result.success else result.error,
                success=result.success,
                session_id=hybrid_context.get_session_id() if hybrid_context else None,
            )

            await self._hook_chain.run_tool_result(context)

        except Exception as e:
            logger.error(f"Post-hook execution failed: {e}")

    # =========================================================================
    # Tool Execution
    # =========================================================================

    async def _execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        working_directory: Optional[str] = None,
    ) -> ToolExecutionResult:
        """
        執行 Tool (通過 ToolRegistry)

        Args:
            tool_name: Tool 名稱
            arguments: Tool 參數
            working_directory: 工作目錄

        Returns:
            ToolExecutionResult: 執行結果
        """
        if not self._tool_registry:
            raise ToolNotFoundError(tool_name)

        tool = self._tool_registry.get_tool_instance(tool_name)
        if not tool:
            raise ToolNotFoundError(tool_name)

        # 處理工作目錄
        if working_directory and "path" in arguments:
            import os
            if not os.path.isabs(arguments["path"]):
                arguments["path"] = os.path.join(
                    working_directory, arguments["path"]
                )

        try:
            # 執行 Tool
            result = await tool.execute(**arguments)

            return ToolExecutionResult(
                success=result.success if hasattr(result, 'success') else True,
                content=result.content if hasattr(result, 'content') else str(result),
                error=result.error if hasattr(result, 'error') else None,
                tool_name=tool_name,
            )

        except Exception as e:
            raise ToolExecutionError(tool_name, str(e))

    # =========================================================================
    # Approval
    # =========================================================================

    async def _request_approval(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        hybrid_context: Optional[Any],
    ) -> bool:
        """
        請求人工審批

        Args:
            tool_name: Tool 名稱
            arguments: Tool 參數
            hybrid_context: 混合上下文

        Returns:
            bool: 是否已批准
        """
        return await self._approval_service.request_approval(
            tool_name, arguments, hybrid_context
        )

    # =========================================================================
    # Result Sync
    # =========================================================================

    async def _sync_result_to_source(
        self,
        result: ToolExecutionResult,
        source: ToolSource,
        hybrid_context: Any,
        session_id: Optional[str],
    ) -> None:
        """
        同步結果回源框架

        Args:
            result: 執行結果
            source: 調用來源
            hybrid_context: 混合上下文
            session_id: 會話 ID
        """
        if not self._context_bridge:
            return

        # 根據來源決定同步方向
        # MAF → 更新 MAF checkpoint
        # Claude → 更新 Claude tool_call_history
        # 這裡的實作依賴 ContextBridge 的具體方法

        logger.debug(
            f"Syncing result to source: source={source.value}, "
            f"session_id={session_id}"
        )

        # 實際同步由 ResultHandler 處理
        # 這裡只是觸發同步

    # =========================================================================
    # Logging
    # =========================================================================

    def _log_execution(
        self,
        execution_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        source: ToolSource,
        result: ToolExecutionResult,
        duration: float,
    ) -> None:
        """記錄執行日誌."""
        self._execution_log.append({
            "execution_id": execution_id,
            "tool_name": tool_name,
            "arguments": arguments,
            "source": source.value,
            "success": result.success,
            "duration": duration,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def get_execution_log(self) -> List[Dict[str, Any]]:
        """獲取執行日誌."""
        return list(self._execution_log)

    def clear_execution_log(self) -> None:
        """清除執行日誌."""
        self._execution_log.clear()

    # =========================================================================
    # Available Tools
    # =========================================================================

    def get_available_tools(self) -> List[str]:
        """獲取可用的 Tool 列表."""
        if not self._tool_registry:
            return []
        return self._tool_registry.get_available_tools()


# =============================================================================
# Context Adapters
# =============================================================================


class _ToolCallContextAdapter:
    """Adapter to create ToolCallContext-like object."""

    def __init__(
        self,
        tool_name: str,
        args: Dict[str, Any],
        session_id: Optional[str] = None,
        tool_source: str = "claude",
        mcp_server: Optional[str] = None,
    ):
        self.tool_name = tool_name
        self.args = args
        self.session_id = session_id
        self.tool_source = tool_source
        self.mcp_server = mcp_server


class _ToolResultContextAdapter:
    """Adapter to create ToolResultContext-like object."""

    def __init__(
        self,
        tool_name: str,
        args: Dict[str, Any],
        result: Any,
        success: bool,
        session_id: Optional[str] = None,
    ):
        self.tool_name = tool_name
        self.args = args
        self.result = result
        self.success = success
        self.session_id = session_id

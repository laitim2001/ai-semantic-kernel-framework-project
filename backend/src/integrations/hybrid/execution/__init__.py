# =============================================================================
# IPA Platform - Hybrid Execution Module
# =============================================================================
# Sprint 54: HybridOrchestrator Refactor
#
# Unified Tool Execution Layer for Hybrid MAF + Claude SDK Architecture.
#
# Components:
#   - UnifiedToolExecutor: Central tool execution with hooks
#   - ToolRouter: Intelligent tool routing based on source
#   - ResultHandler: Result processing and sync
#   - MAFToolCallback: Callback for MAF tool requests (S54-2)
#
# Dependencies:
#   - ContextBridge (src.integrations.hybrid.context)
#   - ToolRegistry (src.integrations.claude_sdk.tools)
#   - HookChain (src.integrations.claude_sdk.hooks)
# =============================================================================

from .unified_executor import (
    ToolSource,
    ToolExecutionResult,
    UnifiedToolExecutor,
    ToolNotFoundError,
    ToolExecutionError,
)

from .tool_router import (
    ToolRouter,
    RoutingDecision,
    RoutingRule,
    RoutingStrategy,
    create_default_router,
)

from .result_handler import (
    ResultHandler,
    ResultFormat,
    FormattedResult,
    create_default_handler,
)

from .tool_callback import (
    MAFToolCallback,
    MAFToolResult,
    CallbackConfig,
    create_maf_callback,
    create_selective_callback,
)

__all__ = [
    # Unified Executor
    "ToolSource",
    "ToolExecutionResult",
    "UnifiedToolExecutor",
    "ToolNotFoundError",
    "ToolExecutionError",
    # Tool Router
    "ToolRouter",
    "RoutingDecision",
    "RoutingRule",
    "RoutingStrategy",
    "create_default_router",
    # Result Handler
    "ResultHandler",
    "ResultFormat",
    "FormattedResult",
    "create_default_handler",
    # MAF Callback (S54-2)
    "MAFToolCallback",
    "MAFToolResult",
    "CallbackConfig",
    "create_maf_callback",
    "create_selective_callback",
]

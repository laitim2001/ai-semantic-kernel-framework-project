# =============================================================================
# IPA Platform - AG-UI Features Package
# =============================================================================
# Sprint 59: AG-UI Basic Features (1-4)
#
# Package exports for AG-UI feature handlers.
# Provides Agentic Chat, Tool Rendering, HITL, and Generative UI features.
#
# Features:
#   - Agentic Chat: Real-time streaming conversation with agents
#   - Tool Rendering: Standardized tool result formatting and display
#   - Human-in-the-Loop: Risk-based approval workflow for high-risk operations
#   - Generative UI: Progress tracking and mode switch notifications
# =============================================================================

from .agentic_chat import (
    AgenticChatHandler,
    ChatConfig,
    ChatMessage,
    ChatRole,
)
from .human_in_loop import (
    ApprovalRequest,
    ApprovalStatus,
    ApprovalStorage,
    HITLHandler,
    ToolCallInfo,
    create_hitl_handler,
    get_approval_storage,
    get_hitl_handler,
)
from .tool_rendering import (
    FormattedResult,
    ResultType,
    ToolCall,
    ToolExecutionStatus,
    ToolRenderingConfig,
    ToolRenderingHandler,
    create_tool_rendering_handler,
)
from .generative_ui import (
    GenerativeUIHandler,
    ModeSwitchInfo,
    ModeSwitchReason,
    ProgressStatus,
    WorkflowProgress,
    WorkflowStep,
    create_generative_ui_handler,
)

__all__ = [
    # S59-1: Agentic Chat
    "AgenticChatHandler",
    "ChatConfig",
    "ChatMessage",
    "ChatRole",
    # S59-2: Tool Rendering
    "FormattedResult",
    "ResultType",
    "ToolCall",
    "ToolExecutionStatus",
    "ToolRenderingConfig",
    "ToolRenderingHandler",
    "create_tool_rendering_handler",
    # S59-3: Human-in-the-Loop
    "ApprovalRequest",
    "ApprovalStatus",
    "ApprovalStorage",
    "HITLHandler",
    "ToolCallInfo",
    "create_hitl_handler",
    "get_approval_storage",
    "get_hitl_handler",
    # S59-4: Generative UI
    "GenerativeUIHandler",
    "ModeSwitchInfo",
    "ModeSwitchReason",
    "ProgressStatus",
    "WorkflowProgress",
    "WorkflowStep",
    "create_generative_ui_handler",
]

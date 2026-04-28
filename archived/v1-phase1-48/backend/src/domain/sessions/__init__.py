# Sessions Domain Module
# Session Mode API - Interactive chat functionality

from .models import (
    Session,
    SessionStatus,
    SessionConfig,
    Message,
    MessageRole,
    Attachment,
    AttachmentType,
    ToolCall,
    ToolCallStatus,
)

# Sprint 45: ExecutionEvent 系統 (S45-4)
from .events import (
    ExecutionEventType,
    ExecutionEvent,
    ExecutionEventFactory,
    ToolCallInfo,
    ToolResultInfo,
    UsageInfo,
    # Session Events (原有)
    SessionEventType,
    SessionEvent,
    SessionEventPublisher,
    get_event_publisher,
)

# Sprint 45: AgentExecutor 核心 (S45-1)
from .executor import (
    AgentExecutor,
    AgentConfig,
    ExecutionConfig,
    ExecutionResult,
    ChatMessage,
    MessageRole as ExecutorMessageRole,
    MCPClientProtocol as ExecutorMCPClientProtocol,  # Alias for executor's simpler version
    create_agent_executor,
)

# Sprint 45: LLM 串流整合 (S45-2)
from .streaming import (
    StreamingLLMHandler,
    StreamConfig,
    StreamStats,
    StreamState,
    ToolCallDelta,
    TokenCounter,
    create_streaming_handler,
)

# Sprint 45: 工具調用框架 (S45-3)
from .tool_handler import (
    ToolCallHandler,
    ToolCallParser,
    ToolHandlerConfig,
    ToolHandlerStats,
    ParsedToolCall,
    ToolExecutionResult,
    ToolSource,
    ToolPermission,
    ToolRegistryProtocol,
    MCPClientProtocol,
    ApprovalCallback,
    create_tool_handler,
)

# Sprint 46: 工具審批流程 (S46-4)
from .approval import (
    ApprovalStatus,
    ToolApprovalRequest,
    ToolApprovalManager,
    ApprovalNotFoundError,
    ApprovalAlreadyResolvedError,
    ApprovalExpiredError,
    ApprovalCacheProtocol,
    create_approval_manager,
)

# Sprint 46: SessionAgentBridge 核心 (S46-1)
from .bridge import (
    SessionAgentBridge,
    BridgeConfig,
    ProcessingContext,
    BridgeError,
    SessionNotFoundError as BridgeSessionNotFoundError,
    SessionNotActiveError as BridgeSessionNotActiveError,
    AgentNotFoundError,
    MaxIterationsExceededError,
    PendingApprovalError,
    SessionServiceProtocol,
    AgentRepositoryProtocol,
    create_session_agent_bridge,
)

__all__ = [
    # Session
    "Session",
    "SessionStatus",
    "SessionConfig",
    # Message
    "Message",
    "MessageRole",
    # Attachment
    "Attachment",
    "AttachmentType",
    # ToolCall
    "ToolCall",
    "ToolCallStatus",
    # Sprint 45: ExecutionEvent 系統 (S45-4)
    "ExecutionEventType",
    "ExecutionEvent",
    "ExecutionEventFactory",
    "ToolCallInfo",
    "ToolResultInfo",
    "UsageInfo",
    # Session Events
    "SessionEventType",
    "SessionEvent",
    "SessionEventPublisher",
    "get_event_publisher",
    # Sprint 45: AgentExecutor 核心 (S45-1)
    "AgentExecutor",
    "AgentConfig",
    "ExecutionConfig",
    "ExecutionResult",
    "ChatMessage",
    "ExecutorMessageRole",
    "ExecutorMCPClientProtocol",  # Executor's simpler MCP protocol
    "create_agent_executor",
    # Sprint 45: LLM 串流整合 (S45-2)
    "StreamingLLMHandler",
    "StreamConfig",
    "StreamStats",
    "StreamState",
    "ToolCallDelta",
    "TokenCounter",
    "create_streaming_handler",
    # Sprint 45: 工具調用框架 (S45-3)
    "ToolCallHandler",
    "ToolCallParser",
    "ToolHandlerConfig",
    "ToolHandlerStats",
    "ParsedToolCall",
    "ToolExecutionResult",
    "ToolSource",
    "ToolPermission",
    "ToolRegistryProtocol",
    "MCPClientProtocol",
    "ApprovalCallback",
    "create_tool_handler",
    # Sprint 46: 工具審批流程 (S46-4)
    "ApprovalStatus",
    "ToolApprovalRequest",
    "ToolApprovalManager",
    "ApprovalNotFoundError",
    "ApprovalAlreadyResolvedError",
    "ApprovalExpiredError",
    "ApprovalCacheProtocol",
    "create_approval_manager",
    # Sprint 46: SessionAgentBridge 核心 (S46-1)
    "SessionAgentBridge",
    "BridgeConfig",
    "ProcessingContext",
    "BridgeError",
    "BridgeSessionNotFoundError",
    "BridgeSessionNotActiveError",
    "AgentNotFoundError",
    "MaxIterationsExceededError",
    "PendingApprovalError",
    "SessionServiceProtocol",
    "AgentRepositoryProtocol",
    "create_session_agent_bridge",
]

"""Claude Agent SDK Integration.

This module provides integration with Claude Agent SDK for autonomous AI agent operations.

Sprint 48: Core SDK Integration (35 pts)
- S48-1: ClaudeSDKClient 核心封裝 (10 pts)
- S48-2: Query API 實現 (8 pts)
- S48-3: Session 管理實現 (10 pts)
- S48-4: API 端點整合 (7 pts)

Sprint 80: S80-4 - Claude Session 狀態增強 (5 pts)
- Session 狀態持久化
- 跨會話上下文恢復
- 上下文壓縮策略

Example usage:
    from src.integrations.claude_sdk import ClaudeSDKClient

    # One-shot query
    client = ClaudeSDKClient()
    result = await client.query("Analyze this code")

    # Multi-turn session
    session = await client.create_session()
    await session.query("Read the auth module")
    await session.query("What issues do you see?")
    await session.close()
"""

from .client import ClaudeSDKClient
from .config import ClaudeSDKConfig
from .session import Session
from .types import (
    ToolCall,
    Message,
    ToolCallContext,
    ToolResultContext,
    QueryContext,
    HookResult,
    QueryResult,
    SessionResponse,
    ALLOW,
)
from .exceptions import (
    ClaudeSDKError,
    AuthenticationError,
    RateLimitError,
    TimeoutError,
    ToolError,
    HookRejectionError,
    MCPError,
    MCPConnectionError,
    MCPToolError,
)

# Sprint 80: Session State Management
from .session_state import (
    SessionStateConfig,
    SessionState,
    SessionStateManager,
    DEFAULT_SESSION_STATE_CONFIG,
)

__all__ = [
    # Client
    "ClaudeSDKClient",
    "ClaudeSDKConfig",
    "Session",
    # Types
    "ToolCall",
    "Message",
    "ToolCallContext",
    "ToolResultContext",
    "QueryContext",
    "HookResult",
    "QueryResult",
    "SessionResponse",
    "ALLOW",
    # Exceptions
    "ClaudeSDKError",
    "AuthenticationError",
    "RateLimitError",
    "TimeoutError",
    "ToolError",
    "HookRejectionError",
    "MCPError",
    "MCPConnectionError",
    "MCPToolError",
    # Session State (Sprint 80)
    "SessionStateConfig",
    "SessionState",
    "SessionStateManager",
    "DEFAULT_SESSION_STATE_CONFIG",
]

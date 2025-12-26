"""Type definitions for Claude SDK."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


@dataclass
class ToolCall:
    """Represents a single tool invocation."""

    id: str
    name: str
    args: Dict[str, Any]
    result: Optional[str] = None
    success: bool = True
    duration: Optional[float] = None


@dataclass
class Message:
    """Represents a conversation message."""

    role: str  # 'user', 'assistant'
    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    timestamp: Optional[float] = None


@dataclass
class ToolCallContext:
    """Context passed to hooks for tool call interception."""

    tool_name: str
    args: Dict[str, Any]
    session_id: Optional[str] = None
    tool_source: str = "builtin"  # 'builtin' or 'mcp'
    mcp_server: Optional[str] = None


@dataclass
class ToolResultContext:
    """Context passed to hooks after tool execution."""

    tool_name: str
    result: str
    success: bool
    session_id: Optional[str] = None
    duration: Optional[float] = None


@dataclass
class QueryContext:
    """Context passed to hooks for query interception."""

    prompt: str
    session_id: Optional[str] = None
    tools: List[str] = field(default_factory=list)


class HookResult:
    """Result from a hook execution."""

    ALLOW: "HookResult" = None  # Will be set after class definition

    def __init__(
        self,
        allowed: bool = True,
        reason: Optional[str] = None,
        modified_args: Optional[Dict[str, Any]] = None,
    ):
        self.allowed = allowed
        self.reason = reason
        self.modified_args = modified_args

    @property
    def is_allowed(self) -> bool:
        return self.allowed

    @property
    def is_rejected(self) -> bool:
        return not self.allowed

    @property
    def is_modified(self) -> bool:
        return self.modified_args is not None

    @classmethod
    def reject(cls, reason: str) -> "HookResult":
        """Create a rejection result."""
        return cls(allowed=False, reason=reason)

    @classmethod
    def modify(cls, modified_args: Dict[str, Any]) -> "HookResult":
        """Create a modification result."""
        return cls(allowed=True, modified_args=modified_args)


# Set class-level ALLOW constant
HookResult.ALLOW = HookResult(allowed=True)

# Module-level constant for easier import
ALLOW = HookResult.ALLOW


@dataclass
class QueryResult:
    """Result of a one-shot query."""

    content: str
    tool_calls: List[ToolCall]
    tokens_used: int
    duration: float
    status: str  # 'success', 'error', 'timeout'
    error: Optional[str] = None

    @property
    def successful(self) -> bool:
        return self.status == "success"


@dataclass
class SessionResponse:
    """Response from a session query."""

    content: str
    tool_calls: List[ToolCall]
    tokens_used: int
    message_index: int  # Position in conversation history

"""Type definitions for Hybrid Orchestrator.

Sprint 50: S50-3 - Hybrid Orchestrator (12 pts)

This module provides type definitions for the hybrid orchestration
between Microsoft Agent Framework and Claude Agent SDK.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class TaskCapability(Enum):
    """Task required capabilities.

    Represents the capabilities needed to execute a specific task.
    Used by CapabilityMatcher to determine the best framework.
    """

    # Multi-agent collaboration
    MULTI_AGENT = "multi_agent"

    # Agent handoff and delegation
    HANDOFF = "handoff"

    # File operations (read, write, edit)
    FILE_OPERATIONS = "file_operations"

    # Code execution and scripting
    CODE_EXECUTION = "code_execution"

    # Web search and internet access
    WEB_SEARCH = "web_search"

    # Database access and queries
    DATABASE_ACCESS = "database_access"

    # Task planning and scheduling
    PLANNING = "planning"

    # Conversation and history management
    CONVERSATION = "conversation"

    # External API integrations
    API_INTEGRATION = "api_integration"

    # Document processing
    DOCUMENT_PROCESSING = "document_processing"


class Framework(Enum):
    """Supported frameworks for task execution."""

    MICROSOFT_AGENT_FRAMEWORK = "microsoft_agent_framework"
    CLAUDE_SDK = "claude_sdk"


@dataclass
class TaskAnalysis:
    """Task analysis result.

    Contains the analysis of a task prompt including identified
    capabilities, complexity score, and framework recommendation.
    """

    # Identified capabilities needed for this task
    capabilities: Set[TaskCapability] = field(default_factory=set)

    # Complexity score from 0.0 (simple) to 1.0 (complex)
    complexity: float = 0.0

    # Recommended framework for execution
    recommended_framework: str = "claude_sdk"

    # Confidence in the recommendation (0.0 to 1.0)
    confidence: float = 0.5

    # Keywords that triggered capability detection
    matched_keywords: Dict[TaskCapability, List[str]] = field(default_factory=dict)

    def requires_multi_agent(self) -> bool:
        """Check if task requires multi-agent collaboration."""
        return TaskCapability.MULTI_AGENT in self.capabilities

    def requires_handoff(self) -> bool:
        """Check if task requires agent handoff."""
        return TaskCapability.HANDOFF in self.capabilities

    def is_claude_suitable(self) -> bool:
        """Check if task is suitable for Claude SDK."""
        claude_caps = {
            TaskCapability.FILE_OPERATIONS,
            TaskCapability.CODE_EXECUTION,
            TaskCapability.WEB_SEARCH,
            TaskCapability.CONVERSATION,
        }
        return bool(self.capabilities & claude_caps)

    def is_ms_suitable(self) -> bool:
        """Check if task is suitable for Microsoft Agent Framework."""
        ms_caps = {
            TaskCapability.MULTI_AGENT,
            TaskCapability.HANDOFF,
            TaskCapability.PLANNING,
        }
        return bool(self.capabilities & ms_caps)


@dataclass
class ToolCall:
    """Record of a tool call execution."""

    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    success: bool = True
    error: Optional[str] = None
    duration_ms: float = 0.0
    framework: str = "claude_sdk"


@dataclass
class HybridResult:
    """Result from hybrid orchestration execution.

    Contains the execution result along with metadata about
    which framework was used and performance metrics.
    """

    # Response content
    content: str = ""

    # Which framework executed the task
    framework_used: str = "claude_sdk"

    # List of tool calls made during execution
    tool_calls: List[ToolCall] = field(default_factory=list)

    # Token usage
    tokens_used: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    # Execution time in seconds
    duration: float = 0.0

    # Whether execution was successful
    success: bool = True

    # Error message if failed
    error: Optional[str] = None

    # Session ID if applicable
    session_id: Optional[str] = None

    # Task analysis that led to framework selection
    task_analysis: Optional[TaskAnalysis] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "content": self.content,
            "framework_used": self.framework_used,
            "tool_calls": [
                {
                    "name": tc.name,
                    "arguments": tc.arguments,
                    "result": tc.result,
                    "success": tc.success,
                    "error": tc.error,
                    "duration_ms": tc.duration_ms,
                }
                for tc in self.tool_calls
            ],
            "tokens_used": self.tokens_used,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "duration": self.duration,
            "success": self.success,
            "error": self.error,
            "session_id": self.session_id,
        }


@dataclass
class HybridSessionConfig:
    """Configuration for a hybrid session."""

    # Primary framework to use
    primary_framework: str = "claude_sdk"

    # Whether to auto-switch frameworks based on task
    auto_switch: bool = True

    # Minimum confidence to switch frameworks
    switch_confidence_threshold: float = 0.7

    # Whether to sync context across frameworks
    sync_context: bool = True

    # Maximum messages to sync
    max_sync_messages: int = 20

    # Session timeout in seconds
    timeout: int = 3600

    # Enable streaming responses
    stream: bool = False

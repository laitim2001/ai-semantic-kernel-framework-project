"""
Shared Protocol Definitions for Cross-Module Communication.

Sprint 116: Defines Protocol-based interfaces that break circular dependencies
between orchestration (L5) and execution engine (L6) modules.

Architecture:
    Before (circular):
        L5 (orchestration) imports L6 (claude_sdk) for execution
        L6 (claude_sdk) imports L5 (orchestration) for tool callbacks

    After (acyclic):
        L5 (orchestration) depends on shared/protocols.ToolCallbackProtocol
        L6 (claude_sdk) implements shared/protocols.ToolCallbackProtocol

        L5 (orchestration) depends on shared/protocols.ExecutionEngineProtocol
        L6 (claude_sdk) implements shared/protocols.ExecutionEngineProtocol

Uses Python's typing.Protocol for structural subtyping (duck typing with type safety).
No runtime cost — Protocol checking is purely at type-check time.

Dependencies:
    - typing (Protocol, runtime_checkable)
    - Standard library only (no external dependencies)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# =============================================================================
# Data Transfer Objects (shared between L5 and L6)
# =============================================================================


class ToolCallStatus(str, Enum):
    """Status of a tool call."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ToolCallEvent:
    """
    Event data for a tool call invocation.

    Passed from L6 to L5 when a tool is invoked during execution.

    Attributes:
        tool_name: Name of the tool being called
        tool_id: Unique identifier for this tool call instance
        input_params: Parameters passed to the tool
        is_mcp: Whether this is an MCP tool
        timestamp: When the tool was called
        worker_id: Optional worker identifier (for swarm mode)
        metadata: Additional event metadata
    """

    tool_name: str
    tool_id: str
    input_params: Dict[str, Any] = field(default_factory=dict)
    is_mcp: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)
    worker_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "tool_name": self.tool_name,
            "tool_id": self.tool_id,
            "input_params": self.input_params,
            "is_mcp": self.is_mcp,
            "timestamp": self.timestamp.isoformat(),
            "worker_id": self.worker_id,
            "metadata": self.metadata,
        }


@dataclass
class ToolResultEvent:
    """
    Event data for a tool call result.

    Passed from L6 to L5 when a tool call completes.

    Attributes:
        tool_name: Name of the tool
        tool_id: Unique identifier matching the ToolCallEvent
        status: Final status of the tool call
        result: Tool execution result (if successful)
        error: Error message (if failed)
        duration_ms: Execution duration in milliseconds
        timestamp: When the result was received
        worker_id: Optional worker identifier (for swarm mode)
    """

    tool_name: str
    tool_id: str
    status: ToolCallStatus = ToolCallStatus.COMPLETED
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    worker_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "tool_name": self.tool_name,
            "tool_id": self.tool_id,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "worker_id": self.worker_id,
        }


@dataclass
class ExecutionRequest:
    """
    Request to execute a task via an execution engine.

    Passed from L5 to L6.

    Attributes:
        intent: The classified intent/task description
        context: Execution context (session state, history, etc.)
        tools: Available tools for execution
        max_tokens: Token limit for response
        timeout: Execution timeout in seconds
        session_id: Session identifier for state tracking
        metadata: Additional request metadata
    """

    intent: str
    context: Dict[str, Any] = field(default_factory=dict)
    tools: Optional[List[Dict[str, Any]]] = None
    max_tokens: Optional[int] = None
    timeout: Optional[float] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "intent": self.intent,
            "context": self.context,
            "tools": self.tools,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
            "session_id": self.session_id,
            "metadata": self.metadata,
        }


@dataclass
class ExecutionResult:
    """
    Result from an execution engine.

    Returned from L6 to L5.

    Attributes:
        success: Whether execution completed successfully
        content: Response content
        error: Error message (if failed)
        framework_used: Which framework processed the request
        tool_calls: List of tool calls made during execution
        tokens_used: Total tokens consumed
        duration_ms: Execution duration in milliseconds
        metadata: Additional result metadata
    """

    success: bool
    content: str = ""
    error: Optional[str] = None
    framework_used: str = ""
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tokens_used: int = 0
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "success": self.success,
            "content": self.content,
            "error": self.error,
            "framework_used": self.framework_used,
            "tool_calls": self.tool_calls,
            "tokens_used": self.tokens_used,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


@dataclass
class SwarmEvent:
    """
    Event data for swarm coordination events.

    Used by SwarmCallbackProtocol to communicate swarm state changes.

    Attributes:
        event_type: Type of swarm event
        swarm_id: Swarm identifier
        worker_id: Optional worker identifier
        data: Event-specific data
        timestamp: When the event occurred
    """

    event_type: str
    swarm_id: str
    worker_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "event_type": self.event_type,
            "swarm_id": self.swarm_id,
            "worker_id": self.worker_id,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }


# =============================================================================
# Protocol Definitions
# =============================================================================


@runtime_checkable
class ToolCallbackProtocol(Protocol):
    """
    Protocol for tool call callbacks.

    Implemented by L5 (orchestration/hybrid) to receive notifications
    from L6 (claude_sdk/agent_framework) about tool call events.

    Example:
        class MyToolHandler:
            async def on_tool_call(self, event: ToolCallEvent) -> Dict[str, Any]:
                logger.info(f"Tool called: {event.tool_name}")
                return {"approved": True}

            async def on_tool_result(self, event: ToolResultEvent) -> None:
                logger.info(f"Tool completed: {event.tool_name}")

        # Structural subtyping — no explicit inheritance needed
        handler: ToolCallbackProtocol = MyToolHandler()  # Works!
    """

    async def on_tool_call(
        self, event: ToolCallEvent
    ) -> Dict[str, Any]:
        """
        Called when a tool is invoked.

        Args:
            event: Tool call event data

        Returns:
            Dictionary with callback response (e.g., {"approved": True})
        """
        ...

    async def on_tool_result(
        self, event: ToolResultEvent
    ) -> None:
        """
        Called when a tool call completes.

        Args:
            event: Tool result event data
        """
        ...


@runtime_checkable
class ExecutionEngineProtocol(Protocol):
    """
    Protocol for execution engines.

    Implemented by L6 (claude_sdk/agent_framework) to provide
    execution capabilities to L5 (orchestration/hybrid).

    Example:
        class ClaudeEngine:
            async def execute(self, request: ExecutionRequest) -> ExecutionResult:
                response = await self.client.messages.create(...)
                return ExecutionResult(success=True, content=response.content)

            async def is_available(self) -> bool:
                return self.client is not None

        # Structural subtyping
        engine: ExecutionEngineProtocol = ClaudeEngine()
    """

    async def execute(
        self, request: ExecutionRequest
    ) -> ExecutionResult:
        """
        Execute a task.

        Args:
            request: Execution request with intent and context

        Returns:
            ExecutionResult with outcome
        """
        ...

    async def is_available(self) -> bool:
        """
        Check if the engine is available and ready.

        Returns:
            True if the engine can accept requests
        """
        ...


@runtime_checkable
class OrchestrationCallbackProtocol(Protocol):
    """
    Protocol for orchestration callbacks.

    Implemented by L5 (orchestration/hybrid) to receive lifecycle
    notifications from L6 execution engines.
    """

    async def on_execution_started(
        self, request: ExecutionRequest
    ) -> None:
        """Called when execution begins."""
        ...

    async def on_execution_completed(
        self, result: ExecutionResult
    ) -> None:
        """Called when execution completes."""
        ...

    async def on_execution_error(
        self, request: ExecutionRequest, error: str
    ) -> None:
        """Called when execution encounters an error."""
        ...


@runtime_checkable
class SwarmCallbackProtocol(Protocol):
    """
    Protocol for swarm coordination callbacks.

    Implemented by L5 to receive swarm lifecycle events
    from L6 (claude_sdk coordinator).
    """

    async def on_swarm_event(
        self, event: SwarmEvent
    ) -> None:
        """
        Called when a swarm event occurs.

        Args:
            event: Swarm event data
        """
        ...


# =============================================================================
# Utility: Protocol compliance checker
# =============================================================================


def check_protocol_compliance(
    instance: Any,
    protocol: type,
) -> Dict[str, Any]:
    """
    Check if an instance complies with a Protocol.

    Useful for runtime validation and debugging.

    Args:
        instance: Object to check
        protocol: Protocol class to check against

    Returns:
        Dictionary with compliance info:
            - compliant: bool
            - missing_methods: List[str]
            - protocol_name: str
            - checked_methods: List[str]
    """
    protocol_name = getattr(protocol, "__name__", str(protocol))

    # Get protocol methods (excluding dunder and private)
    protocol_methods: List[str] = []
    for name in dir(protocol):
        if name.startswith("_"):
            continue
        member = getattr(protocol, name, None)
        if callable(member):
            protocol_methods.append(name)

    # Check instance for each required method
    missing: List[str] = []
    for method_name in protocol_methods:
        if not hasattr(instance, method_name):
            missing.append(method_name)
        elif not callable(getattr(instance, method_name)):
            missing.append(f"{method_name} (not callable)")

    return {
        "compliant": len(missing) == 0,
        "missing_methods": missing,
        "protocol_name": protocol_name,
        "checked_methods": protocol_methods,
    }

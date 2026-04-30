"""
Agent Swarm Data Models

This module defines the core data structures for the Agent Swarm visualization system.
These models represent the state and execution details of multi-agent collaboration.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import json


class WorkerType(str, Enum):
    """Worker type enumeration.

    Defines the specialized roles that workers can take in a swarm.
    """
    RESEARCH = "research"
    WRITER = "writer"
    DESIGNER = "designer"
    REVIEWER = "reviewer"
    COORDINATOR = "coordinator"
    ANALYST = "analyst"
    CODER = "coder"
    TESTER = "tester"
    CUSTOM = "custom"


class WorkerStatus(str, Enum):
    """Worker execution status enumeration.

    Represents the current state of a worker's execution lifecycle.
    """
    PENDING = "pending"
    RUNNING = "running"
    THINKING = "thinking"
    TOOL_CALLING = "tool_calling"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SwarmMode(str, Enum):
    """Swarm execution mode enumeration.

    Defines how workers in a swarm coordinate their execution.
    """
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HIERARCHICAL = "hierarchical"


class SwarmStatus(str, Enum):
    """Swarm overall status enumeration.

    Represents the current state of the entire swarm's execution.
    """
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ToolCallStatus(str, Enum):
    """Tool call status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ToolCallInfo:
    """Information about a single tool call.

    Tracks the invocation and result of a tool call made by a worker.

    Attributes:
        tool_id: Unique identifier for this tool call instance.
        tool_name: Name of the tool being called.
        is_mcp: Whether this is an MCP (Model Context Protocol) tool.
        input_params: Parameters passed to the tool.
        status: Current status of the tool call.
        result: Result returned by the tool (if completed).
        error: Error message (if failed).
        started_at: When the tool call started.
        completed_at: When the tool call completed.
        duration_ms: Duration of the tool call in milliseconds.
    """
    tool_id: str
    tool_name: str
    is_mcp: bool
    input_params: Dict[str, Any]
    status: str = ToolCallStatus.PENDING.value
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with datetime serialization."""
        data = asdict(self)
        if data["started_at"]:
            data["started_at"] = data["started_at"].isoformat()
        if data["completed_at"]:
            data["completed_at"] = data["completed_at"].isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolCallInfo":
        """Create instance from dictionary."""
        if data.get("started_at") and isinstance(data["started_at"], str):
            data["started_at"] = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at") and isinstance(data["completed_at"], str):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])
        return cls(**data)


@dataclass
class ThinkingContent:
    """Extended Thinking content block.

    Represents a piece of Claude's extended thinking output.

    Attributes:
        content: The thinking text content.
        timestamp: When this thinking was generated.
        token_count: Number of tokens in this thinking block.
    """
    content: str
    timestamp: datetime
    token_count: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with datetime serialization."""
        return {
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "token_count": self.token_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ThinkingContent":
        """Create instance from dictionary."""
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


@dataclass
class WorkerMessage:
    """A message in the worker's conversation history.

    Attributes:
        role: The role of the message sender (user, assistant).
        content: The message content.
        timestamp: When this message was created.
        thinking: Associated thinking content (for assistant messages).
    """
    role: str
    content: str
    timestamp: datetime
    thinking: Optional[List[ThinkingContent]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with datetime serialization."""
        data = {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.thinking:
            data["thinking"] = [t.to_dict() for t in self.thinking]
        else:
            data["thinking"] = None
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkerMessage":
        """Create instance from dictionary."""
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        if data.get("thinking"):
            data["thinking"] = [
                ThinkingContent.from_dict(t) for t in data["thinking"]
            ]
        return cls(**data)


@dataclass
class WorkerExecution:
    """Execution state of a single worker in the swarm.

    Tracks all aspects of a worker's execution including progress,
    tool calls, thinking content, and messages.

    Attributes:
        worker_id: Unique identifier for this worker.
        worker_name: Display name of the worker.
        worker_type: Type/role of the worker.
        role: Descriptive role in the current task.
        status: Current execution status.
        progress: Progress percentage (0-100).
        current_task: Description of current task.
        tool_calls: List of tool calls made by this worker.
        thinking_contents: List of extended thinking blocks.
        messages: Conversation history.
        started_at: When execution started.
        completed_at: When execution completed.
        error: Error message if failed.
        metadata: Additional metadata.
    """
    worker_id: str
    worker_name: str
    worker_type: WorkerType
    role: str
    status: WorkerStatus
    progress: int = 0
    current_task: Optional[str] = None
    tool_calls: List[ToolCallInfo] = field(default_factory=list)
    thinking_contents: List[ThinkingContent] = field(default_factory=list)
    messages: List[WorkerMessage] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with datetime serialization."""
        return {
            "worker_id": self.worker_id,
            "worker_name": self.worker_name,
            "worker_type": self.worker_type.value if isinstance(self.worker_type, WorkerType) else self.worker_type,
            "role": self.role,
            "status": self.status.value if isinstance(self.status, WorkerStatus) else self.status,
            "progress": self.progress,
            "current_task": self.current_task,
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "thinking_contents": [tc.to_dict() for tc in self.thinking_contents],
            "messages": [m.to_dict() for m in self.messages],
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkerExecution":
        """Create instance from dictionary."""
        # Convert enums
        if isinstance(data.get("worker_type"), str):
            data["worker_type"] = WorkerType(data["worker_type"])
        if isinstance(data.get("status"), str):
            data["status"] = WorkerStatus(data["status"])

        # Convert datetimes
        if data.get("started_at") and isinstance(data["started_at"], str):
            data["started_at"] = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at") and isinstance(data["completed_at"], str):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])

        # Convert nested objects
        if data.get("tool_calls"):
            data["tool_calls"] = [
                ToolCallInfo.from_dict(tc) if isinstance(tc, dict) else tc
                for tc in data["tool_calls"]
            ]
        if data.get("thinking_contents"):
            data["thinking_contents"] = [
                ThinkingContent.from_dict(tc) if isinstance(tc, dict) else tc
                for tc in data["thinking_contents"]
            ]
        if data.get("messages"):
            data["messages"] = [
                WorkerMessage.from_dict(m) if isinstance(m, dict) else m
                for m in data["messages"]
            ]

        return cls(**data)

    def get_tool_calls_count(self) -> int:
        """Get total number of tool calls."""
        return len(self.tool_calls)

    def get_completed_tool_calls_count(self) -> int:
        """Get number of completed tool calls."""
        return len([
            tc for tc in self.tool_calls
            if tc.status == ToolCallStatus.COMPLETED.value
        ])


@dataclass
class AgentSwarmStatus:
    """Overall status of an Agent Swarm execution.

    Represents the complete state of a multi-agent swarm including
    all workers and their execution details.

    Attributes:
        swarm_id: Unique identifier for this swarm.
        mode: Execution mode (sequential, parallel, hierarchical).
        status: Overall swarm status.
        overall_progress: Combined progress percentage (0-100).
        workers: List of worker executions.
        total_tool_calls: Total number of tool calls across all workers.
        completed_tool_calls: Number of completed tool calls.
        started_at: When the swarm started.
        completed_at: When the swarm completed.
        metadata: Additional metadata.
    """
    swarm_id: str
    mode: SwarmMode
    status: SwarmStatus
    overall_progress: int
    workers: List[WorkerExecution]
    total_tool_calls: int
    completed_tool_calls: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with datetime serialization."""
        return {
            "swarm_id": self.swarm_id,
            "mode": self.mode.value if isinstance(self.mode, SwarmMode) else self.mode,
            "status": self.status.value if isinstance(self.status, SwarmStatus) else self.status,
            "overall_progress": self.overall_progress,
            "workers": [w.to_dict() for w in self.workers],
            "total_tool_calls": self.total_tool_calls,
            "completed_tool_calls": self.completed_tool_calls,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentSwarmStatus":
        """Create instance from dictionary."""
        # Convert enums
        if isinstance(data.get("mode"), str):
            data["mode"] = SwarmMode(data["mode"])
        if isinstance(data.get("status"), str):
            data["status"] = SwarmStatus(data["status"])

        # Convert datetimes
        if data.get("started_at") and isinstance(data["started_at"], str):
            data["started_at"] = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at") and isinstance(data["completed_at"], str):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])

        # Convert workers
        if data.get("workers"):
            data["workers"] = [
                WorkerExecution.from_dict(w) if isinstance(w, dict) else w
                for w in data["workers"]
            ]

        return cls(**data)

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "AgentSwarmStatus":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def get_worker_by_id(self, worker_id: str) -> Optional[WorkerExecution]:
        """Find a worker by ID."""
        for worker in self.workers:
            if worker.worker_id == worker_id:
                return worker
        return None

    def get_active_workers(self) -> List[WorkerExecution]:
        """Get all workers that are currently active."""
        active_statuses = {WorkerStatus.RUNNING, WorkerStatus.THINKING, WorkerStatus.TOOL_CALLING}
        return [w for w in self.workers if w.status in active_statuses]

    def get_completed_workers(self) -> List[WorkerExecution]:
        """Get all workers that have completed."""
        return [w for w in self.workers if w.status == WorkerStatus.COMPLETED]

    def get_failed_workers(self) -> List[WorkerExecution]:
        """Get all workers that have failed."""
        return [w for w in self.workers if w.status == WorkerStatus.FAILED]

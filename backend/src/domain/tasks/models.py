"""Task domain models — persistent task tracking across sessions.

Provides the core Task entity used by the Orchestrator to track dispatched
work items (workflows, Claude worker tasks, swarm coordination).

Sprint 113 — Phase 37 E2E Assembly B.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Lifecycle states for a task."""

    PENDING = "pending"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Execution priority levels."""

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class TaskType(str, Enum):
    """Dispatch target type."""

    WORKFLOW = "workflow"           # MAF Workflow Engine
    CLAUDE_WORKER = "claude_worker"  # Claude SDK Worker Pool
    SWARM = "swarm"                # Multi-Agent Swarm
    MANUAL = "manual"              # User-created task
    APPROVAL = "approval"          # HITL Approval task


class TaskResult(BaseModel):
    """Unified result format returned by any worker."""

    task_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    completed_at: Optional[datetime] = None


class Task(BaseModel):
    """Core task entity tracked by the Task Registry.

    Persisted in PostgreSQL via TaskStore for cross-session durability.
    """

    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str = ""
    task_type: TaskType = TaskType.MANUAL
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL

    # Assignment
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    assigned_agent: Optional[str] = None

    # Execution data
    input_params: Dict[str, Any] = Field(default_factory=dict)
    partial_results: List[Dict[str, Any]] = Field(default_factory=list)
    final_result: Optional[TaskResult] = None
    checkpoint_data: Dict[str, Any] = Field(default_factory=dict)

    # Progress
    progress: float = 0.0  # 0.0 - 1.0

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def mark_started(self) -> None:
        """Transition task to in-progress."""
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def mark_completed(self, result: Optional[TaskResult] = None) -> None:
        """Transition task to completed."""
        self.status = TaskStatus.COMPLETED
        self.progress = 1.0
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        if result:
            self.final_result = result

    def mark_failed(self, error: str) -> None:
        """Transition task to failed."""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.final_result = TaskResult(
            task_id=self.task_id,
            success=False,
            error=error,
            completed_at=datetime.utcnow(),
        )

    def update_progress(self, progress: float, partial: Optional[Dict[str, Any]] = None) -> None:
        """Update task progress and optionally append partial results."""
        self.progress = min(max(progress, 0.0), 1.0)
        self.updated_at = datetime.utcnow()
        if partial:
            self.partial_results.append(partial)

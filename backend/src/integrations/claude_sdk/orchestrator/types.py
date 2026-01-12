# =============================================================================
# IPA Platform - Claude Orchestrator Types
# =============================================================================
# Sprint 81: S81-1 - Claude 主導的多 Agent 協調 (10 pts)
#
# This module defines the data types for Claude-led multi-agent coordination.
# =============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class TaskComplexity(str, Enum):
    """Task complexity levels."""

    SIMPLE = "simple"  # Single agent can handle
    MODERATE = "moderate"  # 2-3 agents needed
    COMPLEX = "complex"  # 4+ agents needed
    CRITICAL = "critical"  # Requires special coordination


class ExecutionMode(str, Enum):
    """Execution mode for multi-agent tasks."""

    SEQUENTIAL = "sequential"  # Execute one after another
    PARALLEL = "parallel"  # Execute simultaneously
    PIPELINE = "pipeline"  # Output of one feeds into next
    HYBRID = "hybrid"  # Mix of parallel and sequential


class AgentStatus(str, Enum):
    """Agent availability status."""

    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


class SubtaskStatus(str, Enum):
    """Subtask execution status."""

    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CoordinationStatus(str, Enum):
    """Overall coordination status."""

    INITIALIZING = "initializing"
    ANALYZING = "analyzing"
    ALLOCATING = "allocating"
    EXECUTING = "executing"
    AGGREGATING = "aggregating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentInfo:
    """Information about an agent."""

    agent_id: str
    name: str
    description: str = ""
    capabilities: List[str] = field(default_factory=list)
    skills: Dict[str, float] = field(default_factory=dict)  # skill -> proficiency (0-1)
    max_concurrent_tasks: int = 5
    current_load: int = 0
    status: AgentStatus = AgentStatus.AVAILABLE
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def availability_score(self) -> float:
        """Calculate availability score (0-1)."""
        if self.status != AgentStatus.AVAILABLE:
            return 0.0
        if self.max_concurrent_tasks == 0:
            return 0.0
        return 1.0 - (self.current_load / self.max_concurrent_tasks)

    def can_handle(self, required_capabilities: List[str]) -> bool:
        """Check if agent can handle required capabilities."""
        return all(cap in self.capabilities for cap in required_capabilities)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "skills": self.skills,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "current_load": self.current_load,
            "status": self.status.value,
            "availability_score": self.availability_score,
            "metadata": self.metadata,
        }


@dataclass
class ComplexTask:
    """A complex task that may require multiple agents."""

    task_id: str
    description: str
    requirements: List[str] = field(default_factory=list)  # Required capabilities
    priority: int = 5  # 1-10, higher is more important
    deadline: Optional[datetime] = None
    context: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "description": self.description,
            "requirements": self.requirements,
            "priority": self.priority,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "context": self.context,
            "constraints": self.constraints,
            "metadata": self.metadata,
        }


@dataclass
class TaskAnalysis:
    """Result of analyzing a complex task."""

    task_id: str
    complexity: TaskComplexity
    execution_mode: ExecutionMode
    required_capabilities: List[str]
    subtask_count: int
    estimated_duration_seconds: int
    can_parallel: bool
    dependencies: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "complexity": self.complexity.value,
            "execution_mode": self.execution_mode.value,
            "required_capabilities": self.required_capabilities,
            "subtask_count": self.subtask_count,
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "can_parallel": self.can_parallel,
            "dependencies": self.dependencies,
            "risk_factors": self.risk_factors,
            "reasoning": self.reasoning,
        }


@dataclass
class Subtask:
    """A subtask assigned to a specific agent."""

    subtask_id: str
    parent_task_id: str
    description: str
    assigned_agent_id: Optional[str] = None
    required_capabilities: List[str] = field(default_factory=list)
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None
    depends_on: List[str] = field(default_factory=list)  # Subtask IDs
    status: SubtaskStatus = SubtaskStatus.PENDING
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "subtask_id": self.subtask_id,
            "parent_task_id": self.parent_task_id,
            "description": self.description,
            "assigned_agent_id": self.assigned_agent_id,
            "required_capabilities": self.required_capabilities,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "depends_on": self.depends_on,
            "status": self.status.value,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class AgentSelection:
    """Result of agent selection."""

    agent: AgentInfo
    subtask: Subtask
    capability_score: float
    availability_score: float
    overall_score: float
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent": self.agent.to_dict(),
            "subtask": self.subtask.to_dict(),
            "capability_score": self.capability_score,
            "availability_score": self.availability_score,
            "overall_score": self.overall_score,
            "reasoning": self.reasoning,
        }


@dataclass
class SubtaskResult:
    """Result from executing a subtask."""

    subtask_id: str
    agent_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    execution_time_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "subtask_id": self.subtask_id,
            "agent_id": self.agent_id,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "execution_time_seconds": self.execution_time_seconds,
            "metadata": self.metadata,
        }


@dataclass
class CoordinationResult:
    """Final result of multi-agent coordination."""

    task_id: str
    status: CoordinationStatus
    subtask_results: List[SubtaskResult] = field(default_factory=list)
    aggregated_output: Any = None
    total_execution_time_seconds: float = 0.0
    agents_used: List[str] = field(default_factory=list)
    success_rate: float = 0.0
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "subtask_results": [r.to_dict() for r in self.subtask_results],
            "aggregated_output": self.aggregated_output,
            "total_execution_time_seconds": self.total_execution_time_seconds,
            "agents_used": self.agents_used,
            "success_rate": self.success_rate,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class CoordinationContext:
    """Context passed between coordination phases."""

    task: ComplexTask
    analysis: Optional[TaskAnalysis] = None
    subtasks: List[Subtask] = field(default_factory=list)
    selections: List[AgentSelection] = field(default_factory=list)
    results: List[SubtaskResult] = field(default_factory=list)
    shared_data: Dict[str, Any] = field(default_factory=dict)

    def update_shared_data(self, key: str, value: Any) -> None:
        """Update shared data."""
        self.shared_data[key] = value

    def get_shared_data(self, key: str, default: Any = None) -> Any:
        """Get shared data."""
        return self.shared_data.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task": self.task.to_dict(),
            "analysis": self.analysis.to_dict() if self.analysis else None,
            "subtasks": [s.to_dict() for s in self.subtasks],
            "selections": [s.to_dict() for s in self.selections],
            "results": [r.to_dict() for r in self.results],
            "shared_data": self.shared_data,
        }

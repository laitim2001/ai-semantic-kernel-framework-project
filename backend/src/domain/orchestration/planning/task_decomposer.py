# =============================================================================
# IPA Platform - Task Decomposer
# =============================================================================
# Sprint 10: S10-1 TaskDecomposer (8 points)
#
# Intelligent task decomposition using LLM to break down complex tasks into
# executable subtasks with dependency analysis and execution ordering.
#
# Features:
# - 4 decomposition strategies: hierarchical, sequential, parallel, hybrid
# - Automatic dependency detection and execution order calculation
# - Confidence scoring for decomposition quality assessment
# - Refinement capability based on feedback
# =============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol
from uuid import UUID, uuid4
import json


class TaskPriority(str, Enum):
    """Task priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    READY = "ready"           # Dependencies satisfied, can execute
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"       # Dependencies not satisfied


class DependencyType(str, Enum):
    """Types of task dependencies."""
    FINISH_TO_START = "finish_to_start"    # Predecessor must finish before successor starts
    START_TO_START = "start_to_start"      # Tasks can start together
    FINISH_TO_FINISH = "finish_to_finish"  # Tasks should finish together
    DATA_DEPENDENCY = "data_dependency"    # Requires data from predecessor


class DecompositionStrategy(str, Enum):
    """Task decomposition strategies."""
    HIERARCHICAL = "hierarchical"
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HYBRID = "hybrid"


class LLMServiceProtocol(Protocol):
    """Protocol for LLM service interface."""

    async def generate(self, prompt: str, max_tokens: int = 2000) -> str:
        """Generate text from a prompt."""
        ...


class AgentRegistryProtocol(Protocol):
    """Protocol for agent registry interface."""

    def get_agent_capabilities(self, agent_id: str) -> List[str]:
        """Get capabilities of an agent."""
        ...

    def find_agents_by_capability(self, capability: str) -> List[str]:
        """Find agents with a specific capability."""
        ...


@dataclass
class SubTask:
    """
    Represents a subtask in a task decomposition.

    Contains all information needed to execute and track a subtask,
    including dependencies, timing estimates, and execution state.
    """
    id: UUID
    parent_task_id: UUID
    name: str
    description: str
    priority: TaskPriority
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent_id: Optional[str] = None
    dependencies: List[UUID] = field(default_factory=list)
    dependency_type: DependencyType = DependencyType.FINISH_TO_START
    estimated_duration_minutes: int = 0
    actual_duration_minutes: Optional[int] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert subtask to dictionary representation."""
        return {
            "id": str(self.id),
            "parent_task_id": str(self.parent_task_id),
            "name": self.name,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "assigned_agent_id": self.assigned_agent_id,
            "dependencies": [str(d) for d in self.dependencies],
            "dependency_type": self.dependency_type.value,
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "actual_duration_minutes": self.actual_duration_minutes,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
        }

    def is_ready(self, completed_task_ids: set) -> bool:
        """Check if this subtask is ready to execute based on completed dependencies."""
        if self.status != TaskStatus.PENDING:
            return False
        return all(dep_id in completed_task_ids for dep_id in self.dependencies)

    def mark_ready(self) -> None:
        """Mark this subtask as ready to execute."""
        self.status = TaskStatus.READY

    def mark_in_progress(self) -> None:
        """Mark this subtask as in progress."""
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = datetime.utcnow()

    def mark_completed(self, outputs: Optional[Dict[str, Any]] = None) -> None:
        """Mark this subtask as completed."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.actual_duration_minutes = int(
                (self.completed_at - self.started_at).total_seconds() / 60
            )
        if outputs:
            self.outputs = outputs

    def mark_failed(self, error_message: str) -> None:
        """Mark this subtask as failed."""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message


@dataclass
class DecompositionResult:
    """
    Result of a task decomposition operation.

    Contains the decomposed subtasks, execution order, and quality metrics.
    """
    task_id: UUID
    original_task: str
    subtasks: List[SubTask]
    execution_order: List[List[UUID]]  # Layered execution order (parallel within layers)
    estimated_total_duration: int
    confidence_score: float  # Decomposition quality score 0-1
    decomposition_strategy: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert decomposition result to dictionary."""
        return {
            "task_id": str(self.task_id),
            "original_task": self.original_task,
            "subtasks": [t.to_dict() for t in self.subtasks],
            "execution_order": [[str(tid) for tid in layer] for layer in self.execution_order],
            "estimated_total_duration": self.estimated_total_duration,
            "confidence_score": self.confidence_score,
            "decomposition_strategy": self.decomposition_strategy,
            "metadata": self.metadata,
        }

    def get_ready_tasks(self, completed_task_ids: Optional[set] = None) -> List[SubTask]:
        """Get subtasks that are ready to execute."""
        completed = completed_task_ids or set()
        return [t for t in self.subtasks if t.is_ready(completed)]

    def get_progress(self) -> Dict[str, Any]:
        """Get current progress of the decomposition execution."""
        total = len(self.subtasks)
        completed = sum(1 for t in self.subtasks if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in self.subtasks if t.status == TaskStatus.FAILED)
        in_progress = sum(1 for t in self.subtasks if t.status == TaskStatus.IN_PROGRESS)

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "pending": total - completed - failed - in_progress,
            "progress_percentage": (completed / total * 100) if total > 0 else 0,
        }


class TaskDecomposer:
    """
    Intelligent Task Decomposer.

    Uses LLM to decompose complex tasks into executable subtasks with
    automatic dependency detection and execution ordering.

    Supports four decomposition strategies:
    - Hierarchical: Break into major phases, then subdivide each phase
    - Sequential: Linear step-by-step decomposition
    - Parallel: Independent tasks that can run concurrently
    - Hybrid: Smart combination of sequential and parallel (default)
    """

    def __init__(
        self,
        llm_service: Optional[LLMServiceProtocol] = None,
        agent_registry: Optional[AgentRegistryProtocol] = None,
        max_subtasks: int = 20,
        max_depth: int = 3
    ):
        """
        Initialize the TaskDecomposer.

        Args:
            llm_service: LLM service for intelligent decomposition
            agent_registry: Agent registry for capability matching
            max_subtasks: Maximum number of subtasks allowed
            max_depth: Maximum decomposition depth
        """
        self.llm_service = llm_service
        self.agent_registry = agent_registry
        self.max_subtasks = max_subtasks
        self.max_depth = max_depth

        # Decomposition strategies
        self._strategies: Dict[str, Callable] = {
            "hierarchical": self._decompose_hierarchical,
            "sequential": self._decompose_sequential,
            "parallel": self._decompose_parallel,
            "hybrid": self._decompose_hybrid,
        }

    async def decompose(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
        strategy: str = "hybrid"
    ) -> DecompositionResult:
        """
        Decompose a task into subtasks.

        Args:
            task_description: Description of the task to decompose
            context: Optional context information
            strategy: Decomposition strategy to use

        Returns:
            DecompositionResult containing subtasks and execution order
        """
        task_id = uuid4()

        # Select decomposition strategy
        decompose_fn = self._strategies.get(strategy, self._decompose_hybrid)

        # Execute decomposition
        subtasks = await decompose_fn(task_id, task_description, context)

        # Analyze dependency relationships and execution order
        execution_order = self._analyze_execution_order(subtasks)

        # Estimate total duration
        total_duration = self._estimate_total_duration(subtasks, execution_order)

        # Calculate confidence score
        confidence = await self._calculate_confidence(task_description, subtasks)

        return DecompositionResult(
            task_id=task_id,
            original_task=task_description,
            subtasks=subtasks,
            execution_order=execution_order,
            estimated_total_duration=total_duration,
            confidence_score=confidence,
            decomposition_strategy=strategy,
            metadata={"context": context} if context else {}
        )

    async def _decompose_hierarchical(
        self,
        task_id: UUID,
        task_description: str,
        context: Optional[Dict[str, Any]]
    ) -> List[SubTask]:
        """Hierarchical decomposition - break into phases, then subdivide."""
        prompt = self._build_decomposition_prompt(
            task_description,
            context,
            approach="hierarchical"
        )

        if self.llm_service:
            response = await self.llm_service.generate(
                prompt=prompt,
                max_tokens=2000
            )
            return self._parse_decomposition_response(task_id, response)

        # Fallback: simple rule-based decomposition
        return self._rule_based_decomposition(task_id, task_description, "hierarchical")

    async def _decompose_sequential(
        self,
        task_id: UUID,
        task_description: str,
        context: Optional[Dict[str, Any]]
    ) -> List[SubTask]:
        """Sequential decomposition - linear step-by-step."""
        prompt = self._build_decomposition_prompt(
            task_description,
            context,
            approach="sequential"
        )

        if self.llm_service:
            response = await self.llm_service.generate(
                prompt=prompt,
                max_tokens=2000
            )
            subtasks = self._parse_decomposition_response(task_id, response)
        else:
            subtasks = self._rule_based_decomposition(task_id, task_description, "sequential")

        # Set sequential dependencies
        for i in range(1, len(subtasks)):
            subtasks[i].dependencies = [subtasks[i - 1].id]

        return subtasks

    async def _decompose_parallel(
        self,
        task_id: UUID,
        task_description: str,
        context: Optional[Dict[str, Any]]
    ) -> List[SubTask]:
        """Parallel decomposition - independent concurrent tasks."""
        prompt = self._build_decomposition_prompt(
            task_description,
            context,
            approach="parallel"
        )

        if self.llm_service:
            response = await self.llm_service.generate(
                prompt=prompt,
                max_tokens=2000
            )
            subtasks = self._parse_decomposition_response(task_id, response)
        else:
            subtasks = self._rule_based_decomposition(task_id, task_description, "parallel")

        # Parallel tasks have no mutual dependencies
        return subtasks

    async def _decompose_hybrid(
        self,
        task_id: UUID,
        task_description: str,
        context: Optional[Dict[str, Any]]
    ) -> List[SubTask]:
        """
        Hybrid decomposition.

        Combines hierarchical and parallel approaches, intelligently
        identifying which tasks can run in parallel.
        """
        prompt = f"""
        Analyze the following task and decompose it into subtasks.
        Identify which tasks can run in parallel and which must run sequentially.

        Task: {task_description}

        Context: {context if context else "No additional context"}

        Return the decomposition in JSON format:
        {{
            "subtasks": [
                {{
                    "name": "Subtask name",
                    "description": "Detailed description",
                    "priority": "high/medium/low",
                    "dependencies": ["Names of dependent subtasks"],
                    "estimated_minutes": 30,
                    "required_capabilities": ["capability1", "capability2"]
                }}
            ],
            "reasoning": "Decomposition reasoning"
        }}

        Guidelines:
        1. Number of subtasks should be between 3-{self.max_subtasks}
        2. Identify true dependencies, avoid over-serialization
        3. Consider task atomicity and testability
        4. Priority should be based on business impact and dependencies
        """

        if self.llm_service:
            response = await self.llm_service.generate(
                prompt=prompt,
                max_tokens=3000
            )
            return self._parse_decomposition_response(task_id, response)

        return self._rule_based_decomposition(task_id, task_description, "hybrid")

    def _build_decomposition_prompt(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]],
        approach: str
    ) -> str:
        """Build the decomposition prompt for LLM."""
        approach_instructions = {
            "hierarchical": "Use hierarchical approach - break into major phases, then subdivide each phase",
            "sequential": "Decompose by execution order - each step depends on the previous",
            "parallel": "Identify independent tasks that can run concurrently"
        }

        return f"""
        Task Decomposition Request:

        Task Description: {task_description}
        Decomposition Method: {approach_instructions.get(approach, "")}
        Context: {context if context else "None"}

        Return a JSON formatted list of subtasks with the following structure:
        {{
            "subtasks": [
                {{
                    "name": "Subtask name",
                    "description": "Detailed description",
                    "priority": "high/medium/low",
                    "dependencies": [],
                    "estimated_minutes": 30
                }}
            ]
        }}
        """

    def _parse_decomposition_response(
        self,
        task_id: UUID,
        response: str
    ) -> List[SubTask]:
        """Parse LLM decomposition response into SubTask objects."""
        try:
            # Try to extract JSON from the response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
                subtasks_data = data.get("subtasks", [])
            else:
                subtasks_data = []
        except json.JSONDecodeError:
            # Fallback: try to extract tasks from text
            subtasks_data = self._extract_tasks_from_text(response)

        subtasks = []
        name_to_id: Dict[str, UUID] = {}

        for task_data in subtasks_data[:self.max_subtasks]:
            subtask_id = uuid4()
            name = task_data.get("name", f"Subtask {len(subtasks) + 1}")
            name_to_id[name] = subtask_id

            priority_str = task_data.get("priority", "medium").lower()
            try:
                priority = TaskPriority(priority_str)
            except ValueError:
                priority = TaskPriority.MEDIUM

            subtask = SubTask(
                id=subtask_id,
                parent_task_id=task_id,
                name=name,
                description=task_data.get("description", ""),
                priority=priority,
                estimated_duration_minutes=task_data.get("estimated_minutes", 30),
                metadata={
                    "required_capabilities": task_data.get("required_capabilities", [])
                }
            )
            subtasks.append(subtask)

        # Resolve dependency names to IDs
        for i, task_data in enumerate(subtasks_data[:self.max_subtasks]):
            dep_names = task_data.get("dependencies", [])
            subtasks[i].dependencies = [
                name_to_id[name] for name in dep_names
                if name in name_to_id
            ]

        return subtasks

    def _extract_tasks_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract task information from plain text response."""
        tasks = []
        lines = text.strip().split('\n')

        for line in lines:
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('*') or
                        (line[0].isdigit() if line else False)):
                task_text = line.lstrip('-*0123456789. ')
                if task_text:
                    tasks.append({
                        "name": task_text[:50],
                        "description": task_text,
                        "priority": "medium"
                    })

        return tasks

    def _rule_based_decomposition(
        self,
        task_id: UUID,
        task_description: str,
        strategy: str
    ) -> List[SubTask]:
        """
        Rule-based fallback decomposition when LLM is not available.

        Creates a simple decomposition based on common task patterns.
        """
        # Default subtasks for common task types
        default_subtasks = [
            ("Analysis", "Analyze requirements and current state", TaskPriority.HIGH),
            ("Design", "Design the solution approach", TaskPriority.HIGH),
            ("Implementation", "Implement the solution", TaskPriority.MEDIUM),
            ("Testing", "Test the implementation", TaskPriority.MEDIUM),
            ("Documentation", "Document the changes", TaskPriority.LOW),
        ]

        subtasks = []
        prev_id: Optional[UUID] = None

        for name, description, priority in default_subtasks:
            subtask_id = uuid4()
            dependencies = [prev_id] if prev_id and strategy == "sequential" else []

            subtask = SubTask(
                id=subtask_id,
                parent_task_id=task_id,
                name=name,
                description=f"{description} for: {task_description[:50]}...",
                priority=priority,
                dependencies=dependencies,
                estimated_duration_minutes=30,
            )
            subtasks.append(subtask)
            prev_id = subtask_id

        return subtasks

    def _analyze_execution_order(
        self,
        subtasks: List[SubTask]
    ) -> List[List[UUID]]:
        """
        Analyze execution order using topological sort.

        Returns layered task IDs where tasks in the same layer can run in parallel.
        """
        if not subtasks:
            return []

        # Build task index
        task_index = {task.id: task for task in subtasks}

        # Calculate in-degree for each task
        in_degree: Dict[UUID, int] = {task.id: 0 for task in subtasks}
        for task in subtasks:
            for dep_id in task.dependencies:
                if dep_id in in_degree:
                    in_degree[task.id] += 1

        # Topological sort with layering
        execution_order: List[List[UUID]] = []
        remaining = set(in_degree.keys())

        while remaining:
            # Find tasks with zero in-degree (ready to execute)
            ready = [
                task_id for task_id in remaining
                if in_degree[task_id] == 0
            ]

            if not ready:
                # Circular dependency detected - break the cycle
                ready = [min(remaining)]

            execution_order.append(ready)

            # Update in-degrees
            for task_id in ready:
                remaining.remove(task_id)
                for other_task in subtasks:
                    if task_id in other_task.dependencies:
                        in_degree[other_task.id] -= 1

        return execution_order

    def _estimate_total_duration(
        self,
        subtasks: List[SubTask],
        execution_order: List[List[UUID]]
    ) -> int:
        """
        Estimate total execution time.

        Considers parallel execution within layers - takes the maximum
        duration from each layer.
        """
        if not subtasks or not execution_order:
            return 0

        task_index = {task.id: task for task in subtasks}
        total = 0

        for layer in execution_order:
            # For each layer, take the maximum duration (parallel execution)
            if layer:
                layer_max = max(
                    task_index[task_id].estimated_duration_minutes
                    for task_id in layer
                    if task_id in task_index
                )
                total += layer_max

        return total

    async def _calculate_confidence(
        self,
        original_task: str,
        subtasks: List[SubTask]
    ) -> float:
        """
        Calculate decomposition confidence score.

        Based on multiple factors:
        - Subtask count reasonableness
        - Description completeness
        - Dependency structure quality
        """
        if not subtasks:
            return 0.0

        factors = []

        # 1. Subtask count reasonableness
        task_count = len(subtasks)
        if 3 <= task_count <= 10:
            factors.append(1.0)
        elif 2 <= task_count <= 15:
            factors.append(0.8)
        else:
            factors.append(0.5)

        # 2. Description completeness
        described = sum(1 for t in subtasks if len(t.description) > 20)
        factors.append(described / len(subtasks))

        # 3. Dependency structure quality (not all tasks should be isolated)
        has_deps = sum(1 for t in subtasks if t.dependencies)
        if len(subtasks) > 1:
            # Some dependencies expected but not all tasks should depend on others
            dep_ratio = has_deps / (len(subtasks) - 1)
            factors.append(min(dep_ratio * 1.5, 1.0))  # Boost but cap at 1.0
        else:
            factors.append(1.0)

        # 4. Priority distribution (should have variety)
        priorities = set(t.priority for t in subtasks)
        factors.append(len(priorities) / 4)  # 4 priority levels

        return sum(factors) / len(factors)

    async def refine_decomposition(
        self,
        result: DecompositionResult,
        feedback: str
    ) -> DecompositionResult:
        """
        Refine decomposition based on feedback.

        Args:
            result: Original decomposition result
            feedback: Improvement feedback

        Returns:
            Refined decomposition result
        """
        prompt = f"""
        Original Task: {result.original_task}

        Current Decomposition:
        {json.dumps([t.to_dict() for t in result.subtasks], indent=2)}

        Feedback: {feedback}

        Please improve the task decomposition based on the feedback.
        Return an updated JSON formatted subtask list.
        """

        if self.llm_service:
            response = await self.llm_service.generate(
                prompt=prompt,
                max_tokens=3000
            )
            new_subtasks = self._parse_decomposition_response(result.task_id, response)
        else:
            # Without LLM, return the original result
            new_subtasks = result.subtasks

        new_execution_order = self._analyze_execution_order(new_subtasks)

        return DecompositionResult(
            task_id=result.task_id,
            original_task=result.original_task,
            subtasks=new_subtasks,
            execution_order=new_execution_order,
            estimated_total_duration=self._estimate_total_duration(
                new_subtasks, new_execution_order
            ),
            confidence_score=await self._calculate_confidence(
                result.original_task, new_subtasks
            ),
            decomposition_strategy=result.decomposition_strategy,
            metadata={**result.metadata, "refined": True, "feedback": feedback}
        )

    def get_task_by_id(
        self,
        result: DecompositionResult,
        task_id: UUID
    ) -> Optional[SubTask]:
        """Get a specific subtask by ID from a decomposition result."""
        return next((t for t in result.subtasks if t.id == task_id), None)

    def update_task_status(
        self,
        result: DecompositionResult,
        task_id: UUID,
        status: TaskStatus,
        outputs: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update a subtask's status in the decomposition result.

        Returns True if the task was found and updated.
        """
        task = self.get_task_by_id(result, task_id)
        if not task:
            return False

        if status == TaskStatus.COMPLETED:
            task.mark_completed(outputs)
        elif status == TaskStatus.FAILED:
            task.mark_failed(error_message or "Unknown error")
        elif status == TaskStatus.IN_PROGRESS:
            task.mark_in_progress()
        elif status == TaskStatus.READY:
            task.mark_ready()
        else:
            task.status = status

        return True

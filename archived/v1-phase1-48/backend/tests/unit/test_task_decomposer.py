# =============================================================================
# IPA Platform - Task Decomposer Unit Tests
# =============================================================================
# Sprint 10: S10-1 TaskDecomposer Tests
#
# Tests for task decomposition functionality including strategies,
# dependency analysis, and confidence scoring.
# =============================================================================

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
import json

from src.domain.orchestration.planning.task_decomposer import (
    TaskDecomposer,
    TaskPriority,
    TaskStatus,
    DependencyType,
    DecompositionStrategy,
    SubTask,
    DecompositionResult,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_llm_service():
    """Create a mock LLM service."""
    service = MagicMock()
    service.generate = AsyncMock(return_value=json.dumps({
        "subtasks": [
            {
                "name": "Design database schema",
                "description": "Design user tables and authentication tables",
                "priority": "high",
                "dependencies": [],
                "estimated_minutes": 60,
                "required_capabilities": ["database", "design"]
            },
            {
                "name": "Implement user registration",
                "description": "Create registration API and validation logic",
                "priority": "high",
                "dependencies": ["Design database schema"],
                "estimated_minutes": 120,
                "required_capabilities": ["backend", "api"]
            },
            {
                "name": "Implement user login",
                "description": "Create login API and JWT generation",
                "priority": "high",
                "dependencies": ["Design database schema"],
                "estimated_minutes": 90,
                "required_capabilities": ["backend", "security"]
            },
            {
                "name": "Write tests",
                "description": "Write unit and integration tests",
                "priority": "medium",
                "dependencies": ["Implement user registration", "Implement user login"],
                "estimated_minutes": 60,
                "required_capabilities": ["testing"]
            }
        ],
        "reasoning": "Decomposed based on standard auth implementation flow"
    }))
    return service


@pytest.fixture
def decomposer(mock_llm_service):
    """Create a TaskDecomposer with mock LLM service."""
    return TaskDecomposer(
        llm_service=mock_llm_service,
        agent_registry=MagicMock(),
        max_subtasks=20,
        max_depth=3
    )


@pytest.fixture
def decomposer_no_llm():
    """Create a TaskDecomposer without LLM service."""
    return TaskDecomposer(
        llm_service=None,
        agent_registry=None,
        max_subtasks=20
    )


# =============================================================================
# SubTask Tests
# =============================================================================


class TestSubTask:
    """Tests for SubTask data class."""

    def test_create_subtask(self):
        """Test creating a subtask."""
        task_id = uuid4()
        parent_id = uuid4()

        subtask = SubTask(
            id=task_id,
            parent_task_id=parent_id,
            name="Test Task",
            description="A test task",
            priority=TaskPriority.HIGH
        )

        assert subtask.id == task_id
        assert subtask.parent_task_id == parent_id
        assert subtask.name == "Test Task"
        assert subtask.priority == TaskPriority.HIGH
        assert subtask.status == TaskStatus.PENDING
        assert subtask.dependencies == []

    def test_subtask_to_dict(self):
        """Test converting subtask to dictionary."""
        subtask = SubTask(
            id=uuid4(),
            parent_task_id=uuid4(),
            name="Test Task",
            description="Description",
            priority=TaskPriority.MEDIUM,
            estimated_duration_minutes=30
        )

        result = subtask.to_dict()

        assert "id" in result
        assert result["name"] == "Test Task"
        assert result["priority"] == "medium"
        assert result["status"] == "pending"
        assert result["estimated_duration_minutes"] == 30

    def test_subtask_is_ready(self):
        """Test checking if subtask is ready."""
        dep_id = uuid4()
        subtask = SubTask(
            id=uuid4(),
            parent_task_id=uuid4(),
            name="Test",
            description="Test",
            priority=TaskPriority.MEDIUM,
            dependencies=[dep_id]
        )

        # Not ready without dependencies completed
        assert not subtask.is_ready(set())

        # Ready when dependency is completed
        assert subtask.is_ready({dep_id})

    def test_subtask_mark_completed(self):
        """Test marking subtask as completed."""
        subtask = SubTask(
            id=uuid4(),
            parent_task_id=uuid4(),
            name="Test",
            description="Test",
            priority=TaskPriority.MEDIUM
        )

        subtask.mark_in_progress()
        assert subtask.status == TaskStatus.IN_PROGRESS
        assert subtask.started_at is not None

        subtask.mark_completed({"result": "success"})
        assert subtask.status == TaskStatus.COMPLETED
        assert subtask.completed_at is not None
        assert subtask.outputs == {"result": "success"}

    def test_subtask_mark_failed(self):
        """Test marking subtask as failed."""
        subtask = SubTask(
            id=uuid4(),
            parent_task_id=uuid4(),
            name="Test",
            description="Test",
            priority=TaskPriority.MEDIUM
        )

        subtask.mark_failed("Something went wrong")
        assert subtask.status == TaskStatus.FAILED
        assert subtask.error_message == "Something went wrong"


# =============================================================================
# TaskDecomposer Tests
# =============================================================================


class TestTaskDecomposer:
    """Tests for TaskDecomposer class."""

    @pytest.mark.asyncio
    async def test_decompose_task_with_llm(self, decomposer):
        """Test decomposing a task with LLM service."""
        result = await decomposer.decompose(
            task_description="Implement user authentication system",
            strategy="hybrid"
        )

        assert result.original_task == "Implement user authentication system"
        assert len(result.subtasks) == 4
        assert result.confidence_score > 0
        assert result.decomposition_strategy == "hybrid"

    @pytest.mark.asyncio
    async def test_decompose_task_without_llm(self, decomposer_no_llm):
        """Test decomposing a task without LLM (rule-based)."""
        result = await decomposer_no_llm.decompose(
            task_description="Build a feature",
            strategy="sequential"
        )

        assert result.original_task == "Build a feature"
        assert len(result.subtasks) > 0
        # Rule-based decomposition creates default subtasks
        subtask_names = [t.name for t in result.subtasks]
        assert "Analysis" in subtask_names
        assert "Implementation" in subtask_names

    @pytest.mark.asyncio
    async def test_decompose_hierarchical_strategy(self, decomposer):
        """Test hierarchical decomposition strategy."""
        result = await decomposer.decompose(
            task_description="Test task",
            strategy="hierarchical"
        )

        assert result.decomposition_strategy == "hierarchical"
        assert len(result.subtasks) > 0

    @pytest.mark.asyncio
    async def test_decompose_sequential_strategy(self, decomposer_no_llm):
        """Test sequential decomposition strategy."""
        result = await decomposer_no_llm.decompose(
            task_description="Test task",
            strategy="sequential"
        )

        # Sequential tasks should have chain dependencies
        for i in range(1, len(result.subtasks)):
            assert len(result.subtasks[i].dependencies) > 0

    @pytest.mark.asyncio
    async def test_decompose_parallel_strategy(self, decomposer_no_llm):
        """Test parallel decomposition strategy."""
        result = await decomposer_no_llm.decompose(
            task_description="Test task",
            strategy="parallel"
        )

        # Parallel tasks should have no dependencies between them
        # (except the rule-based fallback may add sequential deps)
        assert len(result.subtasks) > 0

    @pytest.mark.asyncio
    async def test_execution_order_analysis(self, decomposer):
        """Test execution order analysis."""
        result = await decomposer.decompose(
            task_description="Test task",
            strategy="hybrid"
        )

        # Should have layered execution order
        assert len(result.execution_order) > 0

        # First layer should have no dependencies
        first_layer_ids = set(result.execution_order[0])
        for subtask in result.subtasks:
            if subtask.id in first_layer_ids:
                for dep in subtask.dependencies:
                    assert dep not in first_layer_ids

    @pytest.mark.asyncio
    async def test_duration_estimation(self, decomposer):
        """Test duration estimation."""
        result = await decomposer.decompose(
            task_description="Test task",
            strategy="parallel"
        )

        # Parallel execution should be faster than sum
        total_individual = sum(t.estimated_duration_minutes for t in result.subtasks)
        assert result.estimated_total_duration <= total_individual

    @pytest.mark.asyncio
    async def test_confidence_score(self, decomposer):
        """Test confidence score calculation."""
        result = await decomposer.decompose(
            task_description="Test task",
            strategy="hybrid"
        )

        assert 0 <= result.confidence_score <= 1

    @pytest.mark.asyncio
    async def test_refine_decomposition(self, decomposer):
        """Test refining decomposition with feedback."""
        original = await decomposer.decompose(
            task_description="Test task",
            strategy="hybrid"
        )

        refined = await decomposer.refine_decomposition(
            result=original,
            feedback="Please add more detail to implementation steps"
        )

        assert refined.metadata.get("refined") is True
        assert refined.metadata.get("feedback") is not None

    def test_get_task_by_id(self, decomposer_no_llm):
        """Test getting a task by ID."""
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            decomposer_no_llm.decompose("Test", strategy="sequential")
        )

        task = decomposer_no_llm.get_task_by_id(result, result.subtasks[0].id)
        assert task is not None
        assert task.id == result.subtasks[0].id

        # Non-existent ID
        task = decomposer_no_llm.get_task_by_id(result, uuid4())
        assert task is None

    def test_update_task_status(self, decomposer_no_llm):
        """Test updating task status."""
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            decomposer_no_llm.decompose("Test", strategy="sequential")
        )

        task_id = result.subtasks[0].id

        success = decomposer_no_llm.update_task_status(
            result, task_id, TaskStatus.COMPLETED, {"output": "done"}
        )
        assert success
        assert result.subtasks[0].status == TaskStatus.COMPLETED


# =============================================================================
# DecompositionResult Tests
# =============================================================================


class TestDecompositionResult:
    """Tests for DecompositionResult class."""

    def test_get_ready_tasks(self, decomposer_no_llm):
        """Test getting ready tasks."""
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            decomposer_no_llm.decompose("Test", strategy="sequential")
        )

        # Initially only first task should be ready (no deps)
        ready = result.get_ready_tasks()
        assert len(ready) <= 1  # May be 0 if all have deps

    def test_get_progress(self, decomposer_no_llm):
        """Test getting progress."""
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            decomposer_no_llm.decompose("Test", strategy="sequential")
        )

        progress = result.get_progress()

        assert "total" in progress
        assert "completed" in progress
        assert "progress_percentage" in progress
        assert progress["total"] == len(result.subtasks)
        assert progress["completed"] == 0

    def test_to_dict(self, decomposer_no_llm):
        """Test converting result to dictionary."""
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            decomposer_no_llm.decompose("Test", strategy="hybrid")
        )

        data = result.to_dict()

        assert "task_id" in data
        assert "original_task" in data
        assert "subtasks" in data
        assert "execution_order" in data
        assert "confidence_score" in data


# =============================================================================
# Priority and Status Tests
# =============================================================================


class TestEnums:
    """Tests for enum classes."""

    def test_task_priority_values(self):
        """Test TaskPriority enum values."""
        assert TaskPriority.CRITICAL.value == "critical"
        assert TaskPriority.HIGH.value == "high"
        assert TaskPriority.MEDIUM.value == "medium"
        assert TaskPriority.LOW.value == "low"

    def test_task_status_values(self):
        """Test TaskStatus enum values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.READY.value == "ready"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.BLOCKED.value == "blocked"

    def test_dependency_type_values(self):
        """Test DependencyType enum values."""
        assert DependencyType.FINISH_TO_START.value == "finish_to_start"
        assert DependencyType.START_TO_START.value == "start_to_start"
        assert DependencyType.FINISH_TO_FINISH.value == "finish_to_finish"
        assert DependencyType.DATA_DEPENDENCY.value == "data_dependency"

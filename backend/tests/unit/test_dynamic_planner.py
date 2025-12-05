# =============================================================================
# IPA Platform - Dynamic Planner Unit Tests
# =============================================================================
# Sprint 10: S10-2 DynamicPlanner Tests
#
# Tests for dynamic planning functionality including plan creation,
# execution, replanning, and event handling.
# =============================================================================

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timedelta

from src.domain.orchestration.planning.dynamic_planner import (
    DynamicPlanner,
    PlanStatus,
    PlanEvent,
    PlanAdjustment,
    ExecutionPlan,
)
from src.domain.orchestration.planning.task_decomposer import (
    TaskDecomposer,
    TaskStatus,
    SubTask,
    TaskPriority,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_decomposer():
    """Create a mock TaskDecomposer."""
    decomposer = MagicMock(spec=TaskDecomposer)
    decomposer.decompose = AsyncMock()
    return decomposer


@pytest.fixture
def mock_decision_engine():
    """Create a mock decision engine."""
    engine = MagicMock()
    engine.make_decision = AsyncMock(return_value={
        "action": "retry_failed_tasks",
        "confidence": "high",
        "reasoning": "Retry is the best option"
    })
    return engine


@pytest.fixture
def planner(mock_decomposer, mock_decision_engine):
    """Create a DynamicPlanner with mocked dependencies."""
    return DynamicPlanner(
        task_decomposer=mock_decomposer,
        decision_engine=mock_decision_engine,
        require_approval_for_changes=False
    )


@pytest.fixture
def planner_with_approval(mock_decomposer, mock_decision_engine):
    """Create a DynamicPlanner that requires approval."""
    return DynamicPlanner(
        task_decomposer=mock_decomposer,
        decision_engine=mock_decision_engine,
        require_approval_for_changes=True
    )


# =============================================================================
# PlanAdjustment Tests
# =============================================================================


class TestPlanAdjustment:
    """Tests for PlanAdjustment data class."""

    def test_create_adjustment(self):
        """Test creating a plan adjustment."""
        plan_id = uuid4()
        adjustment = PlanAdjustment(
            id=uuid4(),
            plan_id=plan_id,
            trigger_event=PlanEvent.TASK_FAILED,
            original_state={"status": "executing"},
            new_state={"status": "replanning"},
            reason="Task failed, need to replan"
        )

        assert adjustment.plan_id == plan_id
        assert adjustment.trigger_event == PlanEvent.TASK_FAILED
        assert adjustment.approved is False
        assert adjustment.approved_by is None

    def test_approve_adjustment(self):
        """Test approving an adjustment."""
        adjustment = PlanAdjustment(
            id=uuid4(),
            plan_id=uuid4(),
            trigger_event=PlanEvent.TASK_FAILED,
            original_state={},
            new_state={},
            reason="Test"
        )

        adjustment.approve("admin")

        assert adjustment.approved is True
        assert adjustment.approved_by == "admin"
        assert adjustment.approved_at is not None

    def test_adjustment_to_dict(self):
        """Test converting adjustment to dictionary."""
        adjustment = PlanAdjustment(
            id=uuid4(),
            plan_id=uuid4(),
            trigger_event=PlanEvent.NEW_INFORMATION,
            original_state={"a": 1},
            new_state={"b": 2},
            reason="Updated info"
        )

        data = adjustment.to_dict()

        assert "id" in data
        assert "plan_id" in data
        assert data["trigger_event"] == "new_information"
        assert data["reason"] == "Updated info"


# =============================================================================
# DynamicPlanner Tests
# =============================================================================


class TestDynamicPlanner:
    """Tests for DynamicPlanner class."""

    @pytest.mark.asyncio
    async def test_create_plan(self, planner, mock_decomposer):
        """Test creating a plan."""
        from src.domain.orchestration.planning.task_decomposer import DecompositionResult

        # Setup mock decomposition result
        task_id = uuid4()
        subtask = SubTask(
            id=uuid4(),
            parent_task_id=task_id,
            name="Test Subtask",
            description="A test subtask",
            priority=TaskPriority.HIGH
        )
        mock_result = MagicMock(spec=DecompositionResult)
        mock_result.task_id = task_id
        mock_result.subtasks = [subtask]
        mock_result.execution_order = [[subtask.id]]
        mock_result.estimated_total_duration = 30
        mock_result.confidence_score = 0.8
        mock_result.decomposition_strategy = "hybrid"
        mock_result.get_progress.return_value = {
            "total": 1,
            "completed": 0,
            "progress_percentage": 0
        }

        mock_decomposer.decompose.return_value = mock_result

        plan = await planner.create_plan(
            goal="Build a test feature",
            context={"priority": "high"}
        )

        assert plan.goal == "Build a test feature"
        assert plan.status == PlanStatus.DRAFT
        assert plan.progress_percentage == 0.0

    @pytest.mark.asyncio
    async def test_approve_plan(self, planner, mock_decomposer):
        """Test approving a plan."""
        from src.domain.orchestration.planning.task_decomposer import DecompositionResult

        # Create a plan first
        mock_result = MagicMock(spec=DecompositionResult)
        mock_result.task_id = uuid4()
        mock_result.subtasks = []
        mock_result.execution_order = []
        mock_result.estimated_total_duration = 0
        mock_decomposer.decompose.return_value = mock_result

        plan = await planner.create_plan(goal="Test")

        # Approve it
        await planner.approve_plan(plan.id, "admin")

        assert plan.status == PlanStatus.APPROVED
        assert plan.metadata.get("approved_by") == "admin"

    @pytest.mark.asyncio
    async def test_approve_plan_not_found(self, planner):
        """Test approving a non-existent plan."""
        with pytest.raises(ValueError) as exc_info:
            await planner.approve_plan(uuid4(), "admin")

        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_plan_status(self, planner, mock_decomposer):
        """Test getting plan status."""
        from src.domain.orchestration.planning.task_decomposer import DecompositionResult

        mock_result = MagicMock(spec=DecompositionResult)
        mock_result.task_id = uuid4()
        mock_result.subtasks = []
        mock_result.execution_order = []
        mock_decomposer.decompose.return_value = mock_result

        plan = await planner.create_plan(goal="Test")

        status = planner.get_plan_status(plan.id)

        assert status["id"] == str(plan.id)
        assert status["status"] == "draft"
        assert "progress" in status

    def test_get_plan_status_not_found(self, planner):
        """Test getting status of non-existent plan."""
        status = planner.get_plan_status(uuid4())
        assert "error" in status

    @pytest.mark.asyncio
    async def test_pause_plan(self, planner, mock_decomposer):
        """Test pausing a plan."""
        from src.domain.orchestration.planning.task_decomposer import DecompositionResult

        mock_result = MagicMock(spec=DecompositionResult)
        mock_result.task_id = uuid4()
        mock_result.subtasks = []
        mock_result.execution_order = []
        mock_decomposer.decompose.return_value = mock_result

        plan = await planner.create_plan(goal="Test")
        await planner.approve_plan(plan.id, "admin")

        # Manually set to executing
        plan.status = PlanStatus.EXECUTING

        await planner.pause_plan(plan.id)

        assert plan.status == PlanStatus.PAUSED

    @pytest.mark.asyncio
    async def test_list_plans(self, planner, mock_decomposer):
        """Test listing plans."""
        from src.domain.orchestration.planning.task_decomposer import DecompositionResult

        mock_result = MagicMock(spec=DecompositionResult)
        mock_result.task_id = uuid4()
        mock_result.subtasks = []
        mock_result.execution_order = []
        mock_decomposer.decompose.return_value = mock_result

        # Create multiple plans
        await planner.create_plan(goal="Test 1")
        await planner.create_plan(goal="Test 2")

        plans = planner.list_plans()

        assert len(plans) >= 2

    @pytest.mark.asyncio
    async def test_delete_plan(self, planner, mock_decomposer):
        """Test deleting a plan."""
        from src.domain.orchestration.planning.task_decomposer import DecompositionResult

        mock_result = MagicMock(spec=DecompositionResult)
        mock_result.task_id = uuid4()
        mock_result.subtasks = []
        mock_result.execution_order = []
        mock_decomposer.decompose.return_value = mock_result

        plan = await planner.create_plan(goal="Test")

        assert planner.delete_plan(plan.id) is True
        assert planner.get_plan(plan.id) is None

    def test_delete_plan_not_found(self, planner):
        """Test deleting a non-existent plan."""
        assert planner.delete_plan(uuid4()) is False

    @pytest.mark.asyncio
    async def test_event_handler_registration(self, planner):
        """Test registering event handlers."""
        handler_called = []

        def handler(plan, task):
            handler_called.append(True)

        planner.on_event(PlanEvent.PLAN_CREATED, handler)

        # Trigger by creating a plan
        from src.domain.orchestration.planning.task_decomposer import DecompositionResult

        planner.decomposer.decompose = AsyncMock()
        mock_result = MagicMock(spec=DecompositionResult)
        mock_result.task_id = uuid4()
        mock_result.subtasks = []
        mock_result.execution_order = []
        planner.decomposer.decompose.return_value = mock_result

        await planner.create_plan(goal="Test")

        assert len(handler_called) == 1

    @pytest.mark.asyncio
    async def test_event_handler_removal(self, planner):
        """Test removing event handlers."""
        handler_called = []

        def handler(plan, task):
            handler_called.append(True)

        planner.on_event(PlanEvent.PLAN_CREATED, handler)
        planner.off_event(PlanEvent.PLAN_CREATED, handler)

        # Handler should not be called
        from src.domain.orchestration.planning.task_decomposer import DecompositionResult

        planner.decomposer.decompose = AsyncMock()
        mock_result = MagicMock(spec=DecompositionResult)
        mock_result.task_id = uuid4()
        mock_result.subtasks = []
        mock_result.execution_order = []
        planner.decomposer.decompose.return_value = mock_result

        await planner.create_plan(goal="Test")

        assert len(handler_called) == 0


# =============================================================================
# PlanStatus and PlanEvent Tests
# =============================================================================


class TestEnums:
    """Tests for enum classes."""

    def test_plan_status_values(self):
        """Test PlanStatus enum values."""
        assert PlanStatus.DRAFT.value == "draft"
        assert PlanStatus.APPROVED.value == "approved"
        assert PlanStatus.EXECUTING.value == "executing"
        assert PlanStatus.PAUSED.value == "paused"
        assert PlanStatus.COMPLETED.value == "completed"
        assert PlanStatus.FAILED.value == "failed"
        assert PlanStatus.REPLANNING.value == "replanning"

    def test_plan_event_values(self):
        """Test PlanEvent enum values."""
        assert PlanEvent.TASK_STARTED.value == "task_started"
        assert PlanEvent.TASK_COMPLETED.value == "task_completed"
        assert PlanEvent.TASK_FAILED.value == "task_failed"
        assert PlanEvent.DEADLINE_APPROACHING.value == "deadline_approaching"
        assert PlanEvent.PLAN_CREATED.value == "plan_created"
        assert PlanEvent.REPLANNING_STARTED.value == "replanning_started"

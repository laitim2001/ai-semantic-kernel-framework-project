# =============================================================================
# IPA Platform - AG-UI Generative UI Tests
# =============================================================================
# Sprint 59: AG-UI Basic Features
# S59-4: Agentic Generative UI (6 pts)
#
# Unit tests for GenerativeUIHandler.
# Tests workflow progress tracking and mode switch notifications.
#
# Test Coverage:
#   - ProgressStatus enum
#   - ModeSwitchReason enum
#   - WorkflowStep dataclass
#   - WorkflowProgress dataclass
#   - ModeSwitchInfo dataclass
#   - GenerativeUIHandler class
#   - Factory function
# =============================================================================

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.ag_ui.features.generative_ui import (
    EVENT_MODE_SWITCH,
    EVENT_WORKFLOW_PROGRESS,
    GenerativeUIHandler,
    ModeSwitchInfo,
    ModeSwitchReason,
    ProgressStatus,
    WorkflowProgress,
    WorkflowStep,
    create_generative_ui_handler,
)
from src.integrations.ag_ui.events import CustomEvent
from src.integrations.hybrid.switching.models import (
    SwitchResult,
    SwitchStatus,
    SwitchTrigger,
    SwitchTriggerType,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def handler() -> GenerativeUIHandler:
    """Create a GenerativeUIHandler instance."""
    return GenerativeUIHandler()


@pytest.fixture
def mock_mode_switcher():
    """Create a mock ModeSwitcher."""
    switcher = MagicMock()
    switcher.execute_switch = AsyncMock()
    return switcher


@pytest.fixture
def handler_with_switcher(mock_mode_switcher) -> GenerativeUIHandler:
    """Create handler with mock mode switcher."""
    return GenerativeUIHandler(mode_switcher=mock_mode_switcher)


@pytest.fixture
def sample_step() -> WorkflowStep:
    """Create a sample workflow step."""
    return WorkflowStep(
        step_id="step-001",
        name="Data Extraction",
        description="Extract data from source",
        order=1,
    )


@pytest.fixture
def sample_steps() -> list:
    """Create sample workflow steps."""
    return [
        WorkflowStep(
            step_id="step-001",
            name="Data Extraction",
            description="Extract data from source",
            order=1,
        ),
        WorkflowStep(
            step_id="step-002",
            name="Data Processing",
            description="Process extracted data",
            order=2,
        ),
        WorkflowStep(
            step_id="step-003",
            name="Data Storage",
            description="Store processed data",
            order=3,
        ),
    ]


@pytest.fixture
def sample_progress(sample_steps) -> WorkflowProgress:
    """Create sample workflow progress."""
    return WorkflowProgress(
        workflow_id="wf-001",
        workflow_name="Data Pipeline",
        total_steps=3,
        steps=sample_steps,
    )


@pytest.fixture
def sample_switch_info() -> ModeSwitchInfo:
    """Create sample mode switch info."""
    return ModeSwitchInfo(
        switch_id="sw-001",
        source_mode="chat",
        target_mode="workflow",
        reason="Multi-step task detected",
        trigger_type=SwitchTriggerType.COMPLEXITY.value,
        confidence=0.85,
        message="Switching to workflow mode for complex task",
    )


@pytest.fixture
def sample_trigger() -> SwitchTrigger:
    """Create sample switch trigger."""
    return SwitchTrigger(
        trigger_type=SwitchTriggerType.COMPLEXITY,
        source_mode="chat",
        target_mode="workflow",
        reason="Complex multi-step operation",
        confidence=0.9,
    )


@pytest.fixture
def sample_switch_result(sample_trigger) -> SwitchResult:
    """Create sample switch result."""
    result = SwitchResult(success=True, switch_id="sw-001")
    result.status = SwitchStatus.COMPLETED
    result.trigger = sample_trigger
    result.new_mode = "workflow"
    return result


# =============================================================================
# Test ProgressStatus Enum
# =============================================================================


class TestProgressStatus:
    """Tests for ProgressStatus enum."""

    def test_pending_value(self):
        """Test PENDING enum value."""
        assert ProgressStatus.PENDING.value == "pending"

    def test_in_progress_value(self):
        """Test IN_PROGRESS enum value."""
        assert ProgressStatus.IN_PROGRESS.value == "in_progress"

    def test_completed_value(self):
        """Test COMPLETED enum value."""
        assert ProgressStatus.COMPLETED.value == "completed"

    def test_failed_value(self):
        """Test FAILED enum value."""
        assert ProgressStatus.FAILED.value == "failed"

    def test_skipped_value(self):
        """Test SKIPPED enum value."""
        assert ProgressStatus.SKIPPED.value == "skipped"

    def test_all_statuses_count(self):
        """Test that all expected statuses exist."""
        assert len(ProgressStatus) == 5


# =============================================================================
# Test ModeSwitchReason Enum
# =============================================================================


class TestModeSwitchReason:
    """Tests for ModeSwitchReason enum."""

    def test_complexity_value(self):
        """Test COMPLEXITY enum value."""
        assert ModeSwitchReason.COMPLEXITY.value == "complexity"

    def test_user_request_value(self):
        """Test USER_REQUEST enum value."""
        assert ModeSwitchReason.USER_REQUEST.value == "user_request"

    def test_failure_recovery_value(self):
        """Test FAILURE_RECOVERY enum value."""
        assert ModeSwitchReason.FAILURE_RECOVERY.value == "failure_recovery"

    def test_resource_optimization_value(self):
        """Test RESOURCE_OPTIMIZATION enum value."""
        assert ModeSwitchReason.RESOURCE_OPTIMIZATION.value == "resource_optimization"

    def test_timeout_value(self):
        """Test TIMEOUT enum value."""
        assert ModeSwitchReason.TIMEOUT.value == "timeout"

    def test_automatic_value(self):
        """Test AUTOMATIC enum value."""
        assert ModeSwitchReason.AUTOMATIC.value == "automatic"

    def test_all_reasons_count(self):
        """Test that all expected reasons exist."""
        assert len(ModeSwitchReason) == 6


# =============================================================================
# Test WorkflowStep
# =============================================================================


class TestWorkflowStep:
    """Tests for WorkflowStep dataclass."""

    def test_create_minimal_step(self):
        """Test creating step with minimal fields."""
        step = WorkflowStep(step_id="step-001", name="Test Step")
        assert step.step_id == "step-001"
        assert step.name == "Test Step"
        assert step.description == ""
        assert step.status == ProgressStatus.PENDING
        assert step.order == 0

    def test_create_full_step(self, sample_step):
        """Test creating step with all fields."""
        assert sample_step.step_id == "step-001"
        assert sample_step.name == "Data Extraction"
        assert sample_step.description == "Extract data from source"
        assert sample_step.order == 1
        assert sample_step.status == ProgressStatus.PENDING

    def test_step_with_timestamps(self):
        """Test step with start and completion timestamps."""
        now = datetime.utcnow()
        step = WorkflowStep(
            step_id="step-001",
            name="Test",
            started_at=now,
            completed_at=now + timedelta(seconds=30),
        )
        assert step.started_at == now
        assert step.completed_at is not None

    def test_step_with_result(self):
        """Test step with result data."""
        step = WorkflowStep(
            step_id="step-001",
            name="Test",
            status=ProgressStatus.COMPLETED,
            result={"records": 100, "success": True},
        )
        assert step.result == {"records": 100, "success": True}

    def test_step_with_error(self):
        """Test step with error."""
        step = WorkflowStep(
            step_id="step-001",
            name="Test",
            status=ProgressStatus.FAILED,
            error="Connection timeout",
        )
        assert step.error == "Connection timeout"

    def test_step_to_dict(self, sample_step):
        """Test converting step to dictionary."""
        result = sample_step.to_dict()
        assert result["step_id"] == "step-001"
        assert result["name"] == "Data Extraction"
        assert result["status"] == "pending"
        assert result["order"] == 1
        assert result["started_at"] is None
        assert result["completed_at"] is None

    def test_step_to_dict_with_timestamps(self):
        """Test to_dict with timestamps."""
        now = datetime.utcnow()
        step = WorkflowStep(
            step_id="step-001",
            name="Test",
            started_at=now,
            completed_at=now,
        )
        result = step.to_dict()
        assert result["started_at"] == now.isoformat()
        assert result["completed_at"] == now.isoformat()

    def test_step_with_metadata(self):
        """Test step with metadata."""
        step = WorkflowStep(
            step_id="step-001",
            name="Test",
            metadata={"priority": "high", "retry_count": 0},
        )
        assert step.metadata["priority"] == "high"
        result = step.to_dict()
        assert result["metadata"]["priority"] == "high"


# =============================================================================
# Test WorkflowProgress
# =============================================================================


class TestWorkflowProgress:
    """Tests for WorkflowProgress dataclass."""

    def test_create_minimal_progress(self):
        """Test creating progress with minimal fields."""
        progress = WorkflowProgress(
            workflow_id="wf-001",
            workflow_name="Test Workflow",
            total_steps=3,
        )
        assert progress.workflow_id == "wf-001"
        assert progress.workflow_name == "Test Workflow"
        assert progress.total_steps == 3
        assert progress.completed_steps == 0
        assert progress.overall_progress == 0.0

    def test_create_full_progress(self, sample_progress):
        """Test creating progress with all fields."""
        assert sample_progress.workflow_id == "wf-001"
        assert sample_progress.workflow_name == "Data Pipeline"
        assert sample_progress.total_steps == 3
        assert len(sample_progress.steps) == 3

    def test_calculate_progress_zero(self, sample_progress):
        """Test calculate_progress with no completed steps."""
        result = sample_progress.calculate_progress()
        assert result == 0.0
        assert sample_progress.overall_progress == 0.0

    def test_calculate_progress_partial(self, sample_progress):
        """Test calculate_progress with some completed steps."""
        sample_progress.completed_steps = 1
        result = sample_progress.calculate_progress()
        assert result == pytest.approx(0.333, rel=0.01)

    def test_calculate_progress_half(self, sample_progress):
        """Test calculate_progress at 50%."""
        sample_progress.completed_steps = 1
        sample_progress.total_steps = 2
        result = sample_progress.calculate_progress()
        assert result == 0.5

    def test_calculate_progress_complete(self, sample_progress):
        """Test calculate_progress at 100%."""
        sample_progress.completed_steps = 3
        result = sample_progress.calculate_progress()
        assert result == 1.0

    def test_calculate_progress_zero_steps(self):
        """Test calculate_progress with zero total steps."""
        progress = WorkflowProgress(
            workflow_id="wf-001",
            workflow_name="Empty",
            total_steps=0,
        )
        result = progress.calculate_progress()
        assert result == 0.0

    def test_progress_to_dict(self, sample_progress):
        """Test converting progress to dictionary."""
        result = sample_progress.to_dict()
        assert result["workflow_id"] == "wf-001"
        assert result["workflow_name"] == "Data Pipeline"
        assert result["total_steps"] == 3
        assert result["completed_steps"] == 0
        assert result["overall_progress"] == 0.0
        assert len(result["steps"]) == 3

    def test_progress_to_dict_with_current_step(self, sample_progress, sample_step):
        """Test to_dict with current step."""
        sample_progress.current_step = sample_step
        result = sample_progress.to_dict()
        assert result["current_step"] is not None
        assert result["current_step"]["step_id"] == "step-001"

    def test_progress_to_dict_with_estimated_completion(self, sample_progress):
        """Test to_dict with estimated completion time."""
        future = datetime.utcnow() + timedelta(hours=1)
        sample_progress.estimated_completion = future
        result = sample_progress.to_dict()
        assert result["estimated_completion"] == future.isoformat()

    def test_progress_with_metadata(self, sample_progress):
        """Test progress with metadata."""
        sample_progress.metadata = {"agent_id": "agent-001"}
        result = sample_progress.to_dict()
        assert result["metadata"]["agent_id"] == "agent-001"


# =============================================================================
# Test ModeSwitchInfo
# =============================================================================


class TestModeSwitchInfo:
    """Tests for ModeSwitchInfo dataclass."""

    def test_create_minimal_switch_info(self):
        """Test creating switch info with minimal fields."""
        info = ModeSwitchInfo(
            switch_id="sw-001",
            source_mode="chat",
            target_mode="workflow",
            reason="User requested",
        )
        assert info.switch_id == "sw-001"
        assert info.source_mode == "chat"
        assert info.target_mode == "workflow"
        assert info.reason == "User requested"
        assert info.success is True

    def test_create_full_switch_info(self, sample_switch_info):
        """Test creating switch info with all fields."""
        assert sample_switch_info.switch_id == "sw-001"
        assert sample_switch_info.source_mode == "chat"
        assert sample_switch_info.target_mode == "workflow"
        assert sample_switch_info.confidence == 0.85
        assert sample_switch_info.success is True

    def test_switch_info_defaults(self):
        """Test default values."""
        info = ModeSwitchInfo(
            switch_id="sw-001",
            source_mode="chat",
            target_mode="workflow",
            reason="Test",
        )
        assert info.trigger_type == "manual"
        assert info.confidence == 1.0
        assert info.message == ""
        assert info.success is True
        assert info.rollback_available is False

    def test_switch_info_to_dict(self, sample_switch_info):
        """Test converting switch info to dictionary."""
        result = sample_switch_info.to_dict()
        assert result["switch_id"] == "sw-001"
        assert result["source_mode"] == "chat"
        assert result["target_mode"] == "workflow"
        assert result["confidence"] == 0.85
        assert result["success"] is True
        assert "timestamp" in result

    def test_switch_info_with_failure(self):
        """Test switch info for failed switch."""
        info = ModeSwitchInfo(
            switch_id="sw-001",
            source_mode="chat",
            target_mode="workflow",
            reason="Test",
            success=False,
            message="Switch failed: timeout",
        )
        result = info.to_dict()
        assert result["success"] is False
        assert "timeout" in result["message"]

    def test_switch_info_with_rollback(self):
        """Test switch info with rollback available."""
        info = ModeSwitchInfo(
            switch_id="sw-001",
            source_mode="workflow",
            target_mode="chat",
            reason="User request",
            rollback_available=True,
        )
        assert info.rollback_available is True
        result = info.to_dict()
        assert result["rollback_available"] is True


# =============================================================================
# Test GenerativeUIHandler Initialization
# =============================================================================


class TestGenerativeUIHandlerInit:
    """Tests for GenerativeUIHandler initialization."""

    def test_create_handler(self, handler):
        """Test creating handler with defaults."""
        assert handler.mode_switcher is None
        assert handler._active_workflows == {}
        assert handler._event_history == []
        assert handler._max_event_history == 100

    def test_create_handler_with_switcher(self, mock_mode_switcher):
        """Test creating handler with mode switcher."""
        handler = GenerativeUIHandler(mode_switcher=mock_mode_switcher)
        assert handler.mode_switcher is mock_mode_switcher

    def test_create_handler_custom_history_size(self):
        """Test creating handler with custom history size."""
        handler = GenerativeUIHandler(max_event_history=50)
        assert handler._max_event_history == 50


# =============================================================================
# Test Progress Event Methods
# =============================================================================


class TestProgressEvents:
    """Tests for progress event methods."""

    @pytest.mark.asyncio
    async def test_emit_progress_event(self, handler, sample_progress):
        """Test emitting workflow progress event."""
        event = await handler.emit_progress_event("run-001", sample_progress)

        assert isinstance(event, CustomEvent)
        assert event.event_name == EVENT_WORKFLOW_PROGRESS
        assert event.payload["run_id"] == "run-001"
        assert event.payload["workflow_id"] == "wf-001"
        assert event.payload["workflow_name"] == "Data Pipeline"
        assert event.payload["total_steps"] == 3
        assert event.payload["completed_steps"] == 0

    @pytest.mark.asyncio
    async def test_emit_progress_event_with_steps(self, handler, sample_progress):
        """Test emitting progress event includes steps by default."""
        event = await handler.emit_progress_event("run-001", sample_progress)

        assert "steps" in event.payload
        assert len(event.payload["steps"]) == 3

    @pytest.mark.asyncio
    async def test_emit_progress_event_without_steps(self, handler, sample_progress):
        """Test emitting progress event without steps."""
        event = await handler.emit_progress_event(
            "run-001", sample_progress, include_steps=False
        )

        assert "steps" not in event.payload

    @pytest.mark.asyncio
    async def test_emit_progress_event_with_current_step(
        self, handler, sample_progress, sample_step
    ):
        """Test emitting progress event with current step."""
        sample_progress.current_step = sample_step
        event = await handler.emit_progress_event("run-001", sample_progress)

        assert "current_step" in event.payload
        assert event.payload["current_step"]["step_id"] == "step-001"

    @pytest.mark.asyncio
    async def test_emit_progress_event_calculates_progress(self, handler, sample_progress):
        """Test that progress is calculated when emitting."""
        sample_progress.completed_steps = 1
        event = await handler.emit_progress_event("run-001", sample_progress)

        assert event.payload["overall_progress"] == pytest.approx(0.333, rel=0.01)

    @pytest.mark.asyncio
    async def test_emit_progress_event_tracks_workflow(self, handler, sample_progress):
        """Test that workflow is tracked after emission."""
        await handler.emit_progress_event("run-001", sample_progress)

        assert "wf-001" in handler._active_workflows
        assert handler._active_workflows["wf-001"] is sample_progress

    @pytest.mark.asyncio
    async def test_emit_progress_event_adds_to_history(self, handler, sample_progress):
        """Test that event is added to history."""
        await handler.emit_progress_event("run-001", sample_progress)

        assert len(handler._event_history) == 1
        assert handler._event_history[0].event_name == EVENT_WORKFLOW_PROGRESS


class TestStepEvents:
    """Tests for step-level events."""

    @pytest.mark.asyncio
    async def test_emit_step_started(self, handler, sample_step):
        """Test emitting step started event."""
        event = await handler.emit_step_started("run-001", "wf-001", sample_step)

        assert isinstance(event, CustomEvent)
        assert sample_step.status == ProgressStatus.IN_PROGRESS
        assert sample_step.started_at is not None

    @pytest.mark.asyncio
    async def test_emit_step_started_updates_active_workflow(
        self, handler, sample_progress, sample_step
    ):
        """Test step started updates active workflow."""
        handler._active_workflows["wf-001"] = sample_progress

        event = await handler.emit_step_started("run-001", "wf-001", sample_step)

        assert sample_progress.current_step is sample_step

    @pytest.mark.asyncio
    async def test_emit_step_completed(self, handler, sample_step):
        """Test emitting step completed event."""
        result_data = {"records": 100}
        event = await handler.emit_step_completed(
            "run-001", "wf-001", sample_step, result=result_data
        )

        assert isinstance(event, CustomEvent)
        assert sample_step.status == ProgressStatus.COMPLETED
        assert sample_step.completed_at is not None
        assert sample_step.result == result_data

    @pytest.mark.asyncio
    async def test_emit_step_completed_increments_count(self, handler, sample_progress, sample_step):
        """Test step completed increments completed count."""
        handler._active_workflows["wf-001"] = sample_progress
        initial_count = sample_progress.completed_steps

        await handler.emit_step_completed("run-001", "wf-001", sample_step)

        assert sample_progress.completed_steps == initial_count + 1

    @pytest.mark.asyncio
    async def test_emit_step_failed(self, handler, sample_step):
        """Test emitting step failed event."""
        error_msg = "Connection timeout"
        event = await handler.emit_step_failed(
            "run-001", "wf-001", sample_step, error=error_msg
        )

        assert isinstance(event, CustomEvent)
        assert sample_step.status == ProgressStatus.FAILED
        assert sample_step.error == error_msg
        assert sample_step.completed_at is not None


# =============================================================================
# Test Mode Switch Event Methods
# =============================================================================


class TestModeSwitchEvents:
    """Tests for mode switch event methods."""

    @pytest.mark.asyncio
    async def test_emit_mode_switch_event(self, handler, sample_switch_info):
        """Test emitting mode switch event."""
        event = await handler.emit_mode_switch_event("run-001", sample_switch_info)

        assert isinstance(event, CustomEvent)
        assert event.event_name == EVENT_MODE_SWITCH
        assert event.payload["run_id"] == "run-001"
        assert event.payload["switch_id"] == "sw-001"
        assert event.payload["source_mode"] == "chat"
        assert event.payload["target_mode"] == "workflow"

    @pytest.mark.asyncio
    async def test_emit_mode_switch_event_adds_to_history(self, handler, sample_switch_info):
        """Test mode switch event is added to history."""
        await handler.emit_mode_switch_event("run-001", sample_switch_info)

        assert len(handler._event_history) == 1
        assert handler._event_history[0].event_name == EVENT_MODE_SWITCH

    @pytest.mark.asyncio
    async def test_emit_mode_switch_from_result(self, handler, sample_switch_result):
        """Test emitting mode switch from SwitchResult."""
        event = await handler.emit_mode_switch_from_result(
            "run-001", sample_switch_result
        )

        assert isinstance(event, CustomEvent)
        assert event.event_name == EVENT_MODE_SWITCH
        assert event.payload["source_mode"] == "chat"
        assert event.payload["target_mode"] == "workflow"
        assert event.payload["success"] is True

    @pytest.mark.asyncio
    async def test_emit_mode_switch_from_result_with_custom_message(
        self, handler, sample_switch_result
    ):
        """Test mode switch from result with custom message."""
        event = await handler.emit_mode_switch_from_result(
            "run-001", sample_switch_result, message="Custom message"
        )

        assert event.payload["message"] == "Custom message"

    @pytest.mark.asyncio
    async def test_emit_mode_switch_started(self, handler, sample_trigger):
        """Test emitting mode switch started event."""
        event = await handler.emit_mode_switch_started("run-001", sample_trigger)

        assert isinstance(event, CustomEvent)
        assert event.payload["source_mode"] == "chat"
        assert event.payload["target_mode"] == "workflow"
        assert "Switching" in event.payload["message"]

    @pytest.mark.asyncio
    async def test_emit_mode_switch_completed(self, handler, sample_switch_result):
        """Test emitting mode switch completed event."""
        event = await handler.emit_mode_switch_completed("run-001", sample_switch_result)

        assert isinstance(event, CustomEvent)
        assert event.payload["success"] is True
        assert "Successfully" in event.payload["message"]


# =============================================================================
# Test ModeSwitcher Integration
# =============================================================================


class TestModeSwitcherIntegration:
    """Tests for ModeSwitcher integration."""

    @pytest.mark.asyncio
    async def test_handle_switch_trigger_no_switcher(self, handler, sample_trigger):
        """Test handle_switch_trigger raises when no switcher."""
        with pytest.raises(ValueError, match="ModeSwitcher not configured"):
            async for _ in handler.handle_switch_trigger(
                "run-001", sample_trigger, {}, "session-001"
            ):
                pass

    @pytest.mark.asyncio
    async def test_handle_switch_trigger_success(
        self, handler_with_switcher, sample_trigger, sample_switch_result
    ):
        """Test handle_switch_trigger success flow."""
        handler_with_switcher.mode_switcher.execute_switch.return_value = sample_switch_result

        events = []
        async for event in handler_with_switcher.handle_switch_trigger(
            "run-001", sample_trigger, {}, "session-001"
        ):
            events.append(event)

        assert len(events) == 2  # started + completed
        assert events[0].payload["source_mode"] == "chat"
        assert events[1].payload["success"] is True

    @pytest.mark.asyncio
    async def test_handle_switch_trigger_failure(
        self, handler_with_switcher, sample_trigger
    ):
        """Test handle_switch_trigger failure flow."""
        handler_with_switcher.mode_switcher.execute_switch.side_effect = Exception(
            "Switch failed"
        )

        events = []
        with pytest.raises(Exception, match="Switch failed"):
            async for event in handler_with_switcher.handle_switch_trigger(
                "run-001", sample_trigger, {}, "session-001"
            ):
                events.append(event)

        assert len(events) == 2  # started + error
        assert events[1].payload["success"] is False
        assert "failed" in events[1].payload["message"].lower()


# =============================================================================
# Test Workflow Management
# =============================================================================


class TestWorkflowManagement:
    """Tests for workflow management methods."""

    def test_start_workflow(self, handler, sample_steps):
        """Test starting a workflow."""
        progress = handler.start_workflow("wf-001", "Test Workflow", sample_steps)

        assert isinstance(progress, WorkflowProgress)
        assert progress.workflow_id == "wf-001"
        assert progress.workflow_name == "Test Workflow"
        assert progress.total_steps == 3
        assert "wf-001" in handler._active_workflows

    def test_get_workflow_progress_exists(self, handler, sample_steps):
        """Test getting existing workflow progress."""
        handler.start_workflow("wf-001", "Test", sample_steps)

        progress = handler.get_workflow_progress("wf-001")

        assert progress is not None
        assert progress.workflow_id == "wf-001"

    def test_get_workflow_progress_not_exists(self, handler):
        """Test getting non-existent workflow progress."""
        progress = handler.get_workflow_progress("wf-999")

        assert progress is None

    def test_complete_workflow(self, handler, sample_steps):
        """Test completing a workflow."""
        handler.start_workflow("wf-001", "Test", sample_steps)

        progress = handler.complete_workflow("wf-001")

        assert progress is not None
        assert progress.completed_steps == progress.total_steps
        assert progress.overall_progress == 1.0
        assert "wf-001" not in handler._active_workflows

    def test_complete_workflow_not_exists(self, handler):
        """Test completing non-existent workflow."""
        progress = handler.complete_workflow("wf-999")

        assert progress is None

    def test_cancel_workflow(self, handler, sample_steps):
        """Test cancelling a workflow."""
        handler.start_workflow("wf-001", "Test", sample_steps)

        result = handler.cancel_workflow("wf-001")

        assert result is True
        assert "wf-001" not in handler._active_workflows

    def test_cancel_workflow_not_exists(self, handler):
        """Test cancelling non-existent workflow."""
        result = handler.cancel_workflow("wf-999")

        assert result is False


# =============================================================================
# Test Utility Methods
# =============================================================================


class TestUtilityMethods:
    """Tests for utility methods."""

    def test_generate_switch_message_success(self, handler, sample_switch_result):
        """Test generating message for successful switch."""
        message = handler._generate_switch_message(sample_switch_result)

        assert "Successfully" in message
        assert "workflow" in message

    def test_generate_switch_message_failure(self, handler):
        """Test generating message for failed switch."""
        result = SwitchResult(success=False, switch_id="sw-001")
        result.error = "Timeout"

        message = handler._generate_switch_message(result)

        assert "failed" in message
        assert "Timeout" in message

    @pytest.mark.asyncio
    async def test_add_to_history_limits_size(self, handler, sample_progress):
        """Test that history is limited in size."""
        handler._max_event_history = 5

        for i in range(10):
            sample_progress.completed_steps = i
            await handler.emit_progress_event(f"run-{i}", sample_progress)

        assert len(handler._event_history) == 5

    def test_get_event_history(self, handler):
        """Test getting event history."""
        # Add some events manually
        event1 = CustomEvent(event_name=EVENT_WORKFLOW_PROGRESS, payload={})
        event2 = CustomEvent(event_name=EVENT_MODE_SWITCH, payload={})
        handler._event_history = [event1, event2]

        history = handler.get_event_history()

        assert len(history) == 2

    def test_get_event_history_with_limit(self, handler):
        """Test getting event history with limit."""
        events = [CustomEvent(event_name="test", payload={}) for _ in range(10)]
        handler._event_history = events

        history = handler.get_event_history(limit=3)

        assert len(history) == 3

    def test_get_event_history_filter_by_name(self, handler):
        """Test filtering event history by name."""
        event1 = CustomEvent(event_name=EVENT_WORKFLOW_PROGRESS, payload={})
        event2 = CustomEvent(event_name=EVENT_MODE_SWITCH, payload={})
        event3 = CustomEvent(event_name=EVENT_WORKFLOW_PROGRESS, payload={})
        handler._event_history = [event1, event2, event3]

        history = handler.get_event_history(event_name=EVENT_WORKFLOW_PROGRESS)

        assert len(history) == 2
        assert all(e.event_name == EVENT_WORKFLOW_PROGRESS for e in history)

    def test_get_active_workflow_count(self, handler, sample_steps):
        """Test getting active workflow count."""
        assert handler.get_active_workflow_count() == 0

        handler.start_workflow("wf-001", "Test1", sample_steps)
        assert handler.get_active_workflow_count() == 1

        handler.start_workflow("wf-002", "Test2", sample_steps)
        assert handler.get_active_workflow_count() == 2

    def test_get_active_workflow_ids(self, handler, sample_steps):
        """Test getting active workflow IDs."""
        handler.start_workflow("wf-001", "Test1", sample_steps)
        handler.start_workflow("wf-002", "Test2", sample_steps)

        ids = handler.get_active_workflow_ids()

        assert "wf-001" in ids
        assert "wf-002" in ids

    def test_clear_event_history(self, handler):
        """Test clearing event history."""
        event = CustomEvent(event_name="test", payload={})
        handler._event_history = [event]

        handler.clear_event_history()

        assert len(handler._event_history) == 0


# =============================================================================
# Test Factory Function
# =============================================================================


class TestFactoryFunction:
    """Tests for create_generative_ui_handler factory."""

    def test_create_handler_defaults(self):
        """Test factory with default parameters."""
        handler = create_generative_ui_handler()

        assert isinstance(handler, GenerativeUIHandler)
        assert handler.mode_switcher is None
        assert handler._max_event_history == 100

    def test_create_handler_with_switcher(self, mock_mode_switcher):
        """Test factory with mode switcher."""
        handler = create_generative_ui_handler(mode_switcher=mock_mode_switcher)

        assert handler.mode_switcher is mock_mode_switcher

    def test_create_handler_with_custom_history(self):
        """Test factory with custom history size."""
        handler = create_generative_ui_handler(max_event_history=50)

        assert handler._max_event_history == 50


# =============================================================================
# Test Event Constants
# =============================================================================


class TestEventConstants:
    """Tests for event name constants."""

    def test_workflow_progress_event_name(self):
        """Test workflow progress event name."""
        assert EVENT_WORKFLOW_PROGRESS == "workflow_progress"

    def test_mode_switch_event_name(self):
        """Test mode switch event name."""
        assert EVENT_MODE_SWITCH == "mode_switch"


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for GenerativeUIHandler."""

    @pytest.mark.asyncio
    async def test_full_workflow_lifecycle(self, handler, sample_steps):
        """Test complete workflow lifecycle."""
        # Start workflow
        progress = handler.start_workflow("wf-001", "Integration Test", sample_steps)
        event1 = await handler.emit_progress_event("run-001", progress)

        assert event1.payload["overall_progress"] == 0.0

        # Complete steps
        for i, step in enumerate(sample_steps):
            await handler.emit_step_started("run-001", "wf-001", step)
            await handler.emit_step_completed("run-001", "wf-001", step)

        # Complete workflow
        final_progress = handler.complete_workflow("wf-001")

        assert final_progress.overall_progress == 1.0
        assert final_progress.completed_steps == 3

    @pytest.mark.asyncio
    async def test_multiple_concurrent_workflows(self, handler, sample_steps):
        """Test handling multiple concurrent workflows."""
        # Start multiple workflows
        progress1 = handler.start_workflow("wf-001", "Workflow 1", sample_steps[:2])
        progress2 = handler.start_workflow("wf-002", "Workflow 2", sample_steps[:1])

        await handler.emit_progress_event("run-001", progress1)
        await handler.emit_progress_event("run-002", progress2)

        assert handler.get_active_workflow_count() == 2

        # Complete one workflow
        handler.complete_workflow("wf-001")

        assert handler.get_active_workflow_count() == 1
        assert "wf-002" in handler.get_active_workflow_ids()

    @pytest.mark.asyncio
    async def test_event_history_filtering(self, handler, sample_progress, sample_switch_info):
        """Test event history filtering capabilities."""
        # Emit various events
        await handler.emit_progress_event("run-001", sample_progress)
        await handler.emit_mode_switch_event("run-001", sample_switch_info)
        await handler.emit_progress_event("run-001", sample_progress)

        # Filter by type
        progress_events = handler.get_event_history(
            event_name=EVENT_WORKFLOW_PROGRESS
        )
        switch_events = handler.get_event_history(event_name=EVENT_MODE_SWITCH)

        assert len(progress_events) == 2
        assert len(switch_events) == 1

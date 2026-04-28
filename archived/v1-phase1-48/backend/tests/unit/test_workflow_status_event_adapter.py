# =============================================================================
# IPA Platform - WorkflowStatusEventAdapter Unit Tests
# =============================================================================
# Phase 5: MVP Core Official API Migration
# Sprint 27, Story S27-2: WorkflowStatusEventAdapter Tests
#
# Comprehensive tests for the WorkflowStatusEventAdapter including:
#   - Event creation and conversion
#   - Handler registration and dispatch
#   - Event history tracking
#   - Filter functionality
# =============================================================================

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from src.integrations.agent_framework.core.events import (
    WorkflowStatusEventAdapter,
    ExecutionStatus,
    EventType,
    InternalExecutionEvent,
    EventFilter,
    create_event_adapter,
    create_event,
    create_event_filter,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def execution_id():
    """Create a test execution ID."""
    return uuid4()


@pytest.fixture
def event_adapter():
    """Create a WorkflowStatusEventAdapter."""
    return WorkflowStatusEventAdapter()


@pytest.fixture
def sample_event(execution_id):
    """Create a sample internal event."""
    return InternalExecutionEvent(
        execution_id=execution_id,
        event_type="executor_completed",
        status=ExecutionStatus.RUNNING,
        node_id="node-1",
        node_name="Test Node",
        data={"result": "success"},
    )


@pytest.fixture
def mock_official_event():
    """Create a mock official WorkflowStatusEvent."""
    event = MagicMock()
    event.event_type = "executor_started"
    event.executor_id = "executor-1"
    event.executor_name = "Test Executor"
    event.data = {"input": "test"}
    event.error = None
    event.workflow_id = str(uuid4())
    return event


# =============================================================================
# Test: ExecutionStatus
# =============================================================================

class TestExecutionStatus:
    """Tests for ExecutionStatus enum."""

    def test_status_values(self):
        """Test all status values exist."""
        assert ExecutionStatus.PENDING.value == "pending"
        assert ExecutionStatus.RUNNING.value == "running"
        assert ExecutionStatus.WAITING_APPROVAL.value == "waiting_approval"
        assert ExecutionStatus.COMPLETED.value == "completed"
        assert ExecutionStatus.FAILED.value == "failed"
        assert ExecutionStatus.CANCELLED.value == "cancelled"
        assert ExecutionStatus.PAUSED.value == "paused"
        assert ExecutionStatus.TIMEOUT.value == "timeout"

    def test_from_string(self):
        """Test creating status from string."""
        assert ExecutionStatus.from_string("running") == ExecutionStatus.RUNNING
        assert ExecutionStatus.from_string("COMPLETED") == ExecutionStatus.COMPLETED
        assert ExecutionStatus.from_string("unknown") == ExecutionStatus.RUNNING  # default

    def test_is_terminal(self):
        """Test terminal status detection."""
        assert ExecutionStatus.COMPLETED.is_terminal is True
        assert ExecutionStatus.FAILED.is_terminal is True
        assert ExecutionStatus.CANCELLED.is_terminal is True
        assert ExecutionStatus.TIMEOUT.is_terminal is True
        assert ExecutionStatus.RUNNING.is_terminal is False
        assert ExecutionStatus.PENDING.is_terminal is False

    def test_is_active(self):
        """Test active status detection."""
        assert ExecutionStatus.RUNNING.is_active is True
        assert ExecutionStatus.WAITING_APPROVAL.is_active is True
        assert ExecutionStatus.PAUSED.is_active is True
        assert ExecutionStatus.COMPLETED.is_active is False
        assert ExecutionStatus.PENDING.is_active is False


# =============================================================================
# Test: EventType
# =============================================================================

class TestEventType:
    """Tests for EventType enum."""

    def test_event_type_values(self):
        """Test all event type values exist."""
        assert EventType.STARTED.value == "started"
        assert EventType.COMPLETED.value == "completed"
        assert EventType.EXECUTOR_STARTED.value == "executor_started"
        assert EventType.WAITING_INPUT.value == "waiting_input"

    def test_from_string(self):
        """Test creating event type from string."""
        assert EventType.from_string("completed") == EventType.COMPLETED
        assert EventType.from_string("STARTED") == EventType.STARTED
        assert EventType.from_string("unknown") == EventType.PROGRESS  # default


# =============================================================================
# Test: InternalExecutionEvent
# =============================================================================

class TestInternalExecutionEvent:
    """Tests for InternalExecutionEvent."""

    def test_create_event(self, execution_id):
        """Test creating an event."""
        event = InternalExecutionEvent(
            execution_id=execution_id,
            event_type="completed",
            status=ExecutionStatus.COMPLETED,
        )

        assert event.execution_id == execution_id
        assert event.event_type == "completed"
        assert event.status == ExecutionStatus.COMPLETED

    def test_default_values(self, execution_id):
        """Test default values."""
        event = InternalExecutionEvent(
            execution_id=execution_id,
            event_type="progress",
            status=ExecutionStatus.RUNNING,
        )

        assert event.node_id is None
        assert event.data == {}
        assert event.error is None
        assert event.is_final is False

    def test_to_dict(self, sample_event):
        """Test converting event to dict."""
        data = sample_event.to_dict()

        assert "execution_id" in data
        assert data["event_type"] == "executor_completed"
        assert data["status"] == "running"
        assert data["node_id"] == "node-1"

    def test_from_dict(self, sample_event):
        """Test creating event from dict."""
        data = sample_event.to_dict()
        restored = InternalExecutionEvent.from_dict(data)

        assert restored.execution_id == sample_event.execution_id
        assert restored.event_type == sample_event.event_type
        assert restored.status == sample_event.status

    def test_repr(self, sample_event):
        """Test string representation."""
        repr_str = repr(sample_event)

        assert "InternalExecutionEvent" in repr_str
        assert "executor_completed" in repr_str


# =============================================================================
# Test: WorkflowStatusEventAdapter - Creation
# =============================================================================

class TestWorkflowStatusEventAdapterCreation:
    """Tests for WorkflowStatusEventAdapter creation."""

    def test_create_adapter(self):
        """Test creating an adapter."""
        adapter = WorkflowStatusEventAdapter()

        assert adapter.handler_count == 0
        assert adapter.event_count == 0

    def test_repr(self):
        """Test string representation."""
        adapter = WorkflowStatusEventAdapter()
        repr_str = repr(adapter)

        assert "WorkflowStatusEventAdapter" in repr_str


# =============================================================================
# Test: WorkflowStatusEventAdapter - Handlers
# =============================================================================

class TestWorkflowStatusEventAdapterHandlers:
    """Tests for handler management."""

    def test_add_handler(self, event_adapter):
        """Test adding a handler."""
        handler = AsyncMock()
        event_adapter.add_handler(handler)

        assert event_adapter.handler_count == 1

    def test_add_multiple_handlers(self, event_adapter):
        """Test adding multiple handlers."""
        handler1 = AsyncMock()
        handler2 = AsyncMock()

        event_adapter.add_handler(handler1)
        event_adapter.add_handler(handler2)

        assert event_adapter.handler_count == 2

    def test_remove_handler(self, event_adapter):
        """Test removing a handler."""
        handler = AsyncMock()
        event_adapter.add_handler(handler)
        event_adapter.remove_handler(handler)

        assert event_adapter.handler_count == 0

    def test_remove_nonexistent_handler(self, event_adapter):
        """Test removing nonexistent handler doesn't error."""
        handler = AsyncMock()
        # Should not raise
        event_adapter.remove_handler(handler)

    def test_clear_handlers(self, event_adapter):
        """Test clearing all handlers."""
        event_adapter.add_handler(AsyncMock())
        event_adapter.add_handler(AsyncMock())
        event_adapter.clear_handlers()

        assert event_adapter.handler_count == 0


# =============================================================================
# Test: WorkflowStatusEventAdapter - Event Handling
# =============================================================================

class TestWorkflowStatusEventAdapterHandling:
    """Tests for event handling."""

    @pytest.mark.asyncio
    async def test_handle_dict_event(self, event_adapter, execution_id):
        """Test handling a dict event."""
        event = {
            "event_type": "executor_completed",
            "executor_id": "node-1",
            "data": {"result": "ok"},
        }

        result = await event_adapter.handle(execution_id, event)

        assert isinstance(result, InternalExecutionEvent)
        assert result.event_type == "executor_completed"
        assert result.node_id == "node-1"

    @pytest.mark.asyncio
    async def test_handle_official_event(self, event_adapter, execution_id, mock_official_event):
        """Test handling an official event."""
        result = await event_adapter.handle(execution_id, mock_official_event)

        assert isinstance(result, InternalExecutionEvent)
        assert result.event_type == "executor_started"
        assert result.node_id == "executor-1"

    @pytest.mark.asyncio
    async def test_handler_called(self, event_adapter, execution_id):
        """Test that handlers are called."""
        handler = AsyncMock()
        event_adapter.add_handler(handler)

        await event_adapter.handle(execution_id, {"event_type": "started"})

        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_handler_called(self, event_adapter, execution_id):
        """Test that sync handlers are called."""
        received_events = []

        def sync_handler(event):
            received_events.append(event)

        event_adapter.add_handler(sync_handler)
        await event_adapter.handle(execution_id, {"event_type": "started"})

        assert len(received_events) == 1

    @pytest.mark.asyncio
    async def test_handler_error_doesnt_stop_others(self, event_adapter, execution_id):
        """Test that handler errors don't stop other handlers."""
        bad_handler = AsyncMock(side_effect=Exception("Handler error"))
        good_handler = AsyncMock()

        event_adapter.add_handler(bad_handler)
        event_adapter.add_handler(good_handler)

        await event_adapter.handle(execution_id, {"event_type": "started"})

        good_handler.assert_called_once()


# =============================================================================
# Test: WorkflowStatusEventAdapter - Status Mapping
# =============================================================================

class TestWorkflowStatusEventAdapterStatusMapping:
    """Tests for status mapping."""

    @pytest.mark.asyncio
    async def test_map_started(self, event_adapter, execution_id):
        """Test mapping started event."""
        result = await event_adapter.handle(execution_id, {"event_type": "started"})
        assert result.status == ExecutionStatus.RUNNING

    @pytest.mark.asyncio
    async def test_map_completed(self, event_adapter, execution_id):
        """Test mapping completed event."""
        result = await event_adapter.handle(execution_id, {"event_type": "completed"})
        assert result.status == ExecutionStatus.COMPLETED
        assert result.is_final is True

    @pytest.mark.asyncio
    async def test_map_failed(self, event_adapter, execution_id):
        """Test mapping failed event."""
        result = await event_adapter.handle(execution_id, {"event_type": "failed"})
        assert result.status == ExecutionStatus.FAILED
        assert result.is_final is True

    @pytest.mark.asyncio
    async def test_map_waiting_input(self, event_adapter, execution_id):
        """Test mapping waiting_input event."""
        result = await event_adapter.handle(execution_id, {"event_type": "waiting_input"})
        assert result.status == ExecutionStatus.WAITING_APPROVAL


# =============================================================================
# Test: WorkflowStatusEventAdapter - History
# =============================================================================

class TestWorkflowStatusEventAdapterHistory:
    """Tests for event history."""

    @pytest.mark.asyncio
    async def test_track_history(self, event_adapter, execution_id):
        """Test event history tracking."""
        await event_adapter.handle(execution_id, {"event_type": "started"})
        await event_adapter.handle(execution_id, {"event_type": "completed"})

        history = event_adapter.get_history(execution_id)
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_get_latest_status(self, event_adapter, execution_id):
        """Test getting latest status."""
        await event_adapter.handle(execution_id, {"event_type": "started"})
        await event_adapter.handle(execution_id, {"event_type": "completed"})

        status = event_adapter.get_latest_status(execution_id)
        assert status == ExecutionStatus.COMPLETED

    def test_get_latest_status_no_history(self, event_adapter, execution_id):
        """Test getting latest status with no history."""
        status = event_adapter.get_latest_status(execution_id)
        assert status is None

    @pytest.mark.asyncio
    async def test_clear_history(self, event_adapter, execution_id):
        """Test clearing history."""
        await event_adapter.handle(execution_id, {"event_type": "started"})
        event_adapter.clear_history(execution_id)

        history = event_adapter.get_history(execution_id)
        assert len(history) == 0

    @pytest.mark.asyncio
    async def test_clear_all_history(self, event_adapter):
        """Test clearing all history."""
        exec_id_1 = uuid4()
        exec_id_2 = uuid4()

        await event_adapter.handle(exec_id_1, {"event_type": "started"})
        await event_adapter.handle(exec_id_2, {"event_type": "started"})

        event_adapter.clear_history()

        assert len(event_adapter.get_history(exec_id_1)) == 0
        assert len(event_adapter.get_history(exec_id_2)) == 0

    @pytest.mark.asyncio
    async def test_event_count(self, event_adapter, execution_id):
        """Test event count tracking."""
        assert event_adapter.event_count == 0

        await event_adapter.handle(execution_id, {"event_type": "started"})
        assert event_adapter.event_count == 1

        await event_adapter.handle(execution_id, {"event_type": "completed"})
        assert event_adapter.event_count == 2


# =============================================================================
# Test: EventFilter
# =============================================================================

class TestEventFilter:
    """Tests for EventFilter."""

    def test_filter_by_event_type(self, sample_event):
        """Test filtering by event type."""
        filter = EventFilter(event_types=["executor_completed"])
        assert filter.matches(sample_event) is True

        filter = EventFilter(event_types=["started"])
        assert filter.matches(sample_event) is False

    def test_filter_by_status(self, sample_event):
        """Test filtering by status."""
        filter = EventFilter(statuses=[ExecutionStatus.RUNNING])
        assert filter.matches(sample_event) is True

        filter = EventFilter(statuses=[ExecutionStatus.COMPLETED])
        assert filter.matches(sample_event) is False

    def test_filter_by_node_id(self, sample_event):
        """Test filtering by node ID."""
        filter = EventFilter(node_ids=["node-1"])
        assert filter.matches(sample_event) is True

        filter = EventFilter(node_ids=["node-2"])
        assert filter.matches(sample_event) is False

    def test_filter_terminal_only(self, execution_id):
        """Test terminal only filter."""
        terminal_event = InternalExecutionEvent(
            execution_id=execution_id,
            event_type="completed",
            status=ExecutionStatus.COMPLETED,
            is_final=True,
        )
        non_terminal_event = InternalExecutionEvent(
            execution_id=execution_id,
            event_type="progress",
            status=ExecutionStatus.RUNNING,
            is_final=False,
        )

        filter = EventFilter(include_terminal_only=True)
        assert filter.matches(terminal_event) is True
        assert filter.matches(non_terminal_event) is False

    def test_filter_exclude_progress(self, execution_id):
        """Test exclude progress filter."""
        progress_event = InternalExecutionEvent(
            execution_id=execution_id,
            event_type="progress",
            status=ExecutionStatus.RUNNING,
        )
        completed_event = InternalExecutionEvent(
            execution_id=execution_id,
            event_type="completed",
            status=ExecutionStatus.COMPLETED,
        )

        filter = EventFilter(exclude_progress=True)
        assert filter.matches(progress_event) is False
        assert filter.matches(completed_event) is True

    def test_filter_no_criteria(self, sample_event):
        """Test filter with no criteria matches all."""
        filter = EventFilter()
        assert filter.matches(sample_event) is True


# =============================================================================
# Test: Factory Functions
# =============================================================================

class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_event_adapter(self):
        """Test create_event_adapter factory."""
        adapter = create_event_adapter()
        assert isinstance(adapter, WorkflowStatusEventAdapter)

    def test_create_event(self, execution_id):
        """Test create_event factory."""
        event = create_event(
            execution_id=execution_id,
            event_type="completed",
            node_id="node-1",
        )

        assert isinstance(event, InternalExecutionEvent)
        assert event.execution_id == execution_id
        assert event.event_type == "completed"
        assert event.is_final is True

    def test_create_event_auto_status(self, execution_id):
        """Test create_event auto-maps status."""
        event = create_event(
            execution_id=execution_id,
            event_type="failed",
        )

        assert event.status == ExecutionStatus.FAILED

    def test_create_event_filter(self):
        """Test create_event_filter factory."""
        filter = create_event_filter(
            event_types=["completed", "failed"],
            terminal_only=True,
        )

        assert isinstance(filter, EventFilter)
        assert filter.event_types == {"completed", "failed"}
        assert filter.include_terminal_only is True

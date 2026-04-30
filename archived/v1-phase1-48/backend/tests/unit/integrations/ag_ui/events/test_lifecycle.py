# =============================================================================
# IPA Platform - AG-UI Lifecycle Events Unit Tests
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-4: AG-UI Event Types
#
# Unit tests for AG-UI lifecycle events (RunStarted, RunFinished).
# =============================================================================

import json

import pytest

from src.integrations.ag_ui.events.base import AGUIEventType, RunFinishReason
from src.integrations.ag_ui.events.lifecycle import (
    RunFinishedEvent,
    RunStartedEvent,
)


class TestRunStartedEvent:
    """Tests for RunStartedEvent class."""

    def test_create_run_started_event(self):
        """Test creating a run started event."""
        event = RunStartedEvent(
            thread_id="thread-123",
            run_id="run-456"
        )
        assert event.type == AGUIEventType.RUN_STARTED
        assert event.thread_id == "thread-123"
        assert event.run_id == "run-456"

    def test_type_is_fixed(self):
        """Test type cannot be overridden."""
        event = RunStartedEvent(
            thread_id="thread-123",
            run_id="run-456"
        )
        # Type should always be RUN_STARTED
        assert event.type == AGUIEventType.RUN_STARTED

    def test_json_serialization(self):
        """Test JSON serialization includes all fields."""
        event = RunStartedEvent(
            thread_id="thread-123",
            run_id="run-456"
        )
        json_str = event.model_dump_json()
        data = json.loads(json_str)

        assert data["type"] == "RUN_STARTED"
        assert data["thread_id"] == "thread-123"
        assert data["run_id"] == "run-456"
        assert "timestamp" in data

    def test_sse_output(self):
        """Test SSE format output."""
        event = RunStartedEvent(
            thread_id="thread-123",
            run_id="run-456"
        )
        sse = event.to_sse()
        assert "RUN_STARTED" in sse
        assert "thread-123" in sse
        assert "run-456" in sse

    def test_required_fields(self):
        """Test required fields raise error if missing."""
        with pytest.raises(ValueError):
            RunStartedEvent(thread_id="thread-123")  # Missing run_id

        with pytest.raises(ValueError):
            RunStartedEvent(run_id="run-456")  # Missing thread_id


class TestRunFinishedEvent:
    """Tests for RunFinishedEvent class."""

    def test_create_run_finished_event_success(self):
        """Test creating a successful run finished event."""
        event = RunFinishedEvent(
            thread_id="thread-123",
            run_id="run-456",
            finish_reason=RunFinishReason.COMPLETE
        )
        assert event.type == AGUIEventType.RUN_FINISHED
        assert event.thread_id == "thread-123"
        assert event.run_id == "run-456"
        assert event.finish_reason == RunFinishReason.COMPLETE
        assert event.error is None

    def test_create_run_finished_event_error(self):
        """Test creating an error run finished event."""
        event = RunFinishedEvent(
            thread_id="thread-123",
            run_id="run-456",
            finish_reason=RunFinishReason.ERROR,
            error="Connection timeout"
        )
        assert event.finish_reason == RunFinishReason.ERROR
        assert event.error == "Connection timeout"

    def test_create_run_finished_event_cancelled(self):
        """Test creating a cancelled run finished event."""
        event = RunFinishedEvent(
            thread_id="thread-123",
            run_id="run-456",
            finish_reason=RunFinishReason.CANCELLED
        )
        assert event.finish_reason == RunFinishReason.CANCELLED

    def test_create_run_finished_event_timeout(self):
        """Test creating a timeout run finished event."""
        event = RunFinishedEvent(
            thread_id="thread-123",
            run_id="run-456",
            finish_reason=RunFinishReason.TIMEOUT,
            error="Execution exceeded 30s limit"
        )
        assert event.finish_reason == RunFinishReason.TIMEOUT

    def test_with_usage_stats(self):
        """Test including usage statistics."""
        event = RunFinishedEvent(
            thread_id="thread-123",
            run_id="run-456",
            finish_reason=RunFinishReason.COMPLETE,
            usage={
                "input_tokens": 150,
                "output_tokens": 200,
                "duration_ms": 1500
            }
        )
        assert event.usage is not None
        assert event.usage["input_tokens"] == 150
        assert event.usage["output_tokens"] == 200
        assert event.usage["duration_ms"] == 1500

    def test_default_finish_reason(self):
        """Test default finish reason is COMPLETE."""
        event = RunFinishedEvent(
            thread_id="thread-123",
            run_id="run-456"
        )
        assert event.finish_reason == RunFinishReason.COMPLETE

    def test_json_serialization(self):
        """Test JSON serialization includes all fields."""
        event = RunFinishedEvent(
            thread_id="thread-123",
            run_id="run-456",
            finish_reason=RunFinishReason.COMPLETE,
            usage={"tokens": 350}
        )
        json_str = event.model_dump_json()
        data = json.loads(json_str)

        assert data["type"] == "RUN_FINISHED"
        assert data["thread_id"] == "thread-123"
        assert data["run_id"] == "run-456"
        assert data["finish_reason"] == "complete"
        assert data["usage"]["tokens"] == 350

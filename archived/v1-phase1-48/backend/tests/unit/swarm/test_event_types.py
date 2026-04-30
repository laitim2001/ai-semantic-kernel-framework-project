"""
Unit tests for Swarm event types.

Tests payload serialization and event name constants.
Sprint 101: Swarm Event System + SSE Integration
"""

import pytest
from datetime import datetime

from src.integrations.swarm.events import (
    # Payloads
    SwarmCreatedPayload,
    SwarmStatusUpdatePayload,
    SwarmCompletedPayload,
    WorkerStartedPayload,
    WorkerProgressPayload,
    WorkerThinkingPayload,
    WorkerToolCallPayload,
    WorkerMessagePayload,
    WorkerCompletedPayload,
    # Event names
    SwarmEventNames,
)


class TestSwarmEventNames:
    """Test SwarmEventNames constants."""

    def test_swarm_event_values(self):
        """Test swarm-level event name values."""
        assert SwarmEventNames.SWARM_CREATED == "swarm_created"
        assert SwarmEventNames.SWARM_STATUS_UPDATE == "swarm_status_update"
        assert SwarmEventNames.SWARM_COMPLETED == "swarm_completed"

    def test_worker_event_values(self):
        """Test worker-level event name values."""
        assert SwarmEventNames.WORKER_STARTED == "worker_started"
        assert SwarmEventNames.WORKER_PROGRESS == "worker_progress"
        assert SwarmEventNames.WORKER_THINKING == "worker_thinking"
        assert SwarmEventNames.WORKER_TOOL_CALL == "worker_tool_call"
        assert SwarmEventNames.WORKER_MESSAGE == "worker_message"
        assert SwarmEventNames.WORKER_COMPLETED == "worker_completed"

    def test_all_events(self):
        """Test all_events() returns all event names."""
        all_events = SwarmEventNames.all_events()
        assert len(all_events) == 9
        assert SwarmEventNames.SWARM_CREATED in all_events
        assert SwarmEventNames.WORKER_COMPLETED in all_events

    def test_swarm_events(self):
        """Test swarm_events() returns only swarm-level events."""
        swarm_events = SwarmEventNames.swarm_events()
        assert len(swarm_events) == 3
        assert SwarmEventNames.SWARM_CREATED in swarm_events
        assert SwarmEventNames.WORKER_STARTED not in swarm_events

    def test_worker_events(self):
        """Test worker_events() returns only worker-level events."""
        worker_events = SwarmEventNames.worker_events()
        assert len(worker_events) == 6
        assert SwarmEventNames.WORKER_STARTED in worker_events
        assert SwarmEventNames.SWARM_CREATED not in worker_events

    def test_priority_events(self):
        """Test priority_events() returns high-priority events."""
        priority = SwarmEventNames.priority_events()
        assert SwarmEventNames.SWARM_CREATED in priority
        assert SwarmEventNames.SWARM_COMPLETED in priority
        assert SwarmEventNames.WORKER_TOOL_CALL in priority
        # These should be throttled, not priority
        assert SwarmEventNames.WORKER_PROGRESS not in priority

    def test_throttled_events(self):
        """Test throttled_events() returns events that can be throttled."""
        throttled = SwarmEventNames.throttled_events()
        assert SwarmEventNames.WORKER_PROGRESS in throttled
        assert SwarmEventNames.WORKER_THINKING in throttled
        assert SwarmEventNames.SWARM_STATUS_UPDATE in throttled
        # Priority events should not be throttled
        assert SwarmEventNames.SWARM_CREATED not in throttled


class TestSwarmCreatedPayload:
    """Test SwarmCreatedPayload."""

    def test_create_payload(self):
        """Test creating a SwarmCreatedPayload."""
        payload = SwarmCreatedPayload(
            swarm_id="swarm-123",
            session_id="session-456",
            mode="parallel",
            workers=[
                {"worker_id": "w1", "worker_name": "Agent 1", "worker_type": "research", "role": "R1"}
            ],
            created_at="2026-01-29T12:00:00Z",
        )

        assert payload.swarm_id == "swarm-123"
        assert payload.session_id == "session-456"
        assert payload.mode == "parallel"
        assert len(payload.workers) == 1
        assert payload.workers[0]["worker_id"] == "w1"

    def test_to_dict(self):
        """Test serialization to dictionary."""
        payload = SwarmCreatedPayload(
            swarm_id="swarm-123",
            session_id="session-456",
            mode="sequential",
            workers=[],
            created_at="2026-01-29T12:00:00Z",
        )

        data = payload.to_dict()
        assert data["swarm_id"] == "swarm-123"
        assert data["mode"] == "sequential"
        assert data["workers"] == []


class TestSwarmStatusUpdatePayload:
    """Test SwarmStatusUpdatePayload."""

    def test_create_payload(self):
        """Test creating a SwarmStatusUpdatePayload."""
        payload = SwarmStatusUpdatePayload(
            swarm_id="swarm-123",
            session_id="session-456",
            mode="parallel",
            status="running",
            total_workers=3,
            overall_progress=65,
            workers=[],
            metadata={"custom": "data"},
        )

        assert payload.swarm_id == "swarm-123"
        assert payload.status == "running"
        assert payload.overall_progress == 65
        assert payload.metadata == {"custom": "data"}

    def test_to_dict(self):
        """Test serialization to dictionary."""
        payload = SwarmStatusUpdatePayload(
            swarm_id="swarm-123",
            session_id="",
            mode="hierarchical",
            status="completed",
            total_workers=2,
            overall_progress=100,
            workers=[{"worker_id": "w1"}],
            metadata={},
        )

        data = payload.to_dict()
        assert data["mode"] == "hierarchical"
        assert data["status"] == "completed"
        assert data["overall_progress"] == 100


class TestSwarmCompletedPayload:
    """Test SwarmCompletedPayload."""

    def test_create_payload(self):
        """Test creating a SwarmCompletedPayload."""
        payload = SwarmCompletedPayload(
            swarm_id="swarm-123",
            status="completed",
            total_duration_ms=5000,
            completed_at="2026-01-29T12:05:00Z",
            summary="Task completed successfully",
        )

        assert payload.swarm_id == "swarm-123"
        assert payload.status == "completed"
        assert payload.total_duration_ms == 5000
        assert payload.summary == "Task completed successfully"

    def test_to_dict_with_none_summary(self):
        """Test serialization with None summary."""
        payload = SwarmCompletedPayload(
            swarm_id="swarm-123",
            status="failed",
            total_duration_ms=1000,
            completed_at="2026-01-29T12:01:00Z",
            summary=None,
        )

        data = payload.to_dict()
        assert data["status"] == "failed"
        assert data["summary"] is None


class TestWorkerStartedPayload:
    """Test WorkerStartedPayload."""

    def test_create_payload(self):
        """Test creating a WorkerStartedPayload."""
        payload = WorkerStartedPayload(
            swarm_id="swarm-123",
            worker_id="worker-1",
            worker_name="Research Agent",
            worker_type="research",
            role="Data Gatherer",
            task_description="Searching for information",
            started_at="2026-01-29T12:00:00Z",
        )

        assert payload.worker_id == "worker-1"
        assert payload.worker_name == "Research Agent"
        assert payload.worker_type == "research"
        assert payload.task_description == "Searching for information"

    def test_to_dict(self):
        """Test serialization to dictionary."""
        payload = WorkerStartedPayload(
            swarm_id="swarm-123",
            worker_id="w-1",
            worker_name="Agent",
            worker_type="custom",
            role="Worker",
            task_description="",
            started_at="",
        )

        data = payload.to_dict()
        assert data["worker_id"] == "w-1"
        assert data["worker_type"] == "custom"


class TestWorkerProgressPayload:
    """Test WorkerProgressPayload."""

    def test_create_payload(self):
        """Test creating a WorkerProgressPayload."""
        payload = WorkerProgressPayload(
            swarm_id="swarm-123",
            worker_id="worker-1",
            progress=75,
            status="running",
            updated_at="2026-01-29T12:02:00Z",
            current_action="Analyzing data",
        )

        assert payload.progress == 75
        assert payload.current_action == "Analyzing data"
        assert payload.status == "running"

    def test_to_dict_with_none_action(self):
        """Test serialization with None current_action."""
        payload = WorkerProgressPayload(
            swarm_id="swarm-123",
            worker_id="w-1",
            progress=50,
            status="thinking",
            updated_at="2026-01-29T12:00:00Z",
            current_action=None,
        )

        data = payload.to_dict()
        assert data["progress"] == 50
        assert data["current_action"] is None


class TestWorkerThinkingPayload:
    """Test WorkerThinkingPayload."""

    def test_create_payload(self):
        """Test creating a WorkerThinkingPayload."""
        payload = WorkerThinkingPayload(
            swarm_id="swarm-123",
            worker_id="worker-1",
            thinking_content="Analyzing the search results to identify patterns...",
            timestamp="2026-01-29T12:01:00Z",
            token_count=150,
        )

        assert payload.thinking_content.startswith("Analyzing")
        assert payload.token_count == 150

    def test_to_dict(self):
        """Test serialization to dictionary."""
        payload = WorkerThinkingPayload(
            swarm_id="s-1",
            worker_id="w-1",
            thinking_content="Thinking...",
            timestamp="2026-01-29T12:00:00Z",
            token_count=None,
        )

        data = payload.to_dict()
        assert data["thinking_content"] == "Thinking..."
        assert data["token_count"] is None


class TestWorkerToolCallPayload:
    """Test WorkerToolCallPayload."""

    def test_create_payload_pending(self):
        """Test creating a pending tool call payload."""
        payload = WorkerToolCallPayload(
            swarm_id="swarm-123",
            worker_id="worker-1",
            tool_call_id="tc-1",
            tool_name="web_search",
            status="pending",
            timestamp="2026-01-29T12:00:00Z",
            input_args={"query": "AI news 2026"},
        )

        assert payload.tool_name == "web_search"
        assert payload.status == "pending"
        assert payload.input_args == {"query": "AI news 2026"}
        assert payload.output_result is None

    def test_create_payload_completed(self):
        """Test creating a completed tool call payload."""
        payload = WorkerToolCallPayload(
            swarm_id="swarm-123",
            worker_id="worker-1",
            tool_call_id="tc-1",
            tool_name="web_search",
            status="completed",
            timestamp="2026-01-29T12:00:30Z",
            input_args={"query": "test"},
            output_result={"results": ["item1", "item2"]},
            error=None,
            duration_ms=30000,
        )

        assert payload.status == "completed"
        assert payload.output_result == {"results": ["item1", "item2"]}
        assert payload.duration_ms == 30000

    def test_to_dict(self):
        """Test serialization to dictionary."""
        payload = WorkerToolCallPayload(
            swarm_id="s-1",
            worker_id="w-1",
            tool_call_id="tc-1",
            tool_name="search",
            status="failed",
            timestamp="2026-01-29T12:00:00Z",
            input_args={},
            error="Connection timeout",
        )

        data = payload.to_dict()
        assert data["status"] == "failed"
        assert data["error"] == "Connection timeout"


class TestWorkerMessagePayload:
    """Test WorkerMessagePayload."""

    def test_create_payload(self):
        """Test creating a WorkerMessagePayload."""
        payload = WorkerMessagePayload(
            swarm_id="swarm-123",
            worker_id="worker-1",
            role="assistant",
            content="I found 10 relevant articles.",
            timestamp="2026-01-29T12:01:00Z",
            tool_call_id=None,
        )

        assert payload.role == "assistant"
        assert payload.content == "I found 10 relevant articles."

    def test_to_dict_with_tool_call_id(self):
        """Test serialization with tool_call_id."""
        payload = WorkerMessagePayload(
            swarm_id="s-1",
            worker_id="w-1",
            role="tool",
            content="Search results: ...",
            timestamp="2026-01-29T12:00:00Z",
            tool_call_id="tc-123",
        )

        data = payload.to_dict()
        assert data["role"] == "tool"
        assert data["tool_call_id"] == "tc-123"


class TestWorkerCompletedPayload:
    """Test WorkerCompletedPayload."""

    def test_create_payload_success(self):
        """Test creating a successful completion payload."""
        payload = WorkerCompletedPayload(
            swarm_id="swarm-123",
            worker_id="worker-1",
            status="completed",
            duration_ms=60000,
            completed_at="2026-01-29T12:01:00Z",
            result={"summary": "Task done"},
            error=None,
        )

        assert payload.status == "completed"
        assert payload.duration_ms == 60000
        assert payload.result == {"summary": "Task done"}
        assert payload.error is None

    def test_create_payload_failed(self):
        """Test creating a failed completion payload."""
        payload = WorkerCompletedPayload(
            swarm_id="swarm-123",
            worker_id="worker-1",
            status="failed",
            duration_ms=5000,
            completed_at="2026-01-29T12:00:05Z",
            result=None,
            error="API rate limit exceeded",
        )

        assert payload.status == "failed"
        assert payload.error == "API rate limit exceeded"
        assert payload.result is None

    def test_to_dict(self):
        """Test serialization to dictionary."""
        payload = WorkerCompletedPayload(
            swarm_id="s-1",
            worker_id="w-1",
            status="completed",
            duration_ms=10000,
            completed_at="2026-01-29T12:00:00Z",
        )

        data = payload.to_dict()
        assert data["status"] == "completed"
        assert data["duration_ms"] == 10000

# =============================================================================
# IPA Platform - DevTools Unit Tests
# =============================================================================
# Sprint 4: Developer Experience - DevUI Visual Debugging
#
# Comprehensive tests for execution tracing and debugging functionality.
#
# Author: IPA Platform Team
# Created: 2025-11-30
# =============================================================================

from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.domain.devtools import (
    ExecutionTracer,
    TraceEvent,
    TraceEventType,
    TracerError,
)
from src.domain.devtools.tracer import (
    ExecutionTrace,
    TraceSeverity,
    TraceSpan,
    TraceStatistics,
)


# =============================================================================
# Tracer Service Tests
# =============================================================================


class TestExecutionTracer:
    """Test ExecutionTracer service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tracer = ExecutionTracer()
        self.execution_id = uuid4()
        self.workflow_id = uuid4()

    def teardown_method(self):
        """Clean up after tests."""
        self.tracer.clear_all()

    # =========================================================================
    # Trace Lifecycle Tests
    # =========================================================================

    def test_start_trace(self):
        """Test starting a new trace."""
        trace = self.tracer.start_trace(
            execution_id=self.execution_id,
            workflow_id=self.workflow_id,
            metadata={"test": "value"},
        )

        assert trace is not None
        assert trace.execution_id == self.execution_id
        assert trace.workflow_id == self.workflow_id
        assert trace.status == "running"
        assert trace.metadata["test"] == "value"
        assert len(trace.events) == 1  # WORKFLOW_START event
        assert trace.events[0].event_type == TraceEventType.WORKFLOW_START

    def test_end_trace(self):
        """Test ending a trace."""
        self.tracer.start_trace(
            execution_id=self.execution_id,
            workflow_id=self.workflow_id,
        )

        trace = self.tracer.end_trace(
            execution_id=self.execution_id,
            status="completed",
            result={"output": "success"},
        )

        assert trace is not None
        assert trace.status == "completed"
        assert trace.ended_at is not None
        assert len(trace.events) == 2  # START and END events

    def test_end_trace_not_found(self):
        """Test ending non-existent trace."""
        result = self.tracer.end_trace(
            execution_id=uuid4(),
            status="completed",
        )
        assert result is None

    def test_get_trace(self):
        """Test getting a trace."""
        self.tracer.start_trace(
            execution_id=self.execution_id,
            workflow_id=self.workflow_id,
        )

        trace = self.tracer.get_trace(self.execution_id)
        assert trace is not None
        assert trace.execution_id == self.execution_id

    def test_get_trace_not_found(self):
        """Test getting non-existent trace."""
        trace = self.tracer.get_trace(uuid4())
        assert trace is None

    def test_delete_trace(self):
        """Test deleting a trace."""
        self.tracer.start_trace(
            execution_id=self.execution_id,
            workflow_id=self.workflow_id,
        )

        result = self.tracer.delete_trace(self.execution_id)
        assert result is True

        trace = self.tracer.get_trace(self.execution_id)
        assert trace is None

    def test_delete_trace_not_found(self):
        """Test deleting non-existent trace."""
        result = self.tracer.delete_trace(uuid4())
        assert result is False

    def test_list_traces(self):
        """Test listing traces."""
        # Create multiple traces
        for i in range(5):
            self.tracer.start_trace(
                execution_id=uuid4(),
                workflow_id=self.workflow_id,
            )

        traces = self.tracer.list_traces()
        assert len(traces) == 5

    def test_list_traces_with_workflow_filter(self):
        """Test listing traces with workflow filter."""
        other_workflow = uuid4()

        self.tracer.start_trace(
            execution_id=uuid4(),
            workflow_id=self.workflow_id,
        )
        self.tracer.start_trace(
            execution_id=uuid4(),
            workflow_id=other_workflow,
        )

        traces = self.tracer.list_traces(workflow_id=self.workflow_id)
        assert len(traces) == 1
        assert traces[0].workflow_id == self.workflow_id

    def test_list_traces_with_status_filter(self):
        """Test listing traces with status filter."""
        exec1 = uuid4()
        exec2 = uuid4()

        self.tracer.start_trace(execution_id=exec1, workflow_id=self.workflow_id)
        self.tracer.start_trace(execution_id=exec2, workflow_id=self.workflow_id)
        self.tracer.end_trace(execution_id=exec1, status="completed")

        running = self.tracer.list_traces(status="running")
        completed = self.tracer.list_traces(status="completed")

        assert len(running) == 1
        assert len(completed) == 1

    def test_list_traces_with_limit(self):
        """Test listing traces with limit."""
        for i in range(10):
            self.tracer.start_trace(
                execution_id=uuid4(),
                workflow_id=self.workflow_id,
            )

        traces = self.tracer.list_traces(limit=5)
        assert len(traces) == 5

    # =========================================================================
    # Event Tests
    # =========================================================================

    def test_add_event(self):
        """Test adding an event."""
        self.tracer.start_trace(
            execution_id=self.execution_id,
            workflow_id=self.workflow_id,
        )

        event = self.tracer.add_event(
            execution_id=self.execution_id,
            event_type=TraceEventType.LLM_REQUEST,
            data={"prompt": "Hello, world!"},
            severity=TraceSeverity.INFO,
            executor_id="test_executor",
            step_number=1,
        )

        assert event is not None
        assert event.event_type == TraceEventType.LLM_REQUEST
        assert event.data["prompt"] == "Hello, world!"
        assert event.executor_id == "test_executor"
        assert event.step_number == 1

    def test_add_event_trace_not_found(self):
        """Test adding event to non-existent trace."""
        event = self.tracer.add_event(
            execution_id=uuid4(),
            event_type=TraceEventType.LLM_REQUEST,
            data={},
        )
        assert event is None

    def test_get_events(self):
        """Test getting events."""
        self.tracer.start_trace(
            execution_id=self.execution_id,
            workflow_id=self.workflow_id,
        )

        # Add various events
        self.tracer.add_event(
            execution_id=self.execution_id,
            event_type=TraceEventType.LLM_REQUEST,
            data={"prompt": "test"},
        )
        self.tracer.add_event(
            execution_id=self.execution_id,
            event_type=TraceEventType.LLM_RESPONSE,
            data={"response": "result"},
        )
        self.tracer.add_event(
            execution_id=self.execution_id,
            event_type=TraceEventType.TOOL_CALL,
            data={"tool_name": "search"},
        )

        events = self.tracer.get_events(self.execution_id)
        assert len(events) == 4  # Including WORKFLOW_START

    def test_get_events_with_type_filter(self):
        """Test getting events with type filter."""
        self.tracer.start_trace(
            execution_id=self.execution_id,
            workflow_id=self.workflow_id,
        )

        self.tracer.add_event(
            execution_id=self.execution_id,
            event_type=TraceEventType.LLM_REQUEST,
            data={},
        )
        self.tracer.add_event(
            execution_id=self.execution_id,
            event_type=TraceEventType.TOOL_CALL,
            data={},
        )

        llm_events = self.tracer.get_events(
            execution_id=self.execution_id,
            event_types=[TraceEventType.LLM_REQUEST],
        )
        assert len(llm_events) == 1
        assert llm_events[0].event_type == TraceEventType.LLM_REQUEST

    def test_get_events_with_severity_filter(self):
        """Test getting events with severity filter."""
        self.tracer.start_trace(
            execution_id=self.execution_id,
            workflow_id=self.workflow_id,
        )

        self.tracer.add_event(
            execution_id=self.execution_id,
            event_type=TraceEventType.WARNING,
            data={"message": "Warning!"},
            severity=TraceSeverity.WARNING,
        )
        self.tracer.add_event(
            execution_id=self.execution_id,
            event_type=TraceEventType.ERROR,
            data={"message": "Error!"},
            severity=TraceSeverity.ERROR,
        )

        warnings = self.tracer.get_events(
            execution_id=self.execution_id,
            severity=TraceSeverity.WARNING,
        )
        assert len(warnings) == 1

    def test_get_events_with_executor_filter(self):
        """Test getting events with executor filter."""
        self.tracer.start_trace(
            execution_id=self.execution_id,
            workflow_id=self.workflow_id,
        )

        self.tracer.add_event(
            execution_id=self.execution_id,
            event_type=TraceEventType.EXECUTOR_START,
            data={},
            executor_id="executor_a",
        )
        self.tracer.add_event(
            execution_id=self.execution_id,
            event_type=TraceEventType.EXECUTOR_START,
            data={},
            executor_id="executor_b",
        )

        events = self.tracer.get_events(
            execution_id=self.execution_id,
            executor_id="executor_a",
        )
        assert len(events) == 1

    # =========================================================================
    # Span Tests
    # =========================================================================

    def test_start_span(self):
        """Test starting a span."""
        self.tracer.start_trace(
            execution_id=self.execution_id,
            workflow_id=self.workflow_id,
        )

        span = self.tracer.start_span(
            execution_id=self.execution_id,
            name="llm_call",
            metadata={"model": "gpt-4"},
        )

        assert span is not None
        assert span.name == "llm_call"
        assert span.metadata["model"] == "gpt-4"
        assert span.end_time is None

    def test_start_span_trace_not_found(self):
        """Test starting span on non-existent trace."""
        span = self.tracer.start_span(
            execution_id=uuid4(),
            name="test",
        )
        assert span is None

    def test_end_span(self):
        """Test ending a span."""
        self.tracer.start_trace(
            execution_id=self.execution_id,
            workflow_id=self.workflow_id,
        )

        span = self.tracer.start_span(
            execution_id=self.execution_id,
            name="test_span",
        )

        ended_span = self.tracer.end_span(span.id)
        assert ended_span is not None
        assert ended_span.end_time is not None
        assert ended_span.duration_ms is not None

    def test_end_span_not_found(self):
        """Test ending non-existent span."""
        span = self.tracer.end_span(uuid4())
        assert span is None

    def test_nested_spans(self):
        """Test nested spans."""
        self.tracer.start_trace(
            execution_id=self.execution_id,
            workflow_id=self.workflow_id,
        )

        parent_span = self.tracer.start_span(
            execution_id=self.execution_id,
            name="parent",
        )

        child_span = self.tracer.start_span(
            execution_id=self.execution_id,
            name="child",
            parent_span_id=parent_span.id,
        )

        assert child_span.parent_span_id == parent_span.id

    # =========================================================================
    # Timeline Tests
    # =========================================================================

    def test_get_timeline(self):
        """Test getting timeline."""
        self.tracer.start_trace(
            execution_id=self.execution_id,
            workflow_id=self.workflow_id,
        )

        self.tracer.add_event(
            execution_id=self.execution_id,
            event_type=TraceEventType.LLM_REQUEST,
            data={"prompt": "Hello"},
        )
        self.tracer.add_event(
            execution_id=self.execution_id,
            event_type=TraceEventType.LLM_RESPONSE,
            data={"response": "Hi"},
        )

        timeline = self.tracer.get_timeline(self.execution_id)
        assert len(timeline) == 3  # START + REQUEST + RESPONSE

    def test_get_timeline_empty_trace(self):
        """Test getting timeline for non-existent trace."""
        timeline = self.tracer.get_timeline(uuid4())
        assert len(timeline) == 0

    def test_get_timeline_without_details(self):
        """Test getting timeline without details."""
        self.tracer.start_trace(
            execution_id=self.execution_id,
            workflow_id=self.workflow_id,
        )

        timeline = self.tracer.get_timeline(
            self.execution_id,
            include_details=False,
        )
        assert len(timeline) == 1

    # =========================================================================
    # Statistics Tests
    # =========================================================================

    def test_get_statistics(self):
        """Test getting statistics."""
        self.tracer.start_trace(
            execution_id=self.execution_id,
            workflow_id=self.workflow_id,
        )

        # Add various events
        self.tracer.add_event(
            execution_id=self.execution_id,
            event_type=TraceEventType.LLM_REQUEST,
            data={},
        )
        self.tracer.add_event(
            execution_id=self.execution_id,
            event_type=TraceEventType.LLM_RESPONSE,
            data={},
            duration_ms=100.0,
        )
        self.tracer.add_event(
            execution_id=self.execution_id,
            event_type=TraceEventType.TOOL_CALL,
            data={"tool_name": "search"},
        )
        self.tracer.add_event(
            execution_id=self.execution_id,
            event_type=TraceEventType.TOOL_RESULT,
            data={},
            duration_ms=50.0,
        )
        self.tracer.add_event(
            execution_id=self.execution_id,
            event_type=TraceEventType.ERROR,
            data={"message": "Error!"},
        )
        self.tracer.add_event(
            execution_id=self.execution_id,
            event_type=TraceEventType.WARNING,
            data={"message": "Warning!"},
        )
        self.tracer.add_event(
            execution_id=self.execution_id,
            event_type=TraceEventType.CHECKPOINT_CREATED,
            data={},
        )

        stats = self.tracer.get_statistics(self.execution_id)

        assert stats is not None
        assert stats.total_events == 8  # Including WORKFLOW_START
        assert stats.llm_calls == 1
        assert stats.llm_total_ms == 100.0
        assert stats.tool_calls == 1
        assert stats.tool_total_ms == 50.0
        assert stats.errors == 1
        assert stats.warnings == 1
        assert stats.checkpoints == 1

    def test_get_statistics_not_found(self):
        """Test getting statistics for non-existent trace."""
        stats = self.tracer.get_statistics(uuid4())
        assert stats is None

    # =========================================================================
    # Event Handler Tests
    # =========================================================================

    def test_event_handler(self):
        """Test event handler registration and notification."""
        received_events = []

        def handler(event):
            received_events.append(event)

        self.tracer.on_event(TraceEventType.LLM_REQUEST, handler)

        self.tracer.start_trace(
            execution_id=self.execution_id,
            workflow_id=self.workflow_id,
        )
        self.tracer.add_event(
            execution_id=self.execution_id,
            event_type=TraceEventType.LLM_REQUEST,
            data={},
        )

        assert len(received_events) == 1
        assert received_events[0].event_type == TraceEventType.LLM_REQUEST

    def test_event_handler_error_isolation(self):
        """Test that handler errors don't affect tracing."""
        def bad_handler(event):
            raise Exception("Handler error")

        self.tracer.on_event(TraceEventType.LLM_REQUEST, bad_handler)

        self.tracer.start_trace(
            execution_id=self.execution_id,
            workflow_id=self.workflow_id,
        )

        # Should not raise
        event = self.tracer.add_event(
            execution_id=self.execution_id,
            event_type=TraceEventType.LLM_REQUEST,
            data={},
        )
        assert event is not None

    # =========================================================================
    # Streaming Tests
    # =========================================================================

    def test_subscribe_unsubscribe(self):
        """Test subscribe and unsubscribe."""
        received_events = []

        def callback(event):
            received_events.append(event)

        self.tracer.start_trace(
            execution_id=self.execution_id,
            workflow_id=self.workflow_id,
        )

        self.tracer.subscribe(self.execution_id, callback)

        self.tracer.add_event(
            execution_id=self.execution_id,
            event_type=TraceEventType.LLM_REQUEST,
            data={},
        )

        assert len(received_events) == 1

        self.tracer.unsubscribe(self.execution_id, callback)

        self.tracer.add_event(
            execution_id=self.execution_id,
            event_type=TraceEventType.LLM_RESPONSE,
            data={},
        )

        assert len(received_events) == 1  # No new events

    def test_subscriber_error_isolation(self):
        """Test that subscriber errors don't affect tracing."""
        def bad_callback(event):
            raise Exception("Subscriber error")

        self.tracer.start_trace(
            execution_id=self.execution_id,
            workflow_id=self.workflow_id,
        )

        self.tracer.subscribe(self.execution_id, bad_callback)

        # Should not raise
        event = self.tracer.add_event(
            execution_id=self.execution_id,
            event_type=TraceEventType.LLM_REQUEST,
            data={},
        )
        assert event is not None

    # =========================================================================
    # Utility Tests
    # =========================================================================

    def test_clear_all(self):
        """Test clearing all traces."""
        for i in range(5):
            self.tracer.start_trace(
                execution_id=uuid4(),
                workflow_id=self.workflow_id,
            )

        assert self.tracer.get_trace_count() == 5

        self.tracer.clear_all()

        assert self.tracer.get_trace_count() == 0

    def test_trace_count(self):
        """Test trace count."""
        assert self.tracer.get_trace_count() == 0

        self.tracer.start_trace(
            execution_id=self.execution_id,
            workflow_id=self.workflow_id,
        )

        assert self.tracer.get_trace_count() == 1


# =============================================================================
# Data Class Tests
# =============================================================================


class TestTraceEvent:
    """Test TraceEvent data class."""

    def test_to_dict(self):
        """Test to_dict conversion."""
        event = TraceEvent(
            id=uuid4(),
            trace_id=uuid4(),
            event_type=TraceEventType.LLM_REQUEST,
            timestamp=datetime.utcnow(),
            data={"prompt": "Hello"},
            severity=TraceSeverity.INFO,
            tags=["test"],
        )

        d = event.to_dict()

        assert "id" in d
        assert d["event_type"] == "llm_request"
        assert d["data"]["prompt"] == "Hello"
        assert d["severity"] == "info"
        assert "test" in d["tags"]


class TestTraceSpan:
    """Test TraceSpan data class."""

    def test_duration_calculation(self):
        """Test duration calculation."""
        now = datetime.utcnow()
        span = TraceSpan(
            id=uuid4(),
            name="test",
            start_time=now,
        )

        assert span.duration_ms is None

        # Set end time (simulate 100ms later)
        from datetime import timedelta
        span.end_time = now + timedelta(milliseconds=100)

        assert span.duration_ms is not None
        assert span.duration_ms >= 100

    def test_to_dict(self):
        """Test to_dict conversion."""
        span = TraceSpan(
            id=uuid4(),
            name="test_span",
            start_time=datetime.utcnow(),
        )

        d = span.to_dict()

        assert d["name"] == "test_span"
        assert d["end_time"] is None


class TestExecutionTrace:
    """Test ExecutionTrace data class."""

    def test_to_dict(self):
        """Test to_dict conversion."""
        trace = ExecutionTrace(
            id=uuid4(),
            execution_id=uuid4(),
            workflow_id=uuid4(),
            started_at=datetime.utcnow(),
            status="running",
        )

        d = trace.to_dict()

        assert d["status"] == "running"
        assert d["event_count"] == 0
        assert d["span_count"] == 0


class TestTraceStatistics:
    """Test TraceStatistics data class."""

    def test_to_dict(self):
        """Test to_dict conversion."""
        stats = TraceStatistics(
            total_events=10,
            events_by_type={"llm_request": 5},
            total_duration_ms=1000.0,
            llm_calls=5,
            llm_total_ms=500.0,
            tool_calls=3,
            tool_total_ms=200.0,
            errors=1,
            warnings=2,
            checkpoints=1,
        )

        d = stats.to_dict()

        assert d["total_events"] == 10
        assert d["llm_calls"] == 5
        assert d["errors"] == 1


# =============================================================================
# API Tests
# =============================================================================


class TestDevToolsAPI:
    """Test DevTools API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from main import app
        from src.api.v1.devtools.routes import set_tracer

        # Create fresh tracer for each test
        tracer = ExecutionTracer()
        set_tracer(tracer)

        with TestClient(app) as client:
            yield client

        # Cleanup
        tracer.clear_all()

    @pytest.fixture
    def execution_id(self):
        """Generate execution ID."""
        return uuid4()

    @pytest.fixture
    def workflow_id(self):
        """Generate workflow ID."""
        return uuid4()

    # =========================================================================
    # Health Check Tests
    # =========================================================================

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/devtools/health")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "devtools"
        assert data["status"] == "healthy"

    # =========================================================================
    # Trace Management Tests
    # =========================================================================

    def test_start_trace_api(self, client, execution_id, workflow_id):
        """Test start trace endpoint."""
        response = client.post(
            "/api/v1/devtools/traces",
            json={
                "execution_id": str(execution_id),
                "workflow_id": str(workflow_id),
                "metadata": {"test": "value"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["execution_id"] == str(execution_id)
        assert data["status"] == "running"

    def test_get_trace_api(self, client, execution_id, workflow_id):
        """Test get trace endpoint."""
        # Start trace first
        client.post(
            "/api/v1/devtools/traces",
            json={
                "execution_id": str(execution_id),
                "workflow_id": str(workflow_id),
            },
        )

        response = client.get(f"/api/v1/devtools/traces/{execution_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["execution_id"] == str(execution_id)

    def test_get_trace_not_found(self, client):
        """Test get non-existent trace."""
        response = client.get(f"/api/v1/devtools/traces/{uuid4()}")
        assert response.status_code == 404

    def test_end_trace_api(self, client, execution_id, workflow_id):
        """Test end trace endpoint."""
        client.post(
            "/api/v1/devtools/traces",
            json={
                "execution_id": str(execution_id),
                "workflow_id": str(workflow_id),
            },
        )

        response = client.post(
            f"/api/v1/devtools/traces/{execution_id}/end",
            json={
                "status": "completed",
                "result": {"output": "success"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    def test_delete_trace_api(self, client, execution_id, workflow_id):
        """Test delete trace endpoint."""
        client.post(
            "/api/v1/devtools/traces",
            json={
                "execution_id": str(execution_id),
                "workflow_id": str(workflow_id),
            },
        )

        response = client.delete(f"/api/v1/devtools/traces/{execution_id}")
        assert response.status_code == 200

        response = client.get(f"/api/v1/devtools/traces/{execution_id}")
        assert response.status_code == 404

    def test_list_traces_api(self, client, workflow_id):
        """Test list traces endpoint."""
        # Create multiple traces
        for i in range(3):
            client.post(
                "/api/v1/devtools/traces",
                json={
                    "execution_id": str(uuid4()),
                    "workflow_id": str(workflow_id),
                },
            )

        response = client.get("/api/v1/devtools/traces")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3

    # =========================================================================
    # Event Management Tests
    # =========================================================================

    def test_add_event_api(self, client, execution_id, workflow_id):
        """Test add event endpoint."""
        client.post(
            "/api/v1/devtools/traces",
            json={
                "execution_id": str(execution_id),
                "workflow_id": str(workflow_id),
            },
        )

        response = client.post(
            f"/api/v1/devtools/traces/{execution_id}/events",
            json={
                "event_type": "llm_request",
                "data": {"prompt": "Hello"},
                "severity": "info",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["event_type"] == "llm_request"

    def test_add_event_invalid_type(self, client, execution_id, workflow_id):
        """Test add event with invalid type."""
        client.post(
            "/api/v1/devtools/traces",
            json={
                "execution_id": str(execution_id),
                "workflow_id": str(workflow_id),
            },
        )

        response = client.post(
            f"/api/v1/devtools/traces/{execution_id}/events",
            json={
                "event_type": "invalid_type",
                "data": {},
            },
        )

        assert response.status_code == 400

    def test_get_events_api(self, client, execution_id, workflow_id):
        """Test get events endpoint."""
        client.post(
            "/api/v1/devtools/traces",
            json={
                "execution_id": str(execution_id),
                "workflow_id": str(workflow_id),
            },
        )

        response = client.get(f"/api/v1/devtools/traces/{execution_id}/events")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1  # At least WORKFLOW_START

    # =========================================================================
    # Span Management Tests
    # =========================================================================

    def test_start_span_api(self, client, execution_id, workflow_id):
        """Test start span endpoint."""
        client.post(
            "/api/v1/devtools/traces",
            json={
                "execution_id": str(execution_id),
                "workflow_id": str(workflow_id),
            },
        )

        response = client.post(
            f"/api/v1/devtools/traces/{execution_id}/spans",
            json={
                "name": "test_span",
                "metadata": {"key": "value"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test_span"

    def test_end_span_api(self, client, execution_id, workflow_id):
        """Test end span endpoint."""
        client.post(
            "/api/v1/devtools/traces",
            json={
                "execution_id": str(execution_id),
                "workflow_id": str(workflow_id),
            },
        )

        span_response = client.post(
            f"/api/v1/devtools/traces/{execution_id}/spans",
            json={"name": "test_span"},
        )
        span_id = span_response.json()["id"]

        response = client.post(f"/api/v1/devtools/spans/{span_id}/end")

        assert response.status_code == 200
        data = response.json()
        assert data["end_time"] is not None

    # =========================================================================
    # Timeline Tests
    # =========================================================================

    def test_get_timeline_api(self, client, execution_id, workflow_id):
        """Test get timeline endpoint."""
        client.post(
            "/api/v1/devtools/traces",
            json={
                "execution_id": str(execution_id),
                "workflow_id": str(workflow_id),
            },
        )

        response = client.get(f"/api/v1/devtools/traces/{execution_id}/timeline")

        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert data["execution_id"] == str(execution_id)

    # =========================================================================
    # Statistics Tests
    # =========================================================================

    def test_get_statistics_api(self, client, execution_id, workflow_id):
        """Test get statistics endpoint."""
        client.post(
            "/api/v1/devtools/traces",
            json={
                "execution_id": str(execution_id),
                "workflow_id": str(workflow_id),
            },
        )

        response = client.get(f"/api/v1/devtools/traces/{execution_id}/statistics")

        assert response.status_code == 200
        data = response.json()
        assert "total_events" in data
        assert "llm_calls" in data
        assert "tool_calls" in data

"""
Agent Swarm E2E Tests

End-to-end tests for the Agent Swarm execution flow.
Tests the complete workflow from Swarm creation to completion.

Sprint 106 - Story 106-1: E2E Test Suite
"""

import asyncio
import json
import pytest
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from main import app
from src.integrations.swarm import (
    SwarmTracker,
    SwarmMode,
    WorkerType,
    SwarmStatus,
    WorkerStatus,
    set_swarm_tracker,
)
from src.integrations.swarm.events import (
    SwarmEventEmitter,
    create_swarm_emitter,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sync_client():
    """Create a synchronous test client."""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Create an async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def tracker():
    """Create and set up a test tracker."""
    tracker = SwarmTracker()
    set_swarm_tracker(tracker)
    return tracker


@pytest.fixture
def mock_event_callback():
    """Create a mock event callback that collects events."""
    events: List[Any] = []

    async def callback(event):
        events.append(event)

    callback.events = events
    return callback


@pytest.fixture
async def emitter(mock_event_callback):
    """Create a configured SwarmEventEmitter."""
    emitter = create_swarm_emitter(
        event_callback=mock_event_callback,
        throttle_interval_ms=50,  # Fast for testing
        batch_size=10,
    )
    await emitter.start()
    yield emitter
    await emitter.stop()


@pytest.fixture
def multi_agent_swarm(tracker):
    """Create a multi-agent swarm for testing."""
    swarm = tracker.create_swarm(
        swarm_id="e2e-swarm-001",
        mode=SwarmMode.SEQUENTIAL,
        metadata={"task": "E2E Test", "test": True},
    )

    # Start first worker
    tracker.start_worker(
        swarm_id="e2e-swarm-001",
        worker_id="diagnostic-worker",
        worker_name="DiagnosticWorker",
        worker_type=WorkerType.ANALYST,
        role="diagnostic",
        current_task="Analyzing ETL Pipeline errors",
    )

    # Start second worker
    tracker.start_worker(
        swarm_id="e2e-swarm-001",
        worker_id="remediation-worker",
        worker_name="RemediationWorker",
        worker_type=WorkerType.CUSTOM,
        role="remediation",
        current_task="Preparing remediation actions",
    )

    return swarm


# ============================================================================
# E2E Test Class
# ============================================================================


class TestSwarmE2E:
    """Agent Swarm End-to-End Tests."""

    # ========================================================================
    # Test: Swarm Creation and Execution Flow
    # ========================================================================

    def test_swarm_creation_and_execution(self, sync_client, tracker):
        """Test complete Swarm creation and execution flow."""
        # 1. Create a new swarm
        swarm = tracker.create_swarm(
            swarm_id="exec-test-swarm",
            mode=SwarmMode.PARALLEL,
            metadata={"test_scenario": "creation_and_execution"},
        )
        assert swarm is not None
        assert swarm.swarm_id == "exec-test-swarm"
        assert swarm.status == SwarmStatus.INITIALIZING

        # 2. Verify via API
        response = sync_client.get("/api/v1/swarm/exec-test-swarm")
        assert response.status_code == 200
        data = response.json()
        assert data["swarm_id"] == "exec-test-swarm"
        assert data["mode"] == "parallel"
        assert data["status"] == "initializing"

        # 3. Start workers
        tracker.start_worker(
            swarm_id="exec-test-swarm",
            worker_id="worker-a",
            worker_name="WorkerA",
            worker_type=WorkerType.RESEARCH,
            role="researcher",
            current_task="Gathering data",
        )
        tracker.start_worker(
            swarm_id="exec-test-swarm",
            worker_id="worker-b",
            worker_name="WorkerB",
            worker_type=WorkerType.WRITER,
            role="writer",
            current_task="Writing report",
        )

        # 4. Verify swarm is now running
        response = sync_client.get("/api/v1/swarm/exec-test-swarm")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert len(data["workers"]) == 2

        # 5. Update worker progress
        tracker.update_worker_progress("exec-test-swarm", "worker-a", 50)
        tracker.update_worker_progress("exec-test-swarm", "worker-b", 25)

        # 6. Verify overall progress
        response = sync_client.get("/api/v1/swarm/exec-test-swarm")
        data = response.json()
        # Average of 50 and 25 = 37 (rounded)
        assert data["overall_progress"] == 37

        # 7. Add tool calls
        tracker.add_worker_tool_call(
            swarm_id="exec-test-swarm",
            worker_id="worker-a",
            tool_id="tc-001",
            tool_name="azure:query_adf_logs",
            is_mcp=True,
            input_params={"pipeline": "APAC_ETL"},
        )
        tracker.update_tool_call_result(
            swarm_id="exec-test-swarm",
            worker_id="worker-a",
            tool_call_id="tc-001",
            result={"error_count": 47, "errors": ["Connection timeout"]},
        )

        # 8. Verify tool call via worker detail API
        response = sync_client.get(
            "/api/v1/swarm/exec-test-swarm/workers/worker-a"
        )
        assert response.status_code == 200
        worker_data = response.json()
        assert len(worker_data["tool_calls"]) == 1
        tc = worker_data["tool_calls"][0]
        assert tc["tool_name"] == "azure:query_adf_logs"
        assert tc["status"] == "completed"
        assert tc["result"]["error_count"] == 47

        # 9. Complete workers and swarm
        tracker.complete_worker("exec-test-swarm", "worker-a")
        tracker.complete_worker("exec-test-swarm", "worker-b")
        tracker.complete_swarm("exec-test-swarm")

        # 10. Verify final state
        response = sync_client.get("/api/v1/swarm/exec-test-swarm")
        data = response.json()
        assert data["status"] == "completed"
        assert data["overall_progress"] == 100

    # ========================================================================
    # Test: Swarm API Endpoints
    # ========================================================================

    def test_swarm_api_endpoints(self, sync_client, multi_agent_swarm, tracker):
        """Test all Swarm API endpoints."""
        swarm_id = "e2e-swarm-001"

        # 1. GET /swarm/{swarm_id}
        response = sync_client.get(f"/api/v1/swarm/{swarm_id}")
        assert response.status_code == 200
        swarm_data = response.json()
        assert swarm_data["swarm_id"] == swarm_id
        assert "workers" in swarm_data
        assert len(swarm_data["workers"]) == 2

        # 2. GET /swarm/{swarm_id}/workers
        response = sync_client.get(f"/api/v1/swarm/{swarm_id}/workers")
        assert response.status_code == 200
        workers_data = response.json()
        assert workers_data["swarm_id"] == swarm_id
        assert workers_data["total"] == 2
        assert len(workers_data["workers"]) == 2

        # 3. GET /swarm/{swarm_id}/workers/{worker_id}
        response = sync_client.get(
            f"/api/v1/swarm/{swarm_id}/workers/diagnostic-worker"
        )
        assert response.status_code == 200
        worker_detail = response.json()
        assert worker_detail["worker_id"] == "diagnostic-worker"
        assert worker_detail["worker_name"] == "DiagnosticWorker"
        assert worker_detail["role"] == "diagnostic"

        # 4. Verify worker summary contains correct fields
        worker_summary = swarm_data["workers"][0]
        required_fields = [
            "worker_id",
            "worker_name",
            "worker_type",
            "role",
            "status",
            "progress",
        ]
        for field in required_fields:
            assert field in worker_summary

    # ========================================================================
    # Test: Error Handling
    # ========================================================================

    def test_swarm_error_handling(self, sync_client, tracker):
        """Test error handling for invalid requests."""
        # 1. Test nonexistent swarm ID
        response = sync_client.get("/api/v1/swarm/nonexistent-swarm-999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

        # 2. Create a valid swarm for worker error tests
        tracker.create_swarm("error-test-swarm", SwarmMode.SEQUENTIAL)
        tracker.start_worker(
            "error-test-swarm",
            "valid-worker",
            "ValidWorker",
            WorkerType.CUSTOM,
            "tester",
        )

        # 3. Test nonexistent worker ID
        response = sync_client.get(
            "/api/v1/swarm/error-test-swarm/workers/nonexistent-worker"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

        # 4. Test nonexistent swarm for worker detail
        response = sync_client.get(
            "/api/v1/swarm/nonexistent-swarm/workers/any-worker"
        )
        assert response.status_code == 404

    # ========================================================================
    # Test: Worker Lifecycle
    # ========================================================================

    def test_worker_lifecycle(self, sync_client, tracker):
        """Test complete worker lifecycle."""
        swarm_id = "lifecycle-swarm"
        worker_id = "lifecycle-worker"

        # 1. Create swarm
        tracker.create_swarm(swarm_id, SwarmMode.SEQUENTIAL)

        # 2. Start worker
        tracker.start_worker(
            swarm_id,
            worker_id,
            "LifecycleWorker",
            WorkerType.ANALYST,
            "analyzer",
            current_task="Initial analysis",
        )

        # Verify running status
        response = sync_client.get(f"/api/v1/swarm/{swarm_id}/workers/{worker_id}")
        assert response.json()["status"] == "running"

        # 3. Add thinking content
        tracker.add_worker_thinking(
            swarm_id, worker_id,
            content="Analyzing the problem step by step...",
            token_count=120,
        )
        tracker.add_worker_thinking(
            swarm_id, worker_id,
            content="Found potential root cause.",
            token_count=85,
        )

        # Verify thinking contents
        response = sync_client.get(f"/api/v1/swarm/{swarm_id}/workers/{worker_id}")
        data = response.json()
        assert len(data["thinking_contents"]) == 2
        assert "step by step" in data["thinking_contents"][0]["content"]

        # 4. Add tool call
        tracker.add_worker_tool_call(
            swarm_id, worker_id,
            tool_id="tool-1",
            tool_name="database:query",
            is_mcp=False,
            input_params={"query": "SELECT * FROM logs"},
        )

        # Verify pending tool call
        response = sync_client.get(f"/api/v1/swarm/{swarm_id}/workers/{worker_id}")
        data = response.json()
        assert len(data["tool_calls"]) == 1
        assert data["tool_calls"][0]["status"] == "pending"

        # 5. Complete tool call
        tracker.update_tool_call_result(
            swarm_id, worker_id, "tool-1",
            result={"rows": 100, "duration_ms": 45},
        )

        # Verify completed tool call
        response = sync_client.get(f"/api/v1/swarm/{swarm_id}/workers/{worker_id}")
        data = response.json()
        assert data["tool_calls"][0]["status"] == "completed"
        assert data["tool_calls"][0]["result"]["rows"] == 100

        # 6. Add messages
        tracker.add_worker_message(
            swarm_id, worker_id,
            role="assistant",
            content="Analysis complete. Found 3 issues.",
        )

        # Verify messages
        response = sync_client.get(f"/api/v1/swarm/{swarm_id}/workers/{worker_id}")
        data = response.json()
        assert len(data["messages"]) == 1
        assert data["messages"][0]["role"] == "assistant"

        # 7. Update progress
        tracker.update_worker_progress(swarm_id, worker_id, 100)

        # 8. Complete worker
        tracker.complete_worker(swarm_id, worker_id)

        # Verify completed status
        response = sync_client.get(f"/api/v1/swarm/{swarm_id}/workers/{worker_id}")
        data = response.json()
        assert data["status"] == "completed"
        assert data["progress"] == 100
        assert data["completed_at"] is not None

    # ========================================================================
    # Test: Concurrent Workers
    # ========================================================================

    def test_concurrent_workers(self, sync_client, tracker):
        """Test multiple workers executing concurrently."""
        swarm_id = "concurrent-swarm"

        # Create parallel swarm
        tracker.create_swarm(swarm_id, SwarmMode.PARALLEL)

        # Start multiple workers
        for i in range(5):
            tracker.start_worker(
                swarm_id,
                f"worker-{i}",
                f"Worker{i}",
                WorkerType.CUSTOM,
                f"role-{i}",
                current_task=f"Task {i}",
            )

        # Verify all workers started
        response = sync_client.get(f"/api/v1/swarm/{swarm_id}")
        data = response.json()
        assert len(data["workers"]) == 5

        # Update progress for each worker differently
        for i in range(5):
            tracker.update_worker_progress(swarm_id, f"worker-{i}", (i + 1) * 20)

        # Verify overall progress is average
        response = sync_client.get(f"/api/v1/swarm/{swarm_id}")
        data = response.json()
        # Average of 20, 40, 60, 80, 100 = 60
        assert data["overall_progress"] == 60

        # Complete workers in order
        for i in range(5):
            tracker.complete_worker(swarm_id, f"worker-{i}")

        # Verify all completed
        response = sync_client.get(f"/api/v1/swarm/{swarm_id}/workers")
        data = response.json()
        for worker in data["workers"]:
            assert worker["status"] == "completed"


# ============================================================================
# Event Emitter E2E Tests
# ============================================================================


class TestSwarmEventEmitterE2E:
    """E2E tests for SwarmEventEmitter."""

    @pytest.mark.asyncio
    async def test_event_emission_flow(self, tracker, mock_event_callback, emitter):
        """Test complete event emission flow."""
        # Create swarm
        swarm = tracker.create_swarm(
            "event-swarm",
            SwarmMode.SEQUENTIAL,
            metadata={"test": True},
        )

        # Emit swarm_created event
        await emitter.emit_swarm_created(swarm, session_id="test-session")

        # Wait for event processing
        await asyncio.sleep(0.1)

        # Verify event was emitted
        events = mock_event_callback.events
        assert len(events) >= 1

        # Check event content
        created_event = events[0]
        assert created_event.event_name == "swarm_created"
        assert created_event.payload["swarm_id"] == "event-swarm"

    @pytest.mark.asyncio
    async def test_worker_events(self, tracker, mock_event_callback, emitter):
        """Test worker event emissions."""
        # Setup
        swarm = tracker.create_swarm("worker-event-swarm", SwarmMode.SEQUENTIAL)
        tracker.start_worker(
            "worker-event-swarm",
            "test-worker",
            "TestWorker",
            WorkerType.ANALYST,
            "tester",
        )

        swarm = tracker.get_swarm("worker-event-swarm")
        worker = swarm.get_worker_by_id("test-worker")

        # Emit worker_started event
        await emitter.emit_worker_started("worker-event-swarm", worker)
        await asyncio.sleep(0.1)

        # Emit worker_thinking event
        await emitter.emit_worker_thinking(
            "worker-event-swarm",
            worker,
            "Analyzing the problem...",
            token_count=50,
        )
        await asyncio.sleep(0.2)  # Wait for throttling

        # Verify events
        events = mock_event_callback.events
        event_names = [e.event_name for e in events]

        assert "worker_started" in event_names
        # worker_thinking might be batched, check after stop

    @pytest.mark.asyncio
    async def test_event_throttling(self, tracker, mock_event_callback, emitter):
        """Test that rapid events are throttled properly."""
        swarm = tracker.create_swarm("throttle-swarm", SwarmMode.SEQUENTIAL)
        tracker.start_worker(
            "throttle-swarm",
            "throttle-worker",
            "ThrottleWorker",
            WorkerType.CUSTOM,
            "tester",
        )

        swarm = tracker.get_swarm("throttle-swarm")
        worker = swarm.get_worker_by_id("throttle-worker")

        # Emit many progress events rapidly
        for i in range(20):
            tracker.update_worker_progress("throttle-swarm", "throttle-worker", i * 5)
            swarm = tracker.get_swarm("throttle-swarm")
            worker = swarm.get_worker_by_id("throttle-worker")
            await emitter.emit_worker_progress("throttle-swarm", worker)

        # Wait for batch processing
        await asyncio.sleep(0.5)

        # Not all 20 events should have been sent due to throttling
        events = mock_event_callback.events
        progress_events = [e for e in events if e.event_name == "worker_progress"]

        # Should have fewer than 20 events due to throttling
        assert len(progress_events) < 20


# ============================================================================
# Integration with AG-UI SSE Tests
# ============================================================================


class TestSwarmSSEIntegration:
    """Test Swarm integration with AG-UI SSE events."""

    def test_swarm_events_format(self, tracker):
        """Test that Swarm events follow AG-UI CustomEvent format."""
        # Create swarm with tracker
        swarm = tracker.create_swarm(
            "sse-format-swarm",
            SwarmMode.PARALLEL,
        )
        tracker.start_worker(
            "sse-format-swarm",
            "sse-worker",
            "SSEWorker",
            WorkerType.ANALYST,
            "analyzer",
        )

        # Get swarm status
        swarm = tracker.get_swarm("sse-format-swarm")
        worker = swarm.get_worker_by_id("sse-worker")

        # Verify data structures can be serialized to JSON
        swarm_dict = swarm.to_dict()
        worker_dict = worker.to_dict()

        # Should be JSON serializable
        swarm_json = json.dumps(swarm_dict)
        worker_json = json.dumps(worker_dict)

        # Verify structure
        assert "swarm_id" in swarm_dict
        assert "workers" in swarm_dict
        assert "worker_id" in worker_dict
        assert "status" in worker_dict

    def test_event_payload_structure(self, tracker):
        """Test event payload structures."""
        from src.integrations.swarm.events.types import (
            SwarmCreatedPayload,
            WorkerStartedPayload,
            WorkerToolCallPayload,
        )

        # Test SwarmCreatedPayload
        swarm_payload = SwarmCreatedPayload(
            swarm_id="test",
            session_id="sess-1",
            mode="sequential",
            workers=[],
            created_at=datetime.utcnow().isoformat(),
        )
        payload_dict = swarm_payload.to_dict()
        assert "swarm_id" in payload_dict
        assert "mode" in payload_dict

        # Test WorkerStartedPayload
        worker_payload = WorkerStartedPayload(
            swarm_id="test",
            worker_id="w-1",
            worker_name="Worker1",
            worker_type="analyst",
            role="analyzer",
            task_description="Test task",
            started_at=datetime.utcnow().isoformat(),
        )
        payload_dict = worker_payload.to_dict()
        assert "worker_id" in payload_dict
        assert "task_description" in payload_dict

        # Test WorkerToolCallPayload
        tool_payload = WorkerToolCallPayload(
            swarm_id="test",
            worker_id="w-1",
            tool_call_id="tc-1",
            tool_name="test_tool",
            status="completed",
            input_args={"key": "value"},
            output_result={"result": "success"},
            error=None,
            duration_ms=100,
            timestamp=datetime.utcnow().isoformat(),
        )
        payload_dict = tool_payload.to_dict()
        assert "tool_name" in payload_dict
        assert "duration_ms" in payload_dict


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

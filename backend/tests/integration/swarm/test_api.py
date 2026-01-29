"""
Integration tests for Swarm API endpoints.

Tests the REST API endpoints for swarm status and worker information.
"""

import pytest
from fastapi.testclient import TestClient

from main import app
from src.integrations.swarm import (
    SwarmTracker,
    SwarmMode,
    WorkerType,
    set_swarm_tracker,
)


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def tracker():
    """Create and set up a test tracker."""
    tracker = SwarmTracker()
    set_swarm_tracker(tracker)
    return tracker


@pytest.fixture
def sample_swarm(tracker):
    """Create a sample swarm with workers."""
    swarm = tracker.create_swarm(
        swarm_id="test-swarm-1",
        mode=SwarmMode.PARALLEL,
        metadata={"test": True},
    )

    # Add workers
    tracker.start_worker(
        swarm_id="test-swarm-1",
        worker_id="worker-1",
        worker_name="Research Agent",
        worker_type=WorkerType.RESEARCH,
        role="Data Gatherer",
        current_task="Searching for data",
    )
    tracker.update_worker_progress("test-swarm-1", "worker-1", 75)

    tracker.start_worker(
        swarm_id="test-swarm-1",
        worker_id="worker-2",
        worker_name="Writer Agent",
        worker_type=WorkerType.WRITER,
        role="Content Creator",
        current_task="Writing report",
    )
    tracker.update_worker_progress("test-swarm-1", "worker-2", 25)

    # Add some tool calls
    tracker.add_worker_tool_call(
        "test-swarm-1", "worker-1",
        tool_id="tc-1",
        tool_name="web_search",
        is_mcp=True,
        input_params={"query": "AI news"},
    )
    tracker.update_tool_call_result(
        "test-swarm-1", "worker-1", "tc-1",
        result={"results": ["item1", "item2"]},
    )

    # Add thinking content
    tracker.add_worker_thinking(
        "test-swarm-1", "worker-1",
        content="Analyzing search results...",
        token_count=50,
    )

    # Add messages
    tracker.add_worker_message(
        "test-swarm-1", "worker-1",
        role="assistant",
        content="Found 10 relevant articles.",
    )

    return swarm


class TestGetSwarmStatus:
    """Test GET /api/v1/swarm/{swarm_id} endpoint."""

    def test_get_swarm_status_success(self, client, sample_swarm):
        """Test successfully getting swarm status."""
        response = client.get("/api/v1/swarm/test-swarm-1")
        assert response.status_code == 200

        data = response.json()
        assert data["swarm_id"] == "test-swarm-1"
        assert data["mode"] == "parallel"
        assert data["status"] == "running"
        assert data["overall_progress"] == 50  # (75 + 25) / 2
        assert len(data["workers"]) == 2
        assert data["total_tool_calls"] == 1
        assert data["completed_tool_calls"] == 1

    def test_get_swarm_status_not_found(self, client, tracker):
        """Test getting a nonexistent swarm."""
        response = client.get("/api/v1/swarm/nonexistent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_swarm_workers_summary(self, client, sample_swarm):
        """Test that workers summary contains correct fields."""
        response = client.get("/api/v1/swarm/test-swarm-1")
        assert response.status_code == 200

        data = response.json()
        workers = data["workers"]

        # Find the research worker
        research_worker = next(
            w for w in workers if w["worker_id"] == "worker-1"
        )
        assert research_worker["worker_name"] == "Research Agent"
        assert research_worker["worker_type"] == "research"
        assert research_worker["status"] == "running"
        assert research_worker["progress"] == 75
        assert research_worker["tool_calls_count"] == 1


class TestListSwarmWorkers:
    """Test GET /api/v1/swarm/{swarm_id}/workers endpoint."""

    def test_list_workers_success(self, client, sample_swarm):
        """Test successfully listing workers."""
        response = client.get("/api/v1/swarm/test-swarm-1/workers")
        assert response.status_code == 200

        data = response.json()
        assert data["swarm_id"] == "test-swarm-1"
        assert data["total"] == 2
        assert len(data["workers"]) == 2

    def test_list_workers_swarm_not_found(self, client, tracker):
        """Test listing workers for nonexistent swarm."""
        response = client.get("/api/v1/swarm/nonexistent/workers")
        assert response.status_code == 404


class TestGetWorkerDetails:
    """Test GET /api/v1/swarm/{swarm_id}/workers/{worker_id} endpoint."""

    def test_get_worker_details_success(self, client, sample_swarm):
        """Test successfully getting worker details."""
        response = client.get("/api/v1/swarm/test-swarm-1/workers/worker-1")
        assert response.status_code == 200

        data = response.json()
        assert data["worker_id"] == "worker-1"
        assert data["worker_name"] == "Research Agent"
        assert data["worker_type"] == "research"
        assert data["role"] == "Data Gatherer"
        assert data["progress"] == 75

        # Check tool calls
        assert len(data["tool_calls"]) == 1
        tc = data["tool_calls"][0]
        assert tc["tool_id"] == "tc-1"
        assert tc["tool_name"] == "web_search"
        assert tc["is_mcp"] is True
        assert tc["status"] == "completed"

        # Check thinking contents
        assert len(data["thinking_contents"]) == 1
        thinking = data["thinking_contents"][0]
        assert "Analyzing" in thinking["content"]

        # Check messages
        assert len(data["messages"]) == 1
        msg = data["messages"][0]
        assert msg["role"] == "assistant"
        assert "Found 10" in msg["content"]

    def test_get_worker_swarm_not_found(self, client, tracker):
        """Test getting worker from nonexistent swarm."""
        response = client.get("/api/v1/swarm/nonexistent/workers/worker-1")
        assert response.status_code == 404

    def test_get_worker_not_found(self, client, sample_swarm):
        """Test getting nonexistent worker."""
        response = client.get("/api/v1/swarm/test-swarm-1/workers/nonexistent")
        assert response.status_code == 404


class TestSwarmLifecycle:
    """Test complete swarm lifecycle through API."""

    def test_swarm_lifecycle(self, client, tracker):
        """Test complete swarm lifecycle."""
        # Create swarm
        swarm = tracker.create_swarm("lifecycle-swarm", SwarmMode.SEQUENTIAL)

        # Initial status
        response = client.get("/api/v1/swarm/lifecycle-swarm")
        assert response.status_code == 200
        assert response.json()["status"] == "initializing"
        assert response.json()["overall_progress"] == 0

        # Start worker
        tracker.start_worker(
            "lifecycle-swarm", "w-1", "Agent", WorkerType.CUSTOM, "Worker"
        )

        response = client.get("/api/v1/swarm/lifecycle-swarm")
        assert response.json()["status"] == "running"

        # Update progress
        tracker.update_worker_progress("lifecycle-swarm", "w-1", 50)

        response = client.get("/api/v1/swarm/lifecycle-swarm")
        assert response.json()["overall_progress"] == 50

        # Complete worker
        tracker.complete_worker("lifecycle-swarm", "w-1")

        response = client.get("/api/v1/swarm/lifecycle-swarm/workers/w-1")
        assert response.json()["status"] == "completed"
        assert response.json()["progress"] == 100

        # Complete swarm
        tracker.complete_swarm("lifecycle-swarm")

        response = client.get("/api/v1/swarm/lifecycle-swarm")
        assert response.json()["status"] == "completed"
        assert response.json()["overall_progress"] == 100

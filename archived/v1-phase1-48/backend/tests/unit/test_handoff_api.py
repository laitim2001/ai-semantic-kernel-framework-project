# =============================================================================
# IPA Platform - Handoff API Unit Tests
# =============================================================================
# Sprint 8: Agent Handoff & Collaboration (Phase 2)
#
# Tests for Handoff API endpoints.
# =============================================================================

import pytest
from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.v1.handoff.routes import (
    router,
    _handoffs,
    _agent_capabilities,
    _agent_availability,
)
from src.api.v1.handoff.schemas import (
    HandoffPolicyEnum,
    HandoffStatusEnum,
    CapabilityCategoryEnum,
    MatchStrategyEnum,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_storage():
    """Clear storage before each test."""
    _handoffs.clear()
    _agent_capabilities.clear()
    _agent_availability.clear()
    yield
    _handoffs.clear()
    _agent_capabilities.clear()
    _agent_availability.clear()


@pytest.fixture
def sample_agents():
    """Create sample agents with capabilities."""
    agent1 = uuid4()
    agent2 = uuid4()
    agent3 = uuid4()

    _agent_capabilities[agent1] = [
        {
            "id": uuid4(),
            "name": "data_analysis",
            "description": "Analyze data",
            "category": CapabilityCategoryEnum.REASONING,
            "proficiency_level": 0.9,
            "created_at": datetime.utcnow(),
        },
    ]

    _agent_capabilities[agent2] = [
        {
            "id": uuid4(),
            "name": "code_generation",
            "description": "Generate code",
            "category": CapabilityCategoryEnum.ACTION,
            "proficiency_level": 0.8,
            "created_at": datetime.utcnow(),
        },
        {
            "id": uuid4(),
            "name": "data_analysis",
            "description": "Analyze data",
            "category": CapabilityCategoryEnum.REASONING,
            "proficiency_level": 0.6,
            "created_at": datetime.utcnow(),
        },
    ]

    _agent_availability[agent1] = {
        "is_available": True,
        "current_load": 0.2,
    }
    _agent_availability[agent2] = {
        "is_available": True,
        "current_load": 0.5,
    }

    return agent1, agent2, agent3


# =============================================================================
# Handoff Trigger Tests
# =============================================================================

class TestHandoffTrigger:
    """Tests for POST /handoff/trigger endpoint."""

    def test_trigger_handoff_basic(self, client):
        """Test basic handoff trigger."""
        source_id = uuid4()
        target_id = uuid4()

        response = client.post(
            "/handoff/trigger",
            json={
                "source_agent_id": str(source_id),
                "target_agent_id": str(target_id),
                "policy": "graceful",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "handoff_id" in data
        assert data["status"] == "initiated"
        assert data["source_agent_id"] == str(source_id)
        assert data["target_agent_id"] == str(target_id)

    def test_trigger_handoff_auto_match(self, client, sample_agents):
        """Test handoff with auto-matching target."""
        agent1, agent2, agent3 = sample_agents
        source_id = uuid4()

        response = client.post(
            "/handoff/trigger",
            json={
                "source_agent_id": str(source_id),
                "required_capabilities": ["data_analysis"],
                "policy": "immediate",
            },
        )

        assert response.status_code == 201
        data = response.json()
        # Should auto-match to agent1 (highest data_analysis proficiency)
        assert data["target_agent_id"] == str(agent1)

    def test_trigger_handoff_with_context(self, client):
        """Test handoff with context data."""
        response = client.post(
            "/handoff/trigger",
            json={
                "source_agent_id": str(uuid4()),
                "target_agent_id": str(uuid4()),
                "context": {
                    "task_id": "test-task",
                    "progress": 0.5,
                    "variables": {"key": "value"},
                },
                "reason": "Task requires specialized processing",
            },
        )

        assert response.status_code == 201

    def test_trigger_handoff_policies(self, client):
        """Test different handoff policies."""
        for policy in ["immediate", "graceful", "conditional"]:
            response = client.post(
                "/handoff/trigger",
                json={
                    "source_agent_id": str(uuid4()),
                    "target_agent_id": str(uuid4()),
                    "policy": policy,
                },
            )
            assert response.status_code == 201
            assert response.json()["status"] == "initiated"


# =============================================================================
# Handoff Status Tests
# =============================================================================

class TestHandoffStatus:
    """Tests for GET /handoff/{id}/status endpoint."""

    def test_get_status_success(self, client):
        """Test getting handoff status."""
        # First create a handoff
        create_resp = client.post(
            "/handoff/trigger",
            json={
                "source_agent_id": str(uuid4()),
                "target_agent_id": str(uuid4()),
            },
        )
        handoff_id = create_resp.json()["handoff_id"]

        # Get status
        response = client.get(f"/handoff/{handoff_id}/status")

        assert response.status_code == 200
        data = response.json()
        assert data["handoff_id"] == handoff_id
        assert data["status"] == "initiated"
        assert data["progress"] == 0.0
        assert data["context_transferred"] == False

    def test_get_status_not_found(self, client):
        """Test getting status of non-existent handoff."""
        response = client.get(f"/handoff/{uuid4()}/status")

        assert response.status_code == 404


# =============================================================================
# Handoff Cancel Tests
# =============================================================================

class TestHandoffCancel:
    """Tests for POST /handoff/{id}/cancel endpoint."""

    def test_cancel_handoff_success(self, client):
        """Test cancelling a handoff."""
        # Create handoff
        create_resp = client.post(
            "/handoff/trigger",
            json={
                "source_agent_id": str(uuid4()),
                "target_agent_id": str(uuid4()),
            },
        )
        handoff_id = create_resp.json()["handoff_id"]

        # Cancel
        response = client.post(
            f"/handoff/{handoff_id}/cancel",
            json={"reason": "Test cancellation"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["handoff_id"] == handoff_id
        assert data["status"] == "cancelled"
        assert data["rollback_performed"] == False

    def test_cancel_handoff_not_found(self, client):
        """Test cancelling non-existent handoff."""
        response = client.post(f"/handoff/{uuid4()}/cancel")
        assert response.status_code == 404

    def test_cancel_already_cancelled(self, client):
        """Test cancelling already cancelled handoff."""
        # Create and cancel
        create_resp = client.post(
            "/handoff/trigger",
            json={
                "source_agent_id": str(uuid4()),
                "target_agent_id": str(uuid4()),
            },
        )
        handoff_id = create_resp.json()["handoff_id"]
        client.post(f"/handoff/{handoff_id}/cancel")

        # Try to cancel again
        response = client.post(f"/handoff/{handoff_id}/cancel")
        assert response.status_code == 400


# =============================================================================
# Handoff History Tests
# =============================================================================

class TestHandoffHistory:
    """Tests for GET /handoff/history endpoint."""

    def test_get_history_empty(self, client):
        """Test getting empty history."""
        response = client.get("/handoff/history")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_get_history_with_items(self, client):
        """Test getting history with items."""
        source_id = uuid4()

        # Create multiple handoffs
        for _ in range(5):
            client.post(
                "/handoff/trigger",
                json={
                    "source_agent_id": str(source_id),
                    "target_agent_id": str(uuid4()),
                },
            )

        response = client.get("/handoff/history")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5
        assert data["total"] == 5

    def test_get_history_pagination(self, client):
        """Test history pagination."""
        # Create 15 handoffs
        for _ in range(15):
            client.post(
                "/handoff/trigger",
                json={
                    "source_agent_id": str(uuid4()),
                    "target_agent_id": str(uuid4()),
                },
            )

        # Get first page
        response = client.get("/handoff/history?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10
        assert data["total"] == 15
        assert data["has_more"] == True

        # Get second page
        response = client.get("/handoff/history?page=2&page_size=10")
        data = response.json()
        assert len(data["items"]) == 5
        assert data["has_more"] == False

    def test_get_history_filter_by_source(self, client):
        """Test filtering history by source agent."""
        source1 = uuid4()
        source2 = uuid4()

        # Create handoffs from different sources
        for _ in range(3):
            client.post(
                "/handoff/trigger",
                json={
                    "source_agent_id": str(source1),
                    "target_agent_id": str(uuid4()),
                },
            )
        for _ in range(2):
            client.post(
                "/handoff/trigger",
                json={
                    "source_agent_id": str(source2),
                    "target_agent_id": str(uuid4()),
                },
            )

        # Filter by source1
        response = client.get(f"/handoff/history?source_agent_id={source1}")
        data = response.json()
        assert data["total"] == 3

    def test_get_history_filter_by_status(self, client):
        """Test filtering history by status."""
        # Create and cancel some handoffs
        for _ in range(3):
            resp = client.post(
                "/handoff/trigger",
                json={
                    "source_agent_id": str(uuid4()),
                    "target_agent_id": str(uuid4()),
                },
            )
            handoff_id = resp.json()["handoff_id"]
            client.post(f"/handoff/{handoff_id}/cancel")

        # Create without cancelling
        for _ in range(2):
            client.post(
                "/handoff/trigger",
                json={
                    "source_agent_id": str(uuid4()),
                    "target_agent_id": str(uuid4()),
                },
            )

        # Filter by cancelled
        response = client.get("/handoff/history?status=cancelled")
        data = response.json()
        assert data["total"] == 3


# =============================================================================
# Capability Match Tests
# =============================================================================

class TestCapabilityMatch:
    """Tests for POST /handoff/capability/match endpoint."""

    def test_match_single_requirement(self, client, sample_agents):
        """Test matching with single requirement."""
        agent1, agent2, agent3 = sample_agents

        response = client.post(
            "/handoff/capability/match",
            json={
                "requirements": [
                    {
                        "capability_name": "data_analysis",
                        "min_proficiency": 0.5,
                    }
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["matches"]) == 2  # agent1 and agent2 have data_analysis

    def test_match_multiple_requirements(self, client, sample_agents):
        """Test matching with multiple requirements."""
        response = client.post(
            "/handoff/capability/match",
            json={
                "requirements": [
                    {
                        "capability_name": "data_analysis",
                        "min_proficiency": 0.5,
                    },
                    {
                        "capability_name": "code_generation",
                        "min_proficiency": 0.5,
                    },
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        # Only agent2 has both capabilities
        assert len(data["matches"]) == 1

    def test_match_with_strategy(self, client, sample_agents):
        """Test matching with different strategies."""
        for strategy in ["best_fit", "first_fit", "least_loaded"]:
            response = client.post(
                "/handoff/capability/match",
                json={
                    "requirements": [
                        {"capability_name": "data_analysis", "min_proficiency": 0.5}
                    ],
                    "strategy": strategy,
                },
            )
            assert response.status_code == 200
            assert response.json()["strategy_used"] == strategy

    def test_match_exclude_agents(self, client, sample_agents):
        """Test excluding specific agents."""
        agent1, agent2, agent3 = sample_agents

        response = client.post(
            "/handoff/capability/match",
            json={
                "requirements": [
                    {"capability_name": "data_analysis", "min_proficiency": 0.5}
                ],
                "exclude_agents": [str(agent1)],
            },
        )

        assert response.status_code == 200
        data = response.json()
        agent_ids = [m["agent_id"] for m in data["matches"]]
        assert str(agent1) not in agent_ids

    def test_match_no_results(self, client, sample_agents):
        """Test matching with no results."""
        response = client.post(
            "/handoff/capability/match",
            json={
                "requirements": [
                    {"capability_name": "nonexistent_capability"}
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["matches"]) == 0
        assert data["best_match"] is None


# =============================================================================
# Agent Capabilities Tests
# =============================================================================

class TestAgentCapabilities:
    """Tests for agent capability endpoints."""

    def test_get_capabilities_with_data(self, client, sample_agents):
        """Test getting agent capabilities."""
        agent1, agent2, agent3 = sample_agents

        response = client.get(f"/handoff/agents/{agent1}/capabilities")

        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == str(agent1)
        assert len(data["capabilities"]) == 1
        assert data["capabilities"][0]["name"] == "data_analysis"

    def test_get_capabilities_empty(self, client):
        """Test getting capabilities for unknown agent."""
        response = client.get(f"/handoff/agents/{uuid4()}/capabilities")

        assert response.status_code == 200
        data = response.json()
        assert data["capabilities"] == []

    def test_register_capability(self, client):
        """Test registering a new capability."""
        agent_id = uuid4()

        response = client.post(
            f"/handoff/agents/{agent_id}/capabilities",
            json={
                "name": "text_generation",
                "description": "Generate text",
                "category": "language",
                "proficiency_level": 0.8,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "text_generation"
        assert data["agent_id"] == str(agent_id)

        # Verify it was registered
        get_resp = client.get(f"/handoff/agents/{agent_id}/capabilities")
        assert len(get_resp.json()["capabilities"]) == 1

    def test_register_capability_update(self, client):
        """Test updating an existing capability."""
        agent_id = uuid4()

        # Register initial capability
        client.post(
            f"/handoff/agents/{agent_id}/capabilities",
            json={
                "name": "test_cap",
                "proficiency_level": 0.5,
            },
        )

        # Update with higher proficiency
        response = client.post(
            f"/handoff/agents/{agent_id}/capabilities",
            json={
                "name": "test_cap",
                "proficiency_level": 0.9,
            },
        )

        assert response.status_code == 201
        assert "updated" in response.json()["message"]

        # Verify update
        get_resp = client.get(f"/handoff/agents/{agent_id}/capabilities")
        caps = get_resp.json()["capabilities"]
        assert len(caps) == 1
        assert caps[0]["proficiency_level"] == 0.9

    def test_remove_capability(self, client):
        """Test removing a capability."""
        agent_id = uuid4()

        # Register capability
        client.post(
            f"/handoff/agents/{agent_id}/capabilities",
            json={"name": "test_cap"},
        )

        # Remove it
        response = client.delete(
            f"/handoff/agents/{agent_id}/capabilities/test_cap"
        )
        assert response.status_code == 204

        # Verify removal
        get_resp = client.get(f"/handoff/agents/{agent_id}/capabilities")
        assert len(get_resp.json()["capabilities"]) == 0

    def test_remove_nonexistent_capability(self, client):
        """Test removing non-existent capability (should succeed silently)."""
        response = client.delete(
            f"/handoff/agents/{uuid4()}/capabilities/nonexistent"
        )
        assert response.status_code == 204


# =============================================================================
# Integration Tests
# =============================================================================

class TestHandoffAPIIntegration:
    """Integration tests for handoff API workflow."""

    def test_complete_handoff_workflow(self, client, sample_agents):
        """Test complete handoff workflow."""
        agent1, agent2, agent3 = sample_agents
        source_id = uuid4()

        # 1. Find matching agent
        match_resp = client.post(
            "/handoff/capability/match",
            json={
                "requirements": [
                    {"capability_name": "data_analysis", "min_proficiency": 0.8}
                ],
            },
        )
        assert match_resp.status_code == 200
        best_match = match_resp.json()["best_match"]
        target_id = best_match["agent_id"]

        # 2. Trigger handoff
        trigger_resp = client.post(
            "/handoff/trigger",
            json={
                "source_agent_id": str(source_id),
                "target_agent_id": target_id,
                "context": {"task": "analyze_data"},
                "reason": "Need specialized analysis",
            },
        )
        assert trigger_resp.status_code == 201
        handoff_id = trigger_resp.json()["handoff_id"]

        # 3. Check status
        status_resp = client.get(f"/handoff/{handoff_id}/status")
        assert status_resp.status_code == 200
        assert status_resp.json()["status"] == "initiated"

        # 4. Check history
        history_resp = client.get(
            f"/handoff/history?source_agent_id={source_id}"
        )
        assert history_resp.status_code == 200
        assert history_resp.json()["total"] == 1

    def test_handoff_auto_match_workflow(self, client, sample_agents):
        """Test handoff with automatic agent matching."""
        agent1, agent2, agent3 = sample_agents
        source_id = uuid4()

        # Trigger handoff with auto-match
        trigger_resp = client.post(
            "/handoff/trigger",
            json={
                "source_agent_id": str(source_id),
                "required_capabilities": ["data_analysis"],
            },
        )

        assert trigger_resp.status_code == 201
        data = trigger_resp.json()

        # Should match to agent1 (highest proficiency)
        assert data["target_agent_id"] == str(agent1)

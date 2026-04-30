# =============================================================================
# IPA Platform - Agent API Unit Tests
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# Tests for Agent API endpoints:
#   - POST /api/v1/agents/ - Create agent
#   - GET /api/v1/agents/ - List agents
#   - GET /api/v1/agents/{id} - Get agent
#   - PUT /api/v1/agents/{id} - Update agent
#   - DELETE /api/v1/agents/{id} - Delete agent
#   - POST /api/v1/agents/{id}/run - Run agent
# =============================================================================

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from main import app
from src.domain.agents.schemas import (
    AgentCreateRequest,
    AgentUpdateRequest,
    AgentResponse,
    AgentRunRequest,
    AgentRunResponse,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_agent_id():
    """Generate a sample agent ID."""
    return uuid4()


@pytest.fixture
def sample_agent_data():
    """Create sample agent data."""
    return {
        "name": "test-agent",
        "description": "A test agent",
        "instructions": "You are a helpful test assistant.",
        "category": "testing",
        "tools": ["search", "calculator"],
        "model_config_data": {"temperature": 0.7},
        "max_iterations": 10,
    }


@pytest.fixture
def mock_agent(sample_agent_id):
    """Create a mock Agent ORM object."""
    agent = MagicMock()
    agent.id = sample_agent_id
    agent.name = "test-agent"
    agent.description = "A test agent"
    agent.instructions = "You are a helpful test assistant."
    agent.category = "testing"
    agent.tools = ["search", "calculator"]
    agent.model_config = {"temperature": 0.7}
    agent.max_iterations = 10
    agent.status = "active"
    agent.version = 1
    agent.created_at = datetime.utcnow()
    agent.updated_at = datetime.utcnow()
    return agent


# =============================================================================
# Schema Tests
# =============================================================================


class TestAgentSchemas:
    """Tests for Agent Pydantic schemas."""

    def test_create_request_valid(self, sample_agent_data):
        """Test valid AgentCreateRequest."""
        request = AgentCreateRequest(**sample_agent_data)

        assert request.name == "test-agent"
        assert request.instructions == "You are a helpful test assistant."
        assert len(request.tools) == 2

    def test_create_request_minimal(self):
        """Test minimal AgentCreateRequest (only required fields)."""
        request = AgentCreateRequest(
            name="minimal-agent",
            instructions="Be helpful.",
        )

        assert request.name == "minimal-agent"
        assert request.tools == []
        assert request.max_iterations == 10  # default

    def test_create_request_invalid_empty_name(self):
        """Test AgentCreateRequest rejects empty name."""
        with pytest.raises(ValueError):
            AgentCreateRequest(
                name="",
                instructions="Be helpful.",
            )

    def test_update_request_partial(self):
        """Test AgentUpdateRequest with partial data."""
        request = AgentUpdateRequest(
            description="Updated description",
            status="inactive",
        )

        assert request.description == "Updated description"
        assert request.status == "inactive"
        assert request.name is None
        assert request.instructions is None

    def test_update_request_invalid_status(self):
        """Test AgentUpdateRequest rejects invalid status."""
        with pytest.raises(ValueError):
            AgentUpdateRequest(status="invalid_status")

    def test_run_request_valid(self):
        """Test valid AgentRunRequest."""
        request = AgentRunRequest(
            message="Hello, can you help me?",
            context={"user_id": "123"},
        )

        assert request.message == "Hello, can you help me?"
        assert request.context["user_id"] == "123"

    def test_run_request_empty_message_rejected(self):
        """Test AgentRunRequest rejects empty message."""
        with pytest.raises(ValueError):
            AgentRunRequest(message="")


# =============================================================================
# Create Agent Tests
# =============================================================================


class TestCreateAgentEndpoint:
    """Tests for POST /api/v1/agents/."""

    def test_create_agent_success(self, client, sample_agent_data, sample_agent_id):
        """Test successful agent creation."""
        from src.api.v1.agents.routes import get_agent_repository

        mock_repo = AsyncMock()
        mock_repo.get_by_name.return_value = None  # No duplicate

        # Create mock agent response
        mock_agent = MagicMock()
        mock_agent.id = sample_agent_id
        mock_agent.name = sample_agent_data["name"]
        mock_agent.description = sample_agent_data["description"]
        mock_agent.instructions = sample_agent_data["instructions"]
        mock_agent.category = sample_agent_data["category"]
        mock_agent.tools = sample_agent_data["tools"]
        mock_agent.model_config = sample_agent_data["model_config_data"]
        mock_agent.max_iterations = sample_agent_data["max_iterations"]
        mock_agent.status = "active"
        mock_agent.version = 1
        mock_agent.created_at = datetime.utcnow()
        mock_agent.updated_at = datetime.utcnow()

        mock_repo.create.return_value = mock_agent

        app.dependency_overrides[get_agent_repository] = lambda: mock_repo

        response = client.post("/api/v1/agents/", json=sample_agent_data)

        app.dependency_overrides.clear()

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_agent_data["name"]
        assert data["status"] == "active"

    def test_create_agent_duplicate_name(self, client, sample_agent_data, mock_agent):
        """Test agent creation with duplicate name returns 409."""
        from src.api.v1.agents.routes import get_agent_repository

        mock_repo = AsyncMock()
        mock_repo.get_by_name.return_value = mock_agent  # Duplicate exists

        app.dependency_overrides[get_agent_repository] = lambda: mock_repo

        response = client.post("/api/v1/agents/", json=sample_agent_data)

        app.dependency_overrides.clear()

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_create_agent_validation_error(self, client):
        """Test agent creation with invalid data returns 422."""
        invalid_data = {
            "name": "",  # Empty name should fail
            "instructions": "Be helpful.",
        }

        response = client.post("/api/v1/agents/", json=invalid_data)

        assert response.status_code == 422


# =============================================================================
# List Agents Tests
# =============================================================================


class TestListAgentsEndpoint:
    """Tests for GET /api/v1/agents/."""

    def test_list_agents_empty(self, client):
        """Test listing agents when none exist."""
        from src.api.v1.agents.routes import get_agent_repository

        mock_repo = AsyncMock()
        mock_repo.list.return_value = ([], 0)

        app.dependency_overrides[get_agent_repository] = lambda: mock_repo

        response = client.get("/api/v1/agents/")

        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_agents_with_data(self, client, mock_agent):
        """Test listing agents with data."""
        from src.api.v1.agents.routes import get_agent_repository

        mock_repo = AsyncMock()
        mock_repo.list.return_value = ([mock_agent], 1)

        app.dependency_overrides[get_agent_repository] = lambda: mock_repo

        response = client.get("/api/v1/agents/")

        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["total"] == 1

    def test_list_agents_pagination(self, client):
        """Test listing agents with pagination."""
        from src.api.v1.agents.routes import get_agent_repository

        mock_repo = AsyncMock()
        mock_repo.list.return_value = ([], 50)  # 50 total but empty page

        app.dependency_overrides[get_agent_repository] = lambda: mock_repo

        response = client.get("/api/v1/agents/?page=3&page_size=10")

        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 3
        assert data["page_size"] == 10

    def test_list_agents_with_search(self, client, mock_agent):
        """Test listing agents with search query."""
        from src.api.v1.agents.routes import get_agent_repository

        mock_repo = AsyncMock()
        mock_repo.search.return_value = ([mock_agent], 1)

        app.dependency_overrides[get_agent_repository] = lambda: mock_repo

        response = client.get("/api/v1/agents/?search=test")

        app.dependency_overrides.clear()

        assert response.status_code == 200
        mock_repo.search.assert_called_once()


# =============================================================================
# Get Agent Tests
# =============================================================================


class TestGetAgentEndpoint:
    """Tests for GET /api/v1/agents/{agent_id}."""

    def test_get_agent_success(self, client, mock_agent, sample_agent_id):
        """Test successful agent retrieval."""
        from src.api.v1.agents.routes import get_agent_repository

        mock_repo = AsyncMock()
        mock_repo.get.return_value = mock_agent

        app.dependency_overrides[get_agent_repository] = lambda: mock_repo

        response = client.get(f"/api/v1/agents/{sample_agent_id}")

        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == mock_agent.name

    def test_get_agent_not_found(self, client, sample_agent_id):
        """Test getting non-existent agent returns 404."""
        from src.api.v1.agents.routes import get_agent_repository

        mock_repo = AsyncMock()
        mock_repo.get.return_value = None

        app.dependency_overrides[get_agent_repository] = lambda: mock_repo

        response = client.get(f"/api/v1/agents/{sample_agent_id}")

        app.dependency_overrides.clear()

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_agent_invalid_uuid(self, client):
        """Test getting agent with invalid UUID returns 422."""
        response = client.get("/api/v1/agents/invalid-uuid")

        assert response.status_code == 422


# =============================================================================
# Update Agent Tests
# =============================================================================


class TestUpdateAgentEndpoint:
    """Tests for PUT /api/v1/agents/{agent_id}."""

    def test_update_agent_success(self, client, mock_agent, sample_agent_id):
        """Test successful agent update."""
        from src.api.v1.agents.routes import get_agent_repository

        mock_repo = AsyncMock()
        mock_repo.get.return_value = mock_agent
        mock_repo.get_by_name.return_value = None
        mock_repo.update.return_value = mock_agent
        mock_repo.increment_version.return_value = None

        app.dependency_overrides[get_agent_repository] = lambda: mock_repo

        update_data = {"description": "Updated description"}
        response = client.put(f"/api/v1/agents/{sample_agent_id}", json=update_data)

        app.dependency_overrides.clear()

        assert response.status_code == 200

    def test_update_agent_not_found(self, client, sample_agent_id):
        """Test updating non-existent agent returns 404."""
        from src.api.v1.agents.routes import get_agent_repository

        mock_repo = AsyncMock()
        mock_repo.get.return_value = None

        app.dependency_overrides[get_agent_repository] = lambda: mock_repo

        update_data = {"description": "Updated"}
        response = client.put(f"/api/v1/agents/{sample_agent_id}", json=update_data)

        app.dependency_overrides.clear()

        assert response.status_code == 404

    def test_update_agent_duplicate_name(self, client, mock_agent, sample_agent_id):
        """Test updating agent to existing name returns 409."""
        from src.api.v1.agents.routes import get_agent_repository

        mock_repo = AsyncMock()
        mock_repo.get.return_value = mock_agent

        # Another agent with the target name exists
        other_agent = MagicMock()
        other_agent.id = uuid4()
        other_agent.name = "other-name"
        mock_repo.get_by_name.return_value = other_agent

        app.dependency_overrides[get_agent_repository] = lambda: mock_repo

        update_data = {"name": "other-name"}
        response = client.put(f"/api/v1/agents/{sample_agent_id}", json=update_data)

        app.dependency_overrides.clear()

        assert response.status_code == 409


# =============================================================================
# Delete Agent Tests
# =============================================================================


class TestDeleteAgentEndpoint:
    """Tests for DELETE /api/v1/agents/{agent_id}."""

    def test_delete_agent_success(self, client, sample_agent_id):
        """Test successful agent deletion."""
        from src.api.v1.agents.routes import get_agent_repository

        mock_repo = AsyncMock()
        mock_repo.delete.return_value = True

        app.dependency_overrides[get_agent_repository] = lambda: mock_repo

        response = client.delete(f"/api/v1/agents/{sample_agent_id}")

        app.dependency_overrides.clear()

        assert response.status_code == 204

    def test_delete_agent_not_found(self, client, sample_agent_id):
        """Test deleting non-existent agent returns 404."""
        from src.api.v1.agents.routes import get_agent_repository

        mock_repo = AsyncMock()
        mock_repo.delete.return_value = False

        app.dependency_overrides[get_agent_repository] = lambda: mock_repo

        response = client.delete(f"/api/v1/agents/{sample_agent_id}")

        app.dependency_overrides.clear()

        assert response.status_code == 404


# =============================================================================
# Run Agent Tests
# =============================================================================


class TestRunAgentEndpoint:
    """Tests for POST /api/v1/agents/{agent_id}/run."""

    def test_run_agent_success(self, client, mock_agent, sample_agent_id):
        """Test successful agent execution."""
        from src.api.v1.agents.routes import get_agent_repository, get_service
        from src.domain.agents.service import AgentExecutionResult

        mock_repo = AsyncMock()
        mock_repo.get.return_value = mock_agent

        mock_service = AsyncMock()
        mock_service.is_initialized = True
        mock_service.run_agent_with_config.return_value = AgentExecutionResult(
            text="Hello! How can I help you?",
            llm_calls=1,
            llm_tokens=100,
            llm_cost=0.001,
            tool_calls=[],
        )

        app.dependency_overrides[get_agent_repository] = lambda: mock_repo
        app.dependency_overrides[get_service] = lambda: mock_service

        run_data = {"message": "Hello!"}
        response = client.post(f"/api/v1/agents/{sample_agent_id}/run", json=run_data)

        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert "Hello" in data["result"]
        assert data["stats"]["llm_calls"] == 1

    def test_run_agent_not_found(self, client, sample_agent_id):
        """Test running non-existent agent returns 404."""
        from src.api.v1.agents.routes import get_agent_repository, get_service

        mock_repo = AsyncMock()
        mock_repo.get.return_value = None

        mock_service = AsyncMock()

        app.dependency_overrides[get_agent_repository] = lambda: mock_repo
        app.dependency_overrides[get_service] = lambda: mock_service

        run_data = {"message": "Hello!"}
        response = client.post(f"/api/v1/agents/{sample_agent_id}/run", json=run_data)

        app.dependency_overrides.clear()

        assert response.status_code == 404

    def test_run_agent_inactive(self, client, mock_agent, sample_agent_id):
        """Test running inactive agent returns 400."""
        from src.api.v1.agents.routes import get_agent_repository, get_service

        # Set agent status to inactive
        mock_agent.status = "inactive"

        mock_repo = AsyncMock()
        mock_repo.get.return_value = mock_agent

        mock_service = AsyncMock()

        app.dependency_overrides[get_agent_repository] = lambda: mock_repo
        app.dependency_overrides[get_service] = lambda: mock_service

        run_data = {"message": "Hello!"}
        response = client.post(f"/api/v1/agents/{sample_agent_id}/run", json=run_data)

        app.dependency_overrides.clear()

        assert response.status_code == 400
        assert "not active" in response.json()["detail"]

    def test_run_agent_with_context(self, client, mock_agent, sample_agent_id):
        """Test running agent with context."""
        from src.api.v1.agents.routes import get_agent_repository, get_service
        from src.domain.agents.service import AgentExecutionResult

        mock_repo = AsyncMock()
        mock_repo.get.return_value = mock_agent

        mock_service = AsyncMock()
        mock_service.is_initialized = True
        mock_service.run_agent_with_config.return_value = AgentExecutionResult(
            text="Got your context!",
            llm_calls=1,
            llm_tokens=50,
            llm_cost=0.0005,
        )

        app.dependency_overrides[get_agent_repository] = lambda: mock_repo
        app.dependency_overrides[get_service] = lambda: mock_service

        run_data = {
            "message": "Help me!",
            "context": {"user_id": "123", "priority": "high"},
        }
        response = client.post(f"/api/v1/agents/{sample_agent_id}/run", json=run_data)

        app.dependency_overrides.clear()

        assert response.status_code == 200
        # Verify context was passed to service
        call_args = mock_service.run_agent_with_config.call_args
        assert call_args.kwargs["context"]["user_id"] == "123"

    def test_run_agent_service_error(self, client, mock_agent, sample_agent_id):
        """Test agent execution error returns 500."""
        from src.api.v1.agents.routes import get_agent_repository, get_service

        mock_repo = AsyncMock()
        mock_repo.get.return_value = mock_agent

        mock_service = AsyncMock()
        mock_service.is_initialized = True
        mock_service.run_agent_with_config.side_effect = RuntimeError("LLM error")

        app.dependency_overrides[get_agent_repository] = lambda: mock_repo
        app.dependency_overrides[get_service] = lambda: mock_service

        run_data = {"message": "Hello!"}
        response = client.post(f"/api/v1/agents/{sample_agent_id}/run", json=run_data)

        app.dependency_overrides.clear()

        assert response.status_code == 500
        assert "execution failed" in response.json()["detail"]


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_agent_name_max_length(self, client):
        """Test agent name at maximum length."""
        from src.api.v1.agents.routes import get_agent_repository

        mock_repo = AsyncMock()
        mock_repo.get_by_name.return_value = None

        mock_agent = MagicMock()
        mock_agent.id = uuid4()
        mock_agent.name = "a" * 255
        mock_agent.description = None
        mock_agent.instructions = "Test"
        mock_agent.category = None
        mock_agent.tools = []
        mock_agent.model_config = {}
        mock_agent.max_iterations = 10
        mock_agent.status = "active"
        mock_agent.version = 1
        mock_agent.created_at = datetime.utcnow()
        mock_agent.updated_at = datetime.utcnow()

        mock_repo.create.return_value = mock_agent

        app.dependency_overrides[get_agent_repository] = lambda: mock_repo

        agent_data = {
            "name": "a" * 255,  # Max length
            "instructions": "Test",
        }
        response = client.post("/api/v1/agents/", json=agent_data)

        app.dependency_overrides.clear()

        assert response.status_code == 201

    def test_max_iterations_boundary(self, client):
        """Test max_iterations at boundaries."""
        from src.api.v1.agents.routes import get_agent_repository

        mock_repo = AsyncMock()
        mock_repo.get_by_name.return_value = None

        mock_agent = MagicMock()
        mock_agent.id = uuid4()
        mock_agent.name = "test"
        mock_agent.description = None
        mock_agent.instructions = "Test"
        mock_agent.category = None
        mock_agent.tools = []
        mock_agent.model_config = {}
        mock_agent.max_iterations = 100
        mock_agent.status = "active"
        mock_agent.version = 1
        mock_agent.created_at = datetime.utcnow()
        mock_agent.updated_at = datetime.utcnow()

        mock_repo.create.return_value = mock_agent

        app.dependency_overrides[get_agent_repository] = lambda: mock_repo

        # Test max value (100)
        agent_data = {
            "name": "test",
            "instructions": "Test",
            "max_iterations": 100,
        }
        response = client.post("/api/v1/agents/", json=agent_data)

        app.dependency_overrides.clear()

        assert response.status_code == 201

    def test_max_iterations_exceeds_boundary(self, client):
        """Test max_iterations exceeding maximum returns 422."""
        agent_data = {
            "name": "test",
            "instructions": "Test",
            "max_iterations": 101,  # Exceeds max of 100
        }
        response = client.post("/api/v1/agents/", json=agent_data)

        assert response.status_code == 422

    def test_special_characters_in_name(self, client):
        """Test agent name with special characters."""
        from src.api.v1.agents.routes import get_agent_repository

        mock_repo = AsyncMock()
        mock_repo.get_by_name.return_value = None

        mock_agent = MagicMock()
        mock_agent.id = uuid4()
        mock_agent.name = "test-agent_v2.0"
        mock_agent.description = None
        mock_agent.instructions = "Test"
        mock_agent.category = None
        mock_agent.tools = []
        mock_agent.model_config = {}
        mock_agent.max_iterations = 10
        mock_agent.status = "active"
        mock_agent.version = 1
        mock_agent.created_at = datetime.utcnow()
        mock_agent.updated_at = datetime.utcnow()

        mock_repo.create.return_value = mock_agent

        app.dependency_overrides[get_agent_repository] = lambda: mock_repo

        agent_data = {
            "name": "test-agent_v2.0",
            "instructions": "Test",
        }
        response = client.post("/api/v1/agents/", json=agent_data)

        app.dependency_overrides.clear()

        assert response.status_code == 201

    def test_unicode_in_instructions(self, client):
        """Test agent with unicode in instructions."""
        from src.api.v1.agents.routes import get_agent_repository

        mock_repo = AsyncMock()
        mock_repo.get_by_name.return_value = None

        mock_agent = MagicMock()
        mock_agent.id = uuid4()
        mock_agent.name = "unicode-agent"
        mock_agent.description = None
        mock_agent.instructions = "你是一個有幫助的助手 🤖"
        mock_agent.category = None
        mock_agent.tools = []
        mock_agent.model_config = {}
        mock_agent.max_iterations = 10
        mock_agent.status = "active"
        mock_agent.version = 1
        mock_agent.created_at = datetime.utcnow()
        mock_agent.updated_at = datetime.utcnow()

        mock_repo.create.return_value = mock_agent

        app.dependency_overrides[get_agent_repository] = lambda: mock_repo

        agent_data = {
            "name": "unicode-agent",
            "instructions": "你是一個有幫助的助手 🤖",
        }
        response = client.post("/api/v1/agents/", json=agent_data)

        app.dependency_overrides.clear()

        assert response.status_code == 201

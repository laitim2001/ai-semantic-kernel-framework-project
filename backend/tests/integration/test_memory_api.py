# =============================================================================
# IPA Platform - Memory API Integration Tests
# =============================================================================
# Sprint 90: S90-4 - Memory API 集成測試 (3 pts)
#
# Integration tests for Memory API endpoints.
# Uses mocking to isolate external dependencies (mem0, Redis, Qdrant).
# =============================================================================

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import status
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

# We need to mock before importing the app
import sys


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_memory_record():
    """Create a mock memory record."""
    from src.integrations.memory.types import (
        MemoryLayer,
        MemoryMetadata,
        MemoryRecord,
        MemoryType,
    )

    return MemoryRecord(
        id="mem_test_123",
        user_id="user_123",
        content="Test memory content",
        memory_type=MemoryType.CONVERSATION,
        layer=MemoryLayer.LONG_TERM,
        metadata=MemoryMetadata(
            source="test",
            importance=0.8,
            tags=["test", "integration"],
        ),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def mock_search_result(mock_memory_record):
    """Create a mock search result."""
    from src.integrations.memory.types import MemorySearchResult

    return MemorySearchResult(
        memory=mock_memory_record,
        score=0.95,
    )


@pytest.fixture
def mock_memory_manager(mock_memory_record, mock_search_result):
    """Create a mock UnifiedMemoryManager."""
    manager = AsyncMock()
    manager.initialize = AsyncMock()
    manager.add = AsyncMock(return_value=mock_memory_record)
    manager.search = AsyncMock(return_value=[mock_search_result])
    manager.get_user_memories = AsyncMock(return_value=[mock_memory_record])
    manager.get = AsyncMock(return_value=mock_memory_record)
    manager.delete = AsyncMock(return_value=True)
    manager.promote = AsyncMock(return_value=mock_memory_record)
    manager.get_context = AsyncMock(return_value=[mock_memory_record])

    # Health check attributes
    manager._mem0_client = MagicMock()
    manager._mem0_client._initialized = True
    manager._redis = AsyncMock()
    manager._redis.ping = AsyncMock()
    manager._embedding_service = MagicMock()
    manager._embedding_service._initialized = True
    manager.config = MagicMock()
    manager.config.qdrant_path = "/test/qdrant"
    manager.config.embedding_model = "text-embedding-3-small"

    return manager


@pytest.fixture
def app_with_mock_manager(mock_memory_manager):
    """Create FastAPI app with mocked memory manager."""
    from main import app
    from src.api.v1.memory.routes import get_memory_manager

    async def override_get_memory_manager():
        return mock_memory_manager

    app.dependency_overrides[get_memory_manager] = override_get_memory_manager
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def test_client(app_with_mock_manager):
    """Create a test client."""
    return TestClient(app_with_mock_manager)


# =============================================================================
# Add Memory Tests
# =============================================================================


class TestAddMemoryEndpoint:
    """Tests for POST /api/v1/memory/add endpoint."""

    def test_add_memory_success(self, test_client, mock_memory_manager):
        """Test successful memory addition."""
        response = test_client.post(
            "/api/v1/memory/add",
            json={
                "content": "User prefers dark mode",
                "user_id": "user_123",
                "memory_type": "user_preference",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "id" in data
        assert data["user_id"] == "user_123"
        assert data["memory_type"] == "conversation"  # From mock
        mock_memory_manager.add.assert_called_once()

    def test_add_memory_with_metadata(self, test_client, mock_memory_manager):
        """Test memory addition with metadata."""
        response = test_client.post(
            "/api/v1/memory/add",
            json={
                "content": "Important event resolution",
                "user_id": "user_123",
                "memory_type": "event_resolution",
                "metadata": {
                    "source": "event_handler",
                    "importance": 0.9,
                    "tags": ["critical", "resolved"],
                },
                "layer": "long_term",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        mock_memory_manager.add.assert_called_once()

    def test_add_memory_invalid_type(self, test_client):
        """Test memory addition with invalid type."""
        response = test_client.post(
            "/api/v1/memory/add",
            json={
                "content": "Test content",
                "user_id": "user_123",
                "memory_type": "invalid_type",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid memory type" in response.json()["detail"]

    def test_add_memory_missing_content(self, test_client):
        """Test memory addition without content."""
        response = test_client.post(
            "/api/v1/memory/add",
            json={
                "user_id": "user_123",
                "memory_type": "conversation",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# =============================================================================
# Search Memory Tests
# =============================================================================


class TestSearchMemoryEndpoint:
    """Tests for POST /api/v1/memory/search endpoint."""

    def test_search_memory_success(self, test_client, mock_memory_manager):
        """Test successful memory search."""
        response = test_client.post(
            "/api/v1/memory/search",
            json={
                "query": "user preferences",
                "user_id": "user_123",
                "limit": 10,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "results" in data
        assert "total" in data
        assert data["query"] == "user preferences"
        mock_memory_manager.search.assert_called_once()

    def test_search_memory_with_filters(self, test_client, mock_memory_manager):
        """Test memory search with filters."""
        response = test_client.post(
            "/api/v1/memory/search",
            json={
                "query": "dark mode",
                "user_id": "user_123",
                "memory_types": ["user_preference", "conversation"],
                "layers": ["long_term"],
                "min_importance": 0.5,
                "limit": 5,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        mock_memory_manager.search.assert_called_once()

    def test_search_memory_empty_query(self, test_client):
        """Test memory search with empty query."""
        response = test_client.post(
            "/api/v1/memory/search",
            json={
                "query": "",
                "user_id": "user_123",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# =============================================================================
# Get User Memories Tests
# =============================================================================


class TestGetUserMemoriesEndpoint:
    """Tests for GET /api/v1/memory/user/{user_id} endpoint."""

    def test_get_user_memories_success(self, test_client, mock_memory_manager):
        """Test getting all memories for a user."""
        response = test_client.get("/api/v1/memory/user/user_123")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "memories" in data
        assert "total" in data
        assert data["user_id"] == "user_123"
        mock_memory_manager.get_user_memories.assert_called_once()

    def test_get_user_memories_with_filters(self, test_client, mock_memory_manager):
        """Test getting user memories with filters."""
        response = test_client.get(
            "/api/v1/memory/user/user_123",
            params={
                "memory_types": "user_preference,conversation",
                "layers": "long_term",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        mock_memory_manager.get_user_memories.assert_called_once()


# =============================================================================
# Delete Memory Tests
# =============================================================================


class TestDeleteMemoryEndpoint:
    """Tests for DELETE /api/v1/memory/{memory_id} endpoint."""

    def test_delete_memory_success(self, test_client, mock_memory_manager):
        """Test successful memory deletion."""
        response = test_client.delete(
            "/api/v1/memory/mem_123",
            params={"user_id": "user_123"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["memory_id"] == "mem_123"
        mock_memory_manager.delete.assert_called_once()

    def test_delete_memory_not_found(self, test_client, mock_memory_manager):
        """Test deleting non-existent memory."""
        mock_memory_manager.delete = AsyncMock(return_value=False)

        response = test_client.delete(
            "/api/v1/memory/nonexistent",
            params={"user_id": "user_123"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_memory_with_layer(self, test_client, mock_memory_manager):
        """Test deleting memory from specific layer."""
        response = test_client.delete(
            "/api/v1/memory/mem_123",
            params={
                "user_id": "user_123",
                "layer": "long_term",
            },
        )

        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# Promote Memory Tests
# =============================================================================


class TestPromoteMemoryEndpoint:
    """Tests for POST /api/v1/memory/promote endpoint."""

    def test_promote_memory_success(self, test_client, mock_memory_manager):
        """Test successful memory promotion."""
        response = test_client.post(
            "/api/v1/memory/promote",
            json={
                "memory_id": "mem_123",
                "user_id": "user_123",
                "from_layer": "session",
                "to_layer": "long_term",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "id" in data
        mock_memory_manager.promote.assert_called_once()

    def test_promote_memory_not_found(self, test_client, mock_memory_manager):
        """Test promoting non-existent memory."""
        mock_memory_manager.promote = AsyncMock(return_value=None)

        response = test_client.post(
            "/api/v1/memory/promote",
            json={
                "memory_id": "nonexistent",
                "user_id": "user_123",
                "from_layer": "session",
                "to_layer": "long_term",
            },
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_promote_memory_invalid_layer(self, test_client):
        """Test promoting with invalid layer."""
        response = test_client.post(
            "/api/v1/memory/promote",
            json={
                "memory_id": "mem_123",
                "user_id": "user_123",
                "from_layer": "invalid",
                "to_layer": "long_term",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Context Memory Tests
# =============================================================================


class TestContextMemoryEndpoint:
    """Tests for POST /api/v1/memory/context endpoint."""

    def test_get_context_success(self, test_client, mock_memory_manager):
        """Test getting context memories."""
        response = test_client.post(
            "/api/v1/memory/context",
            json={
                "user_id": "user_123",
                "session_id": "session_456",
                "query": "current task context",
                "limit": 10,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "memories" in data
        mock_memory_manager.get_context.assert_called_once()

    def test_get_context_minimal(self, test_client, mock_memory_manager):
        """Test getting context with minimal parameters."""
        response = test_client.post(
            "/api/v1/memory/context",
            json={
                "user_id": "user_123",
            },
        )

        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# Health Check Tests
# =============================================================================


class TestHealthCheckEndpoint:
    """Tests for GET /api/v1/memory/health endpoint."""

    def test_health_check_healthy(self, test_client, mock_memory_manager):
        """Test health check when all components are healthy."""
        response = test_client.get("/api/v1/memory/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert "mem0_initialized" in data
        assert "redis_connected" in data
        assert "embedding_service" in data

    def test_health_check_degraded(self, test_client, mock_memory_manager):
        """Test health check when some components are unhealthy."""
        mock_memory_manager._mem0_client._initialized = False

        response = test_client.get("/api/v1/memory/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "degraded"


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling in Memory API."""

    def test_add_memory_server_error(self, test_client, mock_memory_manager):
        """Test server error handling in add_memory."""
        mock_memory_manager.add = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        response = test_client.post(
            "/api/v1/memory/add",
            json={
                "content": "Test content",
                "user_id": "user_123",
                "memory_type": "conversation",
            },
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to add memory" in response.json()["detail"]

    def test_search_memory_server_error(self, test_client, mock_memory_manager):
        """Test server error handling in search_memory."""
        mock_memory_manager.search = AsyncMock(
            side_effect=Exception("Search service unavailable")
        )

        response = test_client.post(
            "/api/v1/memory/search",
            json={
                "query": "test query",
                "user_id": "user_123",
            },
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to search memories" in response.json()["detail"]


# =============================================================================
# Validation Tests
# =============================================================================


class TestValidation:
    """Tests for request validation in Memory API."""

    def test_importance_out_of_range(self, test_client):
        """Test importance validation (0.0 to 1.0)."""
        response = test_client.post(
            "/api/v1/memory/search",
            json={
                "query": "test",
                "min_importance": 1.5,  # Invalid
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_limit_out_of_range(self, test_client):
        """Test limit validation (1 to 100)."""
        response = test_client.post(
            "/api/v1/memory/search",
            json={
                "query": "test",
                "limit": 500,  # Invalid
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_valid_memory_types(self, test_client, mock_memory_manager):
        """Test all valid memory types are accepted."""
        valid_types = [
            "event_resolution",
            "user_preference",
            "system_knowledge",
            "best_practice",
            "conversation",
            "feedback",
        ]

        for mem_type in valid_types:
            response = test_client.post(
                "/api/v1/memory/add",
                json={
                    "content": "Test content",
                    "user_id": "user_123",
                    "memory_type": mem_type,
                },
            )
            assert response.status_code == status.HTTP_201_CREATED, f"Failed for type: {mem_type}"

    def test_valid_memory_layers(self, test_client, mock_memory_manager):
        """Test all valid memory layers are accepted."""
        valid_layers = ["working", "session", "long_term"]

        for layer in valid_layers:
            response = test_client.post(
                "/api/v1/memory/add",
                json={
                    "content": "Test content",
                    "user_id": "user_123",
                    "memory_type": "conversation",
                    "layer": layer,
                },
            )
            assert response.status_code == status.HTTP_201_CREATED, f"Failed for layer: {layer}"

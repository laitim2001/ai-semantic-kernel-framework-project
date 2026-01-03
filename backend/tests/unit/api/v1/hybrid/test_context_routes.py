# =============================================================================
# IPA Platform - Hybrid Context API Unit Tests
# =============================================================================
# Sprint 53: Context Bridge & Sync
#
# Unit tests for hybrid context API routes:
#   - GET /hybrid/context/{session_id}
#   - GET /hybrid/context/{session_id}/status
#   - POST /hybrid/context/sync
#   - POST /hybrid/context/merge
#   - GET /hybrid/context
# =============================================================================

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import status
from fastapi.testclient import TestClient

from src.integrations.hybrid.context.models import (
    ClaudeContext,
    HybridContext,
    MAFContext,
    SyncDirection,
    SyncResult,
    SyncStatus,
    SyncStrategy,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_maf_context():
    """Create a mock MAF context."""
    return MAFContext(
        workflow_id="wf-123",
        workflow_name="Test Workflow",
        current_step=2,
        total_steps=5,
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def mock_claude_context():
    """Create a mock Claude context."""
    return ClaudeContext(
        session_id="sess-456",
        current_system_prompt="You are a helpful assistant.",
        context_variables={"user_name": "Test User"},
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def mock_hybrid_context(mock_maf_context, mock_claude_context):
    """Create a mock hybrid context."""
    return HybridContext(
        context_id="hybrid-789",
        maf=mock_maf_context,
        claude=mock_claude_context,
        primary_framework="maf",
        sync_status=SyncStatus.SYNCED,
        version=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        last_sync_at=datetime.utcnow(),
    )


@pytest.fixture
def mock_sync_result(mock_hybrid_context):
    """Create a mock sync result."""
    return SyncResult(
        success=True,
        direction=SyncDirection.BIDIRECTIONAL,
        strategy=SyncStrategy.MERGE,
        source_version=1,
        target_version=2,
        changes_applied=3,
        conflicts_resolved=0,
        conflicts=[],
        hybrid_context=mock_hybrid_context,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        duration_ms=150,
    )


@pytest.fixture
def mock_context_bridge(mock_hybrid_context):
    """Create a mock ContextBridge."""
    bridge = MagicMock()
    bridge.get_hybrid_context = AsyncMock(return_value=mock_hybrid_context)
    bridge.merge_contexts = AsyncMock(return_value=mock_hybrid_context)
    bridge._context_cache = {"hybrid-789": mock_hybrid_context}
    return bridge


@pytest.fixture
def mock_synchronizer(mock_sync_result):
    """Create a mock ContextSynchronizer."""
    synchronizer = MagicMock()
    synchronizer.sync = AsyncMock(return_value=mock_sync_result)
    return synchronizer


# =============================================================================
# Test: GET /hybrid/context/{session_id}
# =============================================================================


class TestGetHybridContext:
    """Tests for GET /hybrid/context/{session_id} endpoint."""

    @patch("src.api.v1.hybrid.context_routes.get_context_bridge")
    def test_get_hybrid_context_success(
        self, mock_get_bridge, mock_context_bridge, mock_hybrid_context
    ):
        """Test successful retrieval of hybrid context."""
        from src.api.v1.hybrid.context_routes import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        mock_get_bridge.return_value = mock_context_bridge

        response = client.get("/hybrid/context/sess-456")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["context_id"] == "hybrid-789"
        assert data["primary_framework"] == "maf"
        assert data["sync_status"] == "synced"

    @patch("src.api.v1.hybrid.context_routes.get_context_bridge")
    def test_get_hybrid_context_not_found(self, mock_get_bridge):
        """Test 404 when hybrid context not found."""
        from src.api.v1.hybrid.context_routes import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        mock_bridge = MagicMock()
        mock_bridge.get_hybrid_context = AsyncMock(return_value=None)
        mock_get_bridge.return_value = mock_bridge

        response = client.get("/hybrid/context/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()


# =============================================================================
# Test: GET /hybrid/context/{session_id}/status
# =============================================================================


class TestGetSyncStatus:
    """Tests for GET /hybrid/context/{session_id}/status endpoint."""

    @patch("src.api.v1.hybrid.context_routes.get_context_bridge")
    def test_get_sync_status_success(
        self, mock_get_bridge, mock_context_bridge, mock_hybrid_context
    ):
        """Test successful retrieval of sync status."""
        from src.api.v1.hybrid.context_routes import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        mock_get_bridge.return_value = mock_context_bridge

        response = client.get("/hybrid/context/sess-456/status")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["session_id"] == "sess-456"
        assert data["sync_status"] == "synced"
        assert data["is_synced"] is True
        assert data["has_conflict"] is False
        assert data["version"] == 1

    @patch("src.api.v1.hybrid.context_routes.get_context_bridge")
    def test_get_sync_status_not_found(self, mock_get_bridge):
        """Test 404 when context not found for status check."""
        from src.api.v1.hybrid.context_routes import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        mock_bridge = MagicMock()
        mock_bridge.get_hybrid_context = AsyncMock(return_value=None)
        mock_get_bridge.return_value = mock_bridge

        response = client.get("/hybrid/context/nonexistent/status")

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Test: POST /hybrid/context/sync
# =============================================================================


class TestTriggerSync:
    """Tests for POST /hybrid/context/sync endpoint."""

    @patch("src.api.v1.hybrid.context_routes.get_synchronizer")
    @patch("src.api.v1.hybrid.context_routes.get_context_bridge")
    def test_trigger_sync_success(
        self,
        mock_get_bridge,
        mock_get_sync,
        mock_context_bridge,
        mock_synchronizer,
        mock_sync_result,
    ):
        """Test successful sync trigger."""
        from src.api.v1.hybrid.context_routes import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        mock_get_bridge.return_value = mock_context_bridge
        mock_get_sync.return_value = mock_synchronizer

        response = client.post(
            "/hybrid/context/sync",
            json={
                "session_id": "sess-456",
                "strategy": "merge",
                "direction": "bidirectional",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["direction"] == "bidirectional"
        assert data["strategy"] == "merge"
        assert data["changes_applied"] == 3

    @patch("src.api.v1.hybrid.context_routes.get_synchronizer")
    @patch("src.api.v1.hybrid.context_routes.get_context_bridge")
    def test_trigger_sync_not_found(
        self, mock_get_bridge, mock_get_sync, mock_synchronizer
    ):
        """Test 404 when context not found for sync."""
        from src.api.v1.hybrid.context_routes import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        mock_bridge = MagicMock()
        mock_bridge.get_hybrid_context = AsyncMock(return_value=None)
        mock_get_bridge.return_value = mock_bridge
        mock_get_sync.return_value = mock_synchronizer

        response = client.post(
            "/hybrid/context/sync",
            json={"session_id": "nonexistent"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("src.api.v1.hybrid.context_routes.get_synchronizer")
    @patch("src.api.v1.hybrid.context_routes.get_context_bridge")
    def test_trigger_sync_invalid_strategy(
        self, mock_get_bridge, mock_get_sync, mock_context_bridge, mock_synchronizer
    ):
        """Test 400 when invalid sync strategy provided."""
        from src.api.v1.hybrid.context_routes import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        mock_get_bridge.return_value = mock_context_bridge
        mock_get_sync.return_value = mock_synchronizer

        response = client.post(
            "/hybrid/context/sync",
            json={
                "session_id": "sess-456",
                "strategy": "invalid_strategy",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "strategy" in response.json()["detail"].lower()

    @patch("src.api.v1.hybrid.context_routes.get_synchronizer")
    @patch("src.api.v1.hybrid.context_routes.get_context_bridge")
    def test_trigger_sync_invalid_direction(
        self, mock_get_bridge, mock_get_sync, mock_context_bridge, mock_synchronizer
    ):
        """Test 400 when invalid sync direction provided."""
        from src.api.v1.hybrid.context_routes import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        mock_get_bridge.return_value = mock_context_bridge
        mock_get_sync.return_value = mock_synchronizer

        response = client.post(
            "/hybrid/context/sync",
            json={
                "session_id": "sess-456",
                "direction": "invalid_direction",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "direction" in response.json()["detail"].lower()


# =============================================================================
# Test: POST /hybrid/context/merge
# =============================================================================


class TestMergeContexts:
    """Tests for POST /hybrid/context/merge endpoint."""

    @patch("src.api.v1.hybrid.context_routes.get_context_bridge")
    def test_merge_contexts_with_both_ids(
        self, mock_get_bridge, mock_context_bridge, mock_hybrid_context
    ):
        """Test merge with both MAF and Claude IDs."""
        from src.api.v1.hybrid.context_routes import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        mock_get_bridge.return_value = mock_context_bridge

        response = client.post(
            "/hybrid/context/merge",
            json={
                "maf_workflow_id": "wf-123",
                "claude_session_id": "sess-456",
                "primary_framework": "maf",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["context_id"] == "hybrid-789"
        assert data["primary_framework"] == "maf"

    @patch("src.api.v1.hybrid.context_routes.get_context_bridge")
    def test_merge_contexts_maf_only(
        self, mock_get_bridge, mock_context_bridge, mock_hybrid_context
    ):
        """Test merge with only MAF ID."""
        from src.api.v1.hybrid.context_routes import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        mock_get_bridge.return_value = mock_context_bridge

        response = client.post(
            "/hybrid/context/merge",
            json={
                "maf_workflow_id": "wf-123",
            },
        )

        assert response.status_code == status.HTTP_200_OK

    @patch("src.api.v1.hybrid.context_routes.get_context_bridge")
    def test_merge_contexts_claude_only(
        self, mock_get_bridge, mock_context_bridge, mock_hybrid_context
    ):
        """Test merge with only Claude ID."""
        from src.api.v1.hybrid.context_routes import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        mock_get_bridge.return_value = mock_context_bridge

        response = client.post(
            "/hybrid/context/merge",
            json={
                "claude_session_id": "sess-456",
                "primary_framework": "claude",
            },
        )

        assert response.status_code == status.HTTP_200_OK

    def test_merge_contexts_no_ids(self):
        """Test 400 when no IDs provided."""
        from src.api.v1.hybrid.context_routes import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.post(
            "/hybrid/context/merge",
            json={},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "must be provided" in response.json()["detail"].lower()


# =============================================================================
# Test: GET /hybrid/context
# =============================================================================


class TestListHybridContexts:
    """Tests for GET /hybrid/context endpoint."""

    @patch("src.api.v1.hybrid.context_routes.get_context_bridge")
    def test_list_hybrid_contexts_success(
        self, mock_get_bridge, mock_context_bridge, mock_hybrid_context
    ):
        """Test successful listing of hybrid contexts."""
        from src.api.v1.hybrid.context_routes import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        mock_get_bridge.return_value = mock_context_bridge

        response = client.get("/hybrid/context")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert data["total"] == 1

    @patch("src.api.v1.hybrid.context_routes.get_context_bridge")
    def test_list_hybrid_contexts_empty(self, mock_get_bridge):
        """Test listing when no contexts exist."""
        from src.api.v1.hybrid.context_routes import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        mock_bridge = MagicMock()
        mock_bridge._context_cache = {}
        mock_get_bridge.return_value = mock_bridge

        response = client.get("/hybrid/context")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"] == []
        assert data["total"] == 0

    @patch("src.api.v1.hybrid.context_routes.get_context_bridge")
    def test_list_hybrid_contexts_pagination(
        self, mock_get_bridge, mock_hybrid_context
    ):
        """Test pagination parameters."""
        from src.api.v1.hybrid.context_routes import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        # Create multiple contexts
        mock_bridge = MagicMock()
        mock_bridge._context_cache = {
            f"ctx-{i}": mock_hybrid_context for i in range(25)
        }
        mock_get_bridge.return_value = mock_bridge

        response = client.get("/hybrid/context?skip=5&limit=10")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) == 10
        assert data["total"] == 25
        assert data["page"] == 1  # (5 // 10) + 1 = 1
        assert data["page_size"] == 10


# =============================================================================
# Test: Response Schema Validation
# =============================================================================


class TestResponseSchemas:
    """Tests for response schema validation."""

    @patch("src.api.v1.hybrid.context_routes.get_context_bridge")
    def test_hybrid_context_response_has_required_fields(
        self, mock_get_bridge, mock_context_bridge
    ):
        """Test that HybridContextResponse has all required fields."""
        from src.api.v1.hybrid.context_routes import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        mock_get_bridge.return_value = mock_context_bridge

        response = client.get("/hybrid/context/sess-456")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Required fields
        required_fields = [
            "context_id",
            "primary_framework",
            "sync_status",
            "version",
            "created_at",
            "updated_at",
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    @patch("src.api.v1.hybrid.context_routes.get_synchronizer")
    @patch("src.api.v1.hybrid.context_routes.get_context_bridge")
    def test_sync_result_response_has_required_fields(
        self,
        mock_get_bridge,
        mock_get_sync,
        mock_context_bridge,
        mock_synchronizer,
    ):
        """Test that SyncResultResponse has all required fields."""
        from src.api.v1.hybrid.context_routes import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        mock_get_bridge.return_value = mock_context_bridge
        mock_get_sync.return_value = mock_synchronizer

        response = client.post(
            "/hybrid/context/sync",
            json={"session_id": "sess-456"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Required fields
        required_fields = [
            "success",
            "direction",
            "strategy",
            "source_version",
            "target_version",
            "changes_applied",
            "conflicts_resolved",
            "conflicts",
            "started_at",
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

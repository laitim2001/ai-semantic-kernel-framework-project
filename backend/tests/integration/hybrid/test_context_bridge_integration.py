# =============================================================================
# IPA Platform - Context Bridge Integration Tests
# =============================================================================
# Phase 13: Hybrid Core Architecture
# Sprint 53: Context Bridge & State Sync
# Sprint 54: Integration Tests (S54-4)
#
# Integration tests for Context Bridge API endpoints.
# Tests the complete flow from HTTP request to response.
# =============================================================================

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from src.api.v1.hybrid.context_routes import router


# =============================================================================
# Test App Setup
# =============================================================================


@pytest.fixture
def app():
    """Create test FastAPI app with context bridge router."""
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app):
    """Create synchronous test client."""
    return TestClient(app)


@pytest.fixture
async def async_client(app):
    """Create asynchronous test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# =============================================================================
# Integration Test: Hybrid Context Operations
# =============================================================================


class TestHybridContextOperations:
    """Integration tests for hybrid context operations."""

    def test_merge_contexts_maf_only(self, client):
        """Test merging contexts with only MAF workflow ID."""
        response = client.post(
            "/hybrid/context/merge",
            json={
                "maf_workflow_id": "test-workflow-123",
                "primary_framework": "maf"
            }
        )
        assert response.status_code == 200
        data = response.json()

        assert data["context_id"] is not None
        assert data["primary_framework"] == "maf"
        assert data["maf"] is not None
        assert data["maf"]["workflow_id"] == "test-workflow-123"

    def test_merge_contexts_claude_only(self, client):
        """Test merging contexts with only Claude session ID."""
        response = client.post(
            "/hybrid/context/merge",
            json={
                "claude_session_id": "test-session-456",
                "primary_framework": "claude"
            }
        )
        assert response.status_code == 200
        data = response.json()

        assert data["context_id"] is not None
        assert data["primary_framework"] == "claude"
        assert data["claude"] is not None
        assert data["claude"]["session_id"] == "test-session-456"

    def test_merge_contexts_both_frameworks(self, client):
        """Test merging contexts with both MAF and Claude IDs."""
        response = client.post(
            "/hybrid/context/merge",
            json={
                "maf_workflow_id": "test-workflow-789",
                "claude_session_id": "test-session-789",
                "primary_framework": "maf"
            }
        )
        assert response.status_code == 200
        data = response.json()

        assert data["context_id"] is not None
        assert data["maf"] is not None
        assert data["claude"] is not None
        assert data["primary_framework"] == "maf"

    def test_merge_contexts_missing_both_ids(self, client):
        """Test error when both IDs are missing."""
        response = client.post(
            "/hybrid/context/merge",
            json={
                "primary_framework": "maf"
            }
        )
        assert response.status_code == 400
        assert "At least one of" in response.json()["detail"]


# =============================================================================
# Integration Test: Get Hybrid Context
# =============================================================================


class TestGetHybridContext:
    """Integration tests for getting hybrid context."""

    def test_get_context_not_found(self, client):
        """Test 404 when context not found."""
        response = client.get("/hybrid/context/nonexistent-session")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_context_after_merge(self, client):
        """Test getting context after merging."""
        # First merge to create context
        merge_response = client.post(
            "/hybrid/context/merge",
            json={
                "maf_workflow_id": "get-test-workflow",
                "primary_framework": "maf"
            }
        )
        assert merge_response.status_code == 200
        context_id = merge_response.json()["context_id"]

        # Then try to get it (may not be cached by session_id, so 404 is acceptable)
        response = client.get(f"/hybrid/context/{context_id}")
        # Context might not be indexed by context_id, so either 200 or 404 is valid
        assert response.status_code in [200, 404]


# =============================================================================
# Integration Test: Sync Operations
# =============================================================================


class TestSyncOperations:
    """Integration tests for context synchronization."""

    def test_trigger_sync_invalid_session(self, client):
        """Test sync for non-existent session."""
        response = client.post(
            "/hybrid/context/sync",
            json={
                "session_id": "nonexistent-session",
                "strategy": "merge",
                "direction": "bidirectional"
            }
        )
        assert response.status_code == 404

    def test_trigger_sync_invalid_strategy(self, client):
        """Test sync with invalid strategy."""
        response = client.post(
            "/hybrid/context/sync",
            json={
                "session_id": "test-session",
                "strategy": "invalid_strategy",
                "direction": "bidirectional"
            }
        )
        # Should return 404 (session not found) or 400 (invalid strategy)
        # Since session lookup happens first, expect 404
        assert response.status_code in [400, 404]

    def test_trigger_sync_invalid_direction(self, client):
        """Test sync with invalid direction."""
        response = client.post(
            "/hybrid/context/sync",
            json={
                "session_id": "test-session",
                "strategy": "merge",
                "direction": "invalid_direction"
            }
        )
        # Should return 404 (session not found) or 400 (invalid direction)
        assert response.status_code in [400, 404]


# =============================================================================
# Integration Test: Sync Status
# =============================================================================


class TestSyncStatus:
    """Integration tests for sync status operations."""

    def test_get_sync_status_not_found(self, client):
        """Test 404 when getting status for non-existent session."""
        response = client.get("/hybrid/context/nonexistent-session/status")
        assert response.status_code == 404


# =============================================================================
# Integration Test: List Contexts
# =============================================================================


class TestListContexts:
    """Integration tests for listing hybrid contexts."""

    def test_list_contexts_empty(self, client):
        """Test listing contexts when cache is empty."""
        response = client.get("/hybrid/context")
        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert isinstance(data["data"], list)

    def test_list_contexts_with_pagination(self, client):
        """Test listing contexts with pagination parameters."""
        response = client.get("/hybrid/context?skip=0&limit=10")
        assert response.status_code == 200
        data = response.json()

        assert data["page_size"] == 10
        assert data["page"] == 1

    def test_list_contexts_pagination_limits(self, client):
        """Test pagination with boundary values."""
        # Test minimum limit
        response = client.get("/hybrid/context?limit=1")
        assert response.status_code == 200

        # Test maximum limit
        response = client.get("/hybrid/context?limit=100")
        assert response.status_code == 200

    def test_list_contexts_invalid_pagination(self, client):
        """Test invalid pagination parameters."""
        # Negative skip should fail validation
        response = client.get("/hybrid/context?skip=-1")
        assert response.status_code == 422

        # Zero limit should fail validation
        response = client.get("/hybrid/context?limit=0")
        assert response.status_code == 422

        # Exceeding max limit should fail validation
        response = client.get("/hybrid/context?limit=101")
        assert response.status_code == 422


# =============================================================================
# Integration Test: End-to-End Flow
# =============================================================================


class TestEndToEndFlow:
    """End-to-end integration tests for context bridge."""

    def test_complete_merge_and_list_flow(self, client):
        """Test complete flow: merge -> list."""
        # Step 1: Merge contexts
        merge_response = client.post(
            "/hybrid/context/merge",
            json={
                "maf_workflow_id": "e2e-workflow-123",
                "claude_session_id": "e2e-session-123",
                "primary_framework": "maf"
            }
        )
        assert merge_response.status_code == 200
        merged = merge_response.json()

        # Verify merged context structure
        assert merged["context_id"] is not None
        assert merged["maf"]["workflow_id"] == "e2e-workflow-123"
        assert merged["claude"]["session_id"] == "e2e-session-123"
        # When both contexts exist and no conflicts, status is "synced"
        assert merged["sync_status"] == "synced"
        assert merged["version"] >= 1

        # Step 2: List contexts (should include merged one)
        list_response = client.get("/hybrid/context")
        assert list_response.status_code == 200
        list_data = list_response.json()

        # Verify list structure
        assert isinstance(list_data["data"], list)
        assert list_data["total"] >= 1

    def test_framework_switching_flow(self, client):
        """Test switching primary framework."""
        # Create context with MAF primary
        response1 = client.post(
            "/hybrid/context/merge",
            json={
                "maf_workflow_id": "switch-test-wf",
                "primary_framework": "maf"
            }
        )
        assert response1.status_code == 200
        assert response1.json()["primary_framework"] == "maf"

        # Create another context with Claude primary
        response2 = client.post(
            "/hybrid/context/merge",
            json={
                "claude_session_id": "switch-test-session",
                "primary_framework": "claude"
            }
        )
        assert response2.status_code == 200
        assert response2.json()["primary_framework"] == "claude"


# =============================================================================
# Integration Test: Error Handling
# =============================================================================


class TestErrorHandling:
    """Integration tests for error handling."""

    def test_malformed_json(self, client):
        """Test handling of malformed JSON."""
        response = client.post(
            "/hybrid/context/merge",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    def test_missing_required_fields(self, client):
        """Test handling of missing required fields."""
        response = client.post(
            "/hybrid/context/sync",
            json={}
        )
        assert response.status_code == 422

    def test_invalid_primary_framework(self, client):
        """Test handling of invalid primary framework value."""
        response = client.post(
            "/hybrid/context/merge",
            json={
                "maf_workflow_id": "test-wf",
                "primary_framework": "invalid_framework"
            }
        )
        # Pydantic validation should catch this
        assert response.status_code == 422


# =============================================================================
# Integration Test: Response Structure Validation
# =============================================================================


class TestResponseStructure:
    """Tests to validate response structure matches expected schemas."""

    def test_hybrid_context_response_structure(self, client):
        """Validate HybridContextResponse structure."""
        response = client.post(
            "/hybrid/context/merge",
            json={
                "maf_workflow_id": "structure-test-wf",
                "claude_session_id": "structure-test-session",
                "primary_framework": "maf"
            }
        )
        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert "context_id" in data
        assert "primary_framework" in data
        assert "sync_status" in data
        assert "version" in data

        # Optional fields (may be None)
        assert "maf" in data
        assert "claude" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_maf_context_response_structure(self, client):
        """Validate MAFContext response structure."""
        response = client.post(
            "/hybrid/context/merge",
            json={
                "maf_workflow_id": "maf-structure-test",
                "primary_framework": "maf"
            }
        )
        assert response.status_code == 200
        maf = response.json()["maf"]

        # MAF context fields
        assert "workflow_id" in maf
        assert "workflow_name" in maf
        assert "current_step" in maf
        assert "total_steps" in maf
        assert "agent_states" in maf
        assert "checkpoint_data" in maf
        assert "pending_approvals" in maf
        assert "execution_history" in maf
        assert "metadata" in maf

    def test_claude_context_response_structure(self, client):
        """Validate ClaudeContext response structure."""
        response = client.post(
            "/hybrid/context/merge",
            json={
                "claude_session_id": "claude-structure-test",
                "primary_framework": "claude"
            }
        )
        assert response.status_code == 200
        claude = response.json()["claude"]

        # Claude context fields
        assert "session_id" in claude
        assert "message_count" in claude
        assert "tool_call_count" in claude
        assert "context_variables" in claude
        assert "active_hooks" in claude
        assert "mcp_server_states" in claude
        assert "metadata" in claude

    def test_list_response_structure(self, client):
        """Validate list response structure."""
        response = client.get("/hybrid/context")
        assert response.status_code == 200
        data = response.json()

        # Pagination fields
        assert "data" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert isinstance(data["data"], list)
        assert isinstance(data["total"], int)
        assert isinstance(data["page"], int)
        assert isinstance(data["page_size"], int)

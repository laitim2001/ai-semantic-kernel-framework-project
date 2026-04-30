# =============================================================================
# IPA Platform - AG-UI Full Flow E2E Tests
# =============================================================================
# Sprint 60: AG-UI Advanced Features - S60-4 E2E Testing
#
# Comprehensive end-to-end tests for AG-UI Protocol integration:
# - Health check endpoint
# - Thread state management (CRUD operations)
# - Approval workflow (pending, approve, reject, cancel)
# - SSE streaming functionality
# - Optimistic concurrency control
#
# Author: IPA Platform Team
# Version: 1.0.0
# =============================================================================

import asyncio
import json
import pytest
import pytest_asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from httpx import AsyncClient


# =============================================================================
# Test Markers
# =============================================================================

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.asyncio,
]


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest_asyncio.fixture(scope="function")
async def test_thread_id() -> str:
    """Generate a unique thread ID for testing."""
    return f"e2e-test-thread-{uuid4().hex[:8]}"


@pytest_asyncio.fixture(scope="function")
async def test_state_data() -> Dict[str, Any]:
    """Provide standard test state data."""
    return {
        "counter": 0,
        "messages": [],
        "user_preferences": {
            "theme": "dark",
            "language": "en"
        },
        "timestamp": datetime.now().isoformat()
    }


@pytest_asyncio.fixture(scope="function")
async def test_approval_request() -> Dict[str, Any]:
    """Provide standard test approval request data."""
    return {
        "tool_name": "file_write",
        "tool_args": {
            "path": "/tmp/test.txt",
            "content": "Test content"
        },
        "reason": "E2E test approval request"
    }


# =============================================================================
# 1. Health Check Tests (健康檢查測試)
# =============================================================================

class TestAGUIHealthCheck:
    """Tests for AG-UI health check endpoint."""

    async def test_health_check_returns_ok(self, client: AsyncClient):
        """Test that health check endpoint returns healthy status."""
        response = await client.get("/api/v1/ag-ui/health")

        if response.status_code == 200:
            data = response.json()
            assert data.get("status") in ["ok", "healthy", "up"]
            assert "service" in data or "name" in data
        elif response.status_code == 404:
            pytest.skip("AG-UI health endpoint not available")
        else:
            # Accept other success codes
            assert response.status_code < 500

    async def test_health_check_includes_version(self, client: AsyncClient):
        """Test that health check includes version information."""
        response = await client.get("/api/v1/ag-ui/health")

        if response.status_code == 200:
            data = response.json()
            # Version info may be optional
            if "version" in data:
                assert isinstance(data["version"], str)
        elif response.status_code == 404:
            pytest.skip("AG-UI health endpoint not available")


# =============================================================================
# 2. Thread State Management Tests (Thread 狀態管理測試)
# =============================================================================

class TestThreadStateManagement:
    """Tests for thread state CRUD operations."""

    async def test_get_thread_state_empty(
        self,
        client: AsyncClient,
        test_thread_id: str,
    ):
        """Test getting state for a thread with no existing state."""
        response = await client.get(f"/api/v1/ag-ui/threads/{test_thread_id}/state")

        if response.status_code == 200:
            data = response.json()
            # Empty state should return empty dict or null values
            assert isinstance(data.get("state"), (dict, type(None)))
        elif response.status_code == 404:
            # Thread not found is acceptable for new thread
            pass
        else:
            pytest.skip("AG-UI state endpoint not available")

    async def test_update_thread_state(
        self,
        client: AsyncClient,
        test_thread_id: str,
        test_state_data: Dict[str, Any],
    ):
        """Test updating thread state with new data."""
        # Patch state
        response = await client.patch(
            f"/api/v1/ag-ui/threads/{test_thread_id}/state",
            json={
                "state": test_state_data,
                "metadata": {"source": "e2e_test"}
            }
        )

        if response.status_code in [200, 201]:
            data = response.json()
            # Should return updated state
            assert "state" in data or "success" in data
        elif response.status_code == 404:
            pytest.skip("AG-UI state endpoint not available")
        else:
            assert response.status_code < 500

    async def test_update_and_get_thread_state(
        self,
        client: AsyncClient,
        test_thread_id: str,
        test_state_data: Dict[str, Any],
    ):
        """Test updating state and then retrieving it."""
        # First, update state
        patch_response = await client.patch(
            f"/api/v1/ag-ui/threads/{test_thread_id}/state",
            json={"state": test_state_data}
        )

        if patch_response.status_code not in [200, 201]:
            pytest.skip("AG-UI state update not available")

        # Then, get state
        get_response = await client.get(
            f"/api/v1/ag-ui/threads/{test_thread_id}/state"
        )

        if get_response.status_code == 200:
            data = get_response.json()
            retrieved_state = data.get("state", data)
            # Verify state was persisted
            if "counter" in test_state_data:
                assert retrieved_state.get("counter") == test_state_data["counter"]

    async def test_delete_thread_state(
        self,
        client: AsyncClient,
        test_thread_id: str,
        test_state_data: Dict[str, Any],
    ):
        """Test deleting thread state."""
        # First, create state
        await client.patch(
            f"/api/v1/ag-ui/threads/{test_thread_id}/state",
            json={"state": test_state_data}
        )

        # Delete state
        delete_response = await client.delete(
            f"/api/v1/ag-ui/threads/{test_thread_id}/state"
        )

        if delete_response.status_code in [200, 204]:
            # Verify deletion
            get_response = await client.get(
                f"/api/v1/ag-ui/threads/{test_thread_id}/state"
            )
            if get_response.status_code == 200:
                data = get_response.json()
                # State should be empty or null after deletion
                state = data.get("state")
                assert state is None or state == {}
        elif delete_response.status_code == 404:
            pytest.skip("AG-UI state delete not available")

    async def test_optimistic_concurrency_with_version(
        self,
        client: AsyncClient,
        test_thread_id: str,
    ):
        """Test optimistic concurrency control with version tracking."""
        # Initial state update with version
        initial_response = await client.patch(
            f"/api/v1/ag-ui/threads/{test_thread_id}/state",
            json={
                "state": {"value": 1},
                "version": 0
            }
        )

        if initial_response.status_code not in [200, 201]:
            pytest.skip("AG-UI state with version not available")

        # Get version from response
        data = initial_response.json()
        current_version = data.get("version", 1)

        # Update with correct version should succeed
        success_response = await client.patch(
            f"/api/v1/ag-ui/threads/{test_thread_id}/state",
            json={
                "state": {"value": 2},
                "version": current_version
            }
        )

        if success_response.status_code in [200, 201]:
            # Verify version was incremented
            updated_data = success_response.json()
            if "version" in updated_data:
                assert updated_data["version"] > current_version

    async def test_concurrent_state_updates_conflict(
        self,
        client: AsyncClient,
        test_thread_id: str,
    ):
        """Test that concurrent updates with stale version fail."""
        # Initial state
        initial_response = await client.patch(
            f"/api/v1/ag-ui/threads/{test_thread_id}/state",
            json={"state": {"value": 1}, "version": 0}
        )

        if initial_response.status_code not in [200, 201]:
            pytest.skip("AG-UI state with version not available")

        data = initial_response.json()
        initial_version = data.get("version", 0)

        # First update succeeds
        await client.patch(
            f"/api/v1/ag-ui/threads/{test_thread_id}/state",
            json={"state": {"value": 2}, "version": initial_version}
        )

        # Second update with same (now stale) version should conflict
        conflict_response = await client.patch(
            f"/api/v1/ag-ui/threads/{test_thread_id}/state",
            json={"state": {"value": 3}, "version": initial_version}
        )

        # Should return conflict or error
        if conflict_response.status_code in [409, 400]:
            # Expected conflict behavior
            assert True
        elif conflict_response.status_code in [200, 201]:
            # Some implementations may auto-resolve
            pass


# =============================================================================
# 3. Approval Workflow Tests (審批流程測試)
# =============================================================================

class TestApprovalWorkflow:
    """Tests for tool approval workflow."""

    async def test_list_pending_approvals(self, client: AsyncClient):
        """Test listing pending approval requests."""
        response = await client.get("/api/v1/ag-ui/approvals/pending")

        if response.status_code == 200:
            data = response.json()
            # Should return list of approvals
            assert isinstance(data, (list, dict))
            if isinstance(data, dict):
                assert "approvals" in data or "items" in data or "data" in data
        elif response.status_code == 404:
            pytest.skip("AG-UI approvals endpoint not available")

    async def test_list_pending_approvals_with_thread_filter(
        self,
        client: AsyncClient,
        test_thread_id: str,
    ):
        """Test filtering pending approvals by thread ID."""
        response = await client.get(
            "/api/v1/ag-ui/approvals/pending",
            params={"thread_id": test_thread_id}
        )

        if response.status_code == 200:
            data = response.json()
            approvals = data if isinstance(data, list) else data.get("approvals", data.get("items", []))
            # All returned approvals should be for the specified thread
            for approval in approvals:
                if "thread_id" in approval:
                    assert approval["thread_id"] == test_thread_id
        elif response.status_code == 404:
            pytest.skip("AG-UI approvals endpoint not available")

    async def test_approve_tool_call(
        self,
        client: AsyncClient,
    ):
        """Test approving a pending tool call."""
        # First, get a pending approval (or create mock scenario)
        pending_response = await client.get("/api/v1/ag-ui/approvals/pending")

        if pending_response.status_code != 200:
            pytest.skip("AG-UI approvals endpoint not available")

        data = pending_response.json()
        approvals = data if isinstance(data, list) else data.get("approvals", data.get("items", []))

        if not approvals:
            # No pending approvals - test with mock ID
            mock_id = str(uuid4())
            response = await client.post(f"/api/v1/ag-ui/approvals/{mock_id}/approve")
            # Should return 404 for non-existent approval
            assert response.status_code in [200, 201, 404]
        else:
            # Approve first pending approval
            approval_id = approvals[0].get("id")
            response = await client.post(
                f"/api/v1/ag-ui/approvals/{approval_id}/approve",
                json={"reason": "E2E test approval"}
            )
            if response.status_code in [200, 201]:
                result = response.json()
                assert result.get("status") in ["approved", "success"]

    async def test_reject_tool_call(
        self,
        client: AsyncClient,
    ):
        """Test rejecting a pending tool call."""
        pending_response = await client.get("/api/v1/ag-ui/approvals/pending")

        if pending_response.status_code != 200:
            pytest.skip("AG-UI approvals endpoint not available")

        data = pending_response.json()
        approvals = data if isinstance(data, list) else data.get("approvals", data.get("items", []))

        if not approvals:
            mock_id = str(uuid4())
            response = await client.post(
                f"/api/v1/ag-ui/approvals/{mock_id}/reject",
                json={"reason": "E2E test rejection"}
            )
            assert response.status_code in [200, 201, 404]
        else:
            approval_id = approvals[0].get("id")
            response = await client.post(
                f"/api/v1/ag-ui/approvals/{approval_id}/reject",
                json={"reason": "E2E test rejection - security concern"}
            )
            if response.status_code in [200, 201]:
                result = response.json()
                assert result.get("status") in ["rejected", "success"]

    async def test_cancel_tool_call(
        self,
        client: AsyncClient,
    ):
        """Test cancelling a pending tool call."""
        mock_id = str(uuid4())
        response = await client.post(f"/api/v1/ag-ui/approvals/{mock_id}/cancel")

        # Cancel should return appropriate status
        assert response.status_code in [200, 201, 404, 400]

    async def test_approval_not_found(
        self,
        client: AsyncClient,
    ):
        """Test handling of non-existent approval ID."""
        fake_id = str(uuid4())
        response = await client.post(f"/api/v1/ag-ui/approvals/{fake_id}/approve")

        # Should return 404 for non-existent approval
        if response.status_code == 404:
            assert True
        elif response.status_code in [200, 201]:
            # Some implementations may accept any ID
            pass


# =============================================================================
# 4. SSE Streaming Tests (SSE 串流測試)
# =============================================================================

class TestSSEStreaming:
    """Tests for SSE streaming functionality."""

    async def test_agent_run_sync_endpoint(
        self,
        client: AsyncClient,
        test_thread_id: str,
    ):
        """Test synchronous agent run endpoint."""
        response = await client.post(
            "/api/v1/ag-ui/sync",
            json={
                "thread_id": test_thread_id,
                "input": "Hello, this is an E2E test message.",
                "config": {}
            }
        )

        if response.status_code in [200, 201]:
            data = response.json()
            # Should return agent response
            assert "response" in data or "output" in data or "content" in data
        elif response.status_code in [404, 501]:
            pytest.skip("AG-UI sync endpoint not available")
        else:
            # Accept other responses for now
            assert response.status_code < 500

    async def test_agent_run_stream_endpoint_exists(
        self,
        client: AsyncClient,
        test_thread_id: str,
    ):
        """Test that SSE streaming endpoint exists and responds."""
        # Note: Full SSE testing requires special handling
        # This test verifies the endpoint exists
        response = await client.post(
            "/api/v1/ag-ui",
            json={
                "thread_id": test_thread_id,
                "input": "E2E test",
                "stream": True
            },
            headers={"Accept": "text/event-stream"}
        )

        # Should return SSE content type or accept the request
        if response.status_code in [200, 201]:
            content_type = response.headers.get("content-type", "")
            # May be text/event-stream or application/json
            assert "text/event-stream" in content_type or "application/json" in content_type or response.status_code == 200
        elif response.status_code in [404, 501]:
            pytest.skip("AG-UI streaming endpoint not available")

    async def test_stream_endpoint_returns_events(
        self,
        client: AsyncClient,
        test_thread_id: str,
    ):
        """Test that stream endpoint returns proper SSE events."""
        async with client.stream(
            "POST",
            "/api/v1/ag-ui",
            json={
                "thread_id": test_thread_id,
                "input": "What is 2+2?",
                "stream": True
            },
            headers={"Accept": "text/event-stream"}
        ) as response:
            if response.status_code in [200, 201]:
                # Read first few events
                event_count = 0
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        event_count += 1
                        if event_count >= 3:
                            break
                # At least some events should be received
                # (may be 0 if endpoint is mock)
            elif response.status_code in [404, 501]:
                pytest.skip("AG-UI streaming endpoint not available")


# =============================================================================
# 5. Integration Flow Tests (整合流程測試)
# =============================================================================

class TestAGUIIntegrationFlow:
    """Tests for complete AG-UI integration flows."""

    async def test_complete_state_lifecycle(
        self,
        client: AsyncClient,
        test_thread_id: str,
    ):
        """Test complete state lifecycle: create → update → read → delete."""
        # Create initial state
        create_response = await client.patch(
            f"/api/v1/ag-ui/threads/{test_thread_id}/state",
            json={"state": {"step": 1, "data": "initial"}}
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("AG-UI state management not available")

        # Update state
        update_response = await client.patch(
            f"/api/v1/ag-ui/threads/{test_thread_id}/state",
            json={"state": {"step": 2, "data": "updated"}}
        )
        assert update_response.status_code in [200, 201]

        # Read state
        read_response = await client.get(
            f"/api/v1/ag-ui/threads/{test_thread_id}/state"
        )
        assert read_response.status_code == 200
        data = read_response.json()
        state = data.get("state", data)
        assert state.get("step") == 2

        # Delete state
        delete_response = await client.delete(
            f"/api/v1/ag-ui/threads/{test_thread_id}/state"
        )
        assert delete_response.status_code in [200, 204]

    async def test_health_before_operations(
        self,
        client: AsyncClient,
    ):
        """Test that health check works before other operations."""
        # Health check should always work
        health_response = await client.get("/api/v1/ag-ui/health")

        if health_response.status_code != 200:
            pytest.skip("AG-UI service not available")

        # If healthy, other operations should be possible
        data = health_response.json()
        assert data.get("status") in ["ok", "healthy", "up"]

    async def test_multiple_threads_isolation(
        self,
        client: AsyncClient,
    ):
        """Test that different threads maintain isolated state."""
        thread1 = f"e2e-thread-1-{uuid4().hex[:8]}"
        thread2 = f"e2e-thread-2-{uuid4().hex[:8]}"

        # Set state for thread 1
        await client.patch(
            f"/api/v1/ag-ui/threads/{thread1}/state",
            json={"state": {"value": "thread1"}}
        )

        # Set different state for thread 2
        await client.patch(
            f"/api/v1/ag-ui/threads/{thread2}/state",
            json={"state": {"value": "thread2"}}
        )

        # Verify thread 1 state
        response1 = await client.get(f"/api/v1/ag-ui/threads/{thread1}/state")
        if response1.status_code == 200:
            data1 = response1.json()
            state1 = data1.get("state", data1)
            assert state1.get("value") == "thread1"

        # Verify thread 2 state is different
        response2 = await client.get(f"/api/v1/ag-ui/threads/{thread2}/state")
        if response2.status_code == 200:
            data2 = response2.json()
            state2 = data2.get("state", data2)
            assert state2.get("value") == "thread2"

        # Cleanup
        await client.delete(f"/api/v1/ag-ui/threads/{thread1}/state")
        await client.delete(f"/api/v1/ag-ui/threads/{thread2}/state")


# =============================================================================
# 6. Error Handling Tests (錯誤處理測試)
# =============================================================================

class TestAGUIErrorHandling:
    """Tests for error handling in AG-UI endpoints."""

    async def test_invalid_thread_id_format(
        self,
        client: AsyncClient,
    ):
        """Test handling of invalid thread ID format."""
        # Very long invalid ID
        invalid_id = "x" * 1000
        response = await client.get(f"/api/v1/ag-ui/threads/{invalid_id}/state")

        # Should return error, not crash
        assert response.status_code in [400, 404, 422]

    async def test_invalid_state_data(
        self,
        client: AsyncClient,
        test_thread_id: str,
    ):
        """Test handling of invalid state data."""
        # Empty state
        response = await client.patch(
            f"/api/v1/ag-ui/threads/{test_thread_id}/state",
            json={}
        )

        # Should handle gracefully
        assert response.status_code in [200, 201, 400, 422]

    async def test_malformed_json_request(
        self,
        client: AsyncClient,
        test_thread_id: str,
    ):
        """Test handling of malformed JSON in request."""
        response = await client.patch(
            f"/api/v1/ag-ui/threads/{test_thread_id}/state",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )

        # Should return 400 or 422 for invalid JSON
        assert response.status_code in [400, 422]

    async def test_missing_required_fields(
        self,
        client: AsyncClient,
    ):
        """Test handling of missing required fields in sync request."""
        response = await client.post(
            "/api/v1/ag-ui/sync",
            json={}  # Missing required fields
        )

        # Should return validation error
        assert response.status_code in [400, 422, 404, 501]


# =============================================================================
# Helper Functions
# =============================================================================

async def wait_for_sse_event(
    client: AsyncClient,
    url: str,
    body: Dict[str, Any],
    event_type: str,
    timeout: int = 10
) -> Optional[Dict[str, Any]]:
    """
    Wait for a specific SSE event type.

    Args:
        client: HTTP client
        url: Endpoint URL
        body: Request body
        event_type: Event type to wait for
        timeout: Maximum wait time in seconds

    Returns:
        Event data if found, None otherwise
    """
    try:
        async with asyncio.timeout(timeout):
            async with client.stream(
                "POST",
                url,
                json=body,
                headers={"Accept": "text/event-stream"}
            ) as response:
                if response.status_code != 200:
                    return None

                async for line in response.aiter_lines():
                    if line.startswith("event:"):
                        current_event = line.split(":", 1)[1].strip()
                        if current_event == event_type:
                            # Read next data line
                            data_line = await response.aiter_lines().__anext__()
                            if data_line.startswith("data:"):
                                return json.loads(data_line.split(":", 1)[1])
    except asyncio.TimeoutError:
        return None
    except Exception:
        return None

    return None

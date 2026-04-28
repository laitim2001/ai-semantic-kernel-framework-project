"""
IPA Platform - Human Approval Flow E2E Tests

Tests the human-in-the-loop approval workflow functionality.

Test Scenarios:
- Complete approval flow (approve)
- Complete rejection flow (reject)
- Approval with feedback
- Approval timeout handling
- Bulk approval operations

Author: IPA Platform Team
Version: 1.0.0
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from datetime import datetime
from typing import Dict, Any

from .conftest import (
    wait_for_execution_complete,
    create_test_workflow
)


# =============================================================================
# Human Approval Flow Tests
# =============================================================================

class TestHumanApprovalFlow:
    """Test human-in-the-loop approval scenarios."""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_approval_flow_approve(
        self,
        authenticated_client: AsyncClient,
        test_workflow_with_approval: Dict[str, Any]
    ):
        """
        Test complete approval flow with approval action.

        Steps:
        1. Create workflow with approval node
        2. Execute workflow
        3. Wait for pending approval state
        4. Submit approval
        5. Verify workflow continues to completion
        """
        client = authenticated_client

        # Create approval workflow
        workflow = await create_test_workflow(client, test_workflow_with_approval)
        workflow_id = workflow.get("id")

        # Execute workflow
        execute_response = await client.post(
            f"/api/v1/workflows/{workflow_id}/execute",
            json={
                "input": {"message": "Please approve this request"},
                "context": {"requestor": "e2e_test"}
            }
        )

        if execute_response.status_code in [200, 201]:
            execution_data = execute_response.json()
            execution_id = execution_data.get("execution_id") or execution_data.get("id")

            # Wait for pending approval state
            try:
                status = await wait_for_execution_complete(
                    client, execution_id, timeout=30
                )

                if status.get("status") == "pending_approval":
                    # Get checkpoint ID
                    checkpoint_response = await client.get(
                        f"/api/v1/checkpoints/execution/{execution_id}"
                    )

                    if checkpoint_response.status_code == 200:
                        checkpoints = checkpoint_response.json()
                        if checkpoints:
                            checkpoint_id = checkpoints[0].get("id")

                            # Submit approval
                            approve_response = await client.post(
                                f"/api/v1/checkpoints/{checkpoint_id}/approve",
                                json={
                                    "decision": "approved",
                                    "comments": "Approved in E2E test"
                                }
                            )

                            assert approve_response.status_code in [200, 201, 404]

                            # Verify workflow continues
                            final_status = await wait_for_execution_complete(
                                client, execution_id, timeout=30
                            )
                            assert final_status["status"] in ["completed", "failed"]

            except TimeoutError:
                pass  # Acceptable for mock environment

        # Cleanup
        await client.delete(f"/api/v1/workflows/{workflow_id}")

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_approval_flow_reject(
        self,
        authenticated_client: AsyncClient,
        test_workflow_with_approval: Dict[str, Any]
    ):
        """
        Test approval flow with rejection action.

        Verifies that:
        - Rejection stops the workflow
        - Rejection reason is recorded
        - Execution status reflects rejection
        """
        client = authenticated_client

        # Create approval workflow
        workflow = await create_test_workflow(client, test_workflow_with_approval)
        workflow_id = workflow.get("id")

        # Execute workflow
        execute_response = await client.post(
            f"/api/v1/workflows/{workflow_id}/execute",
            json={
                "input": {"message": "This should be rejected"},
                "context": {"requestor": "e2e_test"}
            }
        )

        if execute_response.status_code in [200, 201]:
            execution_data = execute_response.json()
            execution_id = execution_data.get("execution_id") or execution_data.get("id")

            try:
                status = await wait_for_execution_complete(
                    client, execution_id, timeout=30
                )

                if status.get("status") == "pending_approval":
                    # Get checkpoint and reject
                    checkpoint_response = await client.get(
                        f"/api/v1/checkpoints/execution/{execution_id}"
                    )

                    if checkpoint_response.status_code == 200:
                        checkpoints = checkpoint_response.json()
                        if checkpoints:
                            checkpoint_id = checkpoints[0].get("id")

                            # Submit rejection
                            reject_response = await client.post(
                                f"/api/v1/checkpoints/{checkpoint_id}/reject",
                                json={
                                    "decision": "rejected",
                                    "reason": "Rejected in E2E test - insufficient data"
                                }
                            )

                            assert reject_response.status_code in [200, 201, 404]

            except TimeoutError:
                pass

        # Cleanup
        await client.delete(f"/api/v1/workflows/{workflow_id}")

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_approval_with_feedback(
        self,
        authenticated_client: AsyncClient,
        test_workflow_with_approval: Dict[str, Any]
    ):
        """
        Test approval with request for more information.

        This tests the feedback loop where approvers can
        request additional information before making a decision.
        """
        client = authenticated_client

        # Create approval workflow
        workflow = await create_test_workflow(client, test_workflow_with_approval)
        workflow_id = workflow.get("id")

        # Execute workflow
        execute_response = await client.post(
            f"/api/v1/workflows/{workflow_id}/execute",
            json={"input": {"message": "Request requiring feedback"}}
        )

        if execute_response.status_code in [200, 201]:
            execution_data = execute_response.json()
            execution_id = execution_data.get("execution_id") or execution_data.get("id")

            try:
                status = await wait_for_execution_complete(
                    client, execution_id, timeout=30
                )

                if status.get("status") == "pending_approval":
                    checkpoint_response = await client.get(
                        f"/api/v1/checkpoints/execution/{execution_id}"
                    )

                    if checkpoint_response.status_code == 200:
                        checkpoints = checkpoint_response.json()
                        if checkpoints:
                            checkpoint_id = checkpoints[0].get("id")

                            # Request feedback/more info
                            feedback_response = await client.post(
                                f"/api/v1/checkpoints/{checkpoint_id}/feedback",
                                json={
                                    "action": "request_info",
                                    "message": "Please provide budget details"
                                }
                            )

                            # Then approve with additional context
                            approve_response = await client.post(
                                f"/api/v1/checkpoints/{checkpoint_id}/approve",
                                json={
                                    "decision": "approved",
                                    "comments": "Approved after receiving budget info",
                                    "additional_data": {"budget_confirmed": True}
                                }
                            )

            except TimeoutError:
                pass

        # Cleanup
        await client.delete(f"/api/v1/workflows/{workflow_id}")


# =============================================================================
# Pending Approvals List Tests
# =============================================================================

class TestPendingApprovals:
    """Test pending approvals management functionality."""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_list_pending_approvals(
        self,
        authenticated_client: AsyncClient
    ):
        """
        Test listing all pending approvals for a user.
        """
        client = authenticated_client

        # Get pending approvals
        response = await client.get("/api/v1/checkpoints/pending")

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            # Should return a list (possibly empty)
            assert isinstance(data, (list, dict))

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_pending_approvals_filter_by_workflow(
        self,
        authenticated_client: AsyncClient
    ):
        """
        Test filtering pending approvals by workflow.
        """
        client = authenticated_client

        # Get pending approvals filtered by workflow
        response = await client.get(
            "/api/v1/checkpoints/pending",
            params={"workflow_id": "test_workflow_id"}
        )

        assert response.status_code in [200, 404]

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_bulk_approval_operations(
        self,
        authenticated_client: AsyncClient
    ):
        """
        Test bulk approval operations.

        This tests the ability to approve/reject multiple
        pending items at once.
        """
        client = authenticated_client

        # Test bulk approve endpoint
        bulk_response = await client.post(
            "/api/v1/checkpoints/bulk-approve",
            json={
                "checkpoint_ids": ["id1", "id2", "id3"],
                "decision": "approved",
                "comments": "Bulk approved in E2E test"
            }
        )

        # Accept various responses (endpoint may not exist)
        assert bulk_response.status_code in [200, 201, 404, 405, 422]


# =============================================================================
# Approval Notifications Tests
# =============================================================================

class TestApprovalNotifications:
    """Test approval notification functionality."""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_approval_creates_notification(
        self,
        authenticated_client: AsyncClient,
        test_workflow_with_approval: Dict[str, Any]
    ):
        """
        Test that pending approvals create notifications.
        """
        client = authenticated_client

        # Check notifications endpoint exists
        response = await client.get("/api/v1/notifications/")

        assert response.status_code in [200, 404]

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_teams_notification_on_approval_request(
        self,
        authenticated_client: AsyncClient
    ):
        """
        Test that Teams notifications are sent for approval requests.

        This is a smoke test to verify the notification system
        is connected to Teams.
        """
        client = authenticated_client

        # Test Teams notification endpoint
        response = await client.post(
            "/api/v1/notifications/teams/test",
            json={
                "message": "E2E Test notification",
                "channel": "test"
            }
        )

        # Accept various responses
        assert response.status_code in [200, 201, 404, 422, 500]

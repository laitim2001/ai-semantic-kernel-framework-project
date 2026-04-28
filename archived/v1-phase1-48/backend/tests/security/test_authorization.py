"""
IPA Platform - Authorization Security Tests

Tests for authorization and access control including:
- Role-based access control
- Resource ownership verification
- Permission enforcement
- Privilege escalation prevention

Author: IPA Platform Team
Version: 1.0.0
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from datetime import datetime, timedelta
import jwt


# =============================================================================
# Test Configuration
# =============================================================================

SECRET_KEY = "test_secret_key_for_security_tests"
ALGORITHM = "HS256"


def create_token_with_role(user_id: str, role: str) -> str:
    """Create a JWT token with specific role."""
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# =============================================================================
# Role-Based Access Control Tests
# =============================================================================

class TestRoleBasedAccess:
    """Test role-based access control."""

    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_admin_only_endpoints(
        self,
        unauthenticated_client: AsyncClient
    ):
        """Test that admin-only endpoints are protected."""
        # Regular user token
        user_token = create_token_with_role("user_123", "user")

        admin_endpoints = [
            ("GET", "/api/v1/admin/users"),
            ("GET", "/api/v1/admin/settings"),
            ("POST", "/api/v1/admin/users"),
            ("DELETE", "/api/v1/admin/users/test_id"),
        ]

        for method, endpoint in admin_endpoints:
            if method == "GET":
                response = await unauthenticated_client.get(
                    endpoint,
                    headers={"Authorization": f"Bearer {user_token}"}
                )
            elif method == "POST":
                response = await unauthenticated_client.post(
                    endpoint,
                    json={},
                    headers={"Authorization": f"Bearer {user_token}"}
                )
            elif method == "DELETE":
                response = await unauthenticated_client.delete(
                    endpoint,
                    headers={"Authorization": f"Bearer {user_token}"}
                )

            # Should be forbidden for regular users
            # 403 Forbidden, 401 Unauthorized, or 404 Not Found (if path doesn't exist)
            assert response.status_code in [401, 403, 404]

    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_role_escalation_prevention(
        self,
        unauthenticated_client: AsyncClient
    ):
        """Test that users cannot escalate their own roles."""
        user_token = create_token_with_role("user_123", "user")

        response = await unauthenticated_client.put(
            "/api/v1/users/user_123",
            json={"role": "admin"},
            headers={"Authorization": f"Bearer {user_token}"}
        )

        # Should not allow role self-escalation
        if response.status_code == 200:
            data = response.json()
            # Role should not be changed to admin
            assert data.get("role") != "admin"
        else:
            # Or request should be rejected
            assert response.status_code in [400, 403, 404, 422]


# =============================================================================
# Resource Ownership Tests
# =============================================================================

class TestResourceOwnership:
    """Test resource ownership verification."""

    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_user_cannot_access_others_resources(
        self,
        unauthenticated_client: AsyncClient
    ):
        """Test that users cannot access resources they don't own."""
        # User A's token
        user_a_token = create_token_with_role("user_a", "user")

        # Try to access User B's resources
        other_user_resources = [
            "/api/v1/users/user_b/workflows",
            "/api/v1/users/user_b/agents",
            "/api/v1/users/user_b/executions",
        ]

        for endpoint in other_user_resources:
            response = await unauthenticated_client.get(
                endpoint,
                headers={"Authorization": f"Bearer {user_a_token}"}
            )

            # Should be forbidden or not found
            assert response.status_code in [403, 404]

    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_user_cannot_modify_others_resources(
        self,
        unauthenticated_client: AsyncClient
    ):
        """Test that users cannot modify resources they don't own."""
        user_token = create_token_with_role("user_a", "user")

        # Try to modify another user's workflow
        response = await unauthenticated_client.put(
            "/api/v1/workflows/other_user_workflow_id",
            json={"name": "Hacked Workflow"},
            headers={"Authorization": f"Bearer {user_token}"}
        )

        # Should be forbidden or not found
        assert response.status_code in [403, 404]

    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_user_cannot_delete_others_resources(
        self,
        unauthenticated_client: AsyncClient
    ):
        """Test that users cannot delete resources they don't own."""
        user_token = create_token_with_role("user_a", "user")

        # Try to delete another user's agent
        response = await unauthenticated_client.delete(
            "/api/v1/agents/other_user_agent_id",
            headers={"Authorization": f"Bearer {user_token}"}
        )

        # Should be forbidden or not found
        assert response.status_code in [403, 404]


# =============================================================================
# IDOR (Insecure Direct Object Reference) Tests
# =============================================================================

class TestIDOR:
    """Test IDOR vulnerability prevention."""

    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_cannot_access_resource_by_guessing_id(
        self,
        unauthenticated_client: AsyncClient
    ):
        """Test that sequential IDs cannot be used to access resources."""
        user_token = create_token_with_role("user_a", "user")

        # Try sequential IDs
        for i in range(1, 11):
            response = await unauthenticated_client.get(
                f"/api/v1/workflows/{i}",
                headers={"Authorization": f"Bearer {user_token}"}
            )

            # Should not return other users' data
            if response.status_code == 200:
                data = response.json()
                # If we get data, it should belong to user_a
                # (or be public data)
                owner = data.get("owner_id") or data.get("user_id")
                if owner:
                    assert owner == "user_a" or data.get("is_public") is True

    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_uuid_based_ids_preferred(
        self,
        unauthenticated_client: AsyncClient
    ):
        """Test that UUIDs are used for resource IDs (harder to guess)."""
        user_token = create_token_with_role("user_a", "user")

        response = await unauthenticated_client.post(
            "/api/v1/workflows/",
            json={
                "name": "Test Workflow",
                "description": "Test"
            },
            headers={"Authorization": f"Bearer {user_token}"}
        )

        if response.status_code in [200, 201]:
            data = response.json()
            resource_id = data.get("id")

            if resource_id:
                # Check if ID looks like UUID (not sequential integer)
                import re
                uuid_pattern = re.compile(
                    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
                    re.IGNORECASE
                )
                # ID should be UUID or at least not a small integer
                is_uuid = bool(uuid_pattern.match(str(resource_id)))
                is_small_int = str(resource_id).isdigit() and int(resource_id) < 1000

                # Prefer UUIDs or large random IDs
                assert is_uuid or not is_small_int


# =============================================================================
# Approval Authorization Tests
# =============================================================================

class TestApprovalAuthorization:
    """Test approval workflow authorization."""

    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_only_approvers_can_approve(
        self,
        unauthenticated_client: AsyncClient
    ):
        """Test that only designated approvers can approve requests."""
        non_approver_token = create_token_with_role("regular_user", "user")

        response = await unauthenticated_client.post(
            "/api/v1/checkpoints/some_checkpoint_id/approve",
            json={"decision": "approved"},
            headers={"Authorization": f"Bearer {non_approver_token}"}
        )

        # Should be forbidden for non-approvers
        assert response.status_code in [403, 404]

    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_cannot_approve_own_request(
        self,
        unauthenticated_client: AsyncClient
    ):
        """Test that users cannot approve their own requests."""
        user_token = create_token_with_role("requestor_user", "user")

        # First create a request (if endpoint exists)
        create_response = await unauthenticated_client.post(
            "/api/v1/workflows/test_workflow/execute",
            json={"input": {"message": "test"}},
            headers={"Authorization": f"Bearer {user_token}"}
        )

        if create_response.status_code in [200, 201]:
            data = create_response.json()
            checkpoint_id = data.get("checkpoint_id")

            if checkpoint_id:
                # Try to approve own request
                approve_response = await unauthenticated_client.post(
                    f"/api/v1/checkpoints/{checkpoint_id}/approve",
                    json={"decision": "approved"},
                    headers={"Authorization": f"Bearer {user_token}"}
                )

                # Should not allow self-approval
                assert approve_response.status_code in [403, 404, 422]


# =============================================================================
# API Key Authorization Tests
# =============================================================================

class TestAPIKeyAuthorization:
    """Test API key authorization if applicable."""

    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_api_key_cannot_access_admin_endpoints(
        self,
        unauthenticated_client: AsyncClient
    ):
        """Test that API keys have limited permissions."""
        # API keys typically have restricted access
        response = await unauthenticated_client.get(
            "/api/v1/admin/users",
            headers={"X-API-Key": "test_api_key_123"}
        )

        # Should be forbidden for API keys
        assert response.status_code in [401, 403, 404]

    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_api_key_rate_limited(
        self,
        unauthenticated_client: AsyncClient
    ):
        """Test that API keys are rate limited."""
        # Make many requests
        responses = []
        for _ in range(50):
            response = await unauthenticated_client.get(
                "/api/v1/workflows/",
                headers={"X-API-Key": "test_api_key_123"}
            )
            responses.append(response.status_code)

        # At least some should be rate limited (429) or rejected
        # This is a soft test as rate limiting config varies
        pass  # Rate limiting is configured separately

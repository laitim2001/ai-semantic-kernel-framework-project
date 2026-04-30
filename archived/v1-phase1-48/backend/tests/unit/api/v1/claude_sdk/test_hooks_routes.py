"""Tests for Claude SDK Hooks API routes.

Sprint 51: S51-2 Hooks API Routes Unit Tests
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.v1.claude_sdk.hooks_routes import (
    router,
    HookManager,
    HookType,
    HookPriority,
    get_hook_manager,
)


# Create test app
app = FastAPI()
app.include_router(router, prefix="/api/v1/claude-sdk")


class TestHooksRoutes:
    """Tests for Claude SDK Hooks API routes."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_hook_manager(self):
        """Create a fresh hook manager for testing."""
        return HookManager()

    @pytest.fixture
    def override_hook_manager(self, mock_hook_manager):
        """Override the global hook manager."""
        with patch(
            "src.api.v1.claude_sdk.hooks_routes.get_hook_manager",
            return_value=mock_hook_manager,
        ):
            yield mock_hook_manager


class TestListHooksEndpoint(TestHooksRoutes):
    """Tests for GET /hooks endpoint."""

    def test_list_hooks_empty(self, client, override_hook_manager):
        """Test listing hooks when none are registered."""
        response = client.get("/api/v1/claude-sdk/hooks")
        assert response.status_code == 200
        data = response.json()
        assert data["hooks"] == []
        assert data["total"] == 0

    def test_list_hooks_success(self, client, override_hook_manager):
        """Test listing registered hooks."""
        # Register a hook first
        override_hook_manager.register_hook(
            hook_type=HookType.APPROVAL,
            name="test_approval",
            priority=HookPriority.HIGH,
        )

        response = client.get("/api/v1/claude-sdk/hooks")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["hooks"][0]["name"] == "test_approval"
        assert data["hooks"][0]["type"] == "approval"

    def test_list_hooks_filter_by_type(self, client, override_hook_manager):
        """Test filtering hooks by type."""
        override_hook_manager.register_hook(HookType.APPROVAL, "approval1")
        override_hook_manager.register_hook(HookType.AUDIT, "audit1")

        response = client.get("/api/v1/claude-sdk/hooks?type=approval")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["hooks"][0]["type"] == "approval"

    def test_list_hooks_filter_enabled_only(self, client, override_hook_manager):
        """Test filtering only enabled hooks."""
        hook = override_hook_manager.register_hook(HookType.APPROVAL, "approval1")
        override_hook_manager.disable_hook(hook.id)
        override_hook_manager.register_hook(HookType.AUDIT, "audit1")

        response = client.get("/api/v1/claude-sdk/hooks?enabled_only=true")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["hooks"][0]["enabled"] is True


class TestGetHookEndpoint(TestHooksRoutes):
    """Tests for GET /hooks/{id} endpoint."""

    def test_get_hook_success(self, client, override_hook_manager):
        """Test getting a specific hook."""
        hook = override_hook_manager.register_hook(
            hook_type=HookType.RATE_LIMIT,
            name="rate_limit_test",
        )

        response = client.get(f"/api/v1/claude-sdk/hooks/{hook.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == hook.id
        assert data["name"] == "rate_limit_test"
        assert data["type"] == "rate_limit"

    def test_get_hook_not_found(self, client, override_hook_manager):
        """Test getting a non-existent hook."""
        response = client.get("/api/v1/claude-sdk/hooks/nonexistent-id")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestRegisterHookEndpoint(TestHooksRoutes):
    """Tests for POST /hooks/register endpoint."""

    def test_register_approval_hook(self, client, override_hook_manager):
        """Test registering an approval hook."""
        response = client.post(
            "/api/v1/claude-sdk/hooks/register",
            json={
                "type": "approval",
                "name": "test_approval",
                "priority": "high",
                "config": {"tools": ["Write", "Edit"]},
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test_approval"
        assert data["type"] == "approval"
        assert data["priority"] == 75  # HIGH priority

    def test_register_audit_hook(self, client, override_hook_manager):
        """Test registering an audit hook."""
        response = client.post(
            "/api/v1/claude-sdk/hooks/register",
            json={
                "type": "audit",
                "config": {"redact_patterns": ["password", "secret"]},
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "audit"

    def test_register_rate_limit_hook(self, client, override_hook_manager):
        """Test registering a rate limit hook."""
        response = client.post(
            "/api/v1/claude-sdk/hooks/register",
            json={
                "type": "rate_limit",
                "config": {"max_calls_per_minute": 30, "max_concurrent": 3},
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "rate_limit"

    def test_register_sandbox_hook(self, client, override_hook_manager):
        """Test registering a sandbox hook."""
        response = client.post(
            "/api/v1/claude-sdk/hooks/register",
            json={
                "type": "sandbox",
                "config": {
                    "allowed_paths": ["/home/user", "/tmp"],
                    "strict_mode": False,
                },
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "sandbox"

    def test_register_hook_with_default_name(self, client, override_hook_manager):
        """Test registering a hook without custom name."""
        response = client.post(
            "/api/v1/claude-sdk/hooks/register",
            json={"type": "approval"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "approval_" in data["name"]

    def test_register_hook_default_priority(self, client, override_hook_manager):
        """Test registering a hook with default priority."""
        response = client.post(
            "/api/v1/claude-sdk/hooks/register",
            json={"type": "audit"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["priority"] == 50  # NORMAL priority


class TestRemoveHookEndpoint(TestHooksRoutes):
    """Tests for DELETE /hooks/{id} endpoint."""

    def test_remove_hook_success(self, client, override_hook_manager):
        """Test removing a registered hook."""
        hook = override_hook_manager.register_hook(HookType.APPROVAL, "to_remove")

        response = client.delete(f"/api/v1/claude-sdk/hooks/{hook.id}")
        assert response.status_code == 204

        # Verify hook is removed
        assert override_hook_manager.get_hook(hook.id) is None

    def test_remove_hook_not_found(self, client, override_hook_manager):
        """Test removing a non-existent hook."""
        response = client.delete("/api/v1/claude-sdk/hooks/nonexistent-id")
        assert response.status_code == 404


class TestEnableHookEndpoint(TestHooksRoutes):
    """Tests for PUT /hooks/{id}/enable endpoint."""

    def test_enable_hook_success(self, client, override_hook_manager):
        """Test enabling a disabled hook."""
        hook = override_hook_manager.register_hook(HookType.APPROVAL, "to_enable")
        override_hook_manager.disable_hook(hook.id)

        response = client.put(f"/api/v1/claude-sdk/hooks/{hook.id}/enable")
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True

    def test_enable_hook_not_found(self, client, override_hook_manager):
        """Test enabling a non-existent hook."""
        response = client.put("/api/v1/claude-sdk/hooks/nonexistent-id/enable")
        assert response.status_code == 404


class TestDisableHookEndpoint(TestHooksRoutes):
    """Tests for PUT /hooks/{id}/disable endpoint."""

    def test_disable_hook_success(self, client, override_hook_manager):
        """Test disabling an enabled hook."""
        hook = override_hook_manager.register_hook(HookType.APPROVAL, "to_disable")

        response = client.put(f"/api/v1/claude-sdk/hooks/{hook.id}/disable")
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False

    def test_disable_hook_not_found(self, client, override_hook_manager):
        """Test disabling a non-existent hook."""
        response = client.put("/api/v1/claude-sdk/hooks/nonexistent-id/disable")
        assert response.status_code == 404


class TestHookPriorityMapping:
    """Tests for hook priority mapping."""

    def test_priority_values(self):
        """Test priority enum to integer mapping."""
        from src.api.v1.claude_sdk.hooks_routes import _priority_to_int

        assert _priority_to_int(HookPriority.LOW) == 25
        assert _priority_to_int(HookPriority.NORMAL) == 50
        assert _priority_to_int(HookPriority.HIGH) == 75
        assert _priority_to_int(HookPriority.CRITICAL) == 100


class TestHookManager:
    """Tests for HookManager class."""

    def test_list_hooks_sorted_by_priority(self):
        """Test that hooks are listed sorted by priority."""
        manager = HookManager()
        manager.register_hook(HookType.APPROVAL, "low", HookPriority.LOW)
        manager.register_hook(HookType.AUDIT, "high", HookPriority.HIGH)
        manager.register_hook(HookType.SANDBOX, "normal", HookPriority.NORMAL)

        hooks = manager.list_hooks()
        priorities = [h.priority for h in hooks]
        assert priorities == sorted(priorities, reverse=True)

    def test_enable_disable_toggle(self):
        """Test enabling and disabling hooks."""
        manager = HookManager()
        hook = manager.register_hook(HookType.APPROVAL, "toggle_test")

        assert hook.enabled is True

        manager.disable_hook(hook.id)
        assert manager.get_hook(hook.id).enabled is False

        manager.enable_hook(hook.id)
        assert manager.get_hook(hook.id).enabled is True

    def test_hook_chain_property(self):
        """Test that hook chain is accessible."""
        manager = HookManager()
        manager.register_hook(HookType.APPROVAL, "chain_test")

        chain = manager.chain
        assert chain is not None

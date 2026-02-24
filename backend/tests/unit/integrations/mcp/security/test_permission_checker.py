"""Tests for MCP Permission Checker.

Sprint 123, Story 123-3: MCP module unit tests.

Tests MCPPermissionChecker from src.integrations.mcp.security.permission_checker,
including log mode, enforce mode, and statistics tracking.
"""

import os
from unittest.mock import patch

import pytest

from src.integrations.mcp.security.permission_checker import MCPPermissionChecker
from src.integrations.mcp.security.permissions import (
    PermissionLevel,
    PermissionManager,
    PermissionPolicy,
)


def _create_restrictive_manager() -> PermissionManager:
    """Create a PermissionManager that denies all operations by default."""
    manager = PermissionManager()
    # No policies added — default deny (NONE level)
    return manager


def _create_permissive_manager() -> PermissionManager:
    """Create a PermissionManager that allows all operations."""
    manager = PermissionManager()
    manager.add_policy(PermissionPolicy(
        name="allow-all",
        servers=["*"],
        tools=["*"],
        level=PermissionLevel.ADMIN,
        priority=100,
    ))
    return manager


class TestMCPPermissionCheckerLogMode:
    """Tests for MCPPermissionChecker in log mode (default)."""

    @patch.dict(os.environ, {"APP_ENV": "development", "MCP_PERMISSION_MODE": "log"})
    def test_default_dev_environment_allows_all(self):
        """Test that development environment creates permissive default policy."""
        checker = MCPPermissionChecker()
        result = checker.check_tool_permission(
            server_name="any-server",
            tool_name="any-tool",
            required_level=3,
            user_id="dev-user",
        )
        assert result is True

    @patch.dict(os.environ, {"MCP_PERMISSION_MODE": "log"})
    def test_allowed_returns_true(self):
        """Test that allowed operations return True."""
        manager = _create_permissive_manager()
        checker = MCPPermissionChecker(permission_manager=manager)

        result = checker.check_tool_permission(
            server_name="azure-mcp",
            tool_name="list_vms",
            required_level=2,
            user_id="user1",
            roles=["developer"],
        )
        assert result is True

    @patch.dict(os.environ, {"MCP_PERMISSION_MODE": "log"})
    def test_denied_logs_warning_returns_false(self):
        """Test that denied operations in log mode return False without raising."""
        manager = _create_restrictive_manager()
        checker = MCPPermissionChecker(permission_manager=manager)

        result = checker.check_tool_permission(
            server_name="azure-mcp",
            tool_name="delete_vm",
            required_level=3,
            user_id="user1",
        )
        # In log mode, denied operations return False (no exception)
        assert result is False

    @patch.dict(os.environ, {"MCP_PERMISSION_MODE": "log"})
    def test_check_count_increments(self):
        """Test that check_count increments with each permission check."""
        manager = _create_permissive_manager()
        checker = MCPPermissionChecker(permission_manager=manager)

        assert checker.check_count == 0
        checker.check_tool_permission("s1", "t1", user_id="u1")
        assert checker.check_count == 1
        checker.check_tool_permission("s2", "t2", user_id="u2")
        assert checker.check_count == 2

    @patch.dict(os.environ, {"MCP_PERMISSION_MODE": "log"})
    def test_deny_count_increments(self):
        """Test that deny_count increments on denied checks."""
        manager = _create_restrictive_manager()
        checker = MCPPermissionChecker(permission_manager=manager)

        assert checker.deny_count == 0
        checker.check_tool_permission("s1", "t1", required_level=3, user_id="u1")
        assert checker.deny_count == 1
        checker.check_tool_permission("s2", "t2", required_level=2, user_id="u2")
        assert checker.deny_count == 2


class TestMCPPermissionCheckerEnforceMode:
    """Tests for MCPPermissionChecker in enforce mode."""

    @patch.dict(os.environ, {"MCP_PERMISSION_MODE": "enforce"})
    def test_denied_raises_permission_error(self):
        """Test that denied operations in enforce mode raise PermissionError."""
        manager = _create_restrictive_manager()
        checker = MCPPermissionChecker(permission_manager=manager)

        with pytest.raises(PermissionError, match="Permission denied"):
            checker.check_tool_permission(
                server_name="azure-mcp",
                tool_name="delete_vm",
                required_level=3,
                user_id="user1",
            )

    @patch.dict(os.environ, {"MCP_PERMISSION_MODE": "enforce"})
    def test_allowed_does_not_raise(self):
        """Test that allowed operations in enforce mode do not raise."""
        manager = _create_permissive_manager()
        checker = MCPPermissionChecker(permission_manager=manager)

        result = checker.check_tool_permission(
            server_name="azure-mcp",
            tool_name="list_vms",
            required_level=2,
            user_id="admin",
        )
        assert result is True


class TestMCPPermissionCheckerStats:
    """Tests for MCPPermissionChecker statistics tracking."""

    @patch.dict(os.environ, {"MCP_PERMISSION_MODE": "log"})
    def test_initial_stats(self):
        """Test that initial stats are zeroed out."""
        manager = _create_permissive_manager()
        checker = MCPPermissionChecker(permission_manager=manager)

        stats = checker.get_stats()
        assert stats["mode"] == "log"
        assert stats["total_checks"] == 0
        assert stats["total_denials"] == 0
        assert stats["denial_rate"] == 0.0

    @patch.dict(os.environ, {"MCP_PERMISSION_MODE": "log"})
    def test_stats_after_checks(self):
        """Test that stats correctly reflect allowed and denied checks."""
        manager = PermissionManager()
        # Policy only allows READ on azure-mcp
        manager.add_policy(PermissionPolicy(
            name="read-only",
            servers=["azure-*"],
            tools=["list_*"],
            level=PermissionLevel.READ,
            priority=50,
        ))
        checker = MCPPermissionChecker(permission_manager=manager)

        # Allowed: READ level on matching server/tool
        checker.check_tool_permission(
            "azure-mcp", "list_vms", required_level=1, user_id="u1"
        )
        # Denied: EXECUTE level exceeds READ policy
        checker.check_tool_permission(
            "azure-mcp", "list_vms", required_level=2, user_id="u1"
        )
        # Denied: non-matching server falls to default deny
        checker.check_tool_permission(
            "shell-mcp", "run_command", required_level=1, user_id="u1"
        )

        stats = checker.get_stats()
        assert stats["total_checks"] == 3
        assert stats["total_denials"] == 2

    @patch.dict(os.environ, {"MCP_PERMISSION_MODE": "log"})
    def test_denial_rate_calculation(self):
        """Test that denial_rate is computed correctly."""
        manager = _create_restrictive_manager()
        checker = MCPPermissionChecker(permission_manager=manager)

        # 4 checks, all denied
        for _ in range(4):
            checker.check_tool_permission(
                "s", "t", required_level=1, user_id="u"
            )

        stats = checker.get_stats()
        assert stats["denial_rate"] == 1.0

        # Mix: use a manager where some pass, some fail
        mixed_manager = PermissionManager()
        mixed_manager.add_policy(PermissionPolicy(
            name="read",
            servers=["*"],
            tools=["*"],
            level=PermissionLevel.READ,
        ))
        mixed_checker = MCPPermissionChecker(permission_manager=mixed_manager)

        # 1 allowed (READ check)
        mixed_checker.check_tool_permission(
            "s", "t", required_level=1, user_id="u"
        )
        # 1 denied (EXECUTE check against READ policy)
        mixed_checker.check_tool_permission(
            "s", "t", required_level=2, user_id="u"
        )

        mixed_stats = mixed_checker.get_stats()
        assert mixed_stats["total_checks"] == 2
        assert mixed_stats["total_denials"] == 1
        assert mixed_stats["denial_rate"] == 0.5

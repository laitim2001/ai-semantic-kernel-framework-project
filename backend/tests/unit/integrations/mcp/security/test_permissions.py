"""Tests for MCP Permission Management.

Sprint 123, Story 123-3: MCP module unit tests.

Tests PermissionLevel, Permission, PermissionPolicy, and PermissionManager
from src.integrations.mcp.security.permissions.
"""

import pytest

from src.integrations.mcp.security.permissions import (
    Permission,
    PermissionLevel,
    PermissionManager,
    PermissionPolicy,
)


class TestPermissionLevel:
    """Tests for PermissionLevel IntEnum hierarchy."""

    def test_hierarchy_values(self):
        """Test that permission levels have correct integer values."""
        assert PermissionLevel.NONE == 0
        assert PermissionLevel.READ == 1
        assert PermissionLevel.EXECUTE == 2
        assert PermissionLevel.ADMIN == 3

    def test_comparison(self):
        """Test that permission levels support comparison operators."""
        assert PermissionLevel.NONE < PermissionLevel.READ
        assert PermissionLevel.READ < PermissionLevel.EXECUTE
        assert PermissionLevel.EXECUTE < PermissionLevel.ADMIN
        assert PermissionLevel.ADMIN >= PermissionLevel.EXECUTE
        assert PermissionLevel.ADMIN > PermissionLevel.NONE
        assert PermissionLevel.EXECUTE >= PermissionLevel.EXECUTE


class TestPermission:
    """Tests for Permission dataclass matching logic."""

    def test_exact_match(self):
        """Test exact server and tool name matching."""
        perm = Permission(
            server="azure-mcp",
            tool="list_vms",
            level=PermissionLevel.READ,
        )
        assert perm.matches("azure-mcp", "list_vms") is True

    def test_wildcard_server(self):
        """Test wildcard pattern matching for server name."""
        perm = Permission(
            server="*",
            tool="list_vms",
            level=PermissionLevel.READ,
        )
        assert perm.matches("azure-mcp", "list_vms") is True
        assert perm.matches("shell-mcp", "list_vms") is True
        assert perm.matches("azure-mcp", "delete_vm") is False

    def test_wildcard_tool(self):
        """Test wildcard pattern matching for tool name."""
        perm = Permission(
            server="azure-mcp",
            tool="*",
            level=PermissionLevel.EXECUTE,
        )
        assert perm.matches("azure-mcp", "list_vms") is True
        assert perm.matches("azure-mcp", "delete_vm") is True
        assert perm.matches("shell-mcp", "list_vms") is False

    def test_no_match(self):
        """Test that non-matching server/tool returns False."""
        perm = Permission(
            server="azure-mcp",
            tool="list_vms",
            level=PermissionLevel.READ,
        )
        assert perm.matches("shell-mcp", "list_vms") is False
        assert perm.matches("azure-mcp", "delete_vm") is False
        assert perm.matches("shell-mcp", "run_command") is False


class TestPermissionPolicy:
    """Tests for PermissionPolicy check logic."""

    def test_deny_list_takes_precedence(self):
        """Test that deny_list patterns return False regardless of level."""
        policy = PermissionPolicy(
            name="restricted",
            servers=["*"],
            tools=["*"],
            level=PermissionLevel.ADMIN,
            deny_list=["azure-mcp/delete_*", "*/destroy_*"],
        )
        # Denied by deny_list even though level is ADMIN
        assert policy.check("azure-mcp", "delete_vm", PermissionLevel.EXECUTE) is False
        assert policy.check("shell-mcp", "destroy_all", PermissionLevel.READ) is False

    def test_server_match_tool_match_level_sufficient(self):
        """Test that matching server+tool with sufficient level returns True."""
        policy = PermissionPolicy(
            name="dev",
            servers=["dev-*"],
            tools=["read_*", "list_*"],
            level=PermissionLevel.EXECUTE,
        )
        assert policy.check("dev-mcp", "read_file", PermissionLevel.READ) is True
        assert policy.check("dev-mcp", "list_vms", PermissionLevel.EXECUTE) is True

    def test_server_match_tool_match_level_insufficient(self):
        """Test that matching server+tool with insufficient level returns False."""
        policy = PermissionPolicy(
            name="reader",
            servers=["*"],
            tools=["*"],
            level=PermissionLevel.READ,
        )
        assert policy.check("azure-mcp", "list_vms", PermissionLevel.EXECUTE) is False
        assert policy.check("azure-mcp", "list_vms", PermissionLevel.ADMIN) is False

    def test_server_no_match(self):
        """Test that non-matching server returns None (not applicable)."""
        policy = PermissionPolicy(
            name="azure-only",
            servers=["azure-*"],
            tools=["*"],
            level=PermissionLevel.ADMIN,
        )
        result = policy.check("shell-mcp", "run_command", PermissionLevel.EXECUTE)
        assert result is None

    def test_tool_no_match(self):
        """Test that non-matching tool returns None (not applicable)."""
        policy = PermissionPolicy(
            name="read-tools",
            servers=["*"],
            tools=["read_*"],
            level=PermissionLevel.EXECUTE,
        )
        result = policy.check("azure-mcp", "delete_vm", PermissionLevel.EXECUTE)
        assert result is None

    def test_wildcard_patterns(self):
        """Test that wildcard patterns in servers and tools work correctly."""
        policy = PermissionPolicy(
            name="all-access",
            servers=["*"],
            tools=["*"],
            level=PermissionLevel.ADMIN,
        )
        assert policy.check("any-server", "any-tool", PermissionLevel.ADMIN) is True
        assert policy.check("azure", "list", PermissionLevel.READ) is True


class TestPermissionManager:
    """Tests for PermissionManager."""

    @pytest.fixture
    def manager(self):
        """Create a fresh PermissionManager instance."""
        return PermissionManager()

    @pytest.fixture
    def admin_policy(self):
        """Create an admin-level permission policy."""
        return PermissionPolicy(
            name="admin",
            servers=["*"],
            tools=["*"],
            level=PermissionLevel.ADMIN,
            priority=100,
        )

    @pytest.fixture
    def developer_policy(self):
        """Create a developer-level permission policy."""
        return PermissionPolicy(
            name="developer",
            servers=["dev-*"],
            tools=["*"],
            level=PermissionLevel.EXECUTE,
            deny_list=["*/delete_*", "*/destroy_*"],
            priority=50,
        )

    def test_add_and_get_policy(self, manager, admin_policy):
        """Test adding and retrieving a policy."""
        manager.add_policy(admin_policy)
        retrieved = manager.get_policy("admin")
        assert retrieved is not None
        assert retrieved.name == "admin"
        assert retrieved.level == PermissionLevel.ADMIN

    def test_remove_policy(self, manager, admin_policy):
        """Test removing an existing policy returns True."""
        manager.add_policy(admin_policy)
        assert manager.remove_policy("admin") is True
        assert manager.get_policy("admin") is None

    def test_remove_nonexistent_returns_false(self, manager):
        """Test removing a nonexistent policy returns False."""
        assert manager.remove_policy("nonexistent") is False

    def test_check_permission_no_policies_default_deny(self, manager):
        """Test that default deny applies when no policies are configured."""
        result = manager.check_permission(
            user_id="user1",
            roles=["developer"],
            server="azure-mcp",
            tool="list_vms",
            level=PermissionLevel.READ,
        )
        assert result is False

    def test_check_permission_with_admin_policy(self, manager, admin_policy):
        """Test permission check with admin policy grants full access."""
        manager.add_policy(admin_policy)
        result = manager.check_permission(
            server="azure-mcp",
            tool="delete_vm",
            level=PermissionLevel.ADMIN,
        )
        assert result is True

    def test_check_permission_with_role_based_policy(
        self, manager, developer_policy
    ):
        """Test permission check using role-based policy assignment."""
        manager.add_policy(developer_policy)
        manager.assign_policy_to_role("developer", "developer")

        # Allowed: dev server, non-deny-listed tool
        result = manager.check_permission(
            user_id="user1",
            roles=["developer"],
            server="dev-mcp",
            tool="read_file",
            level=PermissionLevel.EXECUTE,
        )
        assert result is True

    def test_check_permission_with_user_specific_policy(
        self, manager, admin_policy
    ):
        """Test permission check using user-specific policy assignment."""
        manager.add_policy(admin_policy)
        manager.assign_policy_to_user("admin-user", "admin")

        result = manager.check_permission(
            user_id="admin-user",
            server="azure-mcp",
            tool="delete_vm",
            level=PermissionLevel.ADMIN,
        )
        assert result is True

    def test_deny_list_overrides_allow(self, manager, developer_policy):
        """Test that deny_list in a policy overrides the permission level."""
        manager.add_policy(developer_policy)
        manager.assign_policy_to_role("developer", "developer")

        result = manager.check_permission(
            user_id="user1",
            roles=["developer"],
            server="dev-mcp",
            tool="delete_vm",
            level=PermissionLevel.EXECUTE,
        )
        assert result is False

    def test_priority_ordering(self, manager):
        """Test that higher priority policies are evaluated first."""
        # Low priority deny-all
        deny_policy = PermissionPolicy(
            name="deny-all",
            servers=["*"],
            tools=["*"],
            level=PermissionLevel.NONE,
            priority=10,
        )
        # High priority allow-admin
        allow_policy = PermissionPolicy(
            name="allow-admin",
            servers=["*"],
            tools=["*"],
            level=PermissionLevel.ADMIN,
            priority=100,
        )
        manager.add_policy(deny_policy)
        manager.add_policy(allow_policy)

        # Higher priority allow-admin should be evaluated first
        result = manager.check_permission(
            server="azure-mcp",
            tool="delete_vm",
            level=PermissionLevel.ADMIN,
        )
        assert result is True

    def test_assign_policy_to_nonexistent_returns_false(self, manager):
        """Test assigning a nonexistent policy returns False."""
        assert manager.assign_policy_to_user("user1", "nonexistent") is False
        assert manager.assign_policy_to_role("admin", "nonexistent") is False

    def test_set_default_level(self, manager):
        """Test setting the default permission level affects fallback."""
        manager.set_default_level(PermissionLevel.READ)

        # With default READ, a READ-level check should pass
        result = manager.check_permission(
            server="any-server",
            tool="any-tool",
            level=PermissionLevel.READ,
        )
        assert result is True

        # But EXECUTE should still be denied by default READ
        result = manager.check_permission(
            server="any-server",
            tool="any-tool",
            level=PermissionLevel.EXECUTE,
        )
        assert result is False

    def test_ip_whitelist_condition(self, manager):
        """Test ip_whitelist condition evaluation."""
        policy = PermissionPolicy(
            name="office-only",
            servers=["*"],
            tools=["*"],
            level=PermissionLevel.ADMIN,
            conditions={"ip_whitelist": ["10.0.0.1", "10.0.0.2"]},
            priority=50,
        )
        manager.add_policy(policy)

        # Allowed IP
        result = manager.check_permission(
            server="azure-mcp",
            tool="list_vms",
            level=PermissionLevel.EXECUTE,
            context={"ip_address": "10.0.0.1"},
        )
        assert result is True

        # Blocked IP — condition fails, policy skipped, falls to default deny
        result = manager.check_permission(
            server="azure-mcp",
            tool="list_vms",
            level=PermissionLevel.EXECUTE,
            context={"ip_address": "192.168.1.1"},
        )
        assert result is False

    def test_policies_property_returns_copy(self, manager, admin_policy):
        """Test that policies property returns a copy, not the internal dict."""
        manager.add_policy(admin_policy)
        policies_copy = manager.policies
        policies_copy["injected"] = PermissionPolicy(name="injected")

        # Internal state should not be affected
        assert "injected" not in manager.policies
        assert len(manager.policies) == 1

"""
Integration Tests for LDAP AD Operations.

Sprint 114: AD 場景基礎建設 (Phase 32)
Tests ADConfig, ADOperations with mocked LDAP connections.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.mcp.servers.ldap.ad_config import ADConfig
from src.integrations.mcp.servers.ldap.ad_operations import ADOperations, ADOperationResult
from src.integrations.mcp.servers.ldap.client import (
    LDAPClient,
    LDAPConnectionManager,
    LDAPSearchResult,
)


# ---------------------------------------------------------------------------
# ADConfig Tests
# ---------------------------------------------------------------------------


class TestADConfig:
    """Tests for AD-specific configuration."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = ADConfig()
        assert config.server == "localhost"
        assert config.port == 389
        assert config.pool_size == 5
        assert config.operation_timeout == 30
        assert config.user_object_class == "user"
        assert config.group_object_class == "group"
        assert len(config.user_attributes) > 5
        assert "sAMAccountName" in config.user_attributes
        assert "lockoutTime" in config.user_attributes

    def test_from_env(self) -> None:
        """Test configuration from environment variables."""
        env_vars = {
            "LDAP_SERVER": "ad.test.com",
            "LDAP_PORT": "636",
            "LDAP_USE_SSL": "true",
            "LDAP_BASE_DN": "DC=test,DC=com",
            "LDAP_BIND_DN": "CN=svc,OU=SA,DC=test,DC=com",
            "LDAP_BIND_PASSWORD": "secret",
            "LDAP_USER_SEARCH_BASE": "OU=Users,DC=test,DC=com",
            "LDAP_GROUP_SEARCH_BASE": "OU=Groups,DC=test,DC=com",
            "LDAP_POOL_SIZE": "10",
            "LDAP_OPERATION_TIMEOUT": "60",
        }
        with patch.dict("os.environ", env_vars, clear=False):
            config = ADConfig.from_env()

        assert config.server == "ad.test.com"
        assert config.port == 636
        assert config.use_ssl is True
        assert config.base_dn == "DC=test,DC=com"
        assert config.user_search_base == "OU=Users,DC=test,DC=com"
        assert config.group_search_base == "OU=Groups,DC=test,DC=com"
        assert config.pool_size == 10
        assert config.operation_timeout == 60

    def test_validate_missing_server(self) -> None:
        """Test validation catches missing server."""
        config = ADConfig(server="localhost")
        errors = config.validate()
        assert any("LDAP_SERVER" in e for e in errors)

    def test_validate_missing_base_dn(self) -> None:
        """Test validation catches missing base DN."""
        config = ADConfig(server="ad.test.com", base_dn="")
        errors = config.validate()
        assert any("LDAP_BASE_DN" in e for e in errors)

    def test_validate_missing_bind_dn(self) -> None:
        """Test validation catches missing bind DN."""
        config = ADConfig(
            server="ad.test.com",
            base_dn="DC=test,DC=com",
            bind_dn=None,
        )
        errors = config.validate()
        assert any("LDAP_BIND_DN" in e for e in errors)

    def test_validate_invalid_pool_size(self) -> None:
        """Test validation catches invalid pool size."""
        config = ADConfig(
            server="ad.test.com",
            base_dn="DC=test,DC=com",
            bind_dn="CN=svc",
            bind_password="pass",
            pool_size=100,
        )
        errors = config.validate()
        assert any("LDAP_POOL_SIZE" in e for e in errors)

    def test_validate_valid_config(self) -> None:
        """Test validation passes for valid config."""
        config = ADConfig(
            server="ad.test.com",
            base_dn="DC=test,DC=com",
            bind_dn="CN=svc",
            bind_password="pass",
            pool_size=5,
            operation_timeout=30,
        )
        errors = config.validate()
        assert len(errors) == 0


# ---------------------------------------------------------------------------
# ADOperations Tests
# ---------------------------------------------------------------------------


@pytest.fixture
def ad_config() -> ADConfig:
    """Create test AD config."""
    return ADConfig(
        server="ad.test.com",
        port=389,
        base_dn="DC=test,DC=com",
        bind_dn="CN=svc,OU=SA,DC=test,DC=com",
        bind_password="secret",
        user_search_base="OU=Users,DC=test,DC=com",
        group_search_base="OU=Groups,DC=test,DC=com",
        read_only=False,
        allowed_operations=["search", "bind", "modify"],
        use_ssl=True,
    )


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create mock LDAP client."""
    client = AsyncMock(spec=LDAPClient)
    client.is_connected = True
    return client


@pytest.fixture
def mock_conn_manager(mock_client: AsyncMock) -> AsyncMock:
    """Create mock connection manager."""
    manager = AsyncMock(spec=LDAPConnectionManager)
    manager.get_connection.return_value = mock_client
    return manager


@pytest.fixture
def ad_ops(
    mock_conn_manager: AsyncMock, ad_config: ADConfig
) -> ADOperations:
    """Create ADOperations with mock dependencies."""
    return ADOperations(mock_conn_manager, ad_config)


class TestADFindUser:
    """Tests for user lookup."""

    @pytest.mark.asyncio
    async def test_find_user_success(
        self, ad_ops: ADOperations, mock_client: AsyncMock
    ) -> None:
        """Test successful user lookup."""
        mock_client.search.return_value = LDAPSearchResult(
            entries=[
                {
                    "dn": "CN=John Doe,OU=Users,DC=test,DC=com",
                    "attributes": {
                        "sAMAccountName": "john.doe",
                        "displayName": "John Doe",
                        "mail": "john@test.com",
                    },
                }
            ],
            total_count=1,
            search_time=0.05,
        )

        result = await ad_ops.find_user("john.doe")
        assert result is not None
        assert result["dn"] == "CN=John Doe,OU=Users,DC=test,DC=com"
        mock_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_user_not_found(
        self, ad_ops: ADOperations, mock_client: AsyncMock
    ) -> None:
        """Test user not found returns None."""
        mock_client.search.return_value = LDAPSearchResult(
            entries=[], total_count=0, search_time=0.02
        )

        result = await ad_ops.find_user("nonexistent")
        assert result is None


class TestADUnlockAccount:
    """Tests for account unlock."""

    @pytest.mark.asyncio
    async def test_unlock_success(
        self, ad_ops: ADOperations, mock_client: AsyncMock
    ) -> None:
        """Test successful account unlock."""
        mock_client.search.return_value = LDAPSearchResult(
            entries=[{"dn": "CN=John,OU=Users,DC=test,DC=com", "attributes": {}}],
            total_count=1,
            search_time=0.01,
        )
        mock_client.modify_entry.return_value = True

        result = await ad_ops.unlock_account("john.doe")
        assert result.success is True
        assert result.operation == "unlock_account"
        assert "john.doe" in result.message

    @pytest.mark.asyncio
    async def test_unlock_user_not_found(
        self, ad_ops: ADOperations, mock_client: AsyncMock
    ) -> None:
        """Test unlock for non-existent user."""
        mock_client.search.return_value = LDAPSearchResult(
            entries=[], total_count=0, search_time=0.01
        )

        result = await ad_ops.unlock_account("nonexistent")
        assert result.success is False
        assert "not found" in result.message.lower()

    @pytest.mark.asyncio
    async def test_unlock_permission_denied(
        self, ad_ops: ADOperations, mock_client: AsyncMock
    ) -> None:
        """Test unlock when permission is denied."""
        mock_client.search.return_value = LDAPSearchResult(
            entries=[{"dn": "CN=John,OU=Users,DC=test,DC=com", "attributes": {}}],
            total_count=1,
            search_time=0.01,
        )
        mock_client.modify_entry.side_effect = PermissionError("Not allowed")

        result = await ad_ops.unlock_account("john.doe")
        assert result.success is False
        assert "permission" in result.message.lower()


class TestADPasswordReset:
    """Tests for password reset."""

    @pytest.mark.asyncio
    async def test_reset_requires_ssl(self, mock_conn_manager: AsyncMock) -> None:
        """Test password reset rejects non-SSL connection."""
        config = ADConfig(
            server="ad.test.com",
            base_dn="DC=test,DC=com",
            use_ssl=False,
            use_tls=False,
        )
        ops = ADOperations(mock_conn_manager, config)

        result = await ops.reset_password("john.doe", "NewPass123!")
        assert result.success is False
        assert "SSL/TLS" in result.message

    @pytest.mark.asyncio
    async def test_reset_success(
        self, ad_ops: ADOperations, mock_client: AsyncMock
    ) -> None:
        """Test successful password reset."""
        mock_client.search.return_value = LDAPSearchResult(
            entries=[{"dn": "CN=John,OU=Users,DC=test,DC=com", "attributes": {}}],
            total_count=1,
            search_time=0.01,
        )
        mock_client.modify_entry.return_value = True

        result = await ad_ops.reset_password("john.doe", "NewPass123!")
        assert result.success is True
        assert result.operation == "reset_password"


class TestADGroupMembership:
    """Tests for group membership operations."""

    @pytest.mark.asyncio
    async def test_find_group_success(
        self, ad_ops: ADOperations, mock_client: AsyncMock
    ) -> None:
        """Test successful group lookup."""
        mock_client.search.return_value = LDAPSearchResult(
            entries=[
                {
                    "dn": "CN=IT-Admins,OU=Groups,DC=test,DC=com",
                    "attributes": {"cn": "IT-Admins", "member": []},
                }
            ],
            total_count=1,
            search_time=0.02,
        )

        result = await ad_ops.find_group("IT-Admins")
        assert result is not None
        assert result["dn"] == "CN=IT-Admins,OU=Groups,DC=test,DC=com"

    @pytest.mark.asyncio
    async def test_add_to_group_success(
        self, ad_ops: ADOperations, mock_client: AsyncMock
    ) -> None:
        """Test adding user to group."""
        mock_client.search.return_value = LDAPSearchResult(
            entries=[
                {
                    "dn": "CN=IT-Admins,OU=Groups,DC=test,DC=com",
                    "attributes": {"member": []},
                }
            ],
            total_count=1,
            search_time=0.01,
        )
        mock_client.modify_entry.return_value = True

        result = await ad_ops.modify_group_membership(
            "IT-Admins",
            "CN=John,OU=Users,DC=test,DC=com",
            action="add",
        )
        assert result.success is True
        assert "added to" in result.message

    @pytest.mark.asyncio
    async def test_remove_from_group_success(
        self, ad_ops: ADOperations, mock_client: AsyncMock
    ) -> None:
        """Test removing user from group."""
        mock_client.search.return_value = LDAPSearchResult(
            entries=[
                {
                    "dn": "CN=IT-Admins,OU=Groups,DC=test,DC=com",
                    "attributes": {"member": ["CN=John,OU=Users,DC=test,DC=com"]},
                }
            ],
            total_count=1,
            search_time=0.01,
        )
        mock_client.modify_entry.return_value = True

        result = await ad_ops.modify_group_membership(
            "IT-Admins",
            "CN=John,OU=Users,DC=test,DC=com",
            action="remove",
        )
        assert result.success is True
        assert "removed from" in result.message

    @pytest.mark.asyncio
    async def test_invalid_action(self, ad_ops: ADOperations) -> None:
        """Test invalid membership action."""
        result = await ad_ops.modify_group_membership(
            "IT-Admins", "CN=John", action="invalid"
        )
        assert result.success is False
        assert "Invalid action" in result.message

    @pytest.mark.asyncio
    async def test_group_not_found(
        self, ad_ops: ADOperations, mock_client: AsyncMock
    ) -> None:
        """Test membership change on non-existent group."""
        mock_client.search.return_value = LDAPSearchResult(
            entries=[], total_count=0, search_time=0.01
        )

        result = await ad_ops.modify_group_membership(
            "NonExistent",
            "CN=John,OU=Users,DC=test,DC=com",
            action="add",
        )
        assert result.success is False
        assert "not found" in result.message.lower()


class TestADGetGroupMembers:
    """Tests for group member listing."""

    @pytest.mark.asyncio
    async def test_get_members_success(
        self, ad_ops: ADOperations, mock_client: AsyncMock
    ) -> None:
        """Test successful group member listing."""
        mock_client.search.return_value = LDAPSearchResult(
            entries=[
                {
                    "dn": "CN=IT-Admins,OU=Groups,DC=test,DC=com",
                    "attributes": {
                        "member": [
                            "CN=John,OU=Users,DC=test,DC=com",
                            "CN=Jane,OU=Users,DC=test,DC=com",
                        ]
                    },
                }
            ],
            total_count=1,
            search_time=0.01,
        )

        result = await ad_ops.get_group_members("IT-Admins")
        assert result.success is True
        assert result.details["count"] == 2
        assert len(result.details["members"]) == 2

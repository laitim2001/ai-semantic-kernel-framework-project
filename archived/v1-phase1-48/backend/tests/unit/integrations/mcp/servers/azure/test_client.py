"""Tests for Azure client manager.

Tests AzureConfig and AzureClientManager components.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from src.integrations.mcp.servers.azure.client import AzureConfig, AzureClientManager


class TestAzureConfig:
    """Tests for AzureConfig dataclass."""

    def test_from_env_with_required_vars(self):
        """Test config creation from environment variables."""
        with patch.dict(os.environ, {
            "AZURE_SUBSCRIPTION_ID": "test-sub-id",
            "AZURE_TENANT_ID": "test-tenant-id",
            "AZURE_CLIENT_ID": "test-client-id",
            "AZURE_CLIENT_SECRET": "test-secret",
        }):
            config = AzureConfig.from_env()
            assert config.subscription_id == "test-sub-id"
            assert config.tenant_id == "test-tenant-id"
            assert config.client_id == "test-client-id"
            assert config.client_secret == "test-secret"

    def test_from_env_missing_subscription_id_raises_error(self):
        """Test that missing subscription ID raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove AZURE_SUBSCRIPTION_ID if exists
            os.environ.pop("AZURE_SUBSCRIPTION_ID", None)
            with pytest.raises(ValueError, match="AZURE_SUBSCRIPTION_ID"):
                AzureConfig.from_env()

    def test_config_with_optional_fields(self):
        """Test config with optional fields."""
        config = AzureConfig(
            subscription_id="sub-123",
            tenant_id="tenant-456",
            resource_group="rg-test",
            location="eastus",
        )
        assert config.subscription_id == "sub-123"
        assert config.tenant_id == "tenant-456"
        assert config.resource_group == "rg-test"
        assert config.location == "eastus"
        assert config.client_id is None
        assert config.client_secret is None


class TestAzureClientManager:
    """Tests for AzureClientManager."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        return AzureConfig(subscription_id="test-subscription")

    @pytest.fixture
    def manager(self, config):
        """Create test manager."""
        return AzureClientManager(config)

    def test_manager_initialization(self, manager, config):
        """Test manager initializes correctly."""
        assert manager._config == config
        assert manager._credential is not None
        assert manager._compute_client is None  # Lazy loaded
        assert manager._resource_client is None
        assert manager._network_client is None
        assert manager._monitor_client is None
        assert manager._storage_client is None

    @patch("src.integrations.mcp.servers.azure.client.ComputeManagementClient")
    def test_compute_client_lazy_loading(self, mock_compute_class, manager):
        """Test compute client is lazily loaded."""
        mock_client = MagicMock()
        mock_compute_class.return_value = mock_client

        # First access creates client
        client1 = manager.compute
        assert mock_compute_class.called
        assert client1 == mock_client

        # Second access returns cached client
        mock_compute_class.reset_mock()
        client2 = manager.compute
        assert not mock_compute_class.called
        assert client1 == client2

    @patch("src.integrations.mcp.servers.azure.client.ResourceManagementClient")
    def test_resource_client_lazy_loading(self, mock_resource_class, manager):
        """Test resource client is lazily loaded."""
        mock_client = MagicMock()
        mock_resource_class.return_value = mock_client

        client = manager.resource
        assert mock_resource_class.called
        assert client == mock_client

    @patch("src.integrations.mcp.servers.azure.client.NetworkManagementClient")
    def test_network_client_lazy_loading(self, mock_network_class, manager):
        """Test network client is lazily loaded."""
        mock_client = MagicMock()
        mock_network_class.return_value = mock_client

        client = manager.network
        assert mock_network_class.called
        assert client == mock_client

    @patch("src.integrations.mcp.servers.azure.client.MonitorManagementClient")
    def test_monitor_client_lazy_loading(self, mock_monitor_class, manager):
        """Test monitor client is lazily loaded."""
        mock_client = MagicMock()
        mock_monitor_class.return_value = mock_client

        client = manager.monitor
        assert mock_monitor_class.called
        assert client == mock_client

    @patch("src.integrations.mcp.servers.azure.client.StorageManagementClient")
    def test_storage_client_lazy_loading(self, mock_storage_class, manager):
        """Test storage client is lazily loaded."""
        mock_client = MagicMock()
        mock_storage_class.return_value = mock_client

        client = manager.storage
        assert mock_storage_class.called
        assert client == mock_client

    def test_close_cleans_up_clients(self, manager):
        """Test close method cleans up all clients."""
        # Create mock clients
        manager._compute_client = MagicMock()
        manager._resource_client = MagicMock()
        manager._network_client = MagicMock()
        manager._monitor_client = MagicMock()
        manager._storage_client = MagicMock()

        manager.close()

        # Verify all clients are closed
        manager._compute_client.close.assert_called_once()
        manager._resource_client.close.assert_called_once()
        manager._network_client.close.assert_called_once()
        manager._monitor_client.close.assert_called_once()
        manager._storage_client.close.assert_called_once()

    def test_context_manager_support(self, config):
        """Test context manager support."""
        with patch.object(AzureClientManager, 'close') as mock_close:
            with AzureClientManager(config) as manager:
                assert isinstance(manager, AzureClientManager)
            mock_close.assert_called_once()

# =============================================================================
# IPA Platform - Connector Unit Tests
# =============================================================================
# Sprint 2: Workflow & Checkpoints - Cross-System Integration
#
# Tests for the connector infrastructure including:
#   - ConnectorConfig data structure
#   - ConnectorResponse data structure
#   - BaseConnector abstract class
#   - ServiceNowConnector implementation
#   - Dynamics365Connector implementation
#   - SharePointConnector implementation
#   - ConnectorRegistry management
# =============================================================================

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.domain.connectors.base import (
    AuthType,
    BaseConnector,
    ConnectorConfig,
    ConnectorError,
    ConnectorResponse,
    ConnectorStatus,
)
from src.domain.connectors.registry import (
    ConnectorRegistry,
    get_default_registry,
    reset_default_registry,
)
from src.domain.connectors.servicenow import ServiceNowConnector
from src.domain.connectors.dynamics365 import Dynamics365Connector
from src.domain.connectors.sharepoint import SharePointConnector


# =============================================================================
# AuthType Tests
# =============================================================================


class TestAuthType:
    """Tests for AuthType enum."""

    def test_auth_type_values(self):
        """Test all auth type enum values."""
        assert AuthType.NONE.value == "none"
        assert AuthType.API_KEY.value == "api_key"
        assert AuthType.BASIC.value == "basic"
        assert AuthType.OAUTH2.value == "oauth2"
        assert AuthType.OAUTH2_CODE.value == "oauth2_code"
        assert AuthType.CERTIFICATE.value == "certificate"

    def test_auth_type_from_string(self):
        """Test creating auth type from string."""
        assert AuthType("none") == AuthType.NONE
        assert AuthType("basic") == AuthType.BASIC
        assert AuthType("oauth2") == AuthType.OAUTH2


# =============================================================================
# ConnectorStatus Tests
# =============================================================================


class TestConnectorStatus:
    """Tests for ConnectorStatus enum."""

    def test_status_values(self):
        """Test all status enum values."""
        assert ConnectorStatus.DISCONNECTED.value == "disconnected"
        assert ConnectorStatus.CONNECTING.value == "connecting"
        assert ConnectorStatus.CONNECTED.value == "connected"
        assert ConnectorStatus.ERROR.value == "error"
        assert ConnectorStatus.RATE_LIMITED.value == "rate_limited"


# =============================================================================
# ConnectorConfig Tests
# =============================================================================


class TestConnectorConfig:
    """Tests for ConnectorConfig dataclass."""

    def test_initialization_minimal(self):
        """Test minimal initialization."""
        config = ConnectorConfig(
            name="test-connector",
            connector_type="servicenow",
            base_url="https://example.service-now.com",
        )

        assert config.name == "test-connector"
        assert config.connector_type == "servicenow"
        assert config.base_url == "https://example.service-now.com"
        assert config.auth_type == AuthType.NONE
        assert config.timeout_seconds == 30
        assert config.enabled is True

    def test_initialization_full(self):
        """Test full initialization."""
        config = ConnectorConfig(
            name="prod-snow",
            connector_type="servicenow",
            base_url="https://company.service-now.com",
            auth_type=AuthType.BASIC,
            credentials={"username": "api_user", "password": "secret"},
            timeout_seconds=60,
            retry_count=5,
            retry_delay_seconds=2.0,
            headers={"X-Custom": "value"},
            options={"feature": True},
            enabled=True,
        )

        assert config.auth_type == AuthType.BASIC
        assert config.credentials["username"] == "api_user"
        assert config.timeout_seconds == 60
        assert config.retry_count == 5
        assert config.headers["X-Custom"] == "value"

    def test_to_dict_masks_credentials(self):
        """Test that to_dict masks credentials."""
        config = ConnectorConfig(
            name="test",
            connector_type="servicenow",
            base_url="https://example.com",
            credentials={"password": "secret123"},
        )

        result = config.to_dict()

        assert "password" not in str(result)
        assert result["has_credentials"] is True
        assert "credentials" not in result

    def test_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "name": "test",
            "connector_type": "servicenow",
            "base_url": "https://example.com",
            "auth_type": "basic",
            "credentials": {"username": "user"},
            "timeout_seconds": 45,
        }

        config = ConnectorConfig.from_dict(data)

        assert config.name == "test"
        assert config.auth_type == AuthType.BASIC
        assert config.timeout_seconds == 45


# =============================================================================
# ConnectorResponse Tests
# =============================================================================


class TestConnectorResponse:
    """Tests for ConnectorResponse dataclass."""

    def test_success_response(self):
        """Test successful response."""
        response = ConnectorResponse(
            success=True,
            data={"incident_id": "INC001"},
        )

        assert response.success is True
        assert response.data["incident_id"] == "INC001"
        assert response.error is None
        assert response.timestamp is not None

    def test_error_response(self):
        """Test error response."""
        response = ConnectorResponse(
            success=False,
            error="Connection failed",
            error_code="CONNECTION_FAILED",
        )

        assert response.success is False
        assert response.error == "Connection failed"
        assert response.error_code == "CONNECTION_FAILED"

    def test_to_dict(self):
        """Test serialization to dictionary."""
        response = ConnectorResponse(
            success=True,
            data={"key": "value"},
            metadata={"request_id": "abc"},
        )

        result = response.to_dict()

        assert result["success"] is True
        assert result["data"]["key"] == "value"
        assert result["metadata"]["request_id"] == "abc"
        assert "timestamp" in result

    def test_str_representation(self):
        """Test string representation."""
        success_response = ConnectorResponse(success=True, data={"x": 1})
        error_response = ConnectorResponse(success=False, error="Failed")

        assert "success=True" in str(success_response)
        assert "success=False" in str(error_response)


# =============================================================================
# ConnectorError Tests
# =============================================================================


class TestConnectorError:
    """Tests for ConnectorError exception."""

    def test_initialization(self):
        """Test error initialization."""
        error = ConnectorError(
            message="Operation failed",
            connector_name="servicenow",
            operation="get_incident",
            error_code="NOT_FOUND",
            retryable=False,
        )

        assert error.message == "Operation failed"
        assert error.connector_name == "servicenow"
        assert error.operation == "get_incident"
        assert error.error_code == "NOT_FOUND"
        assert error.retryable is False

    def test_to_response(self):
        """Test converting error to response."""
        error = ConnectorError(
            message="Auth failed",
            connector_name="servicenow",
            error_code="AUTH_FAILED",
        )

        response = error.to_response()

        assert response.success is False
        assert response.error == "Auth failed"
        assert response.error_code == "AUTH_FAILED"


# =============================================================================
# ServiceNowConnector Tests
# =============================================================================


class TestServiceNowConnector:
    """Tests for ServiceNowConnector."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return ConnectorConfig(
            name="test-snow",
            connector_type="servicenow",
            base_url="https://test.service-now.com",
            auth_type=AuthType.BASIC,
            credentials={"username": "api_user", "password": "secret"},
        )

    @pytest.fixture
    def connector(self, config):
        """Create connector instance."""
        return ServiceNowConnector(config)

    def test_initialization(self, connector):
        """Test connector initialization."""
        assert connector.name == "servicenow"
        assert connector.description != ""
        assert connector.status == ConnectorStatus.DISCONNECTED
        assert "get_incident" in connector.supported_operations
        assert "list_incidents" in connector.supported_operations

    def test_supported_operations(self, connector):
        """Test supported operations list."""
        ops = connector.supported_operations

        assert "get_incident" in ops
        assert "list_incidents" in ops
        assert "create_incident" in ops
        assert "update_incident" in ops
        assert "get_change" in ops
        assert "search_knowledge" in ops
        assert "health_check" in ops

    @pytest.mark.asyncio
    async def test_connect_success(self, connector):
        """Test successful connection."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"result": []}
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            await connector.connect()

            assert connector.status == ConnectorStatus.CONNECTED
            assert connector.is_connected is True

    @pytest.mark.asyncio
    async def test_connect_auth_failure(self, connector):
        """Test connection with auth failure."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            with pytest.raises(ConnectorError) as exc:
                await connector.connect()

            assert "Authentication failed" in str(exc.value)
            assert connector.status == ConnectorStatus.CONNECTING

    @pytest.mark.asyncio
    async def test_disconnect(self, connector):
        """Test disconnection."""
        connector._status = ConnectorStatus.CONNECTED
        connector._client = AsyncMock()

        await connector.disconnect()

        assert connector.status == ConnectorStatus.DISCONNECTED
        assert connector._client is None

    @pytest.mark.asyncio
    async def test_execute_unsupported_operation(self, connector):
        """Test executing unsupported operation."""
        connector._status = ConnectorStatus.CONNECTED

        with pytest.raises(ConnectorError) as exc:
            await connector.execute("unsupported_op")

        assert "Unsupported operation" in str(exc.value)

    def test_get_stats(self, connector):
        """Test getting connector statistics."""
        connector._request_count = 10
        connector._error_count = 2

        stats = connector.get_stats()

        assert stats["name"] == "servicenow"
        assert stats["request_count"] == 10
        assert stats["error_count"] == 2
        assert "status" in stats

    def test_get_info(self, connector):
        """Test getting connector info."""
        info = connector.get_info()

        assert info["name"] == "servicenow"
        assert "description" in info
        assert "config" in info
        assert "supported_operations" in info


# =============================================================================
# Dynamics365Connector Tests
# =============================================================================


class TestDynamics365Connector:
    """Tests for Dynamics365Connector."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return ConnectorConfig(
            name="test-d365",
            connector_type="dynamics365",
            base_url="https://test.crm.dynamics.com",
            auth_type=AuthType.OAUTH2,
            credentials={
                "tenant_id": "test-tenant",
                "client_id": "test-client",
                "client_secret": "test-secret",
            },
        )

    @pytest.fixture
    def connector(self, config):
        """Create connector instance."""
        return Dynamics365Connector(config)

    def test_initialization(self, connector):
        """Test connector initialization."""
        assert connector.name == "dynamics365"
        assert connector.status == ConnectorStatus.DISCONNECTED
        assert "get_customer" in connector.supported_operations
        assert "get_case" in connector.supported_operations

    def test_supported_operations(self, connector):
        """Test supported operations list."""
        ops = connector.supported_operations

        assert "get_customer" in ops
        assert "list_customers" in ops
        assert "search_customers" in ops
        assert "get_case" in ops
        assert "list_cases" in ops
        assert "create_case" in ops
        assert "get_contact" in ops
        assert "get_account" in ops

    @pytest.mark.asyncio
    async def test_disconnect(self, connector):
        """Test disconnection."""
        connector._status = ConnectorStatus.CONNECTED
        connector._client = AsyncMock()
        connector._access_token = "token"

        await connector.disconnect()

        assert connector.status == ConnectorStatus.DISCONNECTED
        assert connector._access_token is None


# =============================================================================
# SharePointConnector Tests
# =============================================================================


class TestSharePointConnector:
    """Tests for SharePointConnector."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return ConnectorConfig(
            name="test-sp",
            connector_type="sharepoint",
            base_url="https://test.sharepoint.com/sites/mysite",
            auth_type=AuthType.OAUTH2,
            credentials={
                "tenant_id": "test-tenant",
                "client_id": "test-client",
                "client_secret": "test-secret",
            },
        )

    @pytest.fixture
    def connector(self, config):
        """Create connector instance."""
        return SharePointConnector(config)

    def test_initialization(self, connector):
        """Test connector initialization."""
        assert connector.name == "sharepoint"
        assert connector.status == ConnectorStatus.DISCONNECTED
        assert "list_documents" in connector.supported_operations
        assert "search_documents" in connector.supported_operations

    def test_supported_operations(self, connector):
        """Test supported operations list."""
        ops = connector.supported_operations

        assert "list_documents" in ops
        assert "get_document" in ops
        assert "search_documents" in ops
        assert "download_document" in ops
        assert "upload_document" in ops
        assert "list_sites" in ops
        assert "list_lists" in ops

    @pytest.mark.asyncio
    async def test_disconnect(self, connector):
        """Test disconnection."""
        connector._status = ConnectorStatus.CONNECTED
        connector._client = AsyncMock()
        connector._site_id = "site-123"

        await connector.disconnect()

        assert connector.status == ConnectorStatus.DISCONNECTED
        assert connector._site_id is None


# =============================================================================
# ConnectorRegistry Tests
# =============================================================================


class TestConnectorRegistry:
    """Tests for ConnectorRegistry."""

    @pytest.fixture
    def registry(self):
        """Create fresh registry."""
        return ConnectorRegistry()

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return ConnectorConfig(
            name="test-connector",
            connector_type="servicenow",
            base_url="https://test.service-now.com",
        )

    def test_initialization(self, registry):
        """Test registry initialization."""
        assert len(registry) == 0
        types = registry.list_types()
        assert "servicenow" in types
        assert "dynamics365" in types
        assert "sharepoint" in types

    def test_register_from_config(self, registry, config):
        """Test registering connector from config."""
        connector = registry.register_from_config(config)

        assert connector is not None
        assert "test-connector" in registry
        assert len(registry) == 1

    def test_register_duplicate_raises(self, registry, config):
        """Test registering duplicate name raises error."""
        registry.register_from_config(config)

        with pytest.raises(ValueError) as exc:
            registry.register_from_config(config)

        assert "already registered" in str(exc.value)

    def test_register_unknown_type_raises(self, registry):
        """Test registering unknown type raises error."""
        config = ConnectorConfig(
            name="test",
            connector_type="unknown_type",
            base_url="https://example.com",
        )

        with pytest.raises(ValueError) as exc:
            registry.register_from_config(config)

        assert "Unknown connector type" in str(exc.value)

    def test_get_connector(self, registry, config):
        """Test getting connector by name."""
        registry.register_from_config(config)

        connector = registry.get("test-connector")
        assert connector is not None
        assert connector.name == "servicenow"

        missing = registry.get("nonexistent")
        assert missing is None

    def test_get_or_raise(self, registry, config):
        """Test get_or_raise method."""
        registry.register_from_config(config)

        connector = registry.get_or_raise("test-connector")
        assert connector is not None

        with pytest.raises(ValueError):
            registry.get_or_raise("nonexistent")

    def test_unregister(self, registry, config):
        """Test unregistering connector."""
        registry.register_from_config(config)
        assert "test-connector" in registry

        result = registry.unregister("test-connector")
        assert result is True
        assert "test-connector" not in registry

        result = registry.unregister("nonexistent")
        assert result is False

    def test_list_connectors(self, registry, config):
        """Test listing connector names."""
        config2 = ConnectorConfig(
            name="test-2",
            connector_type="dynamics365",
            base_url="https://test.crm.dynamics.com",
        )

        registry.register_from_config(config)
        registry.register_from_config(config2)

        names = registry.list_connectors()
        assert "test-connector" in names
        assert "test-2" in names

    def test_get_by_type(self, registry, config):
        """Test getting connectors by type."""
        config2 = ConnectorConfig(
            name="test-snow-2",
            connector_type="servicenow",
            base_url="https://test2.service-now.com",
        )

        registry.register_from_config(config)
        registry.register_from_config(config2)

        snow_connectors = registry.get_by_type("servicenow")
        assert len(snow_connectors) == 2

    def test_get_all_info(self, registry, config):
        """Test getting all connector info."""
        registry.register_from_config(config)

        all_info = registry.get_all_info()
        assert len(all_info) == 1
        assert all_info[0]["name"] == "servicenow"

    def test_get_all_stats(self, registry, config):
        """Test getting all connector stats."""
        registry.register_from_config(config)

        all_stats = registry.get_all_stats()
        assert len(all_stats) == 1
        assert "request_count" in all_stats[0]

    @pytest.mark.asyncio
    async def test_connect_all(self, registry, config):
        """Test connecting all connectors."""
        connector = registry.register_from_config(config)

        with patch.object(connector, "connect", new_callable=AsyncMock) as mock_connect:
            results = await registry.connect_all()

            assert "test-connector" in results
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_all(self, registry, config):
        """Test disconnecting all connectors."""
        connector = registry.register_from_config(config)
        connector._status = ConnectorStatus.CONNECTED
        connector._client = AsyncMock()

        with patch.object(connector, "disconnect", new_callable=AsyncMock) as mock_disconnect:
            await registry.disconnect_all()

            mock_disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_all(self, registry, config):
        """Test health checking all connectors."""
        connector = registry.register_from_config(config)
        connector._status = ConnectorStatus.CONNECTED

        mock_response = ConnectorResponse(
            success=True,
            data={"status": "healthy", "latency_ms": 50},
        )

        with patch.object(connector, "health_check", new_callable=AsyncMock) as mock_health:
            mock_health.return_value = mock_response

            results = await registry.health_check_all()

            assert "test-connector" in results
            assert results["test-connector"].success is True

    def test_get_health_summary(self, registry):
        """Test generating health summary."""
        health_results = {
            "connector1": ConnectorResponse(
                success=True,
                data={"status": "healthy", "latency_ms": 50},
            ),
            "connector2": ConnectorResponse(
                success=False,
                error="Connection failed",
                data={"status": "unhealthy"},
            ),
        }

        summary = registry.get_health_summary(health_results)

        assert summary["total_connectors"] == 2
        assert summary["healthy_count"] == 1
        assert summary["unhealthy_count"] == 1
        assert summary["status"] == "degraded"

    def test_update_config(self, registry, config):
        """Test updating connector configuration."""
        registry.register_from_config(config)

        result = registry.update_config("test-connector", timeout_seconds=60)
        assert result is True

        connector = registry.get("test-connector")
        assert connector.config.timeout_seconds == 60

    def test_contains(self, registry, config):
        """Test __contains__ method."""
        registry.register_from_config(config)

        assert "test-connector" in registry
        assert "nonexistent" not in registry

    def test_iter(self, registry, config):
        """Test __iter__ method."""
        registry.register_from_config(config)

        names = list(registry)
        assert "test-connector" in names


# =============================================================================
# Default Registry Tests
# =============================================================================


class TestDefaultRegistry:
    """Tests for default registry functions."""

    def teardown_method(self):
        """Reset default registry after each test."""
        reset_default_registry()

    def test_get_default_registry(self):
        """Test getting default registry."""
        registry1 = get_default_registry()
        registry2 = get_default_registry()

        assert registry1 is registry2  # Same instance

    def test_reset_default_registry(self):
        """Test resetting default registry."""
        registry1 = get_default_registry()
        reset_default_registry()
        registry2 = get_default_registry()

        assert registry1 is not registry2


# =============================================================================
# Integration Scenario Tests
# =============================================================================


class TestConnectorScenarios:
    """Tests for complete connector usage scenarios."""

    @pytest.fixture
    def registry(self):
        """Create registry with connectors."""
        reg = ConnectorRegistry()

        reg.register_from_config(ConnectorConfig(
            name="snow-prod",
            connector_type="servicenow",
            base_url="https://prod.service-now.com",
            auth_type=AuthType.BASIC,
            credentials={"username": "api", "password": "secret"},
        ))

        reg.register_from_config(ConnectorConfig(
            name="d365-prod",
            connector_type="dynamics365",
            base_url="https://prod.crm.dynamics.com",
            auth_type=AuthType.OAUTH2,
            credentials={
                "tenant_id": "tenant",
                "client_id": "client",
                "client_secret": "secret",
            },
        ))

        return reg

    def test_multi_connector_setup(self, registry):
        """Test setting up multiple connectors."""
        assert len(registry) == 2
        assert "snow-prod" in registry
        assert "d365-prod" in registry

    def test_get_connectors_by_type(self, registry):
        """Test getting connectors by type."""
        snow = registry.get_by_type("servicenow")
        d365 = registry.get_by_type("dynamics365")

        assert len(snow) == 1
        assert len(d365) == 1

    @pytest.mark.asyncio
    async def test_connector_call_pattern(self, registry):
        """Test the connector call pattern."""
        connector = registry.get("snow-prod")

        # Mock the internal methods
        with patch.object(connector, "connect", new_callable=AsyncMock), \
             patch.object(connector, "execute", new_callable=AsyncMock) as mock_execute:

            mock_execute.return_value = ConnectorResponse(
                success=True,
                data={"incident_id": "INC001"},
            )

            # Use __call__ which handles connection
            result = await connector("get_incident", sys_id="abc123")

            assert result.success is True
            mock_execute.assert_called_once_with("get_incident", sys_id="abc123")

    def test_disabled_connector(self, registry):
        """Test handling disabled connector."""
        registry.update_config("snow-prod", enabled=False)

        connector = registry.get("snow-prod")
        assert connector.config.enabled is False

# =============================================================================
# IPA Platform - Connector Registry
# =============================================================================
# Sprint 2: Workflow & Checkpoints - Cross-System Integration
#
# Central registry for managing connector instances.
# Provides:
#   - ConnectorRegistry: Register, retrieve, and manage connectors
#   - Dynamic connector loading and configuration
#   - Health check aggregation
#   - Connector discovery and enumeration
#
# Usage:
#   registry = ConnectorRegistry()
#
#   # Register connectors
#   registry.register(ServiceNowConnector(config1))
#   registry.register(Dynamics365Connector(config2))
#
#   # Get connector by name
#   snow = registry.get("servicenow")
#   result = await snow.execute("get_incident", sys_id="xxx")
#
#   # Health check all connectors
#   health = await registry.health_check_all()
# =============================================================================

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

from src.domain.connectors.base import (
    BaseConnector,
    ConnectorConfig,
    ConnectorError,
    ConnectorResponse,
    ConnectorStatus,
)

logger = logging.getLogger(__name__)


class ConnectorRegistry:
    """
    Central registry for managing connector instances.

    Provides:
        - Connector registration and retrieval
        - Configuration-based connector instantiation
        - Health check aggregation
        - Connector enumeration and discovery

    Thread Safety:
        The registry is NOT thread-safe. For concurrent access,
        use external synchronization or create separate instances.

    Example:
        registry = ConnectorRegistry()

        # Register from config
        registry.register_from_config(ConnectorConfig(
            name="prod-snow",
            connector_type="servicenow",
            base_url="https://company.service-now.com",
            auth_type=AuthType.BASIC,
            credentials={"username": "api", "password": "secret"},
        ))

        # Get and use connector
        snow = registry.get("prod-snow")
        result = await snow("get_incident", sys_id="INC001")

        # Health check all
        health = await registry.health_check_all()
    """

    # Mapping of connector type names to classes
    _connector_classes: Dict[str, Type[BaseConnector]] = {}

    def __init__(self):
        """Initialize empty registry."""
        self._connectors: Dict[str, BaseConnector] = {}
        self._configs: Dict[str, ConnectorConfig] = {}

        # Register built-in connector types
        self._register_builtin_types()

    def _register_builtin_types(self) -> None:
        """Register built-in connector types."""
        from src.domain.connectors.dynamics365 import Dynamics365Connector
        from src.domain.connectors.servicenow import ServiceNowConnector
        from src.domain.connectors.sharepoint import SharePointConnector

        self._connector_classes = {
            "servicenow": ServiceNowConnector,
            "dynamics365": Dynamics365Connector,
            "sharepoint": SharePointConnector,
        }

    @classmethod
    def register_type(cls, name: str, connector_class: Type[BaseConnector]) -> None:
        """
        Register a new connector type.

        Args:
            name: Type name (e.g., "custom_erp")
            connector_class: Connector class to register

        Example:
            ConnectorRegistry.register_type("custom_erp", CustomERPConnector)
        """
        cls._connector_classes[name] = connector_class
        logger.info(f"Registered connector type: {name}")

    def register(self, connector: BaseConnector) -> None:
        """
        Register a connector instance.

        Args:
            connector: Initialized connector instance

        Raises:
            ValueError: If connector with same name already registered
        """
        name = connector.config.name

        if name in self._connectors:
            raise ValueError(f"Connector already registered: {name}")

        self._connectors[name] = connector
        self._configs[name] = connector.config
        logger.info(f"Registered connector: {name} ({connector.name})")

    def register_from_config(self, config: ConnectorConfig) -> BaseConnector:
        """
        Create and register connector from configuration.

        Args:
            config: ConnectorConfig with settings

        Returns:
            Created connector instance

        Raises:
            ValueError: If connector type unknown or already registered
        """
        if config.name in self._connectors:
            raise ValueError(f"Connector already registered: {config.name}")

        connector_type = config.connector_type.lower()
        if connector_type not in self._connector_classes:
            raise ValueError(f"Unknown connector type: {connector_type}")

        connector_class = self._connector_classes[connector_type]
        connector = connector_class(config)

        self._connectors[config.name] = connector
        self._configs[config.name] = config
        logger.info(f"Registered connector from config: {config.name}")

        return connector

    def unregister(self, name: str) -> bool:
        """
        Unregister and disconnect a connector.

        Args:
            name: Connector name

        Returns:
            True if unregistered, False if not found
        """
        if name not in self._connectors:
            return False

        connector = self._connectors[name]

        # Disconnect if connected (sync context - caller should handle async)
        if connector.is_connected:
            logger.warning(
                f"Unregistering connected connector: {name}. "
                "Caller should await disconnect() first."
            )

        del self._connectors[name]
        del self._configs[name]
        logger.info(f"Unregistered connector: {name}")
        return True

    def get(self, name: str) -> Optional[BaseConnector]:
        """
        Get connector by name.

        Args:
            name: Connector name

        Returns:
            Connector instance or None if not found
        """
        return self._connectors.get(name)

    def get_or_raise(self, name: str) -> BaseConnector:
        """
        Get connector by name or raise error.

        Args:
            name: Connector name

        Returns:
            Connector instance

        Raises:
            ValueError: If connector not found
        """
        connector = self._connectors.get(name)
        if connector is None:
            raise ValueError(f"Connector not found: {name}")
        return connector

    def get_by_type(self, connector_type: str) -> List[BaseConnector]:
        """
        Get all connectors of a specific type.

        Args:
            connector_type: Type name (e.g., "servicenow")

        Returns:
            List of matching connectors
        """
        return [
            c for c in self._connectors.values()
            if c.name == connector_type.lower()
        ]

    def list_connectors(self) -> List[str]:
        """
        List all registered connector names.

        Returns:
            List of connector names
        """
        return list(self._connectors.keys())

    def list_types(self) -> List[str]:
        """
        List all available connector types.

        Returns:
            List of connector type names
        """
        return list(self._connector_classes.keys())

    def get_all_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all registered connectors.

        Returns:
            List of connector info dictionaries
        """
        return [c.get_info() for c in self._connectors.values()]

    def get_all_stats(self) -> List[Dict[str, Any]]:
        """
        Get statistics for all registered connectors.

        Returns:
            List of connector stats dictionaries
        """
        return [c.get_stats() for c in self._connectors.values()]

    async def connect_all(self) -> Dict[str, bool]:
        """
        Connect all enabled connectors.

        Returns:
            Dictionary mapping connector names to success status
        """
        results = {}

        for name, connector in self._connectors.items():
            if not connector.config.enabled:
                results[name] = False
                continue

            try:
                await connector.connect()
                results[name] = True
                logger.info(f"Connected: {name}")
            except ConnectorError as e:
                results[name] = False
                logger.error(f"Failed to connect {name}: {e.message}")
            except Exception as e:
                results[name] = False
                logger.error(f"Failed to connect {name}: {e}")

        return results

    async def disconnect_all(self) -> None:
        """Disconnect all connectors."""
        for name, connector in self._connectors.items():
            if connector.is_connected:
                try:
                    await connector.disconnect()
                    logger.info(f"Disconnected: {name}")
                except Exception as e:
                    logger.error(f"Error disconnecting {name}: {e}")

    async def health_check_all(self) -> Dict[str, ConnectorResponse]:
        """
        Run health check on all connected connectors.

        Returns:
            Dictionary mapping connector names to health responses
        """
        results = {}

        for name, connector in self._connectors.items():
            if not connector.config.enabled:
                results[name] = ConnectorResponse(
                    success=False,
                    error="Connector disabled",
                    error_code="DISABLED",
                    data={"status": "disabled"},
                )
                continue

            if not connector.is_connected:
                results[name] = ConnectorResponse(
                    success=False,
                    error="Connector not connected",
                    error_code="NOT_CONNECTED",
                    data={"status": "disconnected"},
                )
                continue

            try:
                results[name] = await connector.health_check()
            except Exception as e:
                results[name] = ConnectorResponse(
                    success=False,
                    error=str(e),
                    error_code="HEALTH_CHECK_ERROR",
                    data={"status": "error"},
                )

        return results

    def get_health_summary(self, health_results: Dict[str, ConnectorResponse]) -> Dict[str, Any]:
        """
        Generate summary from health check results.

        Args:
            health_results: Results from health_check_all()

        Returns:
            Summary dictionary with counts and status
        """
        total = len(health_results)
        healthy = sum(1 for r in health_results.values() if r.success)
        unhealthy = total - healthy

        status = "healthy" if unhealthy == 0 else "degraded" if healthy > 0 else "unhealthy"

        return {
            "status": status,
            "total_connectors": total,
            "healthy_count": healthy,
            "unhealthy_count": unhealthy,
            "timestamp": datetime.utcnow().isoformat(),
            "connectors": {
                name: {
                    "status": resp.data.get("status", "unknown") if resp.data else "unknown",
                    "latency_ms": resp.data.get("latency_ms") if resp.data else None,
                    "error": resp.error,
                }
                for name, resp in health_results.items()
            },
        }

    def update_config(self, name: str, **updates) -> bool:
        """
        Update connector configuration.

        Note: Changes take effect after reconnecting.

        Args:
            name: Connector name
            **updates: Config fields to update

        Returns:
            True if updated, False if not found
        """
        if name not in self._configs:
            return False

        config = self._configs[name]

        for field, value in updates.items():
            if hasattr(config, field):
                setattr(config, field, value)

        logger.info(f"Updated config for {name}: {list(updates.keys())}")
        return True

    def __len__(self) -> int:
        """Return number of registered connectors."""
        return len(self._connectors)

    def __contains__(self, name: str) -> bool:
        """Check if connector is registered."""
        return name in self._connectors

    def __iter__(self):
        """Iterate over connector names."""
        return iter(self._connectors)

    def __repr__(self) -> str:
        return f"<ConnectorRegistry(connectors={len(self._connectors)})>"


# Global registry instance (optional singleton pattern)
_default_registry: Optional[ConnectorRegistry] = None


def get_default_registry() -> ConnectorRegistry:
    """
    Get the default global registry.

    Returns:
        Default ConnectorRegistry instance
    """
    global _default_registry
    if _default_registry is None:
        _default_registry = ConnectorRegistry()
    return _default_registry


def reset_default_registry() -> None:
    """Reset the default global registry."""
    global _default_registry
    _default_registry = None

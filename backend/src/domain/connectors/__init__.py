# =============================================================================
# IPA Platform - Connectors Domain Module
# =============================================================================
# Sprint 2: Workflow & Checkpoints - Cross-System Integration
#
# Enterprise connector framework for external system integration.
# Provides:
#   - BaseConnector: Abstract base class for all connectors
#   - ConnectorConfig: Configuration data structure
#   - ConnectorResponse: Standard response format
#   - ConnectorRegistry: Connector management and discovery
#   - ServiceNowConnector: ServiceNow ITSM integration
#   - Dynamics365Connector: Microsoft Dynamics 365 CRM integration
#   - SharePointConnector: Microsoft SharePoint document integration
#
# Usage:
#   from src.domain.connectors import (
#       ConnectorRegistry,
#       ServiceNowConnector,
#       ConnectorConfig,
#   )
#
#   # Register connector
#   registry = ConnectorRegistry()
#   registry.register(ServiceNowConnector(config))
#
#   # Execute operation
#   connector = registry.get("servicenow")
#   result = await connector.execute("get_incident", incident_id="INC001")
# =============================================================================

from src.domain.connectors.base import (
    BaseConnector,
    ConnectorConfig,
    ConnectorError,
    ConnectorResponse,
    ConnectorStatus,
)
from src.domain.connectors.dynamics365 import Dynamics365Connector
from src.domain.connectors.registry import ConnectorRegistry
from src.domain.connectors.servicenow import ServiceNowConnector
from src.domain.connectors.sharepoint import SharePointConnector

__all__ = [
    # Base classes
    "BaseConnector",
    "ConnectorConfig",
    "ConnectorError",
    "ConnectorResponse",
    "ConnectorStatus",
    # Registry
    "ConnectorRegistry",
    # Implementations
    "ServiceNowConnector",
    "Dynamics365Connector",
    "SharePointConnector",
]

# =============================================================================
# IPA Platform - Connector Base Classes
# =============================================================================
# Sprint 2: Workflow & Checkpoints - Cross-System Integration
#
# Abstract base classes and data structures for enterprise connectors.
# Provides:
#   - ConnectorStatus: Connection status enumeration
#   - ConnectorConfig: Configuration data structure with authentication
#   - ConnectorResponse: Standard response format for all operations
#   - ConnectorError: Exception class for connector failures
#   - BaseConnector: Abstract base class for connector implementations
#
# All concrete connectors (ServiceNow, Dynamics365, SharePoint) inherit
# from BaseConnector and implement the required abstract methods.
#
# Usage:
#   class MyConnector(BaseConnector):
#       name = "my_connector"
#       description = "Custom connector"
#
#       async def execute(self, operation, **kwargs):
#           return ConnectorResponse(success=True, data=result)
# =============================================================================

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Enumerations
# =============================================================================


class ConnectorStatus(str, Enum):
    """
    Connection status for connectors.

    Values:
        DISCONNECTED: Not connected to external system
        CONNECTING: Connection in progress
        CONNECTED: Successfully connected
        ERROR: Connection failed or error state
        RATE_LIMITED: Temporarily rate limited
    """

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"


class AuthType(str, Enum):
    """
    Authentication types supported by connectors.

    Values:
        NONE: No authentication required
        API_KEY: Simple API key authentication
        BASIC: Username/password basic auth
        OAUTH2: OAuth 2.0 client credentials
        OAUTH2_CODE: OAuth 2.0 authorization code flow
        CERTIFICATE: Certificate-based authentication
    """

    NONE = "none"
    API_KEY = "api_key"
    BASIC = "basic"
    OAUTH2 = "oauth2"
    OAUTH2_CODE = "oauth2_code"
    CERTIFICATE = "certificate"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ConnectorConfig:
    """
    Configuration for a connector instance.

    Attributes:
        name: Unique connector instance name
        connector_type: Type of connector (e.g., "servicenow", "dynamics365")
        base_url: Base URL for API requests
        auth_type: Authentication method to use
        credentials: Authentication credentials (varies by auth_type)
        timeout_seconds: Request timeout in seconds
        retry_count: Number of retries on failure
        retry_delay_seconds: Delay between retries
        headers: Additional HTTP headers
        options: Connector-specific options
        enabled: Whether connector is enabled

    Example:
        config = ConnectorConfig(
            name="production-servicenow",
            connector_type="servicenow",
            base_url="https://company.service-now.com",
            auth_type=AuthType.BASIC,
            credentials={"username": "api_user", "password": "secret"},
        )
    """

    name: str
    connector_type: str
    base_url: str
    auth_type: AuthType = AuthType.NONE
    credentials: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 30
    retry_count: int = 3
    retry_delay_seconds: float = 1.0
    headers: Dict[str, str] = field(default_factory=dict)
    options: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary (excluding sensitive credentials)."""
        return {
            "name": self.name,
            "connector_type": self.connector_type,
            "base_url": self.base_url,
            "auth_type": self.auth_type.value,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "retry_delay_seconds": self.retry_delay_seconds,
            "headers": self.headers,
            "options": self.options,
            "enabled": self.enabled,
            # Credentials masked for security
            "has_credentials": bool(self.credentials),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConnectorConfig":
        """Create config from dictionary."""
        auth_type = data.get("auth_type", "none")
        if isinstance(auth_type, str):
            auth_type = AuthType(auth_type)

        return cls(
            name=data["name"],
            connector_type=data["connector_type"],
            base_url=data["base_url"],
            auth_type=auth_type,
            credentials=data.get("credentials", {}),
            timeout_seconds=data.get("timeout_seconds", 30),
            retry_count=data.get("retry_count", 3),
            retry_delay_seconds=data.get("retry_delay_seconds", 1.0),
            headers=data.get("headers", {}),
            options=data.get("options", {}),
            enabled=data.get("enabled", True),
        )


@dataclass
class ConnectorResponse:
    """
    Standard response format for connector operations.

    Attributes:
        success: Whether the operation succeeded
        data: Response data (varies by operation)
        error: Error message if operation failed
        error_code: Error code for programmatic handling
        metadata: Additional metadata about the response
        timestamp: When the response was created

    Example:
        response = ConnectorResponse(
            success=True,
            data={"incident_id": "INC001", "state": "resolved"},
            metadata={"request_id": "abc123"},
        )
    """

    success: bool
    data: Any = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "error_code": self.error_code,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }

    def __str__(self) -> str:
        """String representation for logging."""
        if self.success:
            return f"ConnectorResponse(success=True, data={self.data})"
        return f"ConnectorResponse(success=False, error={self.error})"


# =============================================================================
# Exceptions
# =============================================================================


class ConnectorError(Exception):
    """
    Exception raised when connector operation fails.

    Attributes:
        message: Error description
        connector_name: Name of the connector that failed
        operation: Operation that was attempted
        error_code: Optional error code
        original_error: Original exception if any
        retryable: Whether the operation can be retried

    Example:
        raise ConnectorError(
            message="Authentication failed",
            connector_name="servicenow",
            operation="connect",
            error_code="AUTH_FAILED",
            retryable=False,
        )
    """

    def __init__(
        self,
        message: str,
        connector_name: Optional[str] = None,
        operation: Optional[str] = None,
        error_code: Optional[str] = None,
        original_error: Optional[Exception] = None,
        retryable: bool = True,
    ):
        self.message = message
        self.connector_name = connector_name
        self.operation = operation
        self.error_code = error_code
        self.original_error = original_error
        self.retryable = retryable
        super().__init__(message)

    def to_response(self) -> ConnectorResponse:
        """Convert error to ConnectorResponse."""
        return ConnectorResponse(
            success=False,
            error=self.message,
            error_code=self.error_code,
            metadata={
                "connector_name": self.connector_name,
                "operation": self.operation,
                "retryable": self.retryable,
                "original_error": str(self.original_error) if self.original_error else None,
            },
        )


# =============================================================================
# Base Connector Class
# =============================================================================


class BaseConnector(ABC):
    """
    Abstract base class for enterprise connectors.

    Subclasses must implement:
        - name: Unique connector type identifier
        - description: Human-readable description
        - connect(): Establish connection to external system
        - disconnect(): Close connection gracefully
        - execute(): Execute an operation on the external system
        - health_check(): Verify connector health

    Attributes:
        config: Connector configuration
        status: Current connection status
        last_error: Last error encountered
        operations: Dictionary of supported operations

    Example:
        class MyConnector(BaseConnector):
            name = "my_connector"
            description = "Custom connector for My System"

            async def connect(self):
                # Establish connection
                self._status = ConnectorStatus.CONNECTED

            async def execute(self, operation: str, **kwargs):
                if operation == "get_data":
                    return await self._get_data(**kwargs)
                raise ConnectorError(f"Unknown operation: {operation}")
    """

    # Subclasses must define these
    name: str = ""
    description: str = ""

    # Supported operations (subclasses should override)
    supported_operations: List[str] = []

    def __init__(self, config: ConnectorConfig):
        """
        Initialize connector with configuration.

        Args:
            config: ConnectorConfig instance
        """
        if not self.name:
            raise ValueError(f"{self.__class__.__name__} must define 'name'")
        if not self.description:
            raise ValueError(f"{self.__class__.__name__} must define 'description'")

        self._config = config
        self._status = ConnectorStatus.DISCONNECTED
        self._last_error: Optional[str] = None
        self._connected_at: Optional[datetime] = None
        self._request_count: int = 0
        self._error_count: int = 0

    @property
    def config(self) -> ConnectorConfig:
        """Get connector configuration."""
        return self._config

    @property
    def status(self) -> ConnectorStatus:
        """Get current connection status."""
        return self._status

    @property
    def last_error(self) -> Optional[str]:
        """Get last error message."""
        return self._last_error

    @property
    def is_connected(self) -> bool:
        """Check if connector is connected."""
        return self._status == ConnectorStatus.CONNECTED

    @abstractmethod
    async def connect(self) -> None:
        """
        Establish connection to external system.

        Should authenticate and verify connectivity.
        Sets status to CONNECTED on success.

        Raises:
            ConnectorError: If connection fails
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Close connection gracefully.

        Should clean up any resources and set status to DISCONNECTED.
        """
        pass

    @abstractmethod
    async def execute(self, operation: str, **kwargs) -> ConnectorResponse:
        """
        Execute an operation on the external system.

        Args:
            operation: Operation name (e.g., "get_incident", "list_customers")
            **kwargs: Operation-specific parameters

        Returns:
            ConnectorResponse with operation result

        Raises:
            ConnectorError: If operation fails
        """
        pass

    @abstractmethod
    async def health_check(self) -> ConnectorResponse:
        """
        Verify connector health and connectivity.

        Returns:
            ConnectorResponse with health status

        Example response data:
            {
                "status": "healthy",
                "latency_ms": 45,
                "last_check": "2024-01-15T10:30:00Z"
            }
        """
        pass

    async def __call__(self, operation: str, **kwargs) -> ConnectorResponse:
        """
        Call connector (wrapper around execute with error handling).

        Args:
            operation: Operation name
            **kwargs: Operation parameters

        Returns:
            ConnectorResponse (never raises, errors captured in response)
        """
        try:
            # Ensure connected
            if not self.is_connected:
                await self.connect()

            self._request_count += 1
            return await self.execute(operation, **kwargs)

        except ConnectorError as e:
            self._error_count += 1
            self._last_error = e.message
            logger.error(f"Connector {self.name} operation {operation} failed: {e.message}")
            return e.to_response()

        except Exception as e:
            self._error_count += 1
            self._last_error = str(e)
            logger.error(f"Connector {self.name} unexpected error: {e}")
            return ConnectorResponse(
                success=False,
                error=str(e),
                error_code="UNEXPECTED_ERROR",
                metadata={"connector_name": self.name, "operation": operation},
            )

    def get_stats(self) -> Dict[str, Any]:
        """
        Get connector statistics.

        Returns:
            Dictionary with connector stats
        """
        return {
            "name": self.name,
            "config_name": self._config.name,
            "status": self._status.value,
            "connected_at": self._connected_at.isoformat() if self._connected_at else None,
            "request_count": self._request_count,
            "error_count": self._error_count,
            "last_error": self._last_error,
            "enabled": self._config.enabled,
        }

    def get_info(self) -> Dict[str, Any]:
        """
        Get connector information.

        Returns:
            Dictionary with connector info and supported operations
        """
        return {
            "name": self.name,
            "description": self.description,
            "config": self._config.to_dict(),
            "status": self._status.value,
            "supported_operations": self.supported_operations,
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}', status={self._status.value})>"

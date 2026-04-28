# =============================================================================
# IPA Platform - Connector API Schemas
# =============================================================================
# Sprint 2: Workflow & Checkpoints - Cross-System Integration
#
# Pydantic schemas for Connector API endpoints.
# Provides request/response validation for connector operations.
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Connector Configuration Schemas
# =============================================================================


class ConnectorConfigRequest(BaseModel):
    """Request schema for creating/updating connector configuration."""

    name: str = Field(..., description="Unique connector instance name")
    connector_type: str = Field(..., description="Connector type (servicenow, dynamics365, sharepoint)")
    base_url: str = Field(..., description="Base URL for the external system")
    auth_type: str = Field("none", description="Authentication type (none, api_key, basic, oauth2)")
    credentials: Dict[str, Any] = Field(default_factory=dict, description="Authentication credentials")
    timeout_seconds: int = Field(30, ge=1, le=300, description="Request timeout in seconds")
    retry_count: int = Field(3, ge=0, le=10, description="Number of retries on failure")
    headers: Dict[str, str] = Field(default_factory=dict, description="Additional HTTP headers")
    options: Dict[str, Any] = Field(default_factory=dict, description="Connector-specific options")
    enabled: bool = Field(True, description="Whether connector is enabled")


class ConnectorConfigResponse(BaseModel):
    """Response schema for connector configuration (credentials masked)."""

    name: str = Field(..., description="Connector instance name")
    connector_type: str = Field(..., description="Connector type")
    base_url: str = Field(..., description="Base URL")
    auth_type: str = Field(..., description="Authentication type")
    timeout_seconds: int = Field(..., description="Request timeout")
    retry_count: int = Field(..., description="Retry count")
    headers: Dict[str, str] = Field(..., description="HTTP headers")
    options: Dict[str, Any] = Field(..., description="Options")
    enabled: bool = Field(..., description="Enabled status")
    has_credentials: bool = Field(..., description="Whether credentials are configured")


# =============================================================================
# Connector Status Schemas
# =============================================================================


class ConnectorStatusResponse(BaseModel):
    """Response schema for connector status."""

    name: str = Field(..., description="Connector instance name")
    config_name: str = Field(..., description="Configuration name")
    status: str = Field(..., description="Connection status")
    connected_at: Optional[datetime] = Field(None, description="When connected")
    request_count: int = Field(0, description="Total requests made")
    error_count: int = Field(0, description="Total errors")
    last_error: Optional[str] = Field(None, description="Last error message")
    enabled: bool = Field(True, description="Enabled status")


class ConnectorInfoResponse(BaseModel):
    """Response schema for connector information."""

    name: str = Field(..., description="Connector type name")
    description: str = Field(..., description="Connector description")
    config: ConnectorConfigResponse = Field(..., description="Configuration")
    status: str = Field(..., description="Connection status")
    supported_operations: List[str] = Field(..., description="Supported operations")


# =============================================================================
# Health Check Schemas
# =============================================================================


class ConnectorHealthResponse(BaseModel):
    """Response schema for individual connector health."""

    name: str = Field(..., description="Connector name")
    status: str = Field(..., description="Health status (healthy, unhealthy, disconnected)")
    latency_ms: Optional[float] = Field(None, description="Response latency in milliseconds")
    error: Optional[str] = Field(None, description="Error message if unhealthy")
    last_check: Optional[datetime] = Field(None, description="When last checked")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")


class HealthSummaryResponse(BaseModel):
    """Response schema for overall health summary."""

    status: str = Field(..., description="Overall status (healthy, degraded, unhealthy)")
    total_connectors: int = Field(..., description="Total registered connectors")
    healthy_count: int = Field(..., description="Number of healthy connectors")
    unhealthy_count: int = Field(..., description="Number of unhealthy connectors")
    timestamp: datetime = Field(..., description="When health check was performed")
    connectors: Dict[str, ConnectorHealthResponse] = Field(
        ..., description="Individual connector health"
    )


# =============================================================================
# Operation Schemas
# =============================================================================


class ConnectorOperationRequest(BaseModel):
    """Request schema for executing a connector operation."""

    operation: str = Field(..., description="Operation name")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Operation parameters")


class ConnectorOperationResponse(BaseModel):
    """Response schema for connector operation result."""

    success: bool = Field(..., description="Whether operation succeeded")
    data: Any = Field(None, description="Operation result data")
    error: Optional[str] = Field(None, description="Error message if failed")
    error_code: Optional[str] = Field(None, description="Error code")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    timestamp: datetime = Field(..., description="When operation completed")


# =============================================================================
# List Schemas
# =============================================================================


class ConnectorListResponse(BaseModel):
    """Response schema for listing connectors."""

    connectors: List[ConnectorInfoResponse] = Field(..., description="List of connectors")
    total: int = Field(..., description="Total number of connectors")


class ConnectorTypesResponse(BaseModel):
    """Response schema for listing connector types."""

    types: List[str] = Field(..., description="Available connector types")
    descriptions: Dict[str, str] = Field(..., description="Type descriptions")

# =============================================================================
# IPA Platform - Connector API Routes
# =============================================================================
# Sprint 2: Workflow & Checkpoints - Cross-System Integration
#
# REST API endpoints for connector management and operations.
# Provides:
#   - GET /connectors/ - List all connectors
#   - GET /connectors/types - List available connector types
#   - GET /connectors/health - Health check all connectors
#   - GET /connectors/{name} - Get connector details
#   - GET /connectors/{name}/health - Health check specific connector
#   - POST /connectors/{name}/execute - Execute connector operation
#   - POST /connectors/{name}/connect - Connect connector
#   - POST /connectors/{name}/disconnect - Disconnect connector
# =============================================================================

import logging
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.v1.connectors.schemas import (
    ConnectorConfigResponse,
    ConnectorHealthResponse,
    ConnectorInfoResponse,
    ConnectorListResponse,
    ConnectorOperationRequest,
    ConnectorOperationResponse,
    ConnectorStatusResponse,
    ConnectorTypesResponse,
    HealthSummaryResponse,
)
from src.domain.connectors import ConnectorRegistry
from src.domain.connectors.base import ConnectorResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/connectors",
    tags=["connectors"],
    responses={
        404: {"description": "Connector not found"},
        500: {"description": "Internal server error"},
    },
)

# =============================================================================
# Dependency Injection
# =============================================================================

# Global registry instance (in production, use proper DI)
_registry: ConnectorRegistry = None


def _register_default_connectors(registry: ConnectorRegistry) -> None:
    """Register default connectors for UAT testing.

    In production, connectors should be registered via configuration
    or admin API. For UAT purposes, we register test connectors.
    """
    from src.domain.connectors.base import ConnectorConfig, AuthType

    # Default test connectors for UAT
    default_configs = [
        ConnectorConfig(
            name="servicenow",
            connector_type="servicenow",
            base_url="https://test.service-now.com",
            auth_type=AuthType.NONE,
            enabled=True,
            options={"test_mode": True},
        ),
        ConnectorConfig(
            name="dynamics365",
            connector_type="dynamics365",
            base_url="https://test.crm.dynamics.com",
            auth_type=AuthType.NONE,
            enabled=True,
            options={"test_mode": True},
        ),
        ConnectorConfig(
            name="sharepoint",
            connector_type="sharepoint",
            base_url="https://test.sharepoint.com",
            auth_type=AuthType.NONE,
            enabled=True,
            options={"test_mode": True},
        ),
    ]

    for config in default_configs:
        try:
            registry.register_from_config(config)
            logger.info(f"Registered default connector: {config.name}")
        except ValueError as e:
            # Already registered, skip
            logger.debug(f"Connector already registered: {config.name}")
        except Exception as e:
            # Log any unexpected errors
            logger.error(f"Failed to register connector {config.name}: {e}")


def get_registry() -> ConnectorRegistry:
    """Get or create connector registry."""
    global _registry
    if _registry is None:
        logger.info("Creating new ConnectorRegistry...")
        _registry = ConnectorRegistry()
        # Register default connectors for UAT testing
        _register_default_connectors(_registry)
        logger.info(f"ConnectorRegistry initialized with {len(_registry._connectors)} connectors")
    return _registry


# =============================================================================
# List Connectors
# =============================================================================


@router.get(
    "/",
    response_model=ConnectorListResponse,
    summary="List all connectors",
    description="Get a list of all registered connectors with their status",
)
async def list_connectors(
    registry: ConnectorRegistry = Depends(get_registry),
) -> ConnectorListResponse:
    """
    List all registered connectors.

    Returns connector information including configuration and status.
    """
    try:
        connectors_info = registry.get_all_info()

        connectors = []
        for info in connectors_info:
            config = info.get("config", {})
            connectors.append(
                ConnectorInfoResponse(
                    name=info.get("name", ""),
                    description=info.get("description", ""),
                    config=ConnectorConfigResponse(
                        name=config.get("name", ""),
                        connector_type=config.get("connector_type", ""),
                        base_url=config.get("base_url", ""),
                        auth_type=config.get("auth_type", "none"),
                        timeout_seconds=config.get("timeout_seconds", 30),
                        retry_count=config.get("retry_count", 3),
                        headers=config.get("headers", {}),
                        options=config.get("options", {}),
                        enabled=config.get("enabled", True),
                        has_credentials=config.get("has_credentials", False),
                    ),
                    status=info.get("status", "disconnected"),
                    supported_operations=info.get("supported_operations", []),
                )
            )

        return ConnectorListResponse(
            connectors=connectors,
            total=len(connectors),
        )

    except Exception as e:
        logger.error(f"Error listing connectors: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list connectors: {str(e)}",
        )


# =============================================================================
# Connector Types
# =============================================================================


@router.get(
    "/types",
    response_model=ConnectorTypesResponse,
    summary="List connector types",
    description="Get available connector types that can be registered",
)
async def list_connector_types(
    registry: ConnectorRegistry = Depends(get_registry),
) -> ConnectorTypesResponse:
    """
    List all available connector types.

    Returns type names and descriptions.
    """
    try:
        types = registry.list_types()

        descriptions = {
            "servicenow": "ServiceNow ITSM connector for incident and service management",
            "dynamics365": "Microsoft Dynamics 365 CRM connector for customer and case management",
            "sharepoint": "Microsoft SharePoint connector for document management",
        }

        return ConnectorTypesResponse(
            types=types,
            descriptions={t: descriptions.get(t, "") for t in types},
        )

    except Exception as e:
        logger.error(f"Error listing connector types: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list connector types: {str(e)}",
        )


# =============================================================================
# Health Check
# =============================================================================


@router.get(
    "/health",
    response_model=HealthSummaryResponse,
    summary="Health check all connectors",
    description="Run health check on all registered connectors",
)
async def health_check_all(
    registry: ConnectorRegistry = Depends(get_registry),
) -> HealthSummaryResponse:
    """
    Run health check on all registered connectors.

    Returns overall health status and individual connector health.
    """
    try:
        health_results = await registry.health_check_all()
        summary = registry.get_health_summary(health_results)

        # Convert to response model
        connectors_health = {}
        for name, resp in health_results.items():
            data = resp.data or {}
            connectors_health[name] = ConnectorHealthResponse(
                name=name,
                status=data.get("status", "unknown"),
                latency_ms=data.get("latency_ms"),
                error=resp.error,
                last_check=datetime.fromisoformat(data["last_check"]) if data.get("last_check") else None,
                details=data,
            )

        return HealthSummaryResponse(
            status=summary["status"],
            total_connectors=summary["total_connectors"],
            healthy_count=summary["healthy_count"],
            unhealthy_count=summary["unhealthy_count"],
            timestamp=datetime.fromisoformat(summary["timestamp"]),
            connectors=connectors_health,
        )

    except Exception as e:
        logger.error(f"Error running health check: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run health check: {str(e)}",
        )


# =============================================================================
# Get Connector
# =============================================================================


@router.get(
    "/{name}",
    response_model=ConnectorInfoResponse,
    summary="Get connector details",
    description="Get detailed information about a specific connector",
)
async def get_connector(
    name: str,
    registry: ConnectorRegistry = Depends(get_registry),
) -> ConnectorInfoResponse:
    """
    Get detailed information about a specific connector.
    """
    try:
        connector = registry.get(name)

        if connector is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connector not found: {name}",
            )

        info = connector.get_info()
        config = info.get("config", {})

        return ConnectorInfoResponse(
            name=info.get("name", ""),
            description=info.get("description", ""),
            config=ConnectorConfigResponse(
                name=config.get("name", ""),
                connector_type=config.get("connector_type", ""),
                base_url=config.get("base_url", ""),
                auth_type=config.get("auth_type", "none"),
                timeout_seconds=config.get("timeout_seconds", 30),
                retry_count=config.get("retry_count", 3),
                headers=config.get("headers", {}),
                options=config.get("options", {}),
                enabled=config.get("enabled", True),
                has_credentials=config.get("has_credentials", False),
            ),
            status=info.get("status", "disconnected"),
            supported_operations=info.get("supported_operations", []),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting connector {name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get connector: {str(e)}",
        )


# =============================================================================
# Connector Status
# =============================================================================


@router.get(
    "/{name}/status",
    response_model=ConnectorStatusResponse,
    summary="Get connector status",
    description="Get current status and statistics for a connector",
)
async def get_connector_status(
    name: str,
    registry: ConnectorRegistry = Depends(get_registry),
) -> ConnectorStatusResponse:
    """
    Get current status and statistics for a connector.
    """
    try:
        connector = registry.get(name)

        if connector is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connector not found: {name}",
            )

        stats = connector.get_stats()

        return ConnectorStatusResponse(
            name=stats.get("name", ""),
            config_name=stats.get("config_name", ""),
            status=stats.get("status", "disconnected"),
            connected_at=datetime.fromisoformat(stats["connected_at"]) if stats.get("connected_at") else None,
            request_count=stats.get("request_count", 0),
            error_count=stats.get("error_count", 0),
            last_error=stats.get("last_error"),
            enabled=stats.get("enabled", True),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting connector status {name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get connector status: {str(e)}",
        )


# =============================================================================
# Connector Health Check
# =============================================================================


@router.get(
    "/{name}/health",
    response_model=ConnectorHealthResponse,
    summary="Health check connector",
    description="Run health check on a specific connector",
)
async def health_check_connector(
    name: str,
    registry: ConnectorRegistry = Depends(get_registry),
) -> ConnectorHealthResponse:
    """
    Run health check on a specific connector.
    """
    try:
        connector = registry.get(name)

        if connector is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connector not found: {name}",
            )

        if not connector.is_connected:
            return ConnectorHealthResponse(
                name=name,
                status="disconnected",
                error="Connector not connected",
                details={"connected": False},
            )

        result = await connector.health_check()
        data = result.data or {}

        return ConnectorHealthResponse(
            name=name,
            status=data.get("status", "unknown"),
            latency_ms=data.get("latency_ms"),
            error=result.error,
            last_check=datetime.fromisoformat(data["last_check"]) if data.get("last_check") else datetime.utcnow(),
            details=data,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error health checking connector {name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to health check connector: {str(e)}",
        )


# =============================================================================
# Execute Operation
# =============================================================================


@router.post(
    "/{name}/execute",
    response_model=ConnectorOperationResponse,
    summary="Execute connector operation",
    description="Execute an operation on a specific connector",
)
async def execute_operation(
    name: str,
    request: ConnectorOperationRequest,
    registry: ConnectorRegistry = Depends(get_registry),
) -> ConnectorOperationResponse:
    """
    Execute an operation on a specific connector.

    The connector will be connected automatically if not already connected.
    """
    try:
        connector = registry.get(name)

        if connector is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connector not found: {name}",
            )

        if not connector.config.enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Connector is disabled: {name}",
            )

        # Execute operation (connector.__call__ handles connection)
        result = await connector(request.operation, **request.parameters)

        return ConnectorOperationResponse(
            success=result.success,
            data=result.data,
            error=result.error,
            error_code=result.error_code,
            metadata=result.metadata,
            timestamp=result.timestamp,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing operation on {name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute operation: {str(e)}",
        )


# =============================================================================
# Connect/Disconnect
# =============================================================================


@router.post(
    "/{name}/connect",
    response_model=Dict[str, Any],
    summary="Connect connector",
    description="Establish connection to the external system",
)
async def connect_connector(
    name: str,
    registry: ConnectorRegistry = Depends(get_registry),
) -> Dict[str, Any]:
    """
    Establish connection to the external system.
    """
    try:
        connector = registry.get(name)

        if connector is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connector not found: {name}",
            )

        if connector.is_connected:
            return {
                "success": True,
                "message": "Already connected",
                "status": connector.status.value,
            }

        await connector.connect()

        return {
            "success": True,
            "message": "Connected successfully",
            "status": connector.status.value,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting connector {name}: {e}")
        return {
            "success": False,
            "message": str(e),
            "status": "error",
        }


@router.post(
    "/{name}/disconnect",
    response_model=Dict[str, Any],
    summary="Disconnect connector",
    description="Close connection to the external system",
)
async def disconnect_connector(
    name: str,
    registry: ConnectorRegistry = Depends(get_registry),
) -> Dict[str, Any]:
    """
    Close connection to the external system.
    """
    try:
        connector = registry.get(name)

        if connector is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connector not found: {name}",
            )

        if not connector.is_connected:
            return {
                "success": True,
                "message": "Already disconnected",
                "status": connector.status.value,
            }

        await connector.disconnect()

        return {
            "success": True,
            "message": "Disconnected successfully",
            "status": connector.status.value,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting connector {name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect connector: {str(e)}",
        )

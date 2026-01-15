"""
Input Gateway Package

Provides the InputGateway entry point for processing requests from various sources:
- InputGateway: Main gateway class for source routing
- Source Handlers: Specialized handlers for ServiceNow, Prometheus, and User input
- Schema Validator: Data validation for webhook payloads

Sprint 95: InputGateway + SourceHandlers (Phase 28)

Architecture:
```
                           ┌──────────────────┐
                           │   InputGateway    │
                           │ _identify_source  │
                           └────────┬─────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
    ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
    │ ServiceNowHandler│  │PrometheusHandler│  │UserInputHandler │
    │ (Mapping + Pattern)│ │(Pattern Matching)│ │(3-Layer Routing)│
    └─────────────────┘  └─────────────────┘  └─────────────────┘
              │                     │                     │
              └─────────────────────┼─────────────────────┘
                                    │
                                    ▼
                           ┌──────────────────┐
                           │  RoutingDecision  │
                           └──────────────────┘
```

Example:
    >>> from backend.src.integrations.orchestration.input_gateway import (
    ...     InputGateway,
    ...     IncomingRequest,
    ...     ServiceNowHandler,
    ... )
    >>> # Create gateway
    >>> gateway = InputGateway(
    ...     source_handlers={"servicenow": ServiceNowHandler()},
    ...     business_router=business_router,
    ... )
    >>> # Process ServiceNow webhook
    >>> request = IncomingRequest.from_servicenow_webhook(payload)
    >>> decision = await gateway.process(request)
"""

from .models import (
    SourceType,
    IncomingRequest,
    GatewayConfig,
    GatewayMetrics,
)
from .gateway import (
    InputGateway,
    MockInputGateway,
    create_input_gateway,
    create_mock_gateway,
)
from .schema_validator import (
    SchemaValidator,
    MockSchemaValidator,
    SchemaDefinition,
    ValidationError,
)
from .source_handlers import (
    BaseSourceHandler,
    MockBaseHandler,
    HandlerMetrics,
    ServiceNowHandler,
    MockServiceNowHandler,
    PrometheusHandler,
    MockPrometheusHandler,
    UserInputHandler,
    MockUserInputHandler,
)

__all__ = [
    # Models
    "SourceType",
    "IncomingRequest",
    "GatewayConfig",
    "GatewayMetrics",
    # Gateway
    "InputGateway",
    "MockInputGateway",
    "create_input_gateway",
    "create_mock_gateway",
    # Schema Validator
    "SchemaValidator",
    "MockSchemaValidator",
    "SchemaDefinition",
    "ValidationError",
    # Source Handlers - Base
    "BaseSourceHandler",
    "MockBaseHandler",
    "HandlerMetrics",
    # Source Handlers - ServiceNow
    "ServiceNowHandler",
    "MockServiceNowHandler",
    # Source Handlers - Prometheus
    "PrometheusHandler",
    "MockPrometheusHandler",
    # Source Handlers - User
    "UserInputHandler",
    "MockUserInputHandler",
]

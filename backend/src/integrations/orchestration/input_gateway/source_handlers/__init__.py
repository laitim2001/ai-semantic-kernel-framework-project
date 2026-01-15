"""
Source Handlers Package

Provides specialized handlers for different input sources:
- BaseSourceHandler: Abstract base class for all handlers
- ServiceNowHandler: ServiceNow webhook handler with mapping table
- PrometheusHandler: Prometheus Alertmanager handler with pattern matching
- UserInputHandler: User input handler with full three-layer routing

Sprint 95: InputGateway + SourceHandlers (Phase 28)
"""

from .base_handler import (
    BaseSourceHandler,
    MockBaseHandler,
    HandlerMetrics,
)
from .servicenow_handler import (
    ServiceNowHandler,
    MockServiceNowHandler,
)
from .prometheus_handler import (
    PrometheusHandler,
    MockPrometheusHandler,
)
from .user_input_handler import (
    UserInputHandler,
    MockUserInputHandler,
)

__all__ = [
    # Base
    "BaseSourceHandler",
    "MockBaseHandler",
    "HandlerMetrics",
    # ServiceNow
    "ServiceNowHandler",
    "MockServiceNowHandler",
    # Prometheus
    "PrometheusHandler",
    "MockPrometheusHandler",
    # User Input
    "UserInputHandler",
    "MockUserInputHandler",
]

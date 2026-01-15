"""
InputGateway Implementation

Main entry point for processing incoming requests from various sources.
Routes system sources (ServiceNow, Prometheus) to simplified handlers
and user input to the full three-layer routing system.

Sprint 95: Story 95-1 - Implement InputGateway (Phase 28)
"""

import logging
import time
from typing import Any, Dict, Optional, TYPE_CHECKING

from .models import (
    GatewayConfig,
    GatewayMetrics,
    IncomingRequest,
    SourceType,
)

if TYPE_CHECKING:
    from .source_handlers.base_handler import BaseSourceHandler
    from ..intent_router.router import BusinessIntentRouter
    from ..intent_router.models import RoutingDecision

logger = logging.getLogger(__name__)


class InputGateway:
    """
    Input Gateway for routing requests to appropriate handlers.

    The gateway identifies the source of incoming requests and routes them:
    - System sources (ServiceNow, Prometheus) → Simplified source handlers
    - User input → Full three-layer routing (Pattern → Semantic → LLM)

    This design enables:
    - Fast processing for system sources (< 10ms target)
    - Rich classification for user input
    - Consistent output format (RoutingDecision)

    Attributes:
        source_handlers: Dictionary mapping source types to handlers
        business_router: Router for user input (three-layer architecture)
        schema_validator: Optional schema validator for incoming data
        config: Gateway configuration

    Example:
        >>> gateway = InputGateway(
        ...     source_handlers={
        ...         "servicenow": ServiceNowHandler(...),
        ...         "prometheus": PrometheusHandler(...),
        ...     },
        ...     business_router=BusinessIntentRouter(...),
        ... )
        >>> # ServiceNow webhook → simplified path
        >>> request = IncomingRequest.from_servicenow_webhook(payload)
        >>> decision = await gateway.process(request)
        >>> print(decision.layer_used)  # "servicenow_mapping"
        >>>
        >>> # User input → full three-layer routing
        >>> request = IncomingRequest.from_user_input("ETL 失敗了")
        >>> decision = await gateway.process(request)
        >>> print(decision.routing_layer)  # "pattern" or "semantic" or "llm"
    """

    def __init__(
        self,
        source_handlers: Dict[str, "BaseSourceHandler"],
        business_router: Optional["BusinessIntentRouter"] = None,
        schema_validator: Optional[Any] = None,
        config: Optional[GatewayConfig] = None,
    ):
        """
        Initialize the InputGateway.

        Args:
            source_handlers: Mapping of source types to their handlers
            business_router: Router for user input (optional for system-only setup)
            schema_validator: Schema validator for incoming data (optional)
            config: Gateway configuration (optional)
        """
        self.source_handlers = source_handlers
        self.business_router = business_router
        self.schema_validator = schema_validator
        self.config = config or GatewayConfig()
        self._metrics = GatewayMetrics()

    async def process(self, request: IncomingRequest) -> "RoutingDecision":
        """
        Process an incoming request and return a routing decision.

        The processing flow:
        1. Identify source type from headers or explicit source_type
        2. If system source → delegate to appropriate source handler
        3. If user source → delegate to BusinessIntentRouter

        Args:
            request: The incoming request to process

        Returns:
            RoutingDecision with routing details and classification

        Raises:
            ValueError: If neither source handler nor business router available
        """
        from ..intent_router.models import (
            CompletenessInfo,
            ITIntentCategory,
            RiskLevel,
            RoutingDecision,
            WorkflowType,
        )

        start_time = time.perf_counter()
        self._metrics.total_requests += 1

        # Identify source type
        source_type = self._identify_source(request)
        logger.debug(f"Identified source type: {source_type}")

        try:
            # System source → Source Handler (simplified path)
            if source_type in self.source_handlers:
                handler = self.source_handlers[source_type]
                logger.info(
                    f"Routing to {source_type} handler "
                    f"(request_id: {request.request_id})"
                )

                # Track metrics by source type
                if source_type == "servicenow":
                    self._metrics.servicenow_requests += 1
                elif source_type == "prometheus":
                    self._metrics.prometheus_requests += 1

                # Optional schema validation
                if self.config.enable_schema_validation and self.schema_validator:
                    try:
                        self.schema_validator.validate(request.data, schema=source_type)
                    except Exception as e:
                        logger.warning(f"Schema validation failed: {e}")
                        self._metrics.validation_errors += 1

                decision = await handler.process(request)
                return self._finalize_decision(decision, start_time)

            # User source → BusinessIntentRouter (full three-layer path)
            if self.business_router:
                logger.info(
                    f"Routing to business router "
                    f"(request_id: {request.request_id})"
                )
                self._metrics.user_requests += 1

                # Use content for user input, or data description for API
                input_text = request.content
                if not input_text and request.data:
                    input_text = request.data.get("description", "")
                    if not input_text:
                        input_text = str(request.data)

                decision = await self.business_router.route(input_text)
                return self._finalize_decision(decision, start_time)

            # No handler available
            logger.error(
                f"No handler available for source type: {source_type}"
            )
            return RoutingDecision(
                intent_category=ITIntentCategory.UNKNOWN,
                confidence=0.0,
                workflow_type=WorkflowType.HANDOFF,
                risk_level=RiskLevel.MEDIUM,
                completeness=CompletenessInfo(
                    is_complete=False,
                    completeness_score=0.0,
                ),
                routing_layer="none",
                reasoning=f"No handler configured for source type: {source_type}",
                processing_time_ms=(time.perf_counter() - start_time) * 1000,
            )

        except Exception as e:
            logger.error(f"Error processing request: {e}", exc_info=True)
            return RoutingDecision(
                intent_category=ITIntentCategory.UNKNOWN,
                confidence=0.0,
                workflow_type=WorkflowType.HANDOFF,
                risk_level=RiskLevel.HIGH,
                completeness=CompletenessInfo(
                    is_complete=False,
                    completeness_score=0.0,
                ),
                routing_layer="error",
                reasoning=f"Processing error: {str(e)}",
                processing_time_ms=(time.perf_counter() - start_time) * 1000,
            )

    def _identify_source(self, request: IncomingRequest) -> str:
        """
        Identify the source type of an incoming request.

        Identification priority:
        1. Check for specific webhook headers (most reliable)
        2. Use explicitly specified source_type field
        3. Fall back to default source type

        Args:
            request: The incoming request

        Returns:
            Source type string (e.g., "servicenow", "prometheus", "user")
        """
        # Check ServiceNow header
        if request.has_header(self.config.servicenow_header):
            return SourceType.SERVICENOW.value

        # Check Prometheus header
        if request.has_header(self.config.prometheus_header):
            return SourceType.PROMETHEUS.value

        # Check other common webhook headers
        if request.has_header("x-webhook-source"):
            source = request.get_header("x-webhook-source", "").lower()
            if source:
                return source

        # Use explicitly specified source type
        if request.source_type:
            return request.source_type.lower()

        # Default to user source
        return self.config.default_source_type

    def _finalize_decision(
        self,
        decision: "RoutingDecision",
        start_time: float,
    ) -> "RoutingDecision":
        """
        Finalize a routing decision with timing and metrics.

        Args:
            decision: The routing decision to finalize
            start_time: Processing start time (from time.perf_counter())

        Returns:
            Finalized RoutingDecision with accurate processing time
        """
        # Update processing time to include gateway overhead
        total_latency_ms = (time.perf_counter() - start_time) * 1000

        # Record metrics
        if self.config.enable_metrics:
            self._metrics.record_latency(total_latency_ms)

        # Log performance warning if system source exceeds target
        if decision.routing_layer in ["servicenow_mapping", "prometheus_mapping"]:
            if total_latency_ms > 10.0:
                logger.warning(
                    f"System source latency exceeded 10ms target: "
                    f"{total_latency_ms:.2f}ms"
                )

        return decision

    def get_metrics(self) -> Dict[str, Any]:
        """Get gateway metrics."""
        return self._metrics.to_dict()

    def reset_metrics(self) -> None:
        """Reset gateway metrics."""
        self._metrics = GatewayMetrics()

    def register_handler(
        self,
        source_type: str,
        handler: "BaseSourceHandler",
    ) -> None:
        """
        Register a source handler dynamically.

        Args:
            source_type: The source type identifier
            handler: The handler instance
        """
        self.source_handlers[source_type.lower()] = handler
        logger.info(f"Registered handler for source type: {source_type}")

    def unregister_handler(self, source_type: str) -> None:
        """
        Unregister a source handler.

        Args:
            source_type: The source type identifier to remove
        """
        if source_type.lower() in self.source_handlers:
            del self.source_handlers[source_type.lower()]
            logger.info(f"Unregistered handler for source type: {source_type}")


class MockInputGateway(InputGateway):
    """
    Mock InputGateway for testing without external dependencies.

    Uses mock implementations of all components.
    """

    def __init__(
        self,
        config: Optional[GatewayConfig] = None,
    ):
        """
        Initialize mock gateway with mock handlers.

        Args:
            config: Gateway configuration (optional)
        """
        from .source_handlers.servicenow_handler import MockServiceNowHandler
        from .source_handlers.prometheus_handler import MockPrometheusHandler
        from .source_handlers.user_input_handler import MockUserInputHandler
        from ..intent_router.router import MockBusinessIntentRouter

        source_handlers = {
            "servicenow": MockServiceNowHandler(),
            "prometheus": MockPrometheusHandler(),
            "user": MockUserInputHandler(),
        }

        super().__init__(
            source_handlers=source_handlers,
            business_router=MockBusinessIntentRouter(),
            config=config or GatewayConfig(),
        )


# =============================================================================
# Factory Functions
# =============================================================================

def create_input_gateway(
    pattern_matcher: Optional[Any] = None,
    business_router: Optional["BusinessIntentRouter"] = None,
    schema_validator: Optional[Any] = None,
    config: Optional[GatewayConfig] = None,
) -> InputGateway:
    """
    Factory function to create a fully configured InputGateway.

    Args:
        pattern_matcher: PatternMatcher for ServiceNow fallback
        business_router: BusinessIntentRouter for user input
        schema_validator: Optional schema validator
        config: Gateway configuration

    Returns:
        Configured InputGateway instance
    """
    from .source_handlers.servicenow_handler import ServiceNowHandler
    from .source_handlers.prometheus_handler import PrometheusHandler
    from .source_handlers.user_input_handler import UserInputHandler
    from .schema_validator import SchemaValidator

    # Create schema validator if not provided
    if schema_validator is None:
        schema_validator = SchemaValidator()

    # Create source handlers
    source_handlers = {
        "servicenow": ServiceNowHandler(
            schema_validator=schema_validator,
            pattern_matcher=pattern_matcher,
        ),
        "prometheus": PrometheusHandler(
            schema_validator=schema_validator,
        ),
    }

    # Add user input handler if business router is provided
    if business_router:
        source_handlers["user"] = UserInputHandler(
            business_router=business_router,
        )

    return InputGateway(
        source_handlers=source_handlers,
        business_router=business_router,
        schema_validator=schema_validator,
        config=config or GatewayConfig.from_env(),
    )


def create_mock_gateway(
    config: Optional[GatewayConfig] = None,
) -> MockInputGateway:
    """
    Factory function to create a mock gateway for testing.

    Args:
        config: Gateway configuration

    Returns:
        MockInputGateway instance
    """
    return MockInputGateway(config=config)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "InputGateway",
    "MockInputGateway",
    "create_input_gateway",
    "create_mock_gateway",
]

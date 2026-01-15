"""
Prometheus Alertmanager Source Handler

Specialized handler for Prometheus Alertmanager webhook requests.
Uses pattern matching on alert names to classify incidents.

This handler implements a SIMPLIFIED processing path:
1. Schema validation (optional)
2. Alert name pattern matching
3. Label extraction for metadata
4. SKIPS Semantic Router and LLM Classifier

Target latency: < 10ms

Sprint 95: Story 95-4 - Implement PrometheusHandler (Phase 28)
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from .base_handler import BaseSourceHandler
from ..models import IncomingRequest

if TYPE_CHECKING:
    from ...intent_router.models import RoutingDecision, ITIntentCategory, RiskLevel, WorkflowType
    from ..schema_validator import SchemaValidator

logger = logging.getLogger(__name__)


class PrometheusHandler(BaseSourceHandler):
    """
    Prometheus Alertmanager webhook handler with pattern-based classification.

    Processing flow:
    1. Validate Alertmanager webhook schema (if validator provided)
    2. Extract alerts from payload
    3. Match alert name against patterns
    4. Extract labels for metadata
    5. SKIP Semantic Router and LLM Classifier

    This ensures Prometheus alerts are processed quickly (< 10ms)
    while providing accurate incident classification.

    Attributes:
        schema_validator: Optional schema validator
        ALERT_PATTERNS: Pattern matching rules for alert classification

    Example:
        >>> handler = PrometheusHandler(
        ...     schema_validator=SchemaValidator(),
        ... )
        >>> request = IncomingRequest.from_prometheus_webhook({
        ...     "alerts": [{
        ...         "alertname": "HighCPUUsage",
        ...         "status": "firing",
        ...         "labels": {"severity": "critical", "instance": "server-01"}
        ...     }]
        ... })
        >>> decision = await handler.process(request)
        >>> print(decision.intent_category)  # ITIntentCategory.INCIDENT
        >>> print(decision.sub_intent)       # "performance_issue"
        >>> print(decision.layer_used)       # "prometheus_mapping"
    """

    # =============================================================================
    # Alert Pattern Mapping
    # =============================================================================
    # Format: (regex_pattern, intent_category, sub_intent, default_workflow)
    # Patterns are matched in order - first match wins

    ALERT_PATTERNS: List[Tuple[str, str, str, str]] = [
        # CPU/Performance issues
        (r".*high.?cpu.*", "incident", "performance_issue", "sequential"),
        (r".*cpu.?high.*", "incident", "performance_issue", "sequential"),
        (r".*cpu.?usage.*", "incident", "performance_issue", "sequential"),
        (r".*high.?load.*", "incident", "performance_issue", "sequential"),

        # Memory issues
        (r".*high.?memory.*", "incident", "memory_issue", "sequential"),
        (r".*memory.?high.*", "incident", "memory_issue", "sequential"),
        (r".*memory.?pressure.*", "incident", "memory_issue", "sequential"),
        (r".*oom.*", "incident", "memory_issue", "magentic"),  # Out of memory is critical

        # Disk/Storage issues
        (r".*disk.?full.*", "incident", "disk_issue", "sequential"),
        (r".*disk.?space.*", "incident", "disk_issue", "sequential"),
        (r".*storage.*", "incident", "disk_issue", "sequential"),
        (r".*filesystem.*", "incident", "disk_issue", "sequential"),

        # Service down/unavailable
        (r".*down$", "incident", "service_down", "magentic"),
        (r".*_down_.*", "incident", "service_down", "magentic"),
        (r".*unavailable.*", "incident", "service_down", "magentic"),
        (r".*unreachable.*", "incident", "service_down", "magentic"),
        (r".*not.?responding.*", "incident", "service_down", "magentic"),

        # Latency issues
        (r".*latency.*", "incident", "latency_issue", "sequential"),
        (r".*slow.*", "incident", "latency_issue", "sequential"),
        (r".*response.?time.*", "incident", "latency_issue", "sequential"),
        (r".*timeout.*", "incident", "latency_issue", "sequential"),

        # Error rate issues
        (r".*error.?rate.*", "incident", "error_rate_issue", "sequential"),
        (r".*5xx.*", "incident", "error_rate_issue", "sequential"),
        (r".*errors.*high.*", "incident", "error_rate_issue", "sequential"),
        (r".*failure.?rate.*", "incident", "error_rate_issue", "sequential"),

        # Certificate issues
        (r".*certificate.*", "incident", "certificate_issue", "sequential"),
        (r".*ssl.*", "incident", "certificate_issue", "sequential"),
        (r".*tls.*", "incident", "certificate_issue", "sequential"),
        (r".*cert.?expir.*", "incident", "certificate_issue", "sequential"),

        # Network issues
        (r".*network.*", "incident", "network_issue", "sequential"),
        (r".*connection.*", "incident", "network_issue", "sequential"),
        (r".*packet.?loss.*", "incident", "network_issue", "sequential"),
        (r".*dns.*", "incident", "network_issue", "sequential"),

        # Database issues
        (r".*database.*", "incident", "database_issue", "magentic"),
        (r".*db.?.*", "incident", "database_issue", "magentic"),
        (r".*mysql.*", "incident", "database_issue", "magentic"),
        (r".*postgres.*", "incident", "database_issue", "magentic"),
        (r".*redis.*", "incident", "database_issue", "sequential"),

        # Queue/Messaging issues
        (r".*queue.*", "incident", "queue_issue", "sequential"),
        (r".*rabbitmq.*", "incident", "queue_issue", "sequential"),
        (r".*kafka.*", "incident", "queue_issue", "sequential"),

        # Container/Kubernetes issues
        (r".*pod.*", "incident", "container_issue", "sequential"),
        (r".*container.*", "incident", "container_issue", "sequential"),
        (r".*kubernetes.*", "incident", "container_issue", "sequential"),
        (r".*k8s.*", "incident", "container_issue", "sequential"),
    ]

    # Severity to risk level mapping
    SEVERITY_RISK_MAPPING: Dict[str, str] = {
        "critical": "critical",
        "warning": "medium",
        "info": "low",
        "none": "low",
        # Also handle numeric severities
        "1": "critical",
        "2": "high",
        "3": "medium",
        "4": "low",
        "5": "low",
    }

    def __init__(
        self,
        schema_validator: Optional["SchemaValidator"] = None,
        enable_metrics: bool = True,
    ):
        """
        Initialize PrometheusHandler.

        Args:
            schema_validator: Schema validator for Prometheus webhooks
            enable_metrics: Whether to track handler metrics
        """
        super().__init__(enable_metrics=enable_metrics)
        self.schema_validator = schema_validator
        # Compile patterns for performance
        self._compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), intent, sub_intent, workflow)
            for pattern, intent, sub_intent, workflow in self.ALERT_PATTERNS
        ]

    @property
    def handler_type(self) -> str:
        """Return handler type identifier."""
        return "prometheus"

    async def process(self, request: IncomingRequest) -> "RoutingDecision":
        """
        Process a Prometheus Alertmanager webhook request.

        Args:
            request: The Prometheus webhook request

        Returns:
            RoutingDecision with classification and routing information
        """
        from ...intent_router.models import (
            ITIntentCategory,
            RiskLevel,
            WorkflowType,
        )

        start_time = time.perf_counter()

        try:
            # Extract Prometheus data
            data = request.data
            if not data:
                logger.warning("Empty Prometheus webhook data")
                return self._build_error_decision(
                    "Empty webhook data",
                    start_time,
                )

            # Optional schema validation
            if self.schema_validator:
                try:
                    validated_data = self.schema_validator.validate(
                        data,
                        schema="prometheus",
                    )
                    data = validated_data
                except Exception as e:
                    logger.warning(f"Prometheus schema validation failed: {e}")
                    # Continue with original data

            # Extract alerts
            alerts = data.get("alerts", [])
            if not alerts:
                logger.warning("No alerts in Prometheus webhook")
                return self._build_error_decision(
                    "No alerts in webhook",
                    start_time,
                )

            # Process first alert (most relevant)
            alert = alerts[0]
            alertname = alert.get("alertname", "")
            status = alert.get("status", "firing")
            labels = alert.get("labels", {})
            annotations = alert.get("annotations", {})

            # Get severity from labels
            severity = labels.get("severity", "warning").lower()

            # Match alert name against patterns
            intent_category, sub_intent, workflow_str = self._match_alert(alertname)

            # Determine risk level from severity
            risk_str = self.SEVERITY_RISK_MAPPING.get(severity, "medium")
            risk_level = RiskLevel.from_string(risk_str)

            # Override workflow for critical severity
            if severity == "critical" and workflow_str != "magentic":
                workflow_str = "magentic"

            workflow_type = WorkflowType.from_string(workflow_str)

            # Calculate latency
            latency_ms = (time.perf_counter() - start_time) * 1000

            # Build metadata from labels and annotations
            metadata = {
                "alertname": alertname,
                "status": status,
                "severity": severity,
                "labels": labels,
                "summary": annotations.get("summary", ""),
                "description": annotations.get("description", ""),
                "alert_count": len(alerts),
                "firing_count": sum(1 for a in alerts if a.get("status") == "firing"),
                **self.extract_metadata(request),
            }

            # Determine reasoning
            if intent_category != ITIntentCategory.UNKNOWN:
                reasoning = f"Alert pattern matched: {alertname}"
                layer_used = "prometheus_mapping"
                confidence = 0.95
            else:
                reasoning = f"No pattern match for alert: {alertname}"
                layer_used = "prometheus_default"
                confidence = 0.7

            # Record success
            self._record_success(latency_ms)

            return self.build_routing_decision(
                intent_category=intent_category,
                sub_intent=sub_intent,
                confidence=confidence,
                workflow_type=workflow_type,
                risk_level=risk_level,
                completeness_score=1.0,  # System source is always complete
                layer_used=layer_used,
                reasoning=reasoning,
                metadata=metadata,
                processing_time_ms=latency_ms,
            )

        except Exception as e:
            logger.error(f"Prometheus processing error: {e}", exc_info=True)
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._record_failure(latency_ms)
            return self._build_error_decision(str(e), start_time)

    def _match_alert(
        self,
        alertname: str,
    ) -> Tuple["ITIntentCategory", Optional[str], str]:
        """
        Match alert name against patterns.

        Args:
            alertname: The alert name to match

        Returns:
            Tuple of (intent_category, sub_intent, workflow_type)
        """
        from ...intent_router.models import ITIntentCategory

        for compiled_pattern, intent_str, sub_intent, workflow in self._compiled_patterns:
            if compiled_pattern.match(alertname):
                intent_category = ITIntentCategory.from_string(intent_str)
                logger.debug(
                    f"Prometheus pattern match: {alertname} → "
                    f"{intent_category.value}/{sub_intent}"
                )
                return intent_category, sub_intent, workflow

        # Default to generic incident
        logger.debug(f"No Prometheus pattern match for: {alertname}")
        return ITIntentCategory.INCIDENT, "general_incident", "sequential"

    def _build_error_decision(
        self,
        error_message: str,
        start_time: float,
    ) -> "RoutingDecision":
        """Build error routing decision."""
        from ...intent_router.models import (
            ITIntentCategory,
            RiskLevel,
            WorkflowType,
        )

        latency_ms = (time.perf_counter() - start_time) * 1000

        return self.build_routing_decision(
            intent_category=ITIntentCategory.UNKNOWN,
            sub_intent=None,
            confidence=0.0,
            workflow_type=WorkflowType.HANDOFF,
            risk_level=RiskLevel.MEDIUM,
            completeness_score=0.0,
            layer_used="prometheus_error",
            reasoning=f"Processing error: {error_message}",
            processing_time_ms=latency_ms,
        )


class MockPrometheusHandler(PrometheusHandler):
    """
    Mock Prometheus handler for testing.

    Processes requests without actual schema validation.
    """

    def __init__(self):
        """Initialize mock handler."""
        super().__init__(
            schema_validator=None,
            enable_metrics=False,
        )

    async def process(self, request: IncomingRequest) -> "RoutingDecision":
        """Process with mock logic - simplified for testing."""
        from ...intent_router.models import ITIntentCategory

        start_time = time.perf_counter()

        # Extract basic fields
        data = request.data
        alerts = data.get("alerts", [])

        if alerts:
            alert = alerts[0]
            alertname = alert.get("alertname", "")
            intent_category, sub_intent, workflow_str = self._match_alert(alertname)
        else:
            intent_category = ITIntentCategory.INCIDENT
            sub_intent = "general_incident"

        latency_ms = (time.perf_counter() - start_time) * 1000

        return self.build_routing_decision(
            intent_category=intent_category,
            sub_intent=sub_intent,
            confidence=0.95,
            layer_used="prometheus_mock",
            reasoning="Mock Prometheus handler response",
            metadata={
                "alertname": alerts[0].get("alertname") if alerts else None,
                "alert_count": len(alerts),
            },
            processing_time_ms=latency_ms,
        )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "PrometheusHandler",
    "MockPrometheusHandler",
]

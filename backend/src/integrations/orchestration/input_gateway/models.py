"""
Input Gateway Data Models

Defines data structures for the input gateway layer:
- IncomingRequest: Unified request model from all sources
- SourceType: Enumeration of supported source types
- GatewayConfig: Configuration for the input gateway

Sprint 95: InputGateway + SourceHandlers (Phase 28)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class SourceType(Enum):
    """
    Supported input source types.

    Types:
    - SERVICENOW: ServiceNow webhook integration
    - PROMETHEUS: Prometheus Alertmanager webhook
    - USER: Direct user input (chat, form, API)
    - API: Generic API request
    - UNKNOWN: Unidentified source
    """
    SERVICENOW = "servicenow"
    PROMETHEUS = "prometheus"
    USER = "user"
    API = "api"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, value: str) -> "SourceType":
        """Convert string to SourceType enum."""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.UNKNOWN


@dataclass
class IncomingRequest:
    """
    Unified incoming request model.

    Represents requests from various sources (ServiceNow, Prometheus, User)
    in a standardized format for processing by InputGateway.

    Attributes:
        content: Primary content/text of the request (for user input)
        data: Structured data payload (for webhooks)
        headers: HTTP headers from the request
        source_type: Explicitly specified source type (optional)
        request_id: Unique request identifier
        timestamp: When the request was received
        metadata: Additional request metadata
    """
    content: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    source_type: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Normalize headers to lowercase keys."""
        self.headers = {k.lower(): v for k, v in self.headers.items()}

    def get_header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get header value (case-insensitive)."""
        return self.headers.get(name.lower(), default)

    def has_header(self, name: str) -> bool:
        """Check if header exists (case-insensitive)."""
        return name.lower() in self.headers

    @classmethod
    def from_user_input(cls, text: str, request_id: Optional[str] = None) -> "IncomingRequest":
        """
        Factory method for user input requests.

        Args:
            text: User's input text
            request_id: Optional request identifier

        Returns:
            IncomingRequest configured for user input
        """
        return cls(
            content=text,
            source_type="user",
            request_id=request_id,
        )

    @classmethod
    def from_servicenow_webhook(
        cls,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        request_id: Optional[str] = None,
    ) -> "IncomingRequest":
        """
        Factory method for ServiceNow webhook requests.

        Args:
            payload: ServiceNow webhook payload
            headers: HTTP headers
            request_id: Optional request identifier

        Returns:
            IncomingRequest configured for ServiceNow
        """
        return cls(
            content=payload.get("short_description", ""),
            data=payload,
            headers=headers or {"x-servicenow-webhook": "true"},
            source_type="servicenow",
            request_id=request_id or payload.get("number"),
        )

    @classmethod
    def from_prometheus_webhook(
        cls,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        request_id: Optional[str] = None,
    ) -> "IncomingRequest":
        """
        Factory method for Prometheus Alertmanager webhook requests.

        Args:
            payload: Prometheus Alertmanager payload
            headers: HTTP headers
            request_id: Optional request identifier

        Returns:
            IncomingRequest configured for Prometheus
        """
        # Extract alert summary from first alert
        alerts = payload.get("alerts", [])
        summary = ""
        if alerts:
            first_alert = alerts[0]
            annotations = first_alert.get("annotations", {})
            summary = annotations.get("summary", first_alert.get("alertname", ""))

        return cls(
            content=summary,
            data=payload,
            headers=headers or {"x-prometheus-alertmanager": "true"},
            source_type="prometheus",
            request_id=request_id,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "content": self.content,
            "data": self.data,
            "headers": self.headers,
            "source_type": self.source_type,
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class GatewayConfig:
    """
    Configuration for InputGateway.

    Attributes:
        enable_schema_validation: Whether to validate incoming data schema
        enable_metrics: Whether to track gateway metrics
        default_source_type: Default source type for unidentified requests
        max_content_length: Maximum content length (0 for unlimited)
        servicenow_header: Header to identify ServiceNow webhooks
        prometheus_header: Header to identify Prometheus webhooks
    """
    enable_schema_validation: bool = True
    enable_metrics: bool = True
    default_source_type: str = "user"
    max_content_length: int = 0
    servicenow_header: str = "x-servicenow-webhook"
    prometheus_header: str = "x-prometheus-alertmanager"

    @classmethod
    def from_env(cls) -> "GatewayConfig":
        """Create configuration from environment variables."""
        import os
        return cls(
            enable_schema_validation=os.getenv(
                "GATEWAY_ENABLE_SCHEMA_VALIDATION", "true"
            ).lower() == "true",
            enable_metrics=os.getenv(
                "GATEWAY_ENABLE_METRICS", "true"
            ).lower() == "true",
            default_source_type=os.getenv(
                "GATEWAY_DEFAULT_SOURCE_TYPE", "user"
            ),
            max_content_length=int(os.getenv(
                "GATEWAY_MAX_CONTENT_LENGTH", "0"
            )),
        )


@dataclass
class GatewayMetrics:
    """
    Metrics for InputGateway operations.

    Attributes:
        total_requests: Total number of processed requests
        servicenow_requests: Count of ServiceNow webhook requests
        prometheus_requests: Count of Prometheus webhook requests
        user_requests: Count of user input requests
        validation_errors: Count of schema validation errors
        latencies: List of processing latencies (ms)
    """
    total_requests: int = 0
    servicenow_requests: int = 0
    prometheus_requests: int = 0
    user_requests: int = 0
    validation_errors: int = 0
    latencies: List[float] = field(default_factory=list)

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency."""
        if not self.latencies:
            return 0.0
        return sum(self.latencies) / len(self.latencies)

    @property
    def p95_latency_ms(self) -> float:
        """Calculate 95th percentile latency."""
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]

    def record_latency(self, latency_ms: float) -> None:
        """Record a latency measurement."""
        self.latencies.append(latency_ms)
        # Keep only last 1000 measurements
        if len(self.latencies) > 1000:
            self.latencies = self.latencies[-1000:]

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "total_requests": self.total_requests,
            "servicenow_requests": self.servicenow_requests,
            "prometheus_requests": self.prometheus_requests,
            "user_requests": self.user_requests,
            "validation_errors": self.validation_errors,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
        }


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "SourceType",
    "IncomingRequest",
    "GatewayConfig",
    "GatewayMetrics",
]

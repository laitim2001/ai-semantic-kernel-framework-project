"""
OpenTelemetry Metrics for Orchestration Module

Provides comprehensive metrics collection for monitoring:
- Routing metrics (requests, latency, layer distribution)
- Dialog metrics (rounds, completion rate)
- HITL metrics (requests, approval time)
- System source metrics (ServiceNow, Prometheus)

Sprint 99: Story 99-3 - Monitoring Metrics Integration (Phase 28)
"""

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Generator, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# OpenTelemetry Integration (with fallback for non-OTel environments)
# =============================================================================

try:
    from opentelemetry import metrics as otel_metrics
    from opentelemetry.metrics import Counter, Histogram, Gauge, Meter

    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    logger.info("OpenTelemetry not available, using fallback metrics")


# =============================================================================
# Metric Type Definitions
# =============================================================================


class MetricType(Enum):
    """Types of metrics that can be collected."""
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    GAUGE = "gauge"


@dataclass
class MetricDefinition:
    """Definition of a metric to be collected."""
    name: str
    description: str
    unit: str
    metric_type: MetricType
    labels: List[str] = field(default_factory=list)


# =============================================================================
# Routing Metrics Definitions
# =============================================================================

ROUTING_METRICS = [
    MetricDefinition(
        name="orchestration_routing_requests_total",
        description="Total number of routing requests",
        unit="requests",
        metric_type=MetricType.COUNTER,
        labels=["intent_category", "layer_used"],
    ),
    MetricDefinition(
        name="orchestration_routing_latency_seconds",
        description="Routing latency in seconds",
        unit="seconds",
        metric_type=MetricType.HISTOGRAM,
        labels=["layer_used"],
    ),
    MetricDefinition(
        name="orchestration_routing_confidence",
        description="Routing confidence score",
        unit="score",
        metric_type=MetricType.HISTOGRAM,
        labels=["intent_category"],
    ),
    MetricDefinition(
        name="orchestration_completeness_score",
        description="Information completeness score",
        unit="score",
        metric_type=MetricType.HISTOGRAM,
        labels=["intent_category"],
    ),
]

# =============================================================================
# Dialog Metrics Definitions
# =============================================================================

DIALOG_METRICS = [
    MetricDefinition(
        name="orchestration_dialog_rounds_total",
        description="Total number of dialog rounds",
        unit="rounds",
        metric_type=MetricType.COUNTER,
        labels=["dialog_id", "phase"],
    ),
    MetricDefinition(
        name="orchestration_dialog_completion_rate",
        description="Dialog completion rate",
        unit="ratio",
        metric_type=MetricType.GAUGE,
        labels=[],
    ),
    MetricDefinition(
        name="orchestration_dialog_duration_seconds",
        description="Dialog duration in seconds",
        unit="seconds",
        metric_type=MetricType.HISTOGRAM,
        labels=["outcome"],
    ),
    MetricDefinition(
        name="orchestration_dialog_active_count",
        description="Number of active dialogs",
        unit="dialogs",
        metric_type=MetricType.GAUGE,
        labels=[],
    ),
]

# =============================================================================
# HITL Metrics Definitions
# =============================================================================

HITL_METRICS = [
    MetricDefinition(
        name="orchestration_hitl_requests_total",
        description="Total HITL approval requests",
        unit="requests",
        metric_type=MetricType.COUNTER,
        labels=["risk_level", "status"],
    ),
    MetricDefinition(
        name="orchestration_hitl_approval_time_seconds",
        description="HITL approval time in seconds",
        unit="seconds",
        metric_type=MetricType.HISTOGRAM,
        labels=["risk_level"],
    ),
    MetricDefinition(
        name="orchestration_hitl_pending_count",
        description="Number of pending HITL requests",
        unit="requests",
        metric_type=MetricType.GAUGE,
        labels=[],
    ),
    MetricDefinition(
        name="orchestration_hitl_approval_rate",
        description="HITL approval rate",
        unit="ratio",
        metric_type=MetricType.GAUGE,
        labels=["risk_level"],
    ),
]

# =============================================================================
# System Source Metrics Definitions
# =============================================================================

SYSTEM_SOURCE_METRICS = [
    MetricDefinition(
        name="orchestration_system_source_requests_total",
        description="Total system source requests",
        unit="requests",
        metric_type=MetricType.COUNTER,
        labels=["source_type"],
    ),
    MetricDefinition(
        name="orchestration_system_source_latency_seconds",
        description="System source processing latency",
        unit="seconds",
        metric_type=MetricType.HISTOGRAM,
        labels=["source_type"],
    ),
    MetricDefinition(
        name="orchestration_system_source_errors_total",
        description="Total system source errors",
        unit="errors",
        metric_type=MetricType.COUNTER,
        labels=["source_type", "error_type"],
    ),
]


# =============================================================================
# Fallback Metrics Implementation
# =============================================================================


class FallbackCounter:
    """Fallback counter implementation when OpenTelemetry is not available."""

    def __init__(self, name: str, description: str, labels: List[str]):
        self.name = name
        self.description = description
        self.labels = labels
        self._values: Dict[tuple, int] = {}

    def add(self, value: int, labels: Optional[Dict[str, str]] = None) -> None:
        """Add to counter."""
        key = tuple(sorted((labels or {}).items()))
        self._values[key] = self._values.get(key, 0) + value

    def get_value(self, labels: Optional[Dict[str, str]] = None) -> int:
        """Get current counter value."""
        key = tuple(sorted((labels or {}).items()))
        return self._values.get(key, 0)

    def reset(self) -> None:
        """Reset counter."""
        self._values.clear()


class FallbackHistogram:
    """Fallback histogram implementation when OpenTelemetry is not available."""

    DEFAULT_BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]

    def __init__(
        self,
        name: str,
        description: str,
        labels: List[str],
        buckets: Optional[List[float]] = None,
    ):
        self.name = name
        self.description = description
        self.labels = labels
        self.buckets = buckets or self.DEFAULT_BUCKETS
        self._values: Dict[tuple, List[float]] = {}

    def record(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a value."""
        key = tuple(sorted((labels or {}).items()))
        if key not in self._values:
            self._values[key] = []
        self._values[key].append(value)

    def get_values(self, labels: Optional[Dict[str, str]] = None) -> List[float]:
        """Get recorded values."""
        key = tuple(sorted((labels or {}).items()))
        return self._values.get(key, [])

    def get_percentile(
        self, percentile: float, labels: Optional[Dict[str, str]] = None
    ) -> float:
        """Get percentile value."""
        values = self.get_values(labels)
        if not values:
            return 0.0
        sorted_values = sorted(values)
        idx = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(idx, len(sorted_values) - 1)]

    def reset(self) -> None:
        """Reset histogram."""
        self._values.clear()


class FallbackGauge:
    """Fallback gauge implementation when OpenTelemetry is not available."""

    def __init__(self, name: str, description: str, labels: List[str]):
        self.name = name
        self.description = description
        self.labels = labels
        self._values: Dict[tuple, float] = {}

    def set(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set gauge value."""
        key = tuple(sorted((labels or {}).items()))
        self._values[key] = value

    def get_value(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get current gauge value."""
        key = tuple(sorted((labels or {}).items()))
        return self._values.get(key, 0.0)

    def reset(self) -> None:
        """Reset gauge."""
        self._values.clear()


# =============================================================================
# Metrics Collector
# =============================================================================


class OrchestrationMetricsCollector:
    """
    Centralized metrics collector for the orchestration module.

    Provides:
    - Automatic metric creation and registration
    - OpenTelemetry integration (when available)
    - Fallback to in-memory metrics
    - Convenient recording methods
    - Metric export in various formats

    Example:
        >>> collector = OrchestrationMetricsCollector()
        >>> collector.record_routing_request(
        ...     intent_category="incident",
        ...     layer_used="pattern",
        ...     latency_seconds=0.005,
        ...     confidence=0.95,
        ... )
        >>> metrics = collector.get_metrics()
    """

    def __init__(
        self,
        meter_name: str = "orchestration",
        use_opentelemetry: bool = True,
    ):
        """
        Initialize the metrics collector.

        Args:
            meter_name: Name for the OpenTelemetry meter
            use_opentelemetry: Whether to use OpenTelemetry (if available)
        """
        self._use_otel = use_opentelemetry and OPENTELEMETRY_AVAILABLE
        self._meter_name = meter_name

        # Initialize metric storage
        self._counters: Dict[str, Any] = {}
        self._histograms: Dict[str, Any] = {}
        self._gauges: Dict[str, Any] = {}

        # Create all metrics
        self._create_metrics()

        logger.info(
            f"OrchestrationMetricsCollector initialized "
            f"(OpenTelemetry: {self._use_otel})"
        )

    def _create_metrics(self) -> None:
        """Create all metric instruments."""
        all_metrics = (
            ROUTING_METRICS +
            DIALOG_METRICS +
            HITL_METRICS +
            SYSTEM_SOURCE_METRICS
        )

        for metric_def in all_metrics:
            if metric_def.metric_type == MetricType.COUNTER:
                self._counters[metric_def.name] = self._create_counter(metric_def)
            elif metric_def.metric_type == MetricType.HISTOGRAM:
                self._histograms[metric_def.name] = self._create_histogram(metric_def)
            elif metric_def.metric_type == MetricType.GAUGE:
                self._gauges[metric_def.name] = self._create_gauge(metric_def)

    def _create_counter(self, definition: MetricDefinition) -> Any:
        """Create a counter metric."""
        if self._use_otel:
            meter = otel_metrics.get_meter(self._meter_name)
            return meter.create_counter(
                name=definition.name,
                description=definition.description,
                unit=definition.unit,
            )
        else:
            return FallbackCounter(
                name=definition.name,
                description=definition.description,
                labels=definition.labels,
            )

    def _create_histogram(self, definition: MetricDefinition) -> Any:
        """Create a histogram metric."""
        # Define appropriate buckets based on metric name
        buckets = None
        if "latency" in definition.name or "time" in definition.name:
            if "hitl" in definition.name:
                # HITL approval time: 1min, 5min, 10min, 30min, 1hr buckets
                buckets = [60, 300, 600, 1800, 3600]
            else:
                # Routing latency: 10ms, 50ms, 100ms, 500ms, 1s, 2s, 5s buckets
                buckets = [0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
        elif "score" in definition.name or "confidence" in definition.name:
            # Score metrics: 0.1 increments
            buckets = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

        if self._use_otel:
            meter = otel_metrics.get_meter(self._meter_name)
            return meter.create_histogram(
                name=definition.name,
                description=definition.description,
                unit=definition.unit,
            )
        else:
            return FallbackHistogram(
                name=definition.name,
                description=definition.description,
                labels=definition.labels,
                buckets=buckets,
            )

    def _create_gauge(self, definition: MetricDefinition) -> Any:
        """Create a gauge metric."""
        if self._use_otel:
            meter = otel_metrics.get_meter(self._meter_name)
            # OpenTelemetry uses ObservableGauge, but for simplicity use UpDownCounter
            return meter.create_up_down_counter(
                name=definition.name,
                description=definition.description,
                unit=definition.unit,
            )
        else:
            return FallbackGauge(
                name=definition.name,
                description=definition.description,
                labels=definition.labels,
            )

    # =========================================================================
    # Routing Metrics Methods
    # =========================================================================

    def record_routing_request(
        self,
        intent_category: str,
        layer_used: str,
        latency_seconds: float,
        confidence: float,
        completeness_score: float = 1.0,
    ) -> None:
        """
        Record a routing request.

        Args:
            intent_category: The classified intent category
            layer_used: The routing layer that made the decision
            latency_seconds: Total routing latency in seconds
            confidence: Confidence score of the classification
            completeness_score: Information completeness score
        """
        labels = {
            "intent_category": intent_category,
            "layer_used": layer_used,
        }

        # Record request count
        counter = self._counters.get("orchestration_routing_requests_total")
        if counter:
            if self._use_otel:
                counter.add(1, labels)
            else:
                counter.add(1, labels)

        # Record latency
        histogram = self._histograms.get("orchestration_routing_latency_seconds")
        if histogram:
            if self._use_otel:
                histogram.record(latency_seconds, {"layer_used": layer_used})
            else:
                histogram.record(latency_seconds, {"layer_used": layer_used})

        # Record confidence
        histogram = self._histograms.get("orchestration_routing_confidence")
        if histogram:
            if self._use_otel:
                histogram.record(confidence, {"intent_category": intent_category})
            else:
                histogram.record(confidence, {"intent_category": intent_category})

        # Record completeness
        histogram = self._histograms.get("orchestration_completeness_score")
        if histogram:
            if self._use_otel:
                histogram.record(completeness_score, {"intent_category": intent_category})
            else:
                histogram.record(completeness_score, {"intent_category": intent_category})

    @contextmanager
    def routing_timer(
        self,
        layer: str,
    ) -> Generator[None, None, None]:
        """
        Context manager for timing routing operations.

        Args:
            layer: The routing layer being timed

        Example:
            >>> with collector.routing_timer("pattern"):
            ...     result = await pattern_matcher.match(input)
        """
        start_time = time.perf_counter()
        try:
            yield
        finally:
            latency = time.perf_counter() - start_time
            histogram = self._histograms.get("orchestration_routing_latency_seconds")
            if histogram:
                if self._use_otel:
                    histogram.record(latency, {"layer_used": layer})
                else:
                    histogram.record(latency, {"layer_used": layer})

    # =========================================================================
    # Dialog Metrics Methods
    # =========================================================================

    def record_dialog_round(
        self,
        dialog_id: str,
        phase: str,
    ) -> None:
        """
        Record a dialog round.

        Args:
            dialog_id: Unique dialog identifier
            phase: Current dialog phase
        """
        counter = self._counters.get("orchestration_dialog_rounds_total")
        if counter:
            labels = {"dialog_id": dialog_id, "phase": phase}
            if self._use_otel:
                counter.add(1, labels)
            else:
                counter.add(1, labels)

    def record_dialog_completion(
        self,
        outcome: str,
        duration_seconds: float,
    ) -> None:
        """
        Record dialog completion.

        Args:
            outcome: Dialog outcome (complete, handoff, timeout)
            duration_seconds: Total dialog duration
        """
        histogram = self._histograms.get("orchestration_dialog_duration_seconds")
        if histogram:
            if self._use_otel:
                histogram.record(duration_seconds, {"outcome": outcome})
            else:
                histogram.record(duration_seconds, {"outcome": outcome})

    def set_active_dialogs(self, count: int) -> None:
        """
        Set the number of active dialogs.

        Args:
            count: Number of active dialogs
        """
        gauge = self._gauges.get("orchestration_dialog_active_count")
        if gauge:
            if self._use_otel:
                # For UpDownCounter, we need to track the delta
                pass  # OpenTelemetry gauge handling
            else:
                gauge.set(count)

    def set_dialog_completion_rate(self, rate: float) -> None:
        """
        Set dialog completion rate.

        Args:
            rate: Completion rate (0.0 to 1.0)
        """
        gauge = self._gauges.get("orchestration_dialog_completion_rate")
        if gauge:
            if self._use_otel:
                pass  # OpenTelemetry gauge handling
            else:
                gauge.set(rate)

    # =========================================================================
    # HITL Metrics Methods
    # =========================================================================

    def record_hitl_request(
        self,
        risk_level: str,
        status: str,
    ) -> None:
        """
        Record a HITL approval request.

        Args:
            risk_level: Risk level of the request
            status: Current status of the request
        """
        counter = self._counters.get("orchestration_hitl_requests_total")
        if counter:
            labels = {"risk_level": risk_level, "status": status}
            if self._use_otel:
                counter.add(1, labels)
            else:
                counter.add(1, labels)

    def record_hitl_approval_time(
        self,
        risk_level: str,
        approval_time_seconds: float,
    ) -> None:
        """
        Record HITL approval time.

        Args:
            risk_level: Risk level of the request
            approval_time_seconds: Time taken for approval
        """
        histogram = self._histograms.get("orchestration_hitl_approval_time_seconds")
        if histogram:
            if self._use_otel:
                histogram.record(approval_time_seconds, {"risk_level": risk_level})
            else:
                histogram.record(approval_time_seconds, {"risk_level": risk_level})

    def set_hitl_pending_count(self, count: int) -> None:
        """
        Set the number of pending HITL requests.

        Args:
            count: Number of pending requests
        """
        gauge = self._gauges.get("orchestration_hitl_pending_count")
        if gauge:
            if self._use_otel:
                pass  # OpenTelemetry gauge handling
            else:
                gauge.set(count)

    def set_hitl_approval_rate(self, risk_level: str, rate: float) -> None:
        """
        Set HITL approval rate for a risk level.

        Args:
            risk_level: Risk level
            rate: Approval rate (0.0 to 1.0)
        """
        gauge = self._gauges.get("orchestration_hitl_approval_rate")
        if gauge:
            if self._use_otel:
                pass  # OpenTelemetry gauge handling
            else:
                gauge.set(rate, {"risk_level": risk_level})

    # =========================================================================
    # System Source Metrics Methods
    # =========================================================================

    def record_system_source_request(
        self,
        source_type: str,
        latency_seconds: float,
    ) -> None:
        """
        Record a system source request.

        Args:
            source_type: Type of system source (servicenow, prometheus)
            latency_seconds: Processing latency
        """
        # Record count
        counter = self._counters.get("orchestration_system_source_requests_total")
        if counter:
            if self._use_otel:
                counter.add(1, {"source_type": source_type})
            else:
                counter.add(1, {"source_type": source_type})

        # Record latency
        histogram = self._histograms.get("orchestration_system_source_latency_seconds")
        if histogram:
            if self._use_otel:
                histogram.record(latency_seconds, {"source_type": source_type})
            else:
                histogram.record(latency_seconds, {"source_type": source_type})

    def record_system_source_error(
        self,
        source_type: str,
        error_type: str,
    ) -> None:
        """
        Record a system source error.

        Args:
            source_type: Type of system source
            error_type: Type of error
        """
        counter = self._counters.get("orchestration_system_source_errors_total")
        if counter:
            labels = {"source_type": source_type, "error_type": error_type}
            if self._use_otel:
                counter.add(1, labels)
            else:
                counter.add(1, labels)

    # =========================================================================
    # Export Methods
    # =========================================================================

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get all collected metrics.

        Returns:
            Dictionary of metric values
        """
        if self._use_otel:
            # OpenTelemetry exports metrics through configured exporters
            return {"message": "Metrics exported via OpenTelemetry"}

        result = {
            "counters": {},
            "histograms": {},
            "gauges": {},
        }

        # Export counters
        for name, counter in self._counters.items():
            if isinstance(counter, FallbackCounter):
                result["counters"][name] = dict(counter._values)

        # Export histograms
        for name, histogram in self._histograms.items():
            if isinstance(histogram, FallbackHistogram):
                hist_data = {}
                for key, values in histogram._values.items():
                    key_str = str(dict(key)) if key else "default"
                    hist_data[key_str] = {
                        "count": len(values),
                        "p50": histogram.get_percentile(50, dict(key) if key else None),
                        "p95": histogram.get_percentile(95, dict(key) if key else None),
                        "p99": histogram.get_percentile(99, dict(key) if key else None),
                    }
                result["histograms"][name] = hist_data

        # Export gauges
        for name, gauge in self._gauges.items():
            if isinstance(gauge, FallbackGauge):
                result["gauges"][name] = dict(gauge._values)

        return result

    def reset_metrics(self) -> None:
        """Reset all metrics to initial state."""
        if not self._use_otel:
            for counter in self._counters.values():
                if isinstance(counter, FallbackCounter):
                    counter.reset()
            for histogram in self._histograms.values():
                if isinstance(histogram, FallbackHistogram):
                    histogram.reset()
            for gauge in self._gauges.values():
                if isinstance(gauge, FallbackGauge):
                    gauge.reset()

        logger.info("Metrics reset")


# =============================================================================
# Global Metrics Instance
# =============================================================================

# Global metrics collector instance
_metrics_collector: Optional[OrchestrationMetricsCollector] = None


def get_metrics_collector() -> OrchestrationMetricsCollector:
    """
    Get or create the global metrics collector.

    Returns:
        OrchestrationMetricsCollector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = OrchestrationMetricsCollector()
    return _metrics_collector


def reset_metrics_collector() -> None:
    """Reset the global metrics collector."""
    global _metrics_collector
    if _metrics_collector is not None:
        _metrics_collector.reset_metrics()
    _metrics_collector = None


# =============================================================================
# Decorator for Automatic Metrics Collection
# =============================================================================


def track_routing_metrics(
    layer: str,
) -> Callable:
    """
    Decorator to automatically track routing metrics.

    Args:
        layer: The routing layer being tracked

    Example:
        @track_routing_metrics("pattern")
        async def match(self, input: str) -> PatternMatchResult:
            ...
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            collector = get_metrics_collector()
            start_time = time.perf_counter()

            try:
                result = await func(*args, **kwargs)
                latency = time.perf_counter() - start_time

                # Try to extract metrics from result
                intent_category = "unknown"
                confidence = 0.0
                completeness = 1.0

                if hasattr(result, "intent_category") and result.intent_category:
                    intent_category = result.intent_category.value
                if hasattr(result, "confidence"):
                    confidence = result.confidence
                if hasattr(result, "completeness") and result.completeness:
                    completeness = result.completeness.completeness_score

                collector.record_routing_request(
                    intent_category=intent_category,
                    layer_used=layer,
                    latency_seconds=latency,
                    confidence=confidence,
                    completeness_score=completeness,
                )

                return result

            except Exception as e:
                latency = time.perf_counter() - start_time
                collector.record_routing_request(
                    intent_category="error",
                    layer_used=layer,
                    latency_seconds=latency,
                    confidence=0.0,
                    completeness_score=0.0,
                )
                raise

        return wrapper
    return decorator


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Constants
    "OPENTELEMETRY_AVAILABLE",
    # Types
    "MetricType",
    "MetricDefinition",
    # Metric Definitions
    "ROUTING_METRICS",
    "DIALOG_METRICS",
    "HITL_METRICS",
    "SYSTEM_SOURCE_METRICS",
    # Fallback Implementations
    "FallbackCounter",
    "FallbackHistogram",
    "FallbackGauge",
    # Collector
    "OrchestrationMetricsCollector",
    # Global Functions
    "get_metrics_collector",
    "reset_metrics_collector",
    # Decorators
    "track_routing_metrics",
]

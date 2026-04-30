"""
Unit Tests for Orchestration Metrics Module

Tests for FallbackCounter, FallbackHistogram, FallbackGauge,
MetricDefinition, OrchestrationMetricsCollector, and global functions.

Sprint 99: Phase 28 - Orchestration Metrics Testing
"""

import time
from unittest.mock import patch

import pytest

from src.integrations.orchestration.metrics import (
    DIALOG_METRICS,
    HITL_METRICS,
    ROUTING_METRICS,
    SYSTEM_SOURCE_METRICS,
    FallbackCounter,
    FallbackGauge,
    FallbackHistogram,
    MetricDefinition,
    MetricType,
    OrchestrationMetricsCollector,
    get_metrics_collector,
    reset_metrics_collector,
    track_routing_metrics,
)


# =============================================================================
# TestFallbackCounter
# =============================================================================


class TestFallbackCounter:
    """Tests for FallbackCounter implementation."""

    def test_add_and_get(self):
        """Test adding values and retrieving them without labels."""
        counter = FallbackCounter(
            name="test_counter",
            description="A test counter",
            labels=[],
        )

        counter.add(1)
        assert counter.get_value() == 1

        counter.add(5)
        assert counter.get_value() == 6

        counter.add(3)
        assert counter.get_value() == 9

    def test_add_with_labels(self):
        """Test adding values with different label combinations produces separate keys."""
        counter = FallbackCounter(
            name="test_counter",
            description="A test counter",
            labels=["intent_category", "layer_used"],
        )

        counter.add(1, {"intent_category": "incident", "layer_used": "pattern"})
        counter.add(2, {"intent_category": "incident", "layer_used": "pattern"})
        counter.add(3, {"intent_category": "request", "layer_used": "semantic"})

        assert counter.get_value(
            {"intent_category": "incident", "layer_used": "pattern"}
        ) == 3
        assert counter.get_value(
            {"intent_category": "request", "layer_used": "semantic"}
        ) == 3

        # Different labels should not mix
        assert counter.get_value(
            {"intent_category": "incident", "layer_used": "semantic"}
        ) == 0

    def test_get_default_zero(self):
        """Test that non-existent keys return 0."""
        counter = FallbackCounter(
            name="test_counter",
            description="A test counter",
            labels=["source"],
        )

        assert counter.get_value() == 0
        assert counter.get_value({"source": "nonexistent"}) == 0

    def test_reset(self):
        """Test that reset clears all stored values."""
        counter = FallbackCounter(
            name="test_counter",
            description="A test counter",
            labels=["layer"],
        )

        counter.add(10)
        counter.add(5, {"layer": "pattern"})
        counter.add(3, {"layer": "semantic"})

        assert counter.get_value() == 10
        assert counter.get_value({"layer": "pattern"}) == 5

        counter.reset()

        assert counter.get_value() == 0
        assert counter.get_value({"layer": "pattern"}) == 0
        assert counter.get_value({"layer": "semantic"}) == 0


# =============================================================================
# TestFallbackHistogram
# =============================================================================


class TestFallbackHistogram:
    """Tests for FallbackHistogram implementation."""

    def test_record_and_get(self):
        """Test recording values and retrieving them."""
        histogram = FallbackHistogram(
            name="test_histogram",
            description="A test histogram",
            labels=["source_type"],
        )

        histogram.record(0.1)
        histogram.record(0.5)
        histogram.record(1.0)

        values = histogram.get_values()
        assert len(values) == 3
        assert values == [0.1, 0.5, 1.0]

        # With labels
        histogram.record(2.0, {"source_type": "servicenow"})
        histogram.record(3.0, {"source_type": "servicenow"})

        labeled_values = histogram.get_values({"source_type": "servicenow"})
        assert len(labeled_values) == 2
        assert labeled_values == [2.0, 3.0]

        # Unlabeled values remain separate
        assert len(histogram.get_values()) == 3

    def test_percentile_calculation(self):
        """Test percentile calculation for p50 and p95."""
        histogram = FallbackHistogram(
            name="test_histogram",
            description="A test histogram",
            labels=[],
        )

        # Record 100 values from 1 to 100
        for i in range(1, 101):
            histogram.record(float(i))

        p50 = histogram.get_percentile(50)
        p95 = histogram.get_percentile(95)

        # p50 should be around median (50th value)
        assert 49.0 <= p50 <= 51.0

        # p95 should be around the 95th value
        assert 94.0 <= p95 <= 96.0

    def test_percentile_empty(self):
        """Test that percentile returns 0.0 for empty histogram."""
        histogram = FallbackHistogram(
            name="test_histogram",
            description="A test histogram",
            labels=[],
        )

        assert histogram.get_percentile(50) == 0.0
        assert histogram.get_percentile(95) == 0.0
        assert histogram.get_percentile(99) == 0.0

        # Also with non-existent labels
        assert histogram.get_percentile(50, {"source": "none"}) == 0.0

    def test_reset(self):
        """Test that reset clears all recorded values."""
        histogram = FallbackHistogram(
            name="test_histogram",
            description="A test histogram",
            labels=["layer"],
        )

        histogram.record(0.5)
        histogram.record(1.0, {"layer": "pattern"})

        assert len(histogram.get_values()) == 1
        assert len(histogram.get_values({"layer": "pattern"})) == 1

        histogram.reset()

        assert histogram.get_values() == []
        assert histogram.get_values({"layer": "pattern"}) == []
        assert histogram.get_percentile(50) == 0.0


# =============================================================================
# TestFallbackGauge
# =============================================================================


class TestFallbackGauge:
    """Tests for FallbackGauge implementation."""

    def test_set_and_get(self):
        """Test setting and getting gauge values."""
        gauge = FallbackGauge(
            name="test_gauge",
            description="A test gauge",
            labels=[],
        )

        gauge.set(42.0)
        assert gauge.get_value() == 42.0

        # Gauge overwrites previous value
        gauge.set(100.0)
        assert gauge.get_value() == 100.0

        gauge.set(0.0)
        assert gauge.get_value() == 0.0

    def test_set_with_labels(self):
        """Test setting gauge values with label-based keys."""
        gauge = FallbackGauge(
            name="test_gauge",
            description="A test gauge",
            labels=["risk_level"],
        )

        gauge.set(0.85, {"risk_level": "high"})
        gauge.set(0.95, {"risk_level": "low"})

        assert gauge.get_value({"risk_level": "high"}) == 0.85
        assert gauge.get_value({"risk_level": "low"}) == 0.95

        # Non-existent label returns default 0.0
        assert gauge.get_value({"risk_level": "medium"}) == 0.0

    def test_reset(self):
        """Test that reset clears all gauge values."""
        gauge = FallbackGauge(
            name="test_gauge",
            description="A test gauge",
            labels=["risk_level"],
        )

        gauge.set(10.0)
        gauge.set(0.75, {"risk_level": "high"})

        assert gauge.get_value() == 10.0
        assert gauge.get_value({"risk_level": "high"}) == 0.75

        gauge.reset()

        assert gauge.get_value() == 0.0
        assert gauge.get_value({"risk_level": "high"}) == 0.0


# =============================================================================
# TestMetricDefinitions
# =============================================================================


class TestMetricDefinitions:
    """Tests for MetricType enum and metric definition constants."""

    def test_metric_type_enum(self):
        """Test MetricType enum has all expected values."""
        assert MetricType.COUNTER.value == "counter"
        assert MetricType.HISTOGRAM.value == "histogram"
        assert MetricType.GAUGE.value == "gauge"

        # Verify exactly 3 members
        assert len(MetricType) == 3

    def test_metric_definitions_count(self):
        """Test that metric definitions sum to 15 total (4+4+4+3)."""
        assert len(ROUTING_METRICS) == 4
        assert len(DIALOG_METRICS) == 4
        assert len(HITL_METRICS) == 4
        assert len(SYSTEM_SOURCE_METRICS) == 3

        total = (
            len(ROUTING_METRICS)
            + len(DIALOG_METRICS)
            + len(HITL_METRICS)
            + len(SYSTEM_SOURCE_METRICS)
        )
        assert total == 15

        # Verify all are MetricDefinition instances
        for metric in ROUTING_METRICS + DIALOG_METRICS + HITL_METRICS + SYSTEM_SOURCE_METRICS:
            assert isinstance(metric, MetricDefinition)
            assert isinstance(metric.metric_type, MetricType)
            assert len(metric.name) > 0
            assert len(metric.description) > 0
            assert len(metric.unit) > 0


# =============================================================================
# TestOrchestrationMetricsCollector
# =============================================================================


class TestOrchestrationMetricsCollector:
    """Tests for OrchestrationMetricsCollector using fallback mode."""

    @pytest.fixture
    def collector(self) -> OrchestrationMetricsCollector:
        """Create a metrics collector in fallback mode."""
        return OrchestrationMetricsCollector(use_opentelemetry=False)

    def test_initialization_fallback(self, collector: OrchestrationMetricsCollector):
        """Test that fallback mode creates FallbackCounter/Histogram/Gauge instances."""
        assert collector._use_otel is False

        # Verify counters are FallbackCounter instances
        for name, counter in collector._counters.items():
            assert isinstance(counter, FallbackCounter), (
                f"Counter '{name}' should be FallbackCounter, got {type(counter)}"
            )

        # Verify histograms are FallbackHistogram instances
        for name, histogram in collector._histograms.items():
            assert isinstance(histogram, FallbackHistogram), (
                f"Histogram '{name}' should be FallbackHistogram, got {type(histogram)}"
            )

        # Verify gauges are FallbackGauge instances
        for name, gauge in collector._gauges.items():
            assert isinstance(gauge, FallbackGauge), (
                f"Gauge '{name}' should be FallbackGauge, got {type(gauge)}"
            )

        # Verify the expected number of instruments
        # Counters: routing_requests_total, dialog_rounds_total, hitl_requests_total,
        #           system_source_requests_total, system_source_errors_total = 5
        assert len(collector._counters) == 5

        # Histograms: routing_latency, routing_confidence, completeness_score,
        #             dialog_duration, hitl_approval_time, system_source_latency = 6
        assert len(collector._histograms) == 6

        # Gauges: dialog_completion_rate, dialog_active_count,
        #         hitl_pending_count, hitl_approval_rate = 4
        assert len(collector._gauges) == 4

    def test_record_routing_request(self, collector: OrchestrationMetricsCollector):
        """Test recording a routing request updates counter and histograms."""
        collector.record_routing_request(
            intent_category="incident",
            layer_used="pattern",
            latency_seconds=0.005,
            confidence=0.95,
            completeness_score=0.8,
        )

        # Verify counter incremented
        counter = collector._counters["orchestration_routing_requests_total"]
        assert counter.get_value(
            {"intent_category": "incident", "layer_used": "pattern"}
        ) == 1

        # Verify latency histogram recorded
        latency_hist = collector._histograms["orchestration_routing_latency_seconds"]
        latency_values = latency_hist.get_values({"layer_used": "pattern"})
        assert len(latency_values) == 1
        assert latency_values[0] == pytest.approx(0.005)

        # Verify confidence histogram recorded
        confidence_hist = collector._histograms["orchestration_routing_confidence"]
        confidence_values = confidence_hist.get_values({"intent_category": "incident"})
        assert len(confidence_values) == 1
        assert confidence_values[0] == pytest.approx(0.95)

        # Verify completeness histogram recorded
        completeness_hist = collector._histograms["orchestration_completeness_score"]
        completeness_values = completeness_hist.get_values({"intent_category": "incident"})
        assert len(completeness_values) == 1
        assert completeness_values[0] == pytest.approx(0.8)

        # Record another request and verify accumulation
        collector.record_routing_request(
            intent_category="incident",
            layer_used="pattern",
            latency_seconds=0.010,
            confidence=0.88,
        )

        assert counter.get_value(
            {"intent_category": "incident", "layer_used": "pattern"}
        ) == 2

    def test_routing_timer(self, collector: OrchestrationMetricsCollector):
        """Test routing_timer context manager records latency."""
        with collector.routing_timer("semantic"):
            time.sleep(0.05)  # Sleep 50ms

        latency_hist = collector._histograms["orchestration_routing_latency_seconds"]
        values = latency_hist.get_values({"layer_used": "semantic"})

        assert len(values) == 1
        # Should be at least 50ms but allow some tolerance
        assert values[0] >= 0.04
        assert values[0] < 1.0  # Should not exceed 1 second

    def test_record_dialog_round(self, collector: OrchestrationMetricsCollector):
        """Test recording dialog rounds increments the counter."""
        collector.record_dialog_round(dialog_id="dialog-001", phase="greeting")
        collector.record_dialog_round(dialog_id="dialog-001", phase="info_gathering")
        collector.record_dialog_round(dialog_id="dialog-002", phase="greeting")

        counter = collector._counters["orchestration_dialog_rounds_total"]

        assert counter.get_value(
            {"dialog_id": "dialog-001", "phase": "greeting"}
        ) == 1
        assert counter.get_value(
            {"dialog_id": "dialog-001", "phase": "info_gathering"}
        ) == 1
        assert counter.get_value(
            {"dialog_id": "dialog-002", "phase": "greeting"}
        ) == 1

    def test_record_dialog_completion(self, collector: OrchestrationMetricsCollector):
        """Test recording dialog completion stores duration in histogram."""
        collector.record_dialog_completion(outcome="complete", duration_seconds=45.0)
        collector.record_dialog_completion(outcome="timeout", duration_seconds=120.0)
        collector.record_dialog_completion(outcome="complete", duration_seconds=30.0)

        histogram = collector._histograms["orchestration_dialog_duration_seconds"]

        complete_values = histogram.get_values({"outcome": "complete"})
        assert len(complete_values) == 2
        assert complete_values[0] == pytest.approx(45.0)
        assert complete_values[1] == pytest.approx(30.0)

        timeout_values = histogram.get_values({"outcome": "timeout"})
        assert len(timeout_values) == 1
        assert timeout_values[0] == pytest.approx(120.0)

    def test_set_active_dialogs_and_completion_rate(
        self, collector: OrchestrationMetricsCollector
    ):
        """Test setting gauge values for active dialogs and completion rate."""
        collector.set_active_dialogs(5)
        active_gauge = collector._gauges["orchestration_dialog_active_count"]
        assert active_gauge.get_value() == 5.0

        # Overwrite with new value
        collector.set_active_dialogs(3)
        assert active_gauge.get_value() == 3.0

        collector.set_dialog_completion_rate(0.85)
        rate_gauge = collector._gauges["orchestration_dialog_completion_rate"]
        assert rate_gauge.get_value() == pytest.approx(0.85)

        # Update rate
        collector.set_dialog_completion_rate(0.92)
        assert rate_gauge.get_value() == pytest.approx(0.92)

    def test_record_hitl_request(self, collector: OrchestrationMetricsCollector):
        """Test recording HITL requests with risk_level and status labels."""
        collector.record_hitl_request(risk_level="high", status="pending")
        collector.record_hitl_request(risk_level="high", status="approved")
        collector.record_hitl_request(risk_level="medium", status="pending")
        collector.record_hitl_request(risk_level="high", status="pending")

        counter = collector._counters["orchestration_hitl_requests_total"]

        assert counter.get_value(
            {"risk_level": "high", "status": "pending"}
        ) == 2
        assert counter.get_value(
            {"risk_level": "high", "status": "approved"}
        ) == 1
        assert counter.get_value(
            {"risk_level": "medium", "status": "pending"}
        ) == 1

        # Test HITL approval time histogram
        collector.record_hitl_approval_time(
            risk_level="high", approval_time_seconds=300.0
        )
        collector.record_hitl_approval_time(
            risk_level="high", approval_time_seconds=600.0
        )

        histogram = collector._histograms["orchestration_hitl_approval_time_seconds"]
        values = histogram.get_values({"risk_level": "high"})
        assert len(values) == 2
        assert values[0] == pytest.approx(300.0)
        assert values[1] == pytest.approx(600.0)

        # Test HITL pending count gauge
        collector.set_hitl_pending_count(7)
        pending_gauge = collector._gauges["orchestration_hitl_pending_count"]
        assert pending_gauge.get_value() == 7.0

        # Test HITL approval rate gauge
        collector.set_hitl_approval_rate(risk_level="high", rate=0.80)
        rate_gauge = collector._gauges["orchestration_hitl_approval_rate"]
        assert rate_gauge.get_value({"risk_level": "high"}) == pytest.approx(0.80)

    def test_record_system_source_request_and_error(
        self, collector: OrchestrationMetricsCollector
    ):
        """Test recording system source requests and errors."""
        # Record requests
        collector.record_system_source_request(
            source_type="servicenow", latency_seconds=0.250
        )
        collector.record_system_source_request(
            source_type="prometheus", latency_seconds=0.100
        )
        collector.record_system_source_request(
            source_type="servicenow", latency_seconds=0.300
        )

        request_counter = collector._counters[
            "orchestration_system_source_requests_total"
        ]
        assert request_counter.get_value({"source_type": "servicenow"}) == 2
        assert request_counter.get_value({"source_type": "prometheus"}) == 1

        # Verify latency histogram
        latency_hist = collector._histograms[
            "orchestration_system_source_latency_seconds"
        ]
        sn_values = latency_hist.get_values({"source_type": "servicenow"})
        assert len(sn_values) == 2
        assert sn_values[0] == pytest.approx(0.250)
        assert sn_values[1] == pytest.approx(0.300)

        prom_values = latency_hist.get_values({"source_type": "prometheus"})
        assert len(prom_values) == 1
        assert prom_values[0] == pytest.approx(0.100)

        # Record errors
        collector.record_system_source_error(
            source_type="servicenow", error_type="timeout"
        )
        collector.record_system_source_error(
            source_type="servicenow", error_type="auth_failure"
        )
        collector.record_system_source_error(
            source_type="servicenow", error_type="timeout"
        )

        error_counter = collector._counters[
            "orchestration_system_source_errors_total"
        ]
        assert error_counter.get_value(
            {"source_type": "servicenow", "error_type": "timeout"}
        ) == 2
        assert error_counter.get_value(
            {"source_type": "servicenow", "error_type": "auth_failure"}
        ) == 1
        assert error_counter.get_value(
            {"source_type": "prometheus", "error_type": "timeout"}
        ) == 0


# =============================================================================
# TestMetricsExport
# =============================================================================


class TestMetricsExport:
    """Tests for metrics export and reset functionality."""

    @pytest.fixture
    def collector(self) -> OrchestrationMetricsCollector:
        """Create a metrics collector in fallback mode."""
        return OrchestrationMetricsCollector(use_opentelemetry=False)

    def test_get_metrics(self, collector: OrchestrationMetricsCollector):
        """Test get_metrics returns dict with counters/histograms/gauges structure."""
        # Populate some metrics
        collector.record_routing_request(
            intent_category="incident",
            layer_used="pattern",
            latency_seconds=0.008,
            confidence=0.92,
        )
        collector.set_active_dialogs(3)
        collector.record_hitl_request(risk_level="high", status="pending")

        metrics = collector.get_metrics()

        # Verify top-level structure
        assert "counters" in metrics
        assert "histograms" in metrics
        assert "gauges" in metrics

        # Verify counters are populated
        assert isinstance(metrics["counters"], dict)
        assert "orchestration_routing_requests_total" in metrics["counters"]
        assert "orchestration_hitl_requests_total" in metrics["counters"]

        # Verify histograms are populated with count and percentiles
        assert isinstance(metrics["histograms"], dict)
        assert "orchestration_routing_latency_seconds" in metrics["histograms"]
        latency_data = metrics["histograms"]["orchestration_routing_latency_seconds"]
        # The key in the export is the string representation of the label dict
        for key_str, hist_info in latency_data.items():
            assert "count" in hist_info
            assert "p50" in hist_info
            assert "p95" in hist_info
            assert "p99" in hist_info
            assert hist_info["count"] >= 1

        # Verify gauges are populated
        assert isinstance(metrics["gauges"], dict)
        assert "orchestration_dialog_active_count" in metrics["gauges"]

    def test_reset_metrics(self, collector: OrchestrationMetricsCollector):
        """Test that reset_metrics clears all counters, histograms, and gauges."""
        # Populate metrics
        collector.record_routing_request(
            intent_category="incident",
            layer_used="pattern",
            latency_seconds=0.005,
            confidence=0.90,
        )
        collector.record_dialog_round(dialog_id="d-1", phase="greeting")
        collector.set_active_dialogs(5)
        collector.record_hitl_request(risk_level="high", status="pending")
        collector.record_system_source_request(
            source_type="servicenow", latency_seconds=0.2
        )

        # Verify metrics are populated
        routing_counter = collector._counters["orchestration_routing_requests_total"]
        assert routing_counter.get_value(
            {"intent_category": "incident", "layer_used": "pattern"}
        ) == 1

        active_gauge = collector._gauges["orchestration_dialog_active_count"]
        assert active_gauge.get_value() == 5.0

        latency_hist = collector._histograms["orchestration_routing_latency_seconds"]
        assert len(latency_hist.get_values({"layer_used": "pattern"})) == 1

        # Reset all metrics
        collector.reset_metrics()

        # Verify all metrics are cleared
        assert routing_counter.get_value(
            {"intent_category": "incident", "layer_used": "pattern"}
        ) == 0
        assert active_gauge.get_value() == 0.0
        assert latency_hist.get_values({"layer_used": "pattern"}) == []

        # Verify get_metrics returns empty structures
        metrics = collector.get_metrics()
        for counter_name, counter_data in metrics["counters"].items():
            assert counter_data == {}, (
                f"Counter '{counter_name}' should be empty after reset"
            )
        for hist_name, hist_data in metrics["histograms"].items():
            assert hist_data == {}, (
                f"Histogram '{hist_name}' should be empty after reset"
            )
        for gauge_name, gauge_data in metrics["gauges"].items():
            assert gauge_data == {}, (
                f"Gauge '{gauge_name}' should be empty after reset"
            )


# =============================================================================
# TestGlobalFunctions
# =============================================================================


class TestGlobalFunctions:
    """Tests for module-level singleton and utility functions."""

    def setup_method(self):
        """Reset global state before each test."""
        reset_metrics_collector()

    def teardown_method(self):
        """Clean up global state after each test."""
        reset_metrics_collector()

    def test_get_metrics_collector_singleton(self):
        """Test that get_metrics_collector returns the same instance on repeated calls."""
        collector_a = get_metrics_collector()
        collector_b = get_metrics_collector()

        assert collector_a is collector_b
        assert isinstance(collector_a, OrchestrationMetricsCollector)

    def test_reset_metrics_collector(self):
        """Test that reset_metrics_collector creates a new instance on next call."""
        collector_before = get_metrics_collector()

        # Record some data
        collector_before.record_routing_request(
            intent_category="query",
            layer_used="llm",
            latency_seconds=1.5,
            confidence=0.70,
        )

        reset_metrics_collector()

        collector_after = get_metrics_collector()

        # Should be a different instance
        assert collector_before is not collector_after
        assert isinstance(collector_after, OrchestrationMetricsCollector)

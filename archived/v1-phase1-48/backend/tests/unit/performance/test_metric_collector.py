"""
Metric Collector Unit Tests
Sprint 12 - S12-7: Testing

Tests for:
- MetricSample dataclass
- AggregationType enum
- AggregatedMetric dataclass
- SystemMetrics dataclass
- ApplicationMetrics dataclass
- MetricCollector class
  - start() / stop()
  - collect_system_metrics()
  - record()
  - aggregate()
  - set_threshold() / get_alerts()
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch

from src.core.performance.metric_collector import (
    MetricSample,
    AggregationType,
    AggregatedMetric,
    SystemMetrics,
    ApplicationMetrics,
    MetricCollector
)


class TestMetricSample:
    """MetricSample dataclass tests"""

    def test_create_sample(self):
        """Test creating a MetricSample"""
        sample = MetricSample(
            name="cpu_usage",
            value=45.5,
            timestamp=datetime.utcnow(),
            tags={"host": "server1"}
        )

        assert sample.name == "cpu_usage"
        assert sample.value == 45.5
        assert sample.tags == {"host": "server1"}

    def test_sample_default_tags(self):
        """Test sample with default empty tags"""
        sample = MetricSample(
            name="memory",
            value=60.0,
            timestamp=datetime.utcnow()
        )

        assert sample.tags == {}


class TestAggregationType:
    """AggregationType enum tests"""

    def test_aggregation_types(self):
        """Test all aggregation types exist"""
        assert AggregationType.AVG == "avg"
        assert AggregationType.SUM == "sum"
        assert AggregationType.MIN == "min"
        assert AggregationType.MAX == "max"
        assert AggregationType.COUNT == "count"
        assert AggregationType.P50 == "p50"
        assert AggregationType.P95 == "p95"
        assert AggregationType.P99 == "p99"

    def test_aggregation_count(self):
        """Test AggregationType has correct number of values"""
        assert len(AggregationType) == 8


class TestAggregatedMetric:
    """AggregatedMetric dataclass tests"""

    def test_create_aggregated_metric(self):
        """Test creating an AggregatedMetric"""
        metric = AggregatedMetric(
            name="latency",
            aggregation_type=AggregationType.AVG,
            value=125.5,
            sample_count=100,
            time_window_seconds=60
        )

        assert metric.name == "latency"
        assert metric.aggregation_type == AggregationType.AVG
        assert metric.value == 125.5
        assert metric.sample_count == 100
        assert metric.time_window_seconds == 60


class TestSystemMetrics:
    """SystemMetrics dataclass tests"""

    def test_create_system_metrics(self):
        """Test creating SystemMetrics"""
        metrics = SystemMetrics(
            cpu_percent=45.0,
            memory_percent=60.0,
            disk_percent=35.0,
            network_bytes_sent=1000000,
            network_bytes_recv=2000000
        )

        assert metrics.cpu_percent == 45.0
        assert metrics.memory_percent == 60.0
        assert metrics.disk_percent == 35.0
        assert metrics.network_bytes_sent == 1000000
        assert metrics.network_bytes_recv == 2000000


class TestApplicationMetrics:
    """ApplicationMetrics dataclass tests"""

    def test_create_app_metrics(self):
        """Test creating ApplicationMetrics"""
        metrics = ApplicationMetrics(
            request_count=1000,
            error_count=10,
            avg_latency_ms=150.0,
            active_connections=50
        )

        assert metrics.request_count == 1000
        assert metrics.error_count == 10
        assert metrics.avg_latency_ms == 150.0
        assert metrics.active_connections == 50


class TestMetricCollector:
    """MetricCollector class tests"""

    @pytest.fixture
    def collector(self):
        """Create a fresh MetricCollector"""
        return MetricCollector(collection_interval=1.0)

    def test_init(self, collector):
        """Test collector initialization"""
        assert collector._collection_interval == 1.0
        assert collector._running is False
        assert collector._metrics == {}
        assert collector._thresholds == {}
        assert collector._alerts == []

    @pytest.mark.asyncio
    async def test_start_stop(self, collector):
        """Test starting and stopping collector"""
        await collector.start()
        assert collector._running is True

        await collector.stop()
        assert collector._running is False

    @pytest.mark.asyncio
    async def test_collect_system_metrics(self, collector):
        """Test collecting system metrics"""
        with patch('psutil.cpu_percent', return_value=50.0):
            with patch('psutil.virtual_memory') as mock_mem:
                mock_mem.return_value = Mock(percent=60.0)
                with patch('psutil.disk_usage') as mock_disk:
                    mock_disk.return_value = Mock(percent=40.0)
                    with patch('psutil.net_io_counters') as mock_net:
                        mock_net.return_value = Mock(
                            bytes_sent=1000,
                            bytes_recv=2000
                        )

                        metrics = await collector.collect_system_metrics()

                        assert metrics.cpu_percent == 50.0
                        assert metrics.memory_percent == 60.0
                        assert metrics.disk_percent == 40.0

    def test_record_metric(self, collector):
        """Test recording a metric"""
        sample = collector.record(
            name="test_metric",
            value=100.0,
            tags={"env": "test"}
        )

        assert sample.name == "test_metric"
        assert sample.value == 100.0
        assert "test_metric" in collector._metrics
        assert len(collector._metrics["test_metric"]) == 1

    def test_record_multiple_metrics(self, collector):
        """Test recording multiple metrics"""
        for i in range(10):
            collector.record("latency", float(100 + i))

        assert len(collector._metrics["latency"]) == 10

    def test_aggregate_avg(self, collector):
        """Test AVG aggregation"""
        for i in range(5):
            collector.record("test", float(i * 10))  # 0, 10, 20, 30, 40

        result = collector.aggregate("test", AggregationType.AVG)

        assert result.aggregation_type == AggregationType.AVG
        assert result.value == 20.0  # Average of 0,10,20,30,40

    def test_aggregate_sum(self, collector):
        """Test SUM aggregation"""
        for i in range(5):
            collector.record("test", float(i + 1))  # 1, 2, 3, 4, 5

        result = collector.aggregate("test", AggregationType.SUM)

        assert result.value == 15.0

    def test_aggregate_min(self, collector):
        """Test MIN aggregation"""
        collector.record("test", 50.0)
        collector.record("test", 10.0)
        collector.record("test", 30.0)

        result = collector.aggregate("test", AggregationType.MIN)

        assert result.value == 10.0

    def test_aggregate_max(self, collector):
        """Test MAX aggregation"""
        collector.record("test", 50.0)
        collector.record("test", 10.0)
        collector.record("test", 30.0)

        result = collector.aggregate("test", AggregationType.MAX)

        assert result.value == 50.0

    def test_aggregate_count(self, collector):
        """Test COUNT aggregation"""
        for _ in range(7):
            collector.record("test", 1.0)

        result = collector.aggregate("test", AggregationType.COUNT)

        assert result.value == 7

    def test_aggregate_percentiles(self, collector):
        """Test percentile aggregations"""
        for i in range(100):
            collector.record("test", float(i + 1))  # 1 to 100

        p50 = collector.aggregate("test", AggregationType.P50)
        p95 = collector.aggregate("test", AggregationType.P95)
        p99 = collector.aggregate("test", AggregationType.P99)

        assert p50.value == 50.0
        assert p95.value == 95.0
        assert p99.value == 99.0

    def test_aggregate_with_time_window(self, collector):
        """Test aggregation with time window"""
        for i in range(10):
            collector.record("test", float(i))

        result = collector.aggregate(
            "test",
            AggregationType.AVG,
            time_window_seconds=60
        )

        assert result.time_window_seconds == 60

    def test_aggregate_nonexistent_metric(self, collector):
        """Test aggregating non-existent metric"""
        result = collector.aggregate("nonexistent", AggregationType.AVG)

        assert result is None

    def test_set_threshold(self, collector):
        """Test setting a threshold"""
        collector.set_threshold("cpu", min_value=0.0, max_value=80.0)

        assert "cpu" in collector._thresholds
        assert collector._thresholds["cpu"]["min"] == 0.0
        assert collector._thresholds["cpu"]["max"] == 80.0

    def test_threshold_violation_max(self, collector):
        """Test threshold violation triggers alert (max)"""
        collector.set_threshold("cpu", max_value=80.0)
        collector.record("cpu", 90.0)  # Exceeds threshold

        alerts = collector.get_alerts()

        assert len(alerts) == 1
        assert alerts[0]["metric_name"] == "cpu"
        assert alerts[0]["value"] == 90.0
        assert "exceeded" in alerts[0]["message"].lower()

    def test_threshold_violation_min(self, collector):
        """Test threshold violation triggers alert (min)"""
        collector.set_threshold("availability", min_value=99.0)
        collector.record("availability", 95.0)  # Below threshold

        alerts = collector.get_alerts()

        assert len(alerts) == 1
        assert alerts[0]["metric_name"] == "availability"

    def test_get_alerts_clear(self, collector):
        """Test getting and clearing alerts"""
        collector.set_threshold("test", max_value=50.0)
        collector.record("test", 60.0)

        alerts1 = collector.get_alerts(clear=True)
        alerts2 = collector.get_alerts()

        assert len(alerts1) == 1
        assert len(alerts2) == 0  # Cleared

    def test_no_alert_within_threshold(self, collector):
        """Test no alert when within threshold"""
        collector.set_threshold("cpu", min_value=0.0, max_value=100.0)
        collector.record("cpu", 50.0)  # Within threshold

        alerts = collector.get_alerts()

        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_collection_loop(self, collector):
        """Test the collection loop runs"""
        collection_count = 0

        original_collect = collector.collect_system_metrics

        async def mock_collect():
            nonlocal collection_count
            collection_count += 1
            return SystemMetrics(
                cpu_percent=50.0,
                memory_percent=60.0,
                disk_percent=40.0,
                network_bytes_sent=0,
                network_bytes_recv=0
            )

        collector.collect_system_metrics = mock_collect
        collector._collection_interval = 0.1  # Fast interval for test

        await collector.start()
        await asyncio.sleep(0.35)  # Allow ~3 collections
        await collector.stop()

        assert collection_count >= 2


class TestMetricCollectorIntegration:
    """Integration tests for MetricCollector"""

    @pytest.mark.asyncio
    async def test_full_collection_workflow(self):
        """Test complete collection workflow"""
        collector = MetricCollector(collection_interval=0.1)

        # Set up thresholds
        collector.set_threshold("cpu_percent", max_value=90.0)
        collector.set_threshold("memory_percent", max_value=85.0)

        # Record some metrics
        for i in range(10):
            collector.record("api_latency", float(100 + i * 10))
            collector.record("request_count", float(i + 1))

        # Check aggregations
        avg_latency = collector.aggregate("api_latency", AggregationType.AVG)
        total_requests = collector.aggregate("request_count", AggregationType.SUM)

        assert avg_latency.value == 145.0  # avg of 100,110,120...190
        assert total_requests.value == 55.0  # sum of 1+2+...+10

    @pytest.mark.asyncio
    async def test_alert_management(self):
        """Test alert generation and management"""
        collector = MetricCollector()

        collector.set_threshold("error_rate", max_value=0.05)

        # Simulate error rate spikes
        collector.record("error_rate", 0.02)  # OK
        collector.record("error_rate", 0.08)  # Alert!
        collector.record("error_rate", 0.03)  # OK
        collector.record("error_rate", 0.10)  # Alert!

        alerts = collector.get_alerts()

        assert len(alerts) == 2

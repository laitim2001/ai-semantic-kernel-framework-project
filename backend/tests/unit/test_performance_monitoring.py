"""
Unit tests for Performance Monitoring (S3-8)

Tests the PerformanceCollector and performance API endpoints.
"""
import pytest
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.api.v1.performance.routes import (
    PerformanceCollector,
    get_performance_collector,
    reset_performance_collector,
    RequestMetric,
    PercentileStats,
)


class TestPerformanceCollectorSingleton:
    """Test cases for PerformanceCollector singleton pattern."""

    @pytest.fixture(autouse=True)
    def reset(self):
        """Reset singleton before each test."""
        PerformanceCollector._instance = None
        yield
        PerformanceCollector._instance = None

    def test_singleton_instance(self):
        """Test that PerformanceCollector is a singleton."""
        c1 = PerformanceCollector()
        c2 = PerformanceCollector()
        assert c1 is c2

    def test_get_performance_collector(self):
        """Test get_performance_collector returns singleton."""
        c1 = get_performance_collector()
        c2 = get_performance_collector()
        assert c1 is c2

    def test_reset_clears_data(self):
        """Test that reset clears all data."""
        collector = get_performance_collector()
        collector.record_request("GET", "/test", 200, 50.0)

        reset_performance_collector()

        summary = collector.get_summary()
        assert summary["total_requests"] == 0


class TestRequestRecording:
    """Test cases for request recording."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up for each test."""
        PerformanceCollector._instance = None
        self.collector = get_performance_collector()
        yield
        PerformanceCollector._instance = None

    def test_record_request_basic(self):
        """Test recording a basic request."""
        self.collector.record_request("GET", "/api/test", 200, 50.0)

        summary = self.collector.get_summary()
        assert summary["total_requests"] == 1
        assert summary["requests_by_method"]["GET"] == 1
        assert summary["requests_by_status"][200] == 1

    def test_record_error_request(self):
        """Test recording an error request."""
        self.collector.record_request("POST", "/api/test", 500, 100.0)

        summary = self.collector.get_summary()
        assert summary["total_requests"] == 1
        assert summary["total_errors"] == 1

    def test_record_multiple_requests(self):
        """Test recording multiple requests."""
        self.collector.record_request("GET", "/api/test", 200, 50.0)
        self.collector.record_request("POST", "/api/test", 201, 75.0)
        self.collector.record_request("GET", "/api/other", 404, 25.0)

        summary = self.collector.get_summary()
        assert summary["total_requests"] == 3
        assert summary["requests_by_method"]["GET"] == 2
        assert summary["requests_by_method"]["POST"] == 1

    def test_record_request_tracks_path(self):
        """Test that requests are tracked by path."""
        self.collector.record_request("GET", "/api/workflows", 200, 50.0)
        self.collector.record_request("GET", "/api/workflows", 200, 60.0)
        self.collector.record_request("GET", "/api/users", 200, 40.0)

        summary = self.collector.get_summary()
        assert "/api/workflows" in summary["top_endpoints"]
        assert summary["top_endpoints"]["/api/workflows"] == 2


class TestPercentileStats:
    """Test cases for percentile statistics."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up for each test."""
        PerformanceCollector._instance = None
        self.collector = get_performance_collector()
        yield
        PerformanceCollector._instance = None

    def test_empty_percentiles(self):
        """Test percentiles with no data."""
        stats = self.collector.get_percentile_stats(window_minutes=5)

        assert stats.p50 == 0
        assert stats.p95 == 0
        assert stats.p99 == 0
        assert stats.count == 0

    def test_percentile_calculation(self):
        """Test percentile calculation with data."""
        # Record 100 requests with latencies 1-100ms
        for i in range(1, 101):
            self.collector.record_request("GET", "/test", 200, float(i))

        stats = self.collector.get_percentile_stats(window_minutes=60)

        assert stats.count == 100
        assert 45 <= stats.p50 <= 55  # ~50
        assert 90 <= stats.p95 <= 100  # ~95
        assert 95 <= stats.p99 <= 100  # ~99

    def test_percentile_with_custom_latencies(self):
        """Test percentile calculation with custom latencies."""
        latencies = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

        stats = self.collector.get_percentile_stats(latencies=latencies)

        assert stats.count == 10
        assert stats.mean == 55.0

    def test_mean_calculation(self):
        """Test mean calculation."""
        self.collector.record_request("GET", "/test", 200, 100.0)
        self.collector.record_request("GET", "/test", 200, 200.0)
        self.collector.record_request("GET", "/test", 200, 300.0)

        stats = self.collector.get_percentile_stats(window_minutes=60)

        assert stats.mean == 200.0


class TestThroughput:
    """Test cases for throughput calculation."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up for each test."""
        PerformanceCollector._instance = None
        self.collector = get_performance_collector()
        yield
        PerformanceCollector._instance = None

    def test_rps_empty(self):
        """Test RPS with no data."""
        rps = self.collector.get_rps(window_seconds=60)
        assert rps == 0

    def test_rps_calculation(self):
        """Test RPS calculation."""
        # Record 60 requests (should be 1 RPS over 60 seconds)
        for _ in range(60):
            self.collector.record_request("GET", "/test", 200, 50.0)

        rps = self.collector.get_rps(window_seconds=60)

        # All 60 requests in window
        assert rps == 1.0


class TestErrorRate:
    """Test cases for error rate calculation."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up for each test."""
        PerformanceCollector._instance = None
        self.collector = get_performance_collector()
        yield
        PerformanceCollector._instance = None

    def test_error_rate_empty(self):
        """Test error rate with no data."""
        rate = self.collector.get_error_rate(window_minutes=5)
        assert rate == 0.0

    def test_error_rate_no_errors(self):
        """Test error rate with no errors."""
        for _ in range(10):
            self.collector.record_request("GET", "/test", 200, 50.0)

        rate = self.collector.get_error_rate(window_minutes=60)
        assert rate == 0.0

    def test_error_rate_calculation(self):
        """Test error rate calculation."""
        # 90 successful, 10 errors = 10% error rate
        for _ in range(90):
            self.collector.record_request("GET", "/test", 200, 50.0)
        for _ in range(10):
            self.collector.record_request("GET", "/test", 500, 100.0)

        rate = self.collector.get_error_rate(window_minutes=60)
        assert rate == 10.0

    def test_error_rate_5xx_only(self):
        """Test that only 5xx counts as errors."""
        self.collector.record_request("GET", "/test", 200, 50.0)
        self.collector.record_request("GET", "/test", 400, 50.0)  # Client error
        self.collector.record_request("GET", "/test", 404, 50.0)  # Not found
        self.collector.record_request("GET", "/test", 500, 50.0)  # Server error

        rate = self.collector.get_error_rate(window_minutes=60)
        assert rate == 25.0  # 1 out of 4


class TestRequestMetricDataclass:
    """Test cases for RequestMetric dataclass."""

    def test_request_metric_creation(self):
        """Test RequestMetric creation."""
        metric = RequestMetric(
            method="GET",
            path="/api/test",
            status_code=200,
            duration_ms=50.0,
        )

        assert metric.method == "GET"
        assert metric.path == "/api/test"
        assert metric.status_code == 200
        assert metric.duration_ms == 50.0
        assert isinstance(metric.timestamp, datetime)

    def test_request_metric_with_timestamp(self):
        """Test RequestMetric with explicit timestamp."""
        ts = datetime(2025, 1, 1, 12, 0, 0)
        metric = RequestMetric(
            method="POST",
            path="/api/users",
            status_code=201,
            duration_ms=75.0,
            timestamp=ts,
        )

        assert metric.timestamp == ts


class TestPercentileStatsDataclass:
    """Test cases for PercentileStats dataclass."""

    def test_percentile_stats_creation(self):
        """Test PercentileStats creation."""
        stats = PercentileStats(
            p50=50.0,
            p75=75.0,
            p90=90.0,
            p95=95.0,
            p99=99.0,
            mean=55.0,
            count=100,
        )

        assert stats.p50 == 50.0
        assert stats.p95 == 95.0
        assert stats.mean == 55.0
        assert stats.count == 100


class TestThreadSafety:
    """Test cases for thread safety."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up for each test."""
        PerformanceCollector._instance = None
        self.collector = get_performance_collector()
        yield
        PerformanceCollector._instance = None

    def test_concurrent_recording(self):
        """Test concurrent request recording."""
        errors = []

        def worker(thread_id):
            try:
                for i in range(100):
                    self.collector.record_request(
                        f"GET",
                        f"/api/thread-{thread_id}",
                        200,
                        float(i),
                    )
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=worker, args=(i,))
            for i in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

        summary = self.collector.get_summary()
        assert summary["total_requests"] == 500  # 5 threads * 100 requests


class TestHistoryLimit:
    """Test cases for history limit."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up for each test."""
        PerformanceCollector._instance = None
        self.collector = get_performance_collector()
        self.collector._max_history = 100  # Set small limit for testing
        yield
        PerformanceCollector._instance = None

    def test_history_trimming(self):
        """Test that history is trimmed to max size."""
        # Record more than max history
        for i in range(150):
            self.collector.record_request("GET", "/test", 200, float(i))

        with self.collector._metrics_lock:
            assert len(self.collector._request_metrics) == 100


class TestResponseModels:
    """Test cases for response models."""

    def test_routes_import(self):
        """Test that routes can be imported."""
        from src.api.v1.performance.routes import router
        assert router is not None

    def test_response_models(self):
        """Test Pydantic response models."""
        from src.api.v1.performance.routes import (
            LatencyStatsResponse,
            ThroughputResponse,
            ErrorRateResponse,
            ResourceUsageResponse,
            DBPoolStatusResponse,
            PerformanceSummaryResponse,
            HealthResponse,
        )

        # Test LatencyStatsResponse
        latency = LatencyStatsResponse(
            p50_ms=50.0,
            p75_ms=75.0,
            p90_ms=90.0,
            p95_ms=95.0,
            p99_ms=99.0,
            mean_ms=55.0,
            sample_count=100,
        )
        assert latency.p95_ms == 95.0

        # Test ThroughputResponse
        throughput = ThroughputResponse(
            requests_per_second=100.0,
            requests_per_minute=6000.0,
            total_requests=10000,
        )
        assert throughput.requests_per_second == 100.0

        # Test ErrorRateResponse
        error_rate = ErrorRateResponse(
            error_rate_percent=1.5,
            total_errors=15,
            total_requests=1000,
        )
        assert error_rate.error_rate_percent == 1.5

        # Test ResourceUsageResponse
        resources = ResourceUsageResponse(
            cpu_percent=25.0,
            memory_percent=50.0,
            memory_mb=512.0,
            thread_count=10,
            open_files=5,
        )
        assert resources.cpu_percent == 25.0

        # Test DBPoolStatusResponse
        db_pool = DBPoolStatusResponse(
            pool_size=20,
            checked_out=5,
            checked_in=15,
            overflow=0,
            status="healthy",
        )
        assert db_pool.status == "healthy"

        # Test HealthResponse
        health = HealthResponse(
            status="healthy",
            p95_latency_ms=50.0,
            error_rate_percent=0.5,
            cpu_percent=25.0,
            memory_percent=50.0,
            healthy=True,
        )
        assert health.healthy is True


class TestEndpointPerformance:
    """Test cases for per-endpoint performance tracking."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up for each test."""
        PerformanceCollector._instance = None
        self.collector = get_performance_collector()
        yield
        PerformanceCollector._instance = None

    def test_endpoint_latency_tracking(self):
        """Test that latencies are tracked per endpoint."""
        # Record requests to different endpoints
        for _ in range(10):
            self.collector.record_request("GET", "/api/fast", 200, 10.0)
        for _ in range(10):
            self.collector.record_request("GET", "/api/slow", 200, 100.0)

        with self.collector._metrics_lock:
            fast_latencies = self.collector._latencies_by_path.get("/api/fast", [])
            slow_latencies = self.collector._latencies_by_path.get("/api/slow", [])

        assert len(fast_latencies) == 10
        assert len(slow_latencies) == 10
        assert sum(fast_latencies) / len(fast_latencies) == 10.0
        assert sum(slow_latencies) / len(slow_latencies) == 100.0


class TestSummary:
    """Test cases for performance summary."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up for each test."""
        PerformanceCollector._instance = None
        self.collector = get_performance_collector()
        yield
        PerformanceCollector._instance = None

    def test_summary_structure(self):
        """Test summary structure."""
        self.collector.record_request("GET", "/test", 200, 50.0)

        summary = self.collector.get_summary()

        assert "total_requests" in summary
        assert "total_errors" in summary
        assert "requests_by_method" in summary
        assert "requests_by_status" in summary
        assert "top_endpoints" in summary

    def test_top_endpoints_ordering(self):
        """Test that top endpoints are ordered by count."""
        for _ in range(10):
            self.collector.record_request("GET", "/api/popular", 200, 50.0)
        for _ in range(5):
            self.collector.record_request("GET", "/api/medium", 200, 50.0)
        for _ in range(1):
            self.collector.record_request("GET", "/api/rare", 200, 50.0)

        summary = self.collector.get_summary()
        endpoints = list(summary["top_endpoints"].keys())

        assert endpoints[0] == "/api/popular"
        assert endpoints[1] == "/api/medium"
        assert endpoints[2] == "/api/rare"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

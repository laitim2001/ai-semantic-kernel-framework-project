"""
Performance Profiler Unit Tests
Sprint 12 - S12-7: Testing

Tests for:
- MetricType enum
- PerformanceMetric dataclass
- ProfileSession dataclass
- PerformanceProfiler class
  - start_session()
  - end_session()
  - record_metric()
  - measure_latency()
  - get_recommendations()
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from uuid import UUID

from src.core.performance.profiler import (
    MetricType,
    PerformanceMetric,
    ProfileSession,
    PerformanceProfiler
)


class TestMetricType:
    """MetricType enum tests"""

    def test_metric_type_values(self):
        """Test all MetricType enum values exist"""
        assert MetricType.LATENCY == "latency"
        assert MetricType.THROUGHPUT == "throughput"
        assert MetricType.MEMORY == "memory"
        assert MetricType.CPU == "cpu"
        assert MetricType.CONCURRENCY == "concurrency"
        assert MetricType.ERROR_RATE == "error_rate"

    def test_metric_type_count(self):
        """Test MetricType has 6 values"""
        assert len(MetricType) == 6


class TestPerformanceMetric:
    """PerformanceMetric dataclass tests"""

    def test_create_metric(self):
        """Test creating a PerformanceMetric"""
        metric = PerformanceMetric(
            name="test_metric",
            metric_type=MetricType.LATENCY,
            value=100.5,
            unit="ms"
        )

        assert metric.name == "test_metric"
        assert metric.metric_type == MetricType.LATENCY
        assert metric.value == 100.5
        assert metric.unit == "ms"
        assert isinstance(metric.timestamp, datetime)
        assert metric.tags == {}

    def test_metric_with_tags(self):
        """Test metric with custom tags"""
        tags = {"endpoint": "/api/test", "method": "GET"}
        metric = PerformanceMetric(
            name="api_latency",
            metric_type=MetricType.LATENCY,
            value=50.0,
            unit="ms",
            tags=tags
        )

        assert metric.tags == tags
        assert metric.tags["endpoint"] == "/api/test"


class TestProfileSession:
    """ProfileSession dataclass tests"""

    def test_create_session(self):
        """Test creating a ProfileSession"""
        from uuid import uuid4

        session_id = uuid4()
        session = ProfileSession(
            id=session_id,
            name="test_session",
            started_at=datetime.utcnow()
        )

        assert session.id == session_id
        assert session.name == "test_session"
        assert session.ended_at is None
        assert session.metrics == []
        assert session.summary is None

    def test_session_with_metrics(self):
        """Test session with metrics"""
        from uuid import uuid4

        metric = PerformanceMetric(
            name="test",
            metric_type=MetricType.LATENCY,
            value=100.0,
            unit="ms"
        )

        session = ProfileSession(
            id=uuid4(),
            name="test_session",
            started_at=datetime.utcnow(),
            metrics=[metric]
        )

        assert len(session.metrics) == 1
        assert session.metrics[0].name == "test"


class TestPerformanceProfiler:
    """PerformanceProfiler class tests"""

    @pytest.fixture
    def profiler(self):
        """Create a fresh profiler for each test"""
        return PerformanceProfiler()

    def test_init(self, profiler):
        """Test profiler initialization"""
        assert profiler._active_session is None
        assert len(profiler._sessions) == 0
        assert len(profiler._metric_collectors) == 6

    def test_start_session(self, profiler):
        """Test starting a profiling session"""
        session = profiler.start_session("test_session")

        assert session.name == "test_session"
        assert isinstance(session.id, UUID)
        assert session.ended_at is None
        assert profiler._active_session == session
        assert session.id in profiler._sessions

    def test_end_session(self, profiler):
        """Test ending a profiling session"""
        session = profiler.start_session("test_session")
        session_id = session.id

        ended_session = profiler.end_session()

        assert ended_session.id == session_id
        assert ended_session.ended_at is not None
        assert ended_session.summary is not None
        assert profiler._active_session is None

    def test_end_session_with_id(self, profiler):
        """Test ending a specific session by ID"""
        session1 = profiler.start_session("session1")
        session2 = profiler.start_session("session2")

        ended = profiler.end_session(session1.id)

        assert ended.id == session1.id
        assert ended.ended_at is not None

    def test_end_session_no_active(self, profiler):
        """Test ending session when no active session"""
        with pytest.raises(ValueError, match="No active session"):
            profiler.end_session()

    def test_record_metric(self, profiler):
        """Test recording a metric"""
        profiler.start_session("test")

        profiler.record_metric(
            name="test_latency",
            metric_type=MetricType.LATENCY,
            value=150.0,
            unit="ms",
            tags={"test": "value"}
        )

        assert len(profiler._active_session.metrics) == 1
        assert profiler._active_session.metrics[0].name == "test_latency"
        assert profiler._active_session.metrics[0].value == 150.0

    def test_record_metric_without_session(self, profiler):
        """Test recording metric without active session (should still record to collectors)"""
        profiler.record_metric(
            name="orphan_metric",
            metric_type=MetricType.THROUGHPUT,
            value=100.0
        )

        assert len(profiler._metric_collectors[MetricType.THROUGHPUT]) == 1

    def test_record_multiple_metrics(self, profiler):
        """Test recording multiple metrics"""
        profiler.start_session("test")

        for i in range(10):
            profiler.record_metric(
                name=f"metric_{i}",
                metric_type=MetricType.LATENCY,
                value=float(i * 10)
            )

        assert len(profiler._active_session.metrics) == 10
        assert len(profiler._metric_collectors[MetricType.LATENCY]) == 10

    @pytest.mark.asyncio
    async def test_measure_latency_async(self, profiler):
        """Test measure_latency decorator with async function"""
        profiler.start_session("test")

        @profiler.measure_latency("async_operation")
        async def slow_operation():
            await asyncio.sleep(0.1)
            return "done"

        result = await slow_operation()

        assert result == "done"
        assert len(profiler._active_session.metrics) == 1
        assert profiler._active_session.metrics[0].metric_type == MetricType.LATENCY
        # Should be around 100ms
        assert profiler._active_session.metrics[0].value >= 90

    def test_measure_latency_sync(self, profiler):
        """Test measure_latency decorator with sync function"""
        profiler.start_session("test")

        @profiler.measure_latency("sync_operation")
        def fast_operation():
            return "done"

        result = fast_operation()

        assert result == "done"
        assert len(profiler._active_session.metrics) == 1
        assert profiler._active_session.metrics[0].metric_type == MetricType.LATENCY

    def test_generate_summary(self, profiler):
        """Test session summary generation"""
        profiler.start_session("test")

        # Add various metrics
        for i in range(10):
            profiler.record_metric("latency", MetricType.LATENCY, float(100 + i * 10))
            profiler.record_metric("throughput", MetricType.THROUGHPUT, float(50 + i))

        session = profiler.end_session()

        assert "duration_seconds" in session.summary
        assert "total_metrics" in session.summary
        assert session.summary["total_metrics"] == 20
        assert "metrics_by_type" in session.summary
        assert "latency" in session.summary["metrics_by_type"]
        assert "throughput" in session.summary["metrics_by_type"]

    def test_summary_statistics(self, profiler):
        """Test summary contains correct statistics"""
        profiler.start_session("test")

        values = [100.0, 200.0, 300.0, 400.0, 500.0]
        for v in values:
            profiler.record_metric("latency", MetricType.LATENCY, v)

        session = profiler.end_session()
        stats = session.summary["metrics_by_type"]["latency"]

        assert stats["count"] == 5
        assert stats["min"] == 100.0
        assert stats["max"] == 500.0
        assert stats["avg"] == 300.0
        assert stats["median"] == 300.0

    def test_get_recommendations_high_latency(self, profiler):
        """Test recommendations for high latency"""
        profiler.start_session("test")

        # Record high latency values (> 1000ms)
        for _ in range(10):
            profiler.record_metric("api", MetricType.LATENCY, 1500.0)

        recommendations = profiler.get_recommendations()

        assert len(recommendations) > 0
        latency_rec = next((r for r in recommendations if r["type"] == "latency"), None)
        assert latency_rec is not None
        assert latency_rec["severity"] == "high"

    def test_get_recommendations_high_variance(self, profiler):
        """Test recommendations for high latency variance"""
        profiler.start_session("test")

        # Record latency with high variance
        for i in range(50):
            profiler.record_metric("api", MetricType.LATENCY, 100.0)
        # Add some very high outliers
        for i in range(5):
            profiler.record_metric("api", MetricType.LATENCY, 5000.0)

        recommendations = profiler.get_recommendations()

        variance_rec = next(
            (r for r in recommendations if r["type"] == "latency_variance"),
            None
        )
        assert variance_rec is not None

    def test_get_recommendations_high_error_rate(self, profiler):
        """Test recommendations for high error rate"""
        profiler.start_session("test")

        # Record high error rates (> 5%)
        for _ in range(10):
            profiler.record_metric("errors", MetricType.ERROR_RATE, 0.10)  # 10%

        recommendations = profiler.get_recommendations()

        error_rec = next((r for r in recommendations if r["type"] == "error_rate"), None)
        assert error_rec is not None
        assert error_rec["severity"] == "high"

    def test_get_recommendations_high_concurrency(self, profiler):
        """Test recommendations for high concurrency"""
        profiler.start_session("test")

        # Record high concurrency (> 100)
        profiler.record_metric("concurrent", MetricType.CONCURRENCY, 150.0)

        recommendations = profiler.get_recommendations()

        concurrency_rec = next(
            (r for r in recommendations if r["type"] == "concurrency"),
            None
        )
        assert concurrency_rec is not None

    def test_get_recommendations_empty(self, profiler):
        """Test no recommendations when metrics are healthy"""
        profiler.start_session("test")

        # Record healthy metrics
        for _ in range(10):
            profiler.record_metric("api", MetricType.LATENCY, 50.0)  # Low latency
            profiler.record_metric("errors", MetricType.ERROR_RATE, 0.01)  # 1% error
            profiler.record_metric("concurrent", MetricType.CONCURRENCY, 10.0)

        recommendations = profiler.get_recommendations()

        # May have some minor recommendations but no high severity
        high_severity = [r for r in recommendations if r["severity"] == "high"]
        assert len(high_severity) == 0

    def test_percentile_calculation(self, profiler):
        """Test percentile calculation"""
        values = list(range(1, 101))  # 1 to 100

        p50 = profiler._percentile(values, 50)
        p95 = profiler._percentile(values, 95)
        p99 = profiler._percentile(values, 99)

        assert p50 == 50
        assert p95 == 95
        assert p99 == 99

    def test_percentile_empty_list(self, profiler):
        """Test percentile with empty list"""
        result = profiler._percentile([], 95)
        assert result == 0

    def test_multiple_sessions(self, profiler):
        """Test managing multiple sessions"""
        session1 = profiler.start_session("session1")
        profiler.record_metric("m1", MetricType.LATENCY, 100.0)
        profiler.end_session()

        session2 = profiler.start_session("session2")
        profiler.record_metric("m2", MetricType.THROUGHPUT, 200.0)
        profiler.end_session()

        assert len(profiler._sessions) == 2
        assert session1.id in profiler._sessions
        assert session2.id in profiler._sessions

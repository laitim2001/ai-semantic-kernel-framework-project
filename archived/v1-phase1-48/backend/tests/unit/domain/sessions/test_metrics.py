"""
Unit tests for Session Metrics (S47-3)

Tests:
- Counter, Histogram, Gauge metrics
- MetricsCollector for message, tool, error, approval tracking
- @track_time decorator
- TimingContext context manager
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
import asyncio
import time

from src.domain.sessions.metrics import (
    MetricType,
    MetricValue,
    Counter,
    Histogram,
    Gauge,
    MetricsCollector,
    TimingContext,
    track_time,
    track_tool_time,
    get_metrics_collector,
    create_metrics_collector,
)


# =============================================================================
# MetricValue Tests
# =============================================================================


class TestMetricValue:
    """Test MetricValue dataclass"""

    def test_create_metric_value(self):
        """Test creating metric value"""
        value = MetricValue(
            name="test_metric",
            value=42.0,
            labels={"env": "test"},
        )

        assert value.name == "test_metric"
        assert value.value == 42.0
        assert value.labels == {"env": "test"}
        assert value.timestamp is not None

    def test_to_dict(self):
        """Test converting to dictionary"""
        value = MetricValue(
            name="test_metric",
            value=100.0,
            labels={"key": "value"},
        )

        data = value.to_dict()

        assert data["name"] == "test_metric"
        assert data["value"] == 100.0
        assert data["labels"] == {"key": "value"}
        assert "timestamp" in data


# =============================================================================
# Counter Tests
# =============================================================================


class TestCounter:
    """Test Counter metric"""

    def test_create_counter(self):
        """Test creating counter"""
        counter = Counter(
            name="test_counter",
            description="Test counter",
            label_names=["status"],
        )

        assert counter.name == "test_counter"
        assert counter.description == "Test counter"
        assert counter.label_names == ["status"]

    def test_increment_without_labels(self):
        """Test incrementing counter without labels"""
        counter = Counter(name="test", description="Test")

        counter.inc()
        assert counter.get() == 1

        counter.inc()
        assert counter.get() == 2

    def test_increment_with_amount(self):
        """Test incrementing counter with custom amount"""
        counter = Counter(name="test", description="Test")

        counter.inc(amount=5)
        assert counter.get() == 5

        counter.inc(amount=3)
        assert counter.get() == 8

    def test_increment_with_labels(self):
        """Test incrementing counter with labels"""
        counter = Counter(
            name="test",
            description="Test",
            label_names=["status"],
        )

        counter.inc(labels={"status": "success"})
        counter.inc(labels={"status": "success"})
        counter.inc(labels={"status": "error"})

        assert counter.get(labels={"status": "success"}) == 2
        assert counter.get(labels={"status": "error"}) == 1
        assert counter.get(labels={"status": "pending"}) == 0

    def test_reset(self):
        """Test resetting counter"""
        counter = Counter(name="test", description="Test")

        counter.inc()
        counter.inc()
        assert counter.get() == 2

        counter.reset()
        assert counter.get() == 0


# =============================================================================
# Histogram Tests
# =============================================================================


class TestHistogram:
    """Test Histogram metric"""

    def test_create_histogram(self):
        """Test creating histogram"""
        histogram = Histogram(
            name="test_histogram",
            description="Test histogram",
            label_names=["operation"],
            buckets=(0.1, 0.5, 1.0),
        )

        assert histogram.name == "test_histogram"
        assert histogram.buckets == (0.1, 0.5, 1.0)

    def test_observe_without_labels(self):
        """Test observing values without labels"""
        histogram = Histogram(name="test", description="Test")

        histogram.observe(0.5)
        histogram.observe(1.0)
        histogram.observe(1.5)

        assert histogram.get_count() == 3
        assert histogram.get_sum() == 3.0
        assert histogram.get_average() == 1.0

    def test_observe_with_labels(self):
        """Test observing values with labels"""
        histogram = Histogram(
            name="test",
            description="Test",
            label_names=["operation"],
        )

        histogram.observe(0.5, labels={"operation": "read"})
        histogram.observe(1.0, labels={"operation": "read"})
        histogram.observe(2.0, labels={"operation": "write"})

        assert histogram.get_count(labels={"operation": "read"}) == 2
        assert histogram.get_sum(labels={"operation": "read"}) == 1.5
        assert histogram.get_count(labels={"operation": "write"}) == 1

    def test_get_percentile(self):
        """Test getting percentile"""
        histogram = Histogram(name="test", description="Test")

        for i in range(1, 101):
            histogram.observe(float(i))

        assert histogram.get_percentile(50) == 50.0
        assert histogram.get_percentile(90) == 90.0
        assert histogram.get_percentile(99) == 99.0

    def test_get_percentile_empty(self):
        """Test getting percentile from empty histogram"""
        histogram = Histogram(name="test", description="Test")

        assert histogram.get_percentile(50) == 0.0

    def test_reset(self):
        """Test resetting histogram"""
        histogram = Histogram(name="test", description="Test")

        histogram.observe(1.0)
        histogram.observe(2.0)
        assert histogram.get_count() == 2

        histogram.reset()
        assert histogram.get_count() == 0
        assert histogram.get_sum() == 0.0


# =============================================================================
# Gauge Tests
# =============================================================================


class TestGauge:
    """Test Gauge metric"""

    def test_create_gauge(self):
        """Test creating gauge"""
        gauge = Gauge(
            name="test_gauge",
            description="Test gauge",
            label_names=["instance"],
        )

        assert gauge.name == "test_gauge"
        assert gauge.description == "Test gauge"

    def test_set_value(self):
        """Test setting gauge value"""
        gauge = Gauge(name="test", description="Test")

        gauge.set(42.0)
        assert gauge.get() == 42.0

        gauge.set(100.0)
        assert gauge.get() == 100.0

    def test_increment_decrement(self):
        """Test incrementing and decrementing gauge"""
        gauge = Gauge(name="test", description="Test")

        gauge.inc()
        assert gauge.get() == 1

        gauge.inc(amount=4)
        assert gauge.get() == 5

        gauge.dec()
        assert gauge.get() == 4

        gauge.dec(amount=2)
        assert gauge.get() == 2

    def test_with_labels(self):
        """Test gauge with labels"""
        gauge = Gauge(
            name="test",
            description="Test",
            label_names=["instance"],
        )

        gauge.set(10, labels={"instance": "a"})
        gauge.set(20, labels={"instance": "b"})

        assert gauge.get(labels={"instance": "a"}) == 10
        assert gauge.get(labels={"instance": "b"}) == 20

    def test_reset(self):
        """Test resetting gauge"""
        gauge = Gauge(name="test", description="Test")

        gauge.set(100)
        assert gauge.get() == 100

        gauge.reset()
        assert gauge.get() == 0


# =============================================================================
# MetricsCollector Tests
# =============================================================================


class TestMetricsCollector:
    """Test MetricsCollector class"""

    @pytest.fixture
    def collector(self):
        """Create metrics collector"""
        return MetricsCollector()

    def test_create_collector(self, collector):
        """Test creating collector"""
        assert collector.messages_total is not None
        assert collector.tool_calls_total is not None
        assert collector.errors_total is not None
        assert collector.response_time is not None
        assert collector.active_sessions is not None

    def test_record_message(self, collector):
        """Test recording messages"""
        collector.record_user_message("session-1")
        collector.record_assistant_message("session-1")
        collector.record_system_message("session-1")

        assert collector.messages_total.get(
            {"session_id": "session-1", "message_type": "user"}
        ) == 1
        assert collector.messages_total.get(
            {"session_id": "session-1", "message_type": "assistant"}
        ) == 1
        assert collector.messages_total.get(
            {"session_id": "session-1", "message_type": "system"}
        ) == 1

    def test_record_tool_call(self, collector):
        """Test recording tool calls"""
        collector.record_tool_success("session-1", "calculator")
        collector.record_tool_failure("session-1", "calculator")
        collector.record_tool_timeout("session-1", "web_search")

        assert collector.tool_calls_total.get(
            {"session_id": "session-1", "tool_name": "calculator", "status": "success"}
        ) == 1
        assert collector.tool_calls_total.get(
            {"session_id": "session-1", "tool_name": "calculator", "status": "failure"}
        ) == 1
        assert collector.tool_calls_total.get(
            {"session_id": "session-1", "tool_name": "web_search", "status": "timeout"}
        ) == 1

    def test_record_tool_execution_time(self, collector):
        """Test recording tool execution time"""
        collector.record_tool_execution_time("calculator", 0.5)
        collector.record_tool_execution_time("calculator", 1.0)

        assert collector.tool_execution_time.get_count(
            labels={"tool_name": "calculator"}
        ) == 2
        assert collector.tool_execution_time.get_average(
            labels={"tool_name": "calculator"}
        ) == 0.75

    def test_record_error(self, collector):
        """Test recording errors"""
        collector.record_error("session-1", "LLM_TIMEOUT")
        collector.record_error("session-1", "LLM_TIMEOUT")
        collector.record_error("session-1", "TOOL_ERROR")

        assert collector.errors_total.get(
            {"session_id": "session-1", "error_code": "LLM_TIMEOUT"}
        ) == 2
        assert collector.errors_total.get(
            {"session_id": "session-1", "error_code": "TOOL_ERROR"}
        ) == 1

    def test_record_approval_lifecycle(self, collector):
        """Test recording approval lifecycle"""
        collector.record_approval_request("session-1")
        assert collector.pending_approvals.get() == 1

        collector.record_approval_granted("session-1")
        assert collector.pending_approvals.get() == 0

        collector.record_approval_request("session-2")
        collector.record_approval_denied("session-2")
        assert collector.pending_approvals.get() == 0

        collector.record_approval_request("session-3")
        collector.record_approval_timeout("session-3")
        assert collector.pending_approvals.get() == 0

    def test_record_response_time(self, collector):
        """Test recording response time"""
        collector.record_response_time("session-1", "llm_call", 1.5)
        collector.record_response_time("session-1", "llm_call", 2.0)

        assert collector.response_time.get_count(
            labels={"session_id": "session-1", "operation": "llm_call"}
        ) == 2
        assert collector.response_time.get_average(
            labels={"session_id": "session-1", "operation": "llm_call"}
        ) == 1.75

    def test_record_token_usage(self, collector):
        """Test recording token usage"""
        collector.record_token_usage("session-1", prompt_tokens=100, completion_tokens=50)

        assert collector.token_usage.get_count(
            labels={"session_id": "session-1", "token_type": "prompt"}
        ) == 1
        assert collector.token_usage.get_count(
            labels={"session_id": "session-1", "token_type": "completion"}
        ) == 1

    def test_record_session_lifecycle(self, collector):
        """Test recording session lifecycle"""
        collector.record_session_start()
        collector.record_session_start()
        assert collector.active_sessions.get() == 2

        collector.record_session_end()
        assert collector.active_sessions.get() == 1

    def test_record_websocket_lifecycle(self, collector):
        """Test recording WebSocket lifecycle"""
        collector.record_websocket_connect()
        collector.record_websocket_connect()
        assert collector.active_connections.get() == 2

        collector.record_websocket_disconnect()
        assert collector.active_connections.get() == 1

    def test_get_statistics(self, collector):
        """Test getting statistics"""
        collector.record_session_start()
        collector.record_websocket_connect()
        collector.record_approval_request("session-1")

        stats = collector.get_statistics()

        assert stats["active_sessions"] == 1
        assert stats["active_connections"] == 1
        assert stats["pending_approvals"] == 1

    def test_get_session_statistics(self, collector):
        """Test getting session-specific statistics"""
        collector.record_user_message("session-1")
        collector.record_assistant_message("session-1")
        collector.record_error("session-1", "TEST_ERROR")

        stats = collector.get_statistics("session-1")

        assert stats["session"]["messages"]["user"] == 1
        assert stats["session"]["messages"]["assistant"] == 1

    def test_reset_all(self, collector):
        """Test resetting all metrics"""
        collector.record_user_message("session-1")
        collector.record_session_start()
        collector.record_error("session-1", "TEST")

        collector.reset_all()

        assert collector.messages_total.get(
            {"session_id": "session-1", "message_type": "user"}
        ) == 0
        assert collector.active_sessions.get() == 0


# =============================================================================
# track_time Decorator Tests
# =============================================================================


class TestTrackTimeDecorator:
    """Test @track_time decorator"""

    @pytest.fixture
    def collector(self):
        """Create metrics collector"""
        return MetricsCollector()

    @pytest.mark.asyncio
    async def test_track_time_with_kwargs(self, collector):
        """Test tracking time with kwargs"""

        @track_time(collector, "test_operation")
        async def test_func(session_id: str) -> str:
            await asyncio.sleep(0.1)
            return "result"

        result = await test_func(session_id="session-1")

        assert result == "result"
        assert collector.response_time.get_count(
            labels={"session_id": "session-1", "operation": "test_operation"}
        ) == 1
        # Check that time was recorded (should be at least 0.1 seconds)
        observations = collector.response_time.get_observations(
            labels={"session_id": "session-1", "operation": "test_operation"}
        )
        assert len(observations) == 1
        assert observations[0] >= 0.1

    @pytest.mark.asyncio
    async def test_track_time_with_args(self, collector):
        """Test tracking time with positional args"""

        @track_time(collector, "test_operation")
        async def test_func(session_id: str) -> str:
            return "result"

        result = await test_func("session-1")

        assert result == "result"
        assert collector.response_time.get_count(
            labels={"session_id": "session-1", "operation": "test_operation"}
        ) == 1

    @pytest.mark.asyncio
    async def test_track_time_with_exception(self, collector):
        """Test tracking time when exception occurs"""

        @track_time(collector, "test_operation")
        async def test_func(session_id: str) -> str:
            await asyncio.sleep(0.05)
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await test_func(session_id="session-1")

        # Time should still be recorded even on exception
        assert collector.response_time.get_count(
            labels={"session_id": "session-1", "operation": "test_operation"}
        ) == 1


class TestTrackToolTimeDecorator:
    """Test @track_tool_time decorator"""

    @pytest.fixture
    def collector(self):
        """Create metrics collector"""
        return MetricsCollector()

    @pytest.mark.asyncio
    async def test_track_tool_time(self, collector):
        """Test tracking tool execution time"""

        @track_tool_time(collector)
        async def execute_tool(tool_name: str, args: dict) -> dict:
            await asyncio.sleep(0.1)
            return {"result": "success"}

        result = await execute_tool(tool_name="calculator", args={})

        assert result == {"result": "success"}
        assert collector.tool_execution_time.get_count(
            labels={"tool_name": "calculator"}
        ) == 1


# =============================================================================
# TimingContext Tests
# =============================================================================


class TestTimingContext:
    """Test TimingContext context manager"""

    @pytest.fixture
    def collector(self):
        """Create metrics collector"""
        return MetricsCollector()

    def test_sync_context(self, collector):
        """Test synchronous context manager"""
        with TimingContext(collector, "session-1", "sync_operation") as ctx:
            time.sleep(0.1)

        assert ctx.duration is not None
        assert ctx.duration >= 0.1
        assert collector.response_time.get_count(
            labels={"session_id": "session-1", "operation": "sync_operation"}
        ) == 1

    @pytest.mark.asyncio
    async def test_async_context(self, collector):
        """Test asynchronous context manager"""
        async with TimingContext(collector, "session-1", "async_operation") as ctx:
            await asyncio.sleep(0.1)

        assert ctx.duration is not None
        assert ctx.duration >= 0.1
        assert collector.response_time.get_count(
            labels={"session_id": "session-1", "operation": "async_operation"}
        ) == 1


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunctions:
    """Test factory functions"""

    def test_create_metrics_collector(self):
        """Test creating collector via factory"""
        collector = create_metrics_collector()
        assert isinstance(collector, MetricsCollector)

    def test_get_metrics_collector_singleton(self):
        """Test getting default collector"""
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()

        assert collector1 is collector2
        assert isinstance(collector1, MetricsCollector)

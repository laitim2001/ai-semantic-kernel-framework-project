"""
Session Metrics (S47-3)

Provides performance monitoring and metrics collection:
- Prometheus counters, histograms, and gauges
- MetricsCollector for centralized metrics management
- @track_time decorator for timing operations
"""

from typing import Optional, Dict, Any, Callable, TypeVar, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from enum import Enum
import time
import asyncio
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


class MetricType(str, Enum):
    """Metric types"""
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    GAUGE = "gauge"


@dataclass
class MetricValue:
    """Metric value with labels"""
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "value": self.value,
            "labels": self.labels,
            "timestamp": self.timestamp.isoformat(),
        }


class Counter:
    """Prometheus-style counter metric"""

    def __init__(self, name: str, description: str, label_names: Optional[list] = None):
        self.name = name
        self.description = description
        self.label_names = label_names or []
        self._values: Dict[str, float] = {}

    def _key(self, labels: Optional[Dict[str, str]] = None) -> str:
        """Generate key for label combination"""
        if not labels:
            return ""
        return "|".join(f"{k}={v}" for k, v in sorted(labels.items()))

    def inc(self, labels: Optional[Dict[str, str]] = None, amount: float = 1) -> None:
        """Increment counter"""
        key = self._key(labels)
        self._values[key] = self._values.get(key, 0) + amount

    def get(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get counter value"""
        key = self._key(labels)
        return self._values.get(key, 0)

    def reset(self) -> None:
        """Reset all values"""
        self._values.clear()


class Histogram:
    """Prometheus-style histogram metric"""

    DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

    def __init__(
        self,
        name: str,
        description: str,
        label_names: Optional[list] = None,
        buckets: Optional[tuple] = None,
    ):
        self.name = name
        self.description = description
        self.label_names = label_names or []
        self.buckets = buckets or self.DEFAULT_BUCKETS
        self._observations: Dict[str, list] = {}

    def _key(self, labels: Optional[Dict[str, str]] = None) -> str:
        """Generate key for label combination"""
        if not labels:
            return ""
        return "|".join(f"{k}={v}" for k, v in sorted(labels.items()))

    def observe(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Observe a value"""
        key = self._key(labels)
        if key not in self._observations:
            self._observations[key] = []
        self._observations[key].append(value)

    def get_observations(self, labels: Optional[Dict[str, str]] = None) -> list:
        """Get all observations"""
        key = self._key(labels)
        return self._observations.get(key, [])

    def get_count(self, labels: Optional[Dict[str, str]] = None) -> int:
        """Get observation count"""
        return len(self.get_observations(labels))

    def get_sum(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get sum of observations"""
        observations = self.get_observations(labels)
        return sum(observations) if observations else 0.0

    def get_average(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get average of observations"""
        observations = self.get_observations(labels)
        if not observations:
            return 0.0
        return sum(observations) / len(observations)

    def get_percentile(
        self,
        percentile: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> float:
        """Get percentile value using nearest-rank method"""
        observations = self.get_observations(labels)
        if not observations:
            return 0.0
        sorted_obs = sorted(observations)
        # Nearest-rank method: P-th percentile is the value at rank ceil(P/100 * N)
        # For 50th percentile of 100 values, we want index 49 (value 50)
        n = len(sorted_obs)
        rank = int((percentile / 100) * n)
        # Ensure index is within bounds (0 to n-1)
        index = max(0, min(rank - 1, n - 1)) if rank > 0 else 0
        return sorted_obs[index]

    def reset(self) -> None:
        """Reset all observations"""
        self._observations.clear()


class Gauge:
    """Prometheus-style gauge metric"""

    def __init__(self, name: str, description: str, label_names: Optional[list] = None):
        self.name = name
        self.description = description
        self.label_names = label_names or []
        self._values: Dict[str, float] = {}

    def _key(self, labels: Optional[Dict[str, str]] = None) -> str:
        """Generate key for label combination"""
        if not labels:
            return ""
        return "|".join(f"{k}={v}" for k, v in sorted(labels.items()))

    def set(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set gauge value"""
        key = self._key(labels)
        self._values[key] = value

    def inc(self, labels: Optional[Dict[str, str]] = None, amount: float = 1) -> None:
        """Increment gauge"""
        key = self._key(labels)
        self._values[key] = self._values.get(key, 0) + amount

    def dec(self, labels: Optional[Dict[str, str]] = None, amount: float = 1) -> None:
        """Decrement gauge"""
        key = self._key(labels)
        self._values[key] = self._values.get(key, 0) - amount

    def get(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get gauge value"""
        key = self._key(labels)
        return self._values.get(key, 0)

    def reset(self) -> None:
        """Reset all values"""
        self._values.clear()


class MetricsCollector:
    """
    Centralized metrics collector for session-agent integration.

    Provides:
    - Message counters
    - Tool call counters
    - Error counters
    - Response time histograms
    - Token usage histograms
    - Active session/connection gauges
    """

    def __init__(self):
        # Counters
        self.messages_total = Counter(
            name="session_messages_total",
            description="Total number of messages processed",
            label_names=["session_id", "message_type"],
        )
        self.tool_calls_total = Counter(
            name="session_tool_calls_total",
            description="Total number of tool calls",
            label_names=["session_id", "tool_name", "status"],
        )
        self.errors_total = Counter(
            name="session_errors_total",
            description="Total number of errors",
            label_names=["session_id", "error_code"],
        )
        self.approvals_total = Counter(
            name="session_approvals_total",
            description="Total number of approval requests",
            label_names=["session_id", "status"],
        )

        # Histograms
        self.response_time = Histogram(
            name="session_response_time_seconds",
            description="Response time in seconds",
            label_names=["session_id", "operation"],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
        )
        self.token_usage = Histogram(
            name="session_token_usage",
            description="Token usage per request",
            label_names=["session_id", "token_type"],
            buckets=(10, 50, 100, 500, 1000, 2000, 4000, 8000),
        )
        self.tool_execution_time = Histogram(
            name="session_tool_execution_time_seconds",
            description="Tool execution time in seconds",
            label_names=["tool_name"],
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0),
        )

        # Gauges
        self.active_sessions = Gauge(
            name="session_active_total",
            description="Number of active sessions",
        )
        self.active_connections = Gauge(
            name="session_websocket_connections_total",
            description="Number of active WebSocket connections",
        )
        self.pending_approvals = Gauge(
            name="session_pending_approvals_total",
            description="Number of pending approval requests",
        )

    # =========================================================================
    # Message Metrics
    # =========================================================================

    def record_message(
        self,
        session_id: str,
        message_type: str = "user",
    ) -> None:
        """Record a message"""
        self.messages_total.inc(
            labels={"session_id": session_id, "message_type": message_type}
        )

    def record_user_message(self, session_id: str) -> None:
        """Record user message"""
        self.record_message(session_id, "user")

    def record_assistant_message(self, session_id: str) -> None:
        """Record assistant message"""
        self.record_message(session_id, "assistant")

    def record_system_message(self, session_id: str) -> None:
        """Record system message"""
        self.record_message(session_id, "system")

    # =========================================================================
    # Tool Call Metrics
    # =========================================================================

    def record_tool_call(
        self,
        session_id: str,
        tool_name: str,
        status: str = "success",
    ) -> None:
        """Record a tool call"""
        self.tool_calls_total.inc(
            labels={"session_id": session_id, "tool_name": tool_name, "status": status}
        )

    def record_tool_success(self, session_id: str, tool_name: str) -> None:
        """Record successful tool call"""
        self.record_tool_call(session_id, tool_name, "success")

    def record_tool_failure(self, session_id: str, tool_name: str) -> None:
        """Record failed tool call"""
        self.record_tool_call(session_id, tool_name, "failure")

    def record_tool_timeout(self, session_id: str, tool_name: str) -> None:
        """Record timed out tool call"""
        self.record_tool_call(session_id, tool_name, "timeout")

    def record_tool_execution_time(self, tool_name: str, duration: float) -> None:
        """Record tool execution time"""
        self.tool_execution_time.observe(duration, labels={"tool_name": tool_name})

    # =========================================================================
    # Error Metrics
    # =========================================================================

    def record_error(self, session_id: str, error_code: str) -> None:
        """Record an error"""
        self.errors_total.inc(
            labels={"session_id": session_id, "error_code": error_code}
        )

    # =========================================================================
    # Approval Metrics
    # =========================================================================

    def record_approval_request(self, session_id: str) -> None:
        """Record approval request"""
        self.approvals_total.inc(labels={"session_id": session_id, "status": "requested"})
        self.pending_approvals.inc()

    def record_approval_granted(self, session_id: str) -> None:
        """Record approval granted"""
        self.approvals_total.inc(labels={"session_id": session_id, "status": "granted"})
        self.pending_approvals.dec()

    def record_approval_denied(self, session_id: str) -> None:
        """Record approval denied"""
        self.approvals_total.inc(labels={"session_id": session_id, "status": "denied"})
        self.pending_approvals.dec()

    def record_approval_timeout(self, session_id: str) -> None:
        """Record approval timeout"""
        self.approvals_total.inc(labels={"session_id": session_id, "status": "timeout"})
        self.pending_approvals.dec()

    # =========================================================================
    # Response Time Metrics
    # =========================================================================

    def record_response_time(
        self,
        session_id: str,
        operation: str,
        duration: float,
    ) -> None:
        """Record response time"""
        self.response_time.observe(
            duration,
            labels={"session_id": session_id, "operation": operation},
        )

    # =========================================================================
    # Token Usage Metrics
    # =========================================================================

    def record_token_usage(
        self,
        session_id: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> None:
        """Record token usage"""
        if prompt_tokens > 0:
            self.token_usage.observe(
                prompt_tokens,
                labels={"session_id": session_id, "token_type": "prompt"},
            )
        if completion_tokens > 0:
            self.token_usage.observe(
                completion_tokens,
                labels={"session_id": session_id, "token_type": "completion"},
            )

    # =========================================================================
    # Session Metrics
    # =========================================================================

    def record_session_start(self) -> None:
        """Record session start"""
        self.active_sessions.inc()

    def record_session_end(self) -> None:
        """Record session end"""
        self.active_sessions.dec()

    def record_websocket_connect(self) -> None:
        """Record WebSocket connection"""
        self.active_connections.inc()

    def record_websocket_disconnect(self) -> None:
        """Record WebSocket disconnection"""
        self.active_connections.dec()

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_statistics(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get current statistics"""
        stats = {
            "active_sessions": self.active_sessions.get(),
            "active_connections": self.active_connections.get(),
            "pending_approvals": self.pending_approvals.get(),
        }

        if session_id:
            # Session-specific stats
            stats["session"] = {
                "messages": {
                    "user": self.messages_total.get(
                        {"session_id": session_id, "message_type": "user"}
                    ),
                    "assistant": self.messages_total.get(
                        {"session_id": session_id, "message_type": "assistant"}
                    ),
                },
                "errors": self.errors_total.get({"session_id": session_id}),
            }

        return stats

    def reset_all(self) -> None:
        """Reset all metrics"""
        self.messages_total.reset()
        self.tool_calls_total.reset()
        self.errors_total.reset()
        self.approvals_total.reset()
        self.response_time.reset()
        self.token_usage.reset()
        self.tool_execution_time.reset()
        self.active_sessions.reset()
        self.active_connections.reset()
        self.pending_approvals.reset()


# =========================================================================
# Decorators
# =========================================================================


def track_time(
    collector: MetricsCollector,
    operation: str,
    session_id_param: str = "session_id",
):
    """
    Decorator to track execution time of async functions.

    Usage:
        @track_time(collector, "llm_call")
        async def call_llm(session_id: str, prompt: str) -> str:
            ...
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # Extract session_id from kwargs or first arg
            session_id = kwargs.get(session_id_param)
            if session_id is None and len(args) > 0:
                session_id = args[0]

            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if session_id:
                    collector.record_response_time(
                        session_id=str(session_id),
                        operation=operation,
                        duration=duration,
                    )
                else:
                    logger.warning(
                        f"track_time: Could not extract session_id for operation {operation}"
                    )

        return wrapper

    return decorator


def track_tool_time(
    collector: MetricsCollector,
    tool_name_param: str = "tool_name",
):
    """
    Decorator to track tool execution time.

    Usage:
        @track_tool_time(collector)
        async def execute_tool(tool_name: str, args: dict) -> Any:
            ...
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # Extract tool_name from kwargs or first arg
            tool_name = kwargs.get(tool_name_param)
            if tool_name is None and len(args) > 0:
                tool_name = args[0]

            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if tool_name:
                    collector.record_tool_execution_time(
                        tool_name=str(tool_name),
                        duration=duration,
                    )

        return wrapper

    return decorator


# =========================================================================
# Context Managers
# =========================================================================


class TimingContext:
    """Context manager for timing operations"""

    def __init__(
        self,
        collector: MetricsCollector,
        session_id: str,
        operation: str,
    ):
        self.collector = collector
        self.session_id = session_id
        self.operation = operation
        self.start_time: Optional[float] = None
        self.duration: Optional[float] = None

    def __enter__(self) -> "TimingContext":
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.start_time:
            self.duration = time.time() - self.start_time
            self.collector.record_response_time(
                session_id=self.session_id,
                operation=self.operation,
                duration=self.duration,
            )

    async def __aenter__(self) -> "TimingContext":
        self.start_time = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.start_time:
            self.duration = time.time() - self.start_time
            self.collector.record_response_time(
                session_id=self.session_id,
                operation=self.operation,
                duration=self.duration,
            )


# =========================================================================
# Global Instance
# =========================================================================

# Global metrics collector instance
_default_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create the default metrics collector"""
    global _default_collector
    if _default_collector is None:
        _default_collector = MetricsCollector()
    return _default_collector


def create_metrics_collector() -> MetricsCollector:
    """Factory function for MetricsCollector"""
    return MetricsCollector()

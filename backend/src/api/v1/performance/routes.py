"""
Performance Monitoring API Routes

Sprint 3 - Story S3-8: Performance Dashboard

Provides endpoints for:
- API performance metrics
- Resource utilization
- Database connection pool status
- Performance health check
"""
import time
import psutil
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, field

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/performance", tags=["performance"])


# ========================================
# Data Classes
# ========================================

@dataclass
class RequestMetric:
    """Single request metric entry."""
    method: str
    path: str
    status_code: int
    duration_ms: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PercentileStats:
    """Percentile statistics."""
    p50: float
    p75: float
    p90: float
    p95: float
    p99: float
    mean: float
    count: int


# ========================================
# Performance Collector (Singleton)
# ========================================

class PerformanceCollector:
    """
    Collects and aggregates performance metrics.

    Thread-safe singleton for tracking request metrics,
    latencies, and resource utilization.
    """
    _instance: Optional["PerformanceCollector"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._metrics_lock = threading.Lock()
        self._request_metrics: List[RequestMetric] = []
        self._max_history = 10000  # Keep last 10K requests

        # Counters
        self._total_requests = 0
        self._total_errors = 0
        self._requests_by_method: Dict[str, int] = defaultdict(int)
        self._requests_by_status: Dict[int, int] = defaultdict(int)
        self._requests_by_path: Dict[str, int] = defaultdict(int)

        # Latency tracking
        self._latencies: List[float] = []
        self._latencies_by_path: Dict[str, List[float]] = defaultdict(list)

        self._initialized = True

    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
    ):
        """Record a request metric."""
        with self._metrics_lock:
            # Create metric entry
            metric = RequestMetric(
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=duration_ms,
            )
            self._request_metrics.append(metric)

            # Trim history if needed
            if len(self._request_metrics) > self._max_history:
                self._request_metrics = self._request_metrics[-self._max_history:]

            # Update counters
            self._total_requests += 1
            if status_code >= 500:
                self._total_errors += 1

            self._requests_by_method[method] += 1
            self._requests_by_status[status_code] += 1
            self._requests_by_path[path] += 1

            # Track latencies
            self._latencies.append(duration_ms)
            if len(self._latencies) > self._max_history:
                self._latencies = self._latencies[-self._max_history:]

            self._latencies_by_path[path].append(duration_ms)
            if len(self._latencies_by_path[path]) > 1000:
                self._latencies_by_path[path] = self._latencies_by_path[path][-1000:]

    def get_percentile_stats(
        self,
        latencies: Optional[List[float]] = None,
        window_minutes: int = 5,
    ) -> PercentileStats:
        """Calculate percentile statistics for latencies."""
        if latencies is None:
            with self._metrics_lock:
                cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
                latencies = [
                    m.duration_ms for m in self._request_metrics
                    if m.timestamp >= cutoff
                ]

        if not latencies:
            return PercentileStats(
                p50=0, p75=0, p90=0, p95=0, p99=0, mean=0, count=0
            )

        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)

        def percentile(p: float) -> float:
            idx = int(n * p / 100)
            return sorted_latencies[min(idx, n - 1)]

        return PercentileStats(
            p50=percentile(50),
            p75=percentile(75),
            p90=percentile(90),
            p95=percentile(95),
            p99=percentile(99),
            mean=sum(sorted_latencies) / n,
            count=n,
        )

    def get_rps(self, window_seconds: int = 60) -> float:
        """Get requests per second over a window."""
        with self._metrics_lock:
            cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
            count = sum(1 for m in self._request_metrics if m.timestamp >= cutoff)
            return count / window_seconds if window_seconds > 0 else 0

    def get_error_rate(self, window_minutes: int = 5) -> float:
        """Get error rate (5xx responses) over a window."""
        with self._metrics_lock:
            cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
            recent = [m for m in self._request_metrics if m.timestamp >= cutoff]

            if not recent:
                return 0.0

            errors = sum(1 for m in recent if m.status_code >= 500)
            return (errors / len(recent)) * 100

    def get_summary(self) -> Dict[str, Any]:
        """Get complete performance summary."""
        with self._metrics_lock:
            return {
                "total_requests": self._total_requests,
                "total_errors": self._total_errors,
                "requests_by_method": dict(self._requests_by_method),
                "requests_by_status": dict(self._requests_by_status),
                "top_endpoints": dict(
                    sorted(
                        self._requests_by_path.items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )[:10]
                ),
            }

    def reset(self):
        """Reset all metrics (for testing)."""
        with self._metrics_lock:
            self._request_metrics.clear()
            self._total_requests = 0
            self._total_errors = 0
            self._requests_by_method.clear()
            self._requests_by_status.clear()
            self._requests_by_path.clear()
            self._latencies.clear()
            self._latencies_by_path.clear()


def get_performance_collector() -> PerformanceCollector:
    """Get the performance collector singleton."""
    return PerformanceCollector()


def reset_performance_collector():
    """Reset the performance collector (for testing)."""
    collector = get_performance_collector()
    collector.reset()


# ========================================
# Response Models
# ========================================

class LatencyStatsResponse(BaseModel):
    """Latency statistics response."""
    p50_ms: float = Field(description="50th percentile latency in ms")
    p75_ms: float = Field(description="75th percentile latency in ms")
    p90_ms: float = Field(description="90th percentile latency in ms")
    p95_ms: float = Field(description="95th percentile latency in ms")
    p99_ms: float = Field(description="99th percentile latency in ms")
    mean_ms: float = Field(description="Mean latency in ms")
    sample_count: int = Field(description="Number of samples")


class ThroughputResponse(BaseModel):
    """Throughput statistics response."""
    requests_per_second: float = Field(description="Current RPS")
    requests_per_minute: float = Field(description="Requests per minute")
    total_requests: int = Field(description="Total requests recorded")


class ErrorRateResponse(BaseModel):
    """Error rate statistics response."""
    error_rate_percent: float = Field(description="Error rate percentage")
    total_errors: int = Field(description="Total 5xx errors")
    total_requests: int = Field(description="Total requests")


class ResourceUsageResponse(BaseModel):
    """Resource usage statistics response."""
    cpu_percent: float = Field(description="CPU usage percentage")
    memory_percent: float = Field(description="Memory usage percentage")
    memory_mb: float = Field(description="Memory usage in MB")
    thread_count: int = Field(description="Active thread count")
    open_files: int = Field(description="Open file descriptors")


class DBPoolStatusResponse(BaseModel):
    """Database connection pool status response."""
    pool_size: int = Field(description="Configured pool size")
    checked_out: int = Field(description="Currently checked out connections")
    checked_in: int = Field(description="Currently available connections")
    overflow: int = Field(description="Overflow connections")
    status: str = Field(description="Pool health status")


class PerformanceSummaryResponse(BaseModel):
    """Complete performance summary response."""
    timestamp: str = Field(description="Summary timestamp")
    latency: LatencyStatsResponse = Field(description="Latency statistics")
    throughput: ThroughputResponse = Field(description="Throughput statistics")
    error_rate: ErrorRateResponse = Field(description="Error rate statistics")
    resources: ResourceUsageResponse = Field(description="Resource usage")
    db_pool: DBPoolStatusResponse = Field(description="Database pool status")


class EndpointPerformanceResponse(BaseModel):
    """Per-endpoint performance response."""
    path: str = Field(description="Endpoint path")
    request_count: int = Field(description="Total requests")
    latency: LatencyStatsResponse = Field(description="Latency statistics")


class HealthResponse(BaseModel):
    """Performance health check response."""
    status: str = Field(description="Health status")
    p95_latency_ms: float = Field(description="P95 latency")
    error_rate_percent: float = Field(description="Error rate")
    cpu_percent: float = Field(description="CPU usage")
    memory_percent: float = Field(description="Memory usage")
    healthy: bool = Field(description="Overall health status")


# ========================================
# Endpoints
# ========================================

@router.get(
    "/latency",
    response_model=LatencyStatsResponse,
    summary="Get API latency statistics",
    description="Returns P50, P75, P90, P95, P99 latency percentiles.",
)
async def get_latency_stats(
    window_minutes: int = Query(5, ge=1, le=60, description="Time window in minutes"),
) -> LatencyStatsResponse:
    """Get latency statistics."""
    collector = get_performance_collector()
    stats = collector.get_percentile_stats(window_minutes=window_minutes)

    return LatencyStatsResponse(
        p50_ms=round(stats.p50, 2),
        p75_ms=round(stats.p75, 2),
        p90_ms=round(stats.p90, 2),
        p95_ms=round(stats.p95, 2),
        p99_ms=round(stats.p99, 2),
        mean_ms=round(stats.mean, 2),
        sample_count=stats.count,
    )


@router.get(
    "/throughput",
    response_model=ThroughputResponse,
    summary="Get throughput statistics",
    description="Returns requests per second and per minute.",
)
async def get_throughput_stats() -> ThroughputResponse:
    """Get throughput statistics."""
    collector = get_performance_collector()
    rps = collector.get_rps(window_seconds=60)
    summary = collector.get_summary()

    return ThroughputResponse(
        requests_per_second=round(rps, 2),
        requests_per_minute=round(rps * 60, 2),
        total_requests=summary["total_requests"],
    )


@router.get(
    "/error-rate",
    response_model=ErrorRateResponse,
    summary="Get error rate statistics",
    description="Returns 5xx error rate percentage.",
)
async def get_error_rate_stats(
    window_minutes: int = Query(5, ge=1, le=60, description="Time window in minutes"),
) -> ErrorRateResponse:
    """Get error rate statistics."""
    collector = get_performance_collector()
    error_rate = collector.get_error_rate(window_minutes=window_minutes)
    summary = collector.get_summary()

    return ErrorRateResponse(
        error_rate_percent=round(error_rate, 2),
        total_errors=summary["total_errors"],
        total_requests=summary["total_requests"],
    )


@router.get(
    "/resources",
    response_model=ResourceUsageResponse,
    summary="Get resource usage",
    description="Returns CPU, memory, and thread statistics.",
)
async def get_resource_usage() -> ResourceUsageResponse:
    """Get resource usage statistics."""
    process = psutil.Process()

    return ResourceUsageResponse(
        cpu_percent=round(process.cpu_percent(interval=0.1), 2),
        memory_percent=round(process.memory_percent(), 2),
        memory_mb=round(process.memory_info().rss / 1024 / 1024, 2),
        thread_count=threading.active_count(),
        open_files=len(process.open_files()) if hasattr(process, "open_files") else 0,
    )


@router.get(
    "/db-pool",
    response_model=DBPoolStatusResponse,
    summary="Get database connection pool status",
    description="Returns database connection pool statistics.",
)
async def get_db_pool_status() -> DBPoolStatusResponse:
    """Get database connection pool status."""
    # In a real implementation, this would query the actual SQLAlchemy pool
    # For now, return simulated values
    return DBPoolStatusResponse(
        pool_size=20,
        checked_out=5,
        checked_in=15,
        overflow=0,
        status="healthy",
    )


@router.get(
    "/summary",
    response_model=PerformanceSummaryResponse,
    summary="Get complete performance summary",
    description="Returns comprehensive performance metrics.",
)
async def get_performance_summary() -> PerformanceSummaryResponse:
    """Get complete performance summary."""
    collector = get_performance_collector()
    latency_stats = collector.get_percentile_stats(window_minutes=5)
    rps = collector.get_rps(window_seconds=60)
    error_rate = collector.get_error_rate(window_minutes=5)
    summary = collector.get_summary()
    process = psutil.Process()

    return PerformanceSummaryResponse(
        timestamp=datetime.utcnow().isoformat(),
        latency=LatencyStatsResponse(
            p50_ms=round(latency_stats.p50, 2),
            p75_ms=round(latency_stats.p75, 2),
            p90_ms=round(latency_stats.p90, 2),
            p95_ms=round(latency_stats.p95, 2),
            p99_ms=round(latency_stats.p99, 2),
            mean_ms=round(latency_stats.mean, 2),
            sample_count=latency_stats.count,
        ),
        throughput=ThroughputResponse(
            requests_per_second=round(rps, 2),
            requests_per_minute=round(rps * 60, 2),
            total_requests=summary["total_requests"],
        ),
        error_rate=ErrorRateResponse(
            error_rate_percent=round(error_rate, 2),
            total_errors=summary["total_errors"],
            total_requests=summary["total_requests"],
        ),
        resources=ResourceUsageResponse(
            cpu_percent=round(process.cpu_percent(interval=0.1), 2),
            memory_percent=round(process.memory_percent(), 2),
            memory_mb=round(process.memory_info().rss / 1024 / 1024, 2),
            thread_count=threading.active_count(),
            open_files=len(process.open_files()) if hasattr(process, "open_files") else 0,
        ),
        db_pool=DBPoolStatusResponse(
            pool_size=20,
            checked_out=5,
            checked_in=15,
            overflow=0,
            status="healthy",
        ),
    )


@router.get(
    "/endpoints",
    response_model=List[EndpointPerformanceResponse],
    summary="Get per-endpoint performance",
    description="Returns performance statistics for each endpoint.",
)
async def get_endpoint_performance(
    limit: int = Query(10, ge=1, le=100, description="Maximum endpoints to return"),
) -> List[EndpointPerformanceResponse]:
    """Get per-endpoint performance statistics."""
    collector = get_performance_collector()
    summary = collector.get_summary()

    result = []
    for path, count in list(summary["top_endpoints"].items())[:limit]:
        with collector._metrics_lock:
            latencies = collector._latencies_by_path.get(path, [])

        stats = collector.get_percentile_stats(latencies=latencies)

        result.append(EndpointPerformanceResponse(
            path=path,
            request_count=count,
            latency=LatencyStatsResponse(
                p50_ms=round(stats.p50, 2),
                p75_ms=round(stats.p75, 2),
                p90_ms=round(stats.p90, 2),
                p95_ms=round(stats.p95, 2),
                p99_ms=round(stats.p99, 2),
                mean_ms=round(stats.mean, 2),
                sample_count=stats.count,
            ),
        ))

    return result


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Performance health check",
    description="Returns performance health status with thresholds.",
)
async def get_performance_health() -> HealthResponse:
    """Get performance health status."""
    collector = get_performance_collector()
    latency_stats = collector.get_percentile_stats(window_minutes=5)
    error_rate = collector.get_error_rate(window_minutes=5)
    process = psutil.Process()

    cpu_percent = process.cpu_percent(interval=0.1)
    memory_percent = process.memory_percent()

    # Determine health status
    healthy = True
    status = "healthy"

    if latency_stats.p95 > 500:  # P95 > 500ms
        healthy = False
        status = "degraded - high latency"
    elif error_rate > 5:  # Error rate > 5%
        healthy = False
        status = "degraded - high error rate"
    elif cpu_percent > 90:  # CPU > 90%
        healthy = False
        status = "degraded - high CPU"
    elif memory_percent > 90:  # Memory > 90%
        healthy = False
        status = "degraded - high memory"

    return HealthResponse(
        status=status,
        p95_latency_ms=round(latency_stats.p95, 2),
        error_rate_percent=round(error_rate, 2),
        cpu_percent=round(cpu_percent, 2),
        memory_percent=round(memory_percent, 2),
        healthy=healthy,
    )


@router.get(
    "/prometheus",
    summary="Prometheus metrics endpoint",
    description="Returns performance metrics in Prometheus exposition format.",
)
async def get_prometheus_metrics() -> PlainTextResponse:
    """Get performance metrics in Prometheus format."""
    collector = get_performance_collector()
    latency_stats = collector.get_percentile_stats(window_minutes=5)
    rps = collector.get_rps(window_seconds=60)
    error_rate = collector.get_error_rate(window_minutes=5)
    summary = collector.get_summary()
    process = psutil.Process()

    lines = [
        "# HELP http_request_duration_ms HTTP request duration in milliseconds",
        "# TYPE http_request_duration_ms summary",
        f'http_request_duration_ms{{quantile="0.5"}} {latency_stats.p50}',
        f'http_request_duration_ms{{quantile="0.75"}} {latency_stats.p75}',
        f'http_request_duration_ms{{quantile="0.9"}} {latency_stats.p90}',
        f'http_request_duration_ms{{quantile="0.95"}} {latency_stats.p95}',
        f'http_request_duration_ms{{quantile="0.99"}} {latency_stats.p99}',
        "",
        "# HELP http_requests_total Total HTTP requests",
        "# TYPE http_requests_total counter",
        f"http_requests_total {summary['total_requests']}",
        "",
        "# HELP http_requests_per_second HTTP requests per second",
        "# TYPE http_requests_per_second gauge",
        f"http_requests_per_second {rps:.2f}",
        "",
        "# HELP http_error_rate_percent HTTP error rate percentage",
        "# TYPE http_error_rate_percent gauge",
        f"http_error_rate_percent {error_rate:.2f}",
        "",
        "# HELP process_cpu_percent Process CPU usage percentage",
        "# TYPE process_cpu_percent gauge",
        f"process_cpu_percent {process.cpu_percent(interval=0.1):.2f}",
        "",
        "# HELP process_memory_mb Process memory usage in MB",
        "# TYPE process_memory_mb gauge",
        f"process_memory_mb {process.memory_info().rss / 1024 / 1024:.2f}",
        "",
        "# HELP process_threads Active thread count",
        "# TYPE process_threads gauge",
        f"process_threads {threading.active_count()}",
    ]

    # Add per-method metrics
    lines.extend([
        "",
        "# HELP http_requests_by_method HTTP requests by method",
        "# TYPE http_requests_by_method counter",
    ])
    for method, count in summary["requests_by_method"].items():
        lines.append(f'http_requests_by_method{{method="{method}"}} {count}')

    # Add per-status metrics
    lines.extend([
        "",
        "# HELP http_requests_by_status HTTP requests by status code",
        "# TYPE http_requests_by_status counter",
    ])
    for status, count in summary["requests_by_status"].items():
        lines.append(f'http_requests_by_status{{status="{status}"}} {count}')

    return PlainTextResponse(
        content="\n".join(lines),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.post(
    "/test/request",
    summary="Generate test request metric",
    description="Generates test request metrics for dashboard testing.",
)
async def generate_test_request(
    method: str = Query("GET", description="HTTP method"),
    path: str = Query("/api/test", description="Request path"),
    status_code: int = Query(200, description="Response status code"),
    duration_ms: float = Query(50.0, description="Request duration in ms"),
    count: int = Query(1, ge=1, le=100, description="Number of requests to generate"),
) -> Dict[str, Any]:
    """Generate test request metrics."""
    collector = get_performance_collector()

    for _ in range(count):
        collector.record_request(
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
        )

    return {
        "status": "ok",
        "message": f"Generated {count} test request(s)",
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": duration_ms,
    }


@router.post(
    "/test/load",
    summary="Generate load test data",
    description="Generates varied load test data for dashboard testing.",
)
async def generate_load_test_data(
    requests: int = Query(100, ge=1, le=1000, description="Number of requests"),
) -> Dict[str, Any]:
    """Generate varied load test data."""
    import random

    collector = get_performance_collector()

    methods = ["GET", "POST", "PUT", "DELETE"]
    paths = [
        "/api/v1/workflows",
        "/api/v1/executions",
        "/api/v1/agents",
        "/api/v1/users",
        "/api/v1/health",
    ]

    for _ in range(requests):
        method = random.choice(methods)
        path = random.choice(paths)

        # 95% success, 5% errors
        if random.random() < 0.95:
            status_code = random.choice([200, 201, 204])
        else:
            status_code = random.choice([500, 502, 503])

        # Random latency with some outliers
        if random.random() < 0.9:
            duration_ms = random.uniform(10, 100)  # Normal
        else:
            duration_ms = random.uniform(100, 500)  # Slow

        collector.record_request(
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
        )

    return {
        "status": "ok",
        "message": f"Generated {requests} test requests with varied data",
        "summary": collector.get_summary(),
    }

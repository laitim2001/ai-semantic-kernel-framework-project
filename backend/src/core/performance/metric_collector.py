"""
Metric Collector Module for IPA Platform

Sprint 12 - S12-1: PerformanceProfiler 效能分析器
This module provides system and application metrics collection capabilities.

Features:
- System metrics collection (CPU, memory, disk, network)
- Application metrics collection (requests, latency, errors)
- Real-time metric streaming
- Aggregation and statistical analysis
- Configurable collection intervals

Author: IPA Platform Team
Created: 2025-12-05
"""

import asyncio
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class CollectorType(str, Enum):
    """Types of metric collectors."""
    SYSTEM = "system"
    APPLICATION = "application"
    CUSTOM = "custom"


class AggregationType(str, Enum):
    """Types of metric aggregation."""
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    P50 = "p50"
    P90 = "p90"
    P95 = "p95"
    P99 = "p99"


@dataclass
class SystemMetrics:
    """
    System-level performance metrics.

    Captures CPU, memory, disk, and network statistics
    for comprehensive system health monitoring.
    """
    timestamp: datetime
    cpu_percent: float
    cpu_count: int
    memory_total_gb: float
    memory_used_gb: float
    memory_percent: float
    disk_total_gb: float
    disk_used_gb: float
    disk_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    process_count: int

    @property
    def memory_available_gb(self) -> float:
        """Calculate available memory."""
        return self.memory_total_gb - self.memory_used_gb

    @property
    def disk_available_gb(self) -> float:
        """Calculate available disk space."""
        return self.disk_total_gb - self.disk_used_gb

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "cpu": {
                "percent": self.cpu_percent,
                "count": self.cpu_count
            },
            "memory": {
                "total_gb": self.memory_total_gb,
                "used_gb": self.memory_used_gb,
                "available_gb": self.memory_available_gb,
                "percent": self.memory_percent
            },
            "disk": {
                "total_gb": self.disk_total_gb,
                "used_gb": self.disk_used_gb,
                "available_gb": self.disk_available_gb,
                "percent": self.disk_percent
            },
            "network": {
                "bytes_sent": self.network_bytes_sent,
                "bytes_recv": self.network_bytes_recv
            },
            "process_count": self.process_count
        }


@dataclass
class ApplicationMetrics:
    """
    Application-level performance metrics.

    Tracks request rates, response times, error rates,
    and other application-specific indicators.
    """
    timestamp: datetime
    request_count: int = 0
    success_count: int = 0
    error_count: int = 0
    total_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')
    max_latency_ms: float = 0.0
    active_connections: int = 0
    queue_size: int = 0
    cache_hits: int = 0
    cache_misses: int = 0

    @property
    def error_rate(self) -> float:
        """Calculate error rate as percentage."""
        if self.request_count == 0:
            return 0.0
        return (self.error_count / self.request_count) * 100

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.request_count == 0:
            return 100.0
        return (self.success_count / self.request_count) * 100

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency."""
        if self.request_count == 0:
            return 0.0
        return self.total_latency_ms / self.request_count

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate as percentage."""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return (self.cache_hits / total) * 100

    def record_request(
        self,
        latency_ms: float,
        success: bool = True,
        cache_hit: Optional[bool] = None
    ) -> None:
        """Record a single request."""
        self.request_count += 1
        self.total_latency_ms += latency_ms
        self.min_latency_ms = min(self.min_latency_ms, latency_ms)
        self.max_latency_ms = max(self.max_latency_ms, latency_ms)

        if success:
            self.success_count += 1
        else:
            self.error_count += 1

        if cache_hit is not None:
            if cache_hit:
                self.cache_hits += 1
            else:
                self.cache_misses += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "requests": {
                "total": self.request_count,
                "success": self.success_count,
                "error": self.error_count,
                "success_rate": self.success_rate,
                "error_rate": self.error_rate
            },
            "latency": {
                "avg_ms": self.avg_latency_ms,
                "min_ms": self.min_latency_ms if self.min_latency_ms != float('inf') else 0.0,
                "max_ms": self.max_latency_ms
            },
            "connections": {
                "active": self.active_connections,
                "queue_size": self.queue_size
            },
            "cache": {
                "hits": self.cache_hits,
                "misses": self.cache_misses,
                "hit_rate": self.cache_hit_rate
            }
        }


@dataclass
class MetricSample:
    """A single metric sample with metadata."""
    name: str
    value: float
    timestamp: datetime
    collector_type: CollectorType
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = ""


@dataclass
class AggregatedMetric:
    """Aggregated metric result."""
    name: str
    aggregation_type: AggregationType
    value: float
    sample_count: int
    start_time: datetime
    end_time: datetime
    tags: Dict[str, str] = field(default_factory=dict)


class MetricCollector:
    """
    Central metric collection and aggregation service.

    Provides:
    - System and application metric collection
    - Custom metric registration
    - Real-time metric streaming
    - Historical data aggregation
    - Threshold-based alerting

    Usage:
        collector = MetricCollector()
        await collector.start()

        # Get current system metrics
        system_metrics = await collector.collect_system_metrics()

        # Record application metric
        collector.record("api.latency", 45.2, tags={"endpoint": "/users"})

        # Get aggregated metrics
        avg_latency = collector.aggregate("api.latency", AggregationType.AVG)

        await collector.stop()
    """

    def __init__(
        self,
        collection_interval: float = 10.0,
        retention_minutes: int = 60,
        max_samples: int = 10000
    ):
        """
        Initialize the metric collector.

        Args:
            collection_interval: Interval between automatic collections (seconds)
            retention_minutes: How long to retain metric samples
            max_samples: Maximum number of samples to retain per metric
        """
        self.collection_interval = collection_interval
        self.retention_minutes = retention_minutes
        self.max_samples = max_samples

        self._samples: Dict[str, List[MetricSample]] = {}
        self._system_metrics_history: List[SystemMetrics] = []
        self._app_metrics: ApplicationMetrics = ApplicationMetrics(timestamp=datetime.utcnow())
        self._running = False
        self._collection_task: Optional[asyncio.Task] = None
        self._callbacks: List[Callable[[MetricSample], None]] = []
        self._thresholds: Dict[str, Tuple[float, float]] = {}  # (min, max)
        self._alerts: List[Dict[str, Any]] = []

    async def start(self) -> None:
        """Start automatic metric collection."""
        if self._running:
            return

        self._running = True
        self._collection_task = asyncio.create_task(self._collection_loop())

    async def stop(self) -> None:
        """Stop automatic metric collection."""
        self._running = False
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
            self._collection_task = None

    async def _collection_loop(self) -> None:
        """Background loop for automatic metric collection."""
        while self._running:
            try:
                # Collect system metrics
                system_metrics = await self.collect_system_metrics()
                self._system_metrics_history.append(system_metrics)

                # Trim old system metrics
                cutoff = datetime.utcnow() - timedelta(minutes=self.retention_minutes)
                self._system_metrics_history = [
                    m for m in self._system_metrics_history
                    if m.timestamp > cutoff
                ]

                # Record system metrics as samples
                self.record("system.cpu_percent", system_metrics.cpu_percent,
                           CollectorType.SYSTEM)
                self.record("system.memory_percent", system_metrics.memory_percent,
                           CollectorType.SYSTEM)
                self.record("system.disk_percent", system_metrics.disk_percent,
                           CollectorType.SYSTEM)

                await asyncio.sleep(self.collection_interval)

            except asyncio.CancelledError:
                break
            except Exception:
                # Log error but continue collection
                await asyncio.sleep(self.collection_interval)

    async def collect_system_metrics(self) -> SystemMetrics:
        """
        Collect current system metrics.

        Returns:
            SystemMetrics object with current system state
        """
        timestamp = datetime.utcnow()

        if PSUTIL_AVAILABLE:
            # Real system metrics using psutil
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count() or 1

            memory = psutil.virtual_memory()
            memory_total_gb = memory.total / (1024 ** 3)
            memory_used_gb = memory.used / (1024 ** 3)
            memory_percent = memory.percent

            disk = psutil.disk_usage('/')
            disk_total_gb = disk.total / (1024 ** 3)
            disk_used_gb = disk.used / (1024 ** 3)
            disk_percent = disk.percent

            net = psutil.net_io_counters()
            network_bytes_sent = net.bytes_sent
            network_bytes_recv = net.bytes_recv

            process_count = len(psutil.pids())
        else:
            # Fallback with simulated values for environments without psutil
            cpu_percent = 0.0
            cpu_count = os.cpu_count() or 1
            memory_total_gb = 16.0
            memory_used_gb = 8.0
            memory_percent = 50.0
            disk_total_gb = 500.0
            disk_used_gb = 250.0
            disk_percent = 50.0
            network_bytes_sent = 0
            network_bytes_recv = 0
            process_count = 100

        return SystemMetrics(
            timestamp=timestamp,
            cpu_percent=cpu_percent,
            cpu_count=cpu_count,
            memory_total_gb=memory_total_gb,
            memory_used_gb=memory_used_gb,
            memory_percent=memory_percent,
            disk_total_gb=disk_total_gb,
            disk_used_gb=disk_used_gb,
            disk_percent=disk_percent,
            network_bytes_sent=network_bytes_sent,
            network_bytes_recv=network_bytes_recv,
            process_count=process_count
        )

    def record(
        self,
        name: str,
        value: float,
        collector_type: CollectorType = CollectorType.APPLICATION,
        tags: Optional[Dict[str, str]] = None,
        unit: str = ""
    ) -> MetricSample:
        """
        Record a metric sample.

        Args:
            name: Metric name (e.g., "api.latency", "db.queries")
            value: Metric value
            collector_type: Type of collector (system, application, custom)
            tags: Optional tags for filtering
            unit: Unit of measurement (e.g., "ms", "bytes")

        Returns:
            The recorded MetricSample
        """
        sample = MetricSample(
            name=name,
            value=value,
            timestamp=datetime.utcnow(),
            collector_type=collector_type,
            tags=tags or {},
            unit=unit
        )

        # Store sample
        if name not in self._samples:
            self._samples[name] = []

        self._samples[name].append(sample)

        # Trim to max samples
        if len(self._samples[name]) > self.max_samples:
            self._samples[name] = self._samples[name][-self.max_samples:]

        # Check thresholds
        self._check_threshold(name, value)

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(sample)
            except Exception:
                pass

        return sample

    def record_request(
        self,
        latency_ms: float,
        success: bool = True,
        cache_hit: Optional[bool] = None,
        endpoint: Optional[str] = None
    ) -> None:
        """
        Record an application request.

        Args:
            latency_ms: Request latency in milliseconds
            success: Whether the request was successful
            cache_hit: Whether the request was served from cache
            endpoint: Optional endpoint identifier
        """
        self._app_metrics.record_request(latency_ms, success, cache_hit)

        tags = {}
        if endpoint:
            tags["endpoint"] = endpoint

        self.record("app.latency", latency_ms, tags=tags, unit="ms")
        self.record("app.success", 1.0 if success else 0.0, tags=tags)

        if cache_hit is not None:
            self.record("app.cache_hit", 1.0 if cache_hit else 0.0, tags=tags)

    def get_application_metrics(self) -> ApplicationMetrics:
        """Get current application metrics."""
        return self._app_metrics

    def reset_application_metrics(self) -> ApplicationMetrics:
        """Reset application metrics and return the old values."""
        old_metrics = self._app_metrics
        self._app_metrics = ApplicationMetrics(timestamp=datetime.utcnow())
        return old_metrics

    def get_samples(
        self,
        name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> List[MetricSample]:
        """
        Get metric samples with optional filtering.

        Args:
            name: Metric name
            start_time: Filter samples after this time
            end_time: Filter samples before this time
            tags: Filter samples with matching tags

        Returns:
            List of matching MetricSamples
        """
        if name not in self._samples:
            return []

        samples = self._samples[name]

        if start_time:
            samples = [s for s in samples if s.timestamp >= start_time]

        if end_time:
            samples = [s for s in samples if s.timestamp <= end_time]

        if tags:
            samples = [
                s for s in samples
                if all(s.tags.get(k) == v for k, v in tags.items())
            ]

        return samples

    def aggregate(
        self,
        name: str,
        aggregation_type: AggregationType,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> Optional[AggregatedMetric]:
        """
        Aggregate metric samples.

        Args:
            name: Metric name
            aggregation_type: Type of aggregation to perform
            start_time: Filter samples after this time
            end_time: Filter samples before this time
            tags: Filter samples with matching tags

        Returns:
            AggregatedMetric or None if no samples
        """
        samples = self.get_samples(name, start_time, end_time, tags)

        if not samples:
            return None

        values = [s.value for s in samples]
        sorted_values = sorted(values)

        if aggregation_type == AggregationType.SUM:
            value = sum(values)
        elif aggregation_type == AggregationType.AVG:
            value = sum(values) / len(values)
        elif aggregation_type == AggregationType.MIN:
            value = min(values)
        elif aggregation_type == AggregationType.MAX:
            value = max(values)
        elif aggregation_type == AggregationType.COUNT:
            value = float(len(values))
        elif aggregation_type == AggregationType.P50:
            value = self._percentile(sorted_values, 50)
        elif aggregation_type == AggregationType.P90:
            value = self._percentile(sorted_values, 90)
        elif aggregation_type == AggregationType.P95:
            value = self._percentile(sorted_values, 95)
        elif aggregation_type == AggregationType.P99:
            value = self._percentile(sorted_values, 99)
        else:
            value = sum(values) / len(values)

        return AggregatedMetric(
            name=name,
            aggregation_type=aggregation_type,
            value=value,
            sample_count=len(samples),
            start_time=min(s.timestamp for s in samples),
            end_time=max(s.timestamp for s in samples),
            tags=tags or {}
        )

    def _percentile(self, sorted_values: List[float], percentile: int) -> float:
        """Calculate percentile from sorted values."""
        if not sorted_values:
            return 0.0

        k = (len(sorted_values) - 1) * percentile / 100
        f = int(k)
        c = f + 1 if f < len(sorted_values) - 1 else f

        if f == c:
            return sorted_values[f]

        return sorted_values[f] * (c - k) + sorted_values[c] * (k - f)

    def set_threshold(
        self,
        name: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> None:
        """
        Set threshold for a metric.

        Args:
            name: Metric name
            min_value: Minimum acceptable value (alert if below)
            max_value: Maximum acceptable value (alert if above)
        """
        self._thresholds[name] = (
            min_value if min_value is not None else float('-inf'),
            max_value if max_value is not None else float('inf')
        )

    def _check_threshold(self, name: str, value: float) -> None:
        """Check if value exceeds threshold and create alert."""
        if name not in self._thresholds:
            return

        min_val, max_val = self._thresholds[name]

        if value < min_val:
            self._alerts.append({
                "metric": name,
                "value": value,
                "threshold_type": "min",
                "threshold_value": min_val,
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"{name} ({value}) is below minimum threshold ({min_val})"
            })
        elif value > max_val:
            self._alerts.append({
                "metric": name,
                "value": value,
                "threshold_type": "max",
                "threshold_value": max_val,
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"{name} ({value}) is above maximum threshold ({max_val})"
            })

    def get_alerts(self, clear: bool = False) -> List[Dict[str, Any]]:
        """
        Get current alerts.

        Args:
            clear: Whether to clear alerts after retrieval

        Returns:
            List of alert dictionaries
        """
        alerts = list(self._alerts)
        if clear:
            self._alerts.clear()
        return alerts

    def add_callback(self, callback: Callable[[MetricSample], None]) -> None:
        """Add a callback for real-time metric notifications."""
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[MetricSample], None]) -> None:
        """Remove a metric callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def get_metric_names(self) -> List[str]:
        """Get all recorded metric names."""
        return list(self._samples.keys())

    def get_system_metrics_history(
        self,
        limit: Optional[int] = None
    ) -> List[SystemMetrics]:
        """
        Get historical system metrics.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of SystemMetrics in chronological order
        """
        if limit:
            return self._system_metrics_history[-limit:]
        return list(self._system_metrics_history)

    def clear(self, name: Optional[str] = None) -> None:
        """
        Clear metric samples.

        Args:
            name: Metric name to clear, or None to clear all
        """
        if name:
            self._samples.pop(name, None)
        else:
            self._samples.clear()
            self._system_metrics_history.clear()
            self._app_metrics = ApplicationMetrics(timestamp=datetime.utcnow())

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of collected metrics."""
        return {
            "metric_count": len(self._samples),
            "total_samples": sum(len(samples) for samples in self._samples.values()),
            "system_metrics_count": len(self._system_metrics_history),
            "application_metrics": self._app_metrics.to_dict(),
            "alert_count": len(self._alerts),
            "active_thresholds": len(self._thresholds),
            "callback_count": len(self._callbacks),
            "running": self._running
        }

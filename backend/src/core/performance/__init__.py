"""
IPA Platform - Performance Optimization Module

Sprint 12 - Integration & Polish
This module provides comprehensive performance optimization utilities including:
- Response compression middleware
- Request timing middleware
- Cache optimization helpers
- Database query optimization utilities
- Performance profiling and analysis (S12-1)
- Performance optimization strategies (S12-2)
- Concurrent execution optimization (S12-3)
- Metric collection and benchmarking

Author: IPA Platform Team
Version: 2.0.0
"""

# Existing middleware components
from .middleware import (
    CompressionMiddleware,
    TimingMiddleware,
    ETagMiddleware,
)
from .cache_optimizer import CacheOptimizer
from .db_optimizer import QueryOptimizer

# S12-1: PerformanceProfiler 效能分析器
from .profiler import (
    MetricType,
    PerformanceMetric,
    ProfileSession,
    PerformanceProfiler,
    OptimizationRecommendation,
)

# S12-2: PerformanceOptimizer 效能優化器
from .optimizer import (
    OptimizationStrategy,
    BenchmarkMetrics,
    OptimizationResult,
    PerformanceOptimizer,
)

# S12-3: ConcurrentOptimizer 並發優化器
from .concurrent_optimizer import (
    ConcurrencyConfig,
    ExecutionResult,
    BatchExecutionStats,
    ConcurrentOptimizer,
    WorkerPool,
)

# Metric Collection
from .metric_collector import (
    CollectorType,
    AggregationType,
    SystemMetrics,
    ApplicationMetrics,
    MetricSample,
    AggregatedMetric,
    MetricCollector,
)

# Benchmarking
from .benchmark import (
    BenchmarkStatus,
    ComparisonResult,
    BenchmarkConfig,
    BenchmarkResult,
    BenchmarkComparison,
    BenchmarkReport,
    BenchmarkRunner,
    benchmark,
)

__all__ = [
    # Middleware
    "CompressionMiddleware",
    "TimingMiddleware",
    "ETagMiddleware",
    "CacheOptimizer",
    "QueryOptimizer",
    # Profiler (S12-1)
    "MetricType",
    "PerformanceMetric",
    "ProfileSession",
    "PerformanceProfiler",
    "OptimizationRecommendation",
    # Optimizer (S12-2)
    "OptimizationStrategy",
    "BenchmarkMetrics",
    "OptimizationResult",
    "PerformanceOptimizer",
    # Concurrent Optimizer (S12-3)
    "ConcurrencyConfig",
    "ExecutionResult",
    "BatchExecutionStats",
    "ConcurrentOptimizer",
    "WorkerPool",
    # Metric Collector
    "CollectorType",
    "AggregationType",
    "SystemMetrics",
    "ApplicationMetrics",
    "MetricSample",
    "AggregatedMetric",
    "MetricCollector",
    # Benchmark
    "BenchmarkStatus",
    "ComparisonResult",
    "BenchmarkConfig",
    "BenchmarkResult",
    "BenchmarkComparison",
    "BenchmarkReport",
    "BenchmarkRunner",
    "benchmark",
]

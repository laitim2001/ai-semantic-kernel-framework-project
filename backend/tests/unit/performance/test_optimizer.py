"""
Performance Optimizer Unit Tests
Sprint 12 - S12-7: Testing

Tests for:
- OptimizationStrategy enum
- BenchmarkMetrics dataclass
- PerformanceOptimizer class
  - analyze_and_optimize()
  - _run_benchmark()
  - _map_recommendation_to_strategy()
  - _apply_* strategies
  - _calculate_improvement()
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from src.core.performance.optimizer import (
    OptimizationStrategy,
    BenchmarkMetrics,
    PerformanceOptimizer
)
from src.core.performance.profiler import PerformanceProfiler


class TestOptimizationStrategy:
    """OptimizationStrategy enum tests"""

    def test_strategy_values(self):
        """Test all OptimizationStrategy enum values"""
        assert OptimizationStrategy.CACHING == "caching"
        assert OptimizationStrategy.BATCHING == "batching"
        assert OptimizationStrategy.CONNECTION_POOLING == "connection_pooling"
        assert OptimizationStrategy.QUERY_OPTIMIZATION == "query_optimization"
        assert OptimizationStrategy.ASYNC_PROCESSING == "async_processing"
        assert OptimizationStrategy.LAZY_LOADING == "lazy_loading"

    def test_strategy_count(self):
        """Test OptimizationStrategy has 6 values"""
        assert len(OptimizationStrategy) == 6


class TestBenchmarkMetrics:
    """BenchmarkMetrics dataclass tests"""

    def test_create_metrics(self):
        """Test creating BenchmarkMetrics"""
        metrics = BenchmarkMetrics(
            avg_latency_ms=100.0,
            p95_latency_ms=150.0,
            p99_latency_ms=200.0,
            throughput_rps=500.0,
            error_rate=0.01,
            memory_mb=256.0,
            cpu_percent=45.0
        )

        assert metrics.avg_latency_ms == 100.0
        assert metrics.p95_latency_ms == 150.0
        assert metrics.p99_latency_ms == 200.0
        assert metrics.throughput_rps == 500.0
        assert metrics.error_rate == 0.01
        assert metrics.memory_mb == 256.0
        assert metrics.cpu_percent == 45.0

    def test_metrics_default_values(self):
        """Test BenchmarkMetrics default values"""
        metrics = BenchmarkMetrics(
            avg_latency_ms=100.0,
            p95_latency_ms=150.0,
            p99_latency_ms=200.0,
            throughput_rps=500.0,
            error_rate=0.01
        )

        assert metrics.memory_mb == 0.0
        assert metrics.cpu_percent == 0.0


class TestPerformanceOptimizer:
    """PerformanceOptimizer class tests"""

    @pytest.fixture
    def profiler(self):
        """Create a mock profiler"""
        profiler = PerformanceProfiler()
        return profiler

    @pytest.fixture
    def optimizer(self, profiler):
        """Create optimizer with mock dependencies"""
        cache_service = Mock()
        config = {"optimization_enabled": True}
        return PerformanceOptimizer(profiler, cache_service, config)

    def test_init(self, optimizer):
        """Test optimizer initialization"""
        assert optimizer.profiler is not None
        assert optimizer.cache is not None
        assert optimizer.config is not None
        assert len(optimizer._strategies) == 4

    def test_strategies_registered(self, optimizer):
        """Test all strategies are registered"""
        assert "caching" in optimizer._strategies
        assert "batching" in optimizer._strategies
        assert "connection_pooling" in optimizer._strategies
        assert "query_optimization" in optimizer._strategies

    @pytest.mark.asyncio
    async def test_analyze_and_optimize(self, optimizer):
        """Test analyze_and_optimize flow"""
        # Mock get_recommendations to return known values
        optimizer.profiler.get_recommendations = Mock(return_value=[
            {"type": "latency", "severity": "high", "message": "High latency"}
        ])

        result = await optimizer.analyze_and_optimize("test_target")

        assert "target" in result
        assert result["target"] == "test_target"
        assert "baseline" in result
        assert "optimized" in result
        assert "improvement" in result
        assert "recommendations" in result

    @pytest.mark.asyncio
    async def test_run_benchmark(self, optimizer):
        """Test _run_benchmark method"""
        result = await optimizer._run_benchmark("test")

        assert "avg_latency_ms" in result
        assert "p95_latency_ms" in result
        assert "error_rate" in result
        assert "throughput_rps" in result

    def test_map_recommendation_to_strategy(self, optimizer):
        """Test recommendation to strategy mapping"""
        latency_rec = {"type": "latency"}
        variance_rec = {"type": "latency_variance"}
        concurrency_rec = {"type": "concurrency"}
        unknown_rec = {"type": "unknown"}

        assert optimizer._map_recommendation_to_strategy(latency_rec) == "caching"
        assert optimizer._map_recommendation_to_strategy(variance_rec) == "query_optimization"
        assert optimizer._map_recommendation_to_strategy(concurrency_rec) == "connection_pooling"
        assert optimizer._map_recommendation_to_strategy(unknown_rec) is None

    @pytest.mark.asyncio
    async def test_apply_caching(self, optimizer):
        """Test _apply_caching strategy"""
        # Should not raise
        await optimizer._apply_caching("test_target")

    @pytest.mark.asyncio
    async def test_apply_batching(self, optimizer):
        """Test _apply_batching strategy"""
        await optimizer._apply_batching("test_target")

    @pytest.mark.asyncio
    async def test_apply_connection_pooling(self, optimizer):
        """Test _apply_connection_pooling strategy"""
        await optimizer._apply_connection_pooling("test_target")

    @pytest.mark.asyncio
    async def test_apply_query_optimization(self, optimizer):
        """Test _apply_query_optimization strategy"""
        await optimizer._apply_query_optimization("test_target")

    def test_calculate_improvement(self, optimizer):
        """Test improvement calculation"""
        baseline = {
            "avg_latency_ms": 200.0,
            "throughput_rps": 100.0,
            "error_rate": 0.10
        }
        optimized = {
            "avg_latency_ms": 150.0,  # 25% improvement
            "throughput_rps": 125.0,  # 25% improvement
            "error_rate": 0.05       # 50% improvement
        }

        improvement = optimizer._calculate_improvement(baseline, optimized)

        assert improvement["latency_improvement"] == 25.0
        assert improvement["throughput_improvement"] == 25.0
        assert improvement["error_rate_improvement"] == 50.0

    def test_calculate_improvement_zero_baseline(self, optimizer):
        """Test improvement calculation with zero baseline"""
        baseline = {
            "avg_latency_ms": 0.0,
            "throughput_rps": 0.0,
            "error_rate": 0.0
        }
        optimized = {
            "avg_latency_ms": 100.0,
            "throughput_rps": 100.0,
            "error_rate": 0.05
        }

        improvement = optimizer._calculate_improvement(baseline, optimized)

        # Should handle zero division gracefully
        assert improvement["latency_improvement"] == 0
        assert improvement["throughput_improvement"] == 0
        assert improvement["error_rate_improvement"] == 0

    @pytest.mark.asyncio
    async def test_analyze_with_no_recommendations(self, optimizer):
        """Test analyze when no recommendations returned"""
        optimizer.profiler.get_recommendations = Mock(return_value=[])

        result = await optimizer.analyze_and_optimize("test")

        assert result["applied_strategies"] == []

    @pytest.mark.asyncio
    async def test_analyze_applies_mapped_strategies(self, optimizer):
        """Test that mapped strategies are applied"""
        optimizer.profiler.get_recommendations = Mock(return_value=[
            {"type": "latency", "severity": "high"},
            {"type": "concurrency", "severity": "medium"}
        ])

        result = await optimizer.analyze_and_optimize("test")

        assert "caching" in result["applied_strategies"]
        assert "connection_pooling" in result["applied_strategies"]

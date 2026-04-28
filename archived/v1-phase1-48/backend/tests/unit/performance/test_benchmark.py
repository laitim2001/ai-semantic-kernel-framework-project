"""
Benchmark Runner Unit Tests
Sprint 12 - S12-7: Testing

Tests for:
- BenchmarkConfig dataclass
- BenchmarkResult dataclass
- BenchmarkComparison dataclass
- BenchmarkReport dataclass
- BenchmarkRunner class
  - run_sync()
  - run_async()
  - run_suite()
  - compare()
  - detect_regressions()
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch

from src.core.performance.benchmark import (
    BenchmarkConfig,
    BenchmarkResult,
    BenchmarkComparison,
    BenchmarkReport,
    BenchmarkRunner
)


class TestBenchmarkConfig:
    """BenchmarkConfig dataclass tests"""

    def test_default_config(self):
        """Test default configuration values"""
        config = BenchmarkConfig()

        assert config.iterations == 100
        assert config.warmup_iterations == 10
        assert config.timeout_seconds == 60.0
        assert config.collect_memory is True
        assert config.collect_cpu is True

    def test_custom_config(self):
        """Test custom configuration"""
        config = BenchmarkConfig(
            iterations=50,
            warmup_iterations=5,
            timeout_seconds=30.0,
            collect_memory=False,
            collect_cpu=False
        )

        assert config.iterations == 50
        assert config.warmup_iterations == 5
        assert config.timeout_seconds == 30.0
        assert config.collect_memory is False
        assert config.collect_cpu is False


class TestBenchmarkResult:
    """BenchmarkResult dataclass tests"""

    def test_create_result(self):
        """Test creating a BenchmarkResult"""
        result = BenchmarkResult(
            name="test_benchmark",
            iterations=100,
            total_time_ms=5000.0,
            mean_ms=50.0,
            std_ms=5.0,
            min_ms=40.0,
            max_ms=70.0,
            p50_ms=49.0,
            p95_ms=60.0,
            p99_ms=68.0,
            throughput_ops=20.0
        )

        assert result.name == "test_benchmark"
        assert result.iterations == 100
        assert result.mean_ms == 50.0
        assert result.throughput_ops == 20.0

    def test_result_timestamp(self):
        """Test result has timestamp"""
        result = BenchmarkResult(
            name="test",
            iterations=10,
            total_time_ms=100.0,
            mean_ms=10.0,
            std_ms=1.0,
            min_ms=8.0,
            max_ms=12.0,
            p50_ms=10.0,
            p95_ms=11.0,
            p99_ms=12.0,
            throughput_ops=100.0
        )

        assert isinstance(result.timestamp, datetime)


class TestBenchmarkComparison:
    """BenchmarkComparison dataclass tests"""

    def test_create_comparison(self):
        """Test creating a BenchmarkComparison"""
        comparison = BenchmarkComparison(
            name="test",
            baseline_mean_ms=100.0,
            current_mean_ms=80.0,
            change_percent=-20.0,
            is_regression=False,
            is_improvement=True
        )

        assert comparison.name == "test"
        assert comparison.change_percent == -20.0
        assert comparison.is_improvement is True
        assert comparison.is_regression is False

    def test_regression_comparison(self):
        """Test comparison indicating regression"""
        comparison = BenchmarkComparison(
            name="test",
            baseline_mean_ms=100.0,
            current_mean_ms=150.0,
            change_percent=50.0,
            is_regression=True,
            is_improvement=False
        )

        assert comparison.is_regression is True


class TestBenchmarkReport:
    """BenchmarkReport dataclass tests"""

    def test_create_report(self):
        """Test creating a BenchmarkReport"""
        result1 = BenchmarkResult(
            name="bench1",
            iterations=100,
            total_time_ms=1000.0,
            mean_ms=10.0,
            std_ms=1.0,
            min_ms=8.0,
            max_ms=12.0,
            p50_ms=10.0,
            p95_ms=11.0,
            p99_ms=12.0,
            throughput_ops=100.0
        )

        report = BenchmarkReport(
            name="test_suite",
            total_duration_ms=5000.0,
            results=[result1],
            system_info={"os": "linux", "cpu": "Intel"}
        )

        assert report.name == "test_suite"
        assert len(report.results) == 1
        assert report.system_info["os"] == "linux"


class TestBenchmarkRunner:
    """BenchmarkRunner class tests"""

    @pytest.fixture
    def config(self):
        """Create test configuration"""
        return BenchmarkConfig(
            iterations=10,
            warmup_iterations=2,
            timeout_seconds=5.0
        )

    @pytest.fixture
    def runner(self, config):
        """Create benchmark runner"""
        return BenchmarkRunner(config)

    def test_init(self, runner, config):
        """Test runner initialization"""
        assert runner.config == config
        assert runner._baselines == {}

    def test_run_sync(self, runner):
        """Test running sync benchmark"""
        def simple_func():
            return sum(range(100))

        result = runner.run_sync("simple_sum", simple_func)

        assert result.name == "simple_sum"
        assert result.iterations == 10
        assert result.mean_ms > 0
        assert result.throughput_ops > 0

    def test_run_sync_with_args(self, runner):
        """Test running sync benchmark with arguments"""
        def add(a, b):
            return a + b

        result = runner.run_sync("addition", add, 5, 3)

        assert result.name == "addition"
        assert result.iterations == 10

    def test_run_sync_with_kwargs(self, runner):
        """Test running sync benchmark with kwargs"""
        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"

        result = runner.run_sync("greeting", greet, "World", greeting="Hi")

        assert result.name == "greeting"

    @pytest.mark.asyncio
    async def test_run_async(self, runner):
        """Test running async benchmark"""
        async def async_func():
            await asyncio.sleep(0.001)
            return "done"

        result = await runner.run_async("async_test", async_func)

        assert result.name == "async_test"
        assert result.iterations == 10
        assert result.mean_ms >= 1.0  # At least 1ms per iteration

    @pytest.mark.asyncio
    async def test_run_async_with_args(self, runner):
        """Test running async benchmark with arguments"""
        async def async_add(a, b):
            await asyncio.sleep(0.001)
            return a + b

        result = await runner.run_async("async_add", async_add, 10, 20)

        assert result.name == "async_add"

    @pytest.mark.asyncio
    async def test_run_suite(self, runner):
        """Test running a benchmark suite"""
        def func1():
            return 1

        async def func2():
            return 2

        benchmarks = [
            ("sync_bench", func1, [], {}),
            ("async_bench", func2, [], {}),
        ]

        report = await runner.run_suite("test_suite", benchmarks)

        assert report.name == "test_suite"
        assert len(report.results) == 2
        assert report.total_duration_ms > 0

    def test_compare(self, runner):
        """Test comparing benchmark results"""
        baseline = BenchmarkResult(
            name="test",
            iterations=100,
            total_time_ms=10000.0,
            mean_ms=100.0,
            std_ms=10.0,
            min_ms=80.0,
            max_ms=120.0,
            p50_ms=100.0,
            p95_ms=115.0,
            p99_ms=118.0,
            throughput_ops=10.0
        )

        current = BenchmarkResult(
            name="test",
            iterations=100,
            total_time_ms=8000.0,
            mean_ms=80.0,  # 20% improvement
            std_ms=8.0,
            min_ms=70.0,
            max_ms=100.0,
            p50_ms=80.0,
            p95_ms=95.0,
            p99_ms=98.0,
            throughput_ops=12.5
        )

        comparison = runner.compare(baseline, current)

        assert comparison.name == "test"
        assert comparison.baseline_mean_ms == 100.0
        assert comparison.current_mean_ms == 80.0
        assert comparison.change_percent == -20.0
        assert comparison.is_improvement is True
        assert comparison.is_regression is False

    def test_compare_regression(self, runner):
        """Test comparing with regression detection"""
        baseline = BenchmarkResult(
            name="test",
            iterations=100,
            total_time_ms=10000.0,
            mean_ms=100.0,
            std_ms=10.0,
            min_ms=80.0,
            max_ms=120.0,
            p50_ms=100.0,
            p95_ms=115.0,
            p99_ms=118.0,
            throughput_ops=10.0
        )

        current = BenchmarkResult(
            name="test",
            iterations=100,
            total_time_ms=15000.0,
            mean_ms=150.0,  # 50% regression
            std_ms=15.0,
            min_ms=130.0,
            max_ms=180.0,
            p50_ms=150.0,
            p95_ms=170.0,
            p99_ms=175.0,
            throughput_ops=6.7
        )

        comparison = runner.compare(baseline, current, regression_threshold=10.0)

        assert comparison.change_percent == 50.0
        assert comparison.is_regression is True
        assert comparison.is_improvement is False

    def test_detect_regressions(self, runner):
        """Test detecting regressions across multiple benchmarks"""
        # Set up baselines
        runner._baselines["fast"] = BenchmarkResult(
            name="fast",
            iterations=100,
            total_time_ms=1000.0,
            mean_ms=10.0,
            std_ms=1.0,
            min_ms=8.0,
            max_ms=12.0,
            p50_ms=10.0,
            p95_ms=11.0,
            p99_ms=12.0,
            throughput_ops=100.0
        )

        runner._baselines["slow"] = BenchmarkResult(
            name="slow",
            iterations=100,
            total_time_ms=10000.0,
            mean_ms=100.0,
            std_ms=10.0,
            min_ms=80.0,
            max_ms=120.0,
            p50_ms=100.0,
            p95_ms=115.0,
            p99_ms=118.0,
            throughput_ops=10.0
        )

        # Current results with one regression
        current_results = [
            BenchmarkResult(
                name="fast",
                iterations=100,
                total_time_ms=2000.0,
                mean_ms=20.0,  # 100% regression!
                std_ms=2.0,
                min_ms=18.0,
                max_ms=22.0,
                p50_ms=20.0,
                p95_ms=21.0,
                p99_ms=22.0,
                throughput_ops=50.0
            ),
            BenchmarkResult(
                name="slow",
                iterations=100,
                total_time_ms=9500.0,
                mean_ms=95.0,  # 5% improvement
                std_ms=9.0,
                min_ms=75.0,
                max_ms=115.0,
                p50_ms=95.0,
                p95_ms=110.0,
                p99_ms=113.0,
                throughput_ops=10.5
            )
        ]

        regressions = runner.detect_regressions(current_results, threshold=10.0)

        assert len(regressions) == 1
        assert regressions[0].name == "fast"
        assert regressions[0].is_regression is True

    def test_statistics_calculation(self, runner):
        """Test statistical calculations in benchmark results"""
        times = []

        def measured_func():
            import time
            time.sleep(0.01)  # 10ms
            return None

        result = runner.run_sync("stats_test", measured_func)

        # Check statistical values are reasonable
        assert result.min_ms <= result.mean_ms <= result.max_ms
        assert result.p50_ms <= result.p95_ms <= result.p99_ms
        assert result.std_ms >= 0

    @pytest.mark.asyncio
    async def test_warmup_excluded(self, runner):
        """Test that warmup iterations are excluded from results"""
        call_count = 0

        def counting_func():
            nonlocal call_count
            call_count += 1
            return None

        result = runner.run_sync("warmup_test", counting_func)

        # Should have run warmup (2) + iterations (10)
        assert call_count == 12
        # But result should only reflect measured iterations
        assert result.iterations == 10


class TestBenchmarkRunnerIntegration:
    """Integration tests for BenchmarkRunner"""

    @pytest.mark.asyncio
    async def test_full_benchmark_workflow(self):
        """Test complete benchmark workflow"""
        config = BenchmarkConfig(iterations=20, warmup_iterations=5)
        runner = BenchmarkRunner(config)

        # Define benchmarks
        def cpu_bound():
            return sum(i * i for i in range(1000))

        async def io_bound():
            await asyncio.sleep(0.005)
            return "done"

        # Run suite
        report = await runner.run_suite(
            "performance_suite",
            [
                ("cpu_benchmark", cpu_bound, [], {}),
                ("io_benchmark", io_bound, [], {}),
            ]
        )

        assert report.name == "performance_suite"
        assert len(report.results) == 2

        cpu_result = next(r for r in report.results if r.name == "cpu_benchmark")
        io_result = next(r for r in report.results if r.name == "io_benchmark")

        # IO bound should be slower
        assert io_result.mean_ms > cpu_result.mean_ms

    @pytest.mark.asyncio
    async def test_regression_detection_workflow(self):
        """Test regression detection workflow"""
        config = BenchmarkConfig(iterations=10, warmup_iterations=2)
        runner = BenchmarkRunner(config)

        # Establish baseline
        baseline = runner.run_sync(
            "baseline_test",
            lambda: sum(range(100))
        )
        runner._baselines["baseline_test"] = baseline

        # Simulate a slower implementation (regression)
        def slower_impl():
            import time
            time.sleep(0.01)  # Add 10ms delay
            return sum(range(100))

        current = runner.run_sync("baseline_test", slower_impl)

        comparison = runner.compare(baseline, current, regression_threshold=50.0)

        # The slower implementation should be detected as regression
        assert comparison.current_mean_ms > comparison.baseline_mean_ms

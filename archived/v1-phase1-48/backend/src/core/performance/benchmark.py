"""
Benchmark Module for IPA Platform

Sprint 12 - S12-1: PerformanceProfiler 效能分析器
This module provides comprehensive benchmarking capabilities for performance testing.

Features:
- Configurable benchmark execution
- Multiple iteration support with warm-up
- Statistical analysis (mean, median, std, percentiles)
- Comparison and regression detection
- Report generation

Author: IPA Platform Team
Created: 2025-12-05
"""

import asyncio
import gc
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, TypeVar, Union
from uuid import UUID, uuid4

T = TypeVar('T')


class BenchmarkStatus(str, Enum):
    """Status of a benchmark run."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ComparisonResult(str, Enum):
    """Result of benchmark comparison."""
    FASTER = "faster"
    SLOWER = "slower"
    SIMILAR = "similar"
    REGRESSION = "regression"
    IMPROVEMENT = "improvement"


@dataclass
class BenchmarkConfig:
    """
    Configuration for benchmark execution.

    Attributes:
        iterations: Number of benchmark iterations
        warmup_iterations: Number of warm-up iterations (not counted)
        timeout_seconds: Maximum time per iteration
        gc_collect: Whether to run garbage collection between iterations
        cooldown_seconds: Time to wait between iterations
        parallel: Whether to run async benchmarks in parallel
        max_concurrent: Maximum concurrent executions for parallel mode
    """
    iterations: int = 100
    warmup_iterations: int = 10
    timeout_seconds: float = 30.0
    gc_collect: bool = True
    cooldown_seconds: float = 0.01
    parallel: bool = False
    max_concurrent: int = 10


@dataclass
class BenchmarkResult:
    """
    Result of a single benchmark run.

    Contains timing information for one benchmark execution.
    """
    id: UUID
    name: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    iterations: int
    timings_ms: List[float]
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def mean_ms(self) -> float:
        """Calculate mean timing."""
        return statistics.mean(self.timings_ms) if self.timings_ms else 0.0

    @property
    def median_ms(self) -> float:
        """Calculate median timing."""
        return statistics.median(self.timings_ms) if self.timings_ms else 0.0

    @property
    def std_ms(self) -> float:
        """Calculate standard deviation."""
        if len(self.timings_ms) < 2:
            return 0.0
        return statistics.stdev(self.timings_ms)

    @property
    def min_ms(self) -> float:
        """Get minimum timing."""
        return min(self.timings_ms) if self.timings_ms else 0.0

    @property
    def max_ms(self) -> float:
        """Get maximum timing."""
        return max(self.timings_ms) if self.timings_ms else 0.0

    @property
    def p50_ms(self) -> float:
        """Calculate 50th percentile."""
        return self._percentile(50)

    @property
    def p90_ms(self) -> float:
        """Calculate 90th percentile."""
        return self._percentile(90)

    @property
    def p95_ms(self) -> float:
        """Calculate 95th percentile."""
        return self._percentile(95)

    @property
    def p99_ms(self) -> float:
        """Calculate 99th percentile."""
        return self._percentile(99)

    @property
    def ops_per_second(self) -> float:
        """Calculate operations per second."""
        if self.mean_ms <= 0:
            return 0.0
        return 1000.0 / self.mean_ms

    def _percentile(self, p: int) -> float:
        """Calculate percentile from timings."""
        if not self.timings_ms:
            return 0.0

        sorted_timings = sorted(self.timings_ms)
        k = (len(sorted_timings) - 1) * p / 100
        f = int(k)
        c = f + 1 if f < len(sorted_timings) - 1 else f

        if f == c:
            return sorted_timings[f]

        return sorted_timings[f] * (c - k) + sorted_timings[c] * (k - f)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "name": self.name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": self.duration_seconds,
            "iterations": self.iterations,
            "success": self.success,
            "error": self.error,
            "statistics": {
                "mean_ms": self.mean_ms,
                "median_ms": self.median_ms,
                "std_ms": self.std_ms,
                "min_ms": self.min_ms,
                "max_ms": self.max_ms,
                "p50_ms": self.p50_ms,
                "p90_ms": self.p90_ms,
                "p95_ms": self.p95_ms,
                "p99_ms": self.p99_ms,
                "ops_per_second": self.ops_per_second
            },
            "metadata": self.metadata
        }


@dataclass
class BenchmarkComparison:
    """Comparison between two benchmark results."""
    baseline: BenchmarkResult
    current: BenchmarkResult
    mean_diff_percent: float
    median_diff_percent: float
    p95_diff_percent: float
    result: ComparisonResult
    threshold_percent: float = 5.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "baseline": {
                "name": self.baseline.name,
                "mean_ms": self.baseline.mean_ms,
                "median_ms": self.baseline.median_ms,
                "p95_ms": self.baseline.p95_ms
            },
            "current": {
                "name": self.current.name,
                "mean_ms": self.current.mean_ms,
                "median_ms": self.current.median_ms,
                "p95_ms": self.current.p95_ms
            },
            "diff_percent": {
                "mean": self.mean_diff_percent,
                "median": self.median_diff_percent,
                "p95": self.p95_diff_percent
            },
            "result": self.result.value,
            "threshold_percent": self.threshold_percent
        }


@dataclass
class BenchmarkReport:
    """Complete benchmark report with multiple results."""
    id: UUID
    name: str
    description: str
    created_at: datetime
    results: List[BenchmarkResult]
    comparisons: List[BenchmarkComparison] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_iterations(self) -> int:
        """Get total iterations across all benchmarks."""
        return sum(r.iterations for r in self.results)

    @property
    def success_count(self) -> int:
        """Get count of successful benchmarks."""
        return sum(1 for r in self.results if r.success)

    @property
    def failure_count(self) -> int:
        """Get count of failed benchmarks."""
        return sum(1 for r in self.results if not r.success)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "summary": {
                "total_benchmarks": len(self.results),
                "success_count": self.success_count,
                "failure_count": self.failure_count,
                "total_iterations": self.total_iterations
            },
            "results": [r.to_dict() for r in self.results],
            "comparisons": [c.to_dict() for c in self.comparisons],
            "metadata": self.metadata
        }


class BenchmarkRunner:
    """
    Benchmark execution engine.

    Provides flexible benchmarking for both sync and async functions
    with comprehensive statistical analysis.

    Usage:
        runner = BenchmarkRunner()

        # Benchmark a sync function
        result = runner.run_sync("my_function", my_function, arg1, arg2)

        # Benchmark an async function
        result = await runner.run_async("my_async_function", my_async_function, arg1)

        # Run benchmark suite
        report = await runner.run_suite("My Suite", [
            ("func1", func1, []),
            ("func2", func2, []),
        ])

        # Compare results
        comparison = runner.compare(baseline_result, current_result)
    """

    def __init__(self, config: Optional[BenchmarkConfig] = None):
        """
        Initialize the benchmark runner.

        Args:
            config: Benchmark configuration (uses defaults if not provided)
        """
        self.config = config or BenchmarkConfig()
        self._results_history: List[BenchmarkResult] = []

    def run_sync(
        self,
        name: str,
        func: Callable[..., T],
        *args: Any,
        config: Optional[BenchmarkConfig] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> BenchmarkResult:
        """
        Run benchmark for a synchronous function.

        Args:
            name: Benchmark name
            func: Function to benchmark
            *args: Positional arguments for the function
            config: Optional config override
            metadata: Optional metadata to include in result
            **kwargs: Keyword arguments for the function

        Returns:
            BenchmarkResult with timing statistics
        """
        cfg = config or self.config
        result_id = uuid4()
        start_time = datetime.utcnow()
        timings: List[float] = []
        error_msg: Optional[str] = None
        success = True

        try:
            # Warm-up phase
            for _ in range(cfg.warmup_iterations):
                try:
                    func(*args, **kwargs)
                except Exception:
                    pass
                if cfg.gc_collect:
                    gc.collect()

            # Benchmark phase
            for _ in range(cfg.iterations):
                if cfg.gc_collect:
                    gc.collect()

                start = time.perf_counter()
                try:
                    func(*args, **kwargs)
                except Exception as e:
                    error_msg = str(e)
                    success = False
                    break
                end = time.perf_counter()

                timing_ms = (end - start) * 1000
                timings.append(timing_ms)

                if cfg.cooldown_seconds > 0:
                    time.sleep(cfg.cooldown_seconds)

        except Exception as e:
            error_msg = str(e)
            success = False

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        result = BenchmarkResult(
            id=result_id,
            name=name,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            iterations=len(timings),
            timings_ms=timings,
            success=success,
            error=error_msg,
            metadata=metadata or {}
        )

        self._results_history.append(result)
        return result

    async def run_async(
        self,
        name: str,
        func: Callable[..., Coroutine[Any, Any, T]],
        *args: Any,
        config: Optional[BenchmarkConfig] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> BenchmarkResult:
        """
        Run benchmark for an asynchronous function.

        Args:
            name: Benchmark name
            func: Async function to benchmark
            *args: Positional arguments for the function
            config: Optional config override
            metadata: Optional metadata to include in result
            **kwargs: Keyword arguments for the function

        Returns:
            BenchmarkResult with timing statistics
        """
        cfg = config or self.config
        result_id = uuid4()
        start_time = datetime.utcnow()
        timings: List[float] = []
        error_msg: Optional[str] = None
        success = True

        try:
            # Warm-up phase
            for _ in range(cfg.warmup_iterations):
                try:
                    await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=cfg.timeout_seconds
                    )
                except Exception:
                    pass
                if cfg.gc_collect:
                    gc.collect()

            # Benchmark phase
            if cfg.parallel:
                # Parallel execution for async benchmarks
                timings = await self._run_parallel_async(
                    func, args, kwargs, cfg
                )
                success = len(timings) == cfg.iterations
            else:
                # Sequential execution
                for _ in range(cfg.iterations):
                    if cfg.gc_collect:
                        gc.collect()

                    start = time.perf_counter()
                    try:
                        await asyncio.wait_for(
                            func(*args, **kwargs),
                            timeout=cfg.timeout_seconds
                        )
                    except asyncio.TimeoutError:
                        error_msg = f"Timeout after {cfg.timeout_seconds}s"
                        success = False
                        break
                    except Exception as e:
                        error_msg = str(e)
                        success = False
                        break
                    end = time.perf_counter()

                    timing_ms = (end - start) * 1000
                    timings.append(timing_ms)

                    if cfg.cooldown_seconds > 0:
                        await asyncio.sleep(cfg.cooldown_seconds)

        except Exception as e:
            error_msg = str(e)
            success = False

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        result = BenchmarkResult(
            id=result_id,
            name=name,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            iterations=len(timings),
            timings_ms=timings,
            success=success,
            error=error_msg,
            metadata=metadata or {}
        )

        self._results_history.append(result)
        return result

    async def _run_parallel_async(
        self,
        func: Callable[..., Coroutine[Any, Any, T]],
        args: tuple,
        kwargs: dict,
        config: BenchmarkConfig
    ) -> List[float]:
        """Run async benchmarks in parallel batches."""
        timings: List[float] = []
        semaphore = asyncio.Semaphore(config.max_concurrent)

        async def timed_execution() -> float:
            async with semaphore:
                start = time.perf_counter()
                await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=config.timeout_seconds
                )
                end = time.perf_counter()
                return (end - start) * 1000

        tasks = [timed_execution() for _ in range(config.iterations)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, float):
                timings.append(result)

        return timings

    async def run_suite(
        self,
        name: str,
        benchmarks: List[tuple],
        description: str = "",
        config: Optional[BenchmarkConfig] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> BenchmarkReport:
        """
        Run a suite of benchmarks.

        Args:
            name: Suite name
            benchmarks: List of (name, func, args) tuples
            description: Suite description
            config: Optional config override for all benchmarks
            metadata: Optional metadata for the report

        Returns:
            BenchmarkReport with all results
        """
        cfg = config or self.config
        report_id = uuid4()
        results: List[BenchmarkResult] = []

        for benchmark in benchmarks:
            bench_name = benchmark[0]
            func = benchmark[1]
            args = benchmark[2] if len(benchmark) > 2 else ()
            kwargs = benchmark[3] if len(benchmark) > 3 else {}

            if asyncio.iscoroutinefunction(func):
                result = await self.run_async(
                    bench_name, func, *args, config=cfg, **kwargs
                )
            else:
                result = self.run_sync(
                    bench_name, func, *args, config=cfg, **kwargs
                )

            results.append(result)

        return BenchmarkReport(
            id=report_id,
            name=name,
            description=description,
            created_at=datetime.utcnow(),
            results=results,
            metadata=metadata or {}
        )

    def compare(
        self,
        baseline: BenchmarkResult,
        current: BenchmarkResult,
        threshold_percent: float = 5.0
    ) -> BenchmarkComparison:
        """
        Compare two benchmark results.

        Args:
            baseline: Baseline benchmark result
            current: Current benchmark result
            threshold_percent: Threshold for significant difference

        Returns:
            BenchmarkComparison with analysis
        """
        def calc_diff_percent(baseline_val: float, current_val: float) -> float:
            if baseline_val == 0:
                return 0.0
            return ((current_val - baseline_val) / baseline_val) * 100

        mean_diff = calc_diff_percent(baseline.mean_ms, current.mean_ms)
        median_diff = calc_diff_percent(baseline.median_ms, current.median_ms)
        p95_diff = calc_diff_percent(baseline.p95_ms, current.p95_ms)

        # Determine result based on mean difference
        if abs(mean_diff) <= threshold_percent:
            result = ComparisonResult.SIMILAR
        elif mean_diff < -threshold_percent:
            result = ComparisonResult.IMPROVEMENT
        elif mean_diff > threshold_percent:
            result = ComparisonResult.REGRESSION
        elif mean_diff < 0:
            result = ComparisonResult.FASTER
        else:
            result = ComparisonResult.SLOWER

        return BenchmarkComparison(
            baseline=baseline,
            current=current,
            mean_diff_percent=mean_diff,
            median_diff_percent=median_diff,
            p95_diff_percent=p95_diff,
            result=result,
            threshold_percent=threshold_percent
        )

    def get_history(
        self,
        name: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[BenchmarkResult]:
        """
        Get benchmark history.

        Args:
            name: Filter by benchmark name
            limit: Maximum results to return

        Returns:
            List of BenchmarkResults
        """
        results = self._results_history

        if name:
            results = [r for r in results if r.name == name]

        if limit:
            results = results[-limit:]

        return results

    def clear_history(self) -> None:
        """Clear benchmark history."""
        self._results_history.clear()

    def detect_regressions(
        self,
        current_results: List[BenchmarkResult],
        baseline_results: Optional[List[BenchmarkResult]] = None,
        threshold_percent: float = 10.0
    ) -> List[BenchmarkComparison]:
        """
        Detect performance regressions in benchmark results.

        Args:
            current_results: Current benchmark results
            baseline_results: Baseline results (uses history if not provided)
            threshold_percent: Threshold for regression detection

        Returns:
            List of comparisons showing regressions
        """
        regressions: List[BenchmarkComparison] = []

        if baseline_results is None:
            # Use historical results as baseline
            baseline_map = {}
            for result in self._results_history:
                if result.name not in baseline_map:
                    baseline_map[result.name] = result
        else:
            baseline_map = {r.name: r for r in baseline_results}

        for current in current_results:
            if current.name in baseline_map:
                baseline = baseline_map[current.name]
                comparison = self.compare(baseline, current, threshold_percent)
                if comparison.result == ComparisonResult.REGRESSION:
                    regressions.append(comparison)

        return regressions


def benchmark(
    name: Optional[str] = None,
    iterations: int = 100,
    warmup: int = 10
) -> Callable:
    """
    Decorator for benchmarking functions.

    Args:
        name: Benchmark name (uses function name if not provided)
        iterations: Number of iterations
        warmup: Number of warm-up iterations

    Returns:
        Decorated function that runs benchmark when called

    Usage:
        @benchmark(iterations=50)
        def my_function():
            # Function code
            pass

        result = my_function()  # Returns BenchmarkResult
    """
    def decorator(func: Callable) -> Callable:
        benchmark_name = name or func.__name__
        config = BenchmarkConfig(iterations=iterations, warmup_iterations=warmup)
        runner = BenchmarkRunner(config)

        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args: Any, **kwargs: Any) -> BenchmarkResult:
                return await runner.run_async(benchmark_name, func, *args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args: Any, **kwargs: Any) -> BenchmarkResult:
                return runner.run_sync(benchmark_name, func, *args, **kwargs)
            return sync_wrapper

    return decorator

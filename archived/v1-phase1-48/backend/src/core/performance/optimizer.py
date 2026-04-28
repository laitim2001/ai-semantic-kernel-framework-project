# =============================================================================
# IPA Platform - Performance Optimizer
# =============================================================================
# Sprint 12: S12-2 Performance Optimizer
#
# Provides automated performance optimization through:
# - Performance analysis
# - Strategy-based optimization
# - Benchmark comparison
# - Improvement tracking
#
# Optimization Strategies:
# - Caching: Add caching for repeated operations
# - Batching: Batch multiple operations together
# - Connection Pooling: Optimize database connections
# - Query Optimization: Optimize database queries
# =============================================================================

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable, Awaitable
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum
import asyncio
import time
import statistics
import logging

from src.core.performance.profiler import (
    PerformanceProfiler,
    MetricType,
    OptimizationRecommendation,
)

logger = logging.getLogger(__name__)


class OptimizationStrategy(str, Enum):
    """
    優化策略類型

    Attributes:
        CACHING: 快取策略 - 緩存重複操作結果
        BATCHING: 批次策略 - 批量處理多個操作
        CONNECTION_POOLING: 連接池策略 - 優化資料庫連接
        QUERY_OPTIMIZATION: 查詢優化策略 - 優化資料庫查詢
        ASYNC_PROCESSING: 異步處理策略 - 使用異步處理
        LAZY_LOADING: 延遲載入策略 - 延遲載入非必要數據
    """
    CACHING = "caching"
    BATCHING = "batching"
    CONNECTION_POOLING = "connection_pooling"
    QUERY_OPTIMIZATION = "query_optimization"
    ASYNC_PROCESSING = "async_processing"
    LAZY_LOADING = "lazy_loading"


@dataclass
class BenchmarkMetrics:
    """
    基準測試指標

    Attributes:
        avg_latency_ms: 平均延遲（毫秒）
        p95_latency_ms: P95 延遲（毫秒）
        p99_latency_ms: P99 延遲（毫秒）
        throughput_rps: 吞吐量（請求/秒）
        error_rate: 錯誤率
        total_requests: 總請求數
        successful_requests: 成功請求數
    """
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    throughput_rps: float
    error_rate: float
    total_requests: int
    successful_requests: int

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "avg_latency_ms": self.avg_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "throughput_rps": self.throughput_rps,
            "error_rate": self.error_rate,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
        }


@dataclass
class OptimizationResult:
    """
    優化結果

    Attributes:
        id: 優化結果 ID
        target: 優化目標
        started_at: 開始時間
        completed_at: 完成時間
        baseline: 優化前基準指標
        optimized: 優化後指標
        improvement: 改進幅度
        applied_strategies: 應用的優化策略
        recommendations: 優化建議
        success: 是否成功
        error: 錯誤信息（如有）
    """
    id: UUID
    target: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    baseline: Optional[BenchmarkMetrics] = None
    optimized: Optional[BenchmarkMetrics] = None
    improvement: Optional[Dict[str, float]] = None
    applied_strategies: List[OptimizationStrategy] = field(default_factory=list)
    recommendations: List[OptimizationRecommendation] = field(default_factory=list)
    success: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "id": str(self.id),
            "target": self.target,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "baseline": self.baseline.to_dict() if self.baseline else None,
            "optimized": self.optimized.to_dict() if self.optimized else None,
            "improvement": self.improvement,
            "applied_strategies": [s.value for s in self.applied_strategies],
            "recommendations": [r.to_dict() for r in self.recommendations],
            "success": self.success,
            "error": self.error,
        }


class PerformanceOptimizer:
    """
    效能優化器

    提供自動化的效能優化功能：
    - 分析當前效能
    - 識別瓶頸
    - 應用優化策略
    - 驗證改進效果

    Example:
        >>> optimizer = PerformanceOptimizer(profiler)
        >>> result = await optimizer.analyze_and_optimize("api_endpoint")
        >>> print(f"Improvement: {result.improvement['latency_improvement']:.1f}%")
    """

    # 建議類型到策略的映射
    RECOMMENDATION_TO_STRATEGY = {
        "latency": OptimizationStrategy.CACHING,
        "latency_variance": OptimizationStrategy.QUERY_OPTIMIZATION,
        "error_rate": OptimizationStrategy.ASYNC_PROCESSING,
        "concurrency": OptimizationStrategy.CONNECTION_POOLING,
        "memory": OptimizationStrategy.LAZY_LOADING,
        "cpu": OptimizationStrategy.BATCHING,
    }

    def __init__(
        self,
        profiler: PerformanceProfiler,
        cache_service: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化效能優化器

        Args:
            profiler: 效能分析器實例
            cache_service: 快取服務（可選）
            config: 配置選項
        """
        self.profiler = profiler
        self.cache = cache_service
        self.config = config or {}

        # 優化策略處理器
        self._strategy_handlers: Dict[
            OptimizationStrategy,
            Callable[[str], Awaitable[None]]
        ] = {
            OptimizationStrategy.CACHING: self._apply_caching,
            OptimizationStrategy.BATCHING: self._apply_batching,
            OptimizationStrategy.CONNECTION_POOLING: self._apply_connection_pooling,
            OptimizationStrategy.QUERY_OPTIMIZATION: self._apply_query_optimization,
            OptimizationStrategy.ASYNC_PROCESSING: self._apply_async_processing,
            OptimizationStrategy.LAZY_LOADING: self._apply_lazy_loading,
        }

        # 優化結果歷史
        self._results: Dict[UUID, OptimizationResult] = {}

    async def analyze_and_optimize(
        self,
        target: str,
        benchmark_requests: int = 100,
        strategies: Optional[List[OptimizationStrategy]] = None,
        dry_run: bool = False
    ) -> OptimizationResult:
        """
        分析並優化目標

        執行完整的優化流程：
        1. 收集基準效能數據
        2. 獲取優化建議
        3. 應用優化策略
        4. 重新測試並比較

        Args:
            target: 優化目標（如 API 端點名稱）
            benchmark_requests: 基準測試請求數
            strategies: 要應用的策略（如果為 None，則自動選擇）
            dry_run: 是否只分析不實際應用優化

        Returns:
            OptimizationResult 包含完整的優化結果
        """
        result = OptimizationResult(
            id=uuid4(),
            target=target,
            started_at=datetime.utcnow()
        )

        try:
            # 1. 開始分析會話
            session = self.profiler.start_session(f"optimization_{target}")

            # 2. 執行基準測試
            logger.info(f"Running baseline benchmark for {target}...")
            baseline = await self._run_benchmark(target, benchmark_requests)
            result.baseline = baseline

            # 3. 獲取優化建議
            recommendations = self.profiler.get_recommendations()
            result.recommendations = recommendations

            if not dry_run:
                # 4. 確定要應用的策略
                if strategies is None:
                    strategies = self._select_strategies(recommendations)

                # 5. 應用優化策略
                applied_strategies = []
                for strategy in strategies:
                    try:
                        logger.info(f"Applying strategy: {strategy.value}")
                        handler = self._strategy_handlers.get(strategy)
                        if handler:
                            await handler(target)
                            applied_strategies.append(strategy)
                    except Exception as e:
                        logger.error(f"Failed to apply {strategy.value}: {e}")

                result.applied_strategies = applied_strategies

                # 6. 重新測試
                if applied_strategies:
                    logger.info("Running post-optimization benchmark...")
                    optimized = await self._run_benchmark(target, benchmark_requests)
                    result.optimized = optimized

                    # 7. 計算改進幅度
                    result.improvement = self._calculate_improvement(
                        baseline, optimized
                    )

            # 結束會話
            self.profiler.end_session(session.id)

            result.completed_at = datetime.utcnow()
            result.success = True

        except Exception as e:
            logger.error(f"Optimization failed for {target}: {e}")
            result.error = str(e)
            result.completed_at = datetime.utcnow()

        # 保存結果
        self._results[result.id] = result

        return result

    async def _run_benchmark(
        self,
        target: str,
        num_requests: int = 100
    ) -> BenchmarkMetrics:
        """
        執行基準測試

        Args:
            target: 測試目標
            num_requests: 請求數量

        Returns:
            BenchmarkMetrics 測試結果
        """
        latencies: List[float] = []
        errors = 0
        start_time = time.perf_counter()

        for i in range(num_requests):
            request_start = time.perf_counter()
            try:
                # 模擬請求（實際使用時應該調用真實的服務）
                await self._simulate_request(target)
                latency = (time.perf_counter() - request_start) * 1000
                latencies.append(latency)

                # 記錄到 profiler
                self.profiler.record_metric(
                    f"benchmark_{target}",
                    MetricType.LATENCY,
                    latency,
                    "ms"
                )
            except Exception as e:
                errors += 1
                logger.debug(f"Benchmark request {i} failed: {e}")

        total_time = time.perf_counter() - start_time

        # 計算統計
        if latencies:
            avg_latency = statistics.mean(latencies)
            sorted_latencies = sorted(latencies)
            p95_idx = int(len(sorted_latencies) * 0.95)
            p99_idx = int(len(sorted_latencies) * 0.99)
            p95_latency = sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)]
            p99_latency = sorted_latencies[min(p99_idx, len(sorted_latencies) - 1)]
        else:
            avg_latency = p95_latency = p99_latency = 0

        return BenchmarkMetrics(
            avg_latency_ms=avg_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            throughput_rps=num_requests / total_time if total_time > 0 else 0,
            error_rate=errors / num_requests if num_requests > 0 else 0,
            total_requests=num_requests,
            successful_requests=num_requests - errors,
        )

    async def _simulate_request(self, target: str) -> None:
        """模擬請求（用於基準測試）"""
        # 模擬變化的延遲
        import random
        base_delay = self.config.get("base_delay", 0.01)
        variance = self.config.get("delay_variance", 0.005)
        delay = base_delay + random.uniform(-variance, variance)
        await asyncio.sleep(max(0, delay))

    def _select_strategies(
        self,
        recommendations: List[OptimizationRecommendation]
    ) -> List[OptimizationStrategy]:
        """
        根據建議選擇優化策略

        Args:
            recommendations: 優化建議列表

        Returns:
            要應用的策略列表
        """
        strategies = set()

        for rec in recommendations:
            strategy = self.RECOMMENDATION_TO_STRATEGY.get(rec.type)
            if strategy:
                strategies.add(strategy)

        return list(strategies)

    def _calculate_improvement(
        self,
        baseline: BenchmarkMetrics,
        optimized: BenchmarkMetrics
    ) -> Dict[str, float]:
        """
        計算改進幅度

        Args:
            baseline: 優化前指標
            optimized: 優化後指標

        Returns:
            改進百分比字典
        """
        def safe_improvement(before: float, after: float, lower_is_better: bool = True) -> float:
            if before == 0:
                return 0
            if lower_is_better:
                return (before - after) / before * 100
            else:
                return (after - before) / before * 100

        return {
            "latency_improvement": safe_improvement(
                baseline.avg_latency_ms,
                optimized.avg_latency_ms,
                lower_is_better=True
            ),
            "p95_latency_improvement": safe_improvement(
                baseline.p95_latency_ms,
                optimized.p95_latency_ms,
                lower_is_better=True
            ),
            "throughput_improvement": safe_improvement(
                baseline.throughput_rps,
                optimized.throughput_rps,
                lower_is_better=False
            ),
            "error_rate_improvement": safe_improvement(
                baseline.error_rate,
                optimized.error_rate,
                lower_is_better=True
            ),
        }

    # =========================================================================
    # Optimization Strategy Handlers
    # =========================================================================

    async def _apply_caching(self, target: str) -> None:
        """
        應用快取策略

        為目標啟用快取以減少重複計算。
        """
        logger.info(f"Applying caching strategy for {target}")

        if self.cache:
            # 配置快取
            cache_config = {
                "ttl": self.config.get("cache_ttl", 300),
                "max_size": self.config.get("cache_max_size", 1000),
            }
            # 實際快取邏輯會在這裡實現
            logger.info(f"Cache configured: {cache_config}")
        else:
            logger.warning("No cache service available, skipping caching strategy")

    async def _apply_batching(self, target: str) -> None:
        """
        應用批次處理策略

        將多個小操作合併為批次操作。
        """
        logger.info(f"Applying batching strategy for {target}")

        batch_config = {
            "batch_size": self.config.get("batch_size", 50),
            "batch_timeout_ms": self.config.get("batch_timeout_ms", 100),
        }
        logger.info(f"Batching configured: {batch_config}")

    async def _apply_connection_pooling(self, target: str) -> None:
        """
        應用連接池策略

        優化資料庫連接管理。
        """
        logger.info(f"Applying connection pooling strategy for {target}")

        pool_config = {
            "min_connections": self.config.get("pool_min", 5),
            "max_connections": self.config.get("pool_max", 20),
            "connection_timeout": self.config.get("pool_timeout", 30),
        }
        logger.info(f"Connection pool configured: {pool_config}")

    async def _apply_query_optimization(self, target: str) -> None:
        """
        應用查詢優化策略

        優化資料庫查詢效能。
        """
        logger.info(f"Applying query optimization strategy for {target}")

        optimization_config = {
            "enable_query_cache": True,
            "use_prepared_statements": True,
            "analyze_slow_queries": True,
        }
        logger.info(f"Query optimization configured: {optimization_config}")

    async def _apply_async_processing(self, target: str) -> None:
        """
        應用異步處理策略

        將同步操作轉換為異步處理。
        """
        logger.info(f"Applying async processing strategy for {target}")

        async_config = {
            "use_background_tasks": True,
            "task_queue": self.config.get("task_queue", "default"),
        }
        logger.info(f"Async processing configured: {async_config}")

    async def _apply_lazy_loading(self, target: str) -> None:
        """
        應用延遲載入策略

        延遲載入非必要數據以減少初始載入時間。
        """
        logger.info(f"Applying lazy loading strategy for {target}")

        lazy_config = {
            "enable_pagination": True,
            "default_page_size": self.config.get("page_size", 50),
            "defer_expensive_computations": True,
        }
        logger.info(f"Lazy loading configured: {lazy_config}")

    # =========================================================================
    # Result Management
    # =========================================================================

    def get_result(self, result_id: UUID) -> Optional[OptimizationResult]:
        """獲取優化結果"""
        return self._results.get(result_id)

    def get_all_results(self) -> List[OptimizationResult]:
        """獲取所有優化結果"""
        return list(self._results.values())

    def get_results_for_target(self, target: str) -> List[OptimizationResult]:
        """獲取特定目標的所有優化結果"""
        return [r for r in self._results.values() if r.target == target]

    def clear_results(self) -> None:
        """清除所有優化結果"""
        self._results.clear()
        logger.info("Cleared all optimization results")

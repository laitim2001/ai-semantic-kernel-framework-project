# =============================================================================
# IPA Platform - Performance Profiler
# =============================================================================
# Sprint 12: S12-1 Performance Profiler
#
# Provides session-based performance profiling with:
# - Latency tracking
# - Throughput measurement
# - Resource usage monitoring
# - Bottleneck identification
# - Optimization recommendations
#
# Usage:
#   profiler = PerformanceProfiler()
#   session = profiler.start_session("my_analysis")
#   profiler.record_metric("api_call", MetricType.LATENCY, 150.5, "ms")
#   profiler.end_session()
#   recommendations = profiler.get_recommendations()
# =============================================================================

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum
import asyncio
import time
import functools
import statistics
import logging

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """
    效能指標類型

    Attributes:
        LATENCY: 延遲測量 (毫秒)
        THROUGHPUT: 吞吐量 (請求/秒)
        MEMORY: 記憶體使用 (MB)
        CPU: CPU 使用率 (%)
        CONCURRENCY: 並發數
        ERROR_RATE: 錯誤率 (0-1)
    """
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    MEMORY = "memory"
    CPU = "cpu"
    CONCURRENCY = "concurrency"
    ERROR_RATE = "error_rate"


@dataclass
class PerformanceMetric:
    """
    效能指標數據

    Attributes:
        name: 指標名稱 (e.g., "api_call", "db_query")
        metric_type: 指標類型
        value: 指標值
        unit: 單位 (e.g., "ms", "MB", "%")
        timestamp: 記錄時間
        tags: 額外標籤 (用於分類和過濾)
    """
    name: str
    metric_type: MetricType
    value: float
    unit: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "name": self.name,
            "metric_type": self.metric_type.value,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
        }


@dataclass
class ProfileSession:
    """
    分析會話

    追蹤一個完整的效能分析週期，包含所有收集的指標和最終摘要。

    Attributes:
        id: 會話 ID
        name: 會話名稱
        started_at: 開始時間
        ended_at: 結束時間
        metrics: 收集的指標列表
        summary: 會話摘要 (結束後生成)
        metadata: 額外元數據
    """
    id: UUID
    name: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    metrics: List[PerformanceMetric] = field(default_factory=list)
    summary: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> Optional[float]:
        """獲取會話持續時間（秒）"""
        if self.ended_at:
            return (self.ended_at - self.started_at).total_seconds()
        return None

    @property
    def is_active(self) -> bool:
        """檢查會話是否仍在進行中"""
        return self.ended_at is None

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "id": str(self.id),
            "name": self.name,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration_seconds": self.duration_seconds,
            "metrics_count": len(self.metrics),
            "summary": self.summary,
            "metadata": self.metadata,
        }


@dataclass
class RecommendationSeverity(str, Enum):
    """建議嚴重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class OptimizationRecommendation:
    """
    優化建議

    Attributes:
        type: 建議類型 (e.g., "latency", "memory", "concurrency")
        severity: 嚴重程度
        message: 問題描述
        recommendation: 建議的解決方案
        metric_value: 相關指標值
        threshold: 觸發閾值
    """
    type: str
    severity: str
    message: str
    recommendation: str
    metric_value: Optional[float] = None
    threshold: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "type": self.type,
            "severity": self.severity,
            "message": self.message,
            "recommendation": self.recommendation,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
        }


class PerformanceProfiler:
    """
    效能分析器

    提供完整的效能分析功能：
    - 延遲追蹤
    - 吞吐量測量
    - 資源使用監控
    - 瓶頸識別
    - 優化建議生成

    Example:
        >>> profiler = PerformanceProfiler()
        >>> session = profiler.start_session("api_analysis")
        >>>
        >>> @profiler.measure_latency("database_query")
        >>> async def fetch_data():
        ...     return await db.query(...)
        >>>
        >>> await fetch_data()
        >>> profiler.end_session()
        >>>
        >>> recommendations = profiler.get_recommendations()
    """

    # 預設閾值配置
    DEFAULT_THRESHOLDS = {
        "latency_avg_ms": 1000,          # 平均延遲閾值 (ms)
        "latency_p99_multiplier": 3,      # P99 vs 平均值的倍數閾值
        "error_rate": 0.05,               # 錯誤率閾值 (5%)
        "concurrency_max": 100,           # 最大並發數閾值
        "memory_usage_mb": 1024,          # 記憶體使用閾值 (MB)
        "cpu_usage_percent": 80,          # CPU 使用率閾值 (%)
    }

    def __init__(
        self,
        thresholds: Optional[Dict[str, float]] = None,
        auto_collect_system_metrics: bool = False
    ):
        """
        初始化效能分析器

        Args:
            thresholds: 自定義閾值配置
            auto_collect_system_metrics: 是否自動收集系統指標
        """
        self._sessions: Dict[UUID, ProfileSession] = {}
        self._active_session: Optional[ProfileSession] = None
        self._metric_collectors: Dict[MetricType, List[float]] = {
            mt: [] for mt in MetricType
        }
        self._thresholds = {**self.DEFAULT_THRESHOLDS, **(thresholds or {})}
        self._auto_collect = auto_collect_system_metrics
        self._collection_task: Optional[asyncio.Task] = None

    def start_session(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProfileSession:
        """
        開始分析會話

        Args:
            name: 會話名稱
            metadata: 額外元數據

        Returns:
            新建立的 ProfileSession
        """
        session = ProfileSession(
            id=uuid4(),
            name=name,
            started_at=datetime.utcnow(),
            metadata=metadata or {}
        )
        self._sessions[session.id] = session
        self._active_session = session

        logger.info(f"Started profiling session: {session.id} ({name})")

        # 如果啟用自動收集，開始背景收集任務
        if self._auto_collect:
            self._start_auto_collection()

        return session

    def end_session(
        self,
        session_id: Optional[UUID] = None
    ) -> ProfileSession:
        """
        結束分析會話

        Args:
            session_id: 要結束的會話 ID（如果為 None，結束當前活躍會話）

        Returns:
            結束的 ProfileSession（包含摘要）

        Raises:
            ValueError: 如果沒有找到指定的會話
        """
        target_id = session_id or (
            self._active_session.id if self._active_session else None
        )

        if not target_id:
            raise ValueError("No active session to end")

        session = self._sessions.get(target_id)
        if not session:
            raise ValueError(f"Session not found: {target_id}")

        session.ended_at = datetime.utcnow()
        session.summary = self._generate_summary(session)

        if session == self._active_session:
            self._active_session = None

        # 停止自動收集
        if self._collection_task:
            self._collection_task.cancel()
            self._collection_task = None

        logger.info(
            f"Ended profiling session: {session.id} "
            f"(duration: {session.duration_seconds:.2f}s)"
        )

        return session

    def record_metric(
        self,
        name: str,
        metric_type: MetricType,
        value: float,
        unit: str = "",
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """
        記錄效能指標

        Args:
            name: 指標名稱
            metric_type: 指標類型
            value: 指標值
            unit: 單位
            tags: 額外標籤
        """
        metric = PerformanceMetric(
            name=name,
            metric_type=metric_type,
            value=value,
            unit=unit,
            tags=tags or {}
        )

        # 添加到當前會話
        if self._active_session:
            self._active_session.metrics.append(metric)

        # 添加到全局收集器（用於跨會話分析）
        self._metric_collectors[metric_type].append(value)

        logger.debug(
            f"Recorded metric: {name} = {value}{unit} ({metric_type.value})"
        )

    def measure_latency(
        self,
        operation_name: str,
        tags: Optional[Dict[str, str]] = None
    ):
        """
        延遲測量裝飾器

        自動測量被裝飾函數的執行時間並記錄為 LATENCY 指標。
        支援同步和異步函數。

        Args:
            operation_name: 操作名稱
            tags: 額外標籤

        Returns:
            裝飾器函數

        Example:
            >>> @profiler.measure_latency("database_query")
            >>> async def fetch_user(user_id: str):
            ...     return await db.get_user(user_id)
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start = time.perf_counter()
                try:
                    return await func(*args, **kwargs)
                finally:
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    self.record_metric(
                        name=operation_name,
                        metric_type=MetricType.LATENCY,
                        value=elapsed_ms,
                        unit="ms",
                        tags=tags
                    )

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                start = time.perf_counter()
                try:
                    return func(*args, **kwargs)
                finally:
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    self.record_metric(
                        name=operation_name,
                        metric_type=MetricType.LATENCY,
                        value=elapsed_ms,
                        unit="ms",
                        tags=tags
                    )

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper

        return decorator

    def measure_throughput(
        self,
        operation_name: str,
        window_seconds: float = 1.0
    ):
        """
        吞吐量測量裝飾器

        測量操作的吞吐量（每秒處理數量）。

        Args:
            operation_name: 操作名稱
            window_seconds: 計算窗口（秒）
        """
        call_times: List[float] = []

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                current_time = time.time()
                call_times.append(current_time)

                # 清理過期的調用記錄
                cutoff = current_time - window_seconds
                while call_times and call_times[0] < cutoff:
                    call_times.pop(0)

                # 計算吞吐量
                throughput = len(call_times) / window_seconds
                self.record_metric(
                    name=operation_name,
                    metric_type=MetricType.THROUGHPUT,
                    value=throughput,
                    unit="req/s"
                )

                return await func(*args, **kwargs)

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                current_time = time.time()
                call_times.append(current_time)

                cutoff = current_time - window_seconds
                while call_times and call_times[0] < cutoff:
                    call_times.pop(0)

                throughput = len(call_times) / window_seconds
                self.record_metric(
                    name=operation_name,
                    metric_type=MetricType.THROUGHPUT,
                    value=throughput,
                    unit="req/s"
                )

                return func(*args, **kwargs)

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper

        return decorator

    def _generate_summary(
        self,
        session: ProfileSession
    ) -> Dict[str, Any]:
        """
        生成會話摘要

        計算各類指標的統計信息，包括：
        - 計數
        - 最小/最大值
        - 平均值
        - 中位數
        - P95/P99 百分位數

        Args:
            session: 要生成摘要的會話

        Returns:
            摘要字典
        """
        summary: Dict[str, Any] = {
            "duration_seconds": session.duration_seconds,
            "total_metrics": len(session.metrics),
            "metrics_by_type": {},
            "metrics_by_name": {},
        }

        # 按類型分組計算統計
        for metric_type in MetricType:
            values = [
                m.value for m in session.metrics
                if m.metric_type == metric_type
            ]

            if values:
                summary["metrics_by_type"][metric_type.value] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": statistics.mean(values),
                    "median": statistics.median(values),
                    "stdev": statistics.stdev(values) if len(values) > 1 else 0,
                    "p95": self._percentile(values, 95),
                    "p99": self._percentile(values, 99),
                }

        # 按名稱分組計算統計
        names = set(m.name for m in session.metrics)
        for name in names:
            values = [m.value for m in session.metrics if m.name == name]
            if values:
                summary["metrics_by_name"][name] = {
                    "count": len(values),
                    "avg": statistics.mean(values),
                    "p95": self._percentile(values, 95),
                    "p99": self._percentile(values, 99),
                }

        return summary

    def _percentile(self, values: List[float], p: int) -> float:
        """
        計算百分位數

        Args:
            values: 數值列表
            p: 百分位 (0-100)

        Returns:
            百分位數值
        """
        if not values:
            return 0.0
        sorted_values = sorted(values)
        idx = int(len(sorted_values) * p / 100)
        return sorted_values[min(idx, len(sorted_values) - 1)]

    def get_recommendations(self) -> List[OptimizationRecommendation]:
        """
        獲取優化建議

        基於收集的指標分析效能問題並生成優化建議。

        Returns:
            優化建議列表
        """
        recommendations: List[OptimizationRecommendation] = []

        # 分析延遲
        latency_values = self._metric_collectors[MetricType.LATENCY]
        if latency_values:
            avg_latency = statistics.mean(latency_values)
            p99_latency = self._percentile(latency_values, 99)

            if avg_latency > self._thresholds["latency_avg_ms"]:
                recommendations.append(OptimizationRecommendation(
                    type="latency",
                    severity="high",
                    message=f"平均延遲 {avg_latency:.0f}ms 超過閾值 "
                            f"{self._thresholds['latency_avg_ms']}ms",
                    recommendation="考慮添加快取、優化資料庫查詢或使用異步處理",
                    metric_value=avg_latency,
                    threshold=self._thresholds["latency_avg_ms"],
                ))

            if p99_latency > avg_latency * self._thresholds["latency_p99_multiplier"]:
                recommendations.append(OptimizationRecommendation(
                    type="latency_variance",
                    severity="medium",
                    message=f"P99 延遲 ({p99_latency:.0f}ms) 遠高於平均值 "
                            f"({avg_latency:.0f}ms)",
                    recommendation="調查長尾請求原因，可能存在偶發性瓶頸",
                    metric_value=p99_latency,
                    threshold=avg_latency * self._thresholds["latency_p99_multiplier"],
                ))

        # 分析錯誤率
        error_values = self._metric_collectors[MetricType.ERROR_RATE]
        if error_values:
            avg_error_rate = statistics.mean(error_values)
            if avg_error_rate > self._thresholds["error_rate"]:
                recommendations.append(OptimizationRecommendation(
                    type="error_rate",
                    severity="critical",
                    message=f"錯誤率 {avg_error_rate:.1%} 超過閾值 "
                            f"{self._thresholds['error_rate']:.1%}",
                    recommendation="檢查錯誤日誌，修復根本原因，增加錯誤處理",
                    metric_value=avg_error_rate,
                    threshold=self._thresholds["error_rate"],
                ))

        # 分析並發
        concurrency_values = self._metric_collectors[MetricType.CONCURRENCY]
        if concurrency_values:
            max_concurrency = max(concurrency_values)
            if max_concurrency > self._thresholds["concurrency_max"]:
                recommendations.append(OptimizationRecommendation(
                    type="concurrency",
                    severity="medium",
                    message=f"最大並發數 {max_concurrency} 超過閾值 "
                            f"{self._thresholds['concurrency_max']}",
                    recommendation="考慮實施請求限流或增加資源",
                    metric_value=max_concurrency,
                    threshold=self._thresholds["concurrency_max"],
                ))

        # 分析記憶體
        memory_values = self._metric_collectors[MetricType.MEMORY]
        if memory_values:
            max_memory = max(memory_values)
            if max_memory > self._thresholds["memory_usage_mb"]:
                recommendations.append(OptimizationRecommendation(
                    type="memory",
                    severity="high",
                    message=f"記憶體使用 {max_memory:.0f}MB 超過閾值 "
                            f"{self._thresholds['memory_usage_mb']}MB",
                    recommendation="檢查記憶體洩漏，優化物件生命週期，使用分頁處理",
                    metric_value=max_memory,
                    threshold=self._thresholds["memory_usage_mb"],
                ))

        # 分析 CPU
        cpu_values = self._metric_collectors[MetricType.CPU]
        if cpu_values:
            avg_cpu = statistics.mean(cpu_values)
            if avg_cpu > self._thresholds["cpu_usage_percent"]:
                recommendations.append(OptimizationRecommendation(
                    type="cpu",
                    severity="high",
                    message=f"平均 CPU 使用率 {avg_cpu:.1f}% 超過閾值 "
                            f"{self._thresholds['cpu_usage_percent']}%",
                    recommendation="優化計算密集型操作，考慮使用並行處理或卸載到背景任務",
                    metric_value=avg_cpu,
                    threshold=self._thresholds["cpu_usage_percent"],
                ))

        return recommendations

    def get_session(self, session_id: UUID) -> Optional[ProfileSession]:
        """獲取指定會話"""
        return self._sessions.get(session_id)

    def get_all_sessions(self) -> List[ProfileSession]:
        """獲取所有會話"""
        return list(self._sessions.values())

    def get_active_session(self) -> Optional[ProfileSession]:
        """獲取當前活躍會話"""
        return self._active_session

    def clear_metrics(self) -> None:
        """清除所有收集的指標"""
        for mt in MetricType:
            self._metric_collectors[mt].clear()
        logger.info("Cleared all collected metrics")

    def get_statistics(self) -> Dict[str, Any]:
        """
        獲取全局統計信息

        Returns:
            包含所有指標類型統計的字典
        """
        stats = {}
        for metric_type, values in self._metric_collectors.items():
            if values:
                stats[metric_type.value] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": statistics.mean(values),
                    "p95": self._percentile(values, 95),
                    "p99": self._percentile(values, 99),
                }
        return stats

    def _start_auto_collection(self) -> None:
        """開始自動收集系統指標"""
        async def collect_loop():
            try:
                import psutil
            except ImportError:
                logger.warning("psutil not installed, system metrics unavailable")
                return

            while True:
                try:
                    # 收集 CPU
                    cpu_percent = psutil.cpu_percent(interval=None)
                    self.record_metric(
                        "system_cpu",
                        MetricType.CPU,
                        cpu_percent,
                        "%"
                    )

                    # 收集記憶體
                    memory = psutil.virtual_memory()
                    self.record_metric(
                        "system_memory",
                        MetricType.MEMORY,
                        memory.used / (1024 * 1024),
                        "MB"
                    )

                    await asyncio.sleep(1)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error collecting system metrics: {e}")
                    await asyncio.sleep(5)

        try:
            loop = asyncio.get_event_loop()
            self._collection_task = loop.create_task(collect_loop())
        except RuntimeError:
            logger.warning("No event loop available for auto collection")

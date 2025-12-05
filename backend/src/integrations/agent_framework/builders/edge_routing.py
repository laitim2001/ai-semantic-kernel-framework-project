# =============================================================================
# FanOut/FanIn Edge Routing Integration
# =============================================================================
# Sprint 14: ConcurrentBuilder 重構
# Phase 3 Feature: P3-F1 (並行執行重構)
#
# 此模組整合 Agent Framework 的 Edge Routing 系統，
# 用於並行任務的分發 (FanOut) 和結果收集 (FanIn)。
#
# Agent Framework Edge 類型:
#   - Edge: 基本的有向邊，可選條件
#   - EdgeGroup: 邊組的基類
#   - FanOutEdgeGroup: 從一個源分發到多個目標
#   - FanInEdgeGroup: 從多個源合併到一個目標
#   - SwitchCaseEdgeGroup: 條件式路由
#
# 與 ConcurrentBuilderAdapter 整合:
#   - FanOutStrategy: 任務分發策略
#   - FanInAggregator: 結果聚合器
#   - ConditionalRouter: 條件式路由
# =============================================================================

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Generic, List, Optional, Sequence, TypeVar

logger = logging.getLogger(__name__)


# =============================================================================
# Edge Types - 與 Agent Framework 對齊
# =============================================================================


@dataclass
class Edge:
    """
    有向邊，連接兩個執行器。

    與 Agent Framework Edge 類對齊，支持條件式路由。

    Attributes:
        source_id: 源執行器 ID
        target_id: 目標執行器 ID
        condition: 可選的條件函數
        condition_name: 條件名稱（用於序列化）

    Example:
        edge = Edge(
            source_id="dispatcher",
            target_id="processor-1",
            condition=lambda data: data.get("priority") == "high"
        )
    """

    source_id: str
    target_id: str
    condition: Optional[Callable[[Any], bool]] = None
    condition_name: Optional[str] = None

    def __post_init__(self):
        """Extract condition name if not provided."""
        if self.condition and not self.condition_name:
            self.condition_name = getattr(
                self.condition, "__name__", "<lambda>"
            )

    @property
    def id(self) -> str:
        """Edge unique identifier."""
        return f"{self.source_id}->{self.target_id}"

    def should_route(self, data: Any) -> bool:
        """
        評估此邊是否應該路由數據。

        Args:
            data: 要路由的數據

        Returns:
            如果條件為 None 或條件評估為 True，返回 True
        """
        if self.condition is None:
            return True
        try:
            return self.condition(data)
        except Exception as e:
            logger.warning(f"Edge condition evaluation failed: {e}")
            return False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize edge to dictionary."""
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "condition_name": self.condition_name,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Edge":
        """Create edge from dictionary."""
        return cls(
            source_id=data["source_id"],
            target_id=data["target_id"],
            condition=None,  # Condition cannot be deserialized
            condition_name=data.get("condition_name"),
        )


# =============================================================================
# Edge Groups - 與 Agent Framework EdgeGroup 對齊
# =============================================================================


@dataclass
class EdgeGroup(ABC):
    """
    邊組的抽象基類。

    提供邊組的通用功能，包括:
    - 邊的集合管理
    - 序列化/反序列化
    - 源和目標 ID 追蹤

    Attributes:
        id: 邊組唯一標識符
        edges: 包含的邊列表
        type: 邊組類型名稱
    """

    id: str
    edges: List[Edge] = field(default_factory=list)
    type: str = field(init=False)

    def __post_init__(self):
        self.type = self.__class__.__name__

    @property
    def source_executor_ids(self) -> List[str]:
        """Get unique source executor IDs."""
        return list(dict.fromkeys(edge.source_id for edge in self.edges))

    @property
    def target_executor_ids(self) -> List[str]:
        """Get unique target executor IDs."""
        return list(dict.fromkeys(edge.target_id for edge in self.edges))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize edge group to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "edges": [edge.to_dict() for edge in self.edges],
        }


@dataclass
class FanOutEdgeGroup(EdgeGroup):
    """
    扇出邊組 - 從一個源分發到多個目標。

    用於並行任務分發，將一個輸入同時發送到多個執行器。

    Attributes:
        source_id: 源執行器 ID
        target_ids: 目標執行器 ID 列表
        selection_func: 可選的目標選擇函數

    Example:
        fan_out = FanOutEdgeGroup(
            id="distribute-tasks",
            source_id="dispatcher",
            target_ids=["worker-1", "worker-2", "worker-3"],
            selection_func=lambda data, targets: targets[:2]  # 只選前兩個
        )
    """

    source_id: str = ""
    target_ids: List[str] = field(default_factory=list)
    selection_func: Optional[Callable[[Any, List[str]], List[str]]] = None
    selection_func_name: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        # Build edges from source to targets
        self.edges = [
            Edge(source_id=self.source_id, target_id=target_id)
            for target_id in self.target_ids
        ]
        if self.selection_func and not self.selection_func_name:
            self.selection_func_name = getattr(
                self.selection_func, "__name__", "<lambda>"
            )

    def select_targets(self, data: Any) -> List[str]:
        """
        根據數據選擇目標。

        Args:
            data: 輸入數據

        Returns:
            選擇的目標 ID 列表
        """
        if self.selection_func is None:
            return self.target_ids.copy()
        try:
            return self.selection_func(data, self.target_ids.copy())
        except Exception as e:
            logger.error(f"FanOut selection function failed: {e}")
            return self.target_ids.copy()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        result = super().to_dict()
        result["source_id"] = self.source_id
        result["target_ids"] = self.target_ids
        result["selection_func_name"] = self.selection_func_name
        return result


@dataclass
class FanInEdgeGroup(EdgeGroup):
    """
    扇入邊組 - 從多個源合併到一個目標。

    用於收集並行任務的結果，將多個輸出合併到一個處理器。

    Attributes:
        source_ids: 源執行器 ID 列表
        target_id: 目標執行器 ID
        aggregator: 可選的結果聚合函數

    Example:
        fan_in = FanInEdgeGroup(
            id="collect-results",
            source_ids=["worker-1", "worker-2", "worker-3"],
            target_id="collector",
            aggregator=lambda results: {"merged": results}
        )
    """

    source_ids: List[str] = field(default_factory=list)
    target_id: str = ""
    aggregator: Optional[Callable[[List[Any]], Any]] = None
    aggregator_name: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        # Build edges from sources to target
        self.edges = [
            Edge(source_id=source_id, target_id=self.target_id)
            for source_id in self.source_ids
        ]
        if self.aggregator and not self.aggregator_name:
            self.aggregator_name = getattr(
                self.aggregator, "__name__", "<lambda>"
            )

    def aggregate(self, results: List[Any]) -> Any:
        """
        聚合多個結果。

        Args:
            results: 來自各源的結果列表

        Returns:
            聚合後的結果
        """
        if self.aggregator is None:
            return results
        try:
            return self.aggregator(results)
        except Exception as e:
            logger.error(f"FanIn aggregator failed: {e}")
            return results

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        result = super().to_dict()
        result["source_ids"] = self.source_ids
        result["target_id"] = self.target_id
        result["aggregator_name"] = self.aggregator_name
        return result


# =============================================================================
# FanOut Strategies - 任務分發策略
# =============================================================================


class FanOutStrategy(str, Enum):
    """
    扇出分發策略。

    Values:
        BROADCAST: 廣播到所有目標
        ROUND_ROBIN: 輪詢分發
        HASH_BASED: 基於哈希分發
        LOAD_BALANCED: 負載均衡分發
        SELECTIVE: 選擇性分發（基於條件）
    """

    BROADCAST = "broadcast"
    ROUND_ROBIN = "round_robin"
    HASH_BASED = "hash_based"
    LOAD_BALANCED = "load_balanced"
    SELECTIVE = "selective"


@dataclass
class FanOutConfig:
    """
    扇出配置。

    Attributes:
        strategy: 分發策略
        targets: 目標執行器列表
        selector: 自定義選擇器（SELECTIVE 策略使用）
        hash_key: 哈希鍵（HASH_BASED 策略使用）
        max_targets: 最大目標數量（可選）
    """

    strategy: FanOutStrategy = FanOutStrategy.BROADCAST
    targets: List[str] = field(default_factory=list)
    selector: Optional[Callable[[Any, List[str]], List[str]]] = None
    hash_key: Optional[str] = None
    max_targets: Optional[int] = None


class FanOutRouter:
    """
    扇出路由器 - 管理任務分發。

    根據配置的策略將任務分發到目標執行器。

    Example:
        router = FanOutRouter(
            FanOutConfig(
                strategy=FanOutStrategy.BROADCAST,
                targets=["worker-1", "worker-2", "worker-3"]
            )
        )
        targets = router.select_targets({"task": "process"})
        # targets = ["worker-1", "worker-2", "worker-3"]
    """

    def __init__(self, config: FanOutConfig):
        """Initialize FanOut router with config."""
        self._config = config
        self._round_robin_index = 0
        self._target_loads: Dict[str, int] = {t: 0 for t in config.targets}

    @property
    def targets(self) -> List[str]:
        """Get all target executor IDs."""
        return self._config.targets.copy()

    def select_targets(self, data: Any) -> List[str]:
        """
        根據策略選擇目標。

        Args:
            data: 輸入數據

        Returns:
            選擇的目標 ID 列表
        """
        strategy = self._config.strategy

        if strategy == FanOutStrategy.BROADCAST:
            targets = self._broadcast_select(data)
        elif strategy == FanOutStrategy.ROUND_ROBIN:
            targets = self._round_robin_select(data)
        elif strategy == FanOutStrategy.HASH_BASED:
            targets = self._hash_based_select(data)
        elif strategy == FanOutStrategy.LOAD_BALANCED:
            targets = self._load_balanced_select(data)
        elif strategy == FanOutStrategy.SELECTIVE:
            targets = self._selective_select(data)
        else:
            targets = self._broadcast_select(data)

        # Apply max_targets limit if configured
        if self._config.max_targets:
            targets = targets[: self._config.max_targets]

        return targets

    def _broadcast_select(self, data: Any) -> List[str]:
        """Broadcast to all targets."""
        return self._config.targets.copy()

    def _round_robin_select(self, data: Any) -> List[str]:
        """Select next target in round-robin fashion."""
        if not self._config.targets:
            return []
        target = self._config.targets[self._round_robin_index]
        self._round_robin_index = (
            self._round_robin_index + 1
        ) % len(self._config.targets)
        return [target]

    def _hash_based_select(self, data: Any) -> List[str]:
        """Select target based on hash of data."""
        if not self._config.targets:
            return []

        # Get hash key value
        hash_key = self._config.hash_key or "id"
        hash_value = data.get(hash_key) if isinstance(data, dict) else str(data)

        # Calculate target index
        index = hash(str(hash_value)) % len(self._config.targets)
        return [self._config.targets[index]]

    def _load_balanced_select(self, data: Any) -> List[str]:
        """Select least loaded target."""
        if not self._config.targets:
            return []

        # Find target with minimum load
        min_load = min(self._target_loads.values())
        for target in self._config.targets:
            if self._target_loads[target] == min_load:
                self._target_loads[target] += 1
                return [target]

        return [self._config.targets[0]]

    def _selective_select(self, data: Any) -> List[str]:
        """Select targets using custom selector."""
        if self._config.selector:
            try:
                return self._config.selector(data, self._config.targets.copy())
            except Exception as e:
                logger.error(f"Selective selector failed: {e}")
        return self._config.targets.copy()

    def mark_completed(self, target: str) -> None:
        """Mark a target as having completed (for load balancing)."""
        if target in self._target_loads:
            self._target_loads[target] = max(0, self._target_loads[target] - 1)

    def create_edge_group(self, source_id: str) -> FanOutEdgeGroup:
        """Create a FanOutEdgeGroup for this router."""
        return FanOutEdgeGroup(
            id=f"fanout-{source_id}",
            source_id=source_id,
            target_ids=self._config.targets,
            selection_func=self.select_targets,
        )


# =============================================================================
# FanIn Strategies - 結果聚合策略
# =============================================================================


class FanInStrategy(str, Enum):
    """
    扇入聚合策略。

    Values:
        COLLECT_ALL: 收集所有結果
        FIRST_COMPLETED: 取第一個完成的
        MAJORITY_VOTE: 多數投票
        MERGE_DICTS: 合併字典
        CUSTOM: 自定義聚合
    """

    COLLECT_ALL = "collect_all"
    FIRST_COMPLETED = "first_completed"
    MAJORITY_VOTE = "majority_vote"
    MERGE_DICTS = "merge_dicts"
    CUSTOM = "custom"


@dataclass
class FanInConfig:
    """
    扇入配置。

    Attributes:
        strategy: 聚合策略
        sources: 源執行器列表
        aggregator: 自定義聚合器（CUSTOM 策略使用）
        timeout_seconds: 等待超時時間
        min_results: 最少需要的結果數量
    """

    strategy: FanInStrategy = FanInStrategy.COLLECT_ALL
    sources: List[str] = field(default_factory=list)
    aggregator: Optional[Callable[[List[Any]], Any]] = None
    timeout_seconds: float = 300.0
    min_results: Optional[int] = None


T = TypeVar("T")


class FanInAggregator(Generic[T]):
    """
    扇入聚合器 - 管理結果收集和聚合。

    根據配置的策略聚合來自多個源的結果。

    Example:
        aggregator = FanInAggregator(
            FanInConfig(
                strategy=FanInStrategy.COLLECT_ALL,
                sources=["worker-1", "worker-2", "worker-3"]
            )
        )
        result = aggregator.aggregate([result1, result2, result3])
    """

    def __init__(self, config: FanInConfig):
        """Initialize FanIn aggregator with config."""
        self._config = config
        self._results: Dict[str, Any] = {}
        self._started_at: Optional[datetime] = None

    @property
    def sources(self) -> List[str]:
        """Get all source executor IDs."""
        return self._config.sources.copy()

    @property
    def min_results_required(self) -> int:
        """Get minimum results required."""
        return self._config.min_results or len(self._config.sources)

    def start(self) -> None:
        """Start aggregation session."""
        self._results = {}
        self._started_at = datetime.now(timezone.utc)

    def add_result(self, source_id: str, result: Any) -> None:
        """
        添加來自特定源的結果。

        Args:
            source_id: 源執行器 ID
            result: 結果數據
        """
        self._results[source_id] = result
        logger.debug(f"FanIn received result from {source_id}")

    def is_complete(self) -> bool:
        """
        檢查是否收集了足夠的結果。

        Returns:
            如果收集了足夠的結果返回 True
        """
        return len(self._results) >= self.min_results_required

    def aggregate(self, results: Optional[List[Any]] = None) -> Any:
        """
        聚合所有收集的結果。

        Args:
            results: 可選的結果列表（如果提供則使用，否則使用內部收集的結果）

        Returns:
            聚合後的結果
        """
        if results is None:
            results = list(self._results.values())

        strategy = self._config.strategy

        if strategy == FanInStrategy.COLLECT_ALL:
            return self._collect_all(results)
        elif strategy == FanInStrategy.FIRST_COMPLETED:
            return self._first_completed(results)
        elif strategy == FanInStrategy.MAJORITY_VOTE:
            return self._majority_vote(results)
        elif strategy == FanInStrategy.MERGE_DICTS:
            return self._merge_dicts(results)
        elif strategy == FanInStrategy.CUSTOM:
            return self._custom_aggregate(results)
        else:
            return self._collect_all(results)

    def _collect_all(self, results: List[Any]) -> Dict[str, Any]:
        """Collect all results into a list."""
        return {
            "strategy": "collect_all",
            "results": results,
            "count": len(results),
        }

    def _first_completed(self, results: List[Any]) -> Dict[str, Any]:
        """Return first result."""
        return {
            "strategy": "first_completed",
            "result": results[0] if results else None,
        }

    def _majority_vote(self, results: List[Any]) -> Dict[str, Any]:
        """Return majority result based on voting."""
        if not results:
            return {"strategy": "majority_vote", "result": None, "votes": 0}

        # Count votes (simple equality comparison)
        votes: Dict[str, int] = {}
        for result in results:
            key = str(result)
            votes[key] = votes.get(key, 0) + 1

        # Find winner
        max_votes = max(votes.values())
        for result in results:
            if votes[str(result)] == max_votes:
                return {
                    "strategy": "majority_vote",
                    "result": result,
                    "votes": max_votes,
                    "total": len(results),
                }

        return {"strategy": "majority_vote", "result": results[0], "votes": 1}

    def _merge_dicts(self, results: List[Any]) -> Dict[str, Any]:
        """Merge dictionary results."""
        merged: Dict[str, Any] = {}
        for result in results:
            if isinstance(result, dict):
                merged.update(result)
        return {
            "strategy": "merge_dicts",
            "merged": merged,
            "sources": len(results),
        }

    def _custom_aggregate(self, results: List[Any]) -> Any:
        """Use custom aggregator."""
        if self._config.aggregator:
            try:
                return self._config.aggregator(results)
            except Exception as e:
                logger.error(f"Custom aggregator failed: {e}")
        return self._collect_all(results)

    def create_edge_group(self, target_id: str) -> FanInEdgeGroup:
        """Create a FanInEdgeGroup for this aggregator."""
        return FanInEdgeGroup(
            id=f"fanin-{target_id}",
            source_ids=self._config.sources,
            target_id=target_id,
            aggregator=self.aggregate if self._config.strategy == FanInStrategy.CUSTOM else None,
        )


# =============================================================================
# Conditional Router - 條件式路由
# =============================================================================


@dataclass
class RouteCondition:
    """
    路由條件。

    Attributes:
        target_id: 目標執行器 ID
        condition: 條件函數
        priority: 優先級（越高越優先）
    """

    target_id: str
    condition: Callable[[Any], bool]
    priority: int = 0


class ConditionalRouter:
    """
    條件式路由器。

    根據條件將數據路由到不同的目標。

    Example:
        router = ConditionalRouter(
            source_id="classifier",
            conditions=[
                RouteCondition(
                    target_id="high-priority",
                    condition=lambda x: x.get("priority") == "high",
                    priority=10
                ),
                RouteCondition(
                    target_id="normal",
                    condition=lambda x: True,  # 默認
                    priority=0
                ),
            ]
        )
        targets = router.route({"priority": "high"})
        # targets = ["high-priority"]
    """

    def __init__(
        self,
        source_id: str,
        conditions: List[RouteCondition],
        default_target: Optional[str] = None,
    ):
        """Initialize conditional router."""
        self._source_id = source_id
        self._conditions = sorted(
            conditions, key=lambda c: c.priority, reverse=True
        )
        self._default_target = default_target

    def route(self, data: Any) -> List[str]:
        """
        根據條件路由數據。

        Args:
            data: 輸入數據

        Returns:
            匹配的目標 ID 列表
        """
        matched: List[str] = []

        for condition in self._conditions:
            try:
                if condition.condition(data):
                    matched.append(condition.target_id)
                    break  # 只匹配第一個符合條件的
            except Exception as e:
                logger.warning(f"Route condition evaluation failed: {e}")

        if not matched and self._default_target:
            matched.append(self._default_target)

        return matched

    def route_all_matching(self, data: Any) -> List[str]:
        """
        返回所有匹配的目標。

        Args:
            data: 輸入數據

        Returns:
            所有匹配的目標 ID 列表
        """
        matched: List[str] = []

        for condition in self._conditions:
            try:
                if condition.condition(data):
                    matched.append(condition.target_id)
            except Exception as e:
                logger.warning(f"Route condition evaluation failed: {e}")

        if not matched and self._default_target:
            matched.append(self._default_target)

        return matched


# =============================================================================
# Factory Functions
# =============================================================================


def create_broadcast_fan_out(
    source_id: str,
    target_ids: List[str],
) -> FanOutEdgeGroup:
    """
    創建廣播式扇出邊組。

    Args:
        source_id: 源執行器 ID
        target_ids: 目標執行器 ID 列表

    Returns:
        FanOutEdgeGroup
    """
    return FanOutEdgeGroup(
        id=f"broadcast-{source_id}",
        source_id=source_id,
        target_ids=target_ids,
    )


def create_collect_all_fan_in(
    source_ids: List[str],
    target_id: str,
) -> FanInEdgeGroup:
    """
    創建收集所有結果的扇入邊組。

    Args:
        source_ids: 源執行器 ID 列表
        target_id: 目標執行器 ID

    Returns:
        FanInEdgeGroup
    """
    return FanInEdgeGroup(
        id=f"collect-{target_id}",
        source_ids=source_ids,
        target_id=target_id,
    )


def create_parallel_routing(
    dispatcher_id: str,
    worker_ids: List[str],
    collector_id: str,
    fan_out_strategy: FanOutStrategy = FanOutStrategy.BROADCAST,
    fan_in_strategy: FanInStrategy = FanInStrategy.COLLECT_ALL,
) -> Dict[str, Any]:
    """
    創建完整的並行路由配置。

    Args:
        dispatcher_id: 分發器執行器 ID
        worker_ids: 工作器執行器 ID 列表
        collector_id: 收集器執行器 ID
        fan_out_strategy: 扇出策略
        fan_in_strategy: 扇入策略

    Returns:
        包含 fan_out 和 fan_in 配置的字典
    """
    fan_out_router = FanOutRouter(
        FanOutConfig(
            strategy=fan_out_strategy,
            targets=worker_ids,
        )
    )

    fan_in_aggregator = FanInAggregator(
        FanInConfig(
            strategy=fan_in_strategy,
            sources=worker_ids,
        )
    )

    return {
        "fan_out": {
            "router": fan_out_router,
            "edge_group": fan_out_router.create_edge_group(dispatcher_id),
        },
        "fan_in": {
            "aggregator": fan_in_aggregator,
            "edge_group": fan_in_aggregator.create_edge_group(collector_id),
        },
    }


__all__ = [
    # Edge types
    "Edge",
    "EdgeGroup",
    "FanOutEdgeGroup",
    "FanInEdgeGroup",
    # FanOut
    "FanOutStrategy",
    "FanOutConfig",
    "FanOutRouter",
    # FanIn
    "FanInStrategy",
    "FanInConfig",
    "FanInAggregator",
    # Conditional routing
    "RouteCondition",
    "ConditionalRouter",
    # Factory functions
    "create_broadcast_fan_out",
    "create_collect_all_fan_in",
    "create_parallel_routing",
]

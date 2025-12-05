# =============================================================================
# Unit Tests for Edge Routing
# =============================================================================
# Sprint 14: ConcurrentBuilder 重構
# Phase 3 Feature: P3-F1 (並行執行重構)
#
# 測試範圍:
#   - Edge, EdgeGroup 基類
#   - FanOutEdgeGroup, FanInEdgeGroup
#   - FanOutRouter (5 種策略)
#   - FanInAggregator (5 種策略)
#   - ConditionalRouter 條件路由
#   - 工廠函數
# =============================================================================

import asyncio
import pytest
from typing import Any, List
from uuid import uuid4

from src.integrations.agent_framework.builders.edge_routing import (
    Edge,
    EdgeGroup,
    FanOutEdgeGroup,
    FanInEdgeGroup,
    FanOutStrategy,
    FanOutConfig,
    FanOutRouter,
    FanInStrategy,
    FanInConfig,
    FanInAggregator,
    RouteCondition,
    ConditionalRouter,
    create_broadcast_fan_out,
    create_collect_all_fan_in,
    create_parallel_routing,
)


# =============================================================================
# Edge 基類測試
# =============================================================================


class TestEdge:
    """Edge 基類測試。"""

    def test_edge_creation(self):
        """測試 Edge 創建。"""
        edge = Edge(
            id="edge-1",
            source="node-a",
            target="node-b",
        )

        assert edge.id == "edge-1"
        assert edge.source == "node-a"
        assert edge.target == "node-b"
        assert edge.metadata == {}

    def test_edge_with_metadata(self):
        """測試帶元數據的 Edge。"""
        edge = Edge(
            id="edge-2",
            source="a",
            target="b",
            metadata={"priority": 1, "type": "data"},
        )

        assert edge.metadata["priority"] == 1
        assert edge.metadata["type"] == "data"

    def test_edge_to_dict(self):
        """測試 Edge 字典轉換。"""
        edge = Edge(id="e1", source="s", target="t")
        data = edge.to_dict()

        assert data["id"] == "e1"
        assert data["source"] == "s"
        assert data["target"] == "t"


# =============================================================================
# EdgeGroup 基類測試
# =============================================================================


class TestEdgeGroup:
    """EdgeGroup 基類測試。"""

    def test_edge_group_creation(self):
        """測試 EdgeGroup 創建。"""
        group = EdgeGroup(
            id="group-1",
            source="start",
            targets=["end-1", "end-2"],
        )

        assert group.id == "group-1"
        assert group.source == "start"
        assert len(group.targets) == 2

    def test_edge_group_edges(self):
        """測試 EdgeGroup 生成的 edges。"""
        group = EdgeGroup(
            id="group-1",
            source="start",
            targets=["end-1", "end-2", "end-3"],
        )

        edges = group.edges
        assert len(edges) == 3

        for edge in edges:
            assert edge.source == "start"
            assert edge.target in ["end-1", "end-2", "end-3"]

    def test_add_target(self):
        """測試添加目標。"""
        group = EdgeGroup(id="g1", source="s", targets=[])
        group.add_target("t1")
        group.add_target("t2")

        assert len(group.targets) == 2
        assert "t1" in group.targets
        assert "t2" in group.targets


# =============================================================================
# FanOutStrategy 測試
# =============================================================================


class TestFanOutStrategy:
    """FanOutStrategy 枚舉測試。"""

    def test_strategy_values(self):
        """測試策略值。"""
        assert FanOutStrategy.BROADCAST.value == "broadcast"
        assert FanOutStrategy.ROUND_ROBIN.value == "round_robin"
        assert FanOutStrategy.HASH_BASED.value == "hash_based"
        assert FanOutStrategy.LOAD_BALANCED.value == "load_balanced"
        assert FanOutStrategy.SELECTIVE.value == "selective"


# =============================================================================
# FanOutConfig 測試
# =============================================================================


class TestFanOutConfig:
    """FanOutConfig 數據類測試。"""

    def test_default_config(self):
        """測試預設配置。"""
        config = FanOutConfig()

        assert config.strategy == FanOutStrategy.BROADCAST
        assert config.hash_key is None
        assert config.selection_predicate is None

    def test_custom_config(self):
        """測試自定義配置。"""
        def predicate(data, target):
            return target.startswith("valid")

        config = FanOutConfig(
            strategy=FanOutStrategy.SELECTIVE,
            hash_key="user_id",
            selection_predicate=predicate,
        )

        assert config.strategy == FanOutStrategy.SELECTIVE
        assert config.hash_key == "user_id"
        assert config.selection_predicate is not None


# =============================================================================
# FanOutRouter 測試
# =============================================================================


class TestFanOutRouter:
    """FanOutRouter 測試。"""

    @pytest.mark.asyncio
    async def test_broadcast_strategy(self):
        """測試廣播策略。"""
        router = FanOutRouter(FanOutConfig(strategy=FanOutStrategy.BROADCAST))
        targets = ["t1", "t2", "t3"]

        result = await router.route({"data": "test"}, targets)

        # 廣播應該返回所有目標
        assert len(result) == 3
        assert set(result) == set(targets)

    @pytest.mark.asyncio
    async def test_round_robin_strategy(self):
        """測試輪詢策略。"""
        router = FanOutRouter(FanOutConfig(strategy=FanOutStrategy.ROUND_ROBIN))
        targets = ["t1", "t2", "t3"]

        results = []
        for _ in range(6):
            result = await router.route({}, targets)
            results.append(result[0])

        # 輪詢應該循環訪問所有目標
        assert results.count("t1") == 2
        assert results.count("t2") == 2
        assert results.count("t3") == 2

    @pytest.mark.asyncio
    async def test_hash_based_strategy(self):
        """測試哈希策略。"""
        router = FanOutRouter(FanOutConfig(
            strategy=FanOutStrategy.HASH_BASED,
            hash_key="user_id",
        ))
        targets = ["t1", "t2", "t3"]

        # 相同的 hash key 應該路由到相同的目標
        result1 = await router.route({"user_id": "user-123"}, targets)
        result2 = await router.route({"user_id": "user-123"}, targets)

        assert result1 == result2

        # 不同的 hash key 可能路由到不同目標
        result3 = await router.route({"user_id": "user-456"}, targets)
        # 結果可能相同也可能不同，只驗證返回單一目標
        assert len(result3) == 1

    @pytest.mark.asyncio
    async def test_load_balanced_strategy(self):
        """測試負載均衡策略。"""
        router = FanOutRouter(FanOutConfig(strategy=FanOutStrategy.LOAD_BALANCED))
        targets = ["t1", "t2", "t3"]

        # 負載均衡返回單一目標
        result = await router.route({}, targets)
        assert len(result) == 1
        assert result[0] in targets

    @pytest.mark.asyncio
    async def test_selective_strategy(self):
        """測試選擇性策略。"""
        def predicate(data, target):
            return "valid" in target

        router = FanOutRouter(FanOutConfig(
            strategy=FanOutStrategy.SELECTIVE,
            selection_predicate=predicate,
        ))
        targets = ["valid-1", "invalid-1", "valid-2"]

        result = await router.route({}, targets)

        assert len(result) == 2
        assert all("valid" in t for t in result)


# =============================================================================
# FanOutEdgeGroup 測試
# =============================================================================


class TestFanOutEdgeGroup:
    """FanOutEdgeGroup 測試。"""

    def test_creation(self):
        """測試創建。"""
        group = FanOutEdgeGroup(
            id="fanout-1",
            source="start",
            targets=["end-1", "end-2"],
            config=FanOutConfig(strategy=FanOutStrategy.BROADCAST),
        )

        assert group.id == "fanout-1"
        assert group.strategy == FanOutStrategy.BROADCAST

    @pytest.mark.asyncio
    async def test_route_data(self):
        """測試路由數據。"""
        group = FanOutEdgeGroup(
            id="fanout-1",
            source="start",
            targets=["end-1", "end-2", "end-3"],
            config=FanOutConfig(strategy=FanOutStrategy.BROADCAST),
        )

        result = await group.route_data({"input": "test"})

        assert len(result) == 3

    def test_to_dict(self):
        """測試字典轉換。"""
        group = FanOutEdgeGroup(
            id="fanout-1",
            source="start",
            targets=["end-1", "end-2"],
        )

        data = group.to_dict()

        assert data["id"] == "fanout-1"
        assert data["type"] == "fan_out"
        assert data["strategy"] == "broadcast"


# =============================================================================
# FanInStrategy 測試
# =============================================================================


class TestFanInStrategy:
    """FanInStrategy 枚舉測試。"""

    def test_strategy_values(self):
        """測試策略值。"""
        assert FanInStrategy.COLLECT_ALL.value == "collect_all"
        assert FanInStrategy.FIRST_COMPLETED.value == "first_completed"
        assert FanInStrategy.MAJORITY_VOTE.value == "majority_vote"
        assert FanInStrategy.MERGE_DICTS.value == "merge_dicts"
        assert FanInStrategy.CUSTOM.value == "custom"


# =============================================================================
# FanInAggregator 測試
# =============================================================================


class TestFanInAggregator:
    """FanInAggregator 測試。"""

    @pytest.mark.asyncio
    async def test_collect_all_strategy(self):
        """測試收集所有策略。"""
        aggregator = FanInAggregator(FanInConfig(strategy=FanInStrategy.COLLECT_ALL))
        results = [
            {"source": "t1", "value": 1},
            {"source": "t2", "value": 2},
            {"source": "t3", "value": 3},
        ]

        aggregated = await aggregator.aggregate(results)

        assert len(aggregated["results"]) == 3
        assert aggregated["count"] == 3

    @pytest.mark.asyncio
    async def test_first_completed_strategy(self):
        """測試首個完成策略。"""
        aggregator = FanInAggregator(FanInConfig(strategy=FanInStrategy.FIRST_COMPLETED))
        results = [
            {"source": "t1", "value": 1, "completed_at": "2024-01-01T00:00:00"},
            {"source": "t2", "value": 2, "completed_at": "2024-01-01T00:00:01"},
        ]

        aggregated = await aggregator.aggregate(results)

        # 應該只返回第一個
        assert aggregated is not None

    @pytest.mark.asyncio
    async def test_majority_vote_strategy(self):
        """測試多數投票策略。"""
        aggregator = FanInAggregator(FanInConfig(strategy=FanInStrategy.MAJORITY_VOTE))
        results = [
            {"vote": "A"},
            {"vote": "A"},
            {"vote": "B"},
            {"vote": "A"},
        ]

        aggregated = await aggregator.aggregate(results)

        # A 獲得多數票
        assert aggregated["winner"] == "A"
        assert aggregated["count"] == 3

    @pytest.mark.asyncio
    async def test_merge_dicts_strategy(self):
        """測試字典合併策略。"""
        aggregator = FanInAggregator(FanInConfig(strategy=FanInStrategy.MERGE_DICTS))
        results = [
            {"key1": "value1"},
            {"key2": "value2"},
            {"key3": "value3"},
        ]

        aggregated = await aggregator.aggregate(results)

        assert aggregated["key1"] == "value1"
        assert aggregated["key2"] == "value2"
        assert aggregated["key3"] == "value3"

    @pytest.mark.asyncio
    async def test_custom_strategy(self):
        """測試自定義策略。"""
        def custom_aggregator(results):
            return {"sum": sum(r.get("value", 0) for r in results)}

        aggregator = FanInAggregator(FanInConfig(
            strategy=FanInStrategy.CUSTOM,
            custom_aggregator=custom_aggregator,
        ))
        results = [
            {"value": 10},
            {"value": 20},
            {"value": 30},
        ]

        aggregated = await aggregator.aggregate(results)

        assert aggregated["sum"] == 60


# =============================================================================
# FanInEdgeGroup 測試
# =============================================================================


class TestFanInEdgeGroup:
    """FanInEdgeGroup 測試。"""

    def test_creation(self):
        """測試創建。"""
        group = FanInEdgeGroup(
            id="fanin-1",
            sources=["start-1", "start-2"],
            target="end",
            config=FanInConfig(strategy=FanInStrategy.COLLECT_ALL),
        )

        assert group.id == "fanin-1"
        assert len(group.sources) == 2
        assert group.target == "end"
        assert group.strategy == FanInStrategy.COLLECT_ALL

    @pytest.mark.asyncio
    async def test_aggregate_results(self):
        """測試聚合結果。"""
        group = FanInEdgeGroup(
            id="fanin-1",
            sources=["s1", "s2"],
            target="end",
            config=FanInConfig(strategy=FanInStrategy.COLLECT_ALL),
        )

        results = [{"value": 1}, {"value": 2}]
        aggregated = await group.aggregate_results(results)

        assert aggregated["count"] == 2

    def test_to_dict(self):
        """測試字典轉換。"""
        group = FanInEdgeGroup(
            id="fanin-1",
            sources=["s1", "s2"],
            target="end",
        )

        data = group.to_dict()

        assert data["id"] == "fanin-1"
        assert data["type"] == "fan_in"
        assert data["strategy"] == "collect_all"


# =============================================================================
# RouteCondition 測試
# =============================================================================


class TestRouteCondition:
    """RouteCondition 測試。"""

    def test_basic_condition(self):
        """測試基本條件。"""
        condition = RouteCondition(
            id="cond-1",
            target="target-a",
            predicate=lambda data: data.get("type") == "A",
        )

        assert condition.id == "cond-1"
        assert condition.target == "target-a"

    def test_condition_evaluation(self):
        """測試條件評估。"""
        condition = RouteCondition(
            id="cond-1",
            target="target-a",
            predicate=lambda data: data.get("value", 0) > 10,
        )

        assert condition.evaluate({"value": 20}) is True
        assert condition.evaluate({"value": 5}) is False

    def test_condition_with_priority(self):
        """測試帶優先級的條件。"""
        condition = RouteCondition(
            id="cond-1",
            target="target-a",
            predicate=lambda data: True,
            priority=10,
        )

        assert condition.priority == 10


# =============================================================================
# ConditionalRouter 測試
# =============================================================================


class TestConditionalRouter:
    """ConditionalRouter 測試。"""

    @pytest.mark.asyncio
    async def test_single_condition_match(self):
        """測試單一條件匹配。"""
        router = ConditionalRouter(
            id="router-1",
            source="start",
        )

        router.add_condition(RouteCondition(
            id="cond-a",
            target="target-a",
            predicate=lambda data: data.get("type") == "A",
        ))

        router.add_condition(RouteCondition(
            id="cond-b",
            target="target-b",
            predicate=lambda data: data.get("type") == "B",
        ))

        result = await router.route({"type": "A"})
        assert result == ["target-a"]

        result = await router.route({"type": "B"})
        assert result == ["target-b"]

    @pytest.mark.asyncio
    async def test_default_target(self):
        """測試默認目標。"""
        router = ConditionalRouter(
            id="router-1",
            source="start",
            default_target="default",
        )

        router.add_condition(RouteCondition(
            id="cond-a",
            target="target-a",
            predicate=lambda data: data.get("type") == "A",
        ))

        # 不匹配任何條件時返回默認目標
        result = await router.route({"type": "C"})
        assert result == ["default"]

    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        """測試優先級排序。"""
        router = ConditionalRouter(
            id="router-1",
            source="start",
        )

        # 添加低優先級條件
        router.add_condition(RouteCondition(
            id="low",
            target="low-priority",
            predicate=lambda data: True,  # 總是匹配
            priority=1,
        ))

        # 添加高優先級條件
        router.add_condition(RouteCondition(
            id="high",
            target="high-priority",
            predicate=lambda data: True,  # 總是匹配
            priority=10,
        ))

        result = await router.route({})

        # 應該返回高優先級目標
        assert result == ["high-priority"]

    @pytest.mark.asyncio
    async def test_multiple_matches(self):
        """測試多個匹配 (allow_multiple=True)。"""
        router = ConditionalRouter(
            id="router-1",
            source="start",
            allow_multiple=True,
        )

        router.add_condition(RouteCondition(
            id="cond-a",
            target="target-a",
            predicate=lambda data: data.get("value", 0) > 5,
        ))

        router.add_condition(RouteCondition(
            id="cond-b",
            target="target-b",
            predicate=lambda data: data.get("value", 0) > 10,
        ))

        result = await router.route({"value": 15})

        # 兩個條件都匹配
        assert len(result) == 2
        assert "target-a" in result
        assert "target-b" in result

    def test_to_dict(self):
        """測試字典轉換。"""
        router = ConditionalRouter(
            id="router-1",
            source="start",
            default_target="default",
        )

        router.add_condition(RouteCondition(
            id="cond-a",
            target="target-a",
            predicate=lambda data: True,
        ))

        data = router.to_dict()

        assert data["id"] == "router-1"
        assert data["type"] == "conditional"
        assert data["source"] == "start"
        assert data["default_target"] == "default"
        assert len(data["conditions"]) == 1


# =============================================================================
# 工廠函數測試
# =============================================================================


class TestFactoryFunctions:
    """工廠函數測試。"""

    def test_create_broadcast_fan_out(self):
        """測試創建廣播 FanOut。"""
        fan_out = create_broadcast_fan_out(
            id="fanout-1",
            source="start",
            targets=["t1", "t2", "t3"],
        )

        assert fan_out.id == "fanout-1"
        assert fan_out.strategy == FanOutStrategy.BROADCAST
        assert len(fan_out.targets) == 3

    def test_create_collect_all_fan_in(self):
        """測試創建收集所有 FanIn。"""
        fan_in = create_collect_all_fan_in(
            id="fanin-1",
            sources=["s1", "s2"],
            target="end",
        )

        assert fan_in.id == "fanin-1"
        assert fan_in.strategy == FanInStrategy.COLLECT_ALL
        assert len(fan_in.sources) == 2

    def test_create_parallel_routing(self):
        """測試創建並行路由配對。"""
        fan_out, fan_in = create_parallel_routing(
            id="parallel-1",
            source="start",
            targets=["worker-1", "worker-2", "worker-3"],
            end_target="end",
        )

        assert fan_out.id == "parallel-1-fanout"
        assert fan_in.id == "parallel-1-fanin"
        assert fan_out.source == "start"
        assert fan_in.target == "end"
        assert len(fan_out.targets) == 3
        assert len(fan_in.sources) == 3


# =============================================================================
# 整合測試
# =============================================================================


class TestIntegration:
    """整合測試。"""

    @pytest.mark.asyncio
    async def test_fanout_fanin_pipeline(self):
        """測試 FanOut → FanIn 管道。"""
        # 創建 FanOut
        fan_out = FanOutEdgeGroup(
            id="fanout",
            source="start",
            targets=["worker-1", "worker-2", "worker-3"],
            config=FanOutConfig(strategy=FanOutStrategy.BROADCAST),
        )

        # 路由數據
        input_data = {"task": "process"}
        routed_targets = await fan_out.route_data(input_data)

        # 模擬工作者處理
        worker_results = [
            {"worker": target, "result": f"processed by {target}"}
            for target in routed_targets
        ]

        # 創建 FanIn
        fan_in = FanInEdgeGroup(
            id="fanin",
            sources=["worker-1", "worker-2", "worker-3"],
            target="end",
            config=FanInConfig(strategy=FanInStrategy.COLLECT_ALL),
        )

        # 聚合結果
        final_result = await fan_in.aggregate_results(worker_results)

        assert final_result["count"] == 3
        assert len(final_result["results"]) == 3

    @pytest.mark.asyncio
    async def test_conditional_with_fanout(self):
        """測試條件路由與 FanOut 組合。"""
        # 條件路由器
        router = ConditionalRouter(
            id="type-router",
            source="input",
            default_target="default-handler",
        )

        router.add_condition(RouteCondition(
            id="parallel-route",
            target="parallel-processing",
            predicate=lambda data: data.get("parallel", False),
        ))

        # 測試路由到並行處理
        parallel_route = await router.route({"parallel": True})
        assert parallel_route == ["parallel-processing"]

        # 如果路由到並行處理，可以使用 FanOut
        if "parallel-processing" in parallel_route:
            fan_out = FanOutEdgeGroup(
                id="parallel-fanout",
                source="parallel-processing",
                targets=["p1", "p2"],
            )
            targets = await fan_out.route_data({})
            assert len(targets) == 2

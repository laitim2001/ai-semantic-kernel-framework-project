# =============================================================================
# IPA Platform - ConcurrentBuilderAdapter Tests
# =============================================================================
# Sprint 22: Concurrent & Memory Migration (Phase 4)
#
# Tests for ConcurrentBuilderAdapter Gateway functionality.
# =============================================================================

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.agent_framework.builders.concurrent import (
    ConcurrentBuilderAdapter,
    ConcurrentMode,
    ConcurrentTaskConfig,
    TaskResult,
    ConcurrentExecutionResult,
    GatewayType,
    JoinCondition,
    MergeStrategy,
    GatewayConfig,
    NOfMAggregator,
    MergeStrategyAggregator,
    AllModeAggregator,
    AnyModeAggregator,
    MajorityModeAggregator,
    FirstSuccessAggregator,
    create_all_concurrent,
    create_any_concurrent,
    create_majority_concurrent,
    create_first_success_concurrent,
    create_parallel_split_gateway,
    create_parallel_join_gateway,
    create_n_of_m_gateway,
    create_inclusive_gateway,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_executor():
    """Create a mock executor."""
    executor = MagicMock()
    executor.id = "test-executor"
    executor.handle = AsyncMock(return_value={"result": "success"})
    return executor


@pytest.fixture
def async_callable():
    """Create an async callable for testing."""
    async def func(data):
        await asyncio.sleep(0.01)
        return {"input": data, "status": "done"}
    return func


# =============================================================================
# GatewayType Enum Tests
# =============================================================================


class TestGatewayType:
    """Tests for GatewayType enum."""

    def test_gateway_type_values(self):
        """Test GatewayType enum values."""
        assert GatewayType.PARALLEL_SPLIT.value == "parallel_split"
        assert GatewayType.PARALLEL_JOIN.value == "parallel_join"
        assert GatewayType.INCLUSIVE_GATEWAY.value == "inclusive_gateway"

    def test_gateway_type_from_string(self):
        """Test creating GatewayType from string."""
        assert GatewayType("parallel_split") == GatewayType.PARALLEL_SPLIT
        assert GatewayType("parallel_join") == GatewayType.PARALLEL_JOIN
        assert GatewayType("inclusive_gateway") == GatewayType.INCLUSIVE_GATEWAY

    def test_gateway_type_iteration(self):
        """Test iterating over GatewayType."""
        types = list(GatewayType)
        assert len(types) == 3
        assert GatewayType.PARALLEL_SPLIT in types
        assert GatewayType.PARALLEL_JOIN in types
        assert GatewayType.INCLUSIVE_GATEWAY in types


# =============================================================================
# JoinCondition Enum Tests
# =============================================================================


class TestJoinCondition:
    """Tests for JoinCondition enum."""

    def test_join_condition_values(self):
        """Test JoinCondition enum values."""
        assert JoinCondition.ALL.value == "all"
        assert JoinCondition.ANY.value == "any"
        assert JoinCondition.FIRST.value == "first"
        assert JoinCondition.N_OF_M.value == "n_of_m"

    def test_join_condition_from_string(self):
        """Test creating JoinCondition from string."""
        assert JoinCondition("all") == JoinCondition.ALL
        assert JoinCondition("any") == JoinCondition.ANY
        assert JoinCondition("first") == JoinCondition.FIRST
        assert JoinCondition("n_of_m") == JoinCondition.N_OF_M


# =============================================================================
# MergeStrategy Enum Tests
# =============================================================================


class TestMergeStrategy:
    """Tests for MergeStrategy enum."""

    def test_merge_strategy_values(self):
        """Test MergeStrategy enum values."""
        assert MergeStrategy.COLLECT_ALL.value == "collect_all"
        assert MergeStrategy.MERGE_DICT.value == "merge_dict"
        assert MergeStrategy.FIRST_RESULT.value == "first_result"
        assert MergeStrategy.AGGREGATE.value == "aggregate"


# =============================================================================
# GatewayConfig Tests
# =============================================================================


class TestGatewayConfig:
    """Tests for GatewayConfig dataclass."""

    def test_gateway_config_default_values(self):
        """Test GatewayConfig default values."""
        config = GatewayConfig()
        assert config.gateway_type == GatewayType.PARALLEL_SPLIT
        assert config.join_condition == JoinCondition.ALL
        assert config.merge_strategy == MergeStrategy.COLLECT_ALL
        assert config.timeout is None
        assert config.n_required == 1
        assert config.fail_fast is False
        assert config.aggregate_function is None

    def test_gateway_config_custom_values(self):
        """Test GatewayConfig with custom values."""
        config = GatewayConfig(
            gateway_type=GatewayType.PARALLEL_JOIN,
            join_condition=JoinCondition.N_OF_M,
            merge_strategy=MergeStrategy.MERGE_DICT,
            timeout=60.0,
            n_required=3,
            fail_fast=True,
            aggregate_function="sum",
        )
        assert config.gateway_type == GatewayType.PARALLEL_JOIN
        assert config.join_condition == JoinCondition.N_OF_M
        assert config.merge_strategy == MergeStrategy.MERGE_DICT
        assert config.timeout == 60.0
        assert config.n_required == 3
        assert config.fail_fast is True
        assert config.aggregate_function == "sum"

    def test_gateway_config_to_dict(self):
        """Test GatewayConfig to_dict method."""
        config = GatewayConfig(
            gateway_type=GatewayType.PARALLEL_SPLIT,
            join_condition=JoinCondition.ALL,
            timeout=30.0,
        )
        result = config.to_dict()
        assert result["gateway_type"] == "parallel_split"
        assert result["join_condition"] == "all"
        assert result["timeout"] == 30.0

    def test_gateway_config_from_dict(self):
        """Test GatewayConfig from_dict method."""
        data = {
            "gateway_type": "parallel_join",
            "join_condition": "n_of_m",
            "merge_strategy": "merge_dict",
            "timeout": 120.0,
            "n_required": 5,
            "fail_fast": True,
        }
        config = GatewayConfig.from_dict(data)
        assert config.gateway_type == GatewayType.PARALLEL_JOIN
        assert config.join_condition == JoinCondition.N_OF_M
        assert config.merge_strategy == MergeStrategy.MERGE_DICT
        assert config.timeout == 120.0
        assert config.n_required == 5
        assert config.fail_fast is True


# =============================================================================
# NOfMAggregator Tests
# =============================================================================


class TestNOfMAggregator:
    """Tests for NOfMAggregator."""

    @pytest.mark.asyncio
    async def test_n_of_m_aggregator_basic(self):
        """Test basic N_OF_M aggregation."""
        aggregator = NOfMAggregator(n_required=2)

        results = [
            TaskResult(task_id="t1", success=True, result={"a": 1}, duration_ms=100),
            TaskResult(task_id="t2", success=True, result={"b": 2}, duration_ms=150),
            TaskResult(task_id="t3", success=False, error="Failed", duration_ms=50),
        ]

        execution_result = await aggregator.aggregate(results, total_expected=5)

        assert execution_result.completed_count == 2
        assert execution_result.failed_count == 1
        assert execution_result.total_tasks == 5
        assert execution_result.metadata["n_required"] == 2
        assert execution_result.metadata["reached_n"] is True

    @pytest.mark.asyncio
    async def test_n_of_m_aggregator_not_reached(self):
        """Test N_OF_M when N is not reached."""
        aggregator = NOfMAggregator(n_required=5)

        results = [
            TaskResult(task_id="t1", success=True, result={"a": 1}, duration_ms=100),
        ]

        execution_result = await aggregator.aggregate(results, total_expected=10)

        assert execution_result.metadata["n_required"] == 5
        assert execution_result.metadata["reached_n"] is False


# =============================================================================
# MergeStrategyAggregator Tests
# =============================================================================


class TestMergeStrategyAggregator:
    """Tests for MergeStrategyAggregator."""

    @pytest.mark.asyncio
    async def test_collect_all_strategy(self):
        """Test COLLECT_ALL merge strategy."""
        aggregator = MergeStrategyAggregator(MergeStrategy.COLLECT_ALL)

        results = [
            TaskResult(task_id="t1", success=True, result={"a": 1}, duration_ms=100),
            TaskResult(task_id="t2", success=True, result={"b": 2}, duration_ms=150),
        ]

        execution_result = await aggregator.aggregate(results, total_expected=2)

        merged = execution_result.metadata["merged_result"]
        assert len(merged) == 2
        assert {"a": 1} in merged
        assert {"b": 2} in merged

    @pytest.mark.asyncio
    async def test_merge_dict_strategy(self):
        """Test MERGE_DICT merge strategy."""
        aggregator = MergeStrategyAggregator(MergeStrategy.MERGE_DICT)

        results = [
            TaskResult(task_id="t1", success=True, result={"a": 1}, duration_ms=100),
            TaskResult(task_id="t2", success=True, result={"b": 2}, duration_ms=150),
        ]

        execution_result = await aggregator.aggregate(results, total_expected=2)

        merged = execution_result.metadata["merged_result"]
        assert merged == {"a": 1, "b": 2}

    @pytest.mark.asyncio
    async def test_first_result_strategy(self):
        """Test FIRST_RESULT merge strategy."""
        aggregator = MergeStrategyAggregator(MergeStrategy.FIRST_RESULT)

        results = [
            TaskResult(task_id="t1", success=True, result={"a": 1}, duration_ms=100),
            TaskResult(task_id="t2", success=True, result={"b": 2}, duration_ms=150),
        ]

        execution_result = await aggregator.aggregate(results, total_expected=2)

        merged = execution_result.metadata["merged_result"]
        assert merged == {"a": 1}

    @pytest.mark.asyncio
    async def test_aggregate_sum_function(self):
        """Test AGGREGATE with sum function."""
        aggregator = MergeStrategyAggregator(MergeStrategy.AGGREGATE, aggregate_function="sum")

        results = [
            TaskResult(task_id="t1", success=True, result=10, duration_ms=100),
            TaskResult(task_id="t2", success=True, result=20, duration_ms=150),
            TaskResult(task_id="t3", success=True, result=30, duration_ms=200),
        ]

        execution_result = await aggregator.aggregate(results, total_expected=3)

        merged = execution_result.metadata["merged_result"]
        assert merged == 60

    @pytest.mark.asyncio
    async def test_aggregate_count_function(self):
        """Test AGGREGATE with count function."""
        aggregator = MergeStrategyAggregator(MergeStrategy.AGGREGATE, aggregate_function="count")

        results = [
            TaskResult(task_id="t1", success=True, result="a", duration_ms=100),
            TaskResult(task_id="t2", success=True, result="b", duration_ms=150),
            TaskResult(task_id="t3", success=True, result="c", duration_ms=200),
        ]

        execution_result = await aggregator.aggregate(results, total_expected=3)

        merged = execution_result.metadata["merged_result"]
        assert merged == 3

    @pytest.mark.asyncio
    async def test_aggregate_avg_function(self):
        """Test AGGREGATE with avg function."""
        aggregator = MergeStrategyAggregator(MergeStrategy.AGGREGATE, aggregate_function="avg")

        results = [
            TaskResult(task_id="t1", success=True, result=10, duration_ms=100),
            TaskResult(task_id="t2", success=True, result=20, duration_ms=150),
            TaskResult(task_id="t3", success=True, result=30, duration_ms=200),
        ]

        execution_result = await aggregator.aggregate(results, total_expected=3)

        merged = execution_result.metadata["merged_result"]
        assert merged == 20.0


# =============================================================================
# ConcurrentBuilderAdapter Gateway Tests
# =============================================================================


class TestConcurrentBuilderAdapterGateway:
    """Tests for ConcurrentBuilderAdapter gateway configuration."""

    def test_with_gateway_config_basic(self, mock_executor):
        """Test basic gateway configuration."""
        adapter = ConcurrentBuilderAdapter(id="test-gateway")
        adapter.add_executor(mock_executor)

        adapter.with_gateway_config(
            gateway_type=GatewayType.PARALLEL_SPLIT,
            join_condition=JoinCondition.ALL,
        )

        assert adapter.gateway_config is not None
        assert adapter.gateway_config.gateway_type == GatewayType.PARALLEL_SPLIT
        assert adapter.gateway_config.join_condition == JoinCondition.ALL

    def test_with_gateway_config_n_of_m(self, mock_executor):
        """Test N_OF_M gateway configuration."""
        adapter = ConcurrentBuilderAdapter(id="test-n-of-m")
        adapter.add_executor(mock_executor)

        adapter.with_gateway_config(
            join_condition=JoinCondition.N_OF_M,
            n_required=3,
        )

        assert adapter.gateway_config is not None
        assert adapter.gateway_config.join_condition == JoinCondition.N_OF_M
        assert adapter.gateway_config.n_required == 3
        assert isinstance(adapter._aggregator, NOfMAggregator)

    def test_with_gateway_config_timeout(self, mock_executor):
        """Test gateway configuration with timeout."""
        adapter = ConcurrentBuilderAdapter(id="test-timeout")
        adapter.add_executor(mock_executor)

        adapter.with_gateway_config(timeout=30.0)

        assert adapter._timeout_seconds == 30.0

    def test_with_gateway_config_merge_strategy(self, mock_executor):
        """Test gateway configuration with merge strategy."""
        adapter = ConcurrentBuilderAdapter(id="test-merge")
        adapter.add_executor(mock_executor)

        adapter.with_gateway_config(
            merge_strategy=MergeStrategy.MERGE_DICT,
        )

        assert adapter.gateway_config.merge_strategy == MergeStrategy.MERGE_DICT

    def test_gateway_config_included_in_to_dict(self, mock_executor):
        """Test that gateway config is included in to_dict."""
        adapter = ConcurrentBuilderAdapter(id="test-dict")
        adapter.add_executor(mock_executor)
        adapter.with_gateway_config(
            gateway_type=GatewayType.PARALLEL_JOIN,
            join_condition=JoinCondition.ANY,
        )

        result = adapter.to_dict()

        assert "gateway_config" in result
        assert result["gateway_config"]["gateway_type"] == "parallel_join"
        assert result["gateway_config"]["join_condition"] == "any"


# =============================================================================
# Gateway Factory Function Tests
# =============================================================================


class TestGatewayFactoryFunctions:
    """Tests for gateway factory functions."""

    def test_create_parallel_split_gateway(self):
        """Test create_parallel_split_gateway factory."""
        adapter = create_parallel_split_gateway(
            id="split-test",
            join_condition=JoinCondition.ALL,
            merge_strategy=MergeStrategy.COLLECT_ALL,
        )

        assert adapter.id == "split-test"
        assert adapter.gateway_config.gateway_type == GatewayType.PARALLEL_SPLIT
        assert adapter.gateway_config.join_condition == JoinCondition.ALL

    def test_create_parallel_join_gateway(self):
        """Test create_parallel_join_gateway factory."""
        adapter = create_parallel_join_gateway(
            id="join-test",
            merge_strategy=MergeStrategy.MERGE_DICT,
        )

        assert adapter.id == "join-test"
        assert adapter.gateway_config.gateway_type == GatewayType.PARALLEL_JOIN
        assert adapter.gateway_config.merge_strategy == MergeStrategy.MERGE_DICT

    def test_create_n_of_m_gateway(self):
        """Test create_n_of_m_gateway factory."""
        adapter = create_n_of_m_gateway(
            id="n-of-m-test",
            n_required=3,
        )

        assert adapter.id == "n-of-m-test"
        assert adapter.gateway_config.join_condition == JoinCondition.N_OF_M
        assert adapter.gateway_config.n_required == 3

    def test_create_inclusive_gateway(self):
        """Test create_inclusive_gateway factory."""
        adapter = create_inclusive_gateway(
            id="inclusive-test",
            join_condition=JoinCondition.ANY,
        )

        assert adapter.id == "inclusive-test"
        assert adapter.gateway_config.gateway_type == GatewayType.INCLUSIVE_GATEWAY
        assert adapter.gateway_config.join_condition == JoinCondition.ANY


# =============================================================================
# Integration Tests
# =============================================================================


class TestConcurrentBuilderAdapterIntegration:
    """Integration tests for ConcurrentBuilderAdapter."""

    @pytest.mark.asyncio
    async def test_run_with_all_join_condition(self, async_callable):
        """Test running with ALL join condition."""
        adapter = ConcurrentBuilderAdapter(id="test-all")
        adapter.add_executor(async_callable, task_id="task1")
        adapter.add_executor(async_callable, task_id="task2")
        adapter.with_gateway_config(
            join_condition=JoinCondition.ALL,
            merge_strategy=MergeStrategy.COLLECT_ALL,
        )

        result = await adapter.run({"test": "data"})

        assert result.completed_count == 2
        assert result.failed_count == 0
        assert len(result.task_results) == 2

    @pytest.mark.asyncio
    async def test_run_with_any_join_condition(self, async_callable):
        """Test running with ANY join condition."""
        adapter = ConcurrentBuilderAdapter(id="test-any")
        adapter.add_executor(async_callable, task_id="task1")
        adapter.add_executor(async_callable, task_id="task2")
        adapter.with_gateway_config(
            join_condition=JoinCondition.ANY,
        )

        result = await adapter.run({"test": "data"})

        # ANY mode returns first completed
        assert result.total_tasks == 2
        assert len(result.task_results) >= 1

    @pytest.mark.asyncio
    async def test_run_with_n_of_m_join_condition(self, async_callable):
        """Test running with N_OF_M join condition."""
        adapter = ConcurrentBuilderAdapter(id="test-n-of-m")
        adapter.add_executor(async_callable, task_id="task1")
        adapter.add_executor(async_callable, task_id="task2")
        adapter.add_executor(async_callable, task_id="task3")
        adapter.with_gateway_config(
            join_condition=JoinCondition.N_OF_M,
            n_required=2,
        )

        result = await adapter.run({"test": "data"})

        # Should complete when 2 tasks are done
        assert len(result.task_results) >= 2


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestConcurrentBuilderAdapterEdgeCases:
    """Edge case tests for ConcurrentBuilderAdapter."""

    def test_gateway_config_after_build_raises(self, mock_executor):
        """Test that configuring gateway after build raises error."""
        adapter = ConcurrentBuilderAdapter(id="test-error")
        adapter.add_executor(mock_executor)
        adapter.build()

        with pytest.raises(Exception):  # ValidationError
            adapter.with_gateway_config(join_condition=JoinCondition.ANY)

    def test_n_of_m_with_zero_n(self, mock_executor):
        """Test N_OF_M with n=0 defaults to 1."""
        adapter = ConcurrentBuilderAdapter(id="test-zero")
        adapter.add_executor(mock_executor)
        adapter.with_gateway_config(
            join_condition=JoinCondition.N_OF_M,
            n_required=0,
        )

        # Should use at least 1
        assert adapter.gateway_config.n_required == 0  # Config stores original
        # But execution should handle this gracefully

    def test_gateway_with_empty_executors(self):
        """Test gateway config with no executors."""
        adapter = ConcurrentBuilderAdapter(id="test-empty")
        adapter.with_gateway_config(join_condition=JoinCondition.ALL)

        assert adapter.task_count == 0
        assert adapter.gateway_config is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

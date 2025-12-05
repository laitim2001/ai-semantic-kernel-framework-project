# =============================================================================
# IPA Platform - Parallel Gateway Unit Tests
# =============================================================================
# Sprint 7: Concurrent Execution Engine (Phase 2)
#
# Tests for parallel gateway executors including:
#   - JoinStrategy enumeration
#   - MergeStrategy enumeration
#   - ParallelGatewayConfig configuration
#   - ParallelForkGateway execution
#   - ParallelJoinGateway result merging
# =============================================================================

import asyncio
import pytest
from uuid import uuid4

from src.domain.workflows.executors.parallel_gateway import (
    JoinStrategy,
    MergeStrategy,
    ParallelGatewayConfig,
    ForkBranchConfig,
    ParallelForkGateway,
    ParallelJoinGateway,
)
from src.domain.workflows.executors.concurrent_state import (
    BranchStatus,
    ConcurrentStateManager,
    reset_state_manager,
)


# =============================================================================
# JoinStrategy Tests
# =============================================================================


class TestJoinStrategy:
    """Tests for JoinStrategy enum."""

    def test_strategy_values(self):
        """Test all strategy enum values."""
        assert JoinStrategy.WAIT_ALL.value == "wait_all"
        assert JoinStrategy.WAIT_ANY.value == "wait_any"
        assert JoinStrategy.WAIT_MAJORITY.value == "wait_majority"
        assert JoinStrategy.WAIT_N.value == "wait_n"

    def test_strategy_from_string(self):
        """Test creating strategy from string."""
        assert JoinStrategy("wait_all") == JoinStrategy.WAIT_ALL
        assert JoinStrategy("wait_any") == JoinStrategy.WAIT_ANY


# =============================================================================
# MergeStrategy Tests
# =============================================================================


class TestMergeStrategy:
    """Tests for MergeStrategy enum."""

    def test_strategy_values(self):
        """Test all strategy enum values."""
        assert MergeStrategy.COLLECT_ALL.value == "collect_all"
        assert MergeStrategy.MERGE_DICT.value == "merge_dict"
        assert MergeStrategy.FIRST_RESULT.value == "first_result"
        assert MergeStrategy.AGGREGATE.value == "aggregate"

    def test_strategy_from_string(self):
        """Test creating strategy from string."""
        assert MergeStrategy("collect_all") == MergeStrategy.COLLECT_ALL
        assert MergeStrategy("merge_dict") == MergeStrategy.MERGE_DICT


# =============================================================================
# ParallelGatewayConfig Tests
# =============================================================================


class TestParallelGatewayConfig:
    """Tests for ParallelGatewayConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ParallelGatewayConfig()

        assert config.max_concurrency == 10
        assert config.timeout == 300
        assert config.join_strategy == JoinStrategy.WAIT_ALL
        assert config.merge_strategy == MergeStrategy.COLLECT_ALL
        assert config.fail_fast is False

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ParallelGatewayConfig(
            max_concurrency=5,
            timeout=120,
            join_strategy=JoinStrategy.WAIT_MAJORITY,
            merge_strategy=MergeStrategy.MERGE_DICT,
            fail_fast=True,
        )

        assert config.max_concurrency == 5
        assert config.timeout == 120
        assert config.join_strategy == JoinStrategy.WAIT_MAJORITY
        assert config.fail_fast is True

    def test_to_dict(self):
        """Test serialization to dictionary."""
        config = ParallelGatewayConfig(
            max_concurrency=3,
            join_strategy=JoinStrategy.WAIT_N,
            wait_n_count=2,
        )

        data = config.to_dict()

        assert data["max_concurrency"] == 3
        assert data["join_strategy"] == "wait_n"
        assert data["wait_n_count"] == 2

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "max_concurrency": 8,
            "timeout": 60,
            "join_strategy": "wait_any",
            "merge_strategy": "first_result",
        }

        config = ParallelGatewayConfig.from_dict(data)

        assert config.max_concurrency == 8
        assert config.timeout == 60
        assert config.join_strategy == JoinStrategy.WAIT_ANY
        assert config.merge_strategy == MergeStrategy.FIRST_RESULT


# =============================================================================
# ForkBranchConfig Tests
# =============================================================================


class TestForkBranchConfig:
    """Tests for ForkBranchConfig dataclass."""

    def test_basic_initialization(self):
        """Test basic initialization."""
        config = ForkBranchConfig(
            id="branch-1",
            target_id="agent-001",
        )

        assert config.id == "branch-1"
        assert config.target_id == "agent-001"
        assert config.condition is None
        assert config.timeout is None

    def test_with_condition(self):
        """Test initialization with condition."""
        config = ForkBranchConfig(
            id="conditional-branch",
            target_id="agent-002",
            condition="input.type == 'urgent'",
            timeout=60,
        )

        assert config.condition == "input.type == 'urgent'"
        assert config.timeout == 60


# =============================================================================
# ParallelForkGateway Tests
# =============================================================================


class TestParallelForkGateway:
    """Tests for ParallelForkGateway class."""

    @pytest.fixture
    def state_manager(self):
        """Create fresh state manager for each test."""
        reset_state_manager()
        return ConcurrentStateManager()

    @pytest.fixture
    def sample_branches(self):
        """Create sample branch configurations."""
        return [
            ForkBranchConfig(id="analysis", target_id="analysis-agent"),
            ForkBranchConfig(id="validation", target_id="validation-agent"),
            ForkBranchConfig(id="enrichment", target_id="enrichment-agent"),
        ]

    @pytest.fixture
    def successful_executor(self):
        """Create executor function that always succeeds."""
        async def executor(target_id: str, input_data: dict):
            await asyncio.sleep(0.01)
            return {"target": target_id, "status": "completed", **input_data}
        return executor

    def test_initialization(self, state_manager, sample_branches):
        """Test gateway initialization."""
        exec_id = uuid4()
        fork = ParallelForkGateway(
            id="fork-1",
            execution_id=exec_id,
            branches=sample_branches,
            state_manager=state_manager,
        )

        assert fork.id == "fork-1"
        assert fork.execution_id == exec_id
        assert len(fork.branches) == 3

    @pytest.mark.asyncio
    async def test_execute_all_branches(self, state_manager, sample_branches, successful_executor):
        """Test executing all branches."""
        exec_id = uuid4()
        fork = ParallelForkGateway(
            id="fork-test",
            execution_id=exec_id,
            branches=sample_branches,
            state_manager=state_manager,
        )

        result = await fork.execute(
            input_data={"message": "test"},
            branch_executor=successful_executor,
        )

        assert result["fork_gateway_id"] == "fork-test"
        assert result["branches_started"] == 3

        # Check state
        state = state_manager.get_state(exec_id)
        assert state is not None
        assert state.completed_count == 3

    @pytest.mark.asyncio
    async def test_execute_with_conditional_branches(self, state_manager, successful_executor):
        """Test executing with conditional branches."""
        branches = [
            ForkBranchConfig(id="always", target_id="agent-1"),
            ForkBranchConfig(id="conditional", target_id="agent-2", condition="input.urgent"),
            ForkBranchConfig(id="never", target_id="agent-3", condition="false"),
        ]

        exec_id = uuid4()
        fork = ParallelForkGateway(
            id="fork-conditional",
            execution_id=exec_id,
            branches=branches,
            state_manager=state_manager,
        )

        # With urgent=True, should execute "always" and "conditional"
        result = await fork.execute(
            input_data={"urgent": True},
            branch_executor=successful_executor,
        )

        # "always" always runs, "conditional" runs when urgent=True, "never" never runs
        assert result["branches_started"] >= 1

    @pytest.mark.asyncio
    async def test_execute_no_matching_branches(self, state_manager):
        """Test when no branches match conditions."""
        branches = [
            ForkBranchConfig(id="never", target_id="agent-1", condition="false"),
        ]

        exec_id = uuid4()
        fork = ParallelForkGateway(
            id="fork-none",
            execution_id=exec_id,
            branches=branches,
            state_manager=state_manager,
        )

        result = await fork.execute(
            input_data={},
            branch_executor=lambda t, d: None,
        )

        assert result["branches_started"] == 0
        assert "error" in result

    @pytest.mark.asyncio
    async def test_execute_with_failures(self, state_manager, sample_branches):
        """Test handling branch failures."""
        fail_count = {"count": 0}

        async def failing_executor(target_id: str, input_data: dict):
            fail_count["count"] += 1
            if target_id == "validation-agent":
                raise Exception("Validation failed")
            await asyncio.sleep(0.01)
            return {"status": "ok"}

        exec_id = uuid4()
        fork = ParallelForkGateway(
            id="fork-fail",
            execution_id=exec_id,
            branches=sample_branches,
            state_manager=state_manager,
        )

        result = await fork.execute(
            input_data={},
            branch_executor=failing_executor,
        )

        state = state_manager.get_state(exec_id)
        assert state.completed_count == 2
        assert state.failed_count == 1


# =============================================================================
# ParallelJoinGateway Tests
# =============================================================================


class TestParallelJoinGateway:
    """Tests for ParallelJoinGateway class."""

    @pytest.fixture
    def state_manager(self):
        """Create fresh state manager for each test."""
        reset_state_manager()
        return ConcurrentStateManager()

    def test_initialization(self, state_manager):
        """Test gateway initialization."""
        exec_id = uuid4()
        join = ParallelJoinGateway(
            id="join-1",
            execution_id=exec_id,
            expected_branches=["b1", "b2", "b3"],
            state_manager=state_manager,
        )

        assert join.id == "join-1"
        assert join.execution_id == exec_id

    @pytest.mark.asyncio
    async def test_wait_for_all_branches(self, state_manager):
        """Test waiting for all branches."""
        exec_id = uuid4()

        # Create state with branches
        state_manager.create_state(
            execution_id=exec_id,
            parent_node_id="fork",
            branch_configs=[
                {"id": "b1", "executor_id": "a1"},
                {"id": "b2", "executor_id": "a2"},
            ],
        )

        join = ParallelJoinGateway(
            id="join-test",
            execution_id=exec_id,
            expected_branches=["b1", "b2"],
            config=ParallelGatewayConfig(join_strategy=JoinStrategy.WAIT_ALL),
            state_manager=state_manager,
        )

        # Complete branches asynchronously
        async def complete_branches():
            await asyncio.sleep(0.05)
            state_manager.complete_branch(exec_id, "b1", result={"data": "1"})
            await asyncio.sleep(0.05)
            state_manager.complete_branch(exec_id, "b2", result={"data": "2"})

        asyncio.create_task(complete_branches())

        await join.wait_for_branches(poll_interval=0.02, timeout=2)

        output = join.get_output()
        assert output["join_completed"] is True
        assert output["branches_completed"] == 2

    @pytest.mark.asyncio
    async def test_wait_for_any_branch(self, state_manager):
        """Test waiting for any branch."""
        exec_id = uuid4()

        state_manager.create_state(
            execution_id=exec_id,
            parent_node_id="fork",
            branch_configs=[
                {"id": "b1", "executor_id": "a1"},
                {"id": "b2", "executor_id": "a2"},
                {"id": "b3", "executor_id": "a3"},
            ],
        )

        join = ParallelJoinGateway(
            id="join-any",
            execution_id=exec_id,
            expected_branches=["b1", "b2", "b3"],
            config=ParallelGatewayConfig(join_strategy=JoinStrategy.WAIT_ANY),
            state_manager=state_manager,
        )

        # Complete just one branch
        async def complete_one():
            await asyncio.sleep(0.05)
            state_manager.complete_branch(exec_id, "b2", result="first")

        asyncio.create_task(complete_one())

        await join.wait_for_branches(poll_interval=0.02, timeout=2)

        output = join.get_output()
        assert output["join_completed"] is True
        assert output["branches_completed"] >= 1

    @pytest.mark.asyncio
    async def test_receive_result(self, state_manager):
        """Test receiving results directly."""
        exec_id = uuid4()

        state_manager.create_state(
            execution_id=exec_id,
            parent_node_id="fork",
            branch_configs=[
                {"id": "b1", "executor_id": "a1"},
                {"id": "b2", "executor_id": "a2"},
            ],
        )

        join = ParallelJoinGateway(
            id="join-receive",
            execution_id=exec_id,
            expected_branches=["b1", "b2"],
            config=ParallelGatewayConfig(join_strategy=JoinStrategy.WAIT_ALL),
            state_manager=state_manager,
        )

        # First result
        completed = await join.receive_result("b1", result={"output": "a"})
        assert completed is False

        # Second result completes join
        completed = await join.receive_result("b2", result={"output": "b"})
        assert completed is True

    def test_merge_collect_all(self, state_manager):
        """Test COLLECT_ALL merge strategy."""
        exec_id = uuid4()

        state_manager.create_state(
            execution_id=exec_id,
            parent_node_id="fork",
            branch_configs=[
                {"id": "b1", "executor_id": "a1"},
                {"id": "b2", "executor_id": "a2"},
            ],
        )

        state_manager.complete_branch(exec_id, "b1", result="result1")
        state_manager.complete_branch(exec_id, "b2", result="result2")

        join = ParallelJoinGateway(
            id="join-collect",
            execution_id=exec_id,
            expected_branches=["b1", "b2"],
            config=ParallelGatewayConfig(merge_strategy=MergeStrategy.COLLECT_ALL),
            state_manager=state_manager,
        )

        join._join_completed = True
        join._merged_result = join._merge_results()

        output = join.get_output()
        assert isinstance(output["merged_result"], list)
        assert len(output["merged_result"]) == 2

    def test_merge_dict(self, state_manager):
        """Test MERGE_DICT merge strategy."""
        exec_id = uuid4()

        state_manager.create_state(
            execution_id=exec_id,
            parent_node_id="fork",
            branch_configs=[
                {"id": "b1", "executor_id": "a1"},
                {"id": "b2", "executor_id": "a2"},
            ],
        )

        state_manager.complete_branch(exec_id, "b1", result={"key1": "value1"})
        state_manager.complete_branch(exec_id, "b2", result={"key2": "value2"})

        join = ParallelJoinGateway(
            id="join-merge",
            execution_id=exec_id,
            expected_branches=["b1", "b2"],
            config=ParallelGatewayConfig(merge_strategy=MergeStrategy.MERGE_DICT),
            state_manager=state_manager,
        )

        result = join._merge_results()

        assert isinstance(result, dict)
        assert result["key1"] == "value1"
        assert result["key2"] == "value2"

    def test_merge_first_result(self, state_manager):
        """Test FIRST_RESULT merge strategy."""
        exec_id = uuid4()

        state_manager.create_state(
            execution_id=exec_id,
            parent_node_id="fork",
            branch_configs=[
                {"id": "b1", "executor_id": "a1"},
                {"id": "b2", "executor_id": "a2"},
            ],
        )

        state_manager.complete_branch(exec_id, "b1", result="first")
        state_manager.complete_branch(exec_id, "b2", result="second")

        join = ParallelJoinGateway(
            id="join-first",
            execution_id=exec_id,
            expected_branches=["b1", "b2"],
            config=ParallelGatewayConfig(merge_strategy=MergeStrategy.FIRST_RESULT),
            state_manager=state_manager,
        )

        result = join._merge_results()
        assert result in ["first", "second"]  # Dict order may vary

    def test_aggregate_sum(self, state_manager):
        """Test AGGREGATE with sum function."""
        exec_id = uuid4()

        state_manager.create_state(
            execution_id=exec_id,
            parent_node_id="fork",
            branch_configs=[
                {"id": "b1", "executor_id": "a1"},
                {"id": "b2", "executor_id": "a2"},
                {"id": "b3", "executor_id": "a3"},
            ],
        )

        state_manager.complete_branch(exec_id, "b1", result=10)
        state_manager.complete_branch(exec_id, "b2", result=20)
        state_manager.complete_branch(exec_id, "b3", result=30)

        join = ParallelJoinGateway(
            id="join-sum",
            execution_id=exec_id,
            expected_branches=["b1", "b2", "b3"],
            config=ParallelGatewayConfig(
                merge_strategy=MergeStrategy.AGGREGATE,
                aggregate_function="sum",
            ),
            state_manager=state_manager,
        )

        result = join._merge_results()
        assert result == 60

    def test_aggregate_avg(self, state_manager):
        """Test AGGREGATE with avg function."""
        exec_id = uuid4()

        state_manager.create_state(
            execution_id=exec_id,
            parent_node_id="fork",
            branch_configs=[
                {"id": "b1", "executor_id": "a1"},
                {"id": "b2", "executor_id": "a2"},
            ],
        )

        state_manager.complete_branch(exec_id, "b1", result=10)
        state_manager.complete_branch(exec_id, "b2", result=30)

        join = ParallelJoinGateway(
            id="join-avg",
            execution_id=exec_id,
            expected_branches=["b1", "b2"],
            config=ParallelGatewayConfig(
                merge_strategy=MergeStrategy.AGGREGATE,
                aggregate_function="avg",
            ),
            state_manager=state_manager,
        )

        result = join._merge_results()
        assert result == 20.0

    def test_to_dict(self, state_manager):
        """Test serialization to dictionary."""
        exec_id = uuid4()
        join = ParallelJoinGateway(
            id="join-dict",
            execution_id=exec_id,
            expected_branches=["b1", "b2"],
            config=ParallelGatewayConfig(join_strategy=JoinStrategy.WAIT_MAJORITY),
            state_manager=state_manager,
        )

        data = join.to_dict()

        assert data["id"] == "join-dict"
        assert data["config"]["join_strategy"] == "wait_majority"
        assert len(data["expected_branches"]) == 2

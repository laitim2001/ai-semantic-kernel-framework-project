# =============================================================================
# IPA Platform - Parallel Gateway Executors
# =============================================================================
# Sprint 7: Concurrent Execution Engine
# Phase 2 Feature: P2-F2 (Enhanced Gateway)
#
# Parallel gateway executors for fork/join patterns:
#   - JoinStrategy: Strategy for waiting on parallel branches
#   - MergeStrategy: Strategy for combining branch results
#   - ParallelGatewayConfig: Configuration for parallel gateways
#   - ParallelForkGateway: Fork execution into parallel branches
#   - ParallelJoinGateway: Join parallel branches and merge results
#
# Implements the Fork-Join pattern for parallel workflow execution.
# =============================================================================

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

from src.domain.workflows.executors.concurrent_state import (
    BranchStatus,
    ConcurrentExecutionState,
    ConcurrentStateManager,
    ParallelBranch,
    get_state_manager,
)

logger = logging.getLogger(__name__)


class JoinStrategy(str, Enum):
    """
    Strategy for waiting on parallel branches at a join gateway.

    Determines when the join gateway should proceed with execution.

    Values:
        WAIT_ALL: Wait for all branches to complete
        WAIT_ANY: Proceed when any single branch completes
        WAIT_MAJORITY: Proceed when majority of branches complete
        WAIT_N: Proceed when N branches complete (configurable)
    """

    WAIT_ALL = "wait_all"
    WAIT_ANY = "wait_any"
    WAIT_MAJORITY = "wait_majority"
    WAIT_N = "wait_n"


class MergeStrategy(str, Enum):
    """
    Strategy for merging results from parallel branches.

    Determines how to combine the outputs from multiple branches.

    Values:
        COLLECT_ALL: Collect all results into a list
        MERGE_DICT: Merge all dict results into one dict
        FIRST_RESULT: Use only the first completed result
        AGGREGATE: Apply custom aggregation function
    """

    COLLECT_ALL = "collect_all"
    MERGE_DICT = "merge_dict"
    FIRST_RESULT = "first_result"
    AGGREGATE = "aggregate"


@dataclass
class ParallelGatewayConfig:
    """
    Configuration for parallel gateway execution.

    Controls concurrency, timeouts, and merge behavior.

    Attributes:
        max_concurrency: Maximum parallel branches (default: 10)
        timeout: Global timeout in seconds (default: 300)
        join_strategy: How to wait for branches (default: WAIT_ALL)
        merge_strategy: How to merge results (default: COLLECT_ALL)
        wait_n_count: Number of branches to wait for when using WAIT_N
        aggregate_function: Name of aggregation function for AGGREGATE strategy
        fail_fast: Stop all branches on first failure (default: False)
        retry_failed: Retry failed branches (default: False)
        retry_count: Maximum retry attempts (default: 0)

    Example:
        config = ParallelGatewayConfig(
            max_concurrency=5,
            timeout=120,
            join_strategy=JoinStrategy.WAIT_MAJORITY,
            merge_strategy=MergeStrategy.MERGE_DICT,
        )
    """

    max_concurrency: int = 10
    timeout: int = 300
    join_strategy: JoinStrategy = JoinStrategy.WAIT_ALL
    merge_strategy: MergeStrategy = MergeStrategy.COLLECT_ALL
    wait_n_count: int = 1
    aggregate_function: Optional[str] = None
    fail_fast: bool = False
    retry_failed: bool = False
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "max_concurrency": self.max_concurrency,
            "timeout": self.timeout,
            "join_strategy": self.join_strategy.value,
            "merge_strategy": self.merge_strategy.value,
            "wait_n_count": self.wait_n_count,
            "aggregate_function": self.aggregate_function,
            "fail_fast": self.fail_fast,
            "retry_failed": self.retry_failed,
            "retry_count": self.retry_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ParallelGatewayConfig":
        """Create configuration from dictionary."""
        return cls(
            max_concurrency=data.get("max_concurrency", 10),
            timeout=data.get("timeout", 300),
            join_strategy=JoinStrategy(data.get("join_strategy", "wait_all")),
            merge_strategy=MergeStrategy(data.get("merge_strategy", "collect_all")),
            wait_n_count=data.get("wait_n_count", 1),
            aggregate_function=data.get("aggregate_function"),
            fail_fast=data.get("fail_fast", False),
            retry_failed=data.get("retry_failed", False),
            retry_count=data.get("retry_count", 0),
        )


@dataclass
class ForkBranchConfig:
    """
    Configuration for a single fork branch.

    Attributes:
        id: Unique branch identifier
        target_id: Target executor/agent ID
        input_transform: Optional input transformation expression
        condition: Optional condition for branch activation
        timeout: Branch-specific timeout (overrides gateway default)
    """

    id: str
    target_id: str
    input_transform: Optional[str] = None
    condition: Optional[str] = None
    timeout: Optional[int] = None


class ParallelForkGateway:
    """
    Parallel fork gateway for splitting execution into multiple branches.

    Receives input and distributes it to multiple parallel branches.
    Each branch executes independently and reports results to a join gateway.

    Features:
        - Conditional branch activation
        - Input transformation per branch
        - Concurrency control via semaphore
        - State tracking via ConcurrentStateManager

    Lifecycle:
        1. __init__() - Configure fork gateway
        2. execute() - Fork input to all branches
        3. Branches execute in parallel
        4. Results collected by ParallelJoinGateway

    Example:
        branches = [
            ForkBranchConfig(id="analysis", target_id="analysis-agent"),
            ForkBranchConfig(id="validation", target_id="validation-agent"),
            ForkBranchConfig(id="enrichment", target_id="enrichment-agent"),
        ]

        fork = ParallelForkGateway(
            id="fork-1",
            execution_id=UUID("..."),
            branches=branches,
            config=ParallelGatewayConfig(max_concurrency=5),
        )

        await fork.execute(
            input_data={"document": "report.pdf"},
            branch_executor=my_executor_fn,
        )
    """

    def __init__(
        self,
        id: str,
        execution_id: UUID,
        branches: List[ForkBranchConfig],
        config: Optional[ParallelGatewayConfig] = None,
        state_manager: Optional[ConcurrentStateManager] = None,
    ):
        """
        Initialize ParallelForkGateway.

        Args:
            id: Unique gateway identifier
            execution_id: Parent workflow execution ID
            branches: List of branch configurations
            config: Gateway configuration
            state_manager: State manager (uses global singleton if None)
        """
        self._id = id
        self._execution_id = execution_id
        self._branches = branches
        self._config = config or ParallelGatewayConfig()
        self._state_manager = state_manager or get_state_manager()
        self._state: Optional[ConcurrentExecutionState] = None

        logger.info(
            f"ParallelForkGateway initialized: id={id}, "
            f"branches={len(branches)}, execution={execution_id}"
        )

    @property
    def id(self) -> str:
        """Get gateway ID."""
        return self._id

    @property
    def execution_id(self) -> UUID:
        """Get execution ID."""
        return self._execution_id

    @property
    def branches(self) -> List[ForkBranchConfig]:
        """Get branch configurations."""
        return self._branches

    async def execute(
        self,
        input_data: Dict[str, Any],
        branch_executor: Callable[[str, Dict[str, Any]], Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute fork, distributing input to all branches.

        Creates execution state, starts all branches in parallel,
        and waits for completion based on configuration.

        Args:
            input_data: Input data to distribute to branches
            branch_executor: Async function to execute each branch
                Signature: async def executor(target_id: str, input_data: dict) -> Any
            context: Optional execution context

        Returns:
            Dictionary containing:
                - fork_gateway_id: This gateway's ID
                - execution_id: Execution UUID
                - branches_started: Number of branches started
                - state_id: State tracking ID

        Example:
            async def my_executor(target_id: str, data: dict) -> dict:
                return await agent_service.execute(target_id, data)

            result = await fork.execute(
                input_data={"message": "process this"},
                branch_executor=my_executor,
            )
        """
        logger.info(f"Executing fork gateway {self._id} with {len(self._branches)} branches")

        # Filter active branches based on conditions
        active_branches = self._get_active_branches(input_data, context)

        if not active_branches:
            logger.warning(f"No active branches for fork gateway {self._id}")
            return {
                "fork_gateway_id": self._id,
                "execution_id": str(self._execution_id),
                "branches_started": 0,
                "error": "No branches matched conditions",
            }

        # Create execution state
        self._state = self._state_manager.create_state(
            execution_id=self._execution_id,
            parent_node_id=self._id,
            branch_configs=[
                {"id": branch.id, "executor_id": branch.target_id}
                for branch in active_branches
            ],
            mode="fork",
        )

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self._config.max_concurrency)

        async def execute_branch(branch: ForkBranchConfig) -> None:
            """Execute a single branch with semaphore control."""
            async with semaphore:
                branch_input = self._transform_input(branch, input_data)
                branch_timeout = branch.timeout or self._config.timeout

                # Mark branch as started
                self._state_manager.start_branch(self._execution_id, branch.id)

                try:
                    result = await asyncio.wait_for(
                        branch_executor(branch.target_id, branch_input),
                        timeout=branch_timeout,
                    )

                    self._state_manager.complete_branch(
                        self._execution_id, branch.id, result=result
                    )

                    logger.debug(f"Branch {branch.id} completed successfully")

                except asyncio.TimeoutError:
                    self._state_manager.timeout_branch(self._execution_id, branch.id)
                    logger.warning(f"Branch {branch.id} timed out")

                    if self._config.fail_fast:
                        raise

                except Exception as e:
                    self._state_manager.fail_branch(
                        self._execution_id, branch.id, error=str(e)
                    )
                    logger.error(f"Branch {branch.id} failed: {e}")

                    if self._config.fail_fast:
                        raise

        # Execute all branches in parallel
        try:
            await asyncio.gather(
                *[execute_branch(branch) for branch in active_branches],
                return_exceptions=not self._config.fail_fast,
            )
        except Exception as e:
            if self._config.fail_fast:
                # Cancel remaining branches
                self._state_manager.cancel_all_branches(self._execution_id)
                raise

        return {
            "fork_gateway_id": self._id,
            "execution_id": str(self._execution_id),
            "branches_started": len(active_branches),
            "state_id": str(self._execution_id),
        }

    def _get_active_branches(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> List[ForkBranchConfig]:
        """Get branches that should be activated based on conditions."""
        active = []
        eval_context = {**(context or {}), "input": input_data}

        for branch in self._branches:
            if branch.condition:
                try:
                    # Simple condition evaluation (for demo; production should use safer eval)
                    if self._evaluate_condition(branch.condition, eval_context):
                        active.append(branch)
                except Exception as e:
                    logger.warning(
                        f"Failed to evaluate condition for branch {branch.id}: {e}"
                    )
            else:
                # No condition means always active
                active.append(branch)

        return active

    def _evaluate_condition(
        self, condition: str, context: Dict[str, Any]
    ) -> bool:
        """
        Evaluate a condition expression.

        Note: This is a simplified implementation. Production code should
        use a proper expression evaluator for security.
        """
        # Simple boolean check for common patterns
        if condition.lower() == "true":
            return True
        if condition.lower() == "false":
            return False

        # Check for key existence patterns like "input.field"
        if "." in condition:
            parts = condition.split(".")
            value = context
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return False
            return bool(value)

        return True  # Default to true if we can't parse

    def _transform_input(
        self,
        branch: ForkBranchConfig,
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Transform input data for a specific branch."""
        if not branch.input_transform:
            return input_data

        # Simple key extraction for now
        # Production should use proper expression evaluation
        if branch.input_transform.startswith("input."):
            key = branch.input_transform[6:]  # Remove "input." prefix
            if key in input_data:
                return {key: input_data[key]}

        return input_data


class ParallelJoinGateway:
    """
    Parallel join gateway for collecting and merging branch results.

    Waits for parallel branches to complete according to join strategy,
    then merges results according to merge strategy.

    Features:
        - Multiple join strategies (ALL, ANY, MAJORITY, N)
        - Multiple merge strategies (COLLECT, MERGE_DICT, FIRST, AGGREGATE)
        - Built-in aggregation functions (sum, count, concat)
        - Progress tracking and timeout handling

    Lifecycle:
        1. __init__() - Configure join gateway
        2. wait_for_branches() - Wait until join condition is met
        3. merge_results() - Combine results according to strategy
        4. get_output() - Get final merged output

    Example:
        join = ParallelJoinGateway(
            id="join-1",
            execution_id=UUID("..."),
            expected_branches=["analysis", "validation", "enrichment"],
            config=ParallelGatewayConfig(
                join_strategy=JoinStrategy.WAIT_ALL,
                merge_strategy=MergeStrategy.MERGE_DICT,
            ),
        )

        await join.wait_for_branches()
        output = join.get_output()
    """

    def __init__(
        self,
        id: str,
        execution_id: UUID,
        expected_branches: List[str],
        config: Optional[ParallelGatewayConfig] = None,
        state_manager: Optional[ConcurrentStateManager] = None,
    ):
        """
        Initialize ParallelJoinGateway.

        Args:
            id: Unique gateway identifier
            execution_id: Parent workflow execution ID
            expected_branches: List of branch IDs to wait for
            config: Gateway configuration
            state_manager: State manager (uses global singleton if None)
        """
        self._id = id
        self._execution_id = execution_id
        self._expected_branches = expected_branches
        self._config = config or ParallelGatewayConfig()
        self._state_manager = state_manager or get_state_manager()
        self._merged_result: Optional[Any] = None
        self._join_completed = False

        logger.info(
            f"ParallelJoinGateway initialized: id={id}, "
            f"expected_branches={len(expected_branches)}, execution={execution_id}"
        )

    @property
    def id(self) -> str:
        """Get gateway ID."""
        return self._id

    @property
    def execution_id(self) -> UUID:
        """Get execution ID."""
        return self._execution_id

    async def wait_for_branches(
        self,
        poll_interval: float = 0.5,
        timeout: Optional[int] = None,
    ) -> bool:
        """
        Wait for branches to complete according to join strategy.

        Polls state manager until join condition is satisfied or timeout.

        Args:
            poll_interval: Seconds between state checks
            timeout: Override default timeout

        Returns:
            True if join condition was satisfied, False on timeout

        Raises:
            TimeoutError: If timeout exceeded
        """
        wait_timeout = timeout or self._config.timeout
        start_time = datetime.utcnow()

        logger.info(
            f"Join gateway {self._id} waiting for branches, "
            f"strategy={self._config.join_strategy.value}"
        )

        while True:
            # Check elapsed time
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed > wait_timeout:
                logger.warning(f"Join gateway {self._id} timed out after {elapsed}s")
                raise TimeoutError(f"Join gateway timeout after {wait_timeout}s")

            # Check if join condition is met
            if self._check_join_condition():
                self._join_completed = True
                self._merged_result = self._merge_results()
                logger.info(f"Join gateway {self._id} condition satisfied")
                return True

            await asyncio.sleep(poll_interval)

    def _check_join_condition(self) -> bool:
        """Check if join condition is satisfied."""
        state = self._state_manager.get_state(self._execution_id)
        if not state:
            return False

        # Count terminal branches
        terminal_count = sum(
            1 for bid in self._expected_branches
            if (branch := state.get_branch(bid)) and branch.is_terminal
        )

        total = len(self._expected_branches)

        if self._config.join_strategy == JoinStrategy.WAIT_ALL:
            return terminal_count >= total

        elif self._config.join_strategy == JoinStrategy.WAIT_ANY:
            return terminal_count >= 1

        elif self._config.join_strategy == JoinStrategy.WAIT_MAJORITY:
            return terminal_count > total // 2

        elif self._config.join_strategy == JoinStrategy.WAIT_N:
            return terminal_count >= self._config.wait_n_count

        return terminal_count >= total

    def _merge_results(self) -> Any:
        """Merge results according to merge strategy."""
        state = self._state_manager.get_state(self._execution_id)
        if not state:
            return None

        # Collect results from completed branches
        results: Dict[str, Any] = {}
        for branch_id in self._expected_branches:
            branch = state.get_branch(branch_id)
            if branch and branch.is_successful:
                results[branch_id] = branch.result

        if not results:
            return None

        # Apply merge strategy
        if self._config.merge_strategy == MergeStrategy.COLLECT_ALL:
            return list(results.values())

        elif self._config.merge_strategy == MergeStrategy.MERGE_DICT:
            merged = {}
            for result in results.values():
                if isinstance(result, dict):
                    merged.update(result)
            return merged

        elif self._config.merge_strategy == MergeStrategy.FIRST_RESULT:
            return next(iter(results.values()), None)

        elif self._config.merge_strategy == MergeStrategy.AGGREGATE:
            return self._apply_aggregation(results)

        return list(results.values())

    def _apply_aggregation(self, results: Dict[str, Any]) -> Any:
        """Apply custom aggregation function."""
        func_name = self._config.aggregate_function

        if func_name == "sum":
            return sum(
                v for v in results.values()
                if isinstance(v, (int, float))
            )

        elif func_name == "count":
            return len(results)

        elif func_name == "concat":
            return "".join(str(v) for v in results.values())

        elif func_name == "max":
            numeric = [v for v in results.values() if isinstance(v, (int, float))]
            return max(numeric) if numeric else None

        elif func_name == "min":
            numeric = [v for v in results.values() if isinstance(v, (int, float))]
            return min(numeric) if numeric else None

        elif func_name == "avg":
            numeric = [v for v in results.values() if isinstance(v, (int, float))]
            return sum(numeric) / len(numeric) if numeric else None

        else:
            # Unknown function, return list
            return list(results.values())

    def get_output(self) -> Dict[str, Any]:
        """
        Get join gateway output.

        Returns:
            Dictionary containing:
                - join_gateway_id: This gateway's ID
                - execution_id: Execution UUID
                - join_strategy: Strategy used
                - merge_strategy: Strategy used
                - merged_result: Combined results
                - branches_completed: Number of completed branches
                - branches_failed: Number of failed branches
        """
        state = self._state_manager.get_state(self._execution_id)

        completed = 0
        failed = 0
        if state:
            for branch_id in self._expected_branches:
                branch = state.get_branch(branch_id)
                if branch:
                    if branch.is_successful:
                        completed += 1
                    elif branch.is_terminal:
                        failed += 1

        return {
            "join_gateway_id": self._id,
            "execution_id": str(self._execution_id),
            "join_strategy": self._config.join_strategy.value,
            "merge_strategy": self._config.merge_strategy.value,
            "merged_result": self._merged_result,
            "branches_completed": completed,
            "branches_failed": failed,
            "join_completed": self._join_completed,
        }

    async def receive_result(
        self,
        branch_id: str,
        result: Any,
        success: bool = True,
        error: Optional[str] = None,
    ) -> bool:
        """
        Receive a result from a branch.

        Alternative to polling-based wait_for_branches when using
        push-based result delivery.

        Args:
            branch_id: Branch identifier
            result: Branch result
            success: Whether branch succeeded
            error: Error message if failed

        Returns:
            True if join condition is now met
        """
        if success:
            self._state_manager.complete_branch(
                self._execution_id, branch_id, result=result
            )
        else:
            self._state_manager.fail_branch(
                self._execution_id, branch_id, error=error or "Unknown error"
            )

        if self._check_join_condition():
            self._join_completed = True
            self._merged_result = self._merge_results()
            return True

        return False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize gateway state to dictionary."""
        return {
            "id": self._id,
            "execution_id": str(self._execution_id),
            "expected_branches": self._expected_branches,
            "config": self._config.to_dict(),
            "join_completed": self._join_completed,
            "merged_result": self._merged_result,
        }

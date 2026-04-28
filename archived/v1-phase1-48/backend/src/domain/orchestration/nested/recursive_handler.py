# =============================================================================
# IPA Platform - Recursive Pattern Handler
# =============================================================================
# Sprint 11: S11-3 RecursivePatternHandler
#
# Handles recursive workflow execution with:
# - Multiple recursion strategies (depth-first, breadth-first, parallel)
# - Termination condition detection
# - Memoization for optimization
# - Convergence detection
# - Stack overflow protection
# =============================================================================

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable, List, Union
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum
import asyncio
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================


class RecursionStrategy(str, Enum):
    """
    遞歸策略

    Strategies for recursive execution:
    - DEPTH_FIRST: Process deeply before siblings
    - BREADTH_FIRST: Process siblings before going deep
    - PARALLEL: Process branches in parallel
    """
    DEPTH_FIRST = "depth_first"
    BREADTH_FIRST = "breadth_first"
    PARALLEL = "parallel"


class TerminationType(str, Enum):
    """
    終止類型

    Types of termination conditions:
    - CONDITION: Custom condition met
    - MAX_DEPTH: Maximum depth reached
    - MAX_ITERATIONS: Maximum iterations reached
    - TIMEOUT: Execution timed out
    - CONVERGENCE: Results have converged
    - USER_ABORT: User requested abort
    """
    CONDITION = "condition"
    MAX_DEPTH = "max_depth"
    MAX_ITERATIONS = "max_iterations"
    TIMEOUT = "timeout"
    CONVERGENCE = "convergence"
    USER_ABORT = "user_abort"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class RecursionConfig:
    """
    遞歸配置

    Configuration for recursive execution including limits,
    strategy, termination conditions, and optimization settings.
    """
    max_depth: int = 10
    max_iterations: int = 100
    timeout_seconds: int = 300
    strategy: RecursionStrategy = RecursionStrategy.DEPTH_FIRST
    termination_condition: Optional[Callable[[Dict[str, Any], int], bool]] = None
    convergence_threshold: Optional[float] = None
    memoization: bool = True
    track_history: bool = True
    max_history_size: int = 1000

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "max_depth": self.max_depth,
            "max_iterations": self.max_iterations,
            "timeout_seconds": self.timeout_seconds,
            "strategy": self.strategy.value,
            "convergence_threshold": self.convergence_threshold,
            "memoization": self.memoization,
            "track_history": self.track_history,
            "max_history_size": self.max_history_size,
        }


@dataclass
class RecursionState:
    """
    遞歸狀態

    Tracks the state of recursive execution including depth,
    iteration count, history, and memoization cache.
    """
    id: UUID
    workflow_id: UUID
    current_depth: int = 0
    iteration_count: int = 0
    history: List[Dict[str, Any]] = field(default_factory=list)
    memo: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    terminated: bool = False
    termination_type: Optional[TerminationType] = None
    final_result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        return {
            "id": str(self.id),
            "workflow_id": str(self.workflow_id),
            "current_depth": self.current_depth,
            "iteration_count": self.iteration_count,
            "history_length": len(self.history),
            "memo_size": len(self.memo),
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "terminated": self.terminated,
            "termination_type": self.termination_type.value if self.termination_type else None,
            "elapsed_seconds": (
                (datetime.utcnow() - self.started_at).total_seconds()
                if not self.completed_at
                else (self.completed_at - self.started_at).total_seconds()
            ),
        }


# =============================================================================
# Recursive Pattern Handler
# =============================================================================


class RecursivePatternHandler:
    """
    遞歸模式處理器

    Safely handles recursive workflow execution with:
    - Multiple recursion strategies
    - Termination condition detection
    - Memoization for optimization
    - Convergence detection
    - History tracking
    """

    def __init__(
        self,
        sub_executor: Any,  # SubWorkflowExecutor
        config: Optional[RecursionConfig] = None
    ):
        """
        Initialize RecursivePatternHandler.

        Args:
            sub_executor: Sub-workflow executor
            config: Recursion configuration
        """
        self.sub_executor = sub_executor
        self.config = config or RecursionConfig()

        # Active recursion states
        self._states: Dict[UUID, RecursionState] = {}

        # Abort flags
        self._abort_flags: Dict[UUID, bool] = {}

    # =========================================================================
    # Main Execution
    # =========================================================================

    async def execute_recursive(
        self,
        workflow_id: UUID,
        initial_inputs: Dict[str, Any],
        recursive_inputs_fn: Callable[[Dict[str, Any]], Union[Dict[str, Any], List[Dict[str, Any]]]],
        config: Optional[RecursionConfig] = None
    ) -> Dict[str, Any]:
        """
        執行遞歸工作流

        Execute a recursive workflow until termination.

        Args:
            workflow_id: Workflow ID to execute
            initial_inputs: Initial input parameters
            recursive_inputs_fn: Function to generate next iteration inputs
            config: Optional config override

        Returns:
            Final execution result
        """
        config = config or self.config

        state = RecursionState(
            id=uuid4(),
            workflow_id=workflow_id,
        )
        self._states[state.id] = state
        self._abort_flags[state.id] = False

        logger.info(f"Starting recursive execution {state.id} for workflow {workflow_id}")

        try:
            result = await self._recursive_execute(
                state=state,
                inputs=initial_inputs,
                recursive_inputs_fn=recursive_inputs_fn,
                config=config,
            )

            state.completed_at = datetime.utcnow()
            state.final_result = result
            return result

        except Exception as e:
            state.terminated = True
            state.termination_type = TerminationType.CONDITION
            state.completed_at = datetime.utcnow()
            logger.error(f"Recursive execution {state.id} failed: {e}")
            raise

        finally:
            # Cleanup abort flag
            self._abort_flags.pop(state.id, None)

    async def _recursive_execute(
        self,
        state: RecursionState,
        inputs: Dict[str, Any],
        recursive_inputs_fn: Callable,
        config: RecursionConfig
    ) -> Dict[str, Any]:
        """
        內部遞歸執行

        Internal recursive execution with all checks and optimizations.
        """
        # Check abort flag
        if self._abort_flags.get(state.id, False):
            state.terminated = True
            state.termination_type = TerminationType.USER_ABORT
            return self._build_termination_result(state, inputs, TerminationType.USER_ABORT)

        # Check memoization
        if config.memoization:
            memo_key = self._generate_memo_key(inputs)
            if memo_key in state.memo:
                logger.debug(f"Memo hit for key {memo_key[:16]}...")
                return state.memo[memo_key]

        # Check termination conditions
        termination = self._check_termination(state, inputs, config)
        if termination:
            state.terminated = True
            state.termination_type = termination
            return self._build_termination_result(state, inputs, termination)

        # Execute current iteration
        state.current_depth += 1
        state.iteration_count += 1

        result = await self._execute_iteration(state, inputs)

        # Track history
        if config.track_history and len(state.history) < config.max_history_size:
            state.history.append({
                "depth": state.current_depth,
                "iteration": state.iteration_count,
                "inputs": inputs,
                "result": result,
                "timestamp": datetime.utcnow().isoformat(),
            })

        # Check if should continue
        if not self._should_continue(state, result, config):
            state.current_depth -= 1
            return result

        # Generate next inputs
        next_inputs = recursive_inputs_fn(result)

        # Execute based on strategy
        if config.strategy == RecursionStrategy.DEPTH_FIRST:
            result = await self._execute_depth_first(
                state, next_inputs, recursive_inputs_fn, config
            )
        elif config.strategy == RecursionStrategy.BREADTH_FIRST:
            result = await self._execute_breadth_first(
                state, next_inputs, recursive_inputs_fn, config
            )
        elif config.strategy == RecursionStrategy.PARALLEL:
            result = await self._execute_parallel(
                state, next_inputs, recursive_inputs_fn, config
            )

        # Store in memo
        if config.memoization:
            memo_key = self._generate_memo_key(inputs)
            state.memo[memo_key] = result

        state.current_depth -= 1
        return result

    async def _execute_iteration(
        self,
        state: RecursionState,
        inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single iteration."""
        from .sub_executor import SubWorkflowExecutionMode

        if self.sub_executor:
            return await self.sub_executor.execute(
                sub_workflow_id=state.workflow_id,
                inputs=inputs,
                mode=SubWorkflowExecutionMode.SYNC,
            )
        else:
            # Mock execution
            return {
                "status": "completed",
                "inputs": inputs,
                "iteration": state.iteration_count,
                "mock": True,
            }

    async def _execute_depth_first(
        self,
        state: RecursionState,
        next_inputs: Union[Dict[str, Any], List[Dict[str, Any]]],
        recursive_inputs_fn: Callable,
        config: RecursionConfig
    ) -> Dict[str, Any]:
        """Depth-first recursion."""
        if isinstance(next_inputs, list):
            # Process each branch sequentially
            results = []
            for inp in next_inputs:
                result = await self._recursive_execute(
                    state, inp, recursive_inputs_fn, config
                )
                results.append(result)
            return self._merge_results(results)
        else:
            return await self._recursive_execute(
                state, next_inputs, recursive_inputs_fn, config
            )

    async def _execute_breadth_first(
        self,
        state: RecursionState,
        next_inputs: Union[Dict[str, Any], List[Dict[str, Any]]],
        recursive_inputs_fn: Callable,
        config: RecursionConfig
    ) -> Dict[str, Any]:
        """Breadth-first recursion (using queue)."""
        # For single input, same as depth-first
        if not isinstance(next_inputs, list):
            return await self._recursive_execute(
                state, next_inputs, recursive_inputs_fn, config
            )

        # Process level by level
        queue = list(next_inputs)
        results = []

        while queue:
            current = queue.pop(0)
            result = await self._execute_iteration(state, current)
            results.append(result)

            if self._should_continue(state, result, config):
                child_inputs = recursive_inputs_fn(result)
                if isinstance(child_inputs, list):
                    queue.extend(child_inputs)
                else:
                    queue.append(child_inputs)

            # Check termination at each level
            termination = self._check_termination(state, current, config)
            if termination:
                break

        return self._merge_results(results)

    async def _execute_parallel(
        self,
        state: RecursionState,
        next_inputs: Union[Dict[str, Any], List[Dict[str, Any]]],
        recursive_inputs_fn: Callable,
        config: RecursionConfig
    ) -> Dict[str, Any]:
        """Parallel recursion."""
        if not isinstance(next_inputs, list):
            return await self._recursive_execute(
                state, next_inputs, recursive_inputs_fn, config
            )

        # Process branches in parallel
        tasks = [
            self._recursive_execute(state, inp, recursive_inputs_fn, config)
            for inp in next_inputs
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append({"error": str(result), "status": "failed"})
            else:
                processed_results.append(result)

        return self._merge_results(processed_results)

    # =========================================================================
    # Termination Checking
    # =========================================================================

    def _check_termination(
        self,
        state: RecursionState,
        inputs: Dict[str, Any],
        config: RecursionConfig
    ) -> Optional[TerminationType]:
        """
        檢查終止條件

        Check all termination conditions.
        """
        # Check max depth
        if state.current_depth >= config.max_depth:
            logger.info(f"Max depth {config.max_depth} reached")
            return TerminationType.MAX_DEPTH

        # Check max iterations
        if state.iteration_count >= config.max_iterations:
            logger.info(f"Max iterations {config.max_iterations} reached")
            return TerminationType.MAX_ITERATIONS

        # Check timeout
        elapsed = (datetime.utcnow() - state.started_at).total_seconds()
        if elapsed >= config.timeout_seconds:
            logger.info(f"Timeout {config.timeout_seconds}s reached")
            return TerminationType.TIMEOUT

        # Check custom condition
        if config.termination_condition:
            try:
                if config.termination_condition(inputs, state.current_depth):
                    logger.info("Custom termination condition met")
                    return TerminationType.CONDITION
            except Exception as e:
                logger.warning(f"Termination condition error: {e}")

        # Check convergence
        if config.convergence_threshold and len(state.history) >= 2:
            if self._check_convergence(state, config.convergence_threshold):
                logger.info("Convergence detected")
                return TerminationType.CONVERGENCE

        return None

    def _check_convergence(
        self,
        state: RecursionState,
        threshold: float
    ) -> bool:
        """
        檢查結果是否收斂

        Check if results have converged below threshold.
        """
        if len(state.history) < 2:
            return False

        last_result = state.history[-1].get("result", {})
        prev_result = state.history[-2].get("result", {})

        try:
            diff = self._calculate_diff(last_result, prev_result)
            return diff < threshold
        except Exception:
            return False

    def _calculate_diff(
        self,
        result1: Dict[str, Any],
        result2: Dict[str, Any]
    ) -> float:
        """
        計算結果差異

        Calculate difference between two results.
        """
        diffs = []

        for key in result1:
            if key in result2:
                val1 = result1[key]
                val2 = result2[key]

                if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                    diffs.append(abs(val1 - val2))

        return sum(diffs) / len(diffs) if diffs else float('inf')

    def _should_continue(
        self,
        state: RecursionState,
        result: Dict[str, Any],
        config: RecursionConfig
    ) -> bool:
        """
        判斷是否繼續遞歸

        Determine if recursion should continue.
        """
        if state.terminated:
            return False

        # Check result for continue signal
        if result.get("continue_recursion") is False:
            return False

        if result.get("status") in ["terminated", "complete", "done"]:
            return False

        return True

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _generate_memo_key(self, inputs: Dict[str, Any]) -> str:
        """Generate memoization key from inputs."""
        try:
            serialized = json.dumps(inputs, sort_keys=True, default=str)
            return hashlib.md5(serialized.encode()).hexdigest()
        except Exception:
            return str(uuid4())

    def _build_termination_result(
        self,
        state: RecursionState,
        last_inputs: Dict[str, Any],
        termination_type: TerminationType
    ) -> Dict[str, Any]:
        """Build termination result."""
        return {
            "status": "terminated",
            "termination_type": termination_type.value,
            "depth_reached": state.current_depth,
            "total_iterations": state.iteration_count,
            "last_inputs": last_inputs,
            "history_length": len(state.history),
            "elapsed_seconds": (datetime.utcnow() - state.started_at).total_seconds(),
        }

    def _merge_results(
        self,
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        合併並行遞歸結果

        Merge results from parallel branches.
        """
        if not results:
            return {"branches": 0, "results": []}

        merged = {
            "branches": len(results),
            "results": results,
            "status": "merged",
        }

        # Aggregate numeric fields
        numeric_keys: set = set()
        for r in results:
            if isinstance(r, dict):
                for k, v in r.items():
                    if isinstance(v, (int, float)):
                        numeric_keys.add(k)

        for key in numeric_keys:
            values = [r.get(key) for r in results if isinstance(r, dict) and key in r]
            if values:
                merged[f"{key}_sum"] = sum(values)
                merged[f"{key}_avg"] = sum(values) / len(values)
                merged[f"{key}_min"] = min(values)
                merged[f"{key}_max"] = max(values)

        return merged

    # =========================================================================
    # Management
    # =========================================================================

    def abort(self, state_id: UUID) -> bool:
        """
        中止遞歸執行

        Request abort of recursive execution.
        """
        if state_id in self._states:
            self._abort_flags[state_id] = True
            return True
        return False

    def get_recursion_stats(
        self,
        state_id: UUID
    ) -> Dict[str, Any]:
        """
        獲取遞歸統計

        Get statistics for a recursion state.
        """
        state = self._states.get(state_id)
        if not state:
            return {"error": "State not found", "state_id": str(state_id)}
        return state.to_dict()

    def get_history(
        self,
        state_id: UUID,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        獲取遞歸歷史

        Get execution history for a state.
        """
        state = self._states.get(state_id)
        if not state:
            return []
        return state.history[-limit:]

    def clear_completed(self) -> int:
        """Clear completed recursion states."""
        to_remove = [
            sid for sid, state in self._states.items()
            if state.terminated or state.completed_at
        ]

        for sid in to_remove:
            del self._states[sid]
            self._abort_flags.pop(sid, None)

        return len(to_remove)

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics."""
        total = len(self._states)
        active = sum(1 for s in self._states.values() if not s.terminated)
        terminated = total - active

        total_iterations = sum(s.iteration_count for s in self._states.values())
        max_depth_reached = max(
            (s.current_depth for s in self._states.values()),
            default=0
        )

        by_termination = {}
        for state in self._states.values():
            if state.termination_type:
                key = state.termination_type.value
                by_termination[key] = by_termination.get(key, 0) + 1

        return {
            "total_states": total,
            "active": active,
            "terminated": terminated,
            "total_iterations": total_iterations,
            "max_depth_reached": max_depth_reached,
            "by_termination_type": by_termination,
            "config": self.config.to_dict(),
        }

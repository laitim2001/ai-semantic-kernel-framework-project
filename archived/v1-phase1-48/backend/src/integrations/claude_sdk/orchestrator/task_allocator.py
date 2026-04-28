# =============================================================================
# IPA Platform - Task Allocator
# =============================================================================
# Sprint 81: S81-1 - Claude 主導的多 Agent 協調 (10 pts)
#
# This module handles task allocation and execution across multiple agents.
# =============================================================================

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from .types import (
    AgentInfo,
    AgentSelection,
    ComplexTask,
    CoordinationContext,
    ExecutionMode,
    Subtask,
    SubtaskResult,
    SubtaskStatus,
    TaskAnalysis,
)
from .context_manager import ContextManager


logger = logging.getLogger(__name__)


# Type for agent executor function
AgentExecutor = Callable[[str, Subtask], SubtaskResult]


class TaskAllocator:
    """
    Allocates tasks to agents and manages execution.

    Responsibilities:
    - Select best agent for each subtask
    - Manage parallel and sequential execution
    - Handle failures and retries
    """

    def __init__(
        self,
        context_manager: Optional[ContextManager] = None,
        max_retries: int = 2,
        timeout_seconds: int = 300,
    ):
        """
        Initialize task allocator.

        Args:
            context_manager: Context manager for data transfer.
            max_retries: Maximum retry attempts for failed subtasks.
            timeout_seconds: Timeout for subtask execution.
        """
        self.context_manager = context_manager or ContextManager()
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds

    def select_agents(
        self,
        subtasks: List[Subtask],
        available_agents: List[AgentInfo],
    ) -> List[AgentSelection]:
        """
        Select best agent for each subtask.

        Args:
            subtasks: List of subtasks to assign.
            available_agents: List of available agents.

        Returns:
            List of agent selections.
        """
        selections = []

        for subtask in subtasks:
            selection = self._select_best_agent(subtask, available_agents)
            if selection:
                selections.append(selection)
                # Update agent load
                selection.agent.current_load += 1
            else:
                logger.warning(
                    f"No suitable agent found for subtask {subtask.subtask_id}"
                )

        return selections

    def _select_best_agent(
        self,
        subtask: Subtask,
        available_agents: List[AgentInfo],
    ) -> Optional[AgentSelection]:
        """Select the best agent for a subtask."""
        candidates = []

        for agent in available_agents:
            # Check if agent can handle the subtask
            if not agent.can_handle(subtask.required_capabilities):
                continue

            # Check availability
            if agent.availability_score <= 0:
                continue

            # Calculate capability score
            capability_score = self._calculate_capability_score(
                agent, subtask.required_capabilities
            )

            # Calculate overall score (70% capability, 30% availability)
            overall_score = (
                capability_score * 0.7 + agent.availability_score * 0.3
            )

            candidates.append(
                AgentSelection(
                    agent=agent,
                    subtask=subtask,
                    capability_score=capability_score,
                    availability_score=agent.availability_score,
                    overall_score=overall_score,
                    reasoning=f"Capability: {capability_score:.2f}, Availability: {agent.availability_score:.2f}",
                )
            )

        if not candidates:
            return None

        # Sort by overall score and select best
        candidates.sort(key=lambda x: x.overall_score, reverse=True)
        best = candidates[0]

        # Assign agent to subtask
        subtask.assigned_agent_id = best.agent.agent_id
        subtask.status = SubtaskStatus.ASSIGNED

        logger.info(
            f"Selected agent {best.agent.name} for subtask {subtask.subtask_id} "
            f"(score: {best.overall_score:.2f})"
        )

        return best

    def _calculate_capability_score(
        self,
        agent: AgentInfo,
        required_capabilities: List[str],
    ) -> float:
        """Calculate capability match score."""
        if not required_capabilities:
            return 1.0

        total_score = 0.0
        for cap in required_capabilities:
            # Check if agent has the capability
            if cap in agent.capabilities:
                # Add skill proficiency if available
                skill_score = agent.skills.get(cap, 0.5)
                total_score += skill_score
            else:
                # Capability not found
                total_score += 0.0

        return total_score / len(required_capabilities)

    async def execute_parallel(
        self,
        subtasks: List[Subtask],
        selections: List[AgentSelection],
        executor: AgentExecutor,
    ) -> List[SubtaskResult]:
        """
        Execute subtasks in parallel.

        Args:
            subtasks: List of subtasks to execute.
            selections: Agent selections for subtasks.
            executor: Function to execute subtask on agent.

        Returns:
            List of subtask results.
        """
        # Filter subtasks that are ready (no pending dependencies)
        ready_subtasks = [
            s for s in subtasks
            if s.status == SubtaskStatus.ASSIGNED
        ]

        logger.info(f"Executing {len(ready_subtasks)} subtasks in parallel")

        # Create tasks for parallel execution
        tasks = []
        for subtask in ready_subtasks:
            selection = next(
                (s for s in selections if s.subtask.subtask_id == subtask.subtask_id),
                None,
            )
            if selection:
                tasks.append(
                    self._execute_with_timeout(
                        subtask, selection.agent.agent_id, executor
                    )
                )

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Subtask execution failed: {result}")
            elif isinstance(result, SubtaskResult):
                processed_results.append(result)

        return processed_results

    async def execute_sequential(
        self,
        subtasks: List[Subtask],
        selections: List[AgentSelection],
        executor: AgentExecutor,
        context: CoordinationContext,
    ) -> List[SubtaskResult]:
        """
        Execute subtasks sequentially, respecting dependencies.

        Args:
            subtasks: List of subtasks to execute.
            selections: Agent selections for subtasks.
            executor: Function to execute subtask on agent.
            context: Coordination context.

        Returns:
            List of subtask results.
        """
        results: List[SubtaskResult] = []
        completed: Dict[str, SubtaskResult] = {}
        completed_subtasks: Dict[str, Subtask] = {}

        # Build dependency graph
        pending = list(subtasks)

        while pending:
            # Find subtasks with satisfied dependencies
            ready = [
                s for s in pending
                if all(dep in completed for dep in s.depends_on)
            ]

            if not ready:
                logger.error("Circular dependency detected or no ready subtasks")
                break

            # Execute ready subtasks (can be parallel within this batch)
            batch_tasks = []
            for subtask in ready:
                # Prepare context from dependencies
                self.context_manager.prepare_subtask_context(
                    subtask, completed_subtasks, completed
                )

                selection = next(
                    (s for s in selections if s.subtask.subtask_id == subtask.subtask_id),
                    None,
                )
                if selection:
                    batch_tasks.append(
                        self._execute_with_timeout(
                            subtask, selection.agent.agent_id, executor
                        )
                    )

            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Process batch results
            for i, result in enumerate(batch_results):
                if isinstance(result, SubtaskResult):
                    results.append(result)
                    completed[ready[i].subtask_id] = result
                    completed_subtasks[ready[i].subtask_id] = ready[i]

                    # Transfer context to dependent subtasks
                    for dep_subtask in pending:
                        if ready[i].subtask_id in dep_subtask.depends_on:
                            self.context_manager.transfer_context(
                                ready[i], dep_subtask, result
                            )

            # Remove completed from pending
            pending = [s for s in pending if s.subtask_id not in completed]

        return results

    async def execute_pipeline(
        self,
        subtasks: List[Subtask],
        selections: List[AgentSelection],
        executor: AgentExecutor,
    ) -> List[SubtaskResult]:
        """
        Execute subtasks in pipeline mode (output feeds into next).

        Args:
            subtasks: List of subtasks in pipeline order.
            selections: Agent selections for subtasks.
            executor: Function to execute subtask on agent.

        Returns:
            List of subtask results.
        """
        results: List[SubtaskResult] = []
        previous_output = None

        for subtask in subtasks:
            # Add previous output to input
            if previous_output is not None:
                subtask.input_data["pipeline_input"] = previous_output

            selection = next(
                (s for s in selections if s.subtask.subtask_id == subtask.subtask_id),
                None,
            )

            if not selection:
                logger.warning(f"No selection for subtask {subtask.subtask_id}")
                continue

            result = await self._execute_with_timeout(
                subtask, selection.agent.agent_id, executor
            )
            results.append(result)

            if result.success:
                previous_output = result.output
            else:
                logger.warning(
                    f"Pipeline interrupted at {subtask.subtask_id}: {result.error}"
                )
                break

        return results

    async def _execute_with_timeout(
        self,
        subtask: Subtask,
        agent_id: str,
        executor: AgentExecutor,
    ) -> SubtaskResult:
        """Execute subtask with timeout and retry."""
        subtask.status = SubtaskStatus.IN_PROGRESS
        subtask.started_at = datetime.utcnow()

        start_time = time.time()

        for attempt in range(self.max_retries + 1):
            try:
                # Execute with timeout
                result = await asyncio.wait_for(
                    self._run_executor(executor, agent_id, subtask),
                    timeout=self.timeout_seconds,
                )

                # Update subtask status
                if result.success:
                    subtask.status = SubtaskStatus.COMPLETED
                    subtask.output_data = result.output
                else:
                    subtask.status = SubtaskStatus.FAILED
                    subtask.error = result.error

                subtask.completed_at = datetime.utcnow()
                result.execution_time_seconds = time.time() - start_time

                return result

            except asyncio.TimeoutError:
                logger.warning(
                    f"Subtask {subtask.subtask_id} timed out (attempt {attempt + 1})"
                )
                if attempt < self.max_retries:
                    continue

                subtask.status = SubtaskStatus.FAILED
                subtask.error = "Execution timed out"
                subtask.completed_at = datetime.utcnow()

                return SubtaskResult(
                    subtask_id=subtask.subtask_id,
                    agent_id=agent_id,
                    success=False,
                    error="Execution timed out",
                    execution_time_seconds=time.time() - start_time,
                )

            except Exception as e:
                logger.error(
                    f"Subtask {subtask.subtask_id} failed (attempt {attempt + 1}): {e}"
                )
                if attempt < self.max_retries:
                    continue

                subtask.status = SubtaskStatus.FAILED
                subtask.error = str(e)
                subtask.completed_at = datetime.utcnow()

                return SubtaskResult(
                    subtask_id=subtask.subtask_id,
                    agent_id=agent_id,
                    success=False,
                    error=str(e),
                    execution_time_seconds=time.time() - start_time,
                )

        # Should not reach here
        return SubtaskResult(
            subtask_id=subtask.subtask_id,
            agent_id=agent_id,
            success=False,
            error="Max retries exceeded",
        )

    async def _run_executor(
        self,
        executor: AgentExecutor,
        agent_id: str,
        subtask: Subtask,
    ) -> SubtaskResult:
        """Run the executor function."""
        if asyncio.iscoroutinefunction(executor):
            return await executor(agent_id, subtask)
        else:
            # Run sync executor in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, executor, agent_id, subtask
            )

    def create_subtasks(
        self,
        task: ComplexTask,
        analysis: TaskAnalysis,
    ) -> List[Subtask]:
        """
        Create subtasks based on task analysis.

        Args:
            task: The complex task.
            analysis: Task analysis result.

        Returns:
            List of created subtasks.
        """
        subtasks = []

        # Simple decomposition based on required capabilities
        for i, cap in enumerate(analysis.required_capabilities):
            subtask = Subtask(
                subtask_id=f"{task.task_id}:sub:{uuid4().hex[:8]}",
                parent_task_id=task.task_id,
                description=f"Handle {cap} for task: {task.description[:50]}",
                required_capabilities=[cap],
                input_data={"task_context": task.context},
            )

            # Set dependencies for sequential execution
            if not analysis.can_parallel and i > 0:
                subtask.depends_on = [subtasks[i - 1].subtask_id]

            subtasks.append(subtask)

        logger.info(
            f"Created {len(subtasks)} subtasks for task {task.task_id}"
        )

        return subtasks

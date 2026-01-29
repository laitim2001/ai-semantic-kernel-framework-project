# =============================================================================
# IPA Platform - Claude Coordinator
# =============================================================================
# Sprint 81: S81-1 - Claude 主導的多 Agent 協調 (10 pts)
#
# This module provides Claude-led multi-agent coordination capabilities.
# Claude acts as the orchestrator, analyzing tasks, selecting agents,
# and coordinating execution.
# =============================================================================

import logging
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING
from uuid import uuid4

from .types import (
    AgentInfo,
    AgentSelection,
    ComplexTask,
    CoordinationContext,
    CoordinationResult,
    CoordinationStatus,
    ExecutionMode,
    Subtask,
    SubtaskResult,
    TaskAnalysis,
    TaskComplexity,
)
from .task_allocator import TaskAllocator, AgentExecutor
from .context_manager import ContextManager

if TYPE_CHECKING:
    from src.integrations.swarm import SwarmIntegration


logger = logging.getLogger(__name__)


class ClaudeCoordinator:
    """
    Claude-led multi-agent coordinator.

    Orchestrates complex tasks across multiple agents by:
    1. Analyzing task requirements and complexity
    2. Selecting appropriate agents based on capabilities
    3. Allocating subtasks to selected agents
    4. Coordinating parallel or sequential execution
    5. Aggregating results from all agents
    """

    def __init__(
        self,
        claude_client: Optional[Any] = None,
        default_agents: Optional[List[AgentInfo]] = None,
        swarm_integration: Optional["SwarmIntegration"] = None,
    ):
        """
        Initialize the coordinator.

        Args:
            claude_client: Claude SDK client for intelligent decisions.
            default_agents: Default list of available agents.
            swarm_integration: Optional SwarmIntegration for tracking swarm state.
        """
        self._claude_client = claude_client
        self._default_agents = default_agents or []
        self._context_manager = ContextManager()
        self._task_allocator = TaskAllocator(context_manager=self._context_manager)
        self._swarm_integration = swarm_integration

        # Agent registry
        self._registered_agents: Dict[str, AgentInfo] = {}
        for agent in self._default_agents:
            self._registered_agents[agent.agent_id] = agent

        # Execution history
        self._coordination_history: List[CoordinationResult] = []

    def register_agent(self, agent: AgentInfo) -> None:
        """
        Register an agent with the coordinator.

        Args:
            agent: Agent information to register.
        """
        self._registered_agents[agent.agent_id] = agent
        logger.info(f"Registered agent: {agent.name} ({agent.agent_id})")

    def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent.

        Args:
            agent_id: ID of agent to unregister.

        Returns:
            True if agent was found and removed.
        """
        if agent_id in self._registered_agents:
            del self._registered_agents[agent_id]
            logger.info(f"Unregistered agent: {agent_id}")
            return True
        return False

    def get_available_agents(self) -> List[AgentInfo]:
        """Get list of all available agents."""
        return [
            agent for agent in self._registered_agents.values()
            if agent.availability_score > 0
        ]

    async def coordinate_agents(
        self,
        task: ComplexTask,
        available_agents: Optional[List[AgentInfo]] = None,
        executor: Optional[AgentExecutor] = None,
    ) -> CoordinationResult:
        """
        Coordinate multiple agents to complete a complex task.

        Args:
            task: The complex task to complete.
            available_agents: Available agents (uses registered if not provided).
            executor: Function to execute subtasks on agents.

        Returns:
            CoordinationResult with aggregated output.
        """
        start_time = time.time()

        # Use registered agents if not provided
        if available_agents is None:
            available_agents = self.get_available_agents()

        if not available_agents:
            logger.error("No available agents for coordination")
            return CoordinationResult(
                task_id=task.task_id,
                status=CoordinationStatus.FAILED,
                error="No available agents",
            )

        # Create coordination context
        context = CoordinationContext(task=task)

        try:
            # Phase 1: Analyze task
            logger.info(f"Analyzing task: {task.task_id}")
            analysis = await self.analyze_task(task)
            context.analysis = analysis

            # Phase 2: Select agents
            logger.info(f"Selecting agents for {analysis.subtask_count} subtasks")
            subtasks = self._task_allocator.create_subtasks(task, analysis)
            context.subtasks = subtasks

            selections = self._task_allocator.select_agents(
                subtasks, available_agents
            )
            context.selections = selections

            if len(selections) < len(subtasks):
                logger.warning(
                    f"Only {len(selections)}/{len(subtasks)} subtasks have agents"
                )

            # Notify SwarmIntegration: coordination started
            if self._swarm_integration:
                try:
                    from src.integrations.swarm import SwarmMode
                    mode_map = {
                        ExecutionMode.SEQUENTIAL: SwarmMode.SEQUENTIAL,
                        ExecutionMode.PARALLEL: SwarmMode.PARALLEL,
                        ExecutionMode.PIPELINE: SwarmMode.SEQUENTIAL,
                        ExecutionMode.HYBRID: SwarmMode.HIERARCHICAL,
                    }
                    swarm_mode = mode_map.get(analysis.execution_mode, SwarmMode.SEQUENTIAL)
                    self._swarm_integration.on_coordination_started(
                        swarm_id=task.task_id,
                        mode=swarm_mode,
                        subtasks=[
                            {"subtask_id": st.subtask_id, "description": st.description}
                            for st in subtasks
                        ],
                        metadata={"task_description": task.description},
                    )
                except Exception as e:
                    logger.warning(f"SwarmIntegration notification failed: {e}")

            # Phase 3: Execute
            logger.info(f"Executing with mode: {analysis.execution_mode.value}")
            executor = executor or self._default_executor

            # Wrap executor to notify SwarmIntegration
            wrapped_executor = self._wrap_executor_for_swarm(executor, task.task_id)

            if analysis.execution_mode == ExecutionMode.PARALLEL:
                results = await self._task_allocator.execute_parallel(
                    subtasks, selections, wrapped_executor
                )
            elif analysis.execution_mode == ExecutionMode.PIPELINE:
                results = await self._task_allocator.execute_pipeline(
                    subtasks, selections, wrapped_executor
                )
            else:
                results = await self._task_allocator.execute_sequential(
                    subtasks, selections, wrapped_executor, context
                )

            context.results = results

            # Phase 4: Aggregate results
            logger.info("Aggregating results")
            aggregated = self._context_manager.aggregate_final_result(
                context, aggregation_type="summary"
            )

            # Calculate success rate
            success_count = sum(1 for r in results if r.success)
            success_rate = success_count / len(results) if results else 0.0

            # Build final result
            result = CoordinationResult(
                task_id=task.task_id,
                status=CoordinationStatus.COMPLETED if success_rate >= 0.5 else CoordinationStatus.FAILED,
                subtask_results=results,
                aggregated_output=aggregated,
                total_execution_time_seconds=time.time() - start_time,
                agents_used=list(set(r.agent_id for r in results)),
                success_rate=success_rate,
                completed_at=datetime.utcnow(),
            )

            # Store in history
            self._coordination_history.append(result)

            # Notify SwarmIntegration: coordination completed
            if self._swarm_integration:
                try:
                    from src.integrations.swarm import SwarmStatus
                    swarm_status = (
                        SwarmStatus.COMPLETED
                        if result.status == CoordinationStatus.COMPLETED
                        else SwarmStatus.FAILED
                    )
                    self._swarm_integration.on_coordination_completed(
                        swarm_id=task.task_id,
                        status=swarm_status,
                    )
                except Exception as e:
                    logger.warning(f"SwarmIntegration notification failed: {e}")

            logger.info(
                f"Coordination completed: {result.status.value} "
                f"(success rate: {success_rate:.1%})"
            )

            return result

        except Exception as e:
            logger.error(f"Coordination failed: {e}")

            # Notify SwarmIntegration: coordination failed
            if self._swarm_integration:
                try:
                    from src.integrations.swarm import SwarmStatus
                    self._swarm_integration.on_coordination_completed(
                        swarm_id=task.task_id,
                        status=SwarmStatus.FAILED,
                    )
                except Exception as notify_error:
                    logger.warning(f"SwarmIntegration notification failed: {notify_error}")

            return CoordinationResult(
                task_id=task.task_id,
                status=CoordinationStatus.FAILED,
                error=str(e),
                total_execution_time_seconds=time.time() - start_time,
                completed_at=datetime.utcnow(),
            )

    def _wrap_executor_for_swarm(
        self,
        executor: AgentExecutor,
        swarm_id: str,
    ) -> AgentExecutor:
        """
        Wrap executor to notify SwarmIntegration of subtask events.

        Args:
            executor: Original executor function.
            swarm_id: The swarm/task ID.

        Returns:
            Wrapped executor that notifies SwarmIntegration.
        """
        if not self._swarm_integration:
            return executor

        def wrapped(agent_id: str, subtask: Subtask) -> SubtaskResult:
            # Notify subtask started
            try:
                from src.integrations.swarm import WorkerType
                worker_type = WorkerType.CUSTOM
                # Try to infer worker type from capabilities
                if subtask.required_capabilities:
                    cap = subtask.required_capabilities[0].lower()
                    if "research" in cap:
                        worker_type = WorkerType.RESEARCH
                    elif "write" in cap:
                        worker_type = WorkerType.WRITER
                    elif "review" in cap:
                        worker_type = WorkerType.REVIEWER
                    elif "code" in cap:
                        worker_type = WorkerType.CODER

                self._swarm_integration.on_subtask_started(
                    swarm_id=swarm_id,
                    worker_id=subtask.subtask_id,
                    worker_name=f"Agent {agent_id}",
                    worker_type=worker_type,
                    role=", ".join(subtask.required_capabilities) if subtask.required_capabilities else "Worker",
                    task_description=subtask.description,
                )
            except Exception as e:
                logger.warning(f"SwarmIntegration subtask start notification failed: {e}")

            # Execute the actual subtask
            result = executor(agent_id, subtask)

            # Notify subtask completed
            try:
                from src.integrations.swarm import WorkerStatus
                status = WorkerStatus.COMPLETED if result.success else WorkerStatus.FAILED
                self._swarm_integration.on_subtask_completed(
                    swarm_id=swarm_id,
                    worker_id=subtask.subtask_id,
                    status=status,
                    error=result.error if hasattr(result, 'error') else None,
                )
            except Exception as e:
                logger.warning(f"SwarmIntegration subtask complete notification failed: {e}")

            return result

        return wrapped

    async def analyze_task(self, task: ComplexTask) -> TaskAnalysis:
        """
        Analyze a task to determine complexity and execution strategy.

        Args:
            task: The task to analyze.

        Returns:
            TaskAnalysis with recommendations.
        """
        # Determine complexity based on requirements
        num_requirements = len(task.requirements)

        if num_requirements <= 1:
            complexity = TaskComplexity.SIMPLE
            execution_mode = ExecutionMode.SEQUENTIAL
            can_parallel = False
        elif num_requirements <= 3:
            complexity = TaskComplexity.MODERATE
            execution_mode = ExecutionMode.PARALLEL
            can_parallel = True
        elif num_requirements <= 6:
            complexity = TaskComplexity.COMPLEX
            execution_mode = ExecutionMode.HYBRID
            can_parallel = True
        else:
            complexity = TaskComplexity.CRITICAL
            execution_mode = ExecutionMode.SEQUENTIAL
            can_parallel = False  # Too complex, need careful sequential handling

        # Use Claude for more intelligent analysis if available
        reasoning = ""
        if self._claude_client:
            try:
                reasoning = await self._claude_analyze(task)
            except Exception as e:
                logger.warning(f"Claude analysis failed: {e}")
                reasoning = "Basic analysis used (Claude unavailable)"
        else:
            reasoning = f"Basic analysis: {num_requirements} requirements, {complexity.value} complexity"

        # Estimate duration (rough estimate: 30s per requirement)
        estimated_duration = num_requirements * 30

        return TaskAnalysis(
            task_id=task.task_id,
            complexity=complexity,
            execution_mode=execution_mode,
            required_capabilities=task.requirements,
            subtask_count=num_requirements or 1,
            estimated_duration_seconds=estimated_duration,
            can_parallel=can_parallel,
            dependencies=list(task.constraints.get("dependencies", [])),
            risk_factors=list(task.constraints.get("risks", [])),
            reasoning=reasoning,
        )

    async def _claude_analyze(self, task: ComplexTask) -> str:
        """Use Claude for intelligent task analysis."""
        if not self._claude_client:
            return ""

        prompt = f"""分析以下任務，提供執行建議：

任務描述: {task.description}
需求能力: {', '.join(task.requirements)}
優先級: {task.priority}
約束: {task.constraints}

請提供：
1. 任務複雜度評估
2. 建議的執行模式（並行/串行/管道）
3. 潛在風險
4. 其他建議"""

        try:
            response = await self._claude_client.query(prompt)
            return response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            logger.warning(f"Claude query failed: {e}")
            return ""

    def _default_executor(
        self,
        agent_id: str,
        subtask: Subtask,
    ) -> SubtaskResult:
        """
        Default executor for subtasks (mock implementation).

        In production, this would delegate to actual agent implementations.
        """
        logger.debug(f"Executing subtask {subtask.subtask_id} on agent {agent_id}")

        # Simulate execution
        return SubtaskResult(
            subtask_id=subtask.subtask_id,
            agent_id=agent_id,
            success=True,
            output={
                "message": f"Subtask {subtask.subtask_id} completed",
                "agent": agent_id,
                "capabilities_used": subtask.required_capabilities,
            },
            execution_time_seconds=0.1,
        )

    async def select_agents(
        self,
        analysis: TaskAnalysis,
        available_agents: List[AgentInfo],
    ) -> List[AgentSelection]:
        """
        Select agents based on task analysis.

        Args:
            analysis: Task analysis result.
            available_agents: List of available agents.

        Returns:
            List of agent selections.
        """
        # Create subtasks from analysis
        subtasks = []
        for i, cap in enumerate(analysis.required_capabilities):
            subtask = Subtask(
                subtask_id=f"{analysis.task_id}:sub:{i}",
                parent_task_id=analysis.task_id,
                description=f"Handle {cap}",
                required_capabilities=[cap],
            )
            subtasks.append(subtask)

        return self._task_allocator.select_agents(subtasks, available_agents)

    def get_coordination_history(
        self,
        limit: int = 100,
    ) -> List[CoordinationResult]:
        """Get coordination history."""
        return self._coordination_history[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """Get coordinator statistics."""
        total = len(self._coordination_history)
        if total == 0:
            return {
                "total_coordinations": 0,
                "success_rate": 0.0,
                "avg_execution_time": 0.0,
                "registered_agents": len(self._registered_agents),
            }

        successful = sum(
            1 for r in self._coordination_history
            if r.status == CoordinationStatus.COMPLETED
        )
        total_time = sum(
            r.total_execution_time_seconds for r in self._coordination_history
        )

        return {
            "total_coordinations": total,
            "success_rate": successful / total,
            "avg_execution_time": total_time / total,
            "registered_agents": len(self._registered_agents),
            "available_agents": len(self.get_available_agents()),
        }

    def clear_history(self) -> None:
        """Clear coordination history."""
        self._coordination_history.clear()
        self._context_manager.clear()
        logger.info("Coordinator history cleared")

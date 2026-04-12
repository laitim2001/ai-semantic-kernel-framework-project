"""
TeamExecutor — Collaborative expert agent execution via SwarmWorkerExecutor.

Delegates to the PoC-proven SwarmWorkerExecutor for real LLM + tool execution
with thinking visualization, real tool calls, and agent interaction events.

Phase 45: Orchestration Core
Phase 45: Integrated PoC SwarmWorkerExecutor (replaces simplified LLM-only version)
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..models import AgentResult, DispatchRequest, DispatchResult, ExecutionRoute
from .base import BaseExecutor
from .event_adapter import EventQueueAdapter

logger = logging.getLogger(__name__)


class TeamExecutor(BaseExecutor):
    """Execute complex tasks via collaborative expert agents.

    Uses SwarmWorkerExecutor (PoC-proven) for each agent, providing:
    - Real LLM thinking visualization (chat_with_tools loop)
    - Real tool execution via tool registry
    - Per-agent SSE events mapped to AGENT_MEMBER_* via EventQueueAdapter
    """

    def __init__(self, llm_client: Optional[Any] = None, model: Optional[str] = None):
        self._llm_client = llm_client
        self._model = model

    @property
    def name(self) -> str:
        return "team"

    async def _execute(
        self,
        request: DispatchRequest,
        event_queue: Optional[asyncio.Queue] = None,
    ) -> DispatchResult:
        start = time.time()
        team_id = f"team-{uuid.uuid4().hex[:8]}"

        try:
            # Create LLM service (same pattern as PoC execution.py:250-252)
            llm_service = self._create_llm_service()

            # Create tool registry (same pattern as PoC execution.py:254-257)
            tool_registry = self._create_tool_registry()

            # Decompose task into sub-tasks
            sub_tasks = await self._decompose_task(request, llm_service, tool_registry)

            # Emit AGENT_TEAM_CREATED with full roster
            if event_queue is not None:
                from ...pipeline.service import PipelineEvent, PipelineEventType

                await event_queue.put(
                    PipelineEvent(
                        PipelineEventType.AGENT_TEAM_CREATED,
                        {
                            "team_id": team_id,
                            "mode": "sequential",
                            "agents": [
                                {
                                    "agent_id": f"w-{t.task_id}",
                                    "agent_name": t.title,
                                    "role": t.role,
                                }
                                for t in sub_tasks
                            ],
                            "total_agents": len(sub_tasks),
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        },
                        step_name="dispatch",
                    )
                )

            # Execute workers sequentially with shared context
            agent_results: List[AgentResult] = []
            shared_context: List[str] = []

            for sub_task in sub_tasks:
                # Append prior findings to task description for sequential context
                if shared_context:
                    sub_task.description += (
                        "\n\n## Prior Team Findings\n"
                        + "\n".join(shared_context)
                    )

                result = await self._run_worker(
                    sub_task, llm_service, tool_registry, event_queue, team_id
                )
                agent_results.append(result)
                shared_context.append(
                    f"[{result.agent_name}]: {result.output[:500]}"
                )

            # Synthesize results
            synthesis = self._synthesize(agent_results)

            # Emit AGENT_TEAM_COMPLETED
            if event_queue is not None:
                from ...pipeline.service import PipelineEvent, PipelineEventType

                await event_queue.put(
                    PipelineEvent(
                        PipelineEventType.AGENT_TEAM_COMPLETED,
                        {
                            "team_id": team_id,
                            "status": "completed",
                            "total_agents": len(sub_tasks),
                            "completed_agents": len(agent_results),
                            "duration_ms": round((time.time() - start) * 1000),
                            "completed_at": datetime.now(timezone.utc).isoformat(),
                        },
                        step_name="dispatch",
                    )
                )

            return DispatchResult(
                route=ExecutionRoute.TEAM,
                response_text=synthesis,
                agent_results=agent_results,
                synthesis=synthesis,
                duration_ms=(time.time() - start) * 1000,
                status="completed",
            )

        except Exception as e:
            logger.error("TeamExecutor failed: %s", str(e)[:200], exc_info=True)
            if event_queue is not None:
                from ...pipeline.service import PipelineEvent, PipelineEventType

                await event_queue.put(
                    PipelineEvent(
                        PipelineEventType.AGENT_TEAM_COMPLETED,
                        {"team_id": team_id, "status": "failed", "error": str(e)[:200]},
                        step_name="dispatch",
                    )
                )
            return DispatchResult(
                route=ExecutionRoute.TEAM,
                response_text=f"Team execution failed: {str(e)[:200]}",
                duration_ms=(time.time() - start) * 1000,
                status="failed",
            )

    def _create_llm_service(self) -> Any:
        """Create LLM service with chat_with_tools support.

        Same pattern as PoC execution.py:250-252.
        """
        from src.integrations.llm.factory import LLMServiceFactory

        return LLMServiceFactory.create(use_cache=True)

    def _create_tool_registry(self) -> Any:
        """Create tool registry for agent tool execution.

        Same pattern as PoC execution.py:254-257.
        Returns None if registry is unavailable (agents run without tools).
        """
        try:
            from src.integrations.hybrid.orchestrator.tools import (
                OrchestratorToolRegistry,
            )

            return OrchestratorToolRegistry()
        except Exception as e:
            logger.warning("Tool registry unavailable, agents run without tools: %s", str(e)[:100])
            return None

    async def _decompose_task(
        self,
        request: DispatchRequest,
        llm_service: Any,
        tool_registry: Any,
    ) -> List[Any]:
        """Decompose task into sub-tasks using TaskDecomposer.

        Falls back to default team composition if decomposition fails.
        """
        try:
            from src.integrations.swarm.task_decomposer import TaskDecomposer

            tool_names = []
            if tool_registry and hasattr(tool_registry, "list_tools"):
                tool_names = [t.name for t in tool_registry.list_tools(role="admin")]
            elif tool_registry and hasattr(tool_registry, "get_openai_tool_schemas"):
                schemas = tool_registry.get_openai_tool_schemas(role="admin")
                tool_names = [s.get("function", {}).get("name", "") for s in schemas]

            decomposer = TaskDecomposer(
                llm_service=llm_service,
                tool_names=tool_names,
            )
            result = await decomposer.decompose(request.task)

            if result.sub_tasks:
                logger.info(
                    "TeamExecutor: Decomposed into %d sub-tasks (mode=%s)",
                    len(result.sub_tasks), result.mode,
                )
                return result.sub_tasks

        except Exception as e:
            logger.warning(
                "Task decomposition failed, using default team: %s", str(e)[:100]
            )

        # Fallback: default team as DecomposedTask objects
        return self._default_team_tasks(request)

    def _default_team_tasks(self, request: DispatchRequest) -> List[Any]:
        """Create default team as DecomposedTask objects."""
        from src.integrations.swarm.task_decomposer import DecomposedTask

        return [
            DecomposedTask(
                task_id=uuid.uuid4().hex[:8],
                title="Investigator",
                description=f"Analyze the problem and gather evidence.\n\nTask: {request.task}",
                role="general",
                tools_needed=["search_knowledge", "search_memory"],
            ),
            DecomposedTask(
                task_id=uuid.uuid4().hex[:8],
                title="Specialist",
                description=f"Apply domain expertise to diagnose root cause.\n\nTask: {request.task}",
                role="general",
                tools_needed=["search_knowledge", "assess_risk"],
            ),
            DecomposedTask(
                task_id=uuid.uuid4().hex[:8],
                title="Advisor",
                description=f"Recommend solutions based on best practices.\n\nTask: {request.task}",
                role="general",
                tools_needed=["search_knowledge"],
            ),
        ]

    async def _run_worker(
        self,
        sub_task: Any,
        llm_service: Any,
        tool_registry: Any,
        event_queue: Optional[asyncio.Queue],
        team_id: str,
    ) -> AgentResult:
        """Run a single worker using SwarmWorkerExecutor.

        Same pattern as PoC execution.py:291-301.
        """
        from src.integrations.swarm.worker_executor import (
            SwarmWorkerExecutor,
        )

        worker_id = f"w-{sub_task.task_id}"

        # Create event adapter (bridges SWARM_WORKER_* → AGENT_MEMBER_* + Queue)
        emitter = EventQueueAdapter(event_queue, team_id) if event_queue else None

        executor = SwarmWorkerExecutor(
            worker_id=worker_id,
            task=sub_task,
            llm_service=llm_service,
            tool_registry=tool_registry,
            event_emitter=emitter,
            timeout=60.0,
        )

        worker_result = await executor.execute()

        return AgentResult(
            agent_name=sub_task.title,
            role=sub_task.role,
            output=worker_result.content,
            duration_ms=worker_result.duration_ms,
            status=worker_result.status,
        )

    @staticmethod
    def _synthesize(results: List[AgentResult]) -> str:
        """Combine team agent results into a summary."""
        parts = []
        for r in results:
            status_icon = "✓" if r.status == "completed" else "✗"
            parts.append(f"**{r.agent_name}** [{status_icon}]:\n{r.output}")
        return "\n\n---\n\n".join(parts)

"""
SubagentExecutor — Parallel independent agent execution via SwarmWorkerExecutor.

Delegates to the PoC-proven SwarmWorkerExecutor for real LLM + tool execution.
Unlike TeamExecutor (sequential with shared context), SubagentExecutor runs
all agents in parallel via asyncio.gather.

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


class SubagentExecutor(BaseExecutor):
    """Execute independent parallel sub-tasks via multiple agents.

    Uses SwarmWorkerExecutor (PoC-proven) for each agent, running them
    concurrently via asyncio.gather with a semaphore for concurrency control.
    """

    def __init__(self, llm_client: Optional[Any] = None, model: Optional[str] = None):
        self._llm_client = llm_client
        self._model = model

    @property
    def name(self) -> str:
        return "subagent"

    async def _execute(
        self,
        request: DispatchRequest,
        event_queue: Optional[asyncio.Queue] = None,
    ) -> DispatchResult:
        start = time.time()
        team_id = f"subagent-{uuid.uuid4().hex[:8]}"

        try:
            # Create LLM service and tool registry (same as TeamExecutor)
            from src.integrations.llm.factory import LLMServiceFactory

            llm_service = LLMServiceFactory.create(use_cache=True)

            # Create tool registry with team collaboration tools
            from .team_tool_registry import TeamToolRegistry

            base_registry = None
            try:
                from src.integrations.hybrid.orchestrator.tools import (
                    OrchestratorToolRegistry,
                )
                base_registry = OrchestratorToolRegistry()
            except Exception as e:
                logger.info("Base tool registry unavailable: %s", str(e)[:100])
            tool_registry = TeamToolRegistry(base_registry=base_registry)

            # Decompose task with complexity-aware TaskDecomposer
            # CC pattern: agent count scales dynamically with task complexity
            sub_tasks = await self._decompose_task(request, llm_service, tool_registry)

            # Emit AGENT_TEAM_CREATED
            if event_queue is not None:
                from ...pipeline.service import PipelineEvent, PipelineEventType

                await event_queue.put(
                    PipelineEvent(
                        PipelineEventType.AGENT_TEAM_CREATED,
                        {
                            "team_id": team_id,
                            "mode": "parallel",
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

            # Run workers in parallel (same pattern as PoC execution.py:287-303)
            max_concurrent = 3
            semaphore = asyncio.Semaphore(max_concurrent)

            async def _run_with_semaphore(sub_task: Any) -> AgentResult:
                async with semaphore:
                    return await self._run_worker(
                        sub_task, llm_service, tool_registry, event_queue, team_id
                    )

            results_or_errors = await asyncio.gather(
                *[_run_with_semaphore(t) for t in sub_tasks],
                return_exceptions=True,
            )

            # Collect results
            results: List[AgentResult] = []
            for r in results_or_errors:
                if isinstance(r, AgentResult):
                    results.append(r)
                elif isinstance(r, Exception):
                    results.append(
                        AgentResult(
                            agent_name="error",
                            output=f"Agent failed: {str(r)[:200]}",
                            status="failed",
                        )
                    )

            synthesis = self._synthesize(results)

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
                            "completed_agents": len(results),
                            "duration_ms": round((time.time() - start) * 1000),
                            "completed_at": datetime.now(timezone.utc).isoformat(),
                        },
                        step_name="dispatch",
                    )
                )

            return DispatchResult(
                route=ExecutionRoute.SUBAGENT,
                response_text=synthesis,
                agent_results=results,
                synthesis=synthesis,
                duration_ms=(time.time() - start) * 1000,
                status="completed",
            )

        except Exception as e:
            logger.error("SubagentExecutor failed: %s", str(e)[:200], exc_info=True)
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
                route=ExecutionRoute.SUBAGENT,
                response_text=f"Subagent execution failed: {str(e)[:200]}",
                duration_ms=(time.time() - start) * 1000,
                status="failed",
            )

    async def _decompose_task(
        self,
        request: DispatchRequest,
        llm_service: Any,
        tool_registry: Any,
    ) -> List[Any]:
        """Decompose task using complexity-aware TaskDecomposer.

        Uses pipeline context (risk_level, intent_summary) to infer
        task complexity and guide the LLM toward an appropriate agent count.
        Falls back to simple decomposition if TaskDecomposer fails.
        """
        try:
            from src.integrations.swarm.task_decomposer import TaskDecomposer

            tool_names: List[str] = []
            if tool_registry and hasattr(tool_registry, "list_tools"):
                tool_names = [t.name for t in tool_registry.list_tools(role="admin")]
            elif tool_registry and hasattr(tool_registry, "get_openai_tool_schemas"):
                schemas = tool_registry.get_openai_tool_schemas(role="admin")
                tool_names = [s.get("function", {}).get("name", "") for s in schemas]

            complexity_hint = self._infer_complexity(request)
            decomposer = TaskDecomposer(
                llm_service=llm_service,
                tool_names=tool_names,
            )
            result = await decomposer.decompose(
                request.task, complexity_hint=complexity_hint
            )

            if result.sub_tasks:
                logger.info(
                    "SubagentExecutor: Decomposed into %d sub-tasks "
                    "(mode=%s, complexity=%s)",
                    len(result.sub_tasks), result.mode, complexity_hint,
                )
                return result.sub_tasks

        except Exception as e:
            logger.warning(
                "Task decomposition failed, using fallback: %s", str(e)[:100]
            )

        # Fallback: single general agent
        from src.integrations.swarm.task_decomposer import DecomposedTask

        return [
            DecomposedTask(
                task_id=uuid.uuid4().hex[:8],
                title="GeneralAgent",
                description=request.task,
                role="general",
            )
        ]

    @staticmethod
    def _infer_complexity(request: DispatchRequest) -> str:
        """Infer task complexity from pipeline context.

        Uses risk_level and intent_summary already populated by
        Steps 3-5 of the pipeline to guide TaskDecomposer.

        Returns:
            "simple", "moderate", "complex", or "auto".
        """
        risk = (request.risk_level or "").upper()
        intent = (request.intent_summary or "").upper()

        # High/Critical risk or INCIDENT → complex (needs thorough investigation)
        if risk in ("CRITICAL", "HIGH") or "INCIDENT" in intent:
            return "complex"

        # Low risk + QUERY → simple (likely a straightforward question)
        if risk == "LOW" and "QUERY" in intent:
            return "simple"

        # Medium risk or REQUEST/CHANGE → moderate
        if risk == "MEDIUM" or "REQUEST" in intent or "CHANGE" in intent:
            return "moderate"

        # Default: let LLM decide
        return "auto"

    async def _run_worker(
        self,
        sub_task: Any,
        llm_service: Any,
        tool_registry: Any,
        event_queue: Optional[asyncio.Queue],
        team_id: str,
    ) -> AgentResult:
        """Run a single worker using SwarmWorkerExecutor."""
        from src.integrations.swarm.worker_executor import SwarmWorkerExecutor

        worker_id = f"w-{sub_task.task_id}"
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

        # Emit full result data (messages, thinking_steps, tool_calls)
        if event_queue is not None:
            from ...pipeline.service import PipelineEvent, PipelineEventType

            if worker_result.messages:
                for msg in worker_result.messages:
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    if role and content and role != "system":
                        await event_queue.put(
                            PipelineEvent(
                                PipelineEventType.AGENT_MEMBER_THINKING,
                                {
                                    "team_id": team_id,
                                    "agent_id": worker_id,
                                    "thinking_content": f"[{role}] {content[:1000]}",
                                    "message_role": role,
                                    "timestamp": "",
                                },
                                step_name="dispatch",
                            )
                        )

        return AgentResult(
            agent_name=sub_task.title,
            role=sub_task.role,
            output=worker_result.content,
            duration_ms=worker_result.duration_ms,
            status=worker_result.status,
        )

    @staticmethod
    def _synthesize(results: List[AgentResult]) -> str:
        """Combine multiple agent results into a summary."""
        parts = []
        for r in results:
            status_icon = "✓" if r.status == "completed" else "✗"
            parts.append(f"**{r.agent_name}** [{status_icon}]:\n{r.output}")
        return "\n\n---\n\n".join(parts)

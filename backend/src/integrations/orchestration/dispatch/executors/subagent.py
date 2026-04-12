"""
SubagentExecutor — Parallel independent agent execution.

Launches multiple MAF agents in parallel, each performing an independent
sub-task. Results are aggregated into a combined response.

Phase 45: Orchestration Core (Sprint 155)
Phase 45: Rich AGENT_TEAM_* events for Agent Team Visualization
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..models import AgentResult, DispatchRequest, DispatchResult, ExecutionRoute
from .base import BaseExecutor

logger = logging.getLogger(__name__)


class SubagentExecutor(BaseExecutor):
    """Execute independent parallel sub-tasks via multiple agents.

    Decomposes the task into independent sub-tasks, creates an agent
    for each, and runs them concurrently via asyncio.gather.
    Each agent writes to its own transcript sidechain.
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
        team_id = f"subagent-{int(time.time() * 1000)}"

        try:
            # Decompose task into sub-tasks
            sub_tasks = self._decompose_task(request)

            if not sub_tasks:
                sub_tasks = [{"name": "GeneralAgent", "task": request.task}]

            # Emit AGENT_TEAM_CREATED with full roster
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
                                    "agent_id": st["name"],
                                    "agent_name": st["name"],
                                    "role": st.get("role", "specialist"),
                                }
                                for st in sub_tasks
                            ],
                            "total_agents": len(sub_tasks),
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        },
                        step_name="dispatch",
                    )
                )

            # Run agents in parallel
            agent_coros = [
                self._run_agent(st, request, event_queue, team_id)
                for st in sub_tasks
            ]
            agent_results = await asyncio.gather(*agent_coros, return_exceptions=True)

            # Collect results
            results: List[AgentResult] = []
            for r in agent_results:
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

            # Synthesize
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
            logger.error("SubagentExecutor failed: %s", str(e)[:200])
            if event_queue is not None:
                from ...pipeline.service import PipelineEvent, PipelineEventType

                await event_queue.put(
                    PipelineEvent(
                        PipelineEventType.AGENT_TEAM_COMPLETED,
                        {
                            "team_id": team_id,
                            "status": "failed",
                            "error": str(e)[:200],
                        },
                        step_name="dispatch",
                    )
                )
            return DispatchResult(
                route=ExecutionRoute.SUBAGENT,
                response_text=f"Subagent execution failed: {str(e)[:200]}",
                duration_ms=(time.time() - start) * 1000,
                status="failed",
            )

    def _decompose_task(self, request: DispatchRequest) -> List[Dict[str, str]]:
        """Simple task decomposition based on request context.

        Returns list of {name, task, role} dicts for each sub-agent.
        """
        # Use route_reasoning and intent to determine sub-tasks
        task_lower = request.task.lower()

        # Pattern: "check X, Y, and Z" → 3 parallel agents
        if any(w in task_lower for w in ["and", "，", ",", "、"]):
            parts = []
            for sep in [" and ", "，", ", ", "、"]:
                if sep in request.task:
                    parts = [p.strip() for p in request.task.split(sep) if p.strip()]
                    break

            if len(parts) >= 2:
                return [
                    {"name": f"Agent-{i+1}", "task": part, "role": "specialist"}
                    for i, part in enumerate(parts[:5])
                ]

        # Default: single agent
        return [{"name": "GeneralAgent", "task": request.task, "role": "generalist"}]

    async def _run_agent(
        self,
        sub_task: Dict[str, str],
        request: DispatchRequest,
        event_queue: Optional[asyncio.Queue] = None,
        team_id: str = "",
    ) -> AgentResult:
        """Run a single sub-agent."""
        agent_name = sub_task["name"]
        task_text = sub_task["task"]
        start = time.time()

        # Emit AGENT_MEMBER_STARTED
        if event_queue is not None:
            from ...pipeline.service import PipelineEvent, PipelineEventType

            await event_queue.put(
                PipelineEvent(
                    PipelineEventType.AGENT_MEMBER_STARTED,
                    {
                        "team_id": team_id,
                        "agent_id": agent_name,
                        "agent_name": agent_name,
                        "role": sub_task.get("role", "specialist"),
                        "started_at": datetime.now(timezone.utc).isoformat(),
                    },
                    step_name="dispatch",
                )
            )
            # Backward compat
            await event_queue.put(
                PipelineEvent(
                    PipelineEventType.AGENT_THINKING,
                    {"agent_name": agent_name, "task": task_text[:100]},
                    step_name="dispatch",
                )
            )

        # Emit AGENT_MEMBER_TOOL_CALL (LLM inference start)
        if event_queue is not None:
            await event_queue.put(
                PipelineEvent(
                    PipelineEventType.AGENT_MEMBER_TOOL_CALL,
                    {
                        "team_id": team_id,
                        "agent_id": agent_name,
                        "tool_call_id": f"llm-{agent_name}",
                        "tool_name": "llm_inference",
                        "status": "running",
                        "input_args": {"task": task_text[:100]},
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    step_name="dispatch",
                )
            )

        try:
            import os

            from openai import AzureOpenAI

            client = self._llm_client or AzureOpenAI(
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                api_version=os.getenv(
                    "AZURE_OPENAI_API_VERSION", "2024-02-15-preview"
                ),
            )

            response = client.chat.completions.create(
                model=self._model
                or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5.4-mini"),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"You are {agent_name}, an IT operations specialist. "
                            f"Complete this sub-task concisely.\n"
                            f"Context: {request.knowledge_text[:500]}"
                        ),
                    },
                    {"role": "user", "content": task_text},
                ],
                max_completion_tokens=1024,
                temperature=0.5,
            )
            output = response.choices[0].message.content or ""

        except Exception as e:
            output = f"Agent error: {str(e)[:150]}"
            logger.warning("Subagent %s failed: %s", agent_name, str(e)[:100])

        duration = (time.time() - start) * 1000

        if event_queue is not None:
            from ...pipeline.service import PipelineEvent, PipelineEventType

            # Emit AGENT_MEMBER_TOOL_CALL (completed)
            await event_queue.put(
                PipelineEvent(
                    PipelineEventType.AGENT_MEMBER_TOOL_CALL,
                    {
                        "team_id": team_id,
                        "agent_id": agent_name,
                        "tool_call_id": f"llm-{agent_name}",
                        "tool_name": "llm_inference",
                        "status": "completed",
                        "output_result": {"preview": output[:200]},
                        "duration_ms": round(duration),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    step_name="dispatch",
                )
            )

            # Emit AGENT_MEMBER_COMPLETED
            await event_queue.put(
                PipelineEvent(
                    PipelineEventType.AGENT_MEMBER_COMPLETED,
                    {
                        "team_id": team_id,
                        "agent_id": agent_name,
                        "agent_name": agent_name,
                        "status": "completed",
                        "output": output[:300],
                        "duration_ms": round(duration),
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                    },
                    step_name="dispatch",
                )
            )
            # Backward compat
            await event_queue.put(
                PipelineEvent(
                    PipelineEventType.AGENT_COMPLETE,
                    {
                        "agent_name": agent_name,
                        "output_preview": output[:200],
                        "duration_ms": round(duration),
                    },
                    step_name="dispatch",
                )
            )

        return AgentResult(
            agent_name=agent_name,
            role=sub_task.get("role", "specialist"),
            output=output,
            duration_ms=duration,
            status="completed" if "error" not in output.lower()[:20] else "failed",
        )

    @staticmethod
    def _synthesize(results: List[AgentResult]) -> str:
        """Combine multiple agent results into a summary."""
        parts = []
        for r in results:
            status_icon = "✓" if r.status == "completed" else "✗"
            parts.append(f"**{r.agent_name}** [{status_icon}]:\n{r.output}")

        return "\n\n---\n\n".join(parts)

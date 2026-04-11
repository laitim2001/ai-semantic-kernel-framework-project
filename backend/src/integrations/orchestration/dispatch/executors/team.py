"""
TeamExecutor — Collaborative expert agent execution.

Launches a team of specialized agents that can exchange information
and build on each other's findings. A TeamLead coordinates and
synthesizes the final output.

Phase 45: Orchestration Core (Sprint 155)
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from ..models import AgentResult, DispatchRequest, DispatchResult, ExecutionRoute
from .base import BaseExecutor

logger = logging.getLogger(__name__)

# Default team composition for different intent categories
DEFAULT_TEAM = [
    {"name": "Investigator", "role": "Analyze the problem and gather evidence"},
    {"name": "Specialist", "role": "Apply domain expertise to diagnose root cause"},
    {"name": "Advisor", "role": "Recommend solutions based on best practices"},
]


class TeamExecutor(BaseExecutor):
    """Execute complex tasks via collaborative expert agents.

    Unlike SubagentExecutor (parallel, independent), TeamExecutor
    runs agents sequentially with shared context — each agent sees
    the output of prior agents, building toward a synthesis.
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

        try:
            team = self._build_team(request)
            shared_context: List[str] = []
            agent_results: List[AgentResult] = []

            # Sequential execution with shared context
            for member in team:
                result = await self._run_team_member(
                    member, request, shared_context, event_queue
                )
                agent_results.append(result)
                shared_context.append(
                    f"[{member['name']}]: {result.output[:500]}"
                )

            # TeamLead synthesis
            synthesis = await self._synthesize(
                request, agent_results, event_queue
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
            logger.error("TeamExecutor failed: %s", str(e)[:200])
            return DispatchResult(
                route=ExecutionRoute.TEAM,
                response_text=f"Team execution failed: {str(e)[:200]}",
                duration_ms=(time.time() - start) * 1000,
                status="failed",
            )

    def _build_team(self, request: DispatchRequest) -> List[Dict[str, str]]:
        """Build team composition based on task context."""
        return list(DEFAULT_TEAM)

    async def _run_team_member(
        self,
        member: Dict[str, str],
        request: DispatchRequest,
        shared_context: List[str],
        event_queue: Optional[asyncio.Queue] = None,
    ) -> AgentResult:
        """Run a single team member with shared context."""
        agent_name = member["name"]
        start = time.time()

        if event_queue is not None:
            from ...pipeline.service import PipelineEvent, PipelineEventType

            await event_queue.put(
                PipelineEvent(
                    PipelineEventType.AGENT_THINKING,
                    {"agent_name": agent_name, "role": member["role"]},
                    step_name="dispatch",
                )
            )

        try:
            import os

            from openai import AzureOpenAI

            client = self._llm_client or AzureOpenAI(
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            )

            # Build context from prior agents
            prior = ""
            if shared_context:
                prior = "\n\n## Prior Team Findings\n" + "\n".join(shared_context)

            response = client.chat.completions.create(
                model=self._model or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"You are {agent_name}, an IT expert. "
                            f"Your role: {member['role']}\n"
                            f"Context: {request.knowledge_text[:500]}"
                            f"{prior}"
                        ),
                    },
                    {"role": "user", "content": request.task},
                ],
                max_completion_tokens=1024,
                temperature=0.5,
            )
            output = response.choices[0].message.content or ""

        except Exception as e:
            output = f"Agent error: {str(e)[:150]}"

        duration = (time.time() - start) * 1000

        if event_queue is not None:
            from ...pipeline.service import PipelineEvent, PipelineEventType

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
            role=member["role"],
            output=output,
            duration_ms=duration,
            status="completed",
        )

    async def _synthesize(
        self,
        request: DispatchRequest,
        results: List[AgentResult],
        event_queue: Optional[asyncio.Queue] = None,
    ) -> str:
        """TeamLead synthesizes all agent findings."""
        try:
            import os

            from openai import AzureOpenAI

            client = self._llm_client or AzureOpenAI(
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            )

            findings = "\n\n".join(
                f"**{r.agent_name}** ({r.role}):\n{r.output}" for r in results
            )

            response = client.chat.completions.create(
                model=self._model or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are the Team Lead. Synthesize the team's findings "
                            "into a clear, actionable summary for the user."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Task: {request.task}\n\n"
                            f"## Team Findings\n{findings}"
                        ),
                    },
                ],
                max_completion_tokens=1500,
                temperature=0.5,
            )
            return response.choices[0].message.content or findings

        except Exception as e:
            logger.warning("Synthesis failed, returning raw findings: %s", str(e)[:100])
            return "\n\n---\n\n".join(f"**{r.agent_name}**: {r.output}" for r in results)

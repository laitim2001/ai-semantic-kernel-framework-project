"""
TeamExecutor — Collaborative expert agent execution via SwarmWorkerExecutor.

Delegates to the PoC-proven SwarmWorkerExecutor for real LLM + tool execution
with thinking visualization, real tool calls, and agent interaction events.

Phase 45: Orchestration Core
Phase 45: Integrated PoC SwarmWorkerExecutor (replaces simplified LLM-only version)
"""

import asyncio
import logging
import os
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

            # Phase 7: Pre-execution memory retrieval (PoC memory_integration.py)
            mem_integration = None
            memory_context = ""
            try:
                from src.integrations.poc.memory_integration import create_memory_integration

                mem_integration = await create_memory_integration()
                if mem_integration:
                    memory_context = await mem_integration.retrieve_for_goal(
                        goal=request.task, user_id=request.user_id or "system"
                    )
                    if memory_context:
                        logger.info("TeamExecutor: injected %d chars of past findings", len(memory_context))
            except Exception as e:
                logger.info("Memory retrieval skipped: %s", str(e)[:100])

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

            # Phase 5: run_parallel_team — PoC's 3-Phase persistent agent loop
            # Phase 0 skipped (production uses TaskDecomposer)
            # Phase 2 skipped (production uses _synthesize_with_llm)
            from src.integrations.poc.shared_task_list import create_shared_task_list
            from src.integrations.poc.agent_work_loop import (
                run_parallel_team, AgentConfig, TeamResult as PoCTeamResult,
            )
            from .team_agent_adapter import TeamAgentAdapter
            from .pipeline_emitter_bridge import PipelineEmitterBridge

            # Create SharedTaskList and populate with decomposed tasks
            shared = create_shared_task_list(session_id=team_id)
            for t in sub_tasks:
                shared.add_task(
                    task_id=t.task_id,
                    description=t.description,
                    priority=getattr(t, "priority", 1),
                    required_expertise=t.role,
                )
            logger.info("TeamExecutor: SharedTaskList populated with %d tasks", shared.task_count())

            # Build AgentConfig list with role-specific instructions
            from src.integrations.swarm.worker_roles import get_role
            agents_config = []
            for t in sub_tasks:
                role_def = get_role(t.role)
                agents_config.append(AgentConfig(
                    name=t.title,
                    instructions=role_def.get("system_prompt", ""),
                    expertise=t.role,
                    tools=[],  # tools provided via TeamAgentAdapter's registry
                ))

            # Bridge: client_factory returns TeamAgentAdapter (MAF Agent compatible)
            def client_factory():
                adapter = TeamAgentAdapter(
                    llm_service=llm_service,
                    tool_registry=tool_registry,
                    name="Agent",
                    instructions="",
                )
                return adapter

            # Bridge: PipelineEmitterBridge maps PoC events → Production Queue
            emitter = PipelineEmitterBridge(event_queue, team_id) if event_queue else None

            # Communication window from env
            comm_window = float(os.getenv("TEAM_COMM_WINDOW_SECONDS", "0"))

            # Run the PoC's proven 3-phase parallel engine
            try:
                team_result = await run_parallel_team(
                    task=request.task,
                    context=memory_context or "",
                    agents_config=agents_config,
                    shared=shared,
                    client_factory=client_factory,
                    lead_tools=[],
                    emitter=emitter,
                    timeout=float(os.getenv("TEAM_TIMEOUT_SECONDS", "180")),
                    comm_window=comm_window,
                    session_id=team_id,
                    skip_phase0=True,   # Production uses TaskDecomposer
                    skip_phase2=True,   # Production uses _synthesize_with_llm
                )
                logger.info(
                    "run_parallel_team completed: reason=%s, agents=%d",
                    team_result.termination_reason,
                    len(team_result.agent_results),
                )
            except Exception as rpt_err:
                logger.error("run_parallel_team failed: %s", rpt_err, exc_info=True)
                team_result = PoCTeamResult(
                    shared_state={},
                    agent_results={},
                    termination_reason=f"error: {str(rpt_err)[:100]}",
                )

            # Convert PoC TeamResult (dict) → Production AgentResult list
            agent_results: List[AgentResult] = []
            for agent_name, output in team_result.agent_results.items():
                status = "completed"
                if output.startswith("ERROR:"):
                    status = "failed"
                elif output.startswith("CANCELLED"):
                    status = "cancelled"
                agent_results.append(AgentResult(
                    agent_name=agent_name,
                    role="team",
                    output=output,
                    duration_ms=0,
                    status=status,
                ))

            # Phase 2: LLM Synthesis (PoC pattern — unified analysis report)
            synthesis = await self._synthesize_with_llm(
                agent_results, request.task, llm_service, event_queue, team_id
            )

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

            # Phase 7: Post-execution memory storage (PoC memory_integration.py)
            if mem_integration and synthesis:
                try:
                    agent_results_dict = {r.agent_name: r.output for r in agent_results}
                    await mem_integration.store_synthesis(
                        team_id, request.task, synthesis, agent_results_dict
                    )
                    logger.info("TeamExecutor: stored synthesis to memory (%d chars)", len(synthesis))
                except Exception as e:
                    logger.info("Memory storage skipped: %s", str(e)[:100])

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
        """Create tool registry with team collaboration tools.

        Provides SharedTaskList-based team tools (send_team_message,
        check_my_inbox, claim_next_task, etc.) merged with any available
        base registry tools (search_knowledge, assess_risk, etc.).
        """
        from .team_tool_registry import TeamToolRegistry

        base_registry = None
        try:
            from src.integrations.hybrid.orchestrator.tools import (
                OrchestratorToolRegistry,
            )
            base_registry = OrchestratorToolRegistry()
        except Exception as e:
            logger.info("Base tool registry unavailable: %s", str(e)[:100])

        return TeamToolRegistry(base_registry=base_registry)

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

        # Emit full result data (messages, thinking_steps, tool_calls)
        # that SwarmWorkerExecutor doesn't emit in real-time events
        if event_queue is not None:
            from ...pipeline.service import PipelineEvent, PipelineEventType

            # Emit messages as conversation history
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
                                    "thinking_content": f"[{role}] {content}",
                                    "message_role": role,
                                    "timestamp": "",
                                },
                                step_name="dispatch",
                            )
                        )

        # Safety net: if worker returned empty content, force a direct LLM call
        final_content = worker_result.content or ""
        if not final_content.strip():
            logger.warning(
                "Worker %s returned empty content (status=%s, tool_calls=%d), forcing direct LLM",
                worker_id, worker_result.status, len(worker_result.tool_calls_made or []),
            )
            try:
                final_content = await llm_service.generate(
                    prompt=(
                        f"你是 {sub_task.title}。\n\n"
                        f"## 任務\n{sub_task.description}\n\n"
                        f"請直接用你的專業知識分析並回答。給出具體的診斷結果和建議。"
                    ),
                    max_tokens=2048,
                    temperature=0.7,
                )
            except Exception as e:
                logger.error("Direct LLM fallback failed for %s: %s", worker_id, e)
                final_content = f"Agent {sub_task.title} 分析完成，但無法生成詳細報告。"

        return AgentResult(
            agent_name=sub_task.title,
            role=sub_task.role,
            output=final_content,
            duration_ms=worker_result.duration_ms,
            status=worker_result.status,
        )

    async def _synthesize_with_llm(
        self,
        results: List[AgentResult],
        task: str,
        llm_service: Any,
        event_queue: Optional[asyncio.Queue] = None,
        team_id: str = "",
    ) -> str:
        """Synthesize team results via LLM — PoC Phase 2 pattern.

        Produces a unified analysis report instead of concatenated agent outputs.
        Falls back to static concatenation if LLM call fails.
        """
        # Build findings from agent outputs (PoC agent_work_loop.py L843-847)
        findings = "\n\n".join(
            f"## {r.agent_name}\n{r.output[:2000]}"
            for r in results
            if r.output and r.status == "completed"
        )

        if not findings.strip():
            return self._synthesize_static(results)

        # Emit synthesis start event
        if event_queue is not None:
            from ...pipeline.service import PipelineEvent, PipelineEventType

            await event_queue.put(
                PipelineEvent(
                    PipelineEventType.AGENT_MEMBER_THINKING,
                    {
                        "team_id": team_id,
                        "agent_id": "team-lead",
                        "thinking_content": "Synthesizing team findings...",
                        "phase": "synthesis",
                    },
                    step_name="dispatch",
                )
            )

        # PoC synthesis prompt (agent_work_loop.py L851-867)
        synthesis_prompt = (
            f"You are the TeamLead synthesizing findings from your expert team.\n\n"
            f"ORIGINAL TASK:\n{task}\n\n"
            f"TEAM FINDINGS:\n{findings}\n\n"
            f"Produce a UNIFIED ANALYSIS REPORT that:\n"
            f"1. Summarizes the key findings from each expert\n"
            f"2. Identifies cross-cutting patterns and correlations between findings\n"
            f"3. Provides a prioritized root cause assessment\n"
            f"4. Gives specific, actionable next steps\n"
            f"5. Highlights any gaps or areas needing further investigation\n\n"
            f"Write as a professional incident report, not a collection of individual reports.\n"
            f"請用繁體中文回覆。"
        )

        try:
            synthesis = await llm_service.generate(
                prompt=synthesis_prompt,
                max_tokens=4096,
                temperature=0.7,
            )
            if synthesis and synthesis.strip():
                logger.info("LLM synthesis completed (%d chars)", len(synthesis))
                return synthesis
        except Exception as e:
            logger.warning("LLM synthesis failed, falling back to static: %s", str(e)[:100])

        return self._synthesize_static(results)

    @staticmethod
    def _synthesize_static(results: List[AgentResult]) -> str:
        """Fallback: combine team agent results via string concatenation."""
        parts = []
        for r in results:
            status_icon = "✓" if r.status == "completed" else "✗"
            parts.append(f"**{r.agent_name}** [{status_icon}]:\n{r.output}")
        return "\n\n---\n\n".join(parts)

    @staticmethod
    def _classify_error(e: Exception) -> str:
        """Classify error as transient or fatal (PoC agent_work_loop.py pattern).

        Transient errors are worth retrying; fatal errors should fail immediately.
        """
        err_str = str(e).lower()
        if any(kw in err_str for kw in (
            "timeout", "429", "503", "504", "rate_limit",
            "overloaded", "connection", "reset",
        )):
            return "transient"
        if any(kw in err_str for kw in (
            "401", "403", "authentication", "forbidden",
            "invalid", "not_found", "404",
        )):
            return "fatal"
        return "unknown"

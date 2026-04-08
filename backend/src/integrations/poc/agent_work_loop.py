"""Parallel Agent Work Loop — asyncio.gather-based team execution engine.

Replaces MAF GroupChatBuilder (turn-based) with true parallel execution,
inspired by Claude Code's InProcessBackend pattern.

Architecture:
  Phase 0: TeamLead decomposes task → SharedTaskList populated
  Phase 1: All agents run in parallel via asyncio.gather
           Each agent: check inbox → claim task → LLM + tools → report → communicate
  Phase 2: Synthesize results into final response

Equivalent to CC's Node.js model:
  AsyncLocalStorage  → Python contextvars (implicit per-task)
  Promise.all()      → asyncio.gather()
  File Mailbox       → SharedTaskList (in-memory, thread-safe)
  AbortController    → asyncio.Task.cancel()

PoC: Agent Team V2 — poc/agent-team branch.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class AgentConfig:
    """Configuration for a single parallel agent."""
    name: str
    instructions: str
    expertise: str  # keyword hints for task matching
    tools: list  # MAF @tool functions
    agent: Any = None  # populated after Agent() construction


@dataclass
class TeamResult:
    """Result from a parallel team execution."""
    shared_state: dict[str, Any]
    agent_results: dict[str, str]  # agent_name → final output
    termination_reason: str  # "all_done" | "timeout" | "no_progress"
    total_duration_ms: float = 0
    phase0_duration_ms: float = 0


# ---------------------------------------------------------------------------
# Phase 0: TeamLead task decomposition
# ---------------------------------------------------------------------------

TEAM_LEAD_PROMPT = """You are a TeamLead responsible for breaking down a complex task into specific sub-tasks.

Analyze the user's request and the available context, then call the `decompose_and_assign_tasks` tool
with a JSON array of sub-tasks. Each sub-task should have:
- "description": A clear, actionable description of what to investigate or do
- "priority": 1 (highest) to 5 (lowest)
- "required_expertise": Keywords describing what expertise is needed (e.g. "database sql", "log analysis", "network")

Create 2-6 sub-tasks depending on complexity. Be specific — each task should be independently actionable.
Do NOT create vague tasks like "investigate further". Each task should tell the agent exactly what to check."""


async def phase0_decompose(
    task: str,
    context: str,
    client,
    lead_tools: list,
    emitter=None,
) -> None:
    """TeamLead: single LLM call to decompose task into sub-tasks.

    Args:
        task: User's original request
        context: Memory/knowledge context from orchestrator pipeline
        client: MAF ChatClient (Azure/OpenAI)
        lead_tools: [decompose_and_assign_tasks] from create_lead_tools()
        emitter: PipelineEventEmitter for SSE events (optional)
    """
    from agent_framework import Agent

    if emitter:
        _patch_emitter(emitter)
        await emitter.emit_event("TASK_DISPATCHED", {
            "phase": 0, "step": "team_lead_decompose", "status": "running",
        })

    lead = Agent(
        client,
        name="TeamLead",
        instructions=TEAM_LEAD_PROMPT,
        tools=lead_tools,
    )

    prompt = f"Task: {task}"
    if context:
        prompt = f"Context:\n{context}\n\n{prompt}"

    t0 = time.time()
    try:
        response = await lead.run(prompt)
        duration_ms = round((time.time() - t0) * 1000)
        logger.info(f"Phase 0 decomposition completed in {duration_ms}ms")

        if emitter:
            await emitter.emit_event("TASK_DISPATCHED", {
                "phase": 0, "step": "team_lead_decompose", "status": "complete",
                "duration_ms": duration_ms,
            })

        return duration_ms
    except Exception as e:
        logger.error(f"Phase 0 decomposition failed: {e}")
        if emitter:
            await emitter.emit_event("TASK_DISPATCHED", {
                "phase": 0, "step": "team_lead_decompose", "status": "error",
                "error": str(e)[:200],
            })
        raise


# ---------------------------------------------------------------------------
# Phase 1: Parallel agent execution
# ---------------------------------------------------------------------------

async def _execute_agent_turn(agent, context: str, emitter, agent_name: str) -> str:
    """Execute a single LLM turn for an agent (with tool calls).

    Returns the agent's text response.
    """
    try:
        response = await agent.run(context)
        # Extract text content from response
        if hasattr(response, "content"):
            return str(response.content)
        return str(response)
    except Exception as e:
        logger.error(f"Agent {agent_name} LLM call failed: {e}")
        return f"ERROR: {str(e)[:200]}"


def _build_agent_context(
    agent_name: str,
    current_task,
    inbox_msgs: str,
    shared,
) -> str:
    """Build the context prompt for an agent's work cycle."""
    parts = []

    if inbox_msgs:
        parts.append(f"DIRECTED MESSAGES FOR YOU:\n{inbox_msgs}\n")

    if current_task:
        parts.append(
            f"YOUR CURRENT TASK [{current_task.task_id}]:\n"
            f"{current_task.description}\n"
            f"Priority: {current_task.priority}\n"
        )

    # Team status summary (concise)
    status = shared.get_status()
    parts.append(f"TEAM STATUS:\n{status}\n")

    # Recent broadcast messages
    recent = shared.get_messages(last_n=5)
    if recent and "No team messages" not in recent:
        parts.append(f"RECENT TEAM MESSAGES:\n{recent}\n")

    parts.append(
        f"INSTRUCTIONS: You are {agent_name}. "
        "Work on your current task using available tools. "
        "When done, call report_task_result with your findings. "
        "If you discover something relevant to another teammate, "
        "use send_team_message with to_agent to notify them directly. "
        "Check your inbox with check_my_inbox for any directed messages."
    )

    return "\n".join(parts)


async def _process_agent_result(
    agent_name: str,
    result_text: str,
    current_task,
    shared,
    emitter,
) -> None:
    """Process an agent's LLM response — emit SSE events."""
    if emitter:
        # Emit the agent's response as a text delta
        await emitter.emit_event("TEXT_DELTA", {
            "agent": agent_name,
            "delta": result_text[:500],
        })

        # If agent completed a task, emit task completion
        if current_task and current_task.status.value == "completed":
            await emitter.emit_event("TASK_COMPLETED", {
                "agent": agent_name,
                "task_id": current_task.task_id,
            })


async def _agent_work_loop(
    cfg: AgentConfig,
    shared,
    emitter,
    llm_semaphore: asyncio.Semaphore,
    no_progress_timeout: float = 30.0,
) -> str:
    """Single agent's autonomous work loop — runs as independent asyncio.Task.

    Loop: check inbox → claim task → build context → LLM call → process result
    Exit: shared.is_all_done() OR no_progress timeout
    """
    name = cfg.name
    agent = cfg.agent
    tools = cfg.tools
    final_output = ""

    if emitter:
        await emitter.emit_event("SWARM_WORKER_START", {"agent": name})

    iteration = 0
    max_iterations = 5  # V2: agents should finish in 1-2 iterations, 5 is safety cap

    while not shared.is_all_done() and iteration < max_iterations:
        iteration += 1

        # 1. Check inbox for directed messages
        inbox_msgs = shared.get_inbox(name, unread_only=True)

        # 2. Check if we have an in-progress task
        current_task = shared.get_agent_current_task(name)

        # 3. If no current task and no inbox, try to claim one
        if not current_task and not inbox_msgs:
            new_task = shared.claim_task(name)
            if not new_task:
                # Nothing to do — check if everyone's done
                if shared.is_all_done():
                    break
                # Check no-progress timeout
                if shared.seconds_since_last_progress() > no_progress_timeout:
                    logger.warning(f"Agent {name}: no progress for {no_progress_timeout}s, exiting")
                    break
                await asyncio.sleep(0.5)
                continue
            current_task = new_task

            if emitter:
                await emitter.emit_event("SWARM_PROGRESS", {
                    "event_type": "task_claimed",
                    "agent": name,
                    "task_id": current_task.task_id,
                    "description": current_task.description[:100],
                })

        # 4. Build context
        context = _build_agent_context(name, current_task, inbox_msgs, shared)

        # 5. Execute LLM turn (rate-limited)
        if emitter:
            await emitter.emit_event("AGENT_THINKING", {"agent": name})

        async with llm_semaphore:
            result_text = await _execute_agent_turn(agent, context, emitter, name)

        final_output = result_text

        # 6. Process results + emit events
        await _process_agent_result(name, result_text, current_task, shared, emitter)

        # 7. If task was not completed by tool calls, auto-complete with LLM output
        if current_task and current_task.status.value == "in_progress":
            shared.complete_task(current_task.task_id, result_text[:2000])
            if emitter:
                await emitter.emit_event("TASK_COMPLETED", {
                    "agent": name,
                    "task_id": current_task.task_id,
                })

    if emitter:
        await emitter.emit_event("SWARM_WORKER_END", {
            "agent": name,
            "status": "completed",
            "iterations": iteration,
        })

    return final_output


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def run_parallel_team(
    task: str,
    context: str,
    agents_config: list[AgentConfig],
    shared,
    client,
    lead_tools: list,
    emitter=None,
    llm_concurrency: int = 3,
    timeout: float = 120.0,
    no_progress_timeout: float = 30.0,
) -> TeamResult:
    """Run a team of agents in parallel with real-time communication.

    Full flow:
      Phase 0: TeamLead decomposes task → SharedTaskList populated
      Phase 1: All agents run in parallel via asyncio.gather
      Phase 2: Collect results

    Args:
        task: User's original request
        context: Memory/knowledge context from orchestrator
        agents_config: List of AgentConfig for each worker agent
        shared: SharedTaskList instance (empty, populated by Phase 0)
        client: MAF ChatClient
        lead_tools: Tools for TeamLead (decompose_and_assign_tasks)
        emitter: PipelineEventEmitter for SSE (optional)
        llm_concurrency: Max concurrent LLM calls
        timeout: Total execution timeout (seconds)
        no_progress_timeout: Per-agent no-progress timeout (seconds)
    """
    t_start = time.time()
    llm_semaphore = asyncio.Semaphore(llm_concurrency)
    agent_results: dict[str, str] = {}
    termination_reason = "all_done"

    if emitter:
        _patch_emitter(emitter)

    # ── Phase 0: TeamLead decomposition ──
    phase0_ms = 0
    try:
        phase0_ms = await phase0_decompose(task, context, client, lead_tools, emitter)
    except Exception as e:
        logger.error(f"Phase 0 failed, falling back to single task: {e}")
        # Fallback: add the entire task as a single item
        shared.add_task("T-fallback", task, priority=1)

    task_count = len(shared._tasks)
    logger.info(f"Phase 0 complete: {task_count} tasks created")

    if emitter:
        await emitter.emit_event("SWARM_PROGRESS", {
            "event_type": "phase0_complete",
            "tasks_created": task_count,
            "phase0_duration_ms": phase0_ms,
        })

    # ── Phase 1: Parallel agent execution ──
    # Build Agent instances
    from agent_framework import Agent

    for cfg in agents_config:
        cfg.agent = Agent(
            client,
            name=cfg.name,
            instructions=cfg.instructions,
            tools=cfg.tools,
        )

    agent_tasks = [
        asyncio.create_task(
            _agent_work_loop(cfg, shared, emitter, llm_semaphore, no_progress_timeout),
            name=f"agent-{cfg.name}",
        )
        for cfg in agents_config
    ]

    try:
        results = await asyncio.wait_for(
            asyncio.gather(*agent_tasks, return_exceptions=True),
            timeout=timeout,
        )
        # Collect results
        for cfg, result in zip(agents_config, results):
            if isinstance(result, Exception):
                agent_results[cfg.name] = f"ERROR: {result}"
                logger.error(f"Agent {cfg.name} failed: {result}")
            else:
                agent_results[cfg.name] = str(result)

    except asyncio.TimeoutError:
        termination_reason = "timeout"
        logger.warning(f"Team execution timed out after {timeout}s")
        for t in agent_tasks:
            if not t.done():
                t.cancel()
        # Collect whatever completed
        for cfg, t in zip(agents_config, agent_tasks):
            if t.done() and not t.cancelled():
                try:
                    agent_results[cfg.name] = str(t.result())
                except Exception as e:
                    agent_results[cfg.name] = f"ERROR: {e}"
            else:
                agent_results[cfg.name] = "CANCELLED: timeout"

    # Check if no-progress was the cause
    if termination_reason == "all_done" and not shared.is_all_done():
        termination_reason = "no_progress"

    total_ms = round((time.time() - t_start) * 1000)

    if emitter:
        await emitter.emit_event("SWARM_PROGRESS", {
            "event_type": "team_complete",
            "termination_reason": termination_reason,
            "total_duration_ms": total_ms,
            "tasks_completed": sum(
                1 for t in shared._tasks.values() if t.status.value == "completed"
            ),
            "tasks_total": len(shared._tasks),
        })

    return TeamResult(
        shared_state=shared.to_dict(),
        agent_results=agent_results,
        termination_reason=termination_reason,
        total_duration_ms=total_ms,
        phase0_duration_ms=phase0_ms,
    )


# ---------------------------------------------------------------------------
# Helper: emit_event adapter
# ---------------------------------------------------------------------------
# PipelineEventEmitter.emit() takes SSEEventType enum, but we want to call
# with string names for flexibility. This adapter handles the conversion.

async def _safe_emit(emitter, event_name: str, data: dict) -> None:
    """Emit an SSE event, gracefully handling missing event types."""
    try:
        from src.integrations.hybrid.orchestrator.sse_events import SSEEventType
        event_type = SSEEventType(event_name)
        await emitter.emit(event_type, data)
    except (ValueError, KeyError):
        # Event type not in enum yet — emit as SWARM_PROGRESS with event_type field
        from src.integrations.hybrid.orchestrator.sse_events import SSEEventType
        await emitter.emit(SSEEventType.SWARM_PROGRESS, {"event_type": event_name, **data})


# Monkey-patch emit_event onto emitter instances for convenience
def _patch_emitter(emitter):
    """Add emit_event(name, data) method to a PipelineEventEmitter."""
    if not hasattr(emitter, "emit_event"):
        async def emit_event(event_name: str, data: dict) -> None:
            await _safe_emit(emitter, event_name, data)
        emitter.emit_event = emit_event
    return emitter

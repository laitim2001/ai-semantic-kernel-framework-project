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

IMPORTANT: Create exactly 3 sub-tasks (one per available team expert).
The team has 3 experts: LogExpert (logs/errors), DBExpert (database/schema), AppExpert (network/infra).
Each task should be specific, actionable, and require THOROUGH investigation (not just surface-level checks).
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
        response = await asyncio.to_thread(_sync_agent_run, lead, prompt)
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

def _sync_agent_run(agent, context: str):
    """Run agent.run() in a fresh event loop for true thread parallelism.

    MAF Agent.run() may use synchronous HTTP internally, blocking the
    asyncio event loop. Running each agent in its own thread with a
    dedicated event loop enables true concurrent execution.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(agent.run(context))
    finally:
        loop.close()


async def _execute_agent_turn(agent, context: str, emitter, agent_name: str,
                              executor=None) -> str:
    """Execute a single LLM turn for an agent (with tool calls).

    Uses explicit ThreadPoolExecutor for true parallelism — each agent.run()
    gets its own thread + event loop, preventing connection serialization.
    """
    try:
        loop = asyncio.get_running_loop()
        t0 = time.time()
        logger.warning(f"Agent {agent_name} submitting to thread pool...")

        if executor:
            future = executor.submit(_sync_agent_run, agent, context)
            response = await asyncio.wrap_future(future)
        else:
            response = await asyncio.to_thread(_sync_agent_run, agent, context)

        duration = round((time.time() - t0) * 1000)
        logger.warning(f"Agent {agent_name} LLM turn completed in {duration}ms")

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
    msg_count_before: int = 0,
) -> None:
    """Process an agent's LLM response — emit SSE events.

    Checks for new team messages added during agent.run() and emits
    TEAM_MESSAGE SSE events for each.
    """
    if emitter:
        # Emit the agent's response as a text delta (no truncation)
        await emitter.emit_event("TEXT_DELTA", {
            "agent": agent_name,
            "delta": result_text,
        })

        # If agent completed a task, emit task completion
        if current_task and current_task.status.value == "completed":
            await emitter.emit_event("TASK_COMPLETED", {
                "agent": agent_name,
                "task_id": current_task.task_id,
            })

        # Emit TEAM_MESSAGE for any new messages added during this turn
        all_msgs = shared._messages  # direct access for SSE emission
        new_msgs = all_msgs[msg_count_before:]
        for msg in new_msgs:
            if msg.from_agent == agent_name:
                await emitter.emit_event("TEAM_MESSAGE", {
                    "from": msg.from_agent,
                    "to": msg.to_agent,
                    "content": msg.content,
                    "directed": msg.to_agent is not None,
                })


async def _agent_work_loop(
    cfg: AgentConfig,
    shared,
    emitter,
    shutdown_event: asyncio.Event,
    executor=None,
) -> str:
    """CC-like persistent agent loop with 3-phase lifecycle.

    Mirrors CC's inProcessRunner.ts pattern:
      Phase A: Active work — execute task or process inbox messages
      Phase B: Idle — no work available, notify team
      Phase C: Poll mailbox every 500ms — wait for messages or shutdown

    Agent NEVER exits on its own. Only exits when:
      - shutdown_event is set (by Lead after communication window)
      - Safety: max 10 LLM turns to prevent runaway costs
    """
    name = cfg.name
    agent = cfg.agent
    final_output = ""
    llm_turns = 0
    max_llm_turns = 10  # safety cap on LLM calls, not on loop iterations

    if emitter:
        await emitter.emit_event("SWARM_WORKER_START", {"agent": name})

    while not shutdown_event.is_set():
        # ── Phase A: Active Work ──────────────────────────────────

        # A1. Check inbox for directed messages
        inbox_msgs = shared.get_inbox(name, unread_only=True)

        if inbox_msgs and emitter:
            # Extract sender names from inbox text for SSE
            import re
            senders = re.findall(r'\[(\w+) → you\]', inbox_msgs)
            await emitter.emit_event("INBOX_RECEIVED", {
                "agent": name,
                "from": ", ".join(senders) if senders else "teammate",
                "message_count": len(senders) or 1,
            })

        # A2. Check for in-progress or claimable task
        current_task = shared.get_agent_current_task(name)
        if not current_task:
            current_task = shared.claim_task(name)
            if current_task and emitter:
                await emitter.emit_event("SWARM_PROGRESS", {
                    "event_type": "task_claimed",
                    "agent": name,
                    "task_id": current_task.task_id,
                    "description": current_task.description[:100],
                })

        # A3. If we have work (task or inbox), execute LLM turn
        if current_task or inbox_msgs:
            if llm_turns >= max_llm_turns:
                logger.warning(f"Agent {name}: max LLM turns ({max_llm_turns}) reached, entering idle")
            else:
                llm_turns += 1
                context = _build_agent_context(name, current_task, inbox_msgs, shared)
                msg_count_before = len(shared._messages)

                if emitter:
                    await emitter.emit_event("AGENT_THINKING", {"agent": name})

                result_text = await _execute_agent_turn(
                    agent, context, emitter, name, executor=executor
                )
                final_output = result_text

                await _process_agent_result(
                    name, result_text, current_task, shared, emitter, msg_count_before
                )

                # Auto-complete task if still in_progress
                if current_task and current_task.status.value == "in_progress":
                    shared.complete_task(current_task.task_id, result_text[:2000])
                    if emitter:
                        await emitter.emit_event("TASK_COMPLETED", {
                            "agent": name,
                            "task_id": current_task.task_id,
                        })

                continue  # immediately check for more work (Phase A again)

        # ── Phase B: Idle — no task, no inbox ─────────────────────
        if emitter:
            await emitter.emit_event("SWARM_PROGRESS", {
                "event_type": "agent_idle",
                "agent": name,
                "llm_turns": llm_turns,
            })

        # ── Phase C: Poll mailbox every 500ms (CC pattern) ────────
        while not shutdown_event.is_set():
            await asyncio.sleep(0.5)

            # Peek for new directed messages (without marking read — Phase A will read them)
            has_unread = shared.get_inbox_count(name, unread_only=True) > 0
            if has_unread:
                logger.info(f"Agent {name}: received message during idle, resuming")
                break  # back to Phase A (which will read + process them)

            # Check for new unclaimed tasks
            new_task = shared.claim_task(name)
            if new_task:
                logger.info(f"Agent {name}: claimed new task during idle, resuming")
                if emitter:
                    await emitter.emit_event("SWARM_PROGRESS", {
                        "event_type": "task_claimed",
                        "agent": name,
                        "task_id": new_task.task_id,
                        "description": new_task.description[:100],
                    })
                break  # back to Phase A

    # ── Shutdown ──────────────────────────────────────────────────
    if emitter:
        await emitter.emit_event("SWARM_WORKER_END", {
            "agent": name,
            "status": "shutdown",
            "llm_turns": llm_turns,
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
    client_factory,
    lead_tools: list,
    emitter=None,
    timeout: float = 120.0,
    comm_window: float = 15.0,
) -> TeamResult:
    """V3: Run agents in parallel with CC-like lifecycle management.

    Full flow:
      Phase 0: TeamLead decomposes task
      Phase 1: Agents run in parallel (persistent loop + idle polling)
      Phase 1.5: Communication window — agents stay alive 15s after all tasks done
      Lead shutdown: signal all agents to exit
      Phase 2: Lead Synthesis — unified report

    Args:
        task: User's original request
        context: Memory/knowledge context from orchestrator
        agents_config: List of AgentConfig for each worker agent
        shared: SharedTaskList instance (empty, populated by Phase 0)
        client_factory: Callable → new ChatClient (independent per agent)
        lead_tools: Tools for TeamLead (decompose_and_assign_tasks)
        emitter: PipelineEventEmitter for SSE (optional)
        timeout: Total execution timeout (seconds)
        comm_window: Communication window after all tasks done (seconds)
    """
    t_start = time.time()
    agent_results: dict[str, str] = {}
    termination_reason = "all_done"
    shutdown_event = asyncio.Event()

    if emitter:
        _patch_emitter(emitter)

    # ── Phase 0: TeamLead decomposition ──
    phase0_ms = 0
    try:
        lead_client = client_factory()
        phase0_ms = await phase0_decompose(task, context, lead_client, lead_tools, emitter)
    except Exception as e:
        logger.error(f"Phase 0 failed, falling back to single task: {e}")
        shared.add_task("T-fallback", task, priority=1)

    task_count = len(shared._tasks)
    logger.info(f"Phase 0 complete: {task_count} tasks created")

    if emitter:
        await emitter.emit_event("SWARM_PROGRESS", {
            "event_type": "phase0_complete",
            "tasks_created": task_count,
            "phase0_duration_ms": phase0_ms,
        })

    # ── Phase 1: Launch persistent agents ──
    from agent_framework import Agent
    import concurrent.futures

    _executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=len(agents_config) + 2,
        thread_name_prefix="agent-worker",
    )
    logger.info(f"=== V3 PARALLEL ENGINE: {len(agents_config)} agents, comm_window={comm_window}s ===")

    for cfg in agents_config:
        agent_client = client_factory()
        cfg.agent = Agent(
            agent_client,
            name=cfg.name,
            instructions=cfg.instructions,
            tools=cfg.tools,
        )

    agent_tasks = [
        asyncio.create_task(
            _agent_work_loop(cfg, shared, emitter, shutdown_event, executor=_executor),
            name=f"agent-{cfg.name}",
        )
        for cfg in agents_config
    ]

    # ── Monitor: wait for all TASKS to complete (not agents) ──
    try:
        while not shared.is_all_done():
            await asyncio.sleep(1.0)
            elapsed = time.time() - t_start
            if elapsed > timeout:
                termination_reason = "timeout"
                logger.warning(f"Team timed out after {timeout}s")
                break

        # ── Phase 1.5: Communication Window ──
        # Keep agents alive to process cross-agent messages (CC pattern)
        if termination_reason == "all_done":
            if emitter:
                await emitter.emit_event("ALL_TASKS_DONE", {
                    "reason": "all_done",
                    "tasks_completed": len(shared._tasks),
                    "tasks_total": len(shared._tasks),
                })
                await emitter.emit_event("SWARM_PROGRESS", {
                    "event_type": "communication_window",
                    "duration_s": comm_window,
                })

            logger.info(f"All tasks done. Communication window: {comm_window}s")
            await asyncio.sleep(comm_window)

    except Exception as e:
        logger.error(f"Monitor loop error: {e}")
        termination_reason = "error"

    # ── Lead Shutdown: signal all agents to exit ──
    if emitter:
        await emitter.emit_event("SWARM_PROGRESS", {
            "event_type": "shutdown_signal",
        })
    shutdown_event.set()
    logger.info("Shutdown signal sent to all agents")

    # Wait for agents to exit (with short timeout for cleanup)
    done, pending = await asyncio.wait(agent_tasks, timeout=5.0)
    for t in pending:
        t.cancel()

    # Collect results
    for cfg, at in zip(agents_config, agent_tasks):
        try:
            if at.done() and not at.cancelled():
                agent_results[cfg.name] = str(at.result())
            else:
                agent_results[cfg.name] = "CANCELLED: shutdown"
        except Exception as e:
            agent_results[cfg.name] = f"ERROR: {e}"

    # ── Phase 2: Lead Synthesis ──
    synthesis = ""
    phase2_ms = 0
    if agent_results:
        if emitter:
            await emitter.emit_event("AGENT_THINKING", {
                "agent": "TeamLead",
                "step": "synthesis",
                "status": "running",
            })

        findings = "\n\n".join(
            f"## {name}\n{output[:2000]}"
            for name, output in agent_results.items()
            if output and not output.startswith("ERROR") and not output.startswith("CANCELLED")
        )

        team_msgs = shared.get_messages(last_n=30)

        synthesis_prompt = (
            f"You are the TeamLead synthesizing findings from your expert team.\n\n"
            f"ORIGINAL TASK:\n{task}\n\n"
            f"TEAM FINDINGS:\n{findings}\n\n"
        )
        if team_msgs and "No team messages" not in team_msgs:
            synthesis_prompt += f"TEAM COMMUNICATION LOG:\n{team_msgs}\n\n"

        synthesis_prompt += (
            "Produce a UNIFIED ANALYSIS REPORT that:\n"
            "1. Summarizes the key findings from each expert\n"
            "2. Identifies cross-cutting patterns and correlations between findings\n"
            "3. Provides a prioritized root cause assessment\n"
            "4. Gives specific, actionable next steps\n"
            "5. Highlights any gaps or areas needing further investigation\n\n"
            "Write as a professional incident report, not a collection of individual reports."
        )

        t2 = time.time()
        try:
            synthesis_client = client_factory()
            from agent_framework import Agent as _Agent
            synthesis_agent = _Agent(
                synthesis_client,
                name="TeamLead-Synthesis",
                instructions="You produce clear, actionable synthesis reports from multi-expert investigations.",
            )
            synthesis_resp = await asyncio.to_thread(
                _sync_agent_run, synthesis_agent, synthesis_prompt
            )
            synthesis = str(getattr(synthesis_resp, "content", synthesis_resp))
            phase2_ms = round((time.time() - t2) * 1000)
            logger.info(f"Phase 2 synthesis completed in {phase2_ms}ms")
        except Exception as e:
            logger.error(f"Phase 2 synthesis failed: {e}")
            synthesis = findings

        if emitter:
            await emitter.emit_event("AGENT_THINKING", {
                "agent": "TeamLead",
                "step": "synthesis",
                "status": "complete",
                "duration_ms": phase2_ms,
            })

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

    result = TeamResult(
        shared_state=shared.to_dict(),
        agent_results=agent_results,
        termination_reason=termination_reason,
        total_duration_ms=total_ms,
        phase0_duration_ms=phase0_ms,
    )
    result.synthesis = synthesis  # type: ignore[attr-defined]
    result.phase2_duration_ms = phase2_ms  # type: ignore[attr-defined]
    return result


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

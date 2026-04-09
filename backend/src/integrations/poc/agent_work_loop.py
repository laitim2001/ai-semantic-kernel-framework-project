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

TEAM_LEAD_PROMPT_TEMPLATE = """You are a TeamLead responsible for breaking down a complex task into specific sub-tasks.

Analyze the user's request and the available context, then call the `decompose_and_assign_tasks` tool
with a JSON array of sub-tasks. Each sub-task should have:
- "description": A clear, actionable description of what to investigate or do
- "priority": 1 (highest) to 5 (lowest)
- "required_expertise": Keywords describing what expertise is needed (e.g. "database sql", "log analysis", "network")

IMPORTANT: Create between {min_agents} and {max_agents} sub-tasks based on the complexity of the request.
- Simple tasks (single domain): {min_agents} sub-tasks
- Moderate tasks (2-3 domains): 3-4 sub-tasks
- Complex tasks (cross-domain investigation): {max_agents} sub-tasks

Available experts: {expert_names}
Each task should be specific, actionable, and require THOROUGH investigation (not just surface-level checks).
Do NOT create vague tasks like "investigate further". Each task should tell the agent exactly what to check."""


def _build_team_lead_prompt(agent_names: list[str], min_agents: int = 2, max_agents: int = 5) -> str:
    """Build TeamLead prompt with dynamic agent count based on available experts."""
    return TEAM_LEAD_PROMPT_TEMPLATE.format(
        min_agents=min_agents,
        max_agents=min(max_agents, len(agent_names)),
        expert_names=", ".join(agent_names),
    )


# V3 backward compat: default prompt for 3 agents
TEAM_LEAD_PROMPT = _build_team_lead_prompt(
    ["LogExpert", "DBExpert", "AppExpert"], min_agents=3, max_agents=3
)


async def phase0_decompose(
    task: str,
    context: str,
    client,
    lead_tools: list,
    emitter=None,
    lead_prompt: str = "",
) -> None:
    """TeamLead: single LLM call to decompose task into sub-tasks.

    Args:
        task: User's original request
        context: Memory/knowledge context from orchestrator pipeline
        client: MAF ChatClient (Azure/OpenAI)
        lead_tools: [decompose_and_assign_tasks] from create_lead_tools()
        emitter: PipelineEventEmitter for SSE events (optional)
        lead_prompt: Custom TeamLead prompt (V4: dynamic agent count)
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
        instructions=lead_prompt or TEAM_LEAD_PROMPT,
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
                              executor=None, llm_pool=None) -> str:
    """Execute a single LLM turn for an agent (with tool calls).

    Uses explicit ThreadPoolExecutor for true parallelism — each agent.run()
    gets its own thread + event loop, preventing connection serialization.

    V4: Optional LLMCallPool integration for rate-limited concurrent access.
    Acquire slot in async context → run LLM in OS thread → release on exit.
    """
    try:
        t0 = time.time()

        if llm_pool:
            # Acquire LLM slot (async context) — blocks until slot available
            from src.core.performance.llm_pool import CallPriority
            async with await llm_pool.acquire(CallPriority.SWARM_WORKER) as token:
                logger.info(f"Agent {agent_name}: acquired LLM pool slot")
                if executor:
                    future = executor.submit(_sync_agent_run, agent, context)
                    response = await asyncio.wrap_future(future)
                else:
                    response = await asyncio.to_thread(_sync_agent_run, agent, context)
        else:
            if executor:
                future = executor.submit(_sync_agent_run, agent, context)
                response = await asyncio.wrap_future(future)
            else:
                response = await asyncio.to_thread(_sync_agent_run, agent, context)

        duration = round((time.time() - t0) * 1000)
        logger.info(f"Agent {agent_name} LLM turn completed in {duration}ms")

        if hasattr(response, "content"):
            return str(response.content)
        return str(response)
    except Exception as e:
        logger.error(f"Agent {agent_name} LLM call failed: {e}")
        raise  # V4: let retry wrapper handle it


# V4: Error classification for retry decisions
def _classify_error(e: Exception) -> str:
    """Classify an error as transient, fatal, or unknown."""
    err_str = str(e).lower()
    # Transient: worth retrying
    if any(kw in err_str for kw in ("timeout", "429", "503", "504", "rate_limit",
                                      "overloaded", "connection", "reset")):
        return "transient"
    # Fatal: don't retry
    if any(kw in err_str for kw in ("401", "403", "authentication", "forbidden",
                                      "invalid", "not_found", "404")):
        return "fatal"
    return "unknown"


async def _execute_agent_turn_with_retry(
    agent, context: str, emitter, agent_name: str,
    executor=None, max_retries: int = 2, llm_pool=None,
) -> str:
    """V4: Execute agent turn with retry for transient errors.

    Retries up to max_retries times with exponential backoff.
    Fatal errors fail immediately.
    """
    for attempt in range(max_retries + 1):
        try:
            return await _execute_agent_turn(
                agent, context, emitter, agent_name, executor, llm_pool=llm_pool
            )
        except Exception as e:
            failure_type = _classify_error(e)

            if failure_type == "fatal" or attempt >= max_retries:
                if attempt > 0:
                    logger.warning(f"Agent {agent_name}: exhausted {attempt} retries, failing")
                return f"ERROR: {str(e)[:200]}"

            delay = min(2 ** attempt, 10)  # 1s, 2s, 4s... capped at 10s
            logger.warning(
                f"Agent {agent_name}: {failure_type} error, retry {attempt + 1}/{max_retries} "
                f"in {delay}s — {str(e)[:100]}"
            )
            if emitter:
                await emitter.emit_event("SWARM_PROGRESS", {
                    "event_type": "agent_retry",
                    "agent": agent_name,
                    "attempt": attempt + 1,
                    "max_retries": max_retries,
                    "reason": str(e)[:200],
                    "failure_type": failure_type,
                })
            await asyncio.sleep(delay)

    return "ERROR: max retries exceeded"  # should not reach here


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


async def _check_task_approval(
    agent_name: str,
    current_task,
    session_id: str,
    emitter,
    approval_manager,
) -> str:
    """V4: Check if the agent's task involves high-risk tools.

    If the task description implies high-risk tool usage, request human
    approval via event-driven TeamApprovalManager (CC PermissionDecision
    equivalent — zero CPU wait, single worker OK).

    Returns "approved", "rejected", or "expired".
    """
    # Determine which tools the agent will likely use based on task keywords
    task_desc = (current_task.description or "").lower()
    tools_needing_approval = []

    if any(kw in task_desc for kw in ("command", "diagnostic", "ping", "curl", "shell")):
        tools_needing_approval.append("run_diagnostic_command")
    if any(kw in task_desc for kw in ("database", "sql", "query", "schema", "table")):
        tools_needing_approval.append("query_database")

    if not tools_needing_approval:
        return "approved"

    from src.integrations.poc.approval_gate import request_and_await_approval

    tool_name = tools_needing_approval[0]
    logger.info(f"Agent {agent_name}: task requires approval for '{tool_name}'")

    return await request_and_await_approval(
        agent_name=agent_name,
        tool_name=tool_name,
        tool_args={"task_id": current_task.task_id, "description": task_desc[:200]},
        session_id=session_id,
        emitter=emitter,
        manager=approval_manager,
        timeout_seconds=300.0,
    )


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
        new_msgs = shared.get_messages_since(msg_count_before)
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
    approval_manager=None,
    session_id: str = "",
    llm_pool=None,
) -> str:
    """CC-like persistent agent loop with 3-phase lifecycle.

    Mirrors CC's inProcessRunner.ts pattern:
      Phase A: Active work — execute task or process inbox messages
      Phase B: Idle — no work available, notify team
      Phase C: Poll mailbox every 500ms — wait for messages or shutdown

    Agent NEVER exits on its own. Only exits when:
      - shutdown_event is set (by Lead after communication window)
      - Safety: max 10 LLM turns to prevent runaway costs

    V4: approval_manager (event-driven, CC PermissionDecision equivalent).
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
                # V4: HITL approval gate — check if agent's tools need approval
                if approval_manager and current_task and llm_turns == 0:
                    approval_result = await _check_task_approval(
                        name, current_task, session_id, emitter, approval_manager
                    )
                    if approval_result == "rejected":
                        shared.fail_task(current_task.task_id, "Rejected by human reviewer")
                        if emitter:
                            await emitter.emit_event("TASK_COMPLETED", {
                                "agent": name, "task_id": current_task.task_id,
                                "status": "rejected",
                            })
                        continue  # skip to next task
                    elif approval_result == "expired":
                        shared.fail_task(current_task.task_id, "Approval timed out")
                        continue

                llm_turns += 1
                context = _build_agent_context(name, current_task, inbox_msgs, shared)
                msg_count_before = shared.message_count()

                if emitter:
                    await emitter.emit_event("AGENT_THINKING", {"agent": name})

                result_text = await _execute_agent_turn_with_retry(
                    agent, context, emitter, name, executor=executor,
                    llm_pool=llm_pool,
                )
                final_output = result_text

                # V4: Check if result is an error — handle task reassignment
                if result_text.startswith("ERROR:") and current_task:
                    retry_count = shared.get_task_retry_count(current_task.task_id)
                    if retry_count < 2:
                        shared.reassign_task(current_task.task_id)
                        logger.warning(
                            f"Agent {name}: task {current_task.task_id} reassigned "
                            f"(retry {retry_count + 1}/2)"
                        )
                        if emitter:
                            await emitter.emit_event("SWARM_PROGRESS", {
                                "event_type": "task_reassigned",
                                "agent": name,
                                "task_id": current_task.task_id,
                                "retry_number": retry_count + 1,
                            })
                    else:
                        shared.fail_task(current_task.task_id, result_text[:500])
                        if emitter:
                            await emitter.emit_event("TASK_COMPLETED", {
                                "agent": name,
                                "task_id": current_task.task_id,
                                "status": "failed",
                            })
                    continue  # try next task

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
        _shutdown_received = False
        while not shutdown_event.is_set():
            await asyncio.sleep(0.5)

            # V4: Check for SHUTDOWN_REQUEST in inbox (graceful shutdown)
            inbox_text = shared.get_inbox(name, unread_only=True)
            if inbox_text and "SHUTDOWN_REQUEST" in inbox_text:
                logger.info(f"Agent {name}: received SHUTDOWN_REQUEST, sending ACK")
                shared.add_message(from_agent=name, content="SHUTDOWN_ACK", to_agent="TeamLead")
                if emitter:
                    await emitter.emit_event("SWARM_PROGRESS", {
                        "event_type": "shutdown_ack", "agent": name,
                    })
                _shutdown_received = True
                break  # exit Phase C → exit main loop

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

        # V4: If shutdown was received in Phase C, exit main loop
        if _shutdown_received:
            break

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
    session_id: str = "",
) -> TeamResult:
    """V3/V4: Run agents in parallel with CC-like lifecycle management.

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
        session_id: Unique session ID (V4: used for Redis key prefix)
    """
    t_start = time.time()
    agent_results: dict[str, str] = {}
    termination_reason = "all_done"
    shutdown_event = asyncio.Event()

    if emitter:
        _patch_emitter(emitter)

    # ── V4: Pre-Phase 0 memory retrieval ──
    memory_integration = None
    memory_context = ""
    try:
        from src.integrations.poc.memory_integration import create_memory_integration
        memory_integration = await create_memory_integration()
        if memory_integration:
            memory_context = await memory_integration.retrieve_for_goal(
                goal=task, user_id="system"
            )
            if memory_context:
                logger.info(f"Memory: injecting {len(memory_context)} chars of past findings")
    except Exception as e:
        logger.info(f"Memory retrieval skipped: {e}")

    # ── V4: Build dynamic TeamLead prompt based on available agents ──
    import os
    max_agents = int(os.getenv("TEAM_MAX_AGENTS", str(len(agents_config))))
    agent_names = [cfg.name for cfg in agents_config]
    dynamic_lead_prompt = _build_team_lead_prompt(
        agent_names, min_agents=2, max_agents=max_agents
    )

    # ── Phase 0: TeamLead decomposition ──
    # Inject memory context into the decomposition prompt
    enriched_context = context
    if memory_context:
        enriched_context = f"{memory_context}\n\n{context}" if context else memory_context

    phase0_ms = 0
    try:
        lead_client = client_factory()
        phase0_ms = await phase0_decompose(
            task, enriched_context, lead_client, lead_tools, emitter,
            lead_prompt=dynamic_lead_prompt,
        )
    except Exception as e:
        logger.error(f"Phase 0 failed, falling back to single task: {e}")
        shared.add_task("T-fallback", task, priority=1)

    task_count = shared.task_count()
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

    # V4: Event-driven approval manager (CC PermissionDecision equivalent)
    _approval_manager = None
    try:
        from src.integrations.poc.approval_gate import create_approval_manager
        _approval_manager = create_approval_manager()
        logger.info("HITL approval gate enabled (event-driven, single worker OK)")
    except Exception as e:
        logger.info(f"Approval manager not available (gate disabled): {e}")

    # V4: LLMCallPool for rate-limited concurrent LLM access (CC flat model scaling)
    _llm_pool = None
    try:
        from src.core.performance.llm_pool import LLMCallPool
        _llm_pool = LLMCallPool.get_instance()
        logger.info(
            f"LLMCallPool enabled: max_concurrent={_llm_pool._max_concurrent}, "
            f"max_per_minute={_llm_pool._max_per_minute}"
        )
    except Exception as e:
        logger.info(f"LLMCallPool not available (no rate limiting): {e}")

    agent_tasks = [
        asyncio.create_task(
            _agent_work_loop(
                cfg, shared, emitter, shutdown_event,
                executor=_executor,
                approval_manager=_approval_manager,
                session_id=session_id,
                llm_pool=_llm_pool,
            ),
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
                    "tasks_completed": shared.task_count(),
                    "tasks_total": shared.task_count(),
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

    # ── V4: Graceful Shutdown Protocol (CC-like) ──
    # Step 1: Send SHUTDOWN_REQUEST to each agent via inbox
    agent_names = [cfg.name for cfg in agents_config]
    for agent_name in agent_names:
        shared.add_message(from_agent="TeamLead", content="SHUTDOWN_REQUEST", to_agent=agent_name)
    logger.info(f"Sent SHUTDOWN_REQUEST to {len(agent_names)} agents")

    if emitter:
        await emitter.emit_event("SWARM_PROGRESS", {
            "event_type": "shutdown_request",
            "agents": agent_names,
        })

    # Step 2: Wait for SHUTDOWN_ACK from each agent (up to 10s)
    ack_deadline = time.time() + 10.0
    acked = set()
    while time.time() < ack_deadline and len(acked) < len(agent_names):
        # Check for ACK messages in TeamLead's inbox
        lead_inbox = shared.get_inbox("TeamLead", unread_only=True)
        if lead_inbox:
            for agent_name in agent_names:
                if agent_name not in acked and agent_name in lead_inbox:
                    acked.add(agent_name)
                    logger.info(f"Received SHUTDOWN_ACK from {agent_name}")
        await asyncio.sleep(0.5)

    not_acked = set(agent_names) - acked
    if not_acked:
        logger.warning(f"Force-killing agents that didn't ACK: {not_acked}")

    # Step 3: Force shutdown (for any agents that didn't ACK)
    shutdown_event.set()
    logger.info(f"Shutdown complete: {len(acked)} ACKed, {len(not_acked)} force-killed")

    if emitter:
        await emitter.emit_event("SWARM_PROGRESS", {
            "event_type": "shutdown_complete",
            "acked": list(acked),
            "force_killed": list(not_acked),
        })

    # Wait for agent tasks to finish
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
            "tasks_completed": shared.completed_count(),
            "tasks_total": shared.task_count(),
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

    # ── V4: Post-Phase 2 memory storage ──
    if memory_integration and synthesis:
        try:
            # Store synthesis as long-term memory
            await memory_integration.store_synthesis(
                session_id=session_id or "unknown",
                goal=task,
                synthesis=synthesis,
                agent_results=agent_results,
            )
            # Store full transcript
            transcript = {
                "session_id": session_id,
                "goal": task,
                "agent_results": {
                    name: output[:1000] for name, output in agent_results.items()
                },
                "synthesis": synthesis[:2000],
                "termination_reason": termination_reason,
                "total_duration_ms": total_ms,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            await memory_integration.store_transcript(
                session_id=session_id or "unknown",
                transcript=transcript,
            )
        except Exception as e:
            logger.warning(f"Post-execution memory storage failed (non-fatal): {e}")

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

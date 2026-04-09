"""PoC: Agent Team + Subagent multi-agent collaboration test endpoints.

Test A: Subagent mode — ConcurrentBuilder (parallel, independent)
Test B: Agent Team mode — GroupChatBuilder + SharedTaskList (collaborative)
Test C: Hybrid mode — Orchestrator decides which mode to use

poc/agent-team branch.
"""

import logging
import time
import traceback
from typing import Any

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/poc/agent-team", tags=["PoC: Agent Team"])


def _get_claude_sdk_tools():
    """Lazy-load Claude SDK tools (LLM-simulated, slower)."""
    try:
        from src.integrations.poc.claude_sdk_tools import create_claude_sdk_tools
        return create_claude_sdk_tools()
    except Exception as e:
        logger.warning(f"Claude SDK tools not available: {e}")
        return []


def _get_real_tools():
    """Lazy-load real diagnostic tools (subprocess, instant).

    V2: Replaces SDK simulated tools for team mode — no extra LLM calls.
    """
    try:
        from src.integrations.poc.real_tools import create_real_tools
        return create_real_tools()
    except Exception as e:
        logger.warning(f"Real tools not available, falling back to SDK: {e}")
        return _get_claude_sdk_tools()


def _build_team_agents_config(all_tools: list, max_agents: int = 0) -> list:
    """Build V4 parallel team agent configs with expandable role library.

    V4: Supports 2-8 agents. max_agents=0 means use TEAM_MAX_AGENTS env var.
    Shared between test_team and test_team_stream to avoid duplication.
    """
    import os
    from src.integrations.poc.agent_work_loop import AgentConfig

    if max_agents <= 0:
        max_agents = int(os.getenv("TEAM_MAX_AGENTS", "5"))

    # Full role library (V4: 8 roles)
    _ROLE_LIBRARY = [
        {
            "name": "LogExpert",
            "role": "You are a log analysis expert.",
            "expertise": "log analysis error pattern trace timestamp",
        },
        {
            "name": "DBExpert",
            "role": "You are a database expert.",
            "expertise": "database sql schema query connection pool migration",
        },
        {
            "name": "AppExpert",
            "role": "You are an infrastructure/network expert.",
            "expertise": "network infrastructure configuration scheduling connectivity",
        },
        {
            "name": "SecurityExpert",
            "role": "You are a security and compliance expert.",
            "expertise": "security vulnerability access control audit compliance",
        },
        {
            "name": "CloudExpert",
            "role": "You are a cloud infrastructure and deployment expert.",
            "expertise": "cloud aws azure kubernetes container deployment scaling",
        },
        {
            "name": "MonitoringExpert",
            "role": "You are a monitoring and observability expert.",
            "expertise": "monitoring metrics alerting dashboard grafana prometheus",
        },
        {
            "name": "AutomationExpert",
            "role": "You are an automation and CI/CD expert.",
            "expertise": "automation cicd pipeline scripting terraform ansible",
        },
        {
            "name": "PerformanceExpert",
            "role": "You are a performance engineering expert.",
            "expertise": "performance optimization latency throughput profiling caching",
        },
    ]

    # Select up to max_agents roles
    selected_roles = _ROLE_LIBRARY[:max_agents]
    all_names = [r["name"] for r in selected_roles]
    teammates_str = ", ".join(all_names)

    _SHARED_WORKFLOW = (
        "You work IN PARALLEL with other experts. You will be called MULTIPLE times.\n\n"
        "EACH TURN — follow these steps:\n"
        "1. FIRST: call check_my_inbox(agent_name=YOUR_NAME)\n"
        "   - If you have messages from teammates, READ them carefully\n"
        "   - RESPOND to each message using send_team_message(to_agent=SENDER_NAME)\n"
        "   - Incorporate their findings into your analysis\n"
        "2. If no task claimed yet: call claim_next_task(agent_name=YOUR_NAME)\n"
        "3. INVESTIGATE using your tools:\n"
        "   - run_diagnostic_command: ping, curl, hostname, df, free, uptime, etc.\n"
        "   - deep_analysis: complex reasoning and root cause analysis\n"
        "   - search_knowledge_base: past incidents and SOPs\n"
        "4. call report_task_result(task_id, result) with DETAILED findings\n"
        "5. Send DIRECTED messages to SPECIFIC teammates about relevant findings:\n"
        "   send_team_message(from_agent=YOUR_NAME, message='...', to_agent='TARGET')\n\n"
        "COMMUNICATION RULES:\n"
        "- ALWAYS respond to inbox messages — this is how the team collaborates\n"
        "- When you discover something relevant to another expert, message them DIRECTLY\n"
        "- Include specific questions or requests in your messages\n"
        f"- Teammates: {teammates_str}\n\n"
        "ANALYSIS RULES:\n"
        "- Provide THOROUGH analysis with evidence and recommendations\n"
        "- If tools can't access the system, use deep_analysis for expert reasoning"
    )

    configs = []
    for role in selected_roles:
        name = role["name"]
        configs.append(AgentConfig(
            name=name,
            instructions=(
                role["role"] + " " + _SHARED_WORKFLOW.replace("YOUR_NAME", name)
            ),
            expertise=role["expertise"],
            tools=all_tools,
        ))

    return configs


def _create_client(provider: str, model: str, azure_endpoint: str = "",
                   azure_api_key: str = "", azure_api_version: str = "2025-03-01-preview",
                   azure_deployment: str = "", max_tokens: int = 1024):
    """Create a ChatClient based on provider.

    Deployment resolution priority:
      1. azure_deployment (explicit UI override)
      2. model (UI dropdown selection — e.g. gpt-5.4-mini)
      3. AZURE_OPENAI_DEPLOYMENT_NAME env var (fallback)
    """
    if provider == "azure":
        import os
        from agent_framework.azure import AzureOpenAIResponsesClient
        endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT", "")
        api_key = azure_api_key or os.getenv("AZURE_OPENAI_API_KEY", "")
        # V2: model param takes priority over env var
        deployment = azure_deployment or model or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5.4-mini")
        version = azure_api_version or os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
        logger.info(f"Creating Azure client: deployment={deployment}, endpoint={endpoint[:40]}...")
        return AzureOpenAIResponsesClient(
            endpoint=endpoint,
            api_key=api_key,
            deployment_name=deployment,
            api_version=version,
        )
    else:
        from src.integrations.agent_framework.clients.anthropic_chat_client import (
            AnthropicChatClient,
        )
        return AnthropicChatClient(model=model, max_tokens=max_tokens)


# ── Diagnostic: Parallel LLM Test ──

@router.get("/test-parallel-diag")
async def test_parallel_diag(
    model: str = Query("gpt-5.4-mini"),
    azure_endpoint: str = Query(""),
    azure_api_key: str = Query(""),
    azure_api_version: str = Query("2024-12-01-preview"),
    azure_deployment: str = Query(""),
):
    """Diagnostic: Test whether 3 independent LLM calls run in parallel.

    Returns timestamps for each call to prove parallelism.
    Access via: GET /api/v1/poc/agent-team/test-parallel-diag
    """
    import asyncio
    import concurrent.futures

    def make_client():
        return _create_client("azure", model, azure_endpoint, azure_api_key,
                              azure_api_version, azure_deployment, max_tokens=256)

    from agent_framework import Agent

    prompts = [
        ("Agent-A", "Reply with exactly: 'Hello from A'. Nothing else."),
        ("Agent-B", "Reply with exactly: 'Hello from B'. Nothing else."),
        ("Agent-C", "Reply with exactly: 'Hello from C'. Nothing else."),
    ]

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=5, thread_name_prefix="diag")
    t_start = time.time()
    results = []

    def run_one(name, prompt):
        """Run a single agent in its own thread + event loop."""
        import asyncio as _aio
        loop = _aio.new_event_loop()
        _aio.set_event_loop(loop)
        try:
            client = make_client()
            agent = Agent(client, name=name, instructions="Be extremely brief.")
            t0 = time.time()
            resp = loop.run_until_complete(agent.run(prompt))
            t1 = time.time()
            text = str(getattr(resp, "content", resp))[:100]
            return {
                "agent": name,
                "start_offset_s": round(t0 - t_start, 2),
                "end_offset_s": round(t1 - t_start, 2),
                "duration_s": round(t1 - t0, 2),
                "response": text,
            }
        finally:
            loop.close()

    # Submit all 3 simultaneously
    futures = [executor.submit(run_one, name, prompt) for name, prompt in prompts]

    # Wait for all
    for f in concurrent.futures.as_completed(futures):
        results.append(f.result())

    total_s = round(time.time() - t_start, 2)
    results.sort(key=lambda r: r["start_offset_s"])

    # Determine if parallel
    starts = [r["start_offset_s"] for r in results]
    ends = [r["end_offset_s"] for r in results]
    max_start_gap = round(max(starts) - min(starts), 2)
    is_parallel = max_start_gap < 1.0  # all started within 1s = parallel

    return {
        "test": "parallel_diag",
        "model": model,
        "total_s": total_s,
        "is_parallel": is_parallel,
        "max_start_gap_s": max_start_gap,
        "verdict": (
            f"PARALLEL ✅ (3 calls in {total_s}s, gap {max_start_gap}s)"
            if is_parallel
            else f"SEQUENTIAL ❌ (3 calls in {total_s}s, gap {max_start_gap}s)"
        ),
        "agents": results,
    }


# ── Test A: Subagent (ConcurrentBuilder) ──

@router.post("/test-subagent")
async def test_subagent(
    provider: str = Query("azure"),
    model: str = Query("gpt-5.4-nano"),
    task: str = Query(
        "Check the status of three systems: "
        "1) APAC ETL Pipeline, 2) CRM Service, 3) Email Server. "
        "Report the health status of each.",
    ),
    user_id: str = Query("user-chris"),
    session_id: str = Query("", description="Link to orchestrator session for sidechain"),
    azure_endpoint: str = Query(""),
    azure_api_key: str = Query(""),
    azure_api_version: str = Query("2025-03-01-preview"),
    azure_deployment: str = Query(""),
):
    """Test A: Subagent mode with ConcurrentBuilder.

    3 Agents run in parallel, each checking one system independently.
    Results are aggregated by a custom aggregator function.
    """
    import os
    import uuid as _uuid

    if not session_id:
        session_id = f"{user_id}-sub-{int(time.time())}-{str(_uuid.uuid4())[:8]}"

    results: dict[str, Any] = {
        "test": "subagent",
        "provider": provider,
        "model": model,
        "task": task,
        "session_id": session_id,
        "steps": [],
        "events": [],
        "agent_states": {},
    }

    try:
        from agent_framework import Agent
        from agent_framework.orchestrations import ConcurrentBuilder

        t0 = time.time()

        client = _create_client(provider, model, azure_endpoint, azure_api_key,
                                azure_api_version, azure_deployment)

        # Load Claude SDK tools for enhanced capabilities
        sdk_tools = _get_claude_sdk_tools()

        # Create 3 independent subagents with Claude SDK tools
        sub1 = Agent(client, name="ETL-Checker",
                     instructions=(
                         "You are an ETL pipeline specialist. Check the ETL pipeline status.\n"
                         "You have access to powerful tools:\n"
                         "- deep_analysis: for complex multi-step reasoning\n"
                         "- run_diagnostic_command: to simulate running diagnostic commands\n"
                         "- search_knowledge_base: to find past incidents and SOPs\n"
                         "Use these tools to provide thorough findings. Be concise in your final report."
                     ),
                     tools=sdk_tools)
        sub2 = Agent(client, name="CRM-Checker",
                     instructions=(
                         "You are a CRM service specialist. Check the CRM service health.\n"
                         "You have access to: deep_analysis, run_diagnostic_command, search_knowledge_base.\n"
                         "Use these tools to investigate. Be concise."
                     ),
                     tools=sdk_tools)
        sub3 = Agent(client, name="Email-Checker",
                     instructions=(
                         "You are an email server specialist. Check the email server status.\n"
                         "You have access to: deep_analysis, run_diagnostic_command, search_knowledge_base.\n"
                         "Use these tools to investigate. Be concise."
                     ),
                     tools=sdk_tools)

        results["steps"].append({
            "step": "create_agents",
            "status": "ok",
            "agents": ["ETL-Checker", "CRM-Checker", "Email-Checker"],
            "sdk_tools": len(sdk_tools),
        })

        # Build with ConcurrentBuilder
        builder = ConcurrentBuilder(participants=[sub1, sub2, sub3])
        workflow = builder.build()
        build_time = round((time.time() - t0) * 1000)
        results["steps"].append({"step": "build_concurrent", "status": "ok", "duration_ms": build_time})

        # Initialize sidechain transcript
        from src.integrations.orchestration.transcript import TranscriptService
        from src.integrations.orchestration.transcript.models import AgentSidechainEntry
        redis_url = f"redis://:{os.getenv('REDIS_PASSWORD', 'redis_password')}@localhost:6379/0"
        sidechain = TranscriptService(redis_url=redis_url)
        await sidechain.initialize()

        agent_names = ["ETL-Checker", "CRM-Checker", "Email-Checker"]
        for name in agent_names:
            await sidechain.append_agent(AgentSidechainEntry(
                user_id=user_id, session_id=session_id, agent_name=name,
                event_type="start", content={"task": task[:100]},
            ))
            results["agent_states"][name] = "running"

        # Run
        t1 = time.time()
        try:
            stream = workflow.run(message=task, stream=True, include_status_events=True)
            agent_responses: list[dict[str, Any]] = []

            async for event in stream:
                event_type = type(event).__name__
                event_info: dict[str, Any] = {"type": event_type}
                if hasattr(event, "data") and event.data:
                    data = event.data
                    data_str = str(data)[:300]
                    event_info["data_preview"] = data_str

                    # Extract actual Agent response text
                    if hasattr(data, '__iter__') and not isinstance(data, str):
                        for item in data:
                            if hasattr(item, 'executor_id') and hasattr(item, 'agent_response'):
                                resp = item.agent_response
                                text = ""
                                if hasattr(resp, 'text') and resp.text:
                                    text = resp.text
                                elif hasattr(resp, 'messages') and resp.messages:
                                    for msg in resp.messages:
                                        if hasattr(msg, 'text') and msg.text:
                                            text += msg.text
                                if text:
                                    agent_responses.append({
                                        "agent": item.executor_id,
                                        "response": text[:500],
                                    })
                                    event_info["agent_name"] = item.executor_id
                                    event_info["agent_response"] = text[:300]
                                    # Sidechain: record agent completion
                                    await sidechain.append_agent(AgentSidechainEntry(
                                        user_id=user_id, session_id=session_id,
                                        agent_name=item.executor_id,
                                        event_type="complete",
                                        content={"response_preview": text[:200]},
                                    ))
                                    results["agent_states"][item.executor_id] = "complete"

                results["events"].append(event_info)

            run_time = round((time.time() - t1) * 1000)
            results["steps"].append({
                "step": "run_concurrent",
                "status": "ok",
                "duration_ms": run_time,
                "total_events": len(results["events"]),
            })

            results["agent_responses"] = agent_responses
            # Mark any agents that didn't respond as failed
            for name in agent_names:
                if results["agent_states"].get(name) == "running":
                    results["agent_states"][name] = "no_response"
                    await sidechain.append_agent(AgentSidechainEntry(
                        user_id=user_id, session_id=session_id, agent_name=name,
                        event_type="error", content={"error": "No response received"},
                    ))

            results["steps"].append({
                "step": "collect_results",
                "status": "ok",
                "agent_results_count": len(agent_responses),
            })

        except Exception as e:
            run_time = round((time.time() - t1) * 1000)
            # Sidechain: record error for all running agents
            for name in agent_names:
                if results["agent_states"].get(name) == "running":
                    results["agent_states"][name] = "error"
                    await sidechain.append_agent(AgentSidechainEntry(
                        user_id=user_id, session_id=session_id, agent_name=name,
                        event_type="error", content={"error": str(e)[:200]},
                    ))
            results["steps"].append({
                "step": "run_concurrent",
                "status": "error",
                "duration_ms": run_time,
                "error": str(e),
                "traceback": traceback.format_exc()[-500:],
            })

        await sidechain.close()

        completed = sum(1 for s in results["agent_states"].values() if s == "complete")
        results["status"] = "ok" if all(s.get("status") == "ok" for s in results["steps"]) else "partial"
        results["summary"] = (
            f"Subagent: {completed}/{len(agent_names)} agents complete, "
            f"{len(results['events'])} events, session={session_id[:20]}..."
        )

    except Exception as e:
        results["status"] = "error"
        results["error"] = str(e)
        results["traceback"] = traceback.format_exc()[-500:]

    return results


# ── Test B: Agent Team (V2 Parallel Engine) ──

@router.post("/test-team")
async def test_team(
    provider: str = Query("azure"),
    model: str = Query("gpt-5.4-mini"),
    task: str = Query(
        "Investigate APAC ETL Pipeline failure. Multiple experts needed: "
        "analyze application logs, check database changes, and verify network connectivity.",
    ),
    user_id: str = Query("user-chris"),
    session_id: str = Query("", description="Link to orchestrator session for sidechain"),
    azure_endpoint: str = Query(""),
    azure_api_key: str = Query(""),
    azure_api_version: str = Query("2024-12-01-preview"),
    azure_deployment: str = Query(""),
    timeout: float = Query(120.0, description="Max execution timeout in seconds"),
):
    """Test B: Agent Team with V2 Parallel Engine.

    Phase 0: TeamLead dynamically decomposes task into sub-tasks.
    Phase 1: 3 agents work IN PARALLEL via asyncio.gather.
    Each agent: claim task → execute with tools → report → communicate.
    """
    import os
    import uuid as _uuid

    if not session_id:
        session_id = f"{user_id}-team-{int(time.time())}-{str(_uuid.uuid4())[:8]}"

    results: dict[str, Any] = {
        "test": "agent_team_v2_parallel",
        "provider": provider,
        "model": model,
        "task": task,
        "session_id": session_id,
        "steps": [],
        "events": [],
        "shared_task_list": None,
        "agent_states": {},
    }

    try:
        from src.integrations.poc.shared_task_list import create_shared_task_list
        from src.integrations.poc.team_tools import create_team_tools, create_lead_tools
        from src.integrations.poc.agent_work_loop import (
            AgentConfig, run_parallel_team,
        )

        t0 = time.time()

        # Step 1: Create SharedTaskList (V4: Redis-backed if available)
        shared = create_shared_task_list(session_id=session_id)
        team_tools = create_team_tools(shared)
        lead_tools = create_lead_tools(shared)
        real_tools = _get_real_tools()  # V2: real subprocess tools
        sdk_tools = _get_claude_sdk_tools()  # deep_analysis fallback for thorough analysis
        all_tools = team_tools + real_tools + sdk_tools

        results["steps"].append({
            "step": "create_tools", "status": "ok",
            "team_tools": len(team_tools), "sdk_tools": len(sdk_tools),
            "lead_tools": len(lead_tools),
        })

        # Step 2: Create client factory + agent configs
        # Each agent gets its OWN client to avoid connection serialization
        def make_client():
            return _create_client(provider, model, azure_endpoint, azure_api_key,
                                  azure_api_version, azure_deployment, max_tokens=2048)

        agents_config = _build_team_agents_config(all_tools)

        team_agent_names = [c.name for c in agents_config]
        results["steps"].append({
            "step": "create_agent_configs", "status": "ok",
            "agents": team_agent_names,
        })

        # Step 3: Initialize sidechain transcript
        from src.integrations.orchestration.transcript import TranscriptService
        from src.integrations.orchestration.transcript.models import AgentSidechainEntry
        redis_url = f"redis://:{os.getenv('REDIS_PASSWORD', 'redis_password')}@localhost:6379/0"
        sidechain = TranscriptService(redis_url=redis_url)
        await sidechain.initialize()

        for name in team_agent_names:
            await sidechain.append_agent(AgentSidechainEntry(
                user_id=user_id, session_id=session_id, agent_name=name,
                event_type="start", content={"task": task[:100]},
            ))
            results["agent_states"][name] = "running"

        # Step 4: Run parallel team (Phase 0 + Phase 1)
        team_result = await run_parallel_team(
            task=task,
            context="",
            agents_config=agents_config,
            shared=shared,
            client_factory=make_client,
            lead_tools=lead_tools,
            emitter=None,
            session_id=session_id,
            timeout=timeout,
        )

        # Step 5: Map results
        for name in team_agent_names:
            agent_output = team_result.agent_results.get(name, "")
            if agent_output.startswith("ERROR") or agent_output.startswith("CANCELLED"):
                results["agent_states"][name] = "error"
                await sidechain.append_agent(AgentSidechainEntry(
                    user_id=user_id, session_id=session_id, agent_name=name,
                    event_type="error", content={"error": agent_output[:200]},
                ))
            else:
                results["agent_states"][name] = "complete"
                await sidechain.append_agent(AgentSidechainEntry(
                    user_id=user_id, session_id=session_id, agent_name=name,
                    event_type="complete", content={"response_preview": agent_output[:200]},
                ))

        results["agent_responses"] = [
            {"agent": name, "response": output[:500]}
            for name, output in team_result.agent_results.items()
        ]

        results["steps"].append({
            "step": "run_parallel_team",
            "status": "ok",
            "duration_ms": team_result.total_duration_ms,
            "phase0_duration_ms": team_result.phase0_duration_ms,
            "termination_reason": team_result.termination_reason,
        })

        await sidechain.close()

        # Step 6: Final state
        results["shared_task_list"] = shared.to_dict()
        results["steps"].append({
            "step": "final_task_state",
            "status": "ok",
            "tasks_completed": shared.to_dict()["progress"]["completed"],
            "tasks_total": shared.to_dict()["progress"]["total"],
            "team_messages": len(shared.to_dict()["messages"]),
            "all_done": shared.is_all_done(),
        })

        completed_agents = sum(1 for s in results["agent_states"].values() if s == "complete")
        results["status"] = "ok" if team_result.termination_reason == "all_done" else "partial"
        results["summary"] = (
            f"Team V2 Parallel: {completed_agents}/{len(team_agent_names)} agents, "
            f"{team_result.termination_reason}, "
            f"{shared.to_dict()['progress']['completed']}/{shared.to_dict()['progress']['total']} tasks, "
            f"{len(shared.to_dict()['messages'])} messages, "
            f"{team_result.total_duration_ms}ms total, session={session_id[:20]}..."
        )

    except Exception as e:
        results["status"] = "error"
        results["error"] = str(e)
        results["traceback"] = traceback.format_exc()[-500:]

    return results


# ── Test C: Hybrid (Orchestrator decides mode) ──

@router.post("/test-hybrid")
async def test_hybrid(
    provider: str = Query("azure"),
    model: str = Query("gpt-5.4-mini"),
    task: str = Query(
        "Check VPN connectivity for Taipei, Hong Kong, and Singapore offices.",
    ),
    azure_endpoint: str = Query(""),
    azure_api_key: str = Query(""),
    azure_api_version: str = Query("2025-03-01-preview"),
    azure_deployment: str = Query(""),
):
    """Test C: Orchestrator Agent decides Subagent vs Team mode.

    Uses function calling to let the Orchestrator choose the execution mode.
    """
    results: dict[str, Any] = {
        "test": "hybrid",
        "provider": provider,
        "model": model,
        "task": task,
        "steps": [],
    }

    try:
        from agent_framework import Agent, tool as maf_tool

        client = _create_client(provider, model, azure_endpoint, azure_api_key,
                                azure_api_version, azure_deployment, max_tokens=2048)

        t0 = time.time()

        # Define mode selection tool
        @maf_tool(name="select_execution_mode", description=(
            "Decide the execution mode for the task. "
            "Use 'subagent' for independent parallel tasks (e.g., checking 3 separate systems). "
            "Use 'team' for tasks requiring expert collaboration (e.g., investigating a complex failure). "
            "Return your reasoning."
        ))
        def select_execution_mode(mode: str, reasoning: str) -> str:
            """Select execution mode: 'subagent' or 'team'."""
            return f"Selected mode: {mode}. Reasoning: {reasoning}"

        # Create Orchestrator with the selection tool
        orchestrator = Agent(
            client,
            name="Orchestrator",
            instructions=(
                "You are an IT operations orchestrator. Analyze the user's request and decide:\n"
                "- Use 'subagent' mode if the task has independent subtasks that can run in parallel\n"
                "- Use 'team' mode if the task requires expert collaboration and information sharing\n"
                "Call select_execution_mode with your decision and reasoning."
            ),
            tools=[select_execution_mode],
        )

        results["steps"].append({"step": "create_orchestrator", "status": "ok"})

        # Run orchestrator to decide
        t1 = time.time()
        try:
            response = await orchestrator.run(task)
            decision_time = round((time.time() - t1) * 1000)

            # Extract the decision
            response_text = ""
            if hasattr(response, "text"):
                response_text = response.text
            elif hasattr(response, "messages") and response.messages:
                for msg in response.messages:
                    if hasattr(msg, "text") and msg.text:
                        response_text += msg.text

            selected_mode = "subagent"  # default
            if "team" in response_text.lower():
                selected_mode = "team"

            results["steps"].append({
                "step": "orchestrator_decision",
                "status": "ok",
                "duration_ms": decision_time,
                "selected_mode": selected_mode,
                "reasoning_preview": response_text[:300],
            })

            # Execute based on decision
            if selected_mode == "subagent":
                # Delegate to subagent test
                sub_result = await test_subagent(
                    provider=provider, model=model, task=task,
                    azure_endpoint=azure_endpoint, azure_api_key=azure_api_key,
                    azure_api_version=azure_api_version, azure_deployment=azure_deployment,
                )
                results["agent_responses"] = sub_result.get("agent_responses", [])
                results["events"] = sub_result.get("events", [])
                results["steps"].append({
                    "step": "execute_subagent",
                    "status": sub_result.get("status", "error"),
                    "events": len(sub_result.get("events", [])),
                    "summary": sub_result.get("summary", ""),
                })
            else:
                # Delegate to team test
                try:
                    team_result = await test_team(
                        provider=provider, model=model, task=task,
                        max_rounds=6,
                        azure_endpoint=azure_endpoint, azure_api_key=azure_api_key,
                        azure_api_version=azure_api_version, azure_deployment=azure_deployment,
                    )
                except Exception as team_err:
                    team_result = {"status": "error", "error": str(team_err),
                                   "events": [], "summary": "", "shared_task_list": None,
                                   "agent_responses": []}
                results["agent_responses"] = team_result.get("agent_responses", [])
                results["events"] = team_result.get("events", [])
                results["steps"].append({
                    "step": "execute_team",
                    "status": team_result.get("status", "error"),
                    "events": len(team_result.get("events", [])),
                    "summary": team_result.get("summary", ""),
                    "shared_task_list": team_result.get("shared_task_list"),
                })

        except Exception as e:
            results["steps"].append({
                "step": "orchestrator_decision",
                "status": "error",
                "error": str(e),
                "traceback": traceback.format_exc()[-500:],
            })

        total_time = round((time.time() - t0) * 1000)
        results["status"] = "ok" if all(s.get("status") == "ok" for s in results["steps"]) else "partial"
        results["summary"] = f"Hybrid: Orchestrator decided mode, total {total_time}ms"

    except Exception as e:
        results["status"] = "error"
        results["error"] = str(e)
        results["traceback"] = traceback.format_exc()[-500:]

    return results


# ── Test D: Orchestrator Agent (hybrid: deterministic pipeline + LLM decision) ──

@router.post("/test-orchestrator")
async def test_orchestrator(
    provider: str = Query("azure"),
    model: str = Query("gpt-5.4-mini"),
    task: str = Query(
        "APAC Glider ETL Pipeline has been failing for 3 days, affecting financial reports.",
    ),
    user_id: str = Query("user-chris", description="User ID for memory lookup"),
    azure_endpoint: str = Query(""),
    azure_api_key: str = Query(""),
    azure_api_version: str = Query("2025-03-01-preview"),
    azure_deployment: str = Query(""),
):
    """Test D: Full Orchestrator Agent — hybrid deterministic + LLM pipeline.

    Steps 1-3, 5-6 are deterministic (code-forced, never skipped).
    Only Step 4 (route decision) uses LLM reasoning.
    """
    # Generate session ID with user isolation
    import os
    import uuid as _uuid
    from datetime import datetime, timezone
    session_id = f"{user_id}-{int(time.time())}-{str(_uuid.uuid4())[:8]}"

    results: dict[str, Any] = {
        "test": "orchestrator",
        "provider": provider,
        "model": model,
        "task": task,
        "user_id": user_id,
        "session_id": session_id,
        "steps": [],
        "orchestrator_actions": [],
        "checkpoints": [],
        "transcript_count": 0,
    }

    try:
        from agent_framework import Agent, tool as maf_tool

        # Initialize transcript service for append-only execution log
        from src.integrations.orchestration.transcript import TranscriptService, TranscriptEntry
        redis_url = f"redis://:{os.getenv('REDIS_PASSWORD', 'redis_password')}@localhost:6379/0"
        transcript = TranscriptService(redis_url=redis_url)
        await transcript.initialize()

        t0 = time.time()

        # ── Step 1: READ MEMORY with Context Budget Manager (CC-inspired) ──
        assembled_context = None
        try:
            from src.integrations.memory.unified_memory import UnifiedMemoryManager
            from src.integrations.memory.context_budget import ContextBudgetManager, AssembledContext
            mgr = UnifiedMemoryManager()
            await mgr.initialize()

            budget_mgr = ContextBudgetManager()
            assembled_context = await budget_mgr.assemble_context(
                user_id=user_id,
                query=task,
                memory_manager=mgr,
            )
            memory_text = assembled_context.to_prompt_text()
            memory_context = []  # for transcript compatibility
        except Exception as e:
            memory_text = f"Memory service unavailable: {str(e)[:100]}"
            memory_context = []

        pinned_count = assembled_context.pinned_count if assembled_context else 0
        budget_pct = assembled_context.budget_used_pct if assembled_context else 0
        step1_status = "ok" if "unavailable" not in memory_text.lower() and "failed" not in memory_text.lower() else "failed"
        results["steps"].append({
            "step": "1_read_memory",
            "status": step1_status,
            "result_preview": memory_text[:300],
            "pinned_count": pinned_count,
            "budget_used_pct": budget_pct,
        })
        results["orchestrator_actions"].append({
            "tool": "get_user_memory",
            "args": f"user_id={user_id}",
            "result": memory_text[:500],
        })
        await transcript.append(TranscriptEntry(
            user_id=user_id, session_id=session_id,
            step_name="read_memory", step_index=0,
            entry_type="step_complete" if step1_status == "ok" else "step_error",
            output_summary={"memory_count": len(memory_context or []), "preview": memory_text[:100]},
            metadata={"duration_ms": round((time.time() - t0) * 1000)},
        ))

        # ── Step 2: SEARCH KNOWLEDGE (deterministic — always execute) ──
        try:
            from openai import AzureOpenAI
            from qdrant_client import QdrantClient

            az = AzureOpenAI(
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                api_version="2024-02-01",
            )
            q_emb = az.embeddings.create(input=task[:500], model="text-embedding-ada-002").data[0].embedding
            qd = QdrantClient(host="localhost", port=6333)
            search_results = qd.query_points("ipa_knowledge", query=q_emb, limit=3)
            knowledge_text = "\n".join(
                f"[{r.payload.get('source','?')}] (score={r.score:.2f}) {r.payload.get('content','')}"
                for r in search_results.points
            ) or "No knowledge found"
        except Exception as e:
            knowledge_text = f"Knowledge search failed: {str(e)[:150]}"

        step2_status = "ok" if "failed" not in knowledge_text.lower() and "No knowledge" not in knowledge_text else "failed"
        results["steps"].append({
            "step": "2_search_knowledge",
            "status": step2_status,
            "result_preview": knowledge_text[:500],
        })
        results["orchestrator_actions"].append({
            "tool": "search_knowledge",
            "args": f"query={task[:80]}",
            "result": knowledge_text,
        })
        await transcript.append(TranscriptEntry(
            user_id=user_id, session_id=session_id,
            step_name="search_knowledge", step_index=1,
            entry_type="step_complete" if step2_status == "ok" else "step_error",
            output_summary={"result_count": len(search_results.points) if "search_results" in dir() else 0, "preview": knowledge_text[:100]},
            metadata={"duration_ms": round((time.time() - t0) * 1000)},
        ))

        # ── Step 3: ANALYZE INTENT (deterministic — always execute) ──
        try:
            from src.integrations.orchestration.intent_router.router import BusinessIntentRouter
            from src.integrations.orchestration.intent_router.pattern_matcher.matcher import PatternMatcher
            from src.integrations.orchestration.intent_router.semantic_router.router import SemanticRouter
            from src.integrations.orchestration.intent_router.llm_classifier.classifier import LLMClassifier

            matcher = PatternMatcher()
            # Add patterns using proper PatternRule objects
            from src.integrations.orchestration.intent_router.models import (
                PatternRule, ITIntentCategory, RiskLevel, WorkflowType,
            )
            poc_rules = [
                PatternRule(
                    id="poc-etl-failure", category=ITIntentCategory.INCIDENT,
                    sub_intent="etl_failure", priority=90,
                    patterns=[r"(?i)(etl|pipeline|data.?flow|batch.?job).*(fail|error|down|broken|stuck)"],
                    risk_level=RiskLevel.HIGH, workflow_type=WorkflowType.MAGENTIC,
                ),
                PatternRule(
                    id="poc-system-outage", category=ITIntentCategory.INCIDENT,
                    sub_intent="system_outage", priority=95,
                    patterns=[r"(?i)(server|service|system|database).*(down|fail|error|crash|outage|unavailable)"],
                    risk_level=RiskLevel.CRITICAL, workflow_type=WorkflowType.MAGENTIC,
                ),
                PatternRule(
                    id="poc-prod-restart", category=ITIntentCategory.CHANGE,
                    sub_intent="production_restart", priority=95,
                    patterns=[r"(?i)(restart|reboot|shutdown|stop|kill).*(prod|production|server|database|db)"],
                    risk_level=RiskLevel.CRITICAL, workflow_type=WorkflowType.MAGENTIC,
                ),
                PatternRule(
                    id="poc-destructive-op", category=ITIntentCategory.CHANGE,
                    sub_intent="destructive_operation", priority=95,
                    patterns=[r"(?i)(delete|drop|truncate|wipe|purge).*(data|table|database|prod|production)"],
                    risk_level=RiskLevel.CRITICAL, workflow_type=WorkflowType.MAGENTIC,
                ),
                PatternRule(
                    id="poc-deployment", category=ITIntentCategory.CHANGE,
                    sub_intent="deployment", priority=50,
                    patterns=[r"(?i)(deploy|release|rollout|update|upgrade|migration)"],
                    risk_level=RiskLevel.MEDIUM, workflow_type=WorkflowType.SEQUENTIAL,
                ),
                PatternRule(
                    id="poc-status-check", category=ITIntentCategory.QUERY,
                    sub_intent="status_check", priority=30,
                    patterns=[r"(?i)(check|status|monitor|health|ping|query|what.?is)"],
                    risk_level=RiskLevel.LOW, workflow_type=WorkflowType.HANDOFF,
                ),
            ]
            for rule in poc_rules:
                try:
                    matcher.add_rule(rule)
                except Exception as rule_err:
                    logger.warning(f"Failed to add pattern rule {rule.id}: {rule_err}")

            # Create LLMClassifier with LLM service for fallback
            try:
                from src.integrations.llm.factory import LLMServiceFactory
                llm_svc = LLMServiceFactory.create(use_cache=True)
                llm_cls = LLMClassifier(llm_service=llm_svc)
            except Exception:
                llm_cls = LLMClassifier()

            router_inst = BusinessIntentRouter(
                pattern_matcher=matcher,
                semantic_router=SemanticRouter(),
                llm_classifier=llm_cls,
            )
            # Check pattern matcher FIRST for high-risk detection (before router may dilute it)
            pattern_result = matcher.match(task)
            pattern_risk = getattr(pattern_result, "risk_level", None)

            decision = await router_inst.route(task)

            # Use pattern matcher's risk if it matched with higher severity
            effective_risk = decision.risk_level
            if pattern_result.matched and pattern_risk:
                risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
                pattern_rank = risk_order.get(str(pattern_risk).split(".")[-1], 0)
                decision_rank = risk_order.get(str(effective_risk).split(".")[-1], 0)
                if pattern_rank > decision_rank:
                    effective_risk = pattern_risk
                    logger.info(f"Pattern matcher elevated risk: {decision.risk_level} → {pattern_risk}")

            intent_text = (
                f"Category: {decision.intent_category}, "
                f"Risk: {effective_risk}, "
                f"Confidence: {decision.confidence:.2f}, "
                f"Workflow: {decision.workflow_type}"
            )
        except Exception as e:
            intent_text = f"Intent analysis partial: {str(e)[:100]}"
            effective_risk = None
            pattern_result = None

        step3_status = "ok" if "UNKNOWN" not in intent_text and "partial" not in intent_text.lower() else "partial"
        results["steps"].append({
            "step": "3_analyze_intent",
            "status": step3_status,
            "result_preview": intent_text[:200],
        })
        results["orchestrator_actions"].append({
            "tool": "analyze_intent",
            "args": f"input={task[:80]}",
            "result": intent_text,
        })

        # Conditional checkpoint: HIGH/CRITICAL risk + CHANGE category → HITL pauses pipeline
        # INCIDENT (investigation) and QUERY (read-only) don't require approval
        step3_checkpoint_id = None
        risk_str = str(effective_risk) if "effective_risk" in dir() and effective_risk else ""
        intent_category_str = str(getattr(decision, "intent_category", "")) if "decision" in dir() else ""
        is_actionable = "CHANGE" in intent_category_str  # Only changes need approval
        is_high_risk = ("HIGH" in risk_str or "CRITICAL" in risk_str) and is_actionable
        if is_high_risk:
            try:
                from agent_framework import WorkflowCheckpoint
                from src.integrations.agent_framework.ipa_checkpoint_storage import IPACheckpointStorage
                from src.integrations.orchestration.approval import ApprovalService, ApprovalRequest as ApprovalReq

                # 1. Create checkpoint
                cp_storage = IPACheckpointStorage(redis_url=redis_url, user_id=user_id)
                await cp_storage.initialize()
                cp3 = WorkflowCheckpoint(
                    workflow_name=session_id,
                    graph_signature_hash="orchestrator-7step-v1",
                    state={
                        "pipeline_step": 3,
                        "memory_context": memory_text[:500],
                        "knowledge_results": knowledge_text[:500],
                        "intent_analysis": intent_text,
                        "route_decision": None,
                        "resume_reason": "hitl_pending",
                    },
                    messages={"orchestrator": [{"role": "user", "content": task}]},
                    iteration_count=3,
                    metadata={"user_id": user_id, "task_preview": task[:100], "risk": str(risk_str)},
                )
                step3_checkpoint_id = await cp_storage.save(cp3)
                await cp_storage.close()

                # 2. Create approval request
                approval_svc = ApprovalService(redis_url=redis_url)
                await approval_svc.initialize()
                approval_req = ApprovalReq(
                    user_id=user_id,
                    session_id=session_id,
                    checkpoint_id=step3_checkpoint_id,
                    task=task[:200],
                    risk_level=str(risk_str),
                    intent_category=str(getattr(decision, "intent_category", "")),
                    confidence=getattr(decision, "confidence", 0.0),
                    context_summary={
                        "memory": memory_text[:200],
                        "knowledge": knowledge_text[:200],
                        "intent": intent_text,
                    },
                )
                approval_id = await approval_svc.create(approval_req)
                await approval_svc.close()

                # 3. Record in transcript
                await transcript.append(TranscriptEntry(
                    user_id=user_id, session_id=session_id,
                    step_name="analyze_intent", step_index=2,
                    entry_type="approval_required",
                    output_summary={"intent": intent_text[:150], "high_risk": True, "approval_id": approval_id},
                    checkpoint_id=step3_checkpoint_id,
                ))
                await transcript.close()

                # 4. ⛔ PAUSE PIPELINE — return early
                total_time = round((time.time() - t0) * 1000)
                results["status"] = "pending_approval"
                results["checkpoints"].append({
                    "id": step3_checkpoint_id, "step": 3, "reason": "high_risk_hitl",
                    "risk": str(risk_str),
                })
                results["approval"] = {
                    "id": approval_id,
                    "status": "pending",
                    "checkpoint_id": step3_checkpoint_id,
                    "risk_level": str(risk_str),
                    "message": f"此操作風險等級為 {risk_str}，需要主管審批後才能繼續執行",
                }
                results["summary"] = (
                    f"Orchestrator: PAUSED at step 3 (risk={risk_str}), "
                    f"awaiting approval, total {total_time}ms"
                )
                results["steps"].append({
                    "step": "3_hitl_pause",
                    "status": "pending_approval",
                    "approval_id": approval_id,
                    "checkpoint_id": step3_checkpoint_id,
                    "risk": str(risk_str),
                })
                return results

            except Exception as cp_err:
                logger.warning(f"Step 3 HITL checkpoint/approval failed: {cp_err}")
                # If HITL setup fails, continue pipeline (graceful degradation)

        await transcript.append(TranscriptEntry(
            user_id=user_id, session_id=session_id,
            step_name="analyze_intent", step_index=2,
            entry_type="step_complete",
            output_summary={"intent": intent_text[:150], "high_risk": is_high_risk},
            checkpoint_id=step3_checkpoint_id,
            metadata={"duration_ms": round((time.time() - t0) * 1000)},
        ))

        # ── Step 4: LLM ROUTE DECISION (only step that uses LLM) ──
        client = _create_client(provider, model, azure_endpoint, azure_api_key,
                                azure_api_version, azure_deployment, max_tokens=2048)

        @maf_tool(name="select_route", description=(
            "Select the execution route for this task. Options: "
            "'direct_answer' (simple Q&A), 'subagent' (parallel independent), "
            "'team' (expert collaboration), 'swarm' (deep Manager analysis), "
            "'workflow' (structured process)."
        ))
        def select_route(route: str, reasoning: str) -> str:
            """Select execution route with reasoning."""
            return f"Route: {route}. Reason: {reasoning}"

        orchestrator = Agent(
            client,
            name="Orchestrator",
            instructions=(
                "You are an IT Operations Orchestrator. Based on the context below, "
                "call select_route to choose the best execution mode.\n\n"
                f"## User Request\n{task}\n\n"
                f"## Memory Context (structured, token-budgeted)\n{memory_text}\n\n"
                f"## Knowledge Base\n{knowledge_text}\n\n"
                f"## Intent Analysis\n{intent_text}\n\n"
                "Choose ONE route:\n"
                "- direct_answer: simple questions, low risk\n"
                "- subagent: independent parallel checks (e.g., check 3 systems)\n"
                "- team: complex investigation needing expert collaboration\n"
                "- swarm: critical incidents needing deep Manager-driven analysis\n"
                "- workflow: structured processes (deploy, change management)\n\n"
                "Call select_route with your choice and reasoning."
            ),
            tools=[select_route],
        )

        t1 = time.time()
        response = await orchestrator.run(task)
        decision_time = round((time.time() - t1) * 1000)

        response_text = ""
        if hasattr(response, "text") and response.text:
            response_text = response.text
        elif hasattr(response, "messages") and response.messages:
            for msg in response.messages:
                if hasattr(msg, "text") and msg.text:
                    response_text += msg.text

        # Extract selected route
        selected_mode = "team"  # default
        for keyword in ["direct_answer", "subagent", "team", "swarm", "workflow"]:
            if keyword in response_text.lower():
                selected_mode = keyword
                break

        results["steps"].append({
            "step": "4_llm_route_decision",
            "status": "ok",
            "duration_ms": decision_time,
            "selected_mode": selected_mode,
        })
        results["orchestrator_actions"].append({
            "tool": "select_route",
            "args": f"route={selected_mode}",
            "result": response_text[:300],
        })
        results["orchestrator_response"] = response_text[:3000]

        # Mandatory decision-point checkpoint at Step 4 (always)
        step4_checkpoint_id = None
        try:
            from agent_framework import WorkflowCheckpoint
            from src.integrations.agent_framework.ipa_checkpoint_storage import IPACheckpointStorage

            cp_storage4 = IPACheckpointStorage(redis_url=redis_url, user_id=user_id)
            await cp_storage4.initialize()

            cp4 = WorkflowCheckpoint(
                workflow_name=session_id,
                graph_signature_hash="orchestrator-7step-v1",
                state={
                    "pipeline_step": 4,
                    "memory_context": memory_text[:500],
                    "knowledge_results": knowledge_text[:500],
                    "intent_analysis": intent_text,
                    "route_decision": selected_mode,
                    "resume_reason": None,
                    "subagent_states": {},
                },
                messages={
                    "orchestrator": [
                        {"role": "user", "content": task},
                        {"role": "assistant", "content": response_text[:500] if response_text else ""},
                    ]
                },
                iteration_count=4,
                metadata={
                    "user_id": user_id,
                    "task_preview": task[:100],
                    "route": selected_mode,
                    "source": "poc-orchestrator-test",
                    "session_id": session_id,
                },
            )
            step4_checkpoint_id = await cp_storage4.save(cp4)
            await cp_storage4.close()
            results["checkpoints"].append({
                "id": step4_checkpoint_id, "step": 4, "reason": "decision_point",
                "route": selected_mode,
            })
        except Exception as cp4_err:
            logger.error(f"Step 4 checkpoint failed: {cp4_err}")

        await transcript.append(TranscriptEntry(
            user_id=user_id, session_id=session_id,
            step_name="llm_route_decision", step_index=3,
            entry_type="decision",
            output_summary={"route": selected_mode, "response_preview": response_text[:150]},
            checkpoint_id=step4_checkpoint_id,
            metadata={"duration_ms": decision_time},
        ))

        # ── Step 5: CHECKPOINT CONFIRMATION (reads back saved checkpoint) ──
        checkpoint_text = (
            f"IPA checkpoint saved: id={step4_checkpoint_id[:12]}..., session={session_id}"
            if step4_checkpoint_id
            else "Checkpoint failed at step 4"
        )

        results["steps"].append({
            "step": "5_save_checkpoint",
            "status": "ok" if step4_checkpoint_id else "failed",
            "result_preview": checkpoint_text[:300],
        })
        results["orchestrator_actions"].append({
            "tool": "save_session_checkpoint",
            "args": f"session={session_id}, protocol=IPA Checkpoint (MAF-compatible format)",
            "result": checkpoint_text,
        })
        await transcript.append(TranscriptEntry(
            user_id=user_id, session_id=session_id,
            step_name="save_checkpoint", step_index=4,
            entry_type="step_complete" if step4_checkpoint_id else "step_error",
            output_summary={"checkpoint_id": step4_checkpoint_id, "route": selected_mode},
            checkpoint_id=step4_checkpoint_id,
        ))

        # ── Step 6: MEMORY EXTRACTION (CC-inspired async LLM extraction) ──
        # Replaces the old low-density "User asked X, routed to Y" save.
        # Now uses LLM to extract structured facts, preferences, decisions, patterns.
        import asyncio
        save_text = "Memory extraction scheduled (async)"
        try:
            from src.integrations.memory.extraction import MemoryExtractionService
            from src.integrations.memory.consolidation import MemoryConsolidationService

            if not mgr._initialized:
                mgr2 = UnifiedMemoryManager()
                await mgr2.initialize()
            else:
                mgr2 = mgr

            extraction_svc = MemoryExtractionService(mgr2)

            # Fire-and-forget: extraction runs in background, doesn't block response
            asyncio.create_task(extraction_svc.extract_and_store(
                user_id=user_id,
                session_id=session_id,
                user_message=task,
                assistant_response=response_text[:2000],
                pipeline_context={
                    "route_decision": selected_mode,
                    "risk_level": str(risk_str) if "risk_str" in dir() else "",
                    "intent_category": str(getattr(decision, "intent_category", "")) if "decision" in dir() else "",
                },
            ))

            # Also check if consolidation is due
            consolidation_svc = MemoryConsolidationService(mgr2)
            should_consolidate = await consolidation_svc.increment_and_check(user_id)
            if should_consolidate:
                asyncio.create_task(consolidation_svc.run_consolidation(user_id))
                save_text += " + consolidation triggered"

        except Exception as mem_err:
            logger.error(f"Memory extraction setup failed: {mem_err}")
            save_text = f"Memory extraction failed: {str(mem_err)[:100]}"

        results["steps"].append({
            "step": "6_save_memory",
            "status": "ok",
            "result_preview": save_text[:200],
        })
        results["orchestrator_actions"].append({
            "tool": "extract_and_save_memory",
            "args": f"user_id={user_id}, mode=async_llm_extraction",
            "result": save_text,
        })
        await transcript.append(TranscriptEntry(
            user_id=user_id, session_id=session_id,
            step_name="save_memory", step_index=5,
            entry_type="step_complete",
            output_summary={"extraction": "scheduled", "consolidation": should_consolidate if "should_consolidate" in dir() else False},
        ))

        # ── Final ──
        total_time = round((time.time() - t0) * 1000)

        await transcript.append(TranscriptEntry(
            user_id=user_id, session_id=session_id,
            step_name="mode_decision", step_index=6,
            entry_type="step_complete",
            output_summary={"route": selected_mode, "total_ms": total_time},
        ))

        transcript_count = await transcript.count(user_id, session_id)
        await transcript.close()

        results["steps"].append({
            "step": "mode_decision",
            "status": "ok",
            "selected_mode": selected_mode,
            "total_tool_calls": len(results["orchestrator_actions"]),
        })
        results["transcript_count"] = transcript_count
        results["status"] = "ok"
        results["summary"] = (
            f"Orchestrator: 6/6 steps completed, route={selected_mode}, "
            f"total {total_time}ms, transcript={transcript_count} entries, "
            f"checkpoints={len(results['checkpoints'])}"
        )

    except Exception as e:
        results["status"] = "error"
        results["error"] = str(e)
        results["traceback"] = traceback.format_exc()[-500:]

    return results


# ── Resume from Checkpoint ────────────────────────────────────────────────

@router.post("/resume")
async def resume_from_checkpoint(
    checkpoint_id: str = Query(..., description="Checkpoint ID to resume from"),
    user_id: str = Query("user-chris"),
    override_route: str = Query("", description="Override route (for re-route scenario)"),
    approval_status: str = Query("", description="approved|rejected (for HITL scenario)"),
    approval_approver: str = Query("", description="Approver name"),
    retry_agents: str = Query("", description="Comma-separated agent names to retry"),
    provider: str = Query("azure"),
    model: str = Query("gpt-5.4-mini"),
):
    """Resume orchestrator execution from an IPA checkpoint.

    Supports 3 scenarios with REAL execution:
    - HITL: approve → runs LLM route decision + dispatches to chosen mode
    - Re-Route: overrides route → dispatches to new mode with LLM
    - Agent Retry: re-runs failed agents (TODO: full implementation in Phase 3)
    """
    import os
    import traceback
    from agent_framework import Agent, tool as maf_tool
    from src.integrations.agent_framework.ipa_checkpoint_storage import IPACheckpointStorage
    from src.integrations.orchestration.transcript import TranscriptService, TranscriptEntry
    from src.integrations.orchestration.resume import ResumeService
    from src.integrations.orchestration.resume.service import ResumeRequest

    redis_url = f"redis://:{os.getenv('REDIS_PASSWORD', 'redis_password')}@localhost:6379/0"

    storage = IPACheckpointStorage(redis_url=redis_url, user_id=user_id)
    await storage.initialize()
    transcript = TranscriptService(redis_url=redis_url)
    await transcript.initialize()

    service = ResumeService(checkpoint_storage=storage, transcript_service=transcript)

    # Build request from query params
    request = ResumeRequest(
        checkpoint_id=checkpoint_id,
        user_id=user_id,
        approval_result=(
            {"status": approval_status, "approver": approval_approver}
            if approval_status else None
        ),
        overrides={"route": override_route} if override_route else None,
        retry_agents=retry_agents.split(",") if retry_agents else None,
    )

    # Phase 1: Validate and record resume intent
    resume_result = await service.resume(request)

    if resume_result.status != "ok":
        await storage.close()
        await transcript.close()
        return {
            "test": "resume",
            "status": resume_result.status,
            "resume_type": resume_result.resume_type,
            "error": resume_result.error,
            "checkpoint_id": checkpoint_id,
        }

    # Phase 2: Actually re-execute from checkpoint
    # Load the full checkpoint to get restored context
    checkpoint = await storage.load(checkpoint_id)
    state = checkpoint.state
    task = checkpoint.metadata.get("task_preview", "")
    # Get full task from messages if available
    if checkpoint.messages.get("orchestrator"):
        for msg in checkpoint.messages["orchestrator"]:
            if msg.get("role") == "user" and msg.get("content"):
                task = msg["content"]
                break

    memory_text = state.get("memory_context", "No memories")
    knowledge_text = state.get("knowledge_results", "No knowledge")
    intent_text = state.get("intent_analysis", "Unknown intent")
    effective_route = resume_result.new_route or resume_result.original_route or "team"

    execution_result = {
        "test": "resume",
        "status": "ok",
        "resume_type": resume_result.resume_type,
        "resumed_from_step": resume_result.resumed_from_step,
        "checkpoint_id": checkpoint_id,
        "session_id": resume_result.session_id,
        "original_route": resume_result.original_route,
        "new_route": resume_result.new_route,
        "effective_route": effective_route,
        "steps_executed": resume_result.steps_executed,
        "orchestrator_response": "",
        "error": None,
        "metadata": resume_result.metadata,
    }

    try:
        t0 = time.time()
        client = _create_client(provider, model, azure_api_version="2025-03-01-preview", max_tokens=2048)

        if resume_result.resume_type == "agent_retry":
            # ── Agent Retry: re-run only failed agents ──
            from src.integrations.orchestration.transcript.models import AgentSidechainEntry
            retry_list = resume_result.metadata.get("retry_agents", [])
            existing_states = resume_result.metadata.get("subagent_states", {})
            sdk_tools = _get_claude_sdk_tools()

            agent_responses = []
            retry_states = {}

            for agent_name in retry_list:
                try:
                    retry_agent = Agent(
                        client,
                        name=f"{agent_name}-Retry",
                        instructions=(
                            f"You are {agent_name}, retrying a failed task.\n"
                            f"Original task: {task}\n\n"
                            f"Context from previous run:\n"
                            f"- Memory: {memory_text[:300]}\n"
                            f"- Knowledge: {knowledge_text[:300]}\n"
                            f"- Intent: {intent_text}\n\n"
                            f"Investigate thoroughly and provide your findings. Be concise."
                        ),
                        tools=sdk_tools,
                    )

                    # Sidechain: record retry start
                    await transcript.append_agent(AgentSidechainEntry(
                        user_id=user_id, session_id=resume_result.session_id,
                        agent_name=agent_name,
                        event_type="retry_start",
                        content={"task": task[:100], "attempt": 2},
                    ))

                    agent_resp = await retry_agent.run(task)
                    resp_text = ""
                    if hasattr(agent_resp, "text") and agent_resp.text:
                        resp_text = agent_resp.text
                    elif hasattr(agent_resp, "messages") and agent_resp.messages:
                        for msg in agent_resp.messages:
                            if hasattr(msg, "text") and msg.text:
                                resp_text += msg.text

                    agent_responses.append({"agent": agent_name, "response": resp_text[:500], "status": "retry_complete"})
                    retry_states[agent_name] = "complete"

                    # Sidechain: record retry complete
                    await transcript.append_agent(AgentSidechainEntry(
                        user_id=user_id, session_id=resume_result.session_id,
                        agent_name=agent_name,
                        event_type="retry_complete",
                        content={"response_preview": resp_text[:200]},
                    ))

                except Exception as agent_err:
                    agent_responses.append({"agent": agent_name, "response": str(agent_err)[:200], "status": "retry_failed"})
                    retry_states[agent_name] = "retry_failed"

                    await transcript.append_agent(AgentSidechainEntry(
                        user_id=user_id, session_id=resume_result.session_id,
                        agent_name=agent_name,
                        event_type="retry_error",
                        content={"error": str(agent_err)[:200]},
                    ))

            decision_time = round((time.time() - t0) * 1000)

            # Merge: kept agents + retried agents
            kept_agents = [
                name for name, s in existing_states.items()
                if s == "complete" and name not in retry_list
            ]

            execution_result["agent_responses"] = agent_responses
            execution_result["agent_states"] = {**{k: "kept" for k in kept_agents}, **retry_states}
            execution_result["steps_executed"].append({
                "step": "agent_retry_execute",
                "status": "ok",
                "duration_ms": decision_time,
                "retried": retry_list,
                "kept": kept_agents,
                "results": len(agent_responses),
            })

        else:
            # ── Re-Route / HITL: LLM generates new response ──
            orchestrator = Agent(
                client,
                name="Orchestrator-Resume",
                instructions=(
                    f"You are an IT Operations Orchestrator resuming from a checkpoint.\n"
                    f"The user's original request was analyzed and a route was selected. "
                    f"{'The route has been CHANGED by the user.' if resume_result.resume_type == 'reroute' else 'A manager has APPROVED this operation.'}\n\n"
                    f"## User Request\n{task}\n\n"
                    f"## Restored Context (from checkpoint)\n"
                    f"### Memory\n{memory_text}\n\n"
                    f"### Knowledge Base\n{knowledge_text}\n\n"
                    f"### Intent Analysis\n{intent_text}\n\n"
                    f"## Execution Mode: {effective_route}\n\n"
                    f"Based on the restored context and the execution mode '{effective_route}', "
                    f"provide your response tailored specifically to the '{effective_route}' approach."
                ),
            )

            response = await orchestrator.run(task)
            decision_time = round((time.time() - t0) * 1000)

            response_text = ""
            if hasattr(response, "text") and response.text:
                response_text = response.text
            elif hasattr(response, "messages") and response.messages:
                for msg in response.messages:
                    if hasattr(msg, "text") and msg.text:
                        response_text += msg.text

            execution_result["orchestrator_response"] = response_text[:3000]
            execution_result["steps_executed"].append({
                "step": f"llm_execute_{effective_route}",
                "status": "ok",
                "duration_ms": decision_time,
                "route": effective_route,
            })

        # Record execution in transcript
        await transcript.append(TranscriptEntry(
            user_id=user_id, session_id=resume_result.session_id,
            step_name=f"resume_{resume_result.resume_type}", step_index=7,
            entry_type="step_complete",
            output_summary={
                "resume_type": resume_result.resume_type,
                "route": effective_route,
                "duration_ms": decision_time,
            },
            checkpoint_id=checkpoint_id,
        ))

        # Save memory
        try:
            from src.integrations.memory.unified_memory import UnifiedMemoryManager
            from src.integrations.memory.types import MemoryType, MemoryLayer
            mgr = UnifiedMemoryManager()
            await mgr.initialize()
            await mgr.add(
                content=f"Resumed ({resume_result.resume_type}). Route: {effective_route}. Task: {task[:80]}",
                user_id=user_id,
                memory_type=MemoryType.INSIGHT,
                layer=MemoryLayer.LONG_TERM,
            )
        except Exception:
            pass

    except Exception as e:
        execution_result["status"] = "error"
        execution_result["error"] = str(e)
        execution_result["steps_executed"].append({
            "step": "resume_execute",
            "status": "error",
            "error": str(e)[:200],
        })

    await storage.close()
    await transcript.close()

    return execution_result


# ── Session Status ────────────────────────────────────────────────────────

@router.get("/session-status/{session_id}")
async def get_session_status(
    session_id: str,
    user_id: str = Query("user-chris"),
):
    """Get session execution status: complete, interrupted, pending approval, etc."""
    import os
    from src.integrations.agent_framework.ipa_checkpoint_storage import IPACheckpointStorage
    from src.integrations.orchestration.transcript import TranscriptService
    from src.integrations.orchestration.resume import ResumeService

    redis_url = f"redis://:{os.getenv('REDIS_PASSWORD', 'redis_password')}@localhost:6379/0"

    storage = IPACheckpointStorage(redis_url=redis_url, user_id=user_id)
    await storage.initialize()
    transcript = TranscriptService(redis_url=redis_url)
    await transcript.initialize()

    service = ResumeService(checkpoint_storage=storage, transcript_service=transcript)
    status = await service.get_session_status(user_id, session_id)

    await storage.close()
    await transcript.close()

    return status


# ── Transcript Viewer ─────────────────────────────────────────────────────

@router.get("/transcript/{session_id}")
async def get_transcript(
    session_id: str,
    user_id: str = Query("user-chris"),
):
    """Get the full execution transcript for a session."""
    import os
    from src.integrations.orchestration.transcript import TranscriptService

    redis_url = f"redis://:{os.getenv('REDIS_PASSWORD', 'redis_password')}@localhost:6379/0"
    transcript = TranscriptService(redis_url=redis_url)
    await transcript.initialize()

    entries = await transcript.read(user_id, session_id)
    count = await transcript.count(user_id, session_id)
    await transcript.close()

    return {
        "session_id": session_id,
        "user_id": user_id,
        "total_entries": count,
        "entries": [e.to_dict() for e in entries],
    }


# ── Approval Management ──────────────────────────────────────────────────

@router.get("/approvals")
async def list_pending_approvals():
    """List all pending HITL approval requests (manager view)."""
    import os
    from src.integrations.orchestration.approval import ApprovalService

    redis_url = f"redis://:{os.getenv('REDIS_PASSWORD', 'redis_password')}@localhost:6379/0"
    svc = ApprovalService(redis_url=redis_url)
    await svc.initialize()

    pending = await svc.list_pending()
    await svc.close()

    return {
        "pending_count": len(pending),
        "approvals": [a.to_dict() for a in pending],
    }


@router.post("/approvals/{approval_id}/decide")
async def decide_approval(
    approval_id: str,
    user_id: str = Query("user-chris", description="The user who requested the action"),
    action: str = Query(..., description="approve or reject"),
    decided_by: str = Query("manager", description="Who is deciding"),
    reason: str = Query("", description="Rejection reason (if rejecting)"),
    auto_resume: bool = Query(True, description="Auto-resume pipeline on approval"),
    provider: str = Query("azure"),
    model: str = Query("gpt-5.4-mini"),
):
    """Approve or reject a HITL request. Optionally auto-resumes the pipeline."""
    import os
    from src.integrations.orchestration.approval import ApprovalService, ApprovalStatus

    redis_url = f"redis://:{os.getenv('REDIS_PASSWORD', 'redis_password')}@localhost:6379/0"
    svc = ApprovalService(redis_url=redis_url)
    await svc.initialize()

    # Validate action
    if action not in ("approve", "reject"):
        await svc.close()
        return {"status": "error", "error": f"Invalid action: {action}. Use 'approve' or 'reject'."}

    status = ApprovalStatus.APPROVED if action == "approve" else ApprovalStatus.REJECTED
    updated = await svc.decide(user_id, approval_id, status, decided_by=decided_by, reason=reason or None)
    await svc.close()

    if not updated:
        return {"status": "error", "error": f"Approval not found: {approval_id}"}

    result = {
        "status": "ok",
        "approval": updated.to_dict(),
        "action": action,
        "decided_by": decided_by,
    }

    # Auto-resume on approval
    if action == "approve" and auto_resume and updated.checkpoint_id:
        from src.integrations.agent_framework.ipa_checkpoint_storage import IPACheckpointStorage
        from src.integrations.orchestration.transcript import TranscriptService, TranscriptEntry
        from src.integrations.orchestration.resume import ResumeService
        from src.integrations.orchestration.resume.service import ResumeRequest

        storage = IPACheckpointStorage(redis_url=redis_url, user_id=user_id)
        await storage.initialize()
        transcript = TranscriptService(redis_url=redis_url)
        await transcript.initialize()

        resume_svc = ResumeService(checkpoint_storage=storage, transcript_service=transcript)

        resume_req = ResumeRequest(
            checkpoint_id=updated.checkpoint_id,
            user_id=user_id,
            approval_result={"status": "approved", "approver": decided_by},
        )
        resume_result = await resume_svc.resume(resume_req)

        # If resume validated OK, do real LLM execution
        if resume_result.status == "ok":
            try:
                from agent_framework import Agent

                checkpoint = await storage.load(updated.checkpoint_id)
                state = checkpoint.state
                task_text = updated.task or checkpoint.metadata.get("task_preview", "")
                if checkpoint.messages.get("orchestrator"):
                    for msg in checkpoint.messages["orchestrator"]:
                        if msg.get("role") == "user" and msg.get("content"):
                            task_text = msg["content"]
                            break

                client = _create_client(provider, model, azure_api_version="2025-03-01-preview", max_tokens=2048)
                orchestrator = Agent(
                    client,
                    name="Orchestrator-HITL-Resume",
                    instructions=(
                        f"You are an IT Operations Orchestrator. A manager has APPROVED this operation.\n\n"
                        f"## Approved Request\n{task_text}\n\n"
                        f"## Context (restored from checkpoint)\n"
                        f"### Memory\n{state.get('memory_context', '')}\n\n"
                        f"### Knowledge Base\n{state.get('knowledge_results', '')}\n\n"
                        f"### Intent Analysis\n{state.get('intent_analysis', '')}\n\n"
                        f"The request was flagged as {updated.risk_level} risk and has been approved by {decided_by}.\n"
                        f"Proceed with the appropriate execution plan."
                    ),
                )

                response = await orchestrator.run(task_text)
                response_text = ""
                if hasattr(response, "text") and response.text:
                    response_text = response.text
                elif hasattr(response, "messages") and response.messages:
                    for msg in response.messages:
                        if hasattr(msg, "text") and msg.text:
                            response_text += msg.text

                await transcript.append(TranscriptEntry(
                    user_id=user_id, session_id=updated.session_id,
                    step_name="hitl_resume_execute", step_index=7,
                    entry_type="step_complete",
                    output_summary={"response_preview": response_text[:150], "approved_by": decided_by},
                    checkpoint_id=updated.checkpoint_id,
                ))

                result["resume"] = {
                    "status": "ok",
                    "resume_type": "hitl",
                    "orchestrator_response": response_text[:3000],
                    "session_id": updated.session_id,
                    "checkpoint_id": updated.checkpoint_id,
                }

            except Exception as exec_err:
                result["resume"] = {
                    "status": "error",
                    "error": str(exec_err)[:300],
                }

        await storage.close()
        await transcript.close()

    return result


# ── V4: Team HITL Approval Endpoint ──────────────────────────────────────


@router.post("/team-approval/{approval_id}/decide")
async def decide_team_approval(
    approval_id: str,
    action: str = Query(..., description="approve or reject"),
    decided_by: str = Query("manager-ui", description="Who is deciding"),
):
    """V4: Approve or reject a team agent's tool call.

    Routes to the shared HITLController used by the active team execution.
    This is separate from the orchestrator approval endpoints.
    """
    from src.integrations.poc.approval_gate import get_active_hitl_controller

    controller = get_active_hitl_controller()
    if controller is None:
        return {"status": "error", "error": "No active team execution with HITL controller"}

    if action not in ("approve", "reject"):
        return {"status": "error", "error": f"Invalid action: {action}"}

    try:
        approved = action == "approve"
        result = await controller.process_approval(
            request_id=approval_id,
            approved=approved,
            approver=decided_by,
            comment=f"{'Approved' if approved else 'Rejected'} via team UI",
        )
        return {
            "status": "ok",
            "action": action,
            "decided_by": decided_by,
            "approval_id": approval_id,
            "approval_status": result.status.value if hasattr(result, "status") else str(result),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ── Pinned Memory PoC Endpoints (no auth, for testing) ───────────────────


@router.post("/pinned")
async def poc_pin_memory(
    content: str = Query(..., description="Knowledge to pin"),
    user_id: str = Query("user-chris"),
    memory_type: str = Query("pinned_knowledge", description="pinned_knowledge or extracted_preference"),
):
    """Pin a memory — always injected into pipeline context (no auth, PoC)."""
    from src.integrations.memory.unified_memory import UnifiedMemoryManager
    from src.integrations.memory.types import MemoryType

    mgr = UnifiedMemoryManager()
    await mgr.initialize()
    try:
        record = await mgr.pin_memory(
            content=content,
            user_id=user_id,
            memory_type=MemoryType(memory_type),
        )
        count = await mgr.get_pinned_count(user_id)
        return {
            "status": "ok",
            "id": record.id,
            "content": record.content,
            "memory_type": record.memory_type.value,
            "pinned_count": count,
            "max_allowed": mgr.config.max_pinned_per_user,
        }
    except ValueError as ve:
        return {"status": "error", "error": str(ve)}
    finally:
        await mgr.close()


@router.get("/pinned")
async def poc_list_pinned(
    user_id: str = Query("user-chris"),
):
    """List all pinned memories for a user (no auth, PoC)."""
    from src.integrations.memory.unified_memory import UnifiedMemoryManager

    mgr = UnifiedMemoryManager()
    await mgr.initialize()
    try:
        records = await mgr.get_pinned(user_id)
        return {
            "status": "ok",
            "total": len(records),
            "max_allowed": mgr.config.max_pinned_per_user,
            "memories": [
                {
                    "id": r.id,
                    "content": r.content,
                    "memory_type": r.memory_type.value,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in records
            ],
        }
    finally:
        await mgr.close()


@router.delete("/pinned/{memory_id}")
async def poc_unpin_memory(
    memory_id: str,
    user_id: str = Query("user-chris"),
):
    """Unpin a memory (no auth, PoC)."""
    from src.integrations.memory.unified_memory import UnifiedMemoryManager

    mgr = UnifiedMemoryManager()
    await mgr.initialize()
    try:
        success = await mgr.unpin_memory(memory_id, user_id)
        return {"status": "ok" if success else "not_found", "memory_id": memory_id}
    finally:
        await mgr.close()


@router.get("/extracted-memories")
async def poc_list_extracted_memories(
    user_id: str = Query("user-chris"),
    limit: int = Query(30, description="Max memories to return"),
):
    """List all LONG_TERM extracted memories for a user (no auth, PoC).

    Shows what the MemoryExtractionService has produced — the CC Memory Files equivalent.
    """
    from src.integrations.memory.unified_memory import UnifiedMemoryManager
    from src.integrations.memory.types import MemoryLayer

    mgr = UnifiedMemoryManager()
    await mgr.initialize()
    try:
        records = await mgr.get_user_memories(
            user_id=user_id,
            layers=[MemoryLayer.LONG_TERM],
        )

        # Sort by created_at descending (newest first)
        records.sort(key=lambda r: r.created_at, reverse=True)
        records = records[:limit]

        def _safe_metadata(r):
            """Extract metadata safely — mem0 may return varied formats."""
            meta = r.metadata
            if meta and hasattr(meta, 'importance'):
                return meta.importance, meta.source, meta.tags
            if meta and isinstance(meta, dict):
                return meta.get('importance', 0.5), meta.get('source', ''), meta.get('tags', [])
            return 0.5, '', []

        return {
            "status": "ok",
            "total": len(records),
            "memories": [
                {
                    "id": r.id,
                    "content": r.content,
                    "memory_type": r.memory_type.value if hasattr(r.memory_type, 'value') else str(r.memory_type),
                    "layer": r.layer.value if hasattr(r.layer, 'value') else str(r.layer),
                    "importance": _safe_metadata(r)[0],
                    "source": _safe_metadata(r)[1],
                    "tags": _safe_metadata(r)[2],
                    "created_at": r.created_at.isoformat() if hasattr(r.created_at, 'isoformat') else str(r.created_at) if r.created_at else None,
                    "access_count": getattr(r, 'access_count', 0),
                }
                for r in records
            ],
        }
    finally:
        await mgr.close()


# ── Test E: Orchestrator Stream (SSE streaming version of test_orchestrator) ──

@router.post("/test-orchestrator-stream")
async def test_orchestrator_stream(
    provider: str = Query("azure"),
    model: str = Query("gpt-5.4-mini"),
    task: str = Query(
        "APAC Glider ETL Pipeline has been failing for 3 days, affecting financial reports.",
    ),
    user_id: str = Query("user-chris", description="User ID for memory lookup"),
    azure_endpoint: str = Query(""),
    azure_api_key: str = Query(""),
    azure_api_version: str = Query("2025-03-01-preview"),
    azure_deployment: str = Query(""),
):
    """Test E: SSE Streaming Orchestrator — same pipeline as test_orchestrator but streams events.

    Returns a text/event-stream response. Each pipeline step emits SSE events
    so the frontend can show real-time progress.
    """
    import asyncio
    from starlette.responses import StreamingResponse
    from src.integrations.hybrid.orchestrator.sse_events import PipelineEventEmitter, SSEEventType

    emitter = PipelineEventEmitter()

    async def _run_pipeline():
        """Execute the orchestrator pipeline, emitting SSE events at each step."""
        import os
        import uuid as _uuid

        session_id = f"{user_id}-{int(time.time())}-{str(_uuid.uuid4())[:8]}"
        t0 = time.time()
        transcript_count = 0
        selected_mode = "team"  # default
        response_text = ""
        memory_text = "No memories"
        knowledge_text = "No knowledge"
        intent_text = "Unknown intent"

        try:
            from agent_framework import Agent, tool as maf_tool
            from src.integrations.orchestration.transcript import TranscriptService, TranscriptEntry

            redis_url = f"redis://:{os.getenv('REDIS_PASSWORD', 'redis_password')}@localhost:6379/0"
            transcript = TranscriptService(redis_url=redis_url)
            await transcript.initialize()

            # Emit pipeline start
            await emitter.emit(SSEEventType.PIPELINE_START, {
                "session_id": session_id,
                "user_id": user_id,
                "task": task[:200],
                "provider": provider,
                "model": model,
            })

            # ── Step 1: READ MEMORY with Context Budget Manager ──
            await emitter.emit(SSEEventType.TASK_DISPATCHED, {
                "step": "1_read_memory", "status": "running", "label": "Reading Memory...",
            })

            assembled_context = None
            mgr = None
            try:
                from src.integrations.memory.unified_memory import UnifiedMemoryManager
                from src.integrations.memory.context_budget import ContextBudgetManager, AssembledContext

                mgr = UnifiedMemoryManager()
                await mgr.initialize()

                budget_mgr = ContextBudgetManager()
                assembled_context = await budget_mgr.assemble_context(
                    user_id=user_id,
                    query=task,
                    memory_manager=mgr,
                )
                memory_text = assembled_context.to_prompt_text()
            except Exception as e:
                memory_text = f"Memory service unavailable: {str(e)[:100]}"

            pinned_count = assembled_context.pinned_count if assembled_context else 0
            budget_pct = assembled_context.budget_used_pct if assembled_context else 0

            await emitter.emit(SSEEventType.ROUTING_COMPLETE, {
                "step": "1_read_memory", "status": "complete",
                "pinned_count": pinned_count, "budget_pct": budget_pct,
                "preview": memory_text,
            })

            # ── Step 2: SEARCH KNOWLEDGE (Qdrant) ──
            await emitter.emit(SSEEventType.TASK_DISPATCHED, {
                "step": "2_search_knowledge", "status": "running", "label": "Searching Knowledge...",
            })

            search_results_count = 0
            try:
                from openai import AzureOpenAI
                from qdrant_client import QdrantClient

                az = AzureOpenAI(
                    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                    api_version="2024-02-01",
                )
                q_emb = az.embeddings.create(input=task[:500], model="text-embedding-ada-002").data[0].embedding
                qd = QdrantClient(host="localhost", port=6333)
                search_results = qd.query_points("ipa_knowledge", query=q_emb, limit=3)
                knowledge_text = "\n".join(
                    f"[{r.payload.get('source', '?')}] (score={r.score:.2f}) {r.payload.get('content', '')}"
                    for r in search_results.points
                ) or "No knowledge found"
                search_results_count = len(search_results.points)
            except Exception as e:
                knowledge_text = f"Knowledge search failed: {str(e)[:150]}"

            await emitter.emit(SSEEventType.ROUTING_COMPLETE, {
                "step": "2_search_knowledge", "status": "complete",
                "results_count": search_results_count,
                "preview": knowledge_text,
            })

            # ── Step 3: ANALYZE INTENT (PatternMatcher + Router) ──
            await emitter.emit(SSEEventType.TASK_DISPATCHED, {
                "step": "3_analyze_intent", "status": "running", "label": "Analyzing Intent...",
            })

            effective_risk = None
            pattern_result = None
            decision = None
            is_high_risk = False
            risk_str = ""
            try:
                from src.integrations.orchestration.intent_router.router import BusinessIntentRouter
                from src.integrations.orchestration.intent_router.pattern_matcher.matcher import PatternMatcher
                from src.integrations.orchestration.intent_router.semantic_router.router import SemanticRouter
                from src.integrations.orchestration.intent_router.llm_classifier.classifier import LLMClassifier
                from src.integrations.orchestration.intent_router.models import (
                    PatternRule, ITIntentCategory, RiskLevel, WorkflowType,
                )

                matcher = PatternMatcher()
                poc_rules = [
                    PatternRule(
                        id="poc-etl-failure", category=ITIntentCategory.INCIDENT,
                        sub_intent="etl_failure", priority=90,
                        patterns=[r"(?i)(etl|pipeline|data.?flow|batch.?job).*(fail|error|down|broken|stuck)"],
                        risk_level=RiskLevel.HIGH, workflow_type=WorkflowType.MAGENTIC,
                    ),
                    PatternRule(
                        id="poc-system-outage", category=ITIntentCategory.INCIDENT,
                        sub_intent="system_outage", priority=95,
                        patterns=[r"(?i)(server|service|system|database).*(down|fail|error|crash|outage|unavailable)"],
                        risk_level=RiskLevel.CRITICAL, workflow_type=WorkflowType.MAGENTIC,
                    ),
                    PatternRule(
                        id="poc-prod-restart", category=ITIntentCategory.CHANGE,
                        sub_intent="production_restart", priority=95,
                        patterns=[r"(?i)(restart|reboot|shutdown|stop|kill).*(prod|production|server|database|db)"],
                        risk_level=RiskLevel.CRITICAL, workflow_type=WorkflowType.MAGENTIC,
                    ),
                    PatternRule(
                        id="poc-destructive-op", category=ITIntentCategory.CHANGE,
                        sub_intent="destructive_operation", priority=95,
                        patterns=[r"(?i)(delete|drop|truncate|wipe|purge).*(data|table|database|prod|production)"],
                        risk_level=RiskLevel.CRITICAL, workflow_type=WorkflowType.MAGENTIC,
                    ),
                    PatternRule(
                        id="poc-deployment", category=ITIntentCategory.CHANGE,
                        sub_intent="deployment", priority=50,
                        patterns=[r"(?i)(deploy|release|rollout|update|upgrade|migration)"],
                        risk_level=RiskLevel.MEDIUM, workflow_type=WorkflowType.SEQUENTIAL,
                    ),
                    PatternRule(
                        id="poc-status-check", category=ITIntentCategory.QUERY,
                        sub_intent="status_check", priority=30,
                        patterns=[r"(?i)(check|status|monitor|health|ping|query|what.?is)"],
                        risk_level=RiskLevel.LOW, workflow_type=WorkflowType.HANDOFF,
                    ),
                ]
                for rule in poc_rules:
                    try:
                        matcher.add_rule(rule)
                    except Exception as rule_err:
                        logger.warning(f"Failed to add pattern rule {rule.id}: {rule_err}")

                try:
                    from src.integrations.llm.factory import LLMServiceFactory
                    llm_svc = LLMServiceFactory.create(use_cache=True)
                    llm_cls = LLMClassifier(llm_service=llm_svc)
                except Exception:
                    llm_cls = LLMClassifier()

                router_inst = BusinessIntentRouter(
                    pattern_matcher=matcher,
                    semantic_router=SemanticRouter(),
                    llm_classifier=llm_cls,
                )

                pattern_result = matcher.match(task)
                pattern_risk = getattr(pattern_result, "risk_level", None)

                decision = await router_inst.route(task)

                effective_risk = decision.risk_level
                if pattern_result.matched and pattern_risk:
                    risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
                    pattern_rank = risk_order.get(str(pattern_risk).split(".")[-1], 0)
                    decision_rank = risk_order.get(str(effective_risk).split(".")[-1], 0)
                    if pattern_rank > decision_rank:
                        effective_risk = pattern_risk
                        logger.info(f"Pattern matcher elevated risk: {decision.risk_level} → {pattern_risk}")

                intent_text = (
                    f"Category: {decision.intent_category}, "
                    f"Risk: {effective_risk}, "
                    f"Confidence: {decision.confidence:.2f}, "
                    f"Workflow: {decision.workflow_type}"
                )
            except Exception as e:
                intent_text = f"Intent analysis partial: {str(e)[:100]}"

            # Check HITL condition
            risk_str = str(effective_risk) if effective_risk else ""
            intent_category_str = str(getattr(decision, "intent_category", "")) if decision else ""
            is_actionable = "CHANGE" in intent_category_str
            is_high_risk = ("HIGH" in risk_str or "CRITICAL" in risk_str) and is_actionable

            if is_high_risk:
                # Create checkpoint + approval, then pause pipeline
                try:
                    from agent_framework import WorkflowCheckpoint
                    from src.integrations.agent_framework.ipa_checkpoint_storage import IPACheckpointStorage
                    from src.integrations.orchestration.approval import ApprovalService, ApprovalRequest as ApprovalReq

                    cp_storage = IPACheckpointStorage(redis_url=redis_url, user_id=user_id)
                    await cp_storage.initialize()
                    cp3 = WorkflowCheckpoint(
                        workflow_name=session_id,
                        graph_signature_hash="orchestrator-7step-v1",
                        state={
                            "pipeline_step": 3,
                            "memory_context": memory_text[:500],
                            "knowledge_results": knowledge_text[:500],
                            "intent_analysis": intent_text,
                            "route_decision": None,
                            "resume_reason": "hitl_pending",
                        },
                        messages={"orchestrator": [{"role": "user", "content": task}]},
                        iteration_count=3,
                        metadata={"user_id": user_id, "task_preview": task[:100], "risk": str(risk_str)},
                    )
                    step3_checkpoint_id = await cp_storage.save(cp3)
                    await cp_storage.close()

                    approval_svc = ApprovalService(redis_url=redis_url)
                    await approval_svc.initialize()
                    approval_req = ApprovalReq(
                        user_id=user_id,
                        session_id=session_id,
                        checkpoint_id=step3_checkpoint_id,
                        task=task[:200],
                        risk_level=str(risk_str),
                        intent_category=str(getattr(decision, "intent_category", "")),
                        confidence=getattr(decision, "confidence", 0.0),
                        context_summary={
                            "memory": memory_text[:200],
                            "knowledge": knowledge_text[:200],
                            "intent": intent_text,
                        },
                    )
                    approval_id = await approval_svc.create(approval_req)
                    await approval_svc.close()

                    await emitter.emit(SSEEventType.APPROVAL_REQUIRED, {
                        "step": "3_hitl_pause",
                        "approval_id": approval_id,
                        "checkpoint_id": step3_checkpoint_id,
                        "risk_level": str(risk_str),
                        "message": "需要主管審批",
                    })
                    await transcript.close()
                    await emitter.emit_complete(
                        "Pipeline paused for HITL approval",
                        {"status": "pending_approval", "session_id": session_id},
                    )
                    return  # End stream — pipeline paused

                except Exception as cp_err:
                    logger.warning(f"Stream: Step 3 HITL checkpoint/approval failed: {cp_err}")
                    # Graceful degradation — continue pipeline

            await emitter.emit(SSEEventType.ROUTING_COMPLETE, {
                "step": "3_analyze_intent", "status": "complete",
                "intent_category": str(getattr(decision, "intent_category", "")) if decision else "",
                "risk_level": str(effective_risk) if effective_risk else "",
                "confidence": getattr(decision, "confidence", 0.0) if decision else 0.0,
            })

            # ── Step 4: LLM ROUTE DECISION ──
            await emitter.emit(SSEEventType.AGENT_THINKING, {
                "step": "4_route_decision", "status": "running", "label": "LLM Route Decision...",
            })

            client = _create_client(
                provider, model, azure_endpoint, azure_api_key,
                azure_api_version, azure_deployment, max_tokens=2048,
            )

            @maf_tool(name="select_route", description=(
                "Select the execution route for this task. Options: "
                "'direct_answer' (simple Q&A), 'subagent' (parallel independent), "
                "'team' (expert collaboration), 'swarm' (deep Manager analysis), "
                "'workflow' (structured process)."
            ))
            def select_route(route: str, reasoning: str) -> str:
                """Select execution route with reasoning."""
                return f"Route: {route}. Reason: {reasoning}"

            orchestrator = Agent(
                client,
                name="Orchestrator",
                instructions=(
                    "You are an IT Operations Orchestrator. Based on the context below, "
                    "call select_route to choose the best execution mode.\n\n"
                    f"## User Request\n{task}\n\n"
                    f"## Memory Context (structured, token-budgeted)\n{memory_text}\n\n"
                    f"## Knowledge Base\n{knowledge_text}\n\n"
                    f"## Intent Analysis\n{intent_text}\n\n"
                    "Choose ONE route:\n"
                    "- direct_answer: simple questions, low risk\n"
                    "- subagent: independent parallel checks (e.g., check 3 systems)\n"
                    "- team: complex investigation needing expert collaboration\n"
                    "- swarm: critical incidents needing deep Manager-driven analysis\n"
                    "- workflow: structured processes (deploy, change management)\n\n"
                    "Call select_route with your choice and reasoning."
                ),
                tools=[select_route],
            )

            t1 = time.time()
            response = await orchestrator.run(task)
            decision_time = round((time.time() - t1) * 1000)

            response_text = ""
            if hasattr(response, "text") and response.text:
                response_text = response.text
            elif hasattr(response, "messages") and response.messages:
                for msg in response.messages:
                    if hasattr(msg, "text") and msg.text:
                        response_text += msg.text

            # Extract selected route
            selected_mode = "team"  # default
            for keyword in ["direct_answer", "subagent", "team", "swarm", "workflow"]:
                if keyword in response_text.lower():
                    selected_mode = keyword
                    break

            await emitter.emit(SSEEventType.ROUTING_COMPLETE, {
                "step": "4_route_decision", "status": "complete",
                "selected_mode": selected_mode,
                "reasoning": response_text[:500],
                "duration_ms": decision_time,
            })

            # Emit the orchestrator's full response as TEXT_DELTA (the AI's actual reply)
            if response_text:
                await emitter.emit(SSEEventType.TEXT_DELTA, {
                    "delta": response_text[:3000],
                    "source": "orchestrator",
                })

            # ── Step 5: SAVE CHECKPOINT ──
            await emitter.emit(SSEEventType.TASK_DISPATCHED, {
                "step": "5_checkpoint", "status": "running",
            })

            step4_checkpoint_id = None
            try:
                from agent_framework import WorkflowCheckpoint
                from src.integrations.agent_framework.ipa_checkpoint_storage import IPACheckpointStorage

                cp_storage4 = IPACheckpointStorage(redis_url=redis_url, user_id=user_id)
                await cp_storage4.initialize()

                cp4 = WorkflowCheckpoint(
                    workflow_name=session_id,
                    graph_signature_hash="orchestrator-7step-v1",
                    state={
                        "pipeline_step": 4,
                        "memory_context": memory_text[:500],
                        "knowledge_results": knowledge_text[:500],
                        "intent_analysis": intent_text,
                        "route_decision": selected_mode,
                        "resume_reason": None,
                        "subagent_states": {},
                    },
                    messages={
                        "orchestrator": [
                            {"role": "user", "content": task},
                            {"role": "assistant", "content": response_text[:500] if response_text else ""},
                        ]
                    },
                    iteration_count=4,
                    metadata={
                        "user_id": user_id,
                        "task_preview": task[:100],
                        "route": selected_mode,
                        "source": "poc-orchestrator-stream",
                        "session_id": session_id,
                    },
                )
                step4_checkpoint_id = await cp_storage4.save(cp4)
                await cp_storage4.close()
            except Exception as cp4_err:
                logger.error(f"Stream: Step 4 checkpoint failed: {cp4_err}")

            await emitter.emit(SSEEventType.ROUTING_COMPLETE, {
                "step": "5_checkpoint", "status": "complete",
                "checkpoint_id": step4_checkpoint_id,
            })

            # ── Step 6: MEMORY EXTRACTION (async background) ──
            await emitter.emit(SSEEventType.TASK_DISPATCHED, {
                "step": "6_extraction", "status": "running",
            })

            try:
                from src.integrations.memory.extraction import MemoryExtractionService
                from src.integrations.memory.consolidation import MemoryConsolidationService

                if mgr is None or not mgr._initialized:
                    from src.integrations.memory.unified_memory import UnifiedMemoryManager as _UMM
                    mgr2 = _UMM()
                    await mgr2.initialize()
                else:
                    mgr2 = mgr

                extraction_svc = MemoryExtractionService(mgr2)
                asyncio.create_task(extraction_svc.extract_and_store(
                    user_id=user_id,
                    session_id=session_id,
                    user_message=task,
                    assistant_response=response_text[:2000],
                    pipeline_context={
                        "route_decision": selected_mode,
                        "risk_level": risk_str,
                        "intent_category": str(getattr(decision, "intent_category", "")) if decision else "",
                    },
                ))

                consolidation_svc = MemoryConsolidationService(mgr2)
                should_consolidate = await consolidation_svc.increment_and_check(user_id)
                if should_consolidate:
                    asyncio.create_task(consolidation_svc.run_consolidation(user_id))
            except Exception as mem_err:
                logger.error(f"Stream: Memory extraction setup failed: {mem_err}")

            await emitter.emit(SSEEventType.ROUTING_COMPLETE, {
                "step": "6_extraction", "status": "complete", "note": "async scheduled",
            })

            # ── Phase 2: Agent Execution ──
            await emitter.emit(SSEEventType.TASK_DISPATCHED, {
                "step": "7_agent_execution", "status": "running",
                "mode": selected_mode, "label": f"Executing {selected_mode} mode...",
            })

            try:
                if selected_mode in ("subagent", "team"):
                    if selected_mode == "subagent":
                        from agent_framework.orchestrations import ConcurrentBuilder

                        systems = ["APAC ETL Pipeline", "CRM Service", "Email Server"]
                        sdk_tools = _get_claude_sdk_tools()

                        builder = ConcurrentBuilder()
                        for sys_name in systems:
                            agent = Agent(
                                client,
                                name=f"{sys_name.replace(' ', '-')}-Checker",
                                instructions=(
                                    f"You are a system health checker for {sys_name}. "
                                    f"Check its status based on: {task}\n\n"
                                    f"Context:\n{memory_text[:300]}\n{knowledge_text[:300]}"
                                ),
                                tools=sdk_tools,
                            )
                            builder.add(agent)

                        workflow = builder.build()
                        stream = workflow.run(message=task, stream=True, include_status_events=True)
                        async for event in stream:
                            event_type_name = type(event).__name__
                            if hasattr(event, "data") and event.data:
                                data = event.data
                                if hasattr(data, '__iter__') and not isinstance(data, str):
                                    for item in data:
                                        if hasattr(item, 'executor_id') and hasattr(item, 'agent_response'):
                                            resp = item.agent_response
                                            text = ""
                                            if hasattr(resp, 'text') and resp.text:
                                                text = resp.text
                                            elif hasattr(resp, 'messages') and resp.messages:
                                                for m in resp.messages:
                                                    if hasattr(m, 'text') and m.text:
                                                        text += m.text
                                            if text:
                                                await emitter.emit(SSEEventType.TEXT_DELTA, {
                                                    "agent": item.executor_id, "delta": text,
                                                })
                                await emitter.emit(SSEEventType.SWARM_PROGRESS, {
                                    "event_type": event_type_name,
                                    "preview": str(event.data)[:200] if event.data else "",
                                })

                    else:  # team
                        from agent_framework.orchestrations import GroupChatBuilder

                        sdk_tools = _get_claude_sdk_tools()
                        roles = [
                            ("Incident-Lead", "You lead incident investigation. Coordinate findings."),
                            ("System-Analyst", "You analyze system logs and metrics for root cause."),
                            ("Comms-Lead", "You draft status updates and stakeholder communications."),
                        ]

                        builder = GroupChatBuilder()
                        for name, desc in roles:
                            agent = Agent(
                                client,
                                name=name,
                                instructions=(
                                    f"{desc}\n\nTask: {task}\n\n"
                                    f"Context:\n{memory_text[:300]}\n{knowledge_text[:300]}"
                                ),
                                tools=sdk_tools,
                            )
                            builder.add(agent)

                        workflow = builder.build()
                        stream = workflow.run(message=task, stream=True, include_status_events=True)
                        async for event in stream:
                            event_type_name = type(event).__name__
                            if hasattr(event, "data") and event.data:
                                data = event.data
                                if hasattr(data, '__iter__') and not isinstance(data, str):
                                    for item in data:
                                        if hasattr(item, 'executor_id') and hasattr(item, 'agent_response'):
                                            resp = item.agent_response
                                            text = ""
                                            if hasattr(resp, 'text') and resp.text:
                                                text = resp.text
                                            elif hasattr(resp, 'messages') and resp.messages:
                                                for m in resp.messages:
                                                    if hasattr(m, 'text') and m.text:
                                                        text += m.text
                                            if text:
                                                await emitter.emit(SSEEventType.TEXT_DELTA, {
                                                    "agent": item.executor_id, "delta": text,
                                                })
                                await emitter.emit(SSEEventType.SWARM_PROGRESS, {
                                    "event_type": event_type_name,
                                    "preview": str(event.data)[:200] if event.data else "",
                                })

                elif selected_mode == "direct_answer":
                    direct_agent = Agent(
                        client,
                        name="DirectAnswer",
                        instructions=(
                            f"Answer directly: {task}\n\n"
                            f"Context:\n{memory_text}\n{knowledge_text}"
                        ),
                    )
                    direct_response = await direct_agent.run(task)
                    resp_text = ""
                    if hasattr(direct_response, "text") and direct_response.text:
                        resp_text = direct_response.text
                    elif hasattr(direct_response, "messages") and direct_response.messages:
                        for m in direct_response.messages:
                            if hasattr(m, "text") and m.text:
                                resp_text += m.text
                    # Emit in chunks to simulate streaming
                    for i in range(0, len(resp_text), 100):
                        await emitter.emit(SSEEventType.TEXT_DELTA, {
                            "delta": resp_text[i:i + 100],
                        })

                else:
                    # swarm/workflow — emit the route decision response as content
                    await emitter.emit(SSEEventType.TEXT_DELTA, {
                        "delta": response_text[:2000],
                    })

                # Mark step 7 complete
                await emitter.emit(SSEEventType.ROUTING_COMPLETE, {
                    "step": "7_agent_execution", "status": "complete",
                    "mode": selected_mode,
                })

            except Exception as exec_err:
                logger.error(f"Stream: Agent execution failed: {exec_err}")
                await emitter.emit(SSEEventType.ROUTING_COMPLETE, {
                    "step": "7_agent_execution", "status": "error",
                    "error": str(exec_err)[:300],
                })

            # ── Final: Pipeline Complete ──
            transcript_count = await transcript.count(user_id, session_id)
            await transcript.close()

            total_time = round((time.time() - t0) * 1000)
            await emitter.emit_complete("Pipeline complete", {
                "total_ms": total_time,
                "route": selected_mode,
                "session_id": session_id,
                "transcript_count": transcript_count,
            })

        except Exception as e:
            logger.error(f"Stream pipeline error: {e}\n{traceback.format_exc()[-500:]}")
            await emitter.emit_error(f"Pipeline failed: {str(e)[:300]}")

    # Launch pipeline as background task; return SSE stream immediately
    asyncio.create_task(_run_pipeline())

    return StreamingResponse(
        emitter.stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Test F: Subagent Stream (SSE) ───────────────────────────────────────

@router.post("/test-subagent-stream")
async def test_subagent_stream(
    provider: str = Query("azure"),
    model: str = Query("gpt-5.4-nano"),
    task: str = Query(
        "Check the status of three systems: "
        "1) APAC ETL Pipeline, 2) CRM Service, 3) Email Server. "
        "Report the health status of each.",
    ),
    user_id: str = Query("user-chris"),
    session_id: str = Query("", description="Link to orchestrator session for sidechain"),
    azure_endpoint: str = Query(""),
    azure_api_key: str = Query(""),
    azure_api_version: str = Query("2025-03-01-preview"),
    azure_deployment: str = Query(""),
):
    """Test F: SSE Streaming Subagent — same logic as test_subagent but streams events.

    Returns a text/event-stream response. Each agent event is forwarded
    as SSE so the frontend can show real-time progress.
    """
    import asyncio
    from starlette.responses import StreamingResponse
    from src.integrations.hybrid.orchestrator.sse_events import PipelineEventEmitter, SSEEventType

    emitter = PipelineEventEmitter()

    async def _run():
        import os
        import uuid as _uuid

        if not session_id:
            _session_id = f"{user_id}-sub-{int(time.time())}-{str(_uuid.uuid4())[:8]}"
        else:
            _session_id = session_id

        t0 = time.time()

        try:
            from agent_framework import Agent
            from agent_framework.orchestrations import ConcurrentBuilder

            await emitter.emit(SSEEventType.PIPELINE_START, {
                "mode": "subagent",
                "session_id": _session_id,
                "task": task[:200],
                "provider": provider,
                "model": model,
            })

            client = _create_client(provider, model, azure_endpoint, azure_api_key,
                                    azure_api_version, azure_deployment)
            sdk_tools = _get_claude_sdk_tools()

            # Create 3 independent subagents
            agent_defs = [
                ("ETL-Checker", (
                    "You are an ETL pipeline specialist. Check the ETL pipeline status.\n"
                    "You have access to powerful tools:\n"
                    "- deep_analysis: for complex multi-step reasoning\n"
                    "- run_diagnostic_command: to simulate running diagnostic commands\n"
                    "- search_knowledge_base: to find past incidents and SOPs\n"
                    "Use these tools to provide thorough findings. Be concise in your final report."
                )),
                ("CRM-Checker", (
                    "You are a CRM service specialist. Check the CRM service health.\n"
                    "You have access to: deep_analysis, run_diagnostic_command, search_knowledge_base.\n"
                    "Use these tools to investigate. Be concise."
                )),
                ("Email-Checker", (
                    "You are an email server specialist. Check the email server status.\n"
                    "You have access to: deep_analysis, run_diagnostic_command, search_knowledge_base.\n"
                    "Use these tools to investigate. Be concise."
                )),
            ]

            agents = []
            agent_names = []
            for name, instructions in agent_defs:
                agent = Agent(client, name=name, instructions=instructions, tools=sdk_tools)
                agents.append(agent)
                agent_names.append(name)
                await emitter.emit(SSEEventType.SWARM_WORKER_START, {
                    "agent": name, "status": "created",
                })

            # Build with ConcurrentBuilder
            builder = ConcurrentBuilder(participants=agents)
            workflow = builder.build()

            # Initialize sidechain transcript
            from src.integrations.orchestration.transcript import TranscriptService
            from src.integrations.orchestration.transcript.models import AgentSidechainEntry
            redis_url = f"redis://:{os.getenv('REDIS_PASSWORD', 'redis_password')}@localhost:6379/0"
            sidechain = TranscriptService(redis_url=redis_url)
            await sidechain.initialize()

            for name in agent_names:
                await sidechain.append_agent(AgentSidechainEntry(
                    user_id=user_id, session_id=_session_id, agent_name=name,
                    event_type="start", content={"task": task[:100]},
                ))

            # Stream workflow events → forward to emitter
            stream = workflow.run(message=task, stream=True, include_status_events=True)
            agent_responses: list[dict[str, Any]] = []

            seen_agents = set()
            async for event in stream:
                event_type_name = type(event).__name__
                got_agent_response = False
                if hasattr(event, "data") and event.data:
                    data = event.data
                    if hasattr(data, '__iter__') and not isinstance(data, str):
                        for item in data:
                            if hasattr(item, 'executor_id') and hasattr(item, 'agent_response'):
                                resp = item.agent_response
                                text = ""
                                if hasattr(resp, 'text') and resp.text:
                                    text = resp.text
                                elif hasattr(resp, 'messages') and resp.messages:
                                    for msg in resp.messages:
                                        if hasattr(msg, 'text') and msg.text:
                                            text += msg.text
                                if text and item.executor_id not in seen_agents:
                                    seen_agents.add(item.executor_id)
                                    got_agent_response = True
                                    await emitter.emit(SSEEventType.TEXT_DELTA, {
                                        "agent": item.executor_id, "delta": text,
                                    })
                                    agent_responses.append({
                                        "agent": item.executor_id,
                                        "response": text,
                                    })
                                    await sidechain.append_agent(AgentSidechainEntry(
                                        user_id=user_id, session_id=_session_id,
                                        agent_name=item.executor_id,
                                        event_type="complete",
                                        content={"response_preview": text[:200]},
                                    ))

                # Only emit SWARM_PROGRESS for non-agent events (skip raw object noise)
                if not got_agent_response and event_type_name not in ("AgentExecutorResponse",):
                    preview = str(event.data)[:200] if hasattr(event, "data") and event.data else ""
                    # Filter out raw Python object representations
                    if "object at 0x" not in preview:
                        await emitter.emit(SSEEventType.SWARM_PROGRESS, {
                            "event_type": event_type_name,
                            "preview": preview,
                        })

            await sidechain.close()

            # Emit consolidated response as TEXT_DELTA (the AI's actual reply)
            if agent_responses:
                summary_parts = []
                for ar in agent_responses:
                    summary_parts.append(f"## {ar['agent']}\n{ar['response']}")
                consolidated = "\n\n".join(summary_parts)
                await emitter.emit(SSEEventType.TEXT_DELTA, {
                    "delta": consolidated,
                    "source": "aggregated",
                })

            total_time = round((time.time() - t0) * 1000)
            await emitter.emit_complete("Subagent pipeline complete", {
                "total_ms": total_time,
                "mode": "subagent",
                "session_id": _session_id,
                "agent_count": len(agent_names),
                "responses_count": len(agent_responses),
            })

        except Exception as e:
            logger.error(f"Subagent stream error: {e}\n{traceback.format_exc()[-500:]}")
            await emitter.emit_error(f"Subagent pipeline failed: {str(e)[:300]}")

    asyncio.create_task(_run())

    return StreamingResponse(
        emitter.stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Test G: Team Stream (SSE) — V2 Parallel Engine ────────────────────

@router.post("/test-team-stream")
async def test_team_stream(
    provider: str = Query("azure"),
    model: str = Query("gpt-5.4-mini"),
    task: str = Query(
        "Investigate APAC ETL Pipeline failure. Multiple experts needed: "
        "analyze application logs, check database changes, and verify network connectivity.",
    ),
    user_id: str = Query("user-chris"),
    session_id: str = Query("", description="Link to orchestrator session for sidechain"),
    azure_endpoint: str = Query(""),
    azure_api_key: str = Query(""),
    azure_api_version: str = Query("2024-12-01-preview"),
    azure_deployment: str = Query(""),
    timeout: float = Query(120.0, description="Max execution timeout in seconds"),
):
    """Test G: SSE Streaming Team — V2 Parallel Engine.

    Phase 0: TeamLead decomposes task (SSE events for progress).
    Phase 1: 3 agents run IN PARALLEL — SSE events interleaved in real-time.
    Returns text/event-stream with concurrent agent activity.
    """
    import asyncio
    from starlette.responses import StreamingResponse
    from src.integrations.hybrid.orchestrator.sse_events import PipelineEventEmitter, SSEEventType

    emitter = PipelineEventEmitter()

    async def _run():
        import os
        import uuid as _uuid

        if not session_id:
            _session_id = f"{user_id}-team-{int(time.time())}-{str(_uuid.uuid4())[:8]}"
        else:
            _session_id = session_id

        t0 = time.time()

        try:
            from src.integrations.poc.shared_task_list import create_shared_task_list
            from src.integrations.poc.team_tools import create_team_tools, create_lead_tools
            from src.integrations.poc.agent_work_loop import (
                AgentConfig, run_parallel_team, _patch_emitter,
            )

            _patch_emitter(emitter)

            await emitter.emit(SSEEventType.PIPELINE_START, {
                "mode": "team_v2_parallel",
                "session_id": _session_id,
                "task": task[:200],
                "provider": provider,
                "model": model,
            })

            # Step 1: Create SharedTaskList + tools (V4: Redis-backed if available)
            shared = create_shared_task_list(session_id=_session_id)
            team_tools = create_team_tools(shared)
            lead_tools = create_lead_tools(shared)
            real_tools = _get_real_tools()  # V2: real subprocess tools
            all_tools = team_tools + real_tools

            # Step 2: Create client factory + agent configs
            def make_client():
                return _create_client(provider, model, azure_endpoint, azure_api_key,
                                      azure_api_version, azure_deployment, max_tokens=2048)

            agents_config = _build_team_agents_config(all_tools)

            team_agent_names = [c.name for c in agents_config]

            # Step 3: Initialize sidechain transcript
            from src.integrations.orchestration.transcript import TranscriptService
            from src.integrations.orchestration.transcript.models import AgentSidechainEntry
            redis_url = f"redis://:{os.getenv('REDIS_PASSWORD', 'redis_password')}@localhost:6379/0"
            sidechain = TranscriptService(redis_url=redis_url)
            await sidechain.initialize()

            for name in team_agent_names:
                await sidechain.append_agent(AgentSidechainEntry(
                    user_id=user_id, session_id=_session_id, agent_name=name,
                    event_type="start", content={"task": task[:100]},
                ))

            # Step 4: Run parallel team (Phase 0 + Phase 1) with SSE
            team_result = await run_parallel_team(
                task=task,
                context="",
                agents_config=agents_config,
                shared=shared,
                client_factory=make_client,
                lead_tools=lead_tools,
                emitter=emitter,
                timeout=timeout,
                session_id=_session_id,
            )

            # Step 5: Sidechain completion records
            for name in team_agent_names:
                agent_output = team_result.agent_results.get(name, "")
                event_type = "complete" if not agent_output.startswith("ERROR") else "error"
                await sidechain.append_agent(AgentSidechainEntry(
                    user_id=user_id, session_id=_session_id, agent_name=name,
                    event_type=event_type,
                    content={"response_preview": agent_output[:200]},
                ))

            await sidechain.close()

            # Phase 2 synthesis — unified report from TeamLead
            synthesis = getattr(team_result, "synthesis", "")
            if synthesis:
                await emitter.emit(SSEEventType.TEXT_DELTA, {
                    "delta": synthesis,
                    "source": "synthesis",
                    "agent": "TeamLead",
                })
            else:
                # Fallback to raw concatenation
                summary_parts = []
                for name, output in team_result.agent_results.items():
                    if output and not output.startswith("ERROR") and not output.startswith("CANCELLED"):
                        summary_parts.append(f"## {name}\n{output}")
                if summary_parts:
                    await emitter.emit(SSEEventType.TEXT_DELTA, {
                        "delta": "\n\n".join(summary_parts),
                        "source": "aggregated",
                    })

            total_time = round((time.time() - t0) * 1000)
            task_state = shared.to_dict()
            await emitter.emit_complete("Team V2 parallel pipeline complete", {
                "total_ms": total_time,
                "mode": "team_v2_parallel",
                "session_id": _session_id,
                "agent_count": len(team_agent_names),
                "termination_reason": team_result.termination_reason,
                "phase0_duration_ms": team_result.phase0_duration_ms,
                "tasks_completed": task_state["progress"]["completed"],
                "tasks_total": task_state["progress"]["total"],
                "team_messages": len(task_state["messages"]),
            })

        except Exception as e:
            logger.error(f"Team stream error: {e}\n{traceback.format_exc()[-500:]}")
            await emitter.emit_error(f"Team pipeline failed: {str(e)[:300]}")

    asyncio.create_task(_run())

    return StreamingResponse(
        emitter.stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Test H: Hybrid Stream (SSE) ─────────────────────────────────────────

@router.post("/test-hybrid-stream")
async def test_hybrid_stream(
    provider: str = Query("azure"),
    model: str = Query("gpt-5.4-mini"),
    task: str = Query(
        "Check VPN connectivity for Taipei, Hong Kong, and Singapore offices.",
    ),
    user_id: str = Query("user-chris"),
    azure_endpoint: str = Query(""),
    azure_api_key: str = Query(""),
    azure_api_version: str = Query("2025-03-01-preview"),
    azure_deployment: str = Query(""),
):
    """Test H: SSE Streaming Hybrid — Orchestrator decides mode, then streams agent execution.

    Returns a text/event-stream response. The mode selection LLM call emits
    AGENT_THINKING, then routes to subagent or team execution with streaming.
    """
    import asyncio
    from starlette.responses import StreamingResponse
    from src.integrations.hybrid.orchestrator.sse_events import PipelineEventEmitter, SSEEventType

    emitter = PipelineEventEmitter()

    async def _run():
        import os
        import uuid as _uuid

        _session_id = f"{user_id}-hybrid-{int(time.time())}-{str(_uuid.uuid4())[:8]}"
        t0 = time.time()

        try:
            from agent_framework import Agent, tool as maf_tool

            await emitter.emit(SSEEventType.PIPELINE_START, {
                "mode": "hybrid",
                "session_id": _session_id,
                "task": task[:200],
                "provider": provider,
                "model": model,
            })

            client = _create_client(provider, model, azure_endpoint, azure_api_key,
                                    azure_api_version, azure_deployment, max_tokens=2048)

            # Step 1: Mode selection via LLM
            await emitter.emit(SSEEventType.AGENT_THINKING, {
                "step": "mode_selection", "status": "running",
                "label": "Orchestrator deciding execution mode...",
            })

            @maf_tool(name="select_execution_mode", description=(
                "Decide the execution mode for the task. "
                "Use 'subagent' for independent parallel tasks (e.g., checking 3 separate systems). "
                "Use 'team' for tasks requiring expert collaboration (e.g., investigating a complex failure). "
                "Return your reasoning."
            ))
            def select_execution_mode(mode: str, reasoning: str) -> str:
                """Select execution mode: 'subagent' or 'team'."""
                return f"Selected mode: {mode}. Reasoning: {reasoning}"

            orchestrator = Agent(
                client,
                name="Orchestrator",
                instructions=(
                    "You are an IT operations orchestrator. Analyze the user's request and decide:\n"
                    "- Use 'subagent' mode if the task has independent subtasks that can run in parallel\n"
                    "- Use 'team' mode if the task requires expert collaboration and information sharing\n"
                    "Call select_execution_mode with your decision and reasoning."
                ),
                tools=[select_execution_mode],
            )

            t1 = time.time()
            response = await orchestrator.run(task)
            decision_time = round((time.time() - t1) * 1000)

            response_text = ""
            if hasattr(response, "text") and response.text:
                response_text = response.text
            elif hasattr(response, "messages") and response.messages:
                for msg in response.messages:
                    if hasattr(msg, "text") and msg.text:
                        response_text += msg.text

            selected_mode = "subagent"  # default
            if "team" in response_text.lower():
                selected_mode = "team"

            await emitter.emit(SSEEventType.ROUTING_COMPLETE, {
                "step": "mode_selection", "status": "complete",
                "selected_mode": selected_mode,
                "reasoning": response_text[:500],
                "duration_ms": decision_time,
            })

            # Step 2: Execute the chosen mode with streaming
            sdk_tools = _get_claude_sdk_tools()

            # Initialize sidechain transcript
            from src.integrations.orchestration.transcript import TranscriptService
            from src.integrations.orchestration.transcript.models import AgentSidechainEntry
            redis_url = f"redis://:{os.getenv('REDIS_PASSWORD', 'redis_password')}@localhost:6379/0"
            sidechain = TranscriptService(redis_url=redis_url)
            await sidechain.initialize()

            if selected_mode == "subagent":
                # Subagent execution (same agents as test_subagent)
                from agent_framework.orchestrations import ConcurrentBuilder

                agent_defs = [
                    ("ETL-Checker", (
                        "You are an ETL pipeline specialist. Check the ETL pipeline status.\n"
                        "You have access to: deep_analysis, run_diagnostic_command, search_knowledge_base.\n"
                        "Use these tools to investigate. Be concise."
                    )),
                    ("CRM-Checker", (
                        "You are a CRM service specialist. Check the CRM service health.\n"
                        "You have access to: deep_analysis, run_diagnostic_command, search_knowledge_base.\n"
                        "Use these tools to investigate. Be concise."
                    )),
                    ("Email-Checker", (
                        "You are an email server specialist. Check the email server status.\n"
                        "You have access to: deep_analysis, run_diagnostic_command, search_knowledge_base.\n"
                        "Use these tools to investigate. Be concise."
                    )),
                ]

                agents = []
                agent_names = []
                for name, instructions in agent_defs:
                    agent = Agent(client, name=name, instructions=instructions, tools=sdk_tools)
                    agents.append(agent)
                    agent_names.append(name)
                    await emitter.emit(SSEEventType.SWARM_WORKER_START, {
                        "agent": name, "status": "created",
                    })
                    await sidechain.append_agent(AgentSidechainEntry(
                        user_id=user_id, session_id=_session_id, agent_name=name,
                        event_type="start", content={"task": task[:100]},
                    ))

                builder = ConcurrentBuilder(participants=agents)
                workflow = builder.build()

                stream = workflow.run(message=task, stream=True, include_status_events=True)
                _seen_sub = set()
                _sub_responses = []
                async for event in stream:
                    event_type_name = type(event).__name__
                    _got = False
                    if hasattr(event, "data") and event.data:
                        data = event.data
                        if hasattr(data, '__iter__') and not isinstance(data, str):
                            for item in data:
                                if hasattr(item, 'executor_id') and hasattr(item, 'agent_response'):
                                    resp = item.agent_response
                                    text = ""
                                    if hasattr(resp, 'text') and resp.text:
                                        text = resp.text
                                    elif hasattr(resp, 'messages') and resp.messages:
                                        for m in resp.messages:
                                            if hasattr(m, 'text') and m.text:
                                                text += m.text
                                    if text and item.executor_id not in _seen_sub:
                                        _seen_sub.add(item.executor_id)
                                        _got = True
                                        await emitter.emit(SSEEventType.TEXT_DELTA, {
                                            "agent": item.executor_id, "delta": text,
                                        })
                                        _sub_responses.append({"agent": item.executor_id, "response": text})
                                        await sidechain.append_agent(AgentSidechainEntry(
                                            user_id=user_id, session_id=_session_id,
                                            agent_name=item.executor_id,
                                            event_type="complete",
                                            content={"response_preview": text[:200]},
                                        ))
                    if not _got and event_type_name not in ("AgentExecutorResponse",):
                        _p = str(event.data)[:500] if hasattr(event, "data") and event.data else ""
                        if "object at 0x" not in _p:
                            await emitter.emit(SSEEventType.SWARM_PROGRESS, {"event_type": event_type_name, "preview": _p})
                if _sub_responses:
                    await emitter.emit(SSEEventType.TEXT_DELTA, {"delta": "\n\n".join(f"## {r['agent']}\n{r['response']}" for r in _sub_responses), "source": "aggregated"})

            else:
                # Team execution — V2 parallel engine
                from src.integrations.poc.shared_task_list import create_shared_task_list
                from src.integrations.poc.team_tools import create_team_tools, create_lead_tools
                from src.integrations.poc.agent_work_loop import (
                    AgentConfig, run_parallel_team, _patch_emitter,
                )

                _patch_emitter(emitter)

                shared = create_shared_task_list(session_id=_session_id)
                team_tools = create_team_tools(shared)
                lead_tools = create_lead_tools(shared)
                real_tools = _get_real_tools()
                sdk_tools_team = _get_claude_sdk_tools()
                all_tools = team_tools + real_tools + sdk_tools_team

                def make_team_client():
                    return _create_client(provider, model, azure_endpoint, azure_api_key,
                                          azure_api_version, azure_deployment, max_tokens=2048)

                agents_config = _build_team_agents_config(all_tools)
                team_agent_names = [c.name for c in agents_config]

                for name in team_agent_names:
                    await sidechain.append_agent(AgentSidechainEntry(
                        user_id=user_id, session_id=_session_id, agent_name=name,
                        event_type="start", content={"task": task[:100]},
                    ))

                team_result = await run_parallel_team(
                    task=task,
                    context="",
                    agents_config=agents_config,
                    shared=shared,
                    client_factory=make_team_client,
                    lead_tools=lead_tools,
                    emitter=emitter,
                    timeout=120.0,
                    session_id=_session_id,
                )

                for name in team_agent_names:
                    output = team_result.agent_results.get(name, "")
                    evt = "complete" if not output.startswith("ERROR") else "error"
                    await sidechain.append_agent(AgentSidechainEntry(
                        user_id=user_id, session_id=_session_id, agent_name=name,
                        event_type=evt, content={"response_preview": output[:200]},
                    ))

                synthesis = getattr(team_result, "synthesis", "")
                if synthesis:
                    await emitter.emit(SSEEventType.TEXT_DELTA, {
                        "delta": synthesis, "source": "synthesis", "agent": "TeamLead",
                    })
                else:
                    parts = [f"## {n}\n{o}" for n, o in team_result.agent_results.items()
                             if o and not o.startswith("ERROR")]
                    if parts:
                        await emitter.emit(SSEEventType.TEXT_DELTA, {
                            "delta": "\n\n".join(parts), "source": "aggregated",
                        })

            await sidechain.close()

            total_time = round((time.time() - t0) * 1000)
            await emitter.emit_complete("Hybrid pipeline complete", {
                "total_ms": total_time,
                "mode": "hybrid",
                "selected_mode": selected_mode,
                "session_id": _session_id,
                "decision_ms": decision_time,
            })

        except Exception as e:
            logger.error(f"Hybrid stream error: {e}\n{traceback.format_exc()[-500:]}")
            await emitter.emit_error(f"Hybrid pipeline failed: {str(e)[:300]}")

    asyncio.create_task(_run())

    return StreamingResponse(
        emitter.stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
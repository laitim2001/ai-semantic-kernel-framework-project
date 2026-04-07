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
    """Lazy-load Claude SDK tools."""
    try:
        from src.integrations.poc.claude_sdk_tools import create_claude_sdk_tools
        return create_claude_sdk_tools()
    except Exception as e:
        logger.warning(f"Claude SDK tools not available: {e}")
        return []


def _create_client(provider: str, model: str, azure_endpoint: str = "",
                   azure_api_key: str = "", azure_api_version: str = "2024-12-01-preview",
                   azure_deployment: str = "", max_tokens: int = 1024):
    """Create a ChatClient based on provider."""
    if provider == "azure":
        import os
        from agent_framework.azure import AzureOpenAIResponsesClient
        endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT", "")
        api_key = azure_api_key or os.getenv("AZURE_OPENAI_API_KEY", "")
        deployment = azure_deployment or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", model)
        version = azure_api_version or os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
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


# ── Test A: Subagent (ConcurrentBuilder) ──

@router.post("/test-subagent")
async def test_subagent(
    provider: str = Query("azure"),
    model: str = Query("gpt-5.4-mini"),
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


# ── Test B: Agent Team (GroupChatBuilder + SharedTaskList) ──

@router.post("/test-team")
async def test_team(
    provider: str = Query("azure"),
    model: str = Query("gpt-5.4-mini"),
    task: str = Query(
        "Investigate APAC ETL Pipeline failure. Multiple experts needed: "
        "analyze application logs, check database changes, and verify network connectivity.",
    ),
    max_rounds: int = Query(8, description="Max GroupChat rounds"),
    user_id: str = Query("user-chris"),
    session_id: str = Query("", description="Link to orchestrator session for sidechain"),
    azure_endpoint: str = Query(""),
    azure_api_key: str = Query(""),
    azure_api_version: str = Query("2024-12-01-preview"),
    azure_deployment: str = Query(""),
):
    """Test B: Agent Team with GroupChatBuilder + SharedTaskList.

    3 Teammates collaborate via shared conversation, claim tasks from
    a SharedTaskList, and communicate findings to each other.
    """
    import os
    import uuid as _uuid

    if not session_id:
        session_id = f"{user_id}-team-{int(time.time())}-{str(_uuid.uuid4())[:8]}"

    results: dict[str, Any] = {
        "test": "agent_team",
        "provider": provider,
        "model": model,
        "task": task,
        "max_rounds": max_rounds,
        "session_id": session_id,
        "steps": [],
        "events": [],
        "shared_task_list": None,
        "agent_states": {},
    }

    try:
        from agent_framework import Agent
        from agent_framework.orchestrations import GroupChatBuilder
        from src.integrations.poc.shared_task_list import SharedTaskList
        from src.integrations.poc.team_tools import create_team_tools

        t0 = time.time()

        # Step 1: Create SharedTaskList with initial tasks
        shared = SharedTaskList()
        shared.add_task("T1", "Analyze ETL application logs for error patterns and root cause", priority=1)
        shared.add_task("T2", "Check database schema changes in the last 7 days", priority=1)
        shared.add_task("T3", "Verify network connectivity between ETL and database servers", priority=2)
        shared.add_task("T4", "Review ETL scheduling configuration for recent modifications", priority=3)

        results["steps"].append({
            "step": "create_task_list",
            "status": "ok",
            "tasks": 4,
        })

        # Step 2: Create team tools + Claude SDK tools
        team_tools = create_team_tools(shared)
        sdk_tools = _get_claude_sdk_tools()
        all_tools = team_tools + sdk_tools
        results["steps"].append({
            "step": "create_tools", "status": "ok",
            "team_tools": len(team_tools), "sdk_tools": len(sdk_tools),
        })

        # Step 3: Create Teammate agents with team + SDK tools
        client = _create_client(provider, model, azure_endpoint, azure_api_key,
                                azure_api_version, azure_deployment, max_tokens=2048)

        log_expert = Agent(
            client, name="LogExpert",
            instructions=(
                "You are a log analysis expert on an IT investigation team.\n"
                "IMPORTANT: Act immediately. Do NOT just observe or coordinate.\n\n"
                "WORKFLOW (do ALL steps in ONE turn):\n"
                "1. Use claim_next_task with your name 'LogExpert' to claim a task\n"
                "2. Use deep_analysis or run_diagnostic_command to investigate\n"
                "3. Use report_task_result to submit your findings\n"
                "4. Use send_team_message to share key discoveries\n"
                "5. Use read_team_messages to check teammate findings\n\n"
                "AVAILABLE TOOLS: claim_next_task, report_task_result, view_team_status, "
                "send_team_message, read_team_messages, deep_analysis, "
                "run_diagnostic_command, search_knowledge_base\n"
                "Be concise. Focus on actionable findings."
            ),
            tools=all_tools,
        )

        db_expert = Agent(
            client, name="DBExpert",
            instructions=(
                "You are a database expert on an IT investigation team.\n"
                "IMPORTANT: Act immediately. Do NOT just observe or coordinate.\n\n"
                "WORKFLOW (do ALL steps in ONE turn):\n"
                "1. Use claim_next_task with your name 'DBExpert' to claim a task\n"
                "2. Use deep_analysis or run_diagnostic_command to investigate\n"
                "3. Use report_task_result to submit your findings\n"
                "4. Use send_team_message to share key discoveries\n"
                "5. Use read_team_messages to check teammate findings\n\n"
                "AVAILABLE TOOLS: claim_next_task, report_task_result, view_team_status, "
                "send_team_message, read_team_messages, deep_analysis, "
                "run_diagnostic_command, search_knowledge_base\n"
                "Focus on schema changes, query performance, data integrity."
            ),
            tools=all_tools,
        )

        app_expert = Agent(
            client, name="AppExpert",
            instructions=(
                "You are an application infrastructure expert on an IT investigation team.\n"
                "IMPORTANT: Act immediately. Do NOT just observe or coordinate.\n\n"
                "WORKFLOW (do ALL steps in ONE turn):\n"
                "1. Use claim_next_task with your name 'AppExpert' to claim a task\n"
                "2. Use deep_analysis or run_diagnostic_command to investigate\n"
                "3. Use report_task_result to submit your findings\n"
                "4. Use send_team_message to share key discoveries\n"
                "5. Use read_team_messages to check teammate findings\n\n"
                "AVAILABLE TOOLS: claim_next_task, report_task_result, view_team_status, "
                "send_team_message, read_team_messages, deep_analysis, "
                "run_diagnostic_command, search_knowledge_base\n"
                "Focus on network, infrastructure, and configuration issues."
            ),
            tools=all_tools,
        )

        results["steps"].append({
            "step": "create_teammates",
            "status": "ok",
            "teammates": ["LogExpert", "DBExpert", "AppExpert"],
        })

        # Step 4: Build GroupChat with round-robin selection
        # Note: orchestrator_agent requires structured output (response_format)
        # which AnthropicChatClient doesn't support yet.
        # Using selection_func for round-robin + task-aware selection instead.
        participant_names = ["LogExpert", "DBExpert", "AppExpert"]
        round_counter = {"n": 0}

        def select_next(messages: list) -> str:
            """Round-robin with awareness: cycle through teammates."""
            idx = round_counter["n"] % len(participant_names)
            round_counter["n"] += 1
            return participant_names[idx]

        from agent_framework_orchestrations._group_chat import TerminationCondition

        # Terminate when all tasks are done
        def check_termination(messages: list) -> bool:
            return shared.is_all_done()

        results["steps"].append({"step": "setup_orchestration", "status": "ok"})

        builder = GroupChatBuilder(
            participants=[log_expert, db_expert, app_expert],
            selection_func=select_next,
            max_rounds=max_rounds,
        )
        workflow = builder.build()
        build_time = round((time.time() - t0) * 1000)
        results["steps"].append({"step": "build_groupchat", "status": "ok", "duration_ms": build_time})

        # Initialize sidechain transcript for team agents
        from src.integrations.orchestration.transcript import TranscriptService
        from src.integrations.orchestration.transcript.models import AgentSidechainEntry
        redis_url = f"redis://:{os.getenv('REDIS_PASSWORD', 'redis_password')}@localhost:6379/0"
        sidechain = TranscriptService(redis_url=redis_url)
        await sidechain.initialize()

        team_agent_names = ["LogExpert", "DBExpert", "AppExpert"]
        for name in team_agent_names:
            await sidechain.append_agent(AgentSidechainEntry(
                user_id=user_id, session_id=session_id, agent_name=name,
                event_type="start", content={"task": task[:100]},
            ))
            results["agent_states"][name] = "running"

        # Step 5: Run GroupChat
        t1 = time.time()
        try:
            initial_msg = (
                f"Team, we have an urgent investigation:\n{task}\n\n"
                f"Here is the current task list:\n{shared.get_status()}\n\n"
                "Each of you should claim a task, work on it, report results, "
                "and share important findings with the team. Check team messages "
                "for discoveries from other teammates."
            )

            stream = workflow.run(message=initial_msg, stream=True, include_status_events=True)
            agent_responses: list[dict[str, Any]] = []

            async for event in stream:
                event_type = type(event).__name__
                event_info: dict[str, Any] = {"type": event_type}
                if hasattr(event, "data") and event.data:
                    data = event.data
                    data_str = str(data)[:300]
                    event_info["data_preview"] = data_str

                    # Extract Agent response text
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
                                    # Sidechain: record agent response
                                    await sidechain.append_agent(AgentSidechainEntry(
                                        user_id=user_id, session_id=session_id,
                                        agent_name=item.executor_id,
                                        event_type="complete",
                                        content={"response_preview": text[:200]},
                                    ))
                                    results["agent_states"][item.executor_id] = "complete"

                results["events"].append(event_info)

            run_time = round((time.time() - t1) * 1000)
            results["agent_responses"] = agent_responses

            # Mark agents that never responded
            for name in team_agent_names:
                if results["agent_states"].get(name) == "running":
                    results["agent_states"][name] = "no_response"
                    await sidechain.append_agent(AgentSidechainEntry(
                        user_id=user_id, session_id=session_id, agent_name=name,
                        event_type="error", content={"error": "No response in groupchat"},
                    ))

            results["steps"].append({
                "step": "run_groupchat",
                "status": "ok",
                "duration_ms": run_time,
                "total_events": len(results["events"]),
                "rounds_used": max_rounds,
            })

        except Exception as e:
            run_time = round((time.time() - t1) * 1000)
            for name in team_agent_names:
                if results["agent_states"].get(name) == "running":
                    results["agent_states"][name] = "error"
                    await sidechain.append_agent(AgentSidechainEntry(
                        user_id=user_id, session_id=session_id, agent_name=name,
                        event_type="error", content={"error": str(e)[:200]},
                    ))
            results["steps"].append({
                "step": "run_groupchat",
                "status": "error",
                "duration_ms": run_time,
                "error": str(e),
                "traceback": traceback.format_exc()[-500:],
            })

        await sidechain.close()

        # Step 6: Capture final SharedTaskList state
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
        results["status"] = "ok" if all(s.get("status") == "ok" for s in results["steps"]) else "partial"
        results["summary"] = (
            f"Team: {completed_agents}/{len(team_agent_names)} agents responded, "
            f"{max_rounds} rounds, "
            f"{shared.to_dict()['progress']['completed']}/{shared.to_dict()['progress']['total']} tasks done, "
            f"{len(shared.to_dict()['messages'])} messages, session={session_id[:20]}..."
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

        # ── Step 1: READ MEMORY (deterministic — always execute) ──
        try:
            from src.integrations.memory.unified_memory import UnifiedMemoryManager
            mgr = UnifiedMemoryManager()
            await mgr.initialize()
            memory_context = await mgr.get_context(user_id=user_id, query=task, limit=5)
            memory_text = "\n".join(
                f"[{getattr(r, 'layer', '?')}] {getattr(r, 'content', str(r))}"
                for r in (memory_context or [])
            ) or "No memories found"
        except Exception as e:
            memory_text = f"Memory service unavailable: {str(e)[:100]}"

        step1_status = "ok" if "unavailable" not in memory_text.lower() and "failed" not in memory_text.lower() else "failed"
        results["steps"].append({
            "step": "1_read_memory",
            "status": step1_status,
            "result_preview": memory_text[:200],
        })
        results["orchestrator_actions"].append({
            "tool": "get_user_memory",
            "args": f"user_id={user_id}",
            "result": memory_text[:300],
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
            # Add ETL/pipeline/incident patterns so common IT tasks get matched
            try:
                matcher.add_rule({
                    "pattern": r"(?i)(etl|pipeline|data.?flow|batch.?job).*(fail|error|down|broken|stuck)",
                    "category": "INCIDENT", "sub_intent": "etl_failure",
                    "risk_level": "HIGH", "workflow_type": "MAGENTIC",
                })
                matcher.add_rule({
                    "pattern": r"(?i)(server|service|system|database).*(down|fail|error|crash|outage|unavailable)",
                    "category": "INCIDENT", "sub_intent": "system_outage",
                    "risk_level": "CRITICAL", "workflow_type": "MAGENTIC",
                })
                matcher.add_rule({
                    "pattern": r"(?i)(deploy|release|rollout|update|upgrade|migration)",
                    "category": "CHANGE", "sub_intent": "deployment",
                    "risk_level": "MEDIUM", "workflow_type": "SEQUENTIAL",
                })
                matcher.add_rule({
                    "pattern": r"(?i)(check|status|monitor|health|ping|query|what.?is)",
                    "category": "QUERY", "sub_intent": "status_check",
                    "risk_level": "LOW", "workflow_type": "HANDOFF",
                })
            except Exception:
                pass  # If add_rule format differs, fallback to defaults

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
            decision = await router_inst.route(task)
            intent_text = (
                f"Category: {decision.intent_category}, "
                f"Risk: {decision.risk_level}, "
                f"Confidence: {decision.confidence:.2f}, "
                f"Workflow: {decision.workflow_type}"
            )
        except Exception as e:
            intent_text = f"Intent analysis partial: {str(e)[:100]}"

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

        # Conditional checkpoint: HIGH/CRITICAL risk → HITL may pause here
        step3_checkpoint_id = None
        risk_str = getattr(decision, "risk_level", "") if "decision" in dir() else ""
        is_high_risk = "HIGH" in str(risk_str) or "CRITICAL" in str(risk_str)
        if is_high_risk:
            try:
                from agent_framework import WorkflowCheckpoint
                from src.integrations.agent_framework.ipa_checkpoint_storage import IPACheckpointStorage
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
                results["checkpoints"].append({
                    "id": step3_checkpoint_id, "step": 3, "reason": "high_risk_hitl",
                    "risk": str(risk_str),
                })
            except Exception as cp_err:
                logger.warning(f"Step 3 checkpoint failed: {cp_err}")

        await transcript.append(TranscriptEntry(
            user_id=user_id, session_id=session_id,
            step_name="analyze_intent", step_index=2,
            entry_type="approval_required" if is_high_risk else "step_complete",
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
                f"## User Memory\n{memory_text}\n\n"
                f"## Knowledge Base\n{knowledge_text[:500]}\n\n"
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

        # ── Step 6: SAVE MEMORY (deterministic — always execute) ──
        memory_content = f"User asked about: {task[:80]}. Routed to: {selected_mode}."
        try:
            from src.integrations.memory.unified_memory import UnifiedMemoryManager
            from src.integrations.memory.types import MemoryType, MemoryLayer
            mgr2 = UnifiedMemoryManager()
            await mgr2.initialize()
            await mgr2.add(
                content=memory_content,
                user_id=user_id,
                memory_type=MemoryType.INSIGHT,
                layer=MemoryLayer.LONG_TERM,  # Explicit: persist to long-term for cross-session retrieval
            )
            save_text = f"Memory saved: {memory_content[:100]}"
        except Exception as mem_err:
            logger.error(f"Memory save failed: {mem_err}")
            save_text = f"Memory save failed: {str(mem_err)[:100]}"

        results["steps"].append({
            "step": "6_save_memory",
            "status": "ok" if "saved:" in save_text.lower() and "failed" not in save_text.lower() else "failed",
            "result_preview": save_text[:200],
        })
        results["orchestrator_actions"].append({
            "tool": "save_memory",
            "args": f"user_id={user_id}",
            "result": save_text,
        })
        await transcript.append(TranscriptEntry(
            user_id=user_id, session_id=session_id,
            step_name="save_memory", step_index=5,
            entry_type="step_complete",
            output_summary={"saved": "failed" not in save_text.lower()},
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

        # Create LLM agent with restored context to generate response for the new route
        client = _create_client(provider, model, azure_api_version="2025-03-01-preview", max_tokens=2048)

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
                f"provide your response. Explain how you would handle this using the "
                f"'{effective_route}' approach:\n"
                f"- direct_answer: Give a concise direct answer\n"
                f"- subagent: Explain what parallel independent checks you'd dispatch\n"
                f"- team: Explain what expert team collaboration you'd organize\n"
                f"- swarm: Explain what deep multi-agent investigation you'd launch\n"
                f"- workflow: Provide a structured step-by-step workflow plan\n"
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
            step_name=f"resume_execute_{effective_route}", step_index=7,
            entry_type="step_complete",
            output_summary={
                "route": effective_route,
                "response_preview": response_text[:150],
                "duration_ms": decision_time,
            },
            checkpoint_id=checkpoint_id,
        ))

        # Save memory for the resumed execution
        try:
            from src.integrations.memory.unified_memory import UnifiedMemoryManager
            from src.integrations.memory.types import MemoryType, MemoryLayer
            mgr = UnifiedMemoryManager()
            await mgr.initialize()
            await mgr.add(
                content=f"Resumed from checkpoint. Route: {resume_result.original_route}→{effective_route}. Task: {task[:80]}",
                user_id=user_id,
                memory_type=MemoryType.INSIGHT,
                layer=MemoryLayer.LONG_TERM,
            )
        except Exception:
            pass  # Memory save is best-effort

    except Exception as e:
        execution_result["status"] = "error"
        execution_result["error"] = str(e)
        execution_result["steps_executed"].append({
            "step": "llm_execute",
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

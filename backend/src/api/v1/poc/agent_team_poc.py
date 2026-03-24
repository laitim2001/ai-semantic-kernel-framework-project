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
                   azure_api_key: str = "", azure_api_version: str = "2025-03-01-preview",
                   azure_deployment: str = "", max_tokens: int = 1024):
    """Create a ChatClient based on provider."""
    if provider == "azure":
        from agent_framework.azure import AzureOpenAIResponsesClient
        return AzureOpenAIResponsesClient(
            endpoint=azure_endpoint,
            api_key=azure_api_key,
            deployment_name=azure_deployment or model,
            api_version=azure_api_version,
        )
    else:
        from src.integrations.agent_framework.clients.anthropic_chat_client import (
            AnthropicChatClient,
        )
        return AnthropicChatClient(model=model, max_tokens=max_tokens)


# ── Test A: Subagent (ConcurrentBuilder) ──

@router.post("/test-subagent")
async def test_subagent(
    provider: str = Query("anthropic"),
    model: str = Query("claude-haiku-4-5-20251001"),
    task: str = Query(
        "Check the status of three systems: "
        "1) APAC ETL Pipeline, 2) CRM Service, 3) Email Server. "
        "Report the health status of each.",
    ),
    azure_endpoint: str = Query(""),
    azure_api_key: str = Query(""),
    azure_api_version: str = Query("2025-03-01-preview"),
    azure_deployment: str = Query(""),
):
    """Test A: Subagent mode with ConcurrentBuilder.

    3 Agents run in parallel, each checking one system independently.
    Results are aggregated by a custom aggregator function.
    """
    results: dict[str, Any] = {
        "test": "subagent",
        "provider": provider,
        "model": model,
        "task": task,
        "steps": [],
        "events": [],
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

                results["events"].append(event_info)

            run_time = round((time.time() - t1) * 1000)
            results["steps"].append({
                "step": "run_concurrent",
                "status": "ok",
                "duration_ms": run_time,
                "total_events": len(results["events"]),
            })

            results["agent_responses"] = agent_responses
            results["steps"].append({
                "step": "collect_results",
                "status": "ok",
                "agent_results_count": len(agent_responses),
            })

        except Exception as e:
            run_time = round((time.time() - t1) * 1000)
            results["steps"].append({
                "step": "run_concurrent",
                "status": "error",
                "duration_ms": run_time,
                "error": str(e),
                "traceback": traceback.format_exc()[-500:],
            })

        results["status"] = "ok" if all(s.get("status") == "ok" for s in results["steps"]) else "partial"
        results["summary"] = f"Subagent: 3 agents parallel, {len(results['events'])} events"

    except Exception as e:
        results["status"] = "error"
        results["error"] = str(e)
        results["traceback"] = traceback.format_exc()[-500:]

    return results


# ── Test B: Agent Team (GroupChatBuilder + SharedTaskList) ──

@router.post("/test-team")
async def test_team(
    provider: str = Query("anthropic"),
    model: str = Query("claude-haiku-4-5-20251001"),
    task: str = Query(
        "Investigate APAC ETL Pipeline failure. Multiple experts needed: "
        "analyze application logs, check database changes, and verify network connectivity.",
    ),
    max_rounds: int = Query(8, description="Max GroupChat rounds"),
    azure_endpoint: str = Query(""),
    azure_api_key: str = Query(""),
    azure_api_version: str = Query("2025-03-01-preview"),
    azure_deployment: str = Query(""),
):
    """Test B: Agent Team with GroupChatBuilder + SharedTaskList.

    3 Teammates collaborate via shared conversation, claim tasks from
    a SharedTaskList, and communicate findings to each other.
    """
    results: dict[str, Any] = {
        "test": "agent_team",
        "provider": provider,
        "model": model,
        "task": task,
        "max_rounds": max_rounds,
        "steps": [],
        "events": [],
        "shared_task_list": None,
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
                                azure_api_version, azure_deployment)

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

                results["events"].append(event_info)

            run_time = round((time.time() - t1) * 1000)
            results["agent_responses"] = agent_responses
            results["steps"].append({
                "step": "run_groupchat",
                "status": "ok",
                "duration_ms": run_time,
                "total_events": len(results["events"]),
                "rounds_used": max_rounds,
            })

        except Exception as e:
            run_time = round((time.time() - t1) * 1000)
            results["steps"].append({
                "step": "run_groupchat",
                "status": "error",
                "duration_ms": run_time,
                "error": str(e),
                "traceback": traceback.format_exc()[-500:],
            })

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

        results["status"] = "ok" if all(s.get("status") == "ok" for s in results["steps"]) else "partial"
        results["summary"] = (
            f"Team: 3 agents, {max_rounds} rounds, "
            f"{shared.to_dict()['progress']['completed']}/{shared.to_dict()['progress']['total']} tasks done, "
            f"{len(shared.to_dict()['messages'])} messages"
        )

    except Exception as e:
        results["status"] = "error"
        results["error"] = str(e)
        results["traceback"] = traceback.format_exc()[-500:]

    return results


# ── Test C: Hybrid (Orchestrator decides mode) ──

@router.post("/test-hybrid")
async def test_hybrid(
    provider: str = Query("anthropic"),
    model: str = Query("claude-haiku-4-5-20251001"),
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

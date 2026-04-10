"""Team Tools — MAF FunctionTool definitions for Agent Team collaboration.

These tools are given to Teammate Agents so they can interact with
the SharedTaskList and communicate with each other.

V2: Added directed messaging (to_agent), check_my_inbox,
    and decompose_and_assign_tasks (for TeamLead Phase 0).

Usage:
    shared = SharedTaskList()
    tools = create_team_tools(shared)          # worker tools
    lead_tools = create_lead_tools(shared)     # lead-only tools
    agent = Agent(client, name="Expert", tools=tools)

PoC: Agent Team — poc/agent-team branch.
"""

import json
import logging
from uuid import uuid4

from agent_framework import tool

from src.integrations.poc.shared_task_list import SharedTaskList

logger = logging.getLogger(__name__)


def create_team_tools(shared: SharedTaskList) -> list:
    """Create MAF FunctionTool instances bound to a SharedTaskList.

    Returns a list of tools that can be passed to Agent(tools=[...]).
    Each tool closure captures the shared instance.
    """

    @tool(name="claim_next_task", description=(
        "Claim the next highest-priority pending task from the shared task list. "
        "Returns the task details if one is available, or a message if all tasks are taken."
    ))
    def claim_next_task(agent_name: str) -> str:
        """Claim the next available task. Pass your own agent name."""
        task = shared.claim_task(agent_name)
        if task:
            return (
                f"Claimed task {task.task_id}: {task.description} "
                f"(priority: {task.priority})"
            )
        return "No pending tasks available. All tasks have been claimed or completed."

    @tool(name="report_task_result", description=(
        "Report the result of a completed task. "
        "Include the task_id and your analysis/findings as the result."
    ))
    def report_task_result(task_id: str, result: str) -> str:
        """Report completion of a task with your findings."""
        success = shared.complete_task(task_id, result)
        if success:
            return f"Task {task_id} marked as completed. Result recorded."
        return f"Task {task_id} not found."

    @tool(name="view_team_status", description=(
        "View the current status of all tasks and which teammate is working on what. "
        "Use this to check progress and find unclaimed tasks."
    ))
    def view_team_status() -> str:
        """View all task statuses and team progress."""
        return shared.get_status()

    @tool(name="send_team_message", description=(
        "Send a message to the team or a specific teammate. "
        "If to_agent is provided, only that agent will see it in their inbox. "
        "If to_agent is empty, all teammates can see the message. "
        "Use this to share findings, request specific help, or coordinate."
    ))
    def send_team_message(from_agent: str, message: str, to_agent: str = "") -> str:
        """Send a message. Set to_agent for directed, leave empty for broadcast."""
        target = to_agent if to_agent else None
        shared.add_message(from_agent, message, to_agent=target)
        if target:
            return f"Directed message sent to {target}: {message[:100]}"
        return f"Broadcast message sent to team: {message[:100]}"

    @tool(name="read_team_messages", description=(
        "Read recent broadcast messages from other team members. "
        "Check this to see if teammates have shared important findings."
    ))
    def read_team_messages() -> str:
        """Read the latest team messages."""
        return shared.get_messages()

    @tool(name="check_my_inbox", description=(
        "Check for messages directed specifically to you. "
        "Other agents can send you targeted messages with important findings "
        "or requests. Check this regularly during your work."
    ))
    def check_my_inbox(agent_name: str) -> str:
        """Check messages directed to this agent. Pass your own agent name."""
        result = shared.get_inbox(agent_name, unread_only=True)
        if not result:
            return "No new directed messages for you."
        return result

    return [
        claim_next_task,
        report_task_result,
        view_team_status,
        send_team_message,
        read_team_messages,
        check_my_inbox,
    ]


def create_lead_tools(shared: SharedTaskList) -> list:
    """Create tools for TeamLead Phase 0 — task decomposition only.

    TeamLead analyzes the user's request and breaks it into sub-tasks
    that worker agents will claim and execute in parallel.
    """

    @tool(name="decompose_and_assign_tasks", description=(
        "Break down a complex task into specific sub-tasks for the team. "
        "Provide a JSON array of objects with: description (what to do), "
        "priority (1=highest), and required_expertise (keyword hints). "
        "Example: [{\"description\": \"Check DB connection pool\", "
        "\"priority\": 1, \"required_expertise\": \"database sql\"}]"
    ))
    def decompose_and_assign_tasks(tasks_json: str) -> str:
        """Create sub-tasks from a JSON array. Called by TeamLead only."""
        try:
            tasks = json.loads(tasks_json)
        except json.JSONDecodeError as e:
            return f"Invalid JSON: {e}"

        if not isinstance(tasks, list) or not tasks:
            return "Expected a non-empty JSON array of task objects."

        created = []
        for t in tasks:
            if not isinstance(t, dict) or "description" not in t:
                continue
            task_id = f"T-{uuid4().hex[:6]}"
            item = shared.add_task(
                task_id=task_id,
                description=t["description"],
                priority=t.get("priority", 1),
                required_expertise=t.get("required_expertise", ""),
            )
            created.append(f"{item.task_id}: {item.description[:80]}")

        if not created:
            return "No valid tasks found in input."

        logger.info(f"TeamLead decomposed into {len(created)} tasks")
        return f"Created {len(created)} sub-tasks:\n" + "\n".join(created)

    return [decompose_and_assign_tasks]

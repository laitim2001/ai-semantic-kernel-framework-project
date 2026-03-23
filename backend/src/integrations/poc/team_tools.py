"""Team Tools — MAF FunctionTool definitions for Agent Team collaboration.

These tools are given to Teammate Agents so they can interact with
the SharedTaskList and communicate with each other.

Usage:
    shared = SharedTaskList()
    tools = create_team_tools(shared)
    agent = Agent(client, name="Expert", tools=tools)

PoC: Agent Team — poc/agent-team branch.
"""

from agent_framework import tool

from src.integrations.poc.shared_task_list import SharedTaskList


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
        "Send a message to the team. All teammates can see this message. "
        "Use this to share important findings, ask for help, or coordinate."
    ))
    def send_team_message(from_agent: str, message: str) -> str:
        """Send a message visible to all team members."""
        shared.add_message(from_agent, message)
        return f"Message sent to team: {message}"

    @tool(name="read_team_messages", description=(
        "Read recent messages from other team members. "
        "Check this to see if teammates have shared important findings."
    ))
    def read_team_messages() -> str:
        """Read the latest team messages."""
        return shared.get_messages()

    return [
        claim_next_task,
        report_task_result,
        view_team_status,
        send_team_message,
        read_team_messages,
    ]

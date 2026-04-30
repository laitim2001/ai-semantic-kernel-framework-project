"""
Swarm Integration Layer

This module provides the integration layer between ClaudeCoordinator
and SwarmTracker, enabling real-time tracking of multi-agent coordination.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .models import (
    AgentSwarmStatus,
    SwarmMode,
    SwarmStatus,
    ThinkingContent,
    ToolCallInfo,
    WorkerExecution,
    WorkerStatus,
    WorkerType,
)
from .tracker import SwarmTracker, get_swarm_tracker


logger = logging.getLogger(__name__)


class SwarmIntegration:
    """
    Integration layer connecting ClaudeCoordinator to SwarmTracker.

    This class provides callback methods that can be invoked during
    coordination execution to track swarm and worker state changes.

    Example:
        tracker = SwarmTracker()
        integration = SwarmIntegration(tracker)

        # In ClaudeCoordinator.coordinate_agents():
        integration.on_coordination_started(
            swarm_id="coord-123",
            mode=SwarmMode.PARALLEL,
            subtasks=[{"id": "sub-1", "name": "Research"}],
        )

        integration.on_subtask_started(
            swarm_id="coord-123",
            worker_id="worker-1",
            worker_name="Research Agent",
            worker_type=WorkerType.RESEARCH,
            role="Data Gatherer",
            task_description="Gather market data",
        )
    """

    def __init__(
        self,
        tracker: Optional[SwarmTracker] = None,
        auto_generate_ids: bool = True,
    ):
        """
        Initialize the SwarmIntegration.

        Args:
            tracker: SwarmTracker instance (uses default if not provided).
            auto_generate_ids: Whether to auto-generate IDs if not provided.
        """
        self._tracker = tracker or get_swarm_tracker()
        self._auto_generate_ids = auto_generate_ids
        self._active_swarms: Dict[str, str] = {}  # coordination_id -> swarm_id mapping

    @property
    def tracker(self) -> SwarmTracker:
        """Get the underlying SwarmTracker."""
        return self._tracker

    def _map_execution_mode_to_swarm_mode(self, execution_mode: str) -> SwarmMode:
        """Map execution mode string to SwarmMode enum."""
        mode_map = {
            "sequential": SwarmMode.SEQUENTIAL,
            "parallel": SwarmMode.PARALLEL,
            "hybrid": SwarmMode.HIERARCHICAL,
            "pipeline": SwarmMode.SEQUENTIAL,
        }
        return mode_map.get(execution_mode.lower(), SwarmMode.SEQUENTIAL)

    def _infer_worker_type(self, name: str, role: str) -> WorkerType:
        """Infer worker type from name and role."""
        name_lower = name.lower()
        role_lower = role.lower()

        if any(kw in name_lower or kw in role_lower for kw in ["research", "gather", "search"]):
            return WorkerType.RESEARCH
        elif any(kw in name_lower or kw in role_lower for kw in ["write", "author", "content"]):
            return WorkerType.WRITER
        elif any(kw in name_lower or kw in role_lower for kw in ["design", "ui", "ux"]):
            return WorkerType.DESIGNER
        elif any(kw in name_lower or kw in role_lower for kw in ["review", "check", "validate"]):
            return WorkerType.REVIEWER
        elif any(kw in name_lower or kw in role_lower for kw in ["coordinate", "orchestrate", "manage"]):
            return WorkerType.COORDINATOR
        elif any(kw in name_lower or kw in role_lower for kw in ["analyze", "analysis"]):
            return WorkerType.ANALYST
        elif any(kw in name_lower or kw in role_lower for kw in ["code", "develop", "program"]):
            return WorkerType.CODER
        elif any(kw in name_lower or kw in role_lower for kw in ["test", "qa"]):
            return WorkerType.TESTER
        else:
            return WorkerType.CUSTOM

    def on_coordination_started(
        self,
        swarm_id: str,
        mode: SwarmMode,
        subtasks: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentSwarmStatus:
        """
        Called when coordination starts.

        Args:
            swarm_id: Unique identifier for this coordination/swarm.
            mode: Execution mode for the swarm.
            subtasks: List of subtasks that will be executed.
            metadata: Optional additional metadata.

        Returns:
            The created AgentSwarmStatus.
        """
        logger.info(f"Coordination started: {swarm_id} with {len(subtasks)} subtasks")

        # Add subtask info to metadata
        full_metadata = metadata or {}
        full_metadata["subtask_count"] = len(subtasks)
        full_metadata["subtasks"] = [
            {"id": st.get("id", st.get("subtask_id")), "description": st.get("description", "")}
            for st in subtasks
        ]

        swarm = self._tracker.create_swarm(
            swarm_id=swarm_id,
            mode=mode,
            metadata=full_metadata,
        )

        self._active_swarms[swarm_id] = swarm_id
        return swarm

    def on_subtask_started(
        self,
        swarm_id: str,
        worker_id: str,
        worker_name: str,
        worker_type: WorkerType,
        role: str,
        task_description: str,
    ) -> WorkerExecution:
        """
        Called when a subtask/worker starts.

        Args:
            swarm_id: The swarm identifier.
            worker_id: Unique identifier for this worker.
            worker_name: Display name of the worker.
            worker_type: Type of the worker.
            role: Role description.
            task_description: Description of the subtask.

        Returns:
            The created WorkerExecution.
        """
        logger.info(f"Subtask started: {worker_id} ({worker_name}) in swarm {swarm_id}")

        return self._tracker.start_worker(
            swarm_id=swarm_id,
            worker_id=worker_id,
            worker_name=worker_name,
            worker_type=worker_type,
            role=role,
            current_task=task_description,
        )

    def on_subtask_progress(
        self,
        swarm_id: str,
        worker_id: str,
        progress: int,
        current_task: Optional[str] = None,
    ) -> WorkerExecution:
        """
        Called when subtask progress updates.

        Args:
            swarm_id: The swarm identifier.
            worker_id: The worker identifier.
            progress: Progress percentage (0-100).
            current_task: Optional updated task description.

        Returns:
            The updated WorkerExecution.
        """
        logger.debug(f"Subtask progress: {worker_id} at {progress}%")

        return self._tracker.update_worker_progress(
            swarm_id=swarm_id,
            worker_id=worker_id,
            progress=progress,
            current_task=current_task,
        )

    def on_tool_call(
        self,
        swarm_id: str,
        worker_id: str,
        tool_id: str,
        tool_name: str,
        is_mcp: bool,
        input_params: Dict[str, Any],
    ) -> ToolCallInfo:
        """
        Called when a tool is invoked.

        Args:
            swarm_id: The swarm identifier.
            worker_id: The worker identifier.
            tool_id: Unique identifier for this tool call.
            tool_name: Name of the tool.
            is_mcp: Whether this is an MCP tool.
            input_params: Tool input parameters.

        Returns:
            The created ToolCallInfo.
        """
        logger.debug(f"Tool call: {tool_name} by {worker_id}")

        return self._tracker.add_worker_tool_call(
            swarm_id=swarm_id,
            worker_id=worker_id,
            tool_id=tool_id,
            tool_name=tool_name,
            is_mcp=is_mcp,
            input_params=input_params,
        )

    def on_tool_result(
        self,
        swarm_id: str,
        worker_id: str,
        tool_id: str,
        result: Any = None,
        error: Optional[str] = None,
    ) -> ToolCallInfo:
        """
        Called when a tool call completes.

        Args:
            swarm_id: The swarm identifier.
            worker_id: The worker identifier.
            tool_id: The tool call identifier.
            result: Tool execution result.
            error: Error message if failed.

        Returns:
            The updated ToolCallInfo.
        """
        logger.debug(f"Tool result: {tool_id} {'failed' if error else 'succeeded'}")

        return self._tracker.update_tool_call_result(
            swarm_id=swarm_id,
            worker_id=worker_id,
            tool_id=tool_id,
            result=result,
            error=error,
        )

    def on_thinking(
        self,
        swarm_id: str,
        worker_id: str,
        content: str,
        token_count: Optional[int] = None,
    ) -> ThinkingContent:
        """
        Called when extended thinking content is generated.

        Args:
            swarm_id: The swarm identifier.
            worker_id: The worker identifier.
            content: The thinking content.
            token_count: Optional token count.

        Returns:
            The created ThinkingContent.
        """
        logger.debug(f"Thinking content from {worker_id}: {len(content)} chars")

        return self._tracker.add_worker_thinking(
            swarm_id=swarm_id,
            worker_id=worker_id,
            content=content,
            token_count=token_count,
        )

    def on_message(
        self,
        swarm_id: str,
        worker_id: str,
        role: str,
        content: str,
    ):
        """
        Called when a message is added to worker conversation.

        Args:
            swarm_id: The swarm identifier.
            worker_id: The worker identifier.
            role: Message role (user/assistant).
            content: Message content.
        """
        logger.debug(f"Message from {worker_id}: {role}")

        return self._tracker.add_worker_message(
            swarm_id=swarm_id,
            worker_id=worker_id,
            role=role,
            content=content,
        )

    def on_subtask_completed(
        self,
        swarm_id: str,
        worker_id: str,
        status: WorkerStatus = WorkerStatus.COMPLETED,
        error: Optional[str] = None,
    ) -> WorkerExecution:
        """
        Called when a subtask/worker completes.

        Args:
            swarm_id: The swarm identifier.
            worker_id: The worker identifier.
            status: Final status (COMPLETED or FAILED).
            error: Error message if failed.

        Returns:
            The updated WorkerExecution.
        """
        logger.info(f"Subtask completed: {worker_id} with status {status.value}")

        return self._tracker.complete_worker(
            swarm_id=swarm_id,
            worker_id=worker_id,
            status=status,
            error=error,
        )

    def on_coordination_completed(
        self,
        swarm_id: str,
        status: SwarmStatus = SwarmStatus.COMPLETED,
    ) -> AgentSwarmStatus:
        """
        Called when coordination completes.

        Args:
            swarm_id: The swarm identifier.
            status: Final status (COMPLETED or FAILED).

        Returns:
            The updated AgentSwarmStatus.
        """
        logger.info(f"Coordination completed: {swarm_id} with status {status.value}")

        # Clean up active swarm tracking
        self._active_swarms.pop(swarm_id, None)

        return self._tracker.complete_swarm(
            swarm_id=swarm_id,
            status=status,
        )

    def get_active_swarm_ids(self) -> List[str]:
        """Get list of active swarm IDs."""
        return list(self._active_swarms.keys())

    def is_swarm_active(self, swarm_id: str) -> bool:
        """Check if a swarm is currently active."""
        return swarm_id in self._active_swarms


# Factory function
def create_swarm_integration(
    tracker: Optional[SwarmTracker] = None,
) -> SwarmIntegration:
    """
    Create a SwarmIntegration instance.

    Args:
        tracker: Optional SwarmTracker (uses default if not provided).

    Returns:
        SwarmIntegration instance.
    """
    return SwarmIntegration(tracker=tracker)

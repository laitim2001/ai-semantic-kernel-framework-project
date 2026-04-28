"""Session Recovery Manager — three-layer checkpoint restore logic.

Coordinates restoration of a session from its three checkpoint layers:
  L1: Conversation State (Redis, ephemeral)
  L2: Task State (PostgreSQL, via TaskStore)
  L3: Agent Execution State (PostgreSQL, permanent)

Sprint 115 — Phase 37 E2E Assembly B.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SessionSummary(BaseModel):
    """Summary of a recoverable session for the sessions list API."""

    session_id: str
    has_conversation: bool = False
    message_count: int = 0
    has_tasks: bool = False
    task_count: int = 0
    pending_tasks: int = 0
    has_execution: bool = False
    execution_count: int = 0
    last_activity: Optional[datetime] = None
    status: str = "unknown"  # active / paused / recoverable / expired
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RecoveryResult(BaseModel):
    """Result of a session recovery attempt."""

    session_id: str
    success: bool
    layers_restored: List[str] = Field(default_factory=list)
    layers_missing: List[str] = Field(default_factory=list)
    conversation_restored: bool = False
    tasks_restored: int = 0
    execution_restored: bool = False
    resume_context: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class SessionRecoveryManager:
    """Coordinates three-layer session recovery.

    Args:
        conversation_store: L1 ConversationStateStore.
        task_service: L2 TaskService.
        execution_store: L3 ExecutionStateStore.
    """

    def __init__(
        self,
        conversation_store: Any = None,
        task_service: Any = None,
        execution_store: Any = None,
    ) -> None:
        self._conv_store = conversation_store
        self._task_service = task_service
        self._exec_store = execution_store

    async def list_recoverable_sessions(
        self,
        user_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[SessionSummary]:
        """List sessions that can potentially be recovered.

        Scans all three layers to find sessions with residual state.
        """
        sessions: Dict[str, SessionSummary] = {}

        # L1: Scan conversation states
        if self._conv_store:
            try:
                active_ids = await self._conv_store.list_active_sessions()
                for sid in active_ids:
                    conv = await self._conv_store.load(sid)
                    if conv:
                        summary = sessions.setdefault(sid, SessionSummary(session_id=sid))
                        summary.has_conversation = True
                        summary.message_count = conv.message_count
                        summary.last_activity = conv.updated_at
                        summary.status = "active"
            except Exception as e:
                logger.warning("L1 scan failed: %s", e)

        # L2: Scan tasks
        if self._task_service:
            try:
                tasks = await self._task_service.list_tasks(
                    user_id=user_id, limit=200
                )
                for task in tasks:
                    if task.session_id:
                        summary = sessions.setdefault(
                            task.session_id, SessionSummary(session_id=task.session_id)
                        )
                        summary.has_tasks = True
                        summary.task_count += 1
                        if task.status.value in ("pending", "in_progress", "queued"):
                            summary.pending_tasks += 1
                        if task.updated_at and (
                            summary.last_activity is None
                            or task.updated_at > summary.last_activity
                        ):
                            summary.last_activity = task.updated_at
                        if summary.pending_tasks > 0:
                            summary.status = "recoverable"
            except Exception as e:
                logger.warning("L2 scan failed: %s", e)

        # Sort by last_activity descending, take limit
        result = sorted(
            sessions.values(),
            key=lambda s: s.last_activity or datetime.min,
            reverse=True,
        )
        return result[:limit]

    async def recover_session(self, session_id: str) -> RecoveryResult:
        """Attempt to recover a session from all three layers.

        Recovery is best-effort: each layer that can be restored adds
        to the resume context. Missing layers are noted but do not
        cause failure.
        """
        result = RecoveryResult(session_id=session_id, success=True)
        resume_ctx: Dict[str, Any] = {"session_id": session_id}

        # L1: Restore conversation
        if self._conv_store:
            try:
                conv = await self._conv_store.load(session_id)
                if conv:
                    result.conversation_restored = True
                    result.layers_restored.append("L1_conversation")
                    resume_ctx["messages"] = [
                        m.model_dump(mode="json") for m in conv.messages[-10:]
                    ]
                    resume_ctx["routing_decision"] = conv.routing_decision
                    resume_ctx["message_count"] = conv.message_count
                    logger.info(
                        "L1 restored: session=%s messages=%d",
                        session_id, conv.message_count,
                    )
                else:
                    result.layers_missing.append("L1_conversation")
            except Exception as e:
                logger.warning("L1 restore failed for %s: %s", session_id, e)
                result.layers_missing.append("L1_conversation")

        # L2: Restore tasks
        if self._task_service:
            try:
                tasks = await self._task_service.list_tasks(session_id=session_id)
                if tasks:
                    result.tasks_restored = len(tasks)
                    result.layers_restored.append("L2_tasks")
                    resume_ctx["tasks"] = [
                        {
                            "task_id": t.task_id,
                            "title": t.title,
                            "status": t.status.value,
                            "progress": t.progress,
                            "task_type": t.task_type.value,
                        }
                        for t in tasks
                    ]
                    logger.info(
                        "L2 restored: session=%s tasks=%d",
                        session_id, len(tasks),
                    )
                else:
                    result.layers_missing.append("L2_tasks")
            except Exception as e:
                logger.warning("L2 restore failed for %s: %s", session_id, e)
                result.layers_missing.append("L2_tasks")

        # L3: Restore execution state
        if self._exec_store:
            try:
                exec_states = await self._exec_store.load_by_session(session_id)
                if exec_states:
                    result.execution_restored = True
                    result.execution_count = len(exec_states)
                    result.layers_restored.append("L3_execution")
                    # Include latest execution context
                    latest = max(exec_states, key=lambda s: s.updated_at)
                    resume_ctx["execution"] = {
                        "execution_id": latest.execution_id,
                        "agent_type": latest.agent_type,
                        "execution_mode": latest.execution_mode,
                        "status": latest.status,
                        "progress": latest.progress,
                        "tool_call_count": len(latest.tool_calls),
                    }
                    logger.info(
                        "L3 restored: session=%s executions=%d",
                        session_id, len(exec_states),
                    )
                else:
                    result.layers_missing.append("L3_execution")
            except Exception as e:
                logger.warning("L3 restore failed for %s: %s", session_id, e)
                result.layers_missing.append("L3_execution")

        result.resume_context = resume_ctx
        result.success = len(result.layers_restored) > 0

        if not result.success:
            result.error = "No recoverable state found in any layer"

        logger.info(
            "Session recovery: session=%s success=%s restored=%s missing=%s",
            session_id, result.success,
            result.layers_restored, result.layers_missing,
        )
        return result

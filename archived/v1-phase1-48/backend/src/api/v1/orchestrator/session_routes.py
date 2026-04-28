"""Session Resume API — endpoints for listing and recovering sessions.

Sprint 115 — Phase 37 E2E Assembly B.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.integrations.hybrid.orchestrator.session_recovery import (
    RecoveryResult,
    SessionRecoveryManager,
    SessionSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions-resume"])

# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_recovery_manager: Optional[SessionRecoveryManager] = None


def _get_recovery_manager() -> SessionRecoveryManager:
    """Lazy-initialise the shared SessionRecoveryManager."""
    global _recovery_manager
    if _recovery_manager is None:
        # Wire up all three layers
        conv_store = None
        task_service = None
        exec_store = None

        try:
            from src.infrastructure.storage.conversation_state import (
                ConversationStateStore,
            )
            conv_store = ConversationStateStore()
        except Exception as e:
            logger.warning("Session resume: L1 store unavailable: %s", e)

        try:
            from src.domain.tasks.service import TaskService
            from src.infrastructure.storage.task_store import TaskStore
            task_service = TaskService(task_store=TaskStore())
        except Exception as e:
            logger.warning("Session resume: L2 store unavailable: %s", e)

        try:
            from src.infrastructure.storage.execution_state import (
                ExecutionStateStore,
            )
            exec_store = ExecutionStateStore()
        except Exception as e:
            logger.warning("Session resume: L3 store unavailable: %s", e)

        _recovery_manager = SessionRecoveryManager(
            conversation_store=conv_store,
            task_service=task_service,
            execution_store=exec_store,
        )
        logger.info("Session resume: RecoveryManager initialized")
    return _recovery_manager


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class SessionListResponse(BaseModel):
    """Response for session listing."""
    sessions: List[Dict[str, Any]]
    total: int


class SessionResumeResponse(BaseModel):
    """Response for session resume."""
    session_id: str
    success: bool
    layers_restored: List[str]
    layers_missing: List[str]
    conversation_restored: bool
    tasks_restored: int
    execution_restored: bool
    resume_context: Dict[str, Any]
    error: Optional[str] = None


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/recoverable", response_model=SessionListResponse)
async def list_recoverable_sessions(
    user_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> SessionListResponse:
    """List sessions that can be recovered.

    Scans L1 (conversation), L2 (tasks), and L3 (execution) layers
    to find sessions with residual state.
    """
    manager = _get_recovery_manager()
    sessions = await manager.list_recoverable_sessions(
        user_id=user_id,
        limit=limit,
    )
    return SessionListResponse(
        sessions=[s.model_dump(mode="json") for s in sessions],
        total=len(sessions),
    )


@router.post("/{session_id}/resume", response_model=SessionResumeResponse)
async def resume_session(session_id: str) -> SessionResumeResponse:
    """Resume a session by recovering state from all three layers.

    Returns the recovered context which can be used to continue the
    conversation from where it left off.
    """
    manager = _get_recovery_manager()
    result = await manager.recover_session(session_id)

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.error or f"No recoverable state for session {session_id}",
        )

    return SessionResumeResponse(
        session_id=result.session_id,
        success=result.success,
        layers_restored=result.layers_restored,
        layers_missing=result.layers_missing,
        conversation_restored=result.conversation_restored,
        tasks_restored=result.tasks_restored,
        execution_restored=result.execution_restored,
        resume_context=result.resume_context,
        error=result.error,
    )

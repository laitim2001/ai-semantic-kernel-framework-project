# =============================================================================
# IPA Platform - Hybrid Mode Switch API Routes
# =============================================================================
# Sprint 56: Mode Switcher & HITL
#
# REST API endpoints for hybrid mode switching:
#   - POST /hybrid/switch - Manual trigger mode switch
#   - GET /hybrid/switch/status/{session_id} - Query switch status
#   - POST /hybrid/switch/rollback - Rollback switch
#   - GET /hybrid/switch/history/{session_id} - Get switch history
#   - GET /hybrid/switch/checkpoints/{session_id} - List available checkpoints
#
# Dependencies:
#   - ModeSwitcher (src.integrations.hybrid.switching)
#   - SwitchTrigger, SwitchResult (src.integrations.hybrid.switching.models)
# =============================================================================

import logging
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status

from src.integrations.hybrid.intent.models import ExecutionMode
from src.integrations.hybrid.switching import (
    InMemoryCheckpointStorage,
    MigrationConfig,
    ModeTransition,
    ModeSwitcher,
    StateMigrator,
    SwitchCheckpoint,
    SwitchConfig,
    SwitchResult,
    SwitchStatus,
    SwitchTrigger,
    SwitchTriggerType,
)
from src.integrations.hybrid.switching.migration.state_migrator import (
    MigrationContext,
    MigrationStatus,
)

from .switch_schemas import (
    MigratedStateResponse,
    ModeTransitionResponse,
    RollbackRequest,
    RollbackResultResponse,
    SwitchCheckpointResponse,
    SwitchHistoryResponse,
    SwitchRequest,
    SwitchResultResponse,
    SwitchStatusResponse,
    SwitchTriggerResponse,
)
from .core_routes import get_context_bridge, get_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/hybrid/switch",
    tags=["hybrid-switch"],
    responses={
        404: {"description": "Session or checkpoint not found"},
        400: {"description": "Invalid switch request"},
        500: {"description": "Internal server error"},
    },
)


# =============================================================================
# Singleton Instances
# =============================================================================

_mode_switcher: Optional[ModeSwitcher] = None
_checkpoint_storage: Optional[InMemoryCheckpointStorage] = None
_session_modes: Dict[str, ExecutionMode] = {}  # Track current mode per session
_transition_history: Dict[str, List[ModeTransition]] = {}  # Track transitions


def get_mode_switcher() -> ModeSwitcher:
    """Get or create ModeSwitcher singleton."""
    global _mode_switcher, _checkpoint_storage
    if _mode_switcher is None:
        _checkpoint_storage = InMemoryCheckpointStorage()
        config = SwitchConfig(
            enable_rollback=True,
            enable_auto_switch=True,
            preserve_history=True,
            preserve_tool_results=True,
        )
        _mode_switcher = ModeSwitcher(
            config=config,
            checkpoint_storage=_checkpoint_storage,
        )
    return _mode_switcher


def get_checkpoint_storage() -> InMemoryCheckpointStorage:
    """Get checkpoint storage singleton."""
    global _checkpoint_storage
    if _checkpoint_storage is None:
        get_mode_switcher()  # Initialize both
    return _checkpoint_storage


def get_session_mode(session_id: str) -> ExecutionMode:
    """Get current execution mode for a session.

    Looks up mode from:
    1. Local _session_modes cache (set by switch operations)
    2. Orchestrator session context (set by execute operations)
    3. Default to CHAT_MODE (matches ExecutionContextV2 default)
    """
    # First check local cache (set by switch operations)
    if session_id in _session_modes:
        logger.info(f"get_session_mode({session_id}): Found in _session_modes cache: {_session_modes[session_id]}")
        return _session_modes[session_id]

    # Then check orchestrator session (set by execute operations)
    try:
        orchestrator = get_orchestrator()
        logger.info(f"get_session_mode({session_id}): orchestrator has {len(orchestrator._sessions)} sessions")
        session_data = orchestrator.get_session(session_id)
        logger.info(f"get_session_mode({session_id}): orchestrator.get_session returned: {session_data}")
        if session_data:
            logger.info(f"get_session_mode({session_id}): session_data.current_mode = {session_data.current_mode}")
            if session_data.current_mode:
                return session_data.current_mode
    except Exception as e:
        logger.warning(f"get_session_mode({session_id}): Exception during orchestrator lookup: {e}")

    # Default to CHAT_MODE (matches ExecutionContextV2 dataclass default)
    logger.info(f"get_session_mode({session_id}): Returning default CHAT_MODE")
    return ExecutionMode.CHAT_MODE


def set_session_mode(session_id: str, mode: ExecutionMode) -> None:
    """Set execution mode for a session."""
    _session_modes[session_id] = mode


def add_transition(session_id: str, transition: ModeTransition) -> None:
    """Add transition to history."""
    if session_id not in _transition_history:
        _transition_history[session_id] = []
    _transition_history[session_id].append(transition)
    # Keep last 100 transitions per session
    _transition_history[session_id] = _transition_history[session_id][-100:]


def get_transitions(session_id: str, limit: int = 10) -> List[ModeTransition]:
    """Get transition history for a session."""
    return _transition_history.get(session_id, [])[-limit:]


# =============================================================================
# Helper Functions
# =============================================================================


def _parse_execution_mode(mode_str: str) -> ExecutionMode:
    """Parse execution mode string to enum."""
    mode_map = {
        "workflow": ExecutionMode.WORKFLOW_MODE,
        "chat": ExecutionMode.CHAT_MODE,
        "hybrid": ExecutionMode.HYBRID_MODE,
    }
    if mode_str not in mode_map:
        raise ValueError(f"Invalid mode: {mode_str}")
    return mode_map[mode_str]


def _mode_to_str(mode: ExecutionMode) -> str:
    """Convert ExecutionMode to string."""
    return mode.value if hasattr(mode, 'value') else str(mode)


def _trigger_to_response(trigger: SwitchTrigger) -> SwitchTriggerResponse:
    """Convert SwitchTrigger to response schema."""
    return SwitchTriggerResponse(
        trigger_type=trigger.trigger_type.value,
        reason=trigger.reason,
        confidence=trigger.confidence,
        source_mode=_mode_to_str(trigger.source_mode),
        target_mode=_mode_to_str(trigger.target_mode),
        detected_at=trigger.detected_at,
        metadata=trigger.metadata,
    )


def _checkpoint_to_response(
    checkpoint: SwitchCheckpoint,
    session_id: str = "",
) -> SwitchCheckpointResponse:
    """Convert SwitchCheckpoint to response schema."""
    # Extract session_id from context_snapshot if available
    cp_session_id = session_id or checkpoint.context_snapshot.get("session_id", "")
    # mode_before contains the source mode
    source_mode = checkpoint.mode_before if isinstance(checkpoint.mode_before, str) else ""
    # Target mode not stored directly, use "unknown" or derive from context
    target_mode = checkpoint.context_snapshot.get("target_mode", "unknown")

    return SwitchCheckpointResponse(
        checkpoint_id=checkpoint.checkpoint_id,
        session_id=cp_session_id,
        source_mode=source_mode,
        target_mode=target_mode,
        created_at=checkpoint.created_at,
        execution_state=checkpoint.context_snapshot,
    )


def _transition_to_response(transition: ModeTransition) -> ModeTransitionResponse:
    """Convert ModeTransition to response schema."""
    # Extract values from result if available
    result = transition.result
    status = result.status.value if result else SwitchStatus.PENDING.value
    checkpoint_id = result.checkpoint_id if result else transition.metadata.get("checkpoint_id")
    started_at = result.started_at if result else transition.created_at
    completed_at = result.completed_at if result else None
    duration_ms = result.switch_time_ms if result else 0
    error = result.error if result else None

    # source_mode and target_mode are already strings in the model
    source_mode = transition.source_mode if isinstance(transition.source_mode, str) else str(transition.source_mode)
    target_mode = transition.target_mode if isinstance(transition.target_mode, str) else str(transition.target_mode)

    return ModeTransitionResponse(
        transition_id=transition.transition_id,
        session_id=transition.session_id,
        source_mode=source_mode,
        target_mode=target_mode,
        status=status,
        trigger=_trigger_to_response(transition.trigger) if transition.trigger else None,
        checkpoint_id=checkpoint_id,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=duration_ms,
        error=error,
    )


def _result_to_response(result: SwitchResult, session_id: str) -> SwitchResultResponse:
    """Convert SwitchResult to response schema."""
    migrated_state = None
    if result.migrated_state:
        ms = result.migrated_state
        # Handle both MigratedState types (models.py has direction, state_migrator.py has source_mode)
        if hasattr(ms, "source_mode"):
            source_mode = _mode_to_str(ms.source_mode)
            target_mode = _mode_to_str(ms.target_mode)
            status_val = ms.status.value if hasattr(ms.status, 'value') else str(ms.status)
            migrated_at = getattr(ms, 'migrated_at', None)
            conv_history = getattr(ms, 'conversation_history', [])
            tool_records = getattr(ms, 'tool_call_records', [])
        elif hasattr(ms, "direction"):
            # Extract source/target from direction enum name (e.g., WORKFLOW_TO_CHAT)
            direction_name = ms.direction.name if hasattr(ms.direction, 'name') else str(ms.direction)
            parts = direction_name.split("_TO_")
            source_mode = parts[0].lower() if len(parts) >= 1 else "unknown"
            target_mode = parts[1].lower() if len(parts) >= 2 else "unknown"
            status_val = "completed"
            migrated_at = None
            conv_history = getattr(ms, 'conversation_history', [])
            tool_records = []
        else:
            source_mode = "unknown"
            target_mode = "unknown"
            status_val = "unknown"
            migrated_at = None
            conv_history = []
            tool_records = []

        migrated_state = MigratedStateResponse(
            source_mode=source_mode,
            target_mode=target_mode,
            status=status_val,
            migrated_at=migrated_at,
            conversation_history_count=len(conv_history),
            tool_call_count=len(tool_records),
            context_summary=getattr(ms, 'context_summary', ""),
            warnings=getattr(ms, 'warnings', []),
        )

    # Note: checkpoint is just an ID in SwitchResult, not the full object
    # We don't fetch the full checkpoint here to keep the function synchronous
    # The checkpoint_id is available in the result for reference
    checkpoint = None  # Full checkpoint would require async storage access

    # can_rollback is determined by whether we have a checkpoint_id
    can_rollback = result.checkpoint_id is not None

    return SwitchResultResponse(
        success=result.success,
        session_id=session_id,
        source_mode=_mode_to_str(result.trigger.source_mode),
        target_mode=_mode_to_str(result.trigger.target_mode),
        status=result.status.value,
        trigger=_trigger_to_response(result.trigger),
        migrated_state=migrated_state,
        checkpoint=checkpoint,
        started_at=result.started_at,
        completed_at=result.completed_at,
        duration_ms=result.switch_time_ms,  # SwitchResult uses switch_time_ms
        error=result.error,
        can_rollback=can_rollback,
    )


# =============================================================================
# API Routes
# =============================================================================


@router.post(
    "",
    response_model=SwitchResultResponse,
    summary="Trigger mode switch",
    description="Manually trigger a mode switch for a session.",
)
async def trigger_switch(request: SwitchRequest):
    """
    Trigger manual mode switch.

    This endpoint allows manual switching between execution modes:
    - workflow: Multi-step structured workflows via MAF adapters
    - chat: Conversational interaction via Claude SDK
    - hybrid: Combined mode with intelligent routing

    Args:
        request: Switch request with session_id and target_mode

    Returns:
        SwitchResultResponse: Result of the switch operation

    Raises:
        HTTPException: 400 if invalid mode or switch conditions not met
    """
    # DEBUG: Trace _session_modes at switch entry
    logger.info(f"trigger_switch ENTRY: session_id={request.session_id}")
    logger.info(f"trigger_switch ENTRY: _session_modes dict id={id(_session_modes)}, content={dict(_session_modes)}")

    switcher = get_mode_switcher()
    current_mode = get_session_mode(request.session_id)
    logger.info(f"trigger_switch: get_session_mode returned {current_mode}")

    # Parse target mode
    try:
        target_mode = _parse_execution_mode(request.target_mode)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid target mode: {request.target_mode}. "
                   f"Valid options: workflow, chat, hybrid"
        )

    # Check if already in target mode
    if current_mode == target_mode and not request.force:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session is already in {request.target_mode} mode. "
                   f"Use force=true to force switch."
        )

    logger.info(
        f"Triggering switch for session {request.session_id} "
        f"from {current_mode} to {target_mode}"
    )

    # Create manual trigger
    # SwitchTrigger expects mode values as strings, not ExecutionMode enums
    trigger = SwitchTrigger(
        trigger_type=SwitchTriggerType.MANUAL,
        reason=request.reason,
        confidence=1.0,  # Manual switches have full confidence
        source_mode=current_mode.value,
        target_mode=target_mode.value,
        metadata=request.metadata,
    )

    # Create migration context with actual session data from orchestrator
    orchestrator = get_orchestrator()
    session_data = orchestrator.get_session(request.session_id)

    # Extract actual session state
    conversation_history = []
    workflow_steps = []
    tool_calls = []
    variables = {}

    if session_data:
        conversation_history = session_data.conversation_history or []
        tool_calls = [
            {"name": t.tool_name, "result": t.result, "success": t.success}
            for t in (session_data.tool_executions or [])
        ]
        # Extract variables from conversation history and metadata
        variables = session_data.metadata.copy() if session_data.metadata else {}
        # Add context from conversation for state preservation
        if session_data.hybrid_context and session_data.hybrid_context.maf:
            maf = session_data.hybrid_context.maf
            variables.update({
                "workflow_id": maf.workflow_id,
                "workflow_name": maf.workflow_name,
                "current_step": maf.current_step,
            })
            if maf.metadata:
                variables.update(maf.metadata)

    context = MigrationContext(
        session_id=request.session_id,
        current_mode=current_mode,
        conversation_history=conversation_history,
        workflow_steps=workflow_steps,
        tool_calls=tool_calls,
        variables=variables,
        metadata=request.metadata,
    )

    try:
        # Execute switch
        result = await switcher.execute_switch(
            trigger=trigger,
            context=context,
            session_id=request.session_id,
        )

        # Update session mode on success
        if result.success:
            set_session_mode(request.session_id, target_mode)

            # Update ContextBridge to ensure get_context_state works
            bridge = get_context_bridge()
            try:
                # Create or update hybrid context in the bridge
                await bridge.get_or_create_hybrid(request.session_id)
            except Exception as e:
                logger.warning(f"Failed to update context bridge: {e}")

            # Create transition record
            transition = ModeTransition(
                transition_id=str(uuid4()),
                session_id=request.session_id,
                source_mode=current_mode,
                target_mode=target_mode,
                trigger=trigger,
                result=result,
                metadata={"checkpoint_id": result.checkpoint_id} if result.checkpoint_id else {},
            )
            add_transition(request.session_id, transition)

        return _result_to_response(result, request.session_id)

    except Exception as e:
        import traceback
        full_trace = traceback.format_exc()
        logger.error(f"Switch failed for session {request.session_id}: {e}\n{full_trace}")
        print(f"=== SWITCH ERROR ===\n{full_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Switch failed: {str(e)}"
        )


@router.get(
    "/status/{session_id}",
    response_model=SwitchStatusResponse,
    summary="Get switch status",
    description="Get the current switch status for a session.",
)
async def get_switch_status(
    session_id: str,
    include_history: bool = Query(True, description="Include switch history"),
    history_limit: int = Query(10, ge=1, le=100, description="History limit"),
):
    """
    Get switch status for a session.

    Args:
        session_id: Session identifier
        include_history: Whether to include transition history
        history_limit: Maximum history items to return

    Returns:
        SwitchStatusResponse: Current switch status
    """
    current_mode = get_session_mode(session_id)
    storage = get_checkpoint_storage()

    # Get available checkpoints
    checkpoints = await storage.list_checkpoints(session_id)

    # Get transition history
    transitions = get_transitions(session_id, history_limit) if include_history else []

    # Get last transition
    last_switch = None
    if transitions:
        last_switch = _transition_to_response(transitions[-1])

    return SwitchStatusResponse(
        session_id=session_id,
        current_mode=_mode_to_str(current_mode),
        last_switch=last_switch,
        pending_switch=None,  # Could be populated if async switch in progress
        switch_history=[_transition_to_response(t) for t in transitions],
        can_switch=True,  # Could add logic to check if switch is allowed
        available_checkpoints=len(checkpoints),
    )


@router.post(
    "/rollback",
    response_model=RollbackResultResponse,
    summary="Rollback switch",
    description="Rollback to a previous mode using a checkpoint.",
)
async def rollback_switch(request: RollbackRequest):
    """
    Rollback a mode switch.

    This endpoint allows rolling back to a previous execution mode
    using a stored checkpoint.

    Args:
        request: Rollback request with session_id and optional checkpoint_id

    Returns:
        RollbackResultResponse: Result of the rollback operation

    Raises:
        HTTPException: 404 if no checkpoint available, 500 if rollback fails
    """
    switcher = get_mode_switcher()
    storage = get_checkpoint_storage()
    current_mode = get_session_mode(request.session_id)

    # Get checkpoint
    if request.checkpoint_id:
        checkpoint = await storage.get_checkpoint(request.checkpoint_id)
        if checkpoint is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Checkpoint not found: {request.checkpoint_id}"
            )
    else:
        # Get latest checkpoint
        checkpoint = await storage.get_latest_checkpoint(request.session_id)
        if checkpoint is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No checkpoints available for session: {request.session_id}"
            )

    logger.info(
        f"Rolling back session {request.session_id} "
        f"to checkpoint {checkpoint.checkpoint_id}"
    )

    try:
        # Execute rollback
        result_bool = await switcher.rollback_switch(
            checkpoint_id_or_checkpoint=checkpoint.checkpoint_id,
        )
        # Create a SwitchResult from the boolean result
        result = SwitchResult(
            success=result_bool,
            status=SwitchStatus.ROLLED_BACK if result_bool else SwitchStatus.FAILED,
            error=None if result_bool else "Rollback failed",
        )

        if result.success:
            # Update session mode - use mode_before (the mode at checkpoint creation)
            set_session_mode(request.session_id, checkpoint.mode_before)

            # Create rollback transition record
            trigger = SwitchTrigger(
                trigger_type=SwitchTriggerType.MANUAL,
                reason=request.reason,
                confidence=1.0,
                source_mode=current_mode,
                target_mode=checkpoint.mode_before,
            )

            transition = ModeTransition(
                transition_id=str(uuid4()),
                session_id=request.session_id,
                source_mode=current_mode,
                target_mode=checkpoint.mode_before,
                trigger=trigger,
                result=result,
                rollback_of=checkpoint.switch_id,
                metadata={"checkpoint_id": checkpoint.checkpoint_id},
            )
            add_transition(request.session_id, transition)

        return RollbackResultResponse(
            success=result.success,
            session_id=request.session_id,
            rolled_back_from=_mode_to_str(current_mode),
            rolled_back_to=_mode_to_str(checkpoint.mode_before),
            checkpoint_id=checkpoint.checkpoint_id,
            restored_state=checkpoint.context_snapshot,  # Already a dict
            completed_at=result.completed_at or datetime.utcnow(),
            error=result.error,
        )

    except Exception as e:
        logger.error(f"Rollback failed for session {request.session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rollback failed: {str(e)}"
        )


@router.get(
    "/history/{session_id}",
    response_model=SwitchHistoryResponse,
    summary="Get switch history",
    description="Get the mode switch history for a session.",
)
async def get_switch_history(
    session_id: str,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of items to return"),
):
    """
    Get switch history for a session.

    Args:
        session_id: Session identifier
        skip: Number of items to skip
        limit: Maximum items to return

    Returns:
        SwitchHistoryResponse: Switch history with pagination
    """
    all_transitions = _transition_history.get(session_id, [])
    total = len(all_transitions)

    # Apply pagination (from most recent)
    transitions = list(reversed(all_transitions))[skip:skip + limit]

    return SwitchHistoryResponse(
        session_id=session_id,
        transitions=[_transition_to_response(t) for t in transitions],
        total=total,
        page=(skip // limit) + 1,
        page_size=limit,
    )


@router.get(
    "/checkpoints/{session_id}",
    summary="List checkpoints",
    description="List available checkpoints for a session.",
)
async def list_checkpoints(
    session_id: str,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=50, description="Number of items to return"),
):
    """
    List available checkpoints for rollback.

    Args:
        session_id: Session identifier
        skip: Number of items to skip
        limit: Maximum items to return

    Returns:
        dict: List of checkpoints with pagination
    """
    storage = get_checkpoint_storage()
    checkpoints = await storage.list_checkpoints(session_id)

    total = len(checkpoints)
    # Sort by created_at descending
    checkpoints = sorted(checkpoints, key=lambda c: c.created_at, reverse=True)
    checkpoints = checkpoints[skip:skip + limit]

    return {
        "data": [_checkpoint_to_response(c, session_id) for c in checkpoints],
        "total": total,
        "page": (skip // limit) + 1,
        "page_size": limit,
        "session_id": session_id,
    }


@router.delete(
    "/checkpoints/{session_id}/{checkpoint_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete checkpoint",
    description="Delete a specific checkpoint.",
)
async def delete_checkpoint(session_id: str, checkpoint_id: str):
    """
    Delete a specific checkpoint.

    Args:
        session_id: Session identifier
        checkpoint_id: Checkpoint to delete

    Raises:
        HTTPException: 404 if checkpoint not found
    """
    storage = get_checkpoint_storage()
    checkpoint = await storage.get_checkpoint(checkpoint_id)

    # session_id is stored in context_snapshot, not as a direct attribute
    checkpoint_session_id = (
        checkpoint.context_snapshot.get("session_id", "") if checkpoint else None
    )
    if checkpoint is None or checkpoint_session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Checkpoint not found: {checkpoint_id}"
        )

    await storage.delete_checkpoint(checkpoint_id)
    logger.info(f"Deleted checkpoint {checkpoint_id} for session {session_id}")


@router.delete(
    "/history/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear switch history",
    description="Clear all switch history for a session.",
)
async def clear_switch_history(session_id: str):
    """
    Clear switch history for a session.

    Args:
        session_id: Session identifier
    """
    if session_id in _transition_history:
        del _transition_history[session_id]
    logger.info(f"Cleared switch history for session {session_id}")

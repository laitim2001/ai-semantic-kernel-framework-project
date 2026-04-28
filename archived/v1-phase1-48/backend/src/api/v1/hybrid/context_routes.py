# =============================================================================
# IPA Platform - Hybrid Context API Routes
# =============================================================================
# Sprint 53: Context Bridge & Sync
#
# REST API endpoints for hybrid context management:
#   - GET /hybrid/context/{session_id} - Get hybrid context
#   - POST /hybrid/context/sync - Trigger manual sync
#   - POST /hybrid/context/merge - Merge MAF and Claude contexts
#   - GET /hybrid/context/{session_id}/status - Get sync status
#
# Dependencies:
#   - ContextBridge (src.integrations.hybrid.context.bridge)
#   - ContextSynchronizer (src.integrations.hybrid.context.sync.synchronizer)
# =============================================================================

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from src.integrations.hybrid.context.bridge import ContextBridge
from src.integrations.hybrid.context.models import (
    ClaudeContext,
    HybridContext,
    MAFContext,
    SyncDirection,
    SyncStrategy,
)
from src.integrations.hybrid.context.sync.synchronizer import ContextSynchronizer
from src.integrations.hybrid.context.sync.events import SyncEventPublisher

from .schemas import (
    ClaudeContextResponse,
    HybridContextResponse,
    MAFContextResponse,
    MergeContextRequest,
    SyncRequest,
    SyncResultResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/hybrid/context",
    tags=["hybrid-context"],
    responses={
        404: {"description": "Context not found"},
        500: {"description": "Internal server error"},
    },
)


# =============================================================================
# Singleton Instances
# =============================================================================

# Note: ContextBridge is shared with core_routes.py to ensure context
# created during execution is visible in context queries
_synchronizer: Optional[ContextSynchronizer] = None
_event_publisher: Optional[SyncEventPublisher] = None


def get_context_bridge() -> ContextBridge:
    """Get shared ContextBridge singleton from core_routes."""
    # Import from core_routes to share the same instance
    from .core_routes import get_context_bridge as get_shared_bridge
    return get_shared_bridge()


def get_synchronizer() -> ContextSynchronizer:
    """Get or create ContextSynchronizer singleton."""
    global _synchronizer, _event_publisher
    if _synchronizer is None:
        _event_publisher = SyncEventPublisher()
        _synchronizer = ContextSynchronizer(
            event_publisher=_event_publisher,
        )
    return _synchronizer


# =============================================================================
# Helper Functions
# =============================================================================


def _maf_context_to_response(maf: MAFContext) -> MAFContextResponse:
    """Convert MAFContext to response schema."""
    return MAFContextResponse(
        workflow_id=maf.workflow_id,
        workflow_name=maf.workflow_name,
        current_step=maf.current_step,
        total_steps=maf.total_steps,
        agent_states={
            k: {
                "agent_id": v.agent_id,
                "agent_name": v.agent_name,
                "status": v.status.value,
                "current_task": v.current_task,
                "last_output": v.last_output,
                "error_message": v.error_message,
                "metadata": v.metadata,
                "updated_at": v.updated_at,
            }
            for k, v in maf.agent_states.items()
        },
        checkpoint_data=maf.checkpoint_data,
        pending_approvals=[
            {
                "request_id": a.request_id,
                "checkpoint_id": a.checkpoint_id,
                "action": a.action,
                "description": a.description,
                "status": a.status.value,
                "requested_by": a.requested_by,
                "requested_at": a.requested_at,
                "responded_at": a.responded_at,
                "timeout_seconds": a.timeout_seconds,
            }
            for a in maf.pending_approvals
        ],
        execution_history=[
            {
                "record_id": r.record_id,
                "step_index": r.step_index,
                "step_name": r.step_name,
                "agent_id": r.agent_id,
                "status": r.status,
                "error": r.error,
                "started_at": r.started_at,
                "completed_at": r.completed_at,
                "duration_ms": r.duration_ms,
            }
            for r in maf.execution_history
        ],
        metadata=maf.metadata,
        created_at=maf.created_at,
        last_updated=maf.last_updated,
    )


def _claude_context_to_response(claude: ClaudeContext) -> ClaudeContextResponse:
    """Convert ClaudeContext to response schema."""
    return ClaudeContextResponse(
        session_id=claude.session_id,
        message_count=len(claude.conversation_history),
        tool_call_count=len(claude.tool_call_history),
        current_system_prompt=claude.current_system_prompt,
        context_variables=claude.context_variables,
        active_hooks=claude.active_hooks,
        mcp_server_states=claude.mcp_server_states,
        metadata=claude.metadata,
        created_at=claude.created_at,
        last_updated=claude.last_updated,
    )


def _hybrid_context_to_response(hybrid: HybridContext) -> HybridContextResponse:
    """Convert HybridContext to response schema."""
    return HybridContextResponse(
        context_id=hybrid.context_id,
        maf=_maf_context_to_response(hybrid.maf) if hybrid.maf else None,
        claude=_claude_context_to_response(hybrid.claude) if hybrid.claude else None,
        primary_framework=hybrid.primary_framework,
        sync_status=hybrid.sync_status.value,
        version=hybrid.version,
        created_at=hybrid.created_at,
        updated_at=hybrid.updated_at,
        last_sync_at=hybrid.last_sync_at,
        sync_error=hybrid.sync_error,
    )


# =============================================================================
# API Routes
# =============================================================================


@router.get(
    "/{session_id}",
    response_model=HybridContextResponse,
    summary="Get hybrid context",
    description="Get the hybrid context for a session or workflow ID.",
)
async def get_hybrid_context(session_id: str):
    """
    Get hybrid context by session or workflow ID.

    Args:
        session_id: Session ID (Claude) or Workflow ID (MAF)

    Returns:
        HybridContextResponse: The hybrid context

    Raises:
        HTTPException: 404 if context not found
    """
    bridge = get_context_bridge()
    logger.info(f"get_hybrid_context({session_id}): bridge._context_cache keys = {list(bridge._context_cache.keys())}")
    hybrid = await bridge.get_hybrid_context(session_id)
    logger.info(f"get_hybrid_context({session_id}): hybrid = {hybrid}")

    if hybrid is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hybrid context not found for session: {session_id}"
        )

    if hybrid.maf:
        logger.info(f"get_hybrid_context({session_id}): maf.metadata = {hybrid.maf.metadata}")

    return _hybrid_context_to_response(hybrid)


@router.get(
    "/{session_id}/status",
    summary="Get sync status",
    description="Get the synchronization status for a session.",
)
async def get_sync_status(session_id: str):
    """
    Get sync status for a session.

    Args:
        session_id: Session or workflow ID

    Returns:
        dict: Sync status information
    """
    bridge = get_context_bridge()
    hybrid = await bridge.get_hybrid_context(session_id)

    if hybrid is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Context not found for session: {session_id}"
        )

    return {
        "session_id": session_id,
        "sync_status": hybrid.sync_status.value,
        "is_synced": hybrid.is_synced(),
        "has_conflict": hybrid.has_conflict(),
        "version": hybrid.version,
        "last_sync_at": hybrid.last_sync_at.isoformat() if hybrid.last_sync_at else None,
        "sync_error": hybrid.sync_error,
    }


@router.post(
    "/sync",
    response_model=SyncResultResponse,
    summary="Trigger sync",
    description="Trigger a manual synchronization between MAF and Claude contexts.",
)
async def trigger_sync(request: SyncRequest):
    """
    Trigger manual sync operation.

    If no hybrid context exists for the session, one will be auto-created
    with minimal MAF and Claude contexts.

    Args:
        request: Sync request with session_id, strategy, and direction

    Returns:
        SyncResultResponse: Result of the sync operation

    Raises:
        HTTPException: 400 if invalid parameters
    """
    bridge = get_context_bridge()
    synchronizer = get_synchronizer()

    # Get existing hybrid context or create new one
    hybrid = await bridge.get_hybrid_context(request.session_id)

    if hybrid is None:
        # Auto-create hybrid context for this session
        logger.info(f"Auto-creating hybrid context for session: {request.session_id}")
        logger.info(f"DEBUG: request.state_data = {request.state_data}")

        # Extract state data if provided
        state = request.state_data or {}
        logger.info(f"DEBUG: state = {state}")
        maf_vars = state.get("variables", {})
        claude_vars = state.get("context_variables", {})
        logger.info(f"DEBUG: initial maf_vars = {maf_vars}, claude_vars = {claude_vars}")

        # If direction is maf_to_claude, put state variables in MAF context
        # If direction is claude_to_maf, put state variables in Claude context
        if request.direction == "maf_to_claude":
            # MAF state data - copy variables to MAF context metadata
            maf_vars = state.get("variables", maf_vars)
            # Also copy MAF variables to Claude context for sync
            claude_vars = maf_vars.copy() if maf_vars else claude_vars
        elif request.direction == "claude_to_maf":
            # Claude state data - copy context_variables
            claude_vars = state.get("context_variables", claude_vars)
            # Also copy Claude variables to MAF for sync
            maf_vars = claude_vars.copy() if claude_vars else maf_vars

        logger.info(f"DEBUG: after direction logic maf_vars = {maf_vars}, claude_vars = {claude_vars}")
        # Create contexts with state data
        # Note: sync_to_claude uses checkpoint_data for conversion to context_variables
        # So we put variables in BOTH checkpoint_data (for sync) and metadata (for API response)
        maf_context = MAFContext(
            workflow_id=state.get("workflow_id", request.session_id),
            workflow_name=state.get("workflow_name", f"Workflow-{request.session_id}"),
            current_step=state.get("current_step", 0),
            total_steps=state.get("total_steps", 0),
            checkpoint_data=maf_vars,  # For sync operation
            metadata=maf_vars.copy() if maf_vars else {},  # For API response
            created_at=datetime.utcnow(),
        )
        claude_context = ClaudeContext(
            session_id=request.session_id,
            context_variables=claude_vars,
            created_at=datetime.utcnow(),
        )

        # Determine primary framework based on direction
        primary_framework = "maf" if request.direction == "maf_to_claude" else "claude"

        # Create hybrid context via merge
        hybrid = await bridge.merge_contexts(
            maf_context=maf_context,
            claude_context=claude_context,
            primary_framework=primary_framework,
        )

    # Parse strategy
    try:
        strategy = SyncStrategy(request.strategy)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sync strategy: {request.strategy}. "
                   f"Valid options: merge, source_wins, target_wins, maf_primary, claude_primary, manual"
        )

    # Parse direction
    try:
        direction = SyncDirection(request.direction)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sync direction: {request.direction}. "
                   f"Valid options: maf_to_claude, claude_to_maf, bidirectional"
        )

    logger.info(
        f"Triggering sync for session {request.session_id} "
        f"with strategy={strategy.value}, direction={direction.value}"
    )

    # Convert direction to target_type for synchronizer
    # maf_to_claude → target is claude
    # claude_to_maf → target is maf
    # bidirectional → default to claude (will sync both ways internally)
    if direction == SyncDirection.MAF_TO_CLAUDE:
        target_type = "claude"
    elif direction == SyncDirection.CLAUDE_TO_MAF:
        target_type = "maf"
    else:  # BIDIRECTIONAL
        target_type = "claude"  # Start with maf→claude, then sync back

    # Execute sync
    result = await synchronizer.sync(
        source=hybrid,
        target_type=target_type,
        strategy=strategy,
    )

    return SyncResultResponse(
        success=result.success,
        direction=result.direction.value,
        strategy=result.strategy.value,
        source_version=result.source_version,
        target_version=result.target_version,
        changes_applied=result.changes_applied,
        conflicts_resolved=result.conflicts_resolved,
        conflicts=[
            {
                "conflict_id": c.conflict_id,
                "field_path": c.field_path,
                "local_value": c.local_value,
                "remote_value": c.remote_value,
                "local_timestamp": c.local_timestamp,
                "remote_timestamp": c.remote_timestamp,
                "resolution": c.resolution,
                "resolved": c.resolved,
            }
            for c in result.conflicts
        ],
        hybrid_context=_hybrid_context_to_response(result.hybrid_context) if result.hybrid_context else None,
        error=result.error,
        started_at=result.started_at,
        completed_at=result.completed_at,
        duration_ms=result.duration_ms,
    )


@router.post(
    "/merge",
    response_model=HybridContextResponse,
    summary="Merge contexts",
    description="Merge MAF and Claude contexts into a hybrid context.",
)
async def merge_contexts(request: MergeContextRequest):
    """
    Merge MAF and Claude contexts.

    Args:
        request: Merge request with workflow and session IDs

    Returns:
        HybridContextResponse: The merged hybrid context

    Raises:
        HTTPException: 400 if both IDs are missing
    """
    if not request.maf_workflow_id and not request.claude_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of maf_workflow_id or claude_session_id must be provided"
        )

    bridge = get_context_bridge()

    # Create placeholder contexts if IDs provided
    # In a real implementation, these would be fetched from respective services
    maf_context = None
    claude_context = None

    if request.maf_workflow_id:
        # Create a minimal MAF context (would be fetched from MAF service)
        from datetime import datetime
        maf_context = MAFContext(
            workflow_id=request.maf_workflow_id,
            workflow_name=f"Workflow-{request.maf_workflow_id}",
            created_at=datetime.utcnow(),
        )

    if request.claude_session_id:
        # Create a minimal Claude context (would be fetched from Claude service)
        from datetime import datetime
        claude_context = ClaudeContext(
            session_id=request.claude_session_id,
            created_at=datetime.utcnow(),
        )

    # Merge contexts
    hybrid = await bridge.merge_contexts(
        maf_context=maf_context,
        claude_context=claude_context,
        primary_framework=request.primary_framework,
    )

    logger.info(
        f"Merged contexts: maf={request.maf_workflow_id}, "
        f"claude={request.claude_session_id}, "
        f"primary={request.primary_framework}"
    )

    return _hybrid_context_to_response(hybrid)


@router.get(
    "",
    summary="List hybrid contexts",
    description="List all cached hybrid contexts.",
)
async def list_hybrid_contexts(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of items to return"),
):
    """
    List all cached hybrid contexts.

    Args:
        skip: Number of items to skip
        limit: Maximum number of items to return

    Returns:
        dict: List of hybrid contexts with pagination info
    """
    bridge = get_context_bridge()

    # Get all cached contexts
    all_contexts = list(bridge._context_cache.values())
    total = len(all_contexts)

    # Apply pagination
    contexts = all_contexts[skip:skip + limit]

    return {
        "data": [_hybrid_context_to_response(h) for h in contexts],
        "total": total,
        "page": (skip // limit) + 1,
        "page_size": limit,
    }

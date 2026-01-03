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

_context_bridge: Optional[ContextBridge] = None
_synchronizer: Optional[ContextSynchronizer] = None
_event_publisher: Optional[SyncEventPublisher] = None


def get_context_bridge() -> ContextBridge:
    """Get or create ContextBridge singleton."""
    global _context_bridge
    if _context_bridge is None:
        _context_bridge = ContextBridge()
    return _context_bridge


def get_synchronizer() -> ContextSynchronizer:
    """Get or create ContextSynchronizer singleton."""
    global _synchronizer, _event_publisher
    if _synchronizer is None:
        _event_publisher = SyncEventPublisher()
        _synchronizer = ContextSynchronizer(
            bridge=get_context_bridge(),
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
    hybrid = await bridge.get_hybrid_context(session_id)

    if hybrid is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hybrid context not found for session: {session_id}"
        )

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

    Args:
        request: Sync request with session_id, strategy, and direction

    Returns:
        SyncResultResponse: Result of the sync operation

    Raises:
        HTTPException: 404 if context not found, 400 if invalid parameters
    """
    bridge = get_context_bridge()
    synchronizer = get_synchronizer()

    # Get existing hybrid context
    hybrid = await bridge.get_hybrid_context(request.session_id)

    if hybrid is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Context not found for session: {request.session_id}"
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

    # Execute sync
    result = await synchronizer.sync(
        hybrid_context=hybrid,
        strategy=strategy,
        direction=direction,
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

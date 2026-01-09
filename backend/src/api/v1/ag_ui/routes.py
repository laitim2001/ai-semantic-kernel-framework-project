# =============================================================================
# IPA Platform - AG-UI API Routes (Updated: 2026-01-08)
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-1: AG-UI SSE Endpoint
# Sprint 59: AG-UI Basic Features
# S59-3: Human-in-the-Loop Approval Endpoints
# Sprint 60: AG-UI Advanced Features
# S60-2: Shared State Management Endpoints
# Sprint 68: S68-4 - History API Implementation
#
# REST API endpoints for AG-UI protocol integration.
# Provides SSE streaming endpoint compatible with CopilotKit frontend.
#
# Main endpoints:
# - POST /api/v1/ag-ui - Run agent (SSE stream)
# - POST /api/v1/ag-ui/approvals/{id}/approve - Approve tool call
# - POST /api/v1/ag-ui/approvals/{id}/reject - Reject tool call
# - GET /api/v1/ag-ui/approvals/pending - List pending approvals
# - GET /api/v1/ag-ui/threads/{id}/state - Get thread state
# - PATCH /api/v1/ag-ui/threads/{id}/state - Update thread state
#
# Dependencies:
#   - HybridEventBridge (src.integrations.ag_ui.bridge)
#   - AG-UI Events (src.integrations.ag_ui.events)
#   - HITLHandler (src.integrations.ag_ui.features.human_in_loop)
#   - SharedStateHandler (src.integrations.ag_ui.features.advanced)
# =============================================================================

import logging
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from src.api.v1.ag_ui.dependencies import (
    get_hybrid_bridge,
    get_bridge_status,
    reset_hybrid_bridge,
)
from src.api.v1.ag_ui.schemas import (
    AGUIExecutionMode,
    ApprovalActionRequest,
    ApprovalActionResponse,
    ApprovalResponse,
    ApprovalStatusEnum,
    ApprovalStorageStats,
    ConflictResolutionStrategyEnum,
    DiffOperationEnum,
    ErrorResponse,
    HealthResponse,
    ModeSwitchEventResponse,
    PendingApprovalsResponse,
    RiskLevelEnum,
    RunAgentRequest,
    RunAgentResponse,
    StateConflictResponse,
    StateDiffSchema,
    StateUpdateResponse,
    TestModeSwitchRequest,
    TestUIComponentRequest,
    TestWorkflowProgressRequest,
    ThreadStateResponse,
    ThreadStateUpdateRequest,
    UIComponentEventResponse,
    UIComponentTypeEnum,
    WorkflowProgressEventResponse,
    WorkflowStepStatusEnum,
)
from src.integrations.ag_ui.bridge import (
    HybridEventBridge,
    RunAgentInput,
)
from src.integrations.ag_ui.features.human_in_loop import (
    ApprovalStorage,
    ApprovalStatus,
    HITLHandler,
    get_approval_storage,
    get_hitl_handler,
)
from src.integrations.hybrid.intent import ExecutionMode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ag-ui", tags=["ag-ui"])


# =============================================================================
# Health Check
# =============================================================================


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="AG-UI Health Check",
    description="Check if AG-UI endpoint is available and functioning.",
)
async def health_check() -> HealthResponse:
    """
    Health check endpoint for AG-UI protocol.

    Returns:
        HealthResponse with status and version information.
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        protocol="ag-ui",
        features=[
            "agentic_chat",
            "tool_rendering",
            "human_in_loop",
            "generative_ui",
            "tool_based_ui",
            "shared_state",
            "predictive_state",
        ],
    )


@router.get(
    "/status",
    summary="AG-UI Bridge Status",
    description="Get current status of HybridEventBridge and Claude SDK.",
)
async def bridge_status() -> Dict[str, Any]:
    """
    Get status of AG-UI bridge components.

    Returns:
        Dict with status information including:
        - api_key_configured: Whether ANTHROPIC_API_KEY is set
        - claude_client_initialized: Whether ClaudeSDKClient is created
        - bridge_initialized: Whether HybridEventBridge is created
        - orchestrator_configured: Whether HybridOrchestratorV2 is configured
        - claude_executor_enabled: Whether claude_executor is available
    """
    return get_bridge_status()


@router.post(
    "/reset",
    summary="Reset AG-UI Bridge",
    description="Reset HybridEventBridge and re-initialize with fresh Claude executor.",
)
async def reset_bridge() -> Dict[str, Any]:
    """
    Reset AG-UI bridge and force re-creation of all components.

    Useful when:
    - Environment variables have changed
    - Debugging Claude SDK connection issues
    - Forcing fresh initialization after errors

    Returns:
        Dict with reset status and diagnostics
    """
    return reset_hybrid_bridge()


# =============================================================================
# Mode Mapping
# =============================================================================

def map_execution_mode(mode: AGUIExecutionMode) -> Optional[ExecutionMode]:
    """
    Map AG-UI execution mode to internal ExecutionMode.

    Args:
        mode: AG-UI execution mode

    Returns:
        Internal ExecutionMode or None for auto-detection
    """
    mapping = {
        AGUIExecutionMode.WORKFLOW: ExecutionMode.WORKFLOW_MODE,
        AGUIExecutionMode.CHAT: ExecutionMode.CHAT_MODE,
        AGUIExecutionMode.HYBRID: ExecutionMode.HYBRID_MODE,
        AGUIExecutionMode.AUTO: None,
    }
    return mapping.get(mode)


# =============================================================================
# SSE Streaming Helper
# =============================================================================

async def generate_sse_stream(
    bridge: HybridEventBridge,
    run_input: RunAgentInput,
) -> AsyncGenerator[str, None]:
    """
    Generate SSE stream from HybridEventBridge.

    Args:
        bridge: HybridEventBridge instance
        run_input: Input for running the agent

    Yields:
        SSE-formatted event strings
    """
    try:
        async for sse_event in bridge.stream_events(run_input):
            yield sse_event

    except ValueError as e:
        # Orchestrator not configured - yield error event
        error_event = bridge.create_run_finished(
            thread_id=run_input.thread_id,
            run_id=run_input.run_id or f"run-{uuid.uuid4().hex[:12]}",
            success=False,
            error=str(e),
        )
        yield bridge.format_event(error_event)

    except Exception as e:
        logger.error(f"SSE stream error: {e}", exc_info=True)
        error_event = bridge.create_run_finished(
            thread_id=run_input.thread_id,
            run_id=run_input.run_id or f"run-{uuid.uuid4().hex[:12]}",
            success=False,
            error=f"Internal error: {str(e)}",
        )
        yield bridge.format_event(error_event)


# =============================================================================
# API Endpoints
# =============================================================================

@router.post(
    "",
    summary="Run Agent (SSE Stream)",
    description="""
    Run an agent with AG-UI protocol streaming response.

    This endpoint follows the CopilotKit AG-UI protocol specification.
    The response is streamed as Server-Sent Events (SSE).

    ## Event Types

    - `RUN_STARTED`: Indicates the run has started
    - `TEXT_MESSAGE_START`: Start of a text message
    - `TEXT_MESSAGE_CONTENT`: Text content delta
    - `TEXT_MESSAGE_END`: End of a text message
    - `TOOL_CALL_START`: Start of a tool call
    - `TOOL_CALL_END`: End of a tool call (with result)
    - `RUN_FINISHED`: Indicates the run has completed

    ## SSE Format

    ```
    data: {"type": "RUN_STARTED", ...}

    data: {"type": "TEXT_MESSAGE_START", ...}

    ...
    ```
    """,
    responses={
        200: {
            "description": "SSE stream of AG-UI events",
            "content": {"text/event-stream": {}},
        },
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def run_agent(
    request: RunAgentRequest,
    bridge: HybridEventBridge = Depends(get_hybrid_bridge),
) -> StreamingResponse:
    """
    Run agent with AG-UI protocol streaming.

    Receives a RunAgentRequest and streams AG-UI events back
    as Server-Sent Events (SSE).
    """
    # Validate request
    if not request.thread_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INVALID_REQUEST",
                "message": "thread_id is required",
            },
        )

    # Extract last user message as prompt
    prompt = ""
    if request.messages:
        for msg in reversed(request.messages):
            if msg.role == "user":
                prompt = msg.content
                break

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INVALID_REQUEST",
                "message": "No user message found in messages",
            },
        )

    # Convert tools to dict format
    tools_dict: Optional[List[Dict[str, Any]]] = None
    if request.tools:
        tools_dict = [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
            for tool in request.tools
        ]

    # S75-5: Extract file IDs from attachments
    file_ids = None
    # Debug: Always log attachments status
    logger.info(f"[S75-5] Request attachments field: {request.attachments}")
    if request.attachments:
        file_ids = [a.file_id for a in request.attachments]
        logger.info(f"[S75-5] Received attachments: {file_ids}")
    else:
        logger.info("[S75-5] No attachments in request (attachments is None or empty)")

    # Create RunAgentInput
    run_input = RunAgentInput(
        prompt=prompt,
        thread_id=request.thread_id,
        run_id=request.run_id,
        session_id=request.session_id,
        force_mode=map_execution_mode(request.mode),
        tools=tools_dict,
        max_tokens=request.max_tokens,
        timeout=request.timeout,
        metadata=request.metadata,
        file_ids=file_ids,  # S75-5: Pass file IDs
    )

    logger.info(
        f"AG-UI run_agent: thread_id={request.thread_id}, "
        f"run_id={run_input.run_id}, mode={request.mode.value}"
        f"{', attachments=' + str(len(file_ids)) if file_ids else ''}"
    )

    # Return streaming response
    return StreamingResponse(
        generate_sse_stream(bridge, run_input),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/sync",
    response_model=RunAgentResponse,
    summary="Run Agent (Synchronous)",
    description="Run an agent synchronously without streaming. Returns complete response.",
    responses={
        200: {"description": "Complete agent response"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def run_agent_sync(
    request: RunAgentRequest,
    bridge: HybridEventBridge = Depends(get_hybrid_bridge),
) -> RunAgentResponse:
    """
    Run agent synchronously (non-streaming).

    Collects all events and returns a complete response.
    Useful for simple integrations that don't support SSE.
    """
    # Validate request
    if not request.thread_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INVALID_REQUEST",
                "message": "thread_id is required",
            },
        )

    # Extract last user message as prompt
    prompt = ""
    if request.messages:
        for msg in reversed(request.messages):
            if msg.role == "user":
                prompt = msg.content
                break

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INVALID_REQUEST",
                "message": "No user message found in messages",
            },
        )

    # Convert tools to dict format
    tools_dict: Optional[List[Dict[str, Any]]] = None
    if request.tools:
        tools_dict = [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
            for tool in request.tools
        ]

    # S75-5: Extract file IDs from attachments
    file_ids_sync = None
    if request.attachments:
        file_ids_sync = [a.file_id for a in request.attachments]

    # Create RunAgentInput
    run_input = RunAgentInput(
        prompt=prompt,
        thread_id=request.thread_id,
        run_id=request.run_id,
        session_id=request.session_id,
        force_mode=map_execution_mode(request.mode),
        tools=tools_dict,
        max_tokens=request.max_tokens,
        timeout=request.timeout,
        metadata=request.metadata,
        file_ids=file_ids_sync,  # S75-5: Pass file IDs
    )

    logger.info(
        f"AG-UI run_agent_sync: thread_id={request.thread_id}, "
        f"run_id={run_input.run_id}, mode={request.mode.value}"
        f"{', attachments=' + str(len(file_ids_sync)) if file_ids_sync else ''}"
    )

    try:
        # Collect all events
        events = await bridge.execute_and_collect(run_input)

        # Extract content and tool calls from events
        content_parts: List[str] = []
        tool_calls: List[Dict[str, Any]] = []
        error_message: Optional[str] = None
        success = True

        from src.integrations.ag_ui.events import (
            AGUIEventType,
            TextMessageContentEvent,
            ToolCallEndEvent,
            RunFinishedEvent,
        )

        for event in events:
            if event.type == AGUIEventType.TEXT_MESSAGE_CONTENT:
                if isinstance(event, TextMessageContentEvent) and event.delta:
                    content_parts.append(event.delta)

            elif event.type == AGUIEventType.TOOL_CALL_END:
                if isinstance(event, ToolCallEndEvent):
                    tool_calls.append({
                        "id": event.tool_call_id,
                        "name": event.tool_name,
                        "result": event.result,
                        "error": event.error,
                    })

            elif event.type == AGUIEventType.RUN_FINISHED:
                if isinstance(event, RunFinishedEvent):
                    from src.integrations.ag_ui.events import RunFinishReason
                    if event.finish_reason in (RunFinishReason.ERROR, "error"):
                        success = False
                        error_message = event.error

        return RunAgentResponse(
            thread_id=request.thread_id,
            run_id=run_input.run_id or "",
            status="success" if success else "error",
            content="".join(content_parts),
            tool_calls=tool_calls,
            error=error_message,
            metadata=request.metadata,
            created_at=datetime.utcnow(),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "BRIDGE_NOT_CONFIGURED",
                "message": str(e),
            },
        )

    except Exception as e:
        logger.error(f"Sync execution error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "EXECUTION_ERROR",
                "message": f"Internal error: {str(e)}",
            },
        )


@router.get(
    "/threads/{thread_id}/history",
    summary="Get Thread History",
    description="Get conversation history for a thread with pagination.",
    responses={
        200: {"description": "Thread history with messages"},
        404: {"model": ErrorResponse, "description": "Thread not found"},
    },
)
async def get_thread_history(
    thread_id: str,
    offset: int = Query(0, ge=0, description="Number of messages to skip"),
    limit: int = Query(50, ge=1, le=200, description="Maximum messages to return"),
    bridge: HybridEventBridge = Depends(get_hybrid_bridge),
) -> Dict[str, Any]:
    """
    Get thread conversation history.

    Sprint 68: S68-4 - Full implementation with pagination.

    Retrieves messages from the session/thread with:
    - Pagination support (offset, limit)
    - Tool calls included
    - Approval states included
    - Sorted by timestamp (oldest first for display)

    Args:
        thread_id: Thread/Session identifier
        offset: Number of messages to skip
        limit: Maximum messages to return
        bridge: HybridEventBridge for thread management

    Returns:
        Thread history with paginated messages
    """
    try:
        # Get thread manager from bridge if available
        thread_manager = getattr(bridge, "_thread_manager", None)

        if thread_manager:
            # Try to get thread state
            thread_state = await thread_manager.get_thread(thread_id)
            if not thread_state:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"error": "THREAD_NOT_FOUND", "message": f"Thread {thread_id} not found"},
                )

            # Get messages from thread state
            all_messages = thread_state.get("messages", [])
            total = len(all_messages)

            # Apply pagination (oldest first for display)
            paginated_messages = all_messages[offset : offset + limit]

            # Format messages for response
            formatted_messages = []
            for msg in paginated_messages:
                formatted_messages.append({
                    "id": msg.get("id", str(uuid.uuid4())),
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                    "tool_calls": msg.get("tool_calls", []),
                    "approval_state": msg.get("approval_state"),
                    "created_at": msg.get("created_at", datetime.utcnow().isoformat()),
                })

            return {
                "thread_id": thread_id,
                "messages": formatted_messages,
                "pagination": {
                    "offset": offset,
                    "limit": limit,
                    "total": total,
                    "has_more": offset + limit < total,
                },
            }

        # Fallback: Return empty history if no thread manager
        # This supports simulation mode and initial setup
        logger.warning(f"No thread manager available for history lookup: {thread_id}")
        return {
            "thread_id": thread_id,
            "messages": [],
            "pagination": {
                "offset": offset,
                "limit": limit,
                "total": 0,
                "has_more": False,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting thread history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "HISTORY_ERROR", "message": str(e)},
        )


# =============================================================================
# S59-3: Human-in-the-Loop Approval Endpoints
# =============================================================================

def _convert_approval_to_response(request) -> ApprovalResponse:
    """Convert ApprovalRequest to ApprovalResponse schema."""
    from src.integrations.hybrid.risk import RiskLevel

    # Map internal RiskLevel to API enum
    risk_level_map = {
        RiskLevel.LOW: RiskLevelEnum.LOW,
        RiskLevel.MEDIUM: RiskLevelEnum.MEDIUM,
        RiskLevel.HIGH: RiskLevelEnum.HIGH,
        RiskLevel.CRITICAL: RiskLevelEnum.CRITICAL,
    }

    # Map internal ApprovalStatus to API enum
    status_map = {
        ApprovalStatus.PENDING: ApprovalStatusEnum.PENDING,
        ApprovalStatus.APPROVED: ApprovalStatusEnum.APPROVED,
        ApprovalStatus.REJECTED: ApprovalStatusEnum.REJECTED,
        ApprovalStatus.TIMEOUT: ApprovalStatusEnum.TIMEOUT,
        ApprovalStatus.CANCELLED: ApprovalStatusEnum.CANCELLED,
    }

    return ApprovalResponse(
        approval_id=request.approval_id,
        tool_call_id=request.tool_call_id,
        tool_name=request.tool_name,
        arguments=request.arguments,
        risk_level=risk_level_map.get(request.risk_level, RiskLevelEnum.MEDIUM),
        risk_score=request.risk_score,
        reasoning=request.reasoning,
        run_id=request.run_id,
        session_id=request.session_id,
        status=status_map.get(request.status, ApprovalStatusEnum.PENDING),
        created_at=request.created_at,
        expires_at=request.expires_at,
        resolved_at=request.resolved_at,
        user_comment=request.user_comment,
    )


@router.get(
    "/approvals/pending",
    response_model=PendingApprovalsResponse,
    summary="List Pending Approvals",
    description="""
    Get all pending approval requests.

    Optionally filter by session_id or run_id.
    Expired requests are automatically marked as timeout.
    """,
    responses={
        200: {"description": "List of pending approvals"},
    },
)
async def list_pending_approvals(
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    run_id: Optional[str] = Query(None, description="Filter by run ID"),
    storage: ApprovalStorage = Depends(get_approval_storage),
) -> PendingApprovalsResponse:
    """
    List all pending approval requests.

    Returns requests sorted by creation time (oldest first).
    """
    pending = await storage.get_pending(session_id=session_id, run_id=run_id)

    return PendingApprovalsResponse(
        pending=[_convert_approval_to_response(r) for r in pending],
        total=len(pending),
    )


@router.get(
    "/approvals/stats",
    response_model=ApprovalStorageStats,
    summary="Get Approval Statistics",
    description="Get statistics about approval storage (counts by status).",
    responses={
        200: {"description": "Approval statistics"},
    },
)
async def get_approval_stats(
    storage: ApprovalStorage = Depends(get_approval_storage),
) -> ApprovalStorageStats:
    """
    Get approval storage statistics.
    """
    stats = storage.get_stats()
    return ApprovalStorageStats(**stats)


@router.get(
    "/approvals/{approval_id}",
    response_model=ApprovalResponse,
    summary="Get Approval Request",
    description="Get details of a specific approval request by ID.",
    responses={
        200: {"description": "Approval request details"},
        404: {"model": ErrorResponse, "description": "Approval not found"},
    },
)
async def get_approval(
    approval_id: str,
    storage: ApprovalStorage = Depends(get_approval_storage),
) -> ApprovalResponse:
    """
    Get a specific approval request by ID.
    """
    request = await storage.get(approval_id)

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "APPROVAL_NOT_FOUND",
                "message": f"Approval request not found: {approval_id}",
            },
        )

    return _convert_approval_to_response(request)


@router.post(
    "/approvals/{approval_id}/approve",
    response_model=ApprovalActionResponse,
    summary="Approve Tool Call",
    description="""
    Approve a pending tool call request.

    The tool call will be executed after approval.
    An optional comment can be provided for audit purposes.
    """,
    responses={
        200: {"description": "Approval action successful"},
        400: {"model": ErrorResponse, "description": "Request already resolved or expired"},
        404: {"model": ErrorResponse, "description": "Approval not found"},
    },
)
async def approve_tool_call(
    approval_id: str,
    body: Optional[ApprovalActionRequest] = None,
    hitl: HITLHandler = Depends(get_hitl_handler),
) -> ApprovalActionResponse:
    """
    Approve a pending tool call.
    """
    comment = body.comment if body else None

    success, request = await hitl.handle_approval_response(
        approval_id=approval_id,
        approved=True,
        user_comment=comment,
    )

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "APPROVAL_NOT_FOUND",
                "message": f"Approval request not found: {approval_id}",
            },
        )

    if not success:
        # Request was already resolved or expired
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "APPROVAL_ALREADY_RESOLVED",
                "message": f"Approval request already resolved or expired: {approval_id}",
                "details": {"status": request.status.value},
            },
        )

    logger.info(f"Tool call approved: {approval_id}")

    return ApprovalActionResponse(
        success=True,
        approval_id=approval_id,
        status=ApprovalStatusEnum.APPROVED,
        message="Tool call approved successfully",
        resolved_at=request.resolved_at,
    )


@router.post(
    "/approvals/{approval_id}/reject",
    response_model=ApprovalActionResponse,
    summary="Reject Tool Call",
    description="""
    Reject a pending tool call request.

    The tool call will not be executed.
    An optional comment can be provided explaining the rejection.
    """,
    responses={
        200: {"description": "Rejection action successful"},
        400: {"model": ErrorResponse, "description": "Request already resolved or expired"},
        404: {"model": ErrorResponse, "description": "Approval not found"},
    },
)
async def reject_tool_call(
    approval_id: str,
    body: Optional[ApprovalActionRequest] = None,
    hitl: HITLHandler = Depends(get_hitl_handler),
) -> ApprovalActionResponse:
    """
    Reject a pending tool call.
    """
    comment = body.comment if body else None

    success, request = await hitl.handle_approval_response(
        approval_id=approval_id,
        approved=False,
        user_comment=comment,
    )

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "APPROVAL_NOT_FOUND",
                "message": f"Approval request not found: {approval_id}",
            },
        )

    if not success:
        # Request was already resolved or expired
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "APPROVAL_ALREADY_RESOLVED",
                "message": f"Approval request already resolved or expired: {approval_id}",
                "details": {"status": request.status.value},
            },
        )

    logger.info(f"Tool call rejected: {approval_id}")

    return ApprovalActionResponse(
        success=True,
        approval_id=approval_id,
        status=ApprovalStatusEnum.REJECTED,
        message="Tool call rejected",
        resolved_at=request.resolved_at,
    )


@router.post(
    "/approvals/{approval_id}/cancel",
    response_model=ApprovalActionResponse,
    summary="Cancel Approval Request",
    description="Cancel a pending approval request without executing the tool call.",
    responses={
        200: {"description": "Cancellation successful"},
        400: {"model": ErrorResponse, "description": "Request already resolved"},
        404: {"model": ErrorResponse, "description": "Approval not found"},
    },
)
async def cancel_approval(
    approval_id: str,
    storage: ApprovalStorage = Depends(get_approval_storage),
) -> ApprovalActionResponse:
    """
    Cancel a pending approval request.
    """
    success = await storage.cancel(approval_id)

    if not success:
        request = await storage.get(approval_id)
        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "APPROVAL_NOT_FOUND",
                    "message": f"Approval request not found: {approval_id}",
                },
            )
        # Request was already resolved
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "APPROVAL_ALREADY_RESOLVED",
                "message": f"Approval request already resolved: {approval_id}",
                "details": {"status": request.status.value},
            },
        )

    logger.info(f"Approval request cancelled: {approval_id}")

    return ApprovalActionResponse(
        success=True,
        approval_id=approval_id,
        status=ApprovalStatusEnum.CANCELLED,
        message="Approval request cancelled",
        resolved_at=datetime.utcnow(),
    )


# =============================================================================
# S60-2: Shared State Management Endpoints
# =============================================================================

# In-memory state storage for demo purposes
# In production, this should use Redis or database
_thread_states: Dict[str, Dict[str, Any]] = {}
_thread_versions: Dict[str, int] = {}
_thread_timestamps: Dict[str, datetime] = {}


def _get_thread_state_storage() -> Dict[str, Dict[str, Any]]:
    """Get thread state storage (dependency injection point)."""
    return _thread_states


def _get_thread_version(thread_id: str) -> int:
    """Get current version for a thread."""
    return _thread_versions.get(thread_id, 0)


def _increment_version(thread_id: str) -> int:
    """Increment and return new version for a thread."""
    current = _thread_versions.get(thread_id, 0)
    new_version = current + 1
    _thread_versions[thread_id] = new_version
    return new_version


def _apply_diff_to_state(
    state: Dict[str, Any],
    diff: StateDiffSchema,
) -> Dict[str, Any]:
    """
    Apply a single diff operation to state.

    Args:
        state: Current state
        diff: Diff operation to apply

    Returns:
        Updated state
    """
    import copy
    state = copy.deepcopy(state)
    path_parts = diff.path.split(".")

    if diff.op == DiffOperationEnum.ADD or diff.op == DiffOperationEnum.REPLACE:
        # Navigate to parent and set value
        current = state
        for part in path_parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[path_parts[-1]] = diff.new_value

    elif diff.op == DiffOperationEnum.REMOVE:
        # Navigate to parent and remove key
        current = state
        for part in path_parts[:-1]:
            if part not in current:
                return state  # Path doesn't exist
            current = current[part]
        if path_parts[-1] in current:
            del current[path_parts[-1]]

    return state


@router.get(
    "/threads/{thread_id}/state",
    response_model=ThreadStateResponse,
    summary="Get Thread State",
    description="""
    Get the current state for a thread.

    Returns the full state snapshot including version number
    for optimistic concurrency control.
    """,
    responses={
        200: {"description": "Thread state"},
        404: {"model": ErrorResponse, "description": "Thread not found"},
    },
)
async def get_thread_state(
    thread_id: str,
) -> ThreadStateResponse:
    """
    Get current thread state.

    Returns state data, version, and metadata for the specified thread.
    """
    state = _thread_states.get(thread_id, {})
    version = _get_thread_version(thread_id)
    last_modified = _thread_timestamps.get(thread_id, datetime.utcnow())

    return ThreadStateResponse(
        thread_id=thread_id,
        state=state,
        version=version,
        last_modified=last_modified,
        metadata={"source": "backend"},
    )


@router.patch(
    "/threads/{thread_id}/state",
    response_model=StateUpdateResponse,
    summary="Update Thread State",
    description="""
    Update thread state with full snapshot or delta diffs.

    Supports two update modes:
    - **Snapshot update**: Provide `state` to replace entire state
    - **Delta update**: Provide `diffs` to apply incremental changes

    Supports optimistic concurrency with `expected_version`.
    """,
    responses={
        200: {"description": "State updated successfully"},
        409: {"model": StateConflictResponse, "description": "Version conflict"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
    },
)
async def update_thread_state(
    thread_id: str,
    request: ThreadStateUpdateRequest,
) -> StateUpdateResponse:
    """
    Update thread state with snapshot or diffs.
    """
    current_version = _get_thread_version(thread_id)

    # Check for version conflict if expected_version is provided
    if request.expected_version is not None:
        if request.expected_version != current_version:
            # Return conflict response
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "VERSION_CONFLICT",
                    "message": "State has been modified by another client",
                    "details": {
                        "server_version": current_version,
                        "client_version": request.expected_version,
                    },
                },
            )

    diffs_applied = 0
    conflicts_resolved = 0

    if request.state is not None:
        # Full snapshot update
        _thread_states[thread_id] = request.state
        diffs_applied = 1  # Treat snapshot as single diff

    elif request.diffs:
        # Delta update
        current_state = _thread_states.get(thread_id, {})

        for diff in request.diffs:
            current_state = _apply_diff_to_state(current_state, diff)
            diffs_applied += 1

        _thread_states[thread_id] = current_state

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INVALID_REQUEST",
                "message": "Either 'state' or 'diffs' must be provided",
            },
        )

    # Update version and timestamp
    new_version = _increment_version(thread_id)
    now = datetime.utcnow()
    _thread_timestamps[thread_id] = now

    logger.info(
        f"Thread state updated: thread_id={thread_id}, "
        f"version={new_version}, diffs_applied={diffs_applied}"
    )

    return StateUpdateResponse(
        success=True,
        thread_id=thread_id,
        version=new_version,
        conflicts_resolved=conflicts_resolved,
        diffs_applied=diffs_applied,
        message="State updated successfully",
        updated_at=now,
    )


@router.delete(
    "/threads/{thread_id}/state",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear Thread State",
    description="Clear all state for a thread.",
    responses={
        204: {"description": "State cleared"},
    },
)
async def clear_thread_state(
    thread_id: str,
) -> None:
    """
    Clear thread state.

    Removes all state data and resets version to 0.
    """
    if thread_id in _thread_states:
        del _thread_states[thread_id]
    if thread_id in _thread_versions:
        del _thread_versions[thread_id]
    if thread_id in _thread_timestamps:
        del _thread_timestamps[thread_id]

    logger.info(f"Thread state cleared: thread_id={thread_id}")


# =============================================================================
# S61-6: Test Endpoints for Feature 4 & 5
# =============================================================================

@router.post(
    "/test/progress",
    response_model=WorkflowProgressEventResponse,
    summary="Test Workflow Progress Event (Feature 4)",
    description="""
    Generate a test workflow progress event for UAT testing.

    This endpoint simulates the workflow progress events that would be
    emitted during real workflow execution, enabling Feature 4 (Generative UI)
    testing without requiring actual workflow execution.
    """,
    tags=["ag-ui", "testing"],
    responses={
        200: {"description": "Workflow progress event generated"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
    },
)
async def test_workflow_progress(
    request: TestWorkflowProgressRequest,
) -> WorkflowProgressEventResponse:
    """
    Generate test workflow progress event.

    Creates a simulated workflow progress event for testing Feature 4
    (Generative UI - Progress Updates).
    """
    import time

    # Generate workflow ID
    workflow_id = f"wf-test-{uuid.uuid4().hex[:8]}"
    run_id = f"run-{uuid.uuid4().hex[:12]}"

    # Create step definitions
    steps = []
    for i in range(1, request.total_steps + 1):
        step_status = "completed" if i < request.current_step else (
            request.step_status.value if i == request.current_step else "pending"
        )
        steps.append({
            "step_id": f"step-{i}",
            "name": f"Step {i}",
            "status": step_status,
            "started_at": datetime.utcnow().isoformat() if step_status != "pending" else None,
            "completed_at": datetime.utcnow().isoformat() if step_status == "completed" else None,
        })

    # Calculate progress
    completed_steps = request.current_step - 1
    if request.step_status == WorkflowStepStatusEnum.COMPLETED:
        completed_steps = request.current_step
    overall_progress = completed_steps / request.total_steps

    # Build payload
    payload = {
        "workflow_id": workflow_id,
        "workflow_name": request.workflow_name,
        "total_steps": request.total_steps,
        "completed_steps": completed_steps,
        "current_step": steps[request.current_step - 1] if steps else None,
        "overall_progress": round(overall_progress, 2),
        "steps": steps,
        "started_at": datetime.utcnow().isoformat(),
        "run_id": run_id,
        "thread_id": request.thread_id,
    }

    logger.info(
        f"Test workflow progress: workflow_id={workflow_id}, "
        f"progress={overall_progress:.0%}"
    )

    return WorkflowProgressEventResponse(
        event_name="workflow_progress",
        payload=payload,
    )


@router.post(
    "/test/mode-switch",
    response_model=ModeSwitchEventResponse,
    summary="Test Mode Switch Event (Feature 4)",
    description="""
    Generate a test mode switch event for UAT testing.

    This endpoint simulates the mode switch events that would be emitted
    when the system switches between chat and workflow execution modes,
    enabling Feature 4 (Generative UI - Mode Switching) testing.
    """,
    tags=["ag-ui", "testing"],
    responses={
        200: {"description": "Mode switch event generated"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
    },
)
async def test_mode_switch(
    request: TestModeSwitchRequest,
) -> ModeSwitchEventResponse:
    """
    Generate test mode switch event.

    Creates a simulated mode switch event for testing Feature 4
    (Generative UI - Mode Switching).
    """
    # Generate switch ID
    switch_id = f"sw-test-{uuid.uuid4().hex[:8]}"
    run_id = f"run-{uuid.uuid4().hex[:12]}"

    # Build payload
    payload = {
        "switch_id": switch_id,
        "source_mode": request.source_mode,
        "target_mode": request.target_mode,
        "reason": request.reason,
        "trigger_type": "manual",
        "confidence": request.confidence,
        "message": f"Successfully switched from {request.source_mode} to {request.target_mode}",
        "success": True,
        "run_id": run_id,
        "thread_id": request.thread_id,
        "timestamp": datetime.utcnow().isoformat(),
    }

    logger.info(
        f"Test mode switch: {request.source_mode} -> {request.target_mode}, "
        f"confidence={request.confidence}"
    )

    return ModeSwitchEventResponse(
        event_name="mode_switch",
        payload=payload,
    )


@router.post(
    "/test/ui-component",
    response_model=UIComponentEventResponse,
    summary="Test UI Component Event (Feature 5)",
    description="""
    Generate a test UI component event for UAT testing.

    This endpoint simulates the dynamic UI component events that would be
    emitted when tools return UI schemas, enabling Feature 5 (Tool-based UI)
    testing without requiring actual tool execution.

    Supported component types:
    - **form**: Dynamic form with fields
    - **chart**: Data visualization (bar, line, pie, etc.)
    - **card**: Information card
    - **table**: Data table with columns
    - **custom**: Custom component
    """,
    tags=["ag-ui", "testing"],
    responses={
        200: {"description": "UI component event generated"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
    },
)
async def test_ui_component(
    request: TestUIComponentRequest,
) -> UIComponentEventResponse:
    """
    Generate test UI component event.

    Creates a simulated UI component event for testing Feature 5
    (Tool-based Dynamic UI).
    """
    import time

    # Generate component ID
    component_id = f"ui-test-{uuid.uuid4().hex[:12]}"

    # Validate props based on component type
    component_type = request.component_type.value

    if component_type == "form":
        # Ensure fields exist for form
        if "fields" not in request.props:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_PROPS",
                    "message": "Form component requires 'fields' in props",
                },
            )

    elif component_type == "chart":
        # Ensure chart has data
        if "data" not in request.props and "chartType" not in request.props:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_PROPS",
                    "message": "Chart component requires 'data' or 'chartType' in props",
                },
            )

    elif component_type == "table":
        # Ensure table has columns
        if "columns" not in request.props and "data" not in request.props:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_PROPS",
                    "message": "Table component requires 'columns' or 'data' in props",
                },
            )

    # Build component definition
    component = {
        "componentId": component_id,
        "componentType": component_type,
        "props": request.props,
        "title": request.title,
        "createdAt": time.time(),
        "threadId": request.thread_id,
    }

    logger.info(
        f"Test UI component: type={component_type}, id={component_id}"
    )

    return UIComponentEventResponse(
        event_name="ui_component",
        component=component,
    )

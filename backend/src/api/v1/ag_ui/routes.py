# =============================================================================
# IPA Platform - AG-UI API Routes
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-1: AG-UI SSE Endpoint
# Sprint 59: AG-UI Basic Features
# S59-3: Human-in-the-Loop Approval Endpoints
#
# REST API endpoints for AG-UI protocol integration.
# Provides SSE streaming endpoint compatible with CopilotKit frontend.
#
# Main endpoints:
# - POST /api/v1/ag-ui - Run agent (SSE stream)
# - POST /api/v1/ag-ui/approvals/{id}/approve - Approve tool call
# - POST /api/v1/ag-ui/approvals/{id}/reject - Reject tool call
# - GET /api/v1/ag-ui/approvals/pending - List pending approvals
#
# Dependencies:
#   - HybridEventBridge (src.integrations.ag_ui.bridge)
#   - AG-UI Events (src.integrations.ag_ui.events)
#   - HITLHandler (src.integrations.ag_ui.features.human_in_loop)
# =============================================================================

import logging
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from src.api.v1.ag_ui.dependencies import get_hybrid_bridge
from src.api.v1.ag_ui.schemas import (
    AGUIExecutionMode,
    ApprovalActionRequest,
    ApprovalActionResponse,
    ApprovalResponse,
    ApprovalStatusEnum,
    ApprovalStorageStats,
    ErrorResponse,
    HealthResponse,
    PendingApprovalsResponse,
    RiskLevelEnum,
    RunAgentRequest,
    RunAgentResponse,
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

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="AG-UI Health Check",
    description="Check the health status of the AG-UI endpoint",
)
async def health_check() -> HealthResponse:
    """
    AG-UI Health Check endpoint.

    Returns service status and supported features.
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        features=["streaming", "tool_calls", "hybrid_mode", "workflow_mode", "chat_mode"],
    )


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
    )

    logger.info(
        f"AG-UI run_agent: thread_id={request.thread_id}, "
        f"run_id={run_input.run_id}, mode={request.mode.value}"
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
    from datetime import datetime

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
    )

    logger.info(
        f"AG-UI run_agent_sync: thread_id={request.thread_id}, "
        f"run_id={run_input.run_id}, mode={request.mode.value}"
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
    description="Get conversation history for a thread (placeholder)",
    responses={
        200: {"description": "Thread history"},
        404: {"model": ErrorResponse, "description": "Thread not found"},
    },
)
async def get_thread_history(
    thread_id: str,
    limit: int = Query(50, ge=1, le=200, description="Maximum messages to return"),
) -> Dict[str, Any]:
    """
    Get thread conversation history.

    This is a placeholder endpoint for future integration
    with ThreadManager and session management.
    """
    # TODO: Integrate with ThreadManager when available
    return {
        "thread_id": thread_id,
        "messages": [],
        "total": 0,
        "limit": limit,
    }


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

    from datetime import datetime
    return ApprovalActionResponse(
        success=True,
        approval_id=approval_id,
        status=ApprovalStatusEnum.CANCELLED,
        message="Approval request cancelled",
        resolved_at=datetime.utcnow(),
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

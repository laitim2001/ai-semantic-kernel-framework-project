"""
Swarm API Routes

FastAPI routes for Agent Swarm status and worker management.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from src.integrations.swarm import (
    SwarmTracker,
    SwarmNotFoundError,
    WorkerNotFoundError,
)

from .dependencies import get_tracker
from .schemas import (
    SwarmStatusResponse,
    WorkerDetailResponse,
    WorkerListResponse,
    WorkerSummarySchema,
    ToolCallInfoSchema,
    ThinkingContentSchema,
    WorkerMessageSchema,
)

router = APIRouter(prefix="/swarm", tags=["Swarm"])


def _worker_to_summary(worker) -> WorkerSummarySchema:
    """Convert WorkerExecution to WorkerSummarySchema."""
    return WorkerSummarySchema(
        worker_id=worker.worker_id,
        worker_name=worker.worker_name,
        worker_type=worker.worker_type.value if hasattr(worker.worker_type, 'value') else str(worker.worker_type),
        role=worker.role,
        status=worker.status.value if hasattr(worker.status, 'value') else str(worker.status),
        progress=worker.progress,
        current_task=worker.current_task,
        tool_calls_count=len(worker.tool_calls),
        started_at=worker.started_at,
        completed_at=worker.completed_at,
    )


def _worker_to_detail(worker) -> WorkerDetailResponse:
    """Convert WorkerExecution to WorkerDetailResponse."""
    return WorkerDetailResponse(
        worker_id=worker.worker_id,
        worker_name=worker.worker_name,
        worker_type=worker.worker_type.value if hasattr(worker.worker_type, 'value') else str(worker.worker_type),
        role=worker.role,
        status=worker.status.value if hasattr(worker.status, 'value') else str(worker.status),
        progress=worker.progress,
        current_task=worker.current_task,
        tool_calls=[
            ToolCallInfoSchema(
                tool_id=tc.tool_id,
                tool_name=tc.tool_name,
                is_mcp=tc.is_mcp,
                input_params=tc.input_params,
                status=tc.status,
                result=tc.result,
                error=tc.error,
                started_at=tc.started_at,
                completed_at=tc.completed_at,
                duration_ms=tc.duration_ms,
            )
            for tc in worker.tool_calls
        ],
        thinking_contents=[
            ThinkingContentSchema(
                content=tc.content,
                timestamp=tc.timestamp,
                token_count=tc.token_count,
            )
            for tc in worker.thinking_contents
        ],
        messages=[
            WorkerMessageSchema(
                role=m.role,
                content=m.content,
                timestamp=m.timestamp,
            )
            for m in worker.messages
        ],
        started_at=worker.started_at,
        completed_at=worker.completed_at,
        error=worker.error,
    )


@router.get(
    "/{swarm_id}",
    response_model=SwarmStatusResponse,
    summary="Get Swarm Status",
    description="Get the current status of a swarm including all workers.",
)
async def get_swarm_status(
    swarm_id: str,
    tracker: SwarmTracker = Depends(get_tracker),
) -> SwarmStatusResponse:
    """Get swarm status by ID.

    Args:
        swarm_id: The swarm identifier.
        tracker: SwarmTracker instance (injected).

    Returns:
        SwarmStatusResponse with current swarm state.

    Raises:
        HTTPException: 404 if swarm not found.
    """
    swarm = tracker.get_swarm(swarm_id)
    if swarm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Swarm not found: {swarm_id}",
        )

    return SwarmStatusResponse(
        swarm_id=swarm.swarm_id,
        mode=swarm.mode.value if hasattr(swarm.mode, 'value') else str(swarm.mode),
        status=swarm.status.value if hasattr(swarm.status, 'value') else str(swarm.status),
        overall_progress=swarm.overall_progress,
        workers=[_worker_to_summary(w) for w in swarm.workers],
        total_tool_calls=swarm.total_tool_calls,
        completed_tool_calls=swarm.completed_tool_calls,
        started_at=swarm.started_at,
        completed_at=swarm.completed_at,
    )


@router.get(
    "/{swarm_id}/workers",
    response_model=WorkerListResponse,
    summary="List Swarm Workers",
    description="Get a list of all workers in a swarm.",
)
async def list_swarm_workers(
    swarm_id: str,
    tracker: SwarmTracker = Depends(get_tracker),
) -> WorkerListResponse:
    """List all workers in a swarm.

    Args:
        swarm_id: The swarm identifier.
        tracker: SwarmTracker instance (injected).

    Returns:
        WorkerListResponse with all workers.

    Raises:
        HTTPException: 404 if swarm not found.
    """
    swarm = tracker.get_swarm(swarm_id)
    if swarm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Swarm not found: {swarm_id}",
        )

    return WorkerListResponse(
        swarm_id=swarm.swarm_id,
        workers=[_worker_to_summary(w) for w in swarm.workers],
        total=len(swarm.workers),
    )


@router.get(
    "/{swarm_id}/workers/{worker_id}",
    response_model=WorkerDetailResponse,
    summary="Get Worker Details",
    description="Get detailed information about a specific worker.",
)
async def get_worker_details(
    swarm_id: str,
    worker_id: str,
    tracker: SwarmTracker = Depends(get_tracker),
) -> WorkerDetailResponse:
    """Get detailed worker information.

    Args:
        swarm_id: The swarm identifier.
        worker_id: The worker identifier.
        tracker: SwarmTracker instance (injected).

    Returns:
        WorkerDetailResponse with full worker details.

    Raises:
        HTTPException: 404 if swarm or worker not found.
    """
    swarm = tracker.get_swarm(swarm_id)
    if swarm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Swarm not found: {swarm_id}",
        )

    worker = swarm.get_worker_by_id(worker_id)
    if worker is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker not found: {worker_id}",
        )

    return _worker_to_detail(worker)

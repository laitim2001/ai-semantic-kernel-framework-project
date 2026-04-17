"""
API routes for Orchestration Execution Logs.

Provides endpoints to query historical pipeline execution records.

Sprint 169 — Phase 47: Pipeline execution persistence.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.session import get_session
from src.infrastructure.database.repositories.orchestration_execution_log import (
    OrchestrationExecutionLogRepository,
)

from .execution_log_schemas import (
    ExecutionLogDetail,
    ExecutionLogDetailResponse,
    ExecutionLogListResponse,
    ExecutionLogSummary,
)

logger = logging.getLogger(__name__)

execution_log_router = APIRouter(
    prefix="/orchestration/executions",
    tags=["Orchestration Execution Logs (Phase 47)"],
)


@execution_log_router.get("", response_model=ExecutionLogListResponse)
async def list_execution_logs(
    session_id: Optional[str] = Query(None, description="Filter by chat session ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_session),
) -> ExecutionLogListResponse:
    """List orchestration execution logs with optional filters."""
    repo = OrchestrationExecutionLogRepository(db)

    filters = {}
    if session_id:
        filters["session_id"] = session_id
    if user_id:
        filters["user_id"] = user_id
    if status:
        filters["status"] = status

    items, total = await repo.list(
        page=page,
        page_size=page_size,
        order_by="created_at",
        order_desc=True,
        **filters,
    )

    return ExecutionLogListResponse(
        data=[ExecutionLogSummary(**item.to_dict()) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@execution_log_router.get(
    "/by-session/{session_id}/latest",
    response_model=ExecutionLogDetailResponse,
)
async def get_latest_for_session(
    session_id: str,
    db: AsyncSession = Depends(get_session),
) -> ExecutionLogDetailResponse:
    """Get the most recent execution log for a chat session."""
    repo = OrchestrationExecutionLogRepository(db)
    item = await repo.get_latest_for_session(session_id)
    if not item:
        raise HTTPException(
            status_code=404,
            detail="No execution log found for this session",
        )
    return ExecutionLogDetailResponse(data=ExecutionLogDetail(**item.to_dict()))


@execution_log_router.get("/{execution_id}", response_model=ExecutionLogDetailResponse)
async def get_execution_log(
    execution_id: str,
    db: AsyncSession = Depends(get_session),
) -> ExecutionLogDetailResponse:
    """Get a specific execution log by ID."""
    try:
        uid = UUID(execution_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid execution ID format")

    repo = OrchestrationExecutionLogRepository(db)
    item = await repo.get(uid)
    if not item:
        raise HTTPException(status_code=404, detail="Execution log not found")

    return ExecutionLogDetailResponse(data=ExecutionLogDetail(**item.to_dict()))

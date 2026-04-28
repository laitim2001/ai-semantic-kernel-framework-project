"""Task CRUD API — REST endpoints for task lifecycle management.

Provides complete CRUD + state-transition endpoints for tasks dispatched
by the Orchestrator.

Sprint 113 — Phase 37 E2E Assembly B.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.domain.tasks.models import Task, TaskPriority, TaskStatus, TaskType
from src.domain.tasks.service import TaskService
from src.infrastructure.storage.task_store import TaskStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])

# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_task_service: Optional[TaskService] = None


def _get_task_service() -> TaskService:
    """Lazy-initialise the shared TaskService."""
    global _task_service
    if _task_service is None:
        store = TaskStore()
        _task_service = TaskService(task_store=store)
        logger.info("Task API: TaskService initialized")
    return _task_service


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class TaskCreateRequest(BaseModel):
    """Request body for creating a task."""

    title: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    task_type: str = Field(default="manual")
    priority: str = Field(default="normal")
    session_id: Optional[str] = None
    input_params: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskUpdateRequest(BaseModel):
    """Request body for updating a task."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    progress: Optional[float] = Field(None, ge=0.0, le=1.0)
    assigned_agent: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TaskProgressRequest(BaseModel):
    """Request body for updating task progress."""

    progress: float = Field(..., ge=0.0, le=1.0)
    partial_result: Optional[Dict[str, Any]] = None


class TaskResponse(BaseModel):
    """Serialised task for API responses."""

    task_id: str
    title: str
    description: str
    task_type: str
    status: str
    priority: str
    session_id: Optional[str]
    user_id: Optional[str]
    assigned_agent: Optional[str]
    progress: float
    created_at: str
    updated_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    input_params: Dict[str, Any]
    partial_results: List[Dict[str, Any]]
    metadata: Dict[str, Any]

    @classmethod
    def from_task(cls, task: Task) -> "TaskResponse":
        return cls(
            task_id=task.task_id,
            title=task.title,
            description=task.description,
            task_type=task.task_type.value,
            status=task.status.value,
            priority=task.priority.value,
            session_id=task.session_id,
            user_id=task.user_id,
            assigned_agent=task.assigned_agent,
            progress=task.progress,
            created_at=task.created_at.isoformat(),
            updated_at=task.updated_at.isoformat(),
            started_at=task.started_at.isoformat() if task.started_at else None,
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
            input_params=task.input_params,
            partial_results=task.partial_results,
            metadata=task.metadata,
        )


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(body: TaskCreateRequest) -> TaskResponse:
    """Create a new task."""
    service = _get_task_service()
    task = await service.create_task(
        title=body.title,
        task_type=body.task_type,
        description=body.description,
        priority=body.priority,
        session_id=body.session_id,
        input_params=body.input_params,
        metadata=body.metadata,
    )
    return TaskResponse.from_task(task)


@router.get("/", response_model=List[TaskResponse])
async def list_tasks(
    session_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[TaskResponse]:
    """List tasks with optional filtering."""
    service = _get_task_service()
    tasks = await service.list_tasks(
        session_id=session_id,
        user_id=user_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return [TaskResponse.from_task(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str) -> TaskResponse:
    """Get a task by ID."""
    service = _get_task_service()
    task = await service.get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    return TaskResponse.from_task(task)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, body: TaskUpdateRequest) -> TaskResponse:
    """Update a task."""
    service = _get_task_service()
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )
    task = await service.update_task(task_id, updates)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    return TaskResponse.from_task(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str) -> None:
    """Delete a task."""
    service = _get_task_service()
    deleted = await service.delete_task(task_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )


@router.post("/{task_id}/start", response_model=TaskResponse)
async def start_task(task_id: str, assigned_agent: Optional[str] = Query(None)) -> TaskResponse:
    """Mark a task as started."""
    service = _get_task_service()
    task = await service.start_task(task_id, assigned_agent=assigned_agent)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    return TaskResponse.from_task(task)


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: str,
    result: Optional[Dict[str, Any]] = None,
) -> TaskResponse:
    """Mark a task as completed."""
    service = _get_task_service()
    task = await service.complete_task(task_id, result=result)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    return TaskResponse.from_task(task)


@router.post("/{task_id}/fail", response_model=TaskResponse)
async def fail_task(task_id: str, error: str = Query(...)) -> TaskResponse:
    """Mark a task as failed."""
    service = _get_task_service()
    task = await service.fail_task(task_id, error=error)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    return TaskResponse.from_task(task)


@router.post("/{task_id}/progress", response_model=TaskResponse)
async def update_progress(task_id: str, body: TaskProgressRequest) -> TaskResponse:
    """Update task progress."""
    service = _get_task_service()
    task = await service.update_progress(
        task_id,
        progress=body.progress,
        partial_result=body.partial_result,
    )
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    return TaskResponse.from_task(task)

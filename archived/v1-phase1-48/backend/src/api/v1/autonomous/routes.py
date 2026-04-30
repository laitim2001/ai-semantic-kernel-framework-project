"""
Autonomous Planning API Routes - Phase 22 Testing

Provides autonomous task planning endpoints for UAT testing.

Endpoints:
    POST   /api/v1/claude/autonomous/plan          - Create autonomous plan
    GET    /api/v1/claude/autonomous/{task_id}     - Get task status
    POST   /api/v1/claude/autonomous/{task_id}/cancel - Cancel task
    GET    /api/v1/claude/autonomous/history       - Get task history
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field


router = APIRouter(prefix="/claude/autonomous", tags=["Autonomous Planning"])


# --- Request/Response Schemas ---


class TaskStep(BaseModel):
    """Single step in an autonomous plan."""
    step_id: str
    step_number: int
    action: str
    description: str
    status: str = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[str] = None
    error: Optional[str] = None


class CreatePlanRequest(BaseModel):
    """Request to create an autonomous plan."""
    goal: str = Field(..., description="The goal to achieve")
    context: Optional[str] = Field(None, description="Additional context")
    max_steps: int = Field(10, ge=1, le=50, description="Maximum steps allowed")
    timeout_minutes: int = Field(30, ge=1, le=120, description="Timeout in minutes")
    auto_execute: bool = Field(False, description="Whether to execute immediately")
    priority: str = Field("normal", description="Priority level: low/normal/high/critical")


class TaskResponse(BaseModel):
    """Response for a single task."""
    task_id: str
    goal: str
    status: str
    priority: str
    steps: List[TaskStep]
    current_step: int
    total_steps: int
    progress_percent: float
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result_summary: Optional[str] = None


class TaskListResponse(BaseModel):
    """Response for task list."""
    tasks: List[TaskResponse]
    total: int
    page: int
    page_size: int


class CancelResponse(BaseModel):
    """Response for cancel operation."""
    task_id: str
    status: str
    message: str
    cancelled_at: datetime


# --- In-Memory Storage ---


class AutonomousTaskStore:
    """In-memory storage for autonomous tasks."""

    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._history: List[str] = []

    def create_task(self, request: CreatePlanRequest) -> Dict[str, Any]:
        """Create a new autonomous task."""
        task_id = f"task_{uuid4().hex[:12]}"
        now = datetime.utcnow()

        # Generate mock steps based on goal
        steps = self._generate_steps(task_id, request.goal, request.max_steps)

        task = {
            "task_id": task_id,
            "goal": request.goal,
            "context": request.context,
            "status": "planning" if not request.auto_execute else "running",
            "priority": request.priority,
            "steps": steps,
            "current_step": 0,
            "total_steps": len(steps),
            "progress_percent": 0.0,
            "created_at": now,
            "updated_at": now,
            "started_at": now if request.auto_execute else None,
            "completed_at": None,
            "error": None,
            "result_summary": None,
            "timeout_minutes": request.timeout_minutes,
        }

        self._tasks[task_id] = task
        self._history.append(task_id)

        return task

    def _generate_steps(self, task_id: str, goal: str, max_steps: int) -> List[Dict]:
        """Generate mock steps for a task."""
        step_templates = [
            ("analyze", "Analyze requirements and gather information"),
            ("plan", "Create detailed execution plan"),
            ("prepare", "Prepare resources and dependencies"),
            ("execute", "Execute main task actions"),
            ("validate", "Validate results and verify completion"),
            ("cleanup", "Clean up temporary resources"),
            ("report", "Generate final report"),
        ]

        num_steps = min(max_steps, len(step_templates))
        steps = []

        for i, (action, description) in enumerate(step_templates[:num_steps]):
            steps.append({
                "step_id": f"{task_id}_step_{i+1}",
                "step_number": i + 1,
                "action": action,
                "description": f"{description} for: {goal[:50]}",
                "status": "pending",
                "started_at": None,
                "completed_at": None,
                "result": None,
                "error": None,
            })

        return steps

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task by ID."""
        task = self._tasks.get(task_id)
        if task:
            # Simulate progress
            self._simulate_progress(task)
        return task

    def _simulate_progress(self, task: Dict[str, Any]) -> None:
        """Simulate task progress for demo purposes."""
        if task["status"] not in ["running", "planning"]:
            return

        now = datetime.utcnow()
        task["updated_at"] = now

        # Simple progress simulation
        steps = task["steps"]
        total = len(steps)
        completed = sum(1 for s in steps if s["status"] == "completed")

        if completed < total:
            current_step = steps[completed]
            if current_step["status"] == "pending":
                current_step["status"] = "in_progress"
                current_step["started_at"] = now
            elif current_step["status"] == "in_progress":
                current_step["status"] = "completed"
                current_step["completed_at"] = now
                current_step["result"] = "Step completed successfully"
                completed += 1

            task["current_step"] = completed
            task["progress_percent"] = (completed / total) * 100

            if completed == total:
                task["status"] = "completed"
                task["completed_at"] = now
                task["result_summary"] = f"Successfully completed all {total} steps"

    def cancel_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Cancel a task."""
        task = self._tasks.get(task_id)
        if not task:
            return None

        if task["status"] in ["completed", "cancelled", "failed"]:
            return None

        now = datetime.utcnow()
        task["status"] = "cancelled"
        task["updated_at"] = now
        task["completed_at"] = now
        task["error"] = "Task cancelled by user"

        # Mark current step as cancelled
        for step in task["steps"]:
            if step["status"] == "in_progress":
                step["status"] = "cancelled"
                step["completed_at"] = now
                step["error"] = "Cancelled"

        return task

    def get_history(
        self,
        limit: int = 20,
        offset: int = 0,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get task history."""
        # Get tasks in reverse order (newest first)
        task_ids = list(reversed(self._history))

        # Filter by status if specified
        tasks = []
        for task_id in task_ids:
            task = self._tasks.get(task_id)
            if task:
                if status_filter and task["status"] != status_filter:
                    continue
                tasks.append(task)

        # Apply pagination
        return tasks[offset:offset + limit]

    def count_tasks(self, status_filter: Optional[str] = None) -> int:
        """Count total tasks."""
        if not status_filter:
            return len(self._tasks)
        return sum(1 for t in self._tasks.values() if t["status"] == status_filter)


# --- Global Store Instance ---


_task_store: Optional[AutonomousTaskStore] = None


def get_task_store() -> AutonomousTaskStore:
    """Get or create task store instance."""
    global _task_store
    if _task_store is None:
        _task_store = AutonomousTaskStore()
    return _task_store


# --- Helper Functions ---


def _to_task_response(task: Dict[str, Any]) -> TaskResponse:
    """Convert task dict to response model."""
    return TaskResponse(
        task_id=task["task_id"],
        goal=task["goal"],
        status=task["status"],
        priority=task["priority"],
        steps=[TaskStep(**s) for s in task["steps"]],
        current_step=task["current_step"],
        total_steps=task["total_steps"],
        progress_percent=task["progress_percent"],
        created_at=task["created_at"],
        updated_at=task["updated_at"],
        started_at=task.get("started_at"),
        completed_at=task.get("completed_at"),
        error=task.get("error"),
        result_summary=task.get("result_summary"),
    )


# --- API Endpoints ---


@router.post("/plan", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(request: CreatePlanRequest):
    """
    Create an autonomous planning task.

    The system will analyze the goal and create a step-by-step plan
    for achieving it autonomously.
    """
    store = get_task_store()
    task = store.create_task(request)
    return _to_task_response(task)


@router.get("/history", response_model=TaskListResponse)
async def get_task_history(
    limit: int = Query(20, ge=1, le=100, description="Number of tasks to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """
    Get autonomous task history.

    Returns a paginated list of all autonomous tasks.
    """
    store = get_task_store()
    tasks = store.get_history(limit=limit, offset=offset, status_filter=status)
    total = store.count_tasks(status_filter=status)

    return TaskListResponse(
        tasks=[_to_task_response(t) for t in tasks],
        total=total,
        page=offset // limit + 1 if limit else 1,
        page_size=limit,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str):
    """
    Get status of an autonomous task.

    Returns detailed information about the task including progress.
    """
    store = get_task_store()
    task = store.get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    return _to_task_response(task)


@router.post("/{task_id}/cancel", response_model=CancelResponse)
async def cancel_task(task_id: str):
    """
    Cancel an autonomous task.

    Attempts to cancel a running or pending task.
    """
    store = get_task_store()
    task = store.cancel_task(task_id)

    if not task:
        # Check if task exists
        existing = store.get_task(task_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task {task_id} cannot be cancelled (status: {existing['status']})",
        )

    return CancelResponse(
        task_id=task_id,
        status="cancelled",
        message="Task cancelled successfully",
        cancelled_at=task["completed_at"],
    )

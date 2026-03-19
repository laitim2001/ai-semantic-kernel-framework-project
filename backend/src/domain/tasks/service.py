"""Task service — business logic for task lifecycle management.

Provides CRUD operations and state transitions for tasks, backed by
TaskStore for persistence.

Sprint 113 — Phase 37 E2E Assembly B.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.domain.tasks.models import (
    Task,
    TaskPriority,
    TaskResult,
    TaskStatus,
    TaskType,
)

logger = logging.getLogger(__name__)


class TaskService:
    """Service layer for task operations.

    Args:
        task_store: Storage backend for task persistence.
    """

    def __init__(self, task_store: Any) -> None:
        self._store = task_store

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_task(
        self,
        title: str,
        task_type: str = "manual",
        description: str = "",
        priority: str = "normal",
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        input_params: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """Create a new task and persist it."""
        task = Task(
            title=title,
            description=description,
            task_type=TaskType(task_type) if task_type in TaskType.__members__.values() else TaskType.MANUAL,
            priority=TaskPriority(priority) if priority in TaskPriority.__members__.values() else TaskPriority.NORMAL,
            session_id=session_id,
            user_id=user_id,
            input_params=input_params or {},
            metadata=metadata or {},
        )
        await self._store.save(task.task_id, task.model_dump(mode="json"))
        logger.info("Task created: %s (%s) type=%s", task.task_id, title, task_type)
        return task

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve a task by ID."""
        data = await self._store.get(task_id)
        if data is None:
            return None
        return Task.model_validate(data)

    async def list_tasks(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Task]:
        """List tasks with optional filtering."""
        all_data = await self._store.list_all()
        tasks: List[Task] = []
        for data in all_data:
            try:
                task = Task.model_validate(data)
            except Exception:
                continue
            if session_id and task.session_id != session_id:
                continue
            if user_id and task.user_id != user_id:
                continue
            if status and task.status.value != status:
                continue
            tasks.append(task)

        # Sort by created_at descending
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks[offset: offset + limit]

    async def update_task(
        self,
        task_id: str,
        updates: Dict[str, Any],
    ) -> Optional[Task]:
        """Update specific fields of a task."""
        task = await self.get_task(task_id)
        if task is None:
            return None

        allowed_fields = {
            "title", "description", "status", "priority",
            "progress", "assigned_agent", "metadata",
            "checkpoint_data", "input_params",
        }
        for key, value in updates.items():
            if key in allowed_fields:
                if key == "status":
                    value = TaskStatus(value)
                elif key == "priority":
                    value = TaskPriority(value)
                setattr(task, key, value)

        task.updated_at = datetime.utcnow()
        await self._store.save(task.task_id, task.model_dump(mode="json"))
        logger.info("Task updated: %s fields=%s", task_id, list(updates.keys()))
        return task

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task by ID."""
        task = await self.get_task(task_id)
        if task is None:
            return False
        await self._store.delete(task_id)
        logger.info("Task deleted: %s", task_id)
        return True

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    async def start_task(self, task_id: str, assigned_agent: Optional[str] = None) -> Optional[Task]:
        """Mark a task as started."""
        task = await self.get_task(task_id)
        if task is None:
            return None
        task.mark_started()
        if assigned_agent:
            task.assigned_agent = assigned_agent
        await self._store.save(task.task_id, task.model_dump(mode="json"))
        logger.info("Task started: %s agent=%s", task_id, assigned_agent)
        return task

    async def complete_task(
        self, task_id: str, result: Optional[Dict[str, Any]] = None
    ) -> Optional[Task]:
        """Mark a task as completed with optional result."""
        task = await self.get_task(task_id)
        if task is None:
            return None
        task_result = None
        if result:
            task_result = TaskResult(
                task_id=task_id,
                success=True,
                output=result,
                completed_at=datetime.utcnow(),
            )
        task.mark_completed(task_result)
        await self._store.save(task.task_id, task.model_dump(mode="json"))
        logger.info("Task completed: %s", task_id)
        return task

    async def fail_task(self, task_id: str, error: str) -> Optional[Task]:
        """Mark a task as failed."""
        task = await self.get_task(task_id)
        if task is None:
            return None
        task.mark_failed(error)
        await self._store.save(task.task_id, task.model_dump(mode="json"))
        logger.warning("Task failed: %s error=%s", task_id, error)
        return task

    async def update_progress(
        self,
        task_id: str,
        progress: float,
        partial_result: Optional[Dict[str, Any]] = None,
    ) -> Optional[Task]:
        """Update task progress."""
        task = await self.get_task(task_id)
        if task is None:
            return None
        task.update_progress(progress, partial_result)
        await self._store.save(task.task_id, task.model_dump(mode="json"))
        return task

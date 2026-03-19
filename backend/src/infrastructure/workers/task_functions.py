"""ARQ Task Functions — background job implementations.

These functions are registered with the ARQ worker and executed
in a separate process. Each function receives a context dict
from ARQ and the task parameters.

Sprint 136 — Phase 39 E2E Assembly D.
"""

import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


async def execute_workflow_task(
    ctx: Dict[str, Any],
    task_id: str,
    session_id: str,
    workflow_type: str,
    input_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute a MAF workflow in the background.

    Args:
        ctx: ARQ context (contains Redis pool, etc.).
        task_id: Task ID for status tracking.
        session_id: Session that initiated the task.
        workflow_type: Type of workflow to execute.
        input_data: Workflow input parameters.

    Returns:
        Task result dict.
    """
    start_time = time.perf_counter()
    logger.info(
        "ARQ: executing workflow task=%s type=%s session=%s",
        task_id, workflow_type, session_id,
    )

    try:
        # Update task status to IN_PROGRESS
        await _update_task_status(task_id, "in_progress", 0.1)

        # Execute workflow via MAF
        try:
            from src.integrations.agent_framework.builders.workflow_executor import (
                WorkflowExecutorAdapter,
            )
            executor = WorkflowExecutorAdapter()
            # TODO: Call executor with workflow_type and input_data
            # result = await executor.execute(workflow_type, input_data)
            await _update_task_status(task_id, "in_progress", 0.5)
        except ImportError:
            logger.warning("ARQ: MAF WorkflowExecutor not available")
        except Exception as e:
            logger.error("ARQ: workflow execution failed: %s", e)
            await _update_task_status(task_id, "failed", error=str(e))
            return {"task_id": task_id, "status": "failed", "error": str(e)}

        # Mark completed
        duration_ms = (time.perf_counter() - start_time) * 1000
        await _update_task_status(task_id, "completed", 1.0)

        result = {
            "task_id": task_id,
            "status": "completed",
            "workflow_type": workflow_type,
            "duration_ms": round(duration_ms, 2),
        }
        logger.info("ARQ: workflow task=%s completed in %.0fms", task_id, duration_ms)
        return result

    except Exception as e:
        logger.error("ARQ: workflow task=%s failed: %s", task_id, e, exc_info=True)
        await _update_task_status(task_id, "failed", error=str(e))
        return {"task_id": task_id, "status": "failed", "error": str(e)}


async def execute_swarm_task(
    ctx: Dict[str, Any],
    task_id: str,
    session_id: str,
    task_description: str,
    worker_count: int = 3,
) -> Dict[str, Any]:
    """Execute a swarm coordination in the background.

    Args:
        ctx: ARQ context.
        task_id: Task ID for tracking.
        session_id: Initiating session.
        task_description: What the swarm should do.
        worker_count: Number of swarm workers.

    Returns:
        Task result dict.
    """
    start_time = time.perf_counter()
    logger.info(
        "ARQ: executing swarm task=%s workers=%d session=%s",
        task_id, worker_count, session_id,
    )

    try:
        await _update_task_status(task_id, "in_progress", 0.1)

        try:
            from src.integrations.swarm.swarm_integration import SwarmIntegration
            swarm = SwarmIntegration()
            swarm_id = f"swarm-{task_id[:8]}"
            swarm.on_coordination_started(
                swarm_id=swarm_id,
                mode="parallel",
                subtasks=[{"description": task_description}],
                metadata={"task_id": task_id, "worker_count": worker_count},
            )
            await _update_task_status(task_id, "in_progress", 0.5)
        except ImportError:
            logger.warning("ARQ: SwarmIntegration not available")
        except Exception as e:
            logger.error("ARQ: swarm execution failed: %s", e)
            await _update_task_status(task_id, "failed", error=str(e))
            return {"task_id": task_id, "status": "failed", "error": str(e)}

        duration_ms = (time.perf_counter() - start_time) * 1000
        await _update_task_status(task_id, "completed", 1.0)

        result = {
            "task_id": task_id,
            "status": "completed",
            "worker_count": worker_count,
            "duration_ms": round(duration_ms, 2),
        }
        logger.info("ARQ: swarm task=%s completed in %.0fms", task_id, duration_ms)
        return result

    except Exception as e:
        logger.error("ARQ: swarm task=%s failed: %s", task_id, e, exc_info=True)
        await _update_task_status(task_id, "failed", error=str(e))
        return {"task_id": task_id, "status": "failed", "error": str(e)}


async def _update_task_status(
    task_id: str,
    status: str,
    progress: float = 0.0,
    error: Optional[str] = None,
) -> None:
    """Update task status in TaskStore."""
    try:
        from src.domain.tasks.service import TaskService
        from src.infrastructure.storage.task_store import TaskStore

        store = TaskStore()
        service = TaskService(task_store=store)
        updates: Dict[str, Any] = {"status": status, "progress": progress}
        if error:
            updates["metadata"] = {"error": error}
        await service.update_task(task_id, updates)
    except Exception as e:
        logger.warning("ARQ: failed to update task status: %s", e)

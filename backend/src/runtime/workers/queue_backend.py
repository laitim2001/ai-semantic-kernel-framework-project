"""
File: backend/src/runtime/workers/queue_backend.py
Purpose: QueueBackend ABC — neutral interface AgentLoopWorker uses to enqueue/poll/cancel tasks.
Category: Runtime / Workers (execution plane)
Scope: Phase 49 / Sprint 49.4

Description:
    Decouples AgentLoopWorker from the chosen queue framework (Temporal —
    selected per worker-queue-decision.md). Production adapter
    (TemporalQueueBackend) lives in runtime/workers/temporal/ and is built
    in Phase 53.1 when HITL signals become a concrete need.

    For Phase 49.4 - 50.1 we ship MockQueueBackend (in-memory) so the loop
    framework can be tested + integrated without standing up Temporal server.

    All side effects (network, persistence) live in concrete adapters.
    QueueBackend ABC is pure abstraction.

Created: 2026-04-29 (Sprint 49.4 Day 2)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.4 Day 2) — neutral ABC + Mock impl

Related:
    - agent_loop_worker.py — primary consumer
    - worker-queue-decision.md — selection rationale (Temporal chosen)
    - 06-phase-roadmap.md §Phase 53.1 — when Temporal adapter ships
"""

from __future__ import annotations

import asyncio
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class TaskEnvelope:
    """Wraps a task payload + metadata for transport across queue backend.

    `tenant_id` is required (multi-tenant rule 1). `trace_id` is required
    for Cat 12 observability (every span across worker boundary keeps trace).
    """

    task_id: str
    tenant_id: str
    user_id: str | None
    payload: dict[str, Any]
    trace_id: str
    enqueued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    max_retries: int = 2

    @classmethod
    def new(
        cls,
        *,
        tenant_id: str,
        payload: dict[str, Any],
        trace_id: str,
        user_id: str | None = None,
        max_retries: int = 2,
    ) -> "TaskEnvelope":
        return cls(
            task_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            payload=payload,
            trace_id=trace_id,
            max_retries=max_retries,
        )


@dataclass(frozen=True)
class TaskResult:
    task_id: str
    status: TaskStatus
    result: dict[str, Any] | None = None
    error: str | None = None
    completed_at: datetime | None = None
    retries: int = 0


class QueueBackend(ABC):
    """Neutral queue interface. Concrete impls: MockQueueBackend / TemporalQueueBackend."""

    @abstractmethod
    async def submit(self, envelope: TaskEnvelope) -> str:
        """Enqueue task; return task_id."""
        ...

    @abstractmethod
    async def poll(self, task_id: str) -> TaskResult:
        """Get current status. Non-blocking."""
        ...

    @abstractmethod
    async def cancel(self, task_id: str) -> bool:
        """Request cancellation. Returns True if accepted (not necessarily yet executed)."""
        ...

    @abstractmethod
    async def list_pending(self, *, tenant_id: str | None = None) -> list[TaskEnvelope]:
        """List pending tasks. tenant_id filter applies (multi-tenant rule 2)."""
        ...


# ---------------------------------------------------------------------------
# Mock implementation — test double; in-memory only
# ---------------------------------------------------------------------------


class MockQueueBackend(QueueBackend):
    """In-memory queue backend for unit tests + Phase 50.1 dev. NO BROKER.

    Tasks submitted are NOT auto-executed; AgentLoopWorker.run_once() consumes
    them. This makes worker tests deterministic without timing.
    """

    def __init__(self) -> None:
        self._pending: list[TaskEnvelope] = []
        self._results: dict[str, TaskResult] = {}
        self._cancelled: set[str] = set()
        self._lock = asyncio.Lock()

    async def submit(self, envelope: TaskEnvelope) -> str:
        async with self._lock:
            self._pending.append(envelope)
            self._results[envelope.task_id] = TaskResult(
                task_id=envelope.task_id, status=TaskStatus.PENDING
            )
        return envelope.task_id

    async def poll(self, task_id: str) -> TaskResult:
        async with self._lock:
            return self._results.get(
                task_id,
                TaskResult(task_id=task_id, status=TaskStatus.FAILED, error="unknown task_id"),
            )

    async def cancel(self, task_id: str) -> bool:
        async with self._lock:
            if task_id not in self._results:
                return False
            self._cancelled.add(task_id)
            current = self._results[task_id]
            if current.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                self._results[task_id] = TaskResult(
                    task_id=task_id,
                    status=TaskStatus.CANCELLED,
                    completed_at=datetime.now(timezone.utc),
                    retries=current.retries,
                )
                self._pending = [e for e in self._pending if e.task_id != task_id]
            return True

    async def list_pending(self, *, tenant_id: str | None = None) -> list[TaskEnvelope]:
        async with self._lock:
            if tenant_id is None:
                return list(self._pending)
            return [e for e in self._pending if e.tenant_id == tenant_id]

    # -- test helpers (not part of QueueBackend ABC) --

    async def _take_one(self) -> TaskEnvelope | None:
        """Worker side: pop a pending task. Used by AgentLoopWorker.run_once()."""
        async with self._lock:
            if not self._pending:
                return None
            envelope = self._pending.pop(0)
            current = self._results[envelope.task_id]
            self._results[envelope.task_id] = TaskResult(
                task_id=envelope.task_id, status=TaskStatus.RUNNING, retries=current.retries
            )
            return envelope

    async def _complete(
        self,
        task_id: str,
        *,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        """Worker side: mark task complete or failed."""
        async with self._lock:
            current = self._results.get(task_id)
            retries = current.retries if current else 0
            self._results[task_id] = TaskResult(
                task_id=task_id,
                status=TaskStatus.FAILED if error else TaskStatus.COMPLETED,
                result=result,
                error=error,
                completed_at=datetime.now(timezone.utc),
                retries=retries,
            )

    def _is_cancelled(self, task_id: str) -> bool:
        return task_id in self._cancelled

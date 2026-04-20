"""Safe fire-and-forget background task management for memory operations.

Sprint 170 (Phase 48) — v2 agent team review integrated.

Addresses the audit-hole risk identified in v1 review:
  "Fire-and-forget async writes can silently fail → audit trail gaps"

Guarantees:
  1. Strong task reference retained (self._tasks set) until task completes —
     prevents GC-dropped tasks (asyncio.create_task anti-pattern).
  2. Semaphore-capped concurrency — prevents unbounded task creation under burst.
  3. done_callback attaches dead-letter logging — exceptions are NEVER silent.
  4. drain() for graceful shutdown / test teardown.

Usage:
    mgr = MemoryBackgroundTaskManager(max_concurrency=100)
    mgr.fire_and_forget(
        self._track_access(memory_id, layer, user_id),
        context={"memory_id": memory_id, "layer": layer.value,
                 "user_id": user_id, "operation": "search_hit"},
    )
    # ... later, on shutdown:
    await mgr.drain(timeout=5.0)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Dict, Optional, Set

_DLQ_LOGGER_NAME = "memory.background.dlq"


class MemoryBackgroundTaskManager:
    """Safe fire-and-forget manager for memory-system background work.

    All fire-and-forget coroutines are wrapped with:
      - Semaphore acquisition (bounded concurrency)
      - Exception capture → dead-letter log with JSON context
      - Strong reference retention until done
    """

    def __init__(self, max_concurrency: int = 100) -> None:
        if max_concurrency < 1:
            raise ValueError(f"max_concurrency must be >= 1, got {max_concurrency}")
        self._tasks: Set[asyncio.Task[Any]] = set()
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._dead_letter_log = logging.getLogger(_DLQ_LOGGER_NAME)
        self._max_concurrency = max_concurrency

    @property
    def pending_count(self) -> int:
        """Count of tasks still running or waiting on semaphore."""
        return len(self._tasks)

    @property
    def max_concurrency(self) -> int:
        return self._max_concurrency

    def fire_and_forget(
        self,
        coro: Awaitable[Any],
        *,
        context: Optional[Dict[str, Any]] = None,
    ) -> asyncio.Task[Any]:
        """Schedule coro as background task with safe failure handling.

        Args:
            coro: The coroutine to run. Must be awaitable.
            context: Diagnostic context dict written to dead-letter log on
                failure. Typical keys: memory_id, layer, user_id, operation.

        Returns:
            The asyncio.Task (for optional direct await in tests).
        """
        ctx = context or {}

        async def _runner() -> None:
            async with self._semaphore:
                try:
                    await coro
                except asyncio.CancelledError:
                    # Propagate cancellation — drain() uses timeout which may cancel
                    raise
                except Exception as exc:  # noqa: BLE001 — DLQ captures all
                    self._dead_letter_log.error(
                        "memory_background_task_failed",
                        extra={
                            "event": "memory_background_task_failed",
                            "context": ctx,
                            "error": str(exc),
                            "error_type": type(exc).__name__,
                        },
                        exc_info=True,
                    )

        task = asyncio.create_task(_runner())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    async def drain(self, timeout: float = 5.0) -> bool:
        """Wait for all pending tasks to complete.

        Args:
            timeout: Max seconds to wait. If exceeded, remaining tasks stay
                scheduled (no forced cancellation).

        Returns:
            True if all tasks completed within timeout, False otherwise.
        """
        if not self._tasks:
            return True
        pending_snapshot = set(self._tasks)
        done, pending = await asyncio.wait(pending_snapshot, timeout=timeout)
        return len(pending) == 0

    async def close(self) -> None:
        """Graceful shutdown — drain then clear tracked set."""
        await self.drain(timeout=5.0)
        self._tasks.clear()

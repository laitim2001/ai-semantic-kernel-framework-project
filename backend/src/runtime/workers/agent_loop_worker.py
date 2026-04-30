"""
File: backend/src/runtime/workers/agent_loop_worker.py
Purpose: AgentLoopWorker — pulls TaskEnvelope from QueueBackend and executes agent loop.
Category: Runtime / Workers (execution plane)
Scope: Phase 49 / Sprint 49.4 (stub) → Phase 50.1 (loop) → Phase 53.1 (HITL)

Description:
    Phase 49.4 stub: scaffold + retry policy + cancellation handling. The actual
    agent loop body (Cat 1) lands in Phase 50.1; HITL pause/resume signals
    land in Phase 53.1 along with TemporalQueueBackend.

    The worker is intentionally MINIMAL right now:
    - poll one envelope from QueueBackend
    - delegate execution to a pluggable handler (defaults to no-op stub)
    - retry on retriable error up to envelope.max_retries
    - respect cancellation
    - propagate trace_context for Cat 12 observability

    NOT in scope this sprint:
    - Temporal-specific signals (Phase 53.1)
    - graceful shutdown (drain pending tasks; Phase 53.1)

Sprint 50.2 Day 2.5 additions:
    - `execute_loop_with_sse(loop, session_id, user_input, sse_emit)` — common
      driver that runs `AgentLoopImpl.run()` and dispatches each LoopEvent to
      the supplied async `sse_emit` callback. Used by both the API SSE router
      (in-process) and the worker handler (queue-backed; Phase 53.1).
    - `build_agent_loop_handler(*, chat_client, tool_registry, tool_executor,
      output_parser, system_prompt, sse_emit) -> TaskHandler` factory: produces
      a worker-ready handler that constructs a fresh AgentLoopImpl per task
      and runs it through `execute_loop_with_sse`. Forward-compatible with
      Phase 53.1 Temporal adapter (TaskHandler signature unchanged).

Created: 2026-04-29 (Sprint 49.4 Day 2)
Last Modified: 2026-04-30

Modification History (newest-first):
    - 2026-04-30: Add execute_loop_with_sse helper + build_agent_loop_handler
        factory (Sprint 50.2 Day 2.5). _default_handler stub kept for now
        (DEPRECATED-IN: 53.1 when TemporalQueueBackend lands).
    - 2026-04-29: Initial stub (Sprint 49.4 Day 2)

Related:
    - queue_backend.py — QueueBackend ABC consumer
    - worker-queue-decision.md — chosen Temporal as production backend
    - 06-phase-roadmap.md §Phase 50.1 (loop body) §Phase 53.1 (HITL)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable
from uuid import UUID

from adapters._base.chat_client import ChatClient
from agent_harness._contracts import (
    LLMResponded,
    LoopCompleted,
    LoopEvent,
    TraceContext,
)
from agent_harness.orchestrator_loop import AgentLoopImpl
from agent_harness.output_parser import OutputParser
from agent_harness.tools import ToolExecutor, ToolRegistry
from runtime.workers.queue_backend import (
    MockQueueBackend,
    QueueBackend,
    TaskEnvelope,
    TaskResult,
    TaskStatus,
)

logger = logging.getLogger(__name__)


# Handler signature: receives envelope, returns result dict.
# In Phase 50.1 the AgentLoop is wired here.
TaskHandler = Callable[[TaskEnvelope], Awaitable[dict[str, object]]]


# === Sprint 50.2 Day 2.5: shared driver + handler factory ====================

# SseEmit callback: receives a LoopEvent, dispatches it to the streaming sink
# (HTTP SSE chunked response, queue, etc.). Async so backpressure-friendly.
SseEmit = Callable[[LoopEvent], Awaitable[None]]


async def execute_loop_with_sse(
    *,
    loop: AgentLoopImpl,
    session_id: UUID,
    user_input: str,
    sse_emit: SseEmit,
    trace_context: TraceContext | None = None,
) -> dict[str, Any]:
    """Drive `loop.run()` and dispatch each event to `sse_emit`.

    Returns a dict suitable as a TaskHandler result: ``{"status",
    "total_turns", "final_content"}``. ``final_content`` captures the
    most recent LLMResponded.content (best-effort final answer).
    """
    final_content = ""
    total_turns = 0
    async for event in loop.run(
        session_id=session_id,
        user_input=user_input,
        trace_context=trace_context,
    ):
        await sse_emit(event)
        if isinstance(event, LLMResponded) and event.content:
            final_content = event.content
        if isinstance(event, LoopCompleted):
            total_turns = event.total_turns
    return {
        "status": "completed",
        "total_turns": total_turns,
        "final_content": final_content,
    }


def build_agent_loop_handler(
    *,
    chat_client: ChatClient,
    tool_registry: ToolRegistry,
    tool_executor: ToolExecutor,
    output_parser: OutputParser,
    sse_emit: SseEmit,
    system_prompt: str = "",
    max_turns: int = 50,
    token_budget: int = 100_000,
) -> TaskHandler:
    """Factory: TaskHandler that runs AgentLoopImpl + emits LoopEvents via SSE.

    The returned handler is queue-backend-agnostic; same wiring works for
    MockQueueBackend (50.2) and TemporalQueueBackend (Phase 53.1).

    The envelope must carry the user message under ``payload["message"]``.
    """

    async def handler(envelope: TaskEnvelope) -> dict[str, Any]:
        loop = AgentLoopImpl(
            chat_client=chat_client,
            output_parser=output_parser,
            tool_executor=tool_executor,
            tool_registry=tool_registry,
            system_prompt=system_prompt,
            max_turns=max_turns,
            token_budget=token_budget,
        )
        message = str(envelope.payload.get("message", ""))
        # task_id is a str; coerce to UUID for the loop's session_id contract.
        try:
            sid = UUID(envelope.task_id)
        except ValueError:
            # Fall back to a deterministic UUID; envelope.task_id may be free-form.
            sid = UUID(int=hash(envelope.task_id) & ((1 << 128) - 1))
        return await execute_loop_with_sse(
            loop=loop,
            session_id=sid,
            user_input=message,
            sse_emit=sse_emit,
        )

    return handler


async def _default_handler(envelope: TaskEnvelope) -> dict[str, object]:
    """Phase 49.4 stub. Phase 50.1 replaces with AgentLoop.run()."""
    logger.info(
        "agent_loop_worker default_handler: task_id=%s tenant=%s trace=%s payload_keys=%s",
        envelope.task_id,
        envelope.tenant_id,
        envelope.trace_id,
        list(envelope.payload.keys()),
    )
    return {"echo": envelope.payload}


@dataclass
class WorkerConfig:
    poll_interval_sec: float = 0.5
    retry_backoff_base_sec: float = 0.5
    retry_backoff_factor: float = 2.0
    max_inflight: int = 1  # Phase 50.1 may raise to N for concurrency


class AgentLoopWorker:
    """Pulls one task at a time from QueueBackend; runs handler with retry / cancel.

    Production wiring: AgentLoopWorker(TemporalQueueBackend(...)) — Phase 53.1.
    Test wiring: AgentLoopWorker(MockQueueBackend()) — this sprint.
    """

    def __init__(
        self,
        backend: QueueBackend,
        *,
        handler: TaskHandler | None = None,
        config: WorkerConfig | None = None,
    ) -> None:
        self.backend = backend
        self.handler = handler or _default_handler
        self.config = config or WorkerConfig()

    async def run_once(self) -> TaskResult | None:
        """Poll one task; execute with retries; return final TaskResult.

        Returns None if queue empty.
        """
        if not isinstance(self.backend, MockQueueBackend):
            raise NotImplementedError(
                "Real-broker poll path lives in concrete adapters (Phase 53.1)"
            )
        envelope = await self.backend._take_one()
        if envelope is None:
            return None

        return await self._execute_with_retry(envelope)

    async def _execute_with_retry(self, envelope: TaskEnvelope) -> TaskResult:
        retries = 0
        last_error: str | None = None

        while retries <= envelope.max_retries:
            if self._is_cancelled(envelope.task_id):
                logger.info("task %s cancelled before retry %d", envelope.task_id, retries)
                # Mock backend already wrote CANCELLED status in cancel(); we just return it
                return await self.backend.poll(envelope.task_id)

            try:
                result = await self.handler(envelope)
                await self._complete_success(envelope.task_id, result)
                return await self.backend.poll(envelope.task_id)
            except asyncio.CancelledError:
                logger.info("task %s cancelled mid-flight", envelope.task_id)
                raise
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc) or exc.__class__.__name__
                retries += 1
                if retries > envelope.max_retries:
                    break
                backoff = self.config.retry_backoff_base_sec * (
                    self.config.retry_backoff_factor ** (retries - 1)
                )
                logger.warning(
                    "task %s failed (attempt %d/%d): %s; backoff=%.2fs",
                    envelope.task_id,
                    retries,
                    envelope.max_retries,
                    last_error,
                    backoff,
                )
                await asyncio.sleep(backoff)

        await self._complete_failure(envelope.task_id, last_error or "max retries exceeded")
        return await self.backend.poll(envelope.task_id)

    # -- helpers -----------------------------------------------------------

    def _is_cancelled(self, task_id: str) -> bool:
        if isinstance(self.backend, MockQueueBackend):
            return self.backend._is_cancelled(task_id)
        return False

    async def _complete_success(self, task_id: str, result: dict[str, object]) -> None:
        if isinstance(self.backend, MockQueueBackend):
            await self.backend._complete(task_id, result=result)
        # production: TemporalQueueBackend acks via its own SDK call

    async def _complete_failure(self, task_id: str, error: str) -> None:
        if isinstance(self.backend, MockQueueBackend):
            await self.backend._complete(task_id, error=error)


__all__ = [
    "AgentLoopWorker",
    "SseEmit",
    "TaskHandler",
    "TaskStatus",
    "WorkerConfig",
    "build_agent_loop_handler",
    "execute_loop_with_sse",
]

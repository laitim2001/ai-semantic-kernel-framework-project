"""
File: backend/src/api/v1/chat/router.py
Purpose: HTTP entrypoint for the V2 main agent flow — POST /chat (SSE) + GET sessions.
Category: api/v1/chat
Scope: Phase 50 / Sprint 50.2 (Day 1.5)

Description:
    Three endpoints:
    - POST /api/v1/chat/                   → starts AgentLoopImpl.run() and
                                             streams LoopEvents as SSE.
    - GET  /api/v1/chat/sessions/{id}      → returns running/completed/cancelled
                                             status for a known session.
    - POST /api/v1/chat/sessions/{id}/cancel → flips status to "cancelled" and
                                             signals cancel_event.

    POST /chat orchestration:
        1. Parse ChatRequest (mode + message).
        2. Generate / accept session_id; register in SessionRegistry.
        3. build_handler(mode, message) — returns wired AgentLoopImpl.
        4. Stream loop.run() events through serialize_loop_event +
           format_sse_message into a StreamingResponse(text/event-stream).
        5. mark_completed on natural termination; raise propagates as 500.

    Phase 50.2 keeps everything in-process. Phase 53.1 will fork the loop
    execution into a worker pool (Temporal / Celery) — at that point the
    POST endpoint becomes a session-creation + SSE-attach pair, and the
    actual loop run lives in the worker.

Created: 2026-04-30 (Sprint 50.2 Day 1.5)
Last Modified: 2026-04-30

Modification History (newest-first):
    - 2026-04-30: Initial creation (Sprint 50.2 Day 1.5) — POST /chat SSE +
        GET / cancel session endpoints. In-process loop execution.

Related:
    - .schemas (ChatRequest / ChatSessionResponse)
    - .handler (build_handler)
    - .sse (serialize_loop_event / format_sse_message)
    - .session_registry (in-memory state)
    - api/main.py (mounts this router)
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from agent_harness._contracts import LoopCompleted

from .handler import build_handler
from .schemas import ChatRequest, ChatSessionResponse
from .session_registry import SessionRegistry, get_default_registry
from .sse import format_sse_message, serialize_loop_event

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", status_code=status.HTTP_200_OK)
async def chat(req: ChatRequest) -> StreamingResponse:
    """Run an agent loop and stream LoopEvents as SSE.

    Response is `text/event-stream` (per 02-architecture-design §SSE).
    Each frame is `event: <type>\\ndata: <json>\\n\\n`. The session_id is
    in the first `loop_start` frame's data.
    """
    try:
        loop = build_handler(req.mode, req.message)
    except (RuntimeError, ValueError) as exc:
        # Misconfiguration (env vars / unsupported mode) → 503.
        # 503 reflects "feature available in principle but not configured here";
        # for invalid mode the schema layer should have rejected first, but we
        # keep this as defense-in-depth.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    session_id = req.session_id or uuid4()
    registry = get_default_registry()
    await registry.register(session_id)

    return StreamingResponse(
        _stream_loop_events(loop, session_id, registry, user_input=req.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable nginx buffering for real-time
            "X-Session-Id": str(session_id),
        },
    )


async def _stream_loop_events(
    loop: object,  # AgentLoopImpl; loose-typed to avoid circular import noise
    session_id: UUID,
    registry: SessionRegistry,
    *,
    user_input: str,
) -> AsyncIterator[bytes]:
    """Drive the loop generator + emit SSE bytes; finalize registry state.

    `user_input` is appended into the loop's messages as the first user turn.
    For ``echo_demo`` mode it is harmless (MockChatClient ignores the request);
    for ``real_llm`` it is what the model actually responds to.
    """
    natural_completion = False
    try:
        async for event in loop.run(  # type: ignore[attr-defined]
            session_id=session_id,
            user_input=user_input,
        ):
            try:
                payload = serialize_loop_event(event)
            except NotImplementedError:
                # Day 1: unimplemented event types (Day 2 fills) — skip for now.
                logger.debug("sse: skip unserialized event %s", type(event).__name__)
                continue
            yield format_sse_message(payload["type"], payload["data"])
            if isinstance(event, LoopCompleted):
                natural_completion = True
                break
    except asyncio.CancelledError:
        logger.info("chat session %s: client disconnected mid-stream", session_id)
        raise
    finally:
        if natural_completion:
            await registry.mark_completed(session_id)
        # else: leave status as-is (running / cancelled) — caller can poll GET.


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_session(session_id: UUID) -> ChatSessionResponse:
    registry = get_default_registry()
    entry = await registry.get(session_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found.",
        )
    return ChatSessionResponse(
        session_id=session_id,
        status=entry.status,
        started_at=entry.started_at,
    )


@router.post("/sessions/{session_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_session(session_id: UUID) -> None:
    registry = get_default_registry()
    found = await registry.cancel(session_id)
    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found.",
        )

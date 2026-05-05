"""
File: backend/src/api/v1/chat/router.py
Purpose: HTTP entrypoint for the V2 main agent flow — POST /chat (SSE) + GET sessions.
Category: api/v1/chat
Scope: Phase 50 / Sprint 50.2 (Day 1.5) — Sprint 52.5 Day 2 (P0 #11+#12 wiring)

Description:
    Three endpoints, all gated by `Depends(get_current_tenant)` (single
    canonical source: JWT-decoded tenant_id from request.state, populated
    by TenantContextMiddleware):

    - POST /api/v1/chat/                   → starts AgentLoopImpl.run() and
                                             streams LoopEvents as SSE.
    - GET  /api/v1/chat/sessions/{id}      → returns running/completed/cancelled
                                             status for a known session of THIS tenant.
    - POST /api/v1/chat/sessions/{id}/cancel → flips status to "cancelled" and
                                             signals cancel_event for THIS tenant.

    POST /chat orchestration (per Sprint 52.5 P0 #11+#12):
        1. JWT middleware populates request.state.tenant_id → Depends extracts.
        2. Parse ChatRequest (mode + message).
        3. Generate / accept session_id; register in SessionRegistry under tenant.
        4. Create root TraceContext(tenant_id=current_tenant, session_id=...).
        5. build_handler(mode, message) — returns wired AgentLoopImpl.
        6. Stream loop.run(trace_context=root_ctx) events through
           serialize_loop_event + format_sse_message.
        7. mark_completed on natural termination; raise propagates as 500.

    Cross-tenant attempts return 404 — never reveal whether the session
    exists under a different tenant (per multi-tenant-data.md 鐵律).

    Phase 50.2 keeps everything in-process. Phase 53.1 will fork the loop
    execution into a worker pool (Temporal / Celery) — at that point the
    POST endpoint becomes a session-creation + SSE-attach pair, and the
    actual loop run lives in the worker.

Created: 2026-04-30 (Sprint 50.2 Day 1.5)
Last Modified: 2026-05-01

Modification History (newest-first):
    - 2026-05-05: Sprint 55.5 Day 1 — wire run_with_verification at L197 (AD-Cat10-Wire-1; Option E)
    - 2026-05-04: Sprint 55.2 — BusinessServiceFactory per-request wiring (AD-BizDomain-1)
    - 2026-05-04: Sprint 53.6 US-4 — ServiceFactory through build_handler (closes AD-Front-2)
    - 2026-05-01: Sprint 52.5 P0 #11+#12 — Depends(get_current_tenant) + root TraceContext + 404
    - 2026-04-30: Sprint 50.2 Day 1.5 — initial: POST /chat SSE + GET/cancel sessions

Related:
    - .schemas (ChatRequest / ChatSessionResponse)
    - .handler (build_handler)
    - .sse (serialize_loop_event / format_sse_message — emits trace_id)
    - .session_registry (tenant-scoped storage)
    - api/main.py (mounts this router; installs TenantContextMiddleware)
    - platform_layer/identity (Depends source)
    - claudedocs/5-status/V2-AUDIT-W3-2-PHASE50-2.md (audit source)
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from agent_harness._contracts import LoopCompleted, TraceContext
from agent_harness.verification import run_with_verification
from business_domain._service_factory import BusinessServiceFactory
from core.config import get_settings
from infrastructure.db.session import get_db_session
from platform_layer.governance.service_factory import (
    ServiceFactory,
    get_service_factory,
)
from platform_layer.identity import get_current_tenant

from ._verifier_factory import select_verifier_registry
from .handler import build_handler
from .schemas import ChatRequest, ChatSessionResponse
from .session_registry import SessionRegistry, get_default_registry
from .sse import format_sse_message, serialize_loop_event

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", status_code=status.HTTP_200_OK)
async def chat(
    req: ChatRequest,
    current_tenant: UUID = Depends(get_current_tenant),
    factory: ServiceFactory = Depends(get_service_factory),
    db: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    """Run an agent loop and stream LoopEvents as SSE.

    Response is `text/event-stream` (per 02-architecture-design §SSE).
    Each frame is `event: <type>\\ndata: <json>\\n\\n`. The session_id is
    in the first `loop_start` frame's data, alongside the `trace_id` of
    the root TraceContext (frontend can correlate with Jaeger / logs).

    Sprint 53.6 US-4 — closes AD-Front-2: passes ServiceFactory through
    `build_handler` so AgentLoopImpl receives the production HITLManager.
    Cat 9 Stage 3 ESCALATE now flows through the full HITL pipeline
    (request_approval → notifier → reviewer UI → wait_for_decision → resume).
    Toggle off via env `HITL_ENABLED=false` (handler.py guards this).

    Sprint 55.2 US-3 — closes AD-BusinessDomainPartialSwap-1 at the wiring
    layer: builds a per-request BusinessServiceFactory(db, tenant_id, tracer=None)
    and passes the factory_provider lambda to build_handler. When
    settings.business_domain_mode='service', business-domain handlers route
    through DB-backed services (5 domains uniformly mode-aware). When
    'mock' (default), preserves 51.0/55.1 PoC behavior. Tracer=None per
    AD-Cat12-Helpers-1 deferred (Phase 56+).
    """
    settings = get_settings()
    business_factory = BusinessServiceFactory(
        db=db,
        tenant_id=current_tenant,
        tracer=None,  # D2: get_tracer factory deferred to Phase 56+
    )

    def business_factory_provider() -> BusinessServiceFactory:
        return business_factory

    try:
        loop = build_handler(
            req.mode,
            req.message,
            service_factory=factory,
            business_factory_provider=(
                business_factory_provider if settings.business_domain_mode == "service" else None
            ),
        )
    except (RuntimeError, ValueError) as exc:
        # Misconfiguration (env vars / unsupported mode) → 503.
        # Schema-layer errors (invalid mode literal) get caught by FastAPI
        # validation as 422 before reaching here.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    session_id = req.session_id or uuid4()
    registry = get_default_registry()
    await registry.register(current_tenant, session_id)

    # P0 #12 — root TraceContext established at API boundary. The loop
    # already accepts trace_context; sse.py will copy trace_id into every
    # SSE frame's data so SSE consumers can correlate with backend traces.
    trace_ctx = TraceContext(
        tenant_id=current_tenant,
        session_id=session_id,
    )

    return StreamingResponse(
        _stream_loop_events(
            loop,
            current_tenant,
            session_id,
            registry,
            user_input=req.message,
            trace_context=trace_ctx,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable nginx buffering for real-time
            "X-Session-Id": str(session_id),
            "X-Trace-Id": trace_ctx.trace_id,
        },
    )


async def _stream_loop_events(
    loop: object,  # AgentLoopImpl; loose-typed to avoid circular import noise
    tenant_id: UUID,
    session_id: UUID,
    registry: SessionRegistry,
    *,
    user_input: str,
    trace_context: TraceContext,
) -> AsyncIterator[bytes]:
    """Drive the loop generator + emit SSE bytes; finalize tenant-scoped registry.

    `user_input` is appended into the loop's messages as the first user turn.
    For ``echo_demo`` mode it is harmless (MockChatClient ignores the request);
    for ``real_llm`` it is what the model actually responds to.

    `trace_context` is the root context for this chat run — passed to
    ``loop.run`` so child spans (TurnStarted / LLMRequested / etc.) inherit
    the trace_id; sse.py extracts trace_id into each SSE event.

    Sprint 55.5 (AD-Cat10-Wire-1; Option E 2-mode post-D4+D5):
    Always invokes ``run_with_verification`` wrapper. When
    ``settings.chat_verification_mode == "disabled"`` (default), passes
    ``verifier_registry=None`` → wrapper transparently delegates to
    ``loop.run()`` per correction_loop.py:99-106 (byte-for-byte event stream
    identical to direct loop.run; backwards-compat preserved). When
    ``"enabled"``, passes a populated ``VerifierRegistry`` → wrapper runs
    verifiers + self-correction loop (max 2 attempts).
    """
    settings = get_settings()
    verifier_registry = select_verifier_registry(settings.chat_verification_mode)

    natural_completion = False
    try:
        async for event in run_with_verification(
            agent_loop=loop,  # type: ignore[arg-type]
            session_id=session_id,
            user_input=user_input,
            trace_context=trace_context,
            verifier_registry=verifier_registry,
            max_correction_attempts=2,
        ):
            try:
                payload = serialize_loop_event(event)
            except NotImplementedError:
                # Event types deferred to later sprints (HITL / Verification / etc.).
                logger.debug("sse: skip unserialized event %s", type(event).__name__)
                continue
            if payload is None:
                # Day 2: serializer signals "skip this event" (e.g. Thinking →
                # LLMResponded carries the canonical content).
                continue
            yield format_sse_message(payload["type"], payload["data"])
            if isinstance(event, LoopCompleted):
                natural_completion = True
                break
    except asyncio.CancelledError:
        logger.info(
            "chat session %s/%s: client disconnected mid-stream",
            tenant_id,
            session_id,
        )
        raise
    finally:
        if natural_completion:
            await registry.mark_completed(tenant_id, session_id)
        # else: leave status as-is (running / cancelled) — caller can poll GET.


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_session(
    session_id: UUID,
    current_tenant: UUID = Depends(get_current_tenant),
) -> ChatSessionResponse:
    """Return session status for THIS tenant; 404 on missing OR cross-tenant.

    Cross-tenant attempts deliberately return 404 (not 403) so the API does
    not reveal that the session exists under a different tenant.
    """
    registry = get_default_registry()
    entry = await registry.get(current_tenant, session_id)
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
async def cancel_session(
    session_id: UUID,
    current_tenant: UUID = Depends(get_current_tenant),
) -> None:
    """Cancel a running session for THIS tenant; 404 on missing OR cross-tenant.

    Same 404-on-cross-tenant rule as get_session — never reveal cross-tenant
    session existence.
    """
    registry = get_default_registry()
    found = await registry.cancel(current_tenant, session_id)
    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found.",
        )

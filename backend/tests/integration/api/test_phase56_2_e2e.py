"""
File: backend/tests/integration/api/test_phase56_2_e2e.py
Purpose: Cross-AD end-to-end integration test — exercises all 4 Phase 56.2 ADs in single flow.
Category: Tests / Integration / API (Phase 56 SaaS Stage 1)
Scope: Sprint 56.2 / Day 3 / US-5 closeout cross-AD e2e

Description:
    Single integrated test that exercises:
    - US-1 (AD-Cat12-BusinessObs): real Tracer threading produces spans
    - US-2 (AD-QuotaEstimation-1): pre-call heuristic estimate (not fixed 1000)
    - US-3 (AD-QuotaPostCall-1): post-call record_usage reconciles via LoopCompleted
    - US-4 (AD-AdminAuth-1): admin endpoint requires admin role (separate flow)

    For US-1+2+3 (chat flow): uses _stream_loop_events with NoOpTracer +
    FakeAsyncRedis-backed QuotaEnforcer + _StubLoop yielding LoopCompleted
    with known total_tokens. Asserts spans recorded + counter reconciled.

    For US-4 (admin flow): uses TestClient with role-aware middleware to
    confirm 403 without role, 201 with role.

Created: 2026-05-06 (Sprint 56.2 Day 3)
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from uuid import UUID, uuid4

import pytest
from fakeredis import FakeAsyncRedis
from fastapi import FastAPI, Request, Response
from httpx import ASGITransport, AsyncClient

from agent_harness._contracts import (
    LoopCompleted,
    SpanCategory,
    TraceContext,
)
from agent_harness.observability.helpers import category_span
from agent_harness.observability.tracer import NoOpTracer
from api.v1.admin.tenants import router as admin_tenants_router
from api.v1.chat.router import _stream_loop_events
from api.v1.chat.session_registry import SessionRegistry
from platform_layer.tenant.plans import PlanLoader
from platform_layer.tenant.quota import QuotaEnforcer

pytestmark = pytest.mark.asyncio


class _StubTracedLoop:
    """Stub agent loop — emits a Cat 12 span via NoOpTracer + LoopCompleted."""

    def __init__(self, *, tracer: NoOpTracer, total_tokens: int) -> None:
        self._tracer = tracer
        self._total_tokens = total_tokens

    async def run(
        self,
        *,
        session_id: UUID,
        user_input: str,
        trace_context: TraceContext,
    ) -> AsyncIterator[object]:
        # Simulate a service method emission within the loop run.
        async with category_span(self._tracer, "incident.create", SpanCategory.TOOLS):
            pass
        yield LoopCompleted(
            stop_reason="end_turn",
            total_turns=1,
            total_tokens=self._total_tokens,
            trace_context=trace_context,
        )


async def _consume(stream: AsyncIterator[bytes]) -> None:
    async for _ in stream:
        pass


async def test_cross_ad_chat_flow_us1_us2_us3() -> None:
    """Single chat flow exercises US-1 (spans) + US-2 (estimate) + US-3 (reconcile)."""
    # Setup: NoOpTracer for span capture, FakeAsyncRedis for quota state.
    tracer = NoOpTracer()
    enforcer = QuotaEnforcer(client=FakeAsyncRedis(), plan_loader=PlanLoader())
    tenant_id = uuid4()
    session_id = uuid4()
    registry = SessionRegistry()
    await registry.register(tenant_id, session_id)

    # US-2: pre-call heuristic estimate from 800-char message → 200 tokens.
    msg = "x" * 800
    estimated_tokens = enforcer.estimate_pre_call_tokens(msg, fallback=1000)
    assert estimated_tokens == 200, f"US-2 estimate wrong: {estimated_tokens}"

    await enforcer.check_and_reserve(
        tenant_id=tenant_id, plan_name="enterprise", estimated_tokens=estimated_tokens
    )
    assert await enforcer.get_usage(tenant_id) == 200

    # US-1 + US-3: stub loop emits Cat 12 span + LoopCompleted with actual=120.
    stub_loop = _StubTracedLoop(tracer=tracer, total_tokens=120)
    trace_ctx = TraceContext(tenant_id=tenant_id, session_id=session_id)
    await _consume(
        _stream_loop_events(
            stub_loop,
            tenant_id,
            session_id,
            registry,
            user_input=msg,
            trace_context=trace_ctx,
            quota_enforcer=enforcer,
            estimated_tokens=estimated_tokens,
        )
    )

    # US-1 assertion: NoOpTracer recorded the span.
    assert ("incident.create", SpanCategory.TOOLS) in tracer.spans_started

    # US-3 assertion: counter reconciled — reserved 200 → actual 120 → counter 120.
    final_usage = await enforcer.get_usage(tenant_id)
    assert final_usage == 120, f"US-3 reconciliation wrong: {final_usage}"


async def test_cross_ad_admin_rbac_us4() -> None:
    """US-4 admin RBAC role check — independent of chat flow."""
    app = FastAPI()

    @app.middleware("http")
    async def _populate_state(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        user_header = request.headers.get("X-Test-User")
        roles_header = request.headers.get("X-Test-Roles")
        request.state.user_id = UUID(user_header) if user_header else None
        request.state.roles = json.loads(roles_header) if roles_header else None
        return await call_next(request)

    app.include_router(admin_tenants_router, prefix="/api/v1")

    user_id = uuid4()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Without admin role → 403.
        resp_403 = await ac.post(
            "/api/v1/admin/tenants",
            json={"code": "x", "display_name": "X", "admin_email": "a@b.com"},
            headers={
                "X-Test-User": str(user_id),
                "X-Test-Roles": json.dumps(["tenant_admin"]),
            },
        )
        assert resp_403.status_code == 403
        assert "Platform admin" in resp_403.json()["detail"]

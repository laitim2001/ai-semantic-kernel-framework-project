"""
File: backend/tests/integration/api/test_chat_quota_reconcile.py
Purpose: Integration test — chat router pre-call estimate + post-call reconciliation.
Category: Tests / Integration / API (Phase 56 SaaS Stage 1)
Scope: Sprint 56.2 / Day 2 / 1 integration US-2 + 1 integration US-3.

Description:
    Exercises the full quota wire-up at the _stream_loop_events boundary
    by stubbing the agent_loop yield sequence (LoopCompleted with known
    total_tokens). Verifies:

    - test_chat_quota_uses_real_estimate (US-2 — AD-QuotaEstimation-1):
      pre-call reservation uses message-length heuristic, NOT fixed 1000.

    - test_chat_quota_reconciliation_releases_overreservation (US-3 —
      AD-QuotaPostCall-1): post-call record_usage releases over-reservation
      back to daily counter. Reserved 200 → actual 100 → counter delta 100.

Created: 2026-05-06 (Sprint 56.2 Day 2)
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from fakeredis import FakeAsyncRedis

from agent_harness._contracts import LoopCompleted, TraceContext
from api.v1.chat.router import _stream_loop_events
from api.v1.chat.session_registry import SessionRegistry
from platform_layer.tenant.plans import PlanLoader
from platform_layer.tenant.quota import QuotaEnforcer

pytestmark = pytest.mark.asyncio


class _StubLoop:
    """Minimal AgentLoopImpl stub — yields a single LoopCompleted with known tokens."""

    def __init__(self, total_tokens: int) -> None:
        self._total_tokens = total_tokens

    async def run(
        self,
        *,
        session_id: UUID,
        user_input: str,
        trace_context: TraceContext,
    ) -> AsyncIterator[object]:
        yield LoopCompleted(
            stop_reason="end_turn",
            total_turns=1,
            total_tokens=self._total_tokens,
            trace_context=trace_context,
        )


async def _consume(stream: AsyncIterator[bytes]) -> None:
    """Drain SSE bytes from _stream_loop_events to completion."""
    async for _ in stream:
        pass


async def test_chat_quota_uses_real_estimate() -> None:
    """US-2 — pre-call reservation uses heuristic, not fixed 1000."""
    enforcer = QuotaEnforcer(client=FakeAsyncRedis(), plan_loader=PlanLoader())
    tenant_id = uuid4()

    # 800-char message → estimate 200 (not fallback 1000).
    msg = "x" * 800
    estimate = enforcer.estimate_pre_call_tokens(msg, fallback=1000)
    assert estimate == 200

    # Simulate router pre-call reservation.
    await enforcer.check_and_reserve(
        tenant_id=tenant_id, plan_name="enterprise", estimated_tokens=estimate
    )
    assert await enforcer.get_usage(tenant_id) == 200


async def test_chat_quota_reconciliation_releases_overreservation() -> None:
    """US-3 — post-call record_usage releases over-reservation."""
    enforcer = QuotaEnforcer(client=FakeAsyncRedis(), plan_loader=PlanLoader())
    tenant_id = uuid4()
    session_id = uuid4()
    registry = SessionRegistry()
    await registry.register(tenant_id, session_id)

    # Pre-call reserve 200.
    estimated_tokens = 200
    await enforcer.check_and_reserve(
        tenant_id=tenant_id, plan_name="enterprise", estimated_tokens=estimated_tokens
    )
    assert await enforcer.get_usage(tenant_id) == 200

    # Stream loop emits LoopCompleted with actual=100; _stream_loop_events
    # observes the event and calls record_usage(actual=100, reserved=200).
    stub_loop = _StubLoop(total_tokens=100)
    trace_ctx = TraceContext(tenant_id=tenant_id, session_id=session_id)
    await _consume(
        _stream_loop_events(
            stub_loop,
            tenant_id,
            session_id,
            registry,
            user_input="x" * 800,
            trace_context=trace_ctx,
            quota_enforcer=enforcer,
            estimated_tokens=estimated_tokens,
        )
    )

    # Counter delta released: 200 reserved → 100 actual → counter = 100.
    assert await enforcer.get_usage(tenant_id) == 100

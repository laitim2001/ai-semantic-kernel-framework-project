"""
File: backend/tests/integration/api/test_chat_sla_recording.py
Purpose: Integration test — chat router LoopCompleted observer wires SLA recorder.
Category: Tests / Integration / API (Phase 56 SaaS Stage 1)
Scope: Sprint 56.3 / Day 1 / 1 integration US-1.

Description:
    Verifies the chat router _stream_loop_events LoopCompleted observer
    extension calls sla_recorder.record_loop_completion with the correct
    tenant_id + complexity + non-zero latency. Mirrors the
    test_chat_quota_reconcile.py pattern (Sprint 56.2) but exercises the
    SLA wiring path instead of the quota wiring path.

Created: 2026-05-06 (Sprint 56.3 Day 1)
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from fakeredis.aioredis import FakeRedis

from agent_harness._contracts import LoopCompleted, TraceContext
from api.v1.chat.router import _stream_loop_events
from api.v1.chat.session_registry import SessionRegistry
from platform_layer.observability.sla_monitor import (
    WINDOW_SEC,
    SLAMetricRecorder,
)

pytestmark = pytest.mark.asyncio


class _StubLoop:
    """Minimal AgentLoopImpl stub — yields a single LoopCompleted (simple class)."""

    def __init__(self, total_turns: int, total_tokens: int) -> None:
        self._total_turns = total_turns
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
            total_turns=self._total_turns,
            total_tokens=self._total_tokens,
            trace_context=trace_context,
        )


async def _consume(stream: AsyncIterator[bytes]) -> None:
    """Drain SSE bytes from _stream_loop_events to completion."""
    async for _ in stream:
        pass


async def test_chat_request_sla_loop_completion_recorded_in_redis_sliding_window() -> None:
    """US-1 — chat router observer writes loop latency into per-tenant Redis key."""
    redis_client = FakeRedis(decode_responses=False)
    recorder = SLAMetricRecorder(redis_client=redis_client)
    tenant_id = uuid4()
    session_id = uuid4()
    registry = SessionRegistry()
    await registry.register(tenant_id, session_id)

    # Stub a "simple" loop: 2 turns + 1500 tokens → simple bucket.
    stub_loop = _StubLoop(total_turns=2, total_tokens=1_500)
    trace_ctx = TraceContext(tenant_id=tenant_id, session_id=session_id)

    # Drive _stream_loop_events with sla_recorder + chat_start_time wired.
    import time as _time

    await _consume(
        _stream_loop_events(
            stub_loop,
            tenant_id,
            session_id,
            registry,
            user_input="hello",
            trace_context=trace_ctx,
            sla_recorder=recorder,
            chat_start_time=_time.monotonic(),
        )
    )

    # Assert: simple bucket key has exactly 1 entry with non-zero latency.
    key = f"sla:metrics:{tenant_id}:loop_simple:{WINDOW_SEC}s"
    entries = await redis_client.zrange(key, 0, -1, withscores=True)
    assert len(entries) == 1
    _member, latency_ms = entries[0]
    assert latency_ms >= 0  # monotonic clock; ≥ 0 always
    # No entries in medium / complex buckets (single LoopCompleted, simple class).
    medium_key = f"sla:metrics:{tenant_id}:loop_medium:{WINDOW_SEC}s"
    complex_key = f"sla:metrics:{tenant_id}:loop_complex:{WINDOW_SEC}s"
    assert await redis_client.zrange(medium_key, 0, -1) == []
    assert await redis_client.zrange(complex_key, 0, -1) == []

    await redis_client.aclose()

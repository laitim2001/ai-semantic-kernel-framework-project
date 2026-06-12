"""
File: backend/tests/integration/api/test_subagent_transcript_observer.py
Purpose: Integration tests for the sidechain transcript observer (Sprint 57.107 US-4).
Category: Tests / Integration / API
Scope: Phase 57 / Sprint 57.107 Day 2 / US-4

Description:
    Drives the REAL `_stream_loop_events` with a fake loop whose run() appends
    SubagentSpawned / SubagentChildEvent / SubagentCompleted into the router's
    subagent_event_buffer (simulating the dispatcher emitting while the parent
    loop awaits task_spawn). Asserts:
    - a sidechain `sessions` row (id=subagent_id, is_sidechain=True,
      parent_session_id=parent) is created on Spawned
    - per-turn `message_events` rows (the table's FIRST consumer) with a
      monotonic sequence_num are written for each SubagentChildEvent
    - Completed marks the sidechain completed + folds summary/tokens into
      meta_data
    - the observer is env-gated (SUBAGENT_TRANSCRIPT_OBSERVER=false → no rows)
    - tenant isolation: the sidechain row is invisible cross-tenant (鐵律)

Created: 2026-06-12 (Sprint 57.107 Day 2 / US-4)

Modification History (newest-first):
    - 2026-06-12: Initial creation (Sprint 57.107 Day 2 / US-4)

Related:
    - api/v1/chat/router.py (_persist_subagent_transcript)
    - infrastructure/db/models/sessions.py (Session sidechain columns + MessageEvent)
    - sprint-57-107-plan.md §3.4
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_harness._contracts import LoopCompleted, LoopEvent, TraceContext
from agent_harness._contracts.events import (
    SubagentChildEvent,
    SubagentCompleted,
    SubagentSpawned,
    TurnStarted,
)
from api.v1.chat.router import _stream_loop_events
from api.v1.chat.session_registry import get_default_registry
from infrastructure.db.models.sessions import MessageEvent
from infrastructure.db.models.sessions import Session as SessionModel
from infrastructure.db.repositories import SessionRepository
from tests.conftest import seed_tenant, seed_user

pytestmark = pytest.mark.asyncio


class _SpawningLoop:
    """Fake AgentLoop: fills the subagent buffer mid-run, then completes."""

    def __init__(self, *, buffer: list[LoopEvent], subagent_id: UUID) -> None:
        self._buffer = buffer
        self._sid = subagent_id

    async def run(
        self,
        *,
        session_id: UUID,
        user_input: str,
        trace_context: TraceContext | None = None,
    ) -> AsyncIterator[LoopEvent]:
        # Simulate the dispatcher emitting while the loop awaits task_spawn:
        # the events land in the router buffer BEFORE the next loop event.
        self._buffer.append(
            SubagentSpawned(subagent_id=self._sid, mode="fork", parent_session_id=session_id)
        )
        self._buffer.append(
            SubagentChildEvent(subagent_id=self._sid, inner=TurnStarted(turn_num=0))
        )
        self._buffer.append(
            SubagentChildEvent(subagent_id=self._sid, inner=TurnStarted(turn_num=1))
        )
        self._buffer.append(
            SubagentCompleted(subagent_id=self._sid, summary="child finding", tokens_used=42)
        )
        yield LoopCompleted(stop_reason="end_turn", total_turns=1, trace_context=trace_context)


async def _seed_parent_session(db: AsyncSession, *, tenant_id: UUID, user_id: UUID) -> SessionModel:
    row = SessionModel(id=uuid4(), tenant_id=tenant_id, user_id=user_id, status="active")
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def _drive(
    db: AsyncSession, *, tenant_id: UUID, parent_id: UUID, user_id: UUID, subagent_id: UUID
) -> None:
    buffer: list[LoopEvent] = []
    loop = _SpawningLoop(buffer=buffer, subagent_id=subagent_id)
    registry = get_default_registry()
    await registry.register(tenant_id, parent_id)
    trace_ctx = TraceContext(tenant_id=tenant_id, session_id=parent_id, user_id=user_id)
    async for _frame in _stream_loop_events(
        loop,
        tenant_id,
        parent_id,
        registry,
        user_input="spawn a subagent",
        trace_context=trace_ctx,
        db=db,
        subagent_event_buffer=buffer,
    ):
        pass


async def test_observer_persists_sidechain_transcript(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SUBAGENT_TRANSCRIPT_OBSERVER", "true")
    tenant = await seed_tenant(db_session, code="SIDECHAIN_T")
    user = await seed_user(db_session, tenant, email="sidechain@test.com")
    parent = await _seed_parent_session(db_session, tenant_id=tenant.id, user_id=user.id)
    sid = uuid4()

    await _drive(
        db_session, tenant_id=tenant.id, parent_id=parent.id, user_id=user.id, subagent_id=sid
    )

    # (a) sidechain session row created + completed + summary folded.
    row = (
        await db_session.execute(select(SessionModel).where(SessionModel.id == sid))
    ).scalar_one()
    assert row.is_sidechain is True
    assert row.parent_session_id == parent.id
    assert row.tenant_id == tenant.id
    assert row.title == "Subagent · fork"
    assert row.status == "completed"
    assert row.meta_data["mode"] == "fork"
    assert row.meta_data["summary"] == "child finding"
    assert row.meta_data["tokens_used"] == 42

    # (b) per-turn message_events rows (first consumer) with monotonic sequence.
    events = (
        (
            await db_session.execute(
                select(MessageEvent)
                .where(MessageEvent.session_id == sid)
                .order_by(MessageEvent.sequence_num)
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 2
    assert [e.sequence_num for e in events] == [1, 2]
    assert all(e.event_type == "subagent_child" for e in events)
    assert all(e.tenant_id == tenant.id for e in events)
    # event_data stores the serializer's data dict (the {inner_type, inner} wrap).
    assert "inner_type" in events[0].event_data
    assert events[0].event_data["inner"]["turn_num"] == 0


async def test_observer_env_gated_off_writes_nothing(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SUBAGENT_TRANSCRIPT_OBSERVER", "false")
    tenant = await seed_tenant(db_session, code="SIDECHAIN_OFF")
    user = await seed_user(db_session, tenant, email="sidechain@off.test")
    parent = await _seed_parent_session(db_session, tenant_id=tenant.id, user_id=user.id)
    sid = uuid4()

    await _drive(
        db_session, tenant_id=tenant.id, parent_id=parent.id, user_id=user.id, subagent_id=sid
    )

    row = (
        await db_session.execute(select(SessionModel).where(SessionModel.id == sid))
    ).scalar_one_or_none()
    assert row is None


async def test_sidechain_invisible_cross_tenant(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The sidechain row is tenant-scoped (multi-tenant 鐵律)."""
    monkeypatch.setenv("SUBAGENT_TRANSCRIPT_OBSERVER", "true")
    tenant_a = await seed_tenant(db_session, code="SIDECHAIN_XT_A")
    tenant_b = await seed_tenant(db_session, code="SIDECHAIN_XT_B")
    user_a = await seed_user(db_session, tenant_a, email="xt_a@sidechain.test")
    parent = await _seed_parent_session(db_session, tenant_id=tenant_a.id, user_id=user_a.id)
    sid = uuid4()

    await _drive(
        db_session, tenant_id=tenant_a.id, parent_id=parent.id, user_id=user_a.id, subagent_id=sid
    )

    repo = SessionRepository(db_session)
    assert await repo.get_session(session_id=sid, tenant_id=tenant_b.id) is None
    assert await repo.get_session(session_id=sid, tenant_id=tenant_a.id) is not None

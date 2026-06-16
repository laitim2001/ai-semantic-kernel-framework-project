"""
File: backend/tests/integration/api/test_chat_resume_persistence.py
Purpose: Integration tests for the RESUME-path transcript observer (Sprint 57.128).
Category: Tests / Integration / API
Scope: Phase 57 / Sprint 57.128 (AD-ChatV2-Resume-Transcript-Persistence)

Description:
    Drives the REAL `_stream_resume_events` with a fake loop whose `resume()`
    yields post-resume LoopEvents. Closes AD-ChatV2-Resume-Transcript-Persistence
    — before this, `_stream_resume_events` omitted the `_persist_main_event` call
    its send-path sibling `_stream_loop_events` has, so a paused-then-resumed
    session's replay stopped at the pause. Asserts:
    - each serializable post-resume event → a `message_events` row keyed by the
      session_id (NO `user_message` row — resume has no new user prompt)
    - Thinking (serializer returns None) is NOT persisted
    - the post-resume sequence_num CONTINUES from the session's MAX (the pre-pause
      events) so a replay folds them after the pre-pause frames (57.126 ordering)
    - the observer is env-gated (MAIN_TRANSCRIPT_OBSERVER=false → no rows)
    - tenant isolation: a resume bound to tenant A is invisible under tenant B (鐵律)

Created: 2026-06-16 (Sprint 57.128)

Modification History (newest-first):
    - 2026-06-16: Initial creation (Sprint 57.128 — resume transcript writer)

Related:
    - api/v1/chat/router.py (_stream_resume_events persist + resume_chat wiring)
    - test_main_transcript_persist.py (the send-path sibling harness)
    - sprint-57-128-plan.md §3.3
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_harness._contracts import LoopCompleted, LoopEvent, TraceContext
from agent_harness._contracts.events import LLMRequested, Thinking, TurnStarted
from api.v1.chat.router import _persist_main_event, _stream_resume_events
from infrastructure.db.models.sessions import MessageEvent
from infrastructure.db.models.sessions import Session as SessionModel
from tests.conftest import seed_tenant, seed_user

pytestmark = pytest.mark.asyncio


class _ResumingLoop:
    """Fake AgentLoop: resume() yields a fixed post-resume event sequence.

    Mirrors the post-approval continuation (the approved tool ran on the original
    run; resume continues to end_turn). `state` is ignored (the real loop rehydrates
    from it; the fake just emits a deterministic stream).
    """

    async def resume(
        self, *, state: object, trace_context: TraceContext | None = None
    ) -> AsyncIterator[LoopEvent]:
        yield TurnStarted(turn_num=1, trace_context=trace_context)
        # Thinking → serializer returns None → must NOT be persisted.
        yield Thinking(text="(resuming)", trace_context=trace_context)
        yield LLMRequested(model="gpt-x", tokens_in=7, trace_context=trace_context)
        yield LoopCompleted(stop_reason="end_turn", total_turns=2, trace_context=trace_context)


async def _seed_main_session(db: AsyncSession, *, tenant_id: UUID, user_id: UUID) -> UUID:
    sid = uuid4()
    db.add(SessionModel(id=sid, tenant_id=tenant_id, user_id=user_id, status="active"))
    await db.flush()
    return sid


async def _drive_resume(
    db: AsyncSession, *, tenant_id: UUID, session_id: UUID, user_id: UUID
) -> None:
    loop = _ResumingLoop()
    trace_ctx = TraceContext(tenant_id=tenant_id, session_id=session_id, user_id=user_id)
    async for _frame in _stream_resume_events(
        loop,  # duck-typed; only .resume() is called
        state=object(),  # the fake ignores it
        trace_context=trace_ctx,
        tenant_id=tenant_id,
        session_id=session_id,
        db=db,
    ):
        pass


async def test_resume_persists_post_resume_events(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MAIN_TRANSCRIPT_OBSERVER", "true")
    tenant = await seed_tenant(db_session, code="RESUMETX")
    user = await seed_user(db_session, tenant, email="resume@tx.test")
    session_id = await _seed_main_session(db_session, tenant_id=tenant.id, user_id=user.id)

    await _drive_resume(db_session, tenant_id=tenant.id, session_id=session_id, user_id=user.id)

    events = (
        (
            await db_session.execute(
                select(MessageEvent)
                .where(MessageEvent.session_id == session_id)
                .order_by(MessageEvent.sequence_num)
            )
        )
        .scalars()
        .all()
    )
    # post-resume: turn_start + llm_request + loop_end; Thinking skipped (None);
    # NO user_message row (resume has no new user prompt).
    assert [e.event_type for e in events] == ["turn_start", "llm_request", "loop_end"]
    assert [e.sequence_num for e in events] == [1, 2, 3]
    assert all(e.tenant_id == tenant.id for e in events)
    assert events[0].event_data["turn_num"] == 1
    assert events[1].event_data["model"] == "gpt-x"
    assert events[2].event_data["stop_reason"] == "end_turn"
    assert "trace_id" in events[0].event_data


async def test_resume_seq_continues_past_pre_pause_max(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Post-resume seq continues AFTER the pre-pause events — `main_seq` seeds from
    the session MAX so a replay folds the resume turns after the pre-pause frames
    (the 57.126 monotonic-ordering logic), not restarting at 1 → no collision."""
    monkeypatch.setenv("MAIN_TRANSCRIPT_OBSERVER", "true")
    tenant = await seed_tenant(db_session, code="RESUMESEQ")
    user = await seed_user(db_session, tenant, email="resume@seq.test")
    session_id = await _seed_main_session(db_session, tenant_id=tenant.id, user_id=user.id)
    # Simulate the pre-pause events the original send already persisted (seq 1..5).
    for i in range(1, 6):
        await _persist_main_event(
            {"type": "turn_start", "data": {"turn_num": 0}},
            db=db_session,
            tenant_id=tenant.id,
            session_id=session_id,
            sequence_num=i,
        )

    await _drive_resume(db_session, tenant_id=tenant.id, session_id=session_id, user_id=user.id)

    seqs = [
        r.sequence_num
        for r in (
            await db_session.execute(
                select(MessageEvent)
                .where(MessageEvent.session_id == session_id)
                .order_by(MessageEvent.sequence_num)
            )
        )
        .scalars()
        .all()
    ]
    # 5 pre-pause + 3 post-resume = 8 rows, strictly monotonic, no UNIQUE collision.
    assert seqs == [1, 2, 3, 4, 5, 6, 7, 8]


async def test_resume_env_gated_off_writes_nothing(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MAIN_TRANSCRIPT_OBSERVER", "false")
    tenant = await seed_tenant(db_session, code="RESUMEOFF")
    user = await seed_user(db_session, tenant, email="resume@off.test")
    session_id = await _seed_main_session(db_session, tenant_id=tenant.id, user_id=user.id)

    await _drive_resume(db_session, tenant_id=tenant.id, session_id=session_id, user_id=user.id)

    rows = (
        (
            await db_session.execute(
                select(MessageEvent).where(MessageEvent.session_id == session_id)
            )
        )
        .scalars()
        .all()
    )
    assert rows == []


async def test_resume_invisible_cross_tenant(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Resume rows are tenant-scoped (multi-tenant 鐵律)."""
    monkeypatch.setenv("MAIN_TRANSCRIPT_OBSERVER", "true")
    tenant_a = await seed_tenant(db_session, code="RESUMEXT_A")
    tenant_b = await seed_tenant(db_session, code="RESUMEXT_B")
    user_a = await seed_user(db_session, tenant_a, email="xt_a@resume.test")
    session_id = await _seed_main_session(db_session, tenant_id=tenant_a.id, user_id=user_a.id)

    await _drive_resume(db_session, tenant_id=tenant_a.id, session_id=session_id, user_id=user_a.id)

    b_rows = (
        (
            await db_session.execute(
                select(MessageEvent)
                .where(MessageEvent.session_id == session_id)
                .where(MessageEvent.tenant_id == tenant_b.id)
            )
        )
        .scalars()
        .all()
    )
    assert b_rows == []

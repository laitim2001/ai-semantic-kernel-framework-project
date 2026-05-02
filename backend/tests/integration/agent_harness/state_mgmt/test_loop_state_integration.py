"""
File: backend/tests/integration/agent_harness/state_mgmt/test_loop_state_integration.py
Purpose: US-4 integration test — AgentLoopImpl + DefaultReducer + DBCheckpointer end-to-end.
Category: Tests / 范疇 1 + 范疇 7
Scope: Phase 53.1 / Sprint 53.1 Day 3

Description:
    Verifies that when AgentLoopImpl is constructed with reducer + checkpointer +
    tenant_id, the loop emits StateCheckpointed events at safe points (post-LLM,
    post-tool) and writes corresponding rows to the state_snapshots table.

    Acceptance (per plan §US-4):
    - 3-turn loop (2 tool calls + 1 final) → DB ≥ 5 snapshots ✅
    - StateCheckpointed events emitted with monotonic DB chain version
    - 51.x baseline preserved when reducer/checkpointer/tenant_id NOT injected

Pre-requisite: docker compose -f docker-compose.dev.yml up -d postgres
              cd backend && alembic upgrade head

Created: 2026-05-02 (Sprint 53.1 Day 3)
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters._testing.mock_clients import MockChatClient
from agent_harness._contracts import (
    ChatResponse,
    StateCheckpointed,
    StopReason,
    ToolCall,
)
from agent_harness.orchestrator_loop import AgentLoopImpl
from agent_harness.output_parser import OutputParserImpl
from agent_harness.state_mgmt import DBCheckpointer, DefaultReducer
from agent_harness.tools import make_echo_executor
from infrastructure.db.models import Session as SessionModel
from infrastructure.db.models import StateSnapshot
from tests.conftest import seed_tenant, seed_user


@pytest.mark.asyncio
async def test_loop_emits_state_checkpoints_to_db(db_session: AsyncSession) -> None:
    """3-turn loop with 2 tool calls + 1 final → 5 state_snapshot rows in DB."""
    # === DB seed: tenant + user + session row ================================
    tenant = await seed_tenant(db_session, code="LOOP_INT")
    user = await seed_user(db_session, tenant, email="loopint@test.com")
    session_row = SessionModel(tenant_id=tenant.id, user_id=user.id)
    db_session.add(session_row)
    await db_session.flush()
    await db_session.refresh(session_row)

    # === Mock LLM scripted for 3 turns =======================================
    registry, executor = make_echo_executor()
    chat = MockChatClient(
        responses=[
            # Turn 1: tool call
            ChatResponse(
                model="m",
                content="calling echo 1",
                tool_calls=[ToolCall(id="call_1", name="echo_tool", arguments={"text": "first"})],
                stop_reason=StopReason.TOOL_USE,
            ),
            # Turn 2: tool call
            ChatResponse(
                model="m",
                content="calling echo 2",
                tool_calls=[ToolCall(id="call_2", name="echo_tool", arguments={"text": "second"})],
                stop_reason=StopReason.TOOL_USE,
            ),
            # Turn 3: final answer
            ChatResponse(
                model="m",
                content="Done.",
                stop_reason=StopReason.END_TURN,
            ),
        ]
    )

    # === AgentLoopImpl with Cat 7 wiring =====================================
    reducer = DefaultReducer()
    checkpointer = DBCheckpointer(db_session, session_id=session_row.id, tenant_id=tenant.id)
    loop = AgentLoopImpl(
        chat_client=chat,
        output_parser=OutputParserImpl(),
        tool_executor=executor,
        tool_registry=registry,
        system_prompt="You are an echo assistant.",
        max_turns=5,
        token_budget=10_000,
        reducer=reducer,
        checkpointer=checkpointer,
        tenant_id=tenant.id,
    )

    events = [ev async for ev in loop.run(session_id=session_row.id, user_input="echo")]

    # === Assertion 1: StateCheckpointed events emitted =======================
    checkpoint_events = [e for e in events if isinstance(e, StateCheckpointed)]
    # Expected: post-LLM(t0) + post-tool(t0) + post-LLM(t1) + post-tool(t1) + post-LLM(t2 final)
    assert (
        len(checkpoint_events) == 5
    ), f"expected 5 StateCheckpointed events, got {len(checkpoint_events)}"
    versions = [e.version for e in checkpoint_events]
    assert versions == sorted(versions), f"versions must be monotonic; got {versions}"
    assert versions[0] == 1, f"first DB chain version must be 1; got {versions[0]}"
    assert versions[-1] == 5, f"final DB chain version must be 5; got {versions[-1]}"

    # === Assertion 2: state_snapshots DB rows ================================
    result = await db_session.execute(
        select(StateSnapshot)
        .where(StateSnapshot.session_id == session_row.id)
        .order_by(StateSnapshot.version)
    )
    snapshots = list(result.scalars())
    assert len(snapshots) == 5
    assert [s.version for s in snapshots] == [1, 2, 3, 4, 5]

    # === Assertion 3: tenant_id correctly stamped ============================
    for snap in snapshots:
        assert snap.tenant_id == tenant.id

    # === Assertion 4: reasons reflect safe points ============================
    reasons = [s.reason for s in snapshots]
    assert "orchestrator_loop:post_llm" in reasons
    assert "orchestrator_loop:post_tool" in reasons


@pytest.mark.asyncio
async def test_loop_without_cat7_wiring_skips_checkpoints(
    db_session: AsyncSession,
) -> None:
    """When reducer/checkpointer/tenant_id NOT injected, no DB writes (51.x compat)."""
    tenant = await seed_tenant(db_session, code="LOOP_NO_C7")
    user = await seed_user(db_session, tenant, email="nocat7@test.com")
    session_row = SessionModel(tenant_id=tenant.id, user_id=user.id)
    db_session.add(session_row)
    await db_session.flush()
    await db_session.refresh(session_row)

    registry, executor = make_echo_executor()
    chat = MockChatClient(
        responses=[
            ChatResponse(
                model="m",
                content="quick",
                stop_reason=StopReason.END_TURN,
            ),
        ]
    )
    loop = AgentLoopImpl(
        chat_client=chat,
        output_parser=OutputParserImpl(),
        tool_executor=executor,
        tool_registry=registry,
        max_turns=3,
        token_budget=10_000,
        # reducer / checkpointer / tenant_id NOT passed → 51.x baseline
    )

    events = [ev async for ev in loop.run(session_id=session_row.id, user_input="hi")]

    # No StateCheckpointed events
    assert not any(isinstance(e, StateCheckpointed) for e in events)

    # No state_snapshots rows for this session
    result = await db_session.execute(
        select(StateSnapshot).where(StateSnapshot.session_id == session_row.id)
    )
    assert list(result.scalars()) == []


@pytest.mark.asyncio
async def test_loop_partial_cat7_wiring_no_crash(db_session: AsyncSession) -> None:
    """If only reducer is set (checkpointer / tenant_id missing), still no checkpoints."""
    tenant = await seed_tenant(db_session, code="LOOP_PARTIAL")
    user = await seed_user(db_session, tenant, email="partial@test.com")
    session_row = SessionModel(tenant_id=tenant.id, user_id=user.id)
    db_session.add(session_row)
    await db_session.flush()
    await db_session.refresh(session_row)

    registry, executor = make_echo_executor()
    chat = MockChatClient(
        responses=[
            ChatResponse(
                model="m",
                content="ok",
                stop_reason=StopReason.END_TURN,
            ),
        ]
    )
    loop = AgentLoopImpl(
        chat_client=chat,
        output_parser=OutputParserImpl(),
        tool_executor=executor,
        tool_registry=registry,
        max_turns=3,
        token_budget=10_000,
        reducer=DefaultReducer(),  # ← only reducer; missing checkpointer + tenant_id
    )

    # Should not crash; checkpoints are no-op due to ALL-three guard.
    events = [ev async for ev in loop.run(session_id=session_row.id, user_input="hi")]
    assert not any(isinstance(e, StateCheckpointed) for e in events)

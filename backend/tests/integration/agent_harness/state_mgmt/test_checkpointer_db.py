"""
File: backend/tests/integration/agent_harness/state_mgmt/test_checkpointer_db.py
Purpose: Integration tests for DBCheckpointer against real PostgreSQL.
Category: Tests / 范疇 7
Scope: Phase 53.1 / Sprint 53.1 Day 2

Description:
    Real-PG integration tests for the V2 范疇 7 DBCheckpointer:
    - save() + load() round-trip equality
    - save() multiple versions then time_travel(K) returns correct K
    - tenant isolation: tenant_b cannot load tenant_a's snapshots
    - StateMismatchError when state binding mismatches checkpointer
    - DB row size constraint (US-3 < 5KB)
    - append-only: parent_hash chain enforced

Pre-requisite (per tests/conftest.py):
    docker compose -f docker-compose.dev.yml up -d postgres
    cd backend && alembic upgrade head

Created: 2026-05-02 (Sprint 53.1 Day 2)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_harness._contracts import (
    DurableState,
    LoopState,
    StateVersion,
    TransientState,
)
from agent_harness.state_mgmt import (
    DBCheckpointer,
    StateMismatchError,
    StateNotFoundError,
)
from infrastructure.db.models import Session as SessionModel
from infrastructure.db.models import StateSnapshot
from tests.conftest import seed_tenant, seed_user


async def _build_session(
    db_session: AsyncSession, *, tenant_code: str = "CHKPT_TEST"
) -> tuple[SessionModel, object]:
    """Helper: seed tenant + user + session row; return (session, tenant)."""
    tenant = await seed_tenant(db_session, code=tenant_code)
    user = await seed_user(db_session, tenant, email=f"{tenant_code.lower()}@test.com")
    session_row = SessionModel(tenant_id=tenant.id, user_id=user.id)
    db_session.add(session_row)
    await db_session.flush()
    await db_session.refresh(session_row)
    return session_row, tenant


def _state_for(
    session_id,
    tenant_id,
    *,
    version: int = 0,
    current_turn: int = 0,
    source_category: str = "orchestrator_loop",
) -> LoopState:
    return LoopState(
        transient=TransientState(current_turn=current_turn),
        durable=DurableState(session_id=session_id, tenant_id=tenant_id),
        version=StateVersion(
            version=version,
            parent_version=None if version == 0 else version - 1,
            created_at=datetime.now(timezone.utc),
            created_by_category=source_category,
        ),
    )


@pytest.mark.asyncio
async def test_save_load_round_trip(db_session: AsyncSession) -> None:
    """save() then load() returns equivalent durable + version metadata."""
    session_row, tenant = await _build_session(db_session, tenant_code="RT")
    cp = DBCheckpointer(db_session, session_id=session_row.id, tenant_id=tenant.id)

    state = _state_for(
        session_row.id,
        tenant.id,
        version=0,
        current_turn=1,
        source_category="orchestrator_loop",
    )
    persisted_v = await cp.save(state)
    assert persisted_v.version == 1  # 49.2 helper bumps to 1 (parent None)
    assert persisted_v.created_by_category == "orchestrator_loop"

    loaded = await cp.load(version=1)
    assert loaded.durable.session_id == session_row.id
    assert loaded.durable.tenant_id == tenant.id
    assert loaded.transient.current_turn == 1
    assert loaded.transient.messages == []  # US-3: empty buffer
    # version from DB chain (authoritative) — append_snapshot bumps to 1
    assert loaded.version.version == 1
    assert loaded.version.created_by_category == "orchestrator_loop"


@pytest.mark.asyncio
async def test_save_multiple_versions_then_time_travel(db_session: AsyncSession) -> None:
    """Save v1, v2, v3; time_travel(2) returns v2 turn_num."""
    session_row, tenant = await _build_session(db_session, tenant_code="TT")
    cp = DBCheckpointer(db_session, session_id=session_row.id, tenant_id=tenant.id)

    for turn in range(1, 4):
        state = _state_for(
            session_row.id,
            tenant.id,
            version=turn - 1,
            current_turn=turn,
            source_category=f"turn_{turn}",
        )
        await cp.save(state)

    # Verify 3 snapshots in DB
    result = await db_session.execute(
        select(StateSnapshot)
        .where(StateSnapshot.session_id == session_row.id)
        .order_by(StateSnapshot.version)
    )
    snapshots = list(result.scalars())
    assert len(snapshots) == 3
    assert [s.version for s in snapshots] == [1, 2, 3]
    assert [s.turn_num for s in snapshots] == [1, 2, 3]

    # Time-travel to v2
    s2 = await cp.time_travel(target_version=2)
    assert s2.transient.current_turn == 2
    assert s2.version.created_by_category == "turn_2"


@pytest.mark.asyncio
async def test_tenant_isolation(db_session: AsyncSession) -> None:
    """tenant_b's checkpointer cannot load tenant_a's snapshot."""
    session_a, tenant_a = await _build_session(db_session, tenant_code="ISO_A")
    cp_a = DBCheckpointer(db_session, session_id=session_a.id, tenant_id=tenant_a.id)

    state_a = _state_for(session_a.id, tenant_a.id, version=0, current_turn=1)
    await cp_a.save(state_a)

    # Build cp_b bound to tenant_b but pointing at session_a's id (attacker probe)
    tenant_b_id = uuid4()
    cp_b = DBCheckpointer(db_session, session_id=session_a.id, tenant_id=tenant_b_id)
    with pytest.raises(StateNotFoundError):
        await cp_b.load(version=1)


@pytest.mark.asyncio
async def test_state_mismatch_session_id_raises(db_session: AsyncSession) -> None:
    """save() rejects state with mismatched session_id."""
    session_row, tenant = await _build_session(db_session, tenant_code="MM_SID")
    cp = DBCheckpointer(db_session, session_id=session_row.id, tenant_id=tenant.id)

    bad_state = _state_for(uuid4(), tenant.id, version=0, current_turn=1)
    with pytest.raises(StateMismatchError, match="session_id"):
        await cp.save(bad_state)


@pytest.mark.asyncio
async def test_state_mismatch_tenant_id_raises(db_session: AsyncSession) -> None:
    """save() rejects state with mismatched tenant_id."""
    session_row, tenant = await _build_session(db_session, tenant_code="MM_TID")
    cp = DBCheckpointer(db_session, session_id=session_row.id, tenant_id=tenant.id)

    bad_state = _state_for(session_row.id, uuid4(), version=0, current_turn=1)
    with pytest.raises(StateMismatchError, match="tenant_id"):
        await cp.save(bad_state)


@pytest.mark.asyncio
async def test_load_unknown_version_raises(db_session: AsyncSession) -> None:
    """load() raises StateNotFoundError when version doesn't exist."""
    session_row, tenant = await _build_session(db_session, tenant_code="MISSING")
    cp = DBCheckpointer(db_session, session_id=session_row.id, tenant_id=tenant.id)

    with pytest.raises(StateNotFoundError):
        await cp.load(version=999)


@pytest.mark.asyncio
async def test_db_row_size_under_5kb(db_session: AsyncSession) -> None:
    """US-3 acceptance: state_data JSONB stays small even with mock heavy transient."""
    session_row, tenant = await _build_session(db_session, tenant_code="SIZE")
    cp = DBCheckpointer(db_session, session_id=session_row.id, tenant_id=tenant.id)

    state = _state_for(session_row.id, tenant.id, version=0, current_turn=10)
    # Heavy metadata stress (still bounded but realistic)
    state.durable.metadata = {f"flag_{i}": f"val_{i}" for i in range(20)}
    await cp.save(state)

    result = await db_session.execute(
        select(StateSnapshot).where(StateSnapshot.session_id == session_row.id)
    )
    row = result.scalar_one()
    encoded = json.dumps(row.state_data)
    assert len(encoded) < 5 * 1024, f"row size {len(encoded)} exceeds 5KB"

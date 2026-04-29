"""
File: backend/tests/unit/infrastructure/db/test_state_race.py
Purpose: AC-3 verification — StateVersion 雙因子 (counter + content_hash) optimistic concurrency.
Category: Tests / Infrastructure / DB / StateVersion race
Scope: Sprint 49.2 Day 4.5

Description:
    Two concurrent workers attempt to append a state snapshot at the same
    parent_version with the same expected_parent_hash. Exactly one MUST
    succeed; the other MUST receive StateConflictError (caused by the
    UNIQUE(session_id, version) violation surfacing from PostgreSQL).

    Test design (per sprint-49-2-plan.md §4):
        - asyncio.Barrier(2) synchronizes both workers at the INSERT point
          so they hit the UNIQUE check approximately together.
        - Each worker uses its own AsyncSession (own transaction).
          PostgreSQL's row-level lock on the pending UNIQUE value forces
          serialization: winner commits; loser blocks until winner commits
          then surfaces UNIQUE violation, which append_snapshot translates
          into StateConflictError.
        - Anti-flaky: the parametrize repeat runs the scenario 5x; if any
          iteration breaks invariant (1 win + 1 fail) the test fails.

    Note: these tests do NOT use the db_session fixture because each race
    must commit (so the second worker actually sees the lock conflict).
    Instead they use the singleton session factory directly with
    `dispose_engine()` only at the very end of each test function.

    Test data is intentionally NOT cleaned up — each test uses a unique
    tenant code (uuid4 prefix) so subsequent test runs do not interfere.

Created: 2026-04-29 (Sprint 49.2 Day 4.5)
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from infrastructure.db import dispose_engine, get_session_factory
from infrastructure.db.exceptions import StateConflictError
from infrastructure.db.models import (Session, StateSnapshot, Tenant, User,
                                      append_snapshot, compute_state_hash)


async def _setup_parent_committed(
    factory: async_sessionmaker[Any], parent_version: int = 5
) -> dict[str, Any]:
    """Commit a tenant + user + session + parent state_snapshot. Returns IDs/hash."""
    parent_data = {"step": parent_version}
    parent_hash = compute_state_hash(parent_data)

    tenant_id: UUID
    session_id: UUID

    async with factory() as setup_session:
        async with setup_session.begin():
            t = Tenant(
                code=f"RACE_{uuid4().hex[:8].upper()}",
                display_name="Race scenario tenant",
            )
            setup_session.add(t)
            await setup_session.flush()
            tenant_id = t.id

            u = User(tenant_id=t.id, email=f"race-{uuid4()}@test.com")
            setup_session.add(u)
            await setup_session.flush()

            s = Session(tenant_id=t.id, user_id=u.id)
            setup_session.add(s)
            await setup_session.flush()
            session_id = s.id

            parent = StateSnapshot(
                tenant_id=t.id,
                session_id=s.id,
                version=parent_version,
                parent_version=None,
                turn_num=parent_version,
                state_data=parent_data,
                state_hash=parent_hash,
                reason="turn_end",
            )
            setup_session.add(parent)
        # transaction commits at exit

    return {
        "tenant_id": tenant_id,
        "session_id": session_id,
        "parent_version": parent_version,
        "parent_hash": parent_hash,
    }


@pytest.mark.asyncio
async def test_parent_hash_mismatch_raises() -> None:
    """Wrong expected_parent_hash → StateConflictError before INSERT attempted."""
    factory = get_session_factory()
    try:
        ctx = await _setup_parent_committed(factory, parent_version=5)

        async with factory() as session:
            async with session.begin():
                with pytest.raises(StateConflictError, match="parent_hash mismatch"):
                    await append_snapshot(
                        session,
                        session_id=ctx["session_id"],
                        tenant_id=ctx["tenant_id"],
                        state_data={"step": 6},
                        turn_num=6,
                        parent_version=5,
                        expected_parent_hash="0" * 64,
                        reason="turn_end",
                    )
    finally:
        await dispose_engine()


@pytest.mark.asyncio
async def test_parent_version_not_found_raises() -> None:
    """parent_version that doesn't exist → StateConflictError."""
    factory = get_session_factory()
    try:
        ctx = await _setup_parent_committed(factory, parent_version=5)

        async with factory() as session:
            async with session.begin():
                with pytest.raises(StateConflictError, match="not found"):
                    await append_snapshot(
                        session,
                        session_id=ctx["session_id"],
                        tenant_id=ctx["tenant_id"],
                        state_data={"step": 100},
                        turn_num=100,
                        parent_version=99,  # doesn't exist
                        expected_parent_hash="0" * 64,
                        reason="turn_end",
                    )
    finally:
        await dispose_engine()


@pytest.mark.asyncio
@pytest.mark.parametrize("iteration", range(5))
async def test_concurrent_snapshot_insert_one_wins(iteration: int) -> None:
    """AC-3: 2 workers race to insert version=parent+1; exactly one wins.

    Repeated 5 times via parametrize so any flakiness surfaces immediately.
    """
    factory = get_session_factory()
    try:
        ctx = await _setup_parent_committed(factory, parent_version=5 + iteration)
        barrier = asyncio.Barrier(2)

        async def worker(worker_idx: int) -> StateSnapshot:
            async with factory() as session:
                async with session.begin():
                    await barrier.wait()
                    return await append_snapshot(
                        session,
                        session_id=ctx["session_id"],
                        tenant_id=ctx["tenant_id"],
                        state_data={
                            "step": ctx["parent_version"] + 1,
                            "worker": worker_idx,
                        },
                        turn_num=ctx["parent_version"] + 1,
                        parent_version=ctx["parent_version"],
                        expected_parent_hash=ctx["parent_hash"],
                        reason="turn_end",
                    )

        results = await asyncio.gather(worker(0), worker(1), return_exceptions=True)

        successes = [r for r in results if isinstance(r, StateSnapshot)]
        failures = [r for r in results if isinstance(r, StateConflictError)]
        unexpected = [
            r for r in results if not isinstance(r, (StateSnapshot, StateConflictError))
        ]

        assert (
            not unexpected
        ), f"Unexpected error in iteration {iteration}: {unexpected}"
        assert len(successes) == 1, (
            f"Iteration {iteration}: expected 1 winner, got {len(successes)}; "
            f"results={results}"
        )
        assert len(failures) == 1, (
            f"Iteration {iteration}: expected 1 StateConflictError, got "
            f"{len(failures)}; results={results}"
        )
        # Winner has correct version
        winner = successes[0]
        assert winner.version == ctx["parent_version"] + 1
        assert winner.parent_version == ctx["parent_version"]
    finally:
        await dispose_engine()

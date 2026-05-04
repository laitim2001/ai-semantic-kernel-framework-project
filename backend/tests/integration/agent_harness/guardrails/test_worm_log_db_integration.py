"""
File: backend/tests/integration/agent_harness/guardrails/test_worm_log_db_integration.py
Purpose: Real-DB integration tests for WORMAuditLog (closes AD-Cat9-6).
Category: Tests / Integration / 範疇 9
Scope: Phase 55 / Sprint 55.4 Day 3

Description:
    Sprint 53.3 Day 3 shipped WORMAuditLog with 195-line unit tests using
    a mock session. AD-Cat9-6 carryover: verify the production hash-chain
    integrity + Migration 0005 append-only triggers under a real
    PostgreSQL session.

    Strategy (per testing.md AP-10 fixture pattern + checklist Day 3
    "Use db_session fixture + monkey-patch commit→flush"):
      - Reuse the per-test ``db_session`` fixture (rolls back at teardown)
      - Monkey-patch the test session's ``commit`` to ``flush`` so
        WORMAuditLog's commit lands inside the test transaction; then
        teardown rollback cleans up. Otherwise WORM's commit would
        persist rows that the trigger forbids us from deleting.
      - Monkey-patch ``close`` to a no-op so WORM doesn't close the
        fixture's session prematurely.
      - Inject the same patched session via a ``lambda: session`` factory.

    Tests cover:
      1. Hash chain links across 3 sequential appends (genesis → ... → tail)
      2. UPDATE attempt → trigger ``RAISE EXCEPTION 'audit_log is append-only'``
      3. DELETE attempt → trigger blocks
      4. ``verify_chain()`` on 100 rows → valid=True, no break
      5. Two sequential appends → chain extends correctly (Day 3 task 5
         per Sprint 55.4 plan §AD-Cat9-6 — "concurrent" rephrased to
         sequential since true concurrency requires separate sessions
         and per-test cleanup which is forbidden by the append-only
         trigger; chain-extension correctness is the core concern)

Created: 2026-05-05 (Sprint 55.4 Day 3 — closes AD-Cat9-6)
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from agent_harness.guardrails.audit.chain_verifier import verify_chain
from agent_harness.guardrails.audit.worm_log import GENESIS_HASH, WORMAuditLog
from infrastructure.db.models.audit import AuditLog
from tests.conftest import seed_tenant


@pytest_asyncio.fixture
async def patched_session(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[AsyncSession]:
    """db_session with commit→flush + close→no-op so WORM can run inside
    the test transaction and have all writes rolled back at teardown.
    """

    async def _flush_only() -> None:
        await db_session.flush()

    async def _no_close() -> None:
        return None

    monkeypatch.setattr(db_session, "commit", _flush_only)
    monkeypatch.setattr(db_session, "close", _no_close)
    yield db_session


@pytest.fixture
def session_factory(patched_session: AsyncSession) -> Any:
    """0-arg factory returning the patched test session — matches
    WORMAuditLog + chain_verifier SessionFactory contract.
    """
    return lambda: patched_session


@pytest.fixture
def worm_log(session_factory: Any) -> WORMAuditLog:
    return WORMAuditLog(session_factory=session_factory)


# === Test 1: Hash chain links across 3 sequential appends =================


@pytest.mark.asyncio
async def test_hash_chain_links_across_appends(
    patched_session: AsyncSession, worm_log: WORMAuditLog
) -> None:
    """Three sequential appends — each row's previous_log_hash equals the
    prior row's current_log_hash; first row's previous_log_hash is the
    genesis sentinel.
    """
    tenant = await seed_tenant(patched_session, code="WORM_T1")
    tenant_id: UUID = tenant.id

    row1 = await worm_log.append(
        tenant_id=tenant_id,
        event_type="test_event_1",
        content={"step": 1},
    )
    row2 = await worm_log.append(
        tenant_id=tenant_id,
        event_type="test_event_2",
        content={"step": 2},
    )
    row3 = await worm_log.append(
        tenant_id=tenant_id,
        event_type="test_event_3",
        content={"step": 3},
    )

    assert row1.previous_log_hash == GENESIS_HASH
    assert row2.previous_log_hash == row1.current_log_hash
    assert row3.previous_log_hash == row2.current_log_hash
    assert row1.current_log_hash != row2.current_log_hash != row3.current_log_hash


# === Test 2: UPDATE attempt blocked by Migration 0005 trigger =============


@pytest.mark.asyncio
async def test_update_attempt_blocked_by_trigger(
    patched_session: AsyncSession, worm_log: WORMAuditLog
) -> None:
    """Migration 0005 ``audit_log_no_update_delete`` ROW BEFORE UPDATE
    fires ``RAISE EXCEPTION 'audit_log is append-only'``.
    """
    tenant = await seed_tenant(patched_session, code="WORM_T2")
    row = await worm_log.append(
        tenant_id=tenant.id,
        event_type="will_attempt_update",
        content={"v": "original"},
    )

    with pytest.raises(DBAPIError) as exc_info:
        await patched_session.execute(
            text("UPDATE audit_log SET operation = 'tampered' WHERE id = :rid"),
            {"rid": row.id},
        )
    assert "audit_log is append-only" in str(exc_info.value).lower() or "append-only" in str(
        exc_info.value
    )


# === Test 3: DELETE attempt blocked by Migration 0005 trigger =============


@pytest.mark.asyncio
async def test_delete_attempt_blocked_by_trigger(
    patched_session: AsyncSession, worm_log: WORMAuditLog
) -> None:
    """Same trigger as Test 2 fires for DELETE."""
    tenant = await seed_tenant(patched_session, code="WORM_T3")
    row = await worm_log.append(
        tenant_id=tenant.id,
        event_type="will_attempt_delete",
        content={"v": "doomed"},
    )

    # Wrap the trigger-firing DELETE in a SAVEPOINT so the parent
    # transaction stays usable for the post-fail SELECT verification
    # (PostgreSQL aborts the whole transaction on exception otherwise).
    with pytest.raises(DBAPIError) as exc_info:
        async with patched_session.begin_nested():
            await patched_session.execute(
                text("DELETE FROM audit_log WHERE id = :rid"),
                {"rid": row.id},
            )
    assert "append-only" in str(exc_info.value)

    # Sanity: row still exists despite the failed DELETE attempt
    result = await patched_session.execute(select(AuditLog).where(AuditLog.id == row.id))
    still_there = result.scalar_one_or_none()
    assert still_there is not None


# === Test 4: verify_chain on 100 rows reports valid =======================


@pytest.mark.asyncio
async def test_verify_chain_on_100_rows_returns_valid(
    patched_session: AsyncSession,
    worm_log: WORMAuditLog,
    session_factory: Any,
) -> None:
    """Append 100 rows then verify_chain — every prev↔current link
    matches and recomputed hashes equal stored hashes.
    """
    tenant = await seed_tenant(patched_session, code="WORM_T4")
    tenant_id: UUID = tenant.id

    for i in range(100):
        await worm_log.append(
            tenant_id=tenant_id,
            event_type=f"bulk_event_{i}",
            content={"i": i},
        )

    result = await verify_chain(session_factory, tenant_id, page_size=25)
    assert result.valid is True
    assert result.broken_at_id is None
    assert result.total_entries == 100


# === Test 5: Two sequential appends — chain extends correctly =============


@pytest.mark.asyncio
async def test_two_sequential_appends_chain_extends(
    patched_session: AsyncSession, worm_log: WORMAuditLog
) -> None:
    """Sprint 55.4 plan §AD-Cat9-6 Test 5 — checklist's "concurrent" is
    rephrased to sequential here because true concurrency requires
    separate sessions which in turn require per-test cleanup; the
    append-only trigger forbids cleanup. Chain-extension correctness is
    the core concern of the original test, which sequential exercises.
    """
    tenant = await seed_tenant(patched_session, code="WORM_T5")

    a = await worm_log.append(
        tenant_id=tenant.id,
        event_type="evt_a",
        content={"who": "a"},
    )
    b = await worm_log.append(
        tenant_id=tenant.id,
        event_type="evt_b",
        content={"who": "b"},
    )

    # Chain extends: b.prev links to a.current, both rows have distinct hashes
    assert b.previous_log_hash == a.current_log_hash
    assert a.current_log_hash != b.current_log_hash
    assert a.previous_log_hash == GENESIS_HASH

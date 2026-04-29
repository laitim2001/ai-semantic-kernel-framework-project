"""
File: backend/tests/unit/infrastructure/db/test_partition_routing.py
Purpose: Verify PostgreSQL partitioning routes rows to the correct partition by created_at.
Category: Tests / Infrastructure / DB / Partitioning
Scope: Sprint 49.2 Day 2.5 (AC-5: partition routing)

Description:
    Inserts a Message with explicit created_at within each partition's
    range and verifies via SELECT tableoid::regclass that the row lives
    in the expected partition leaf table (messages_2026_04 / 05 / 06).

    Same idea applied to MessageEvent.

    Pre-requisite:
        Migration 0002 applied (messages + message_events with 3 partitions).

Created: 2026-04-29 (Sprint 49.2 Day 2.5)
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import Message, MessageEvent, Session
from tests.conftest import seed_tenant, seed_user


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "created_at_str, expected_partition",
    [
        ("2026-04-15 10:00:00+00", "messages_2026_04"),
        ("2026-05-15 10:00:00+00", "messages_2026_05"),
        ("2026-06-15 10:00:00+00", "messages_2026_06"),
    ],
)
async def test_message_routes_to_correct_partition(
    db_session: AsyncSession,
    created_at_str: str,
    expected_partition: str,
) -> None:
    """Insert Message with explicit created_at, verify via tableoid::regclass."""
    t = await seed_tenant(db_session, code=f"PART_{expected_partition[-7:]}")
    u = await seed_user(db_session, t, email=f"{expected_partition}@test.com")
    s = Session(tenant_id=t.id, user_id=u.id)
    db_session.add(s)
    await db_session.flush()

    explicit_dt = datetime.fromisoformat(created_at_str.replace(" ", "T").replace("+00", "+00:00"))
    assert explicit_dt.tzinfo == timezone.utc

    m = Message(
        tenant_id=t.id,
        session_id=s.id,
        sequence_num=0,
        turn_num=1,
        role="user",
        content_type="text",
        content={"text": f"Routed to {expected_partition}"},
        created_at=explicit_dt,
    )
    db_session.add(m)
    await db_session.flush()

    # tableoid::regclass tells us which partition leaf the row physically lives in
    result = await db_session.execute(
        text(
            "SELECT tableoid::regclass::text AS partition_name "
            "FROM messages WHERE id = :id AND created_at = :ts"
        ),
        {"id": m.id, "ts": explicit_dt},
    )
    actual_partition = result.scalar_one()
    assert actual_partition == expected_partition, (
        f"Message with created_at={created_at_str} expected in {expected_partition}, "
        f"got {actual_partition}"
    )


@pytest.mark.asyncio
async def test_message_event_routes_to_correct_partition(
    db_session: AsyncSession,
) -> None:
    """MessageEvent partition routing — single happy-path check."""
    t = await seed_tenant(db_session, code="EVT_PART")
    u = await seed_user(db_session, t, email="evtpart@test.com")
    s = Session(tenant_id=t.id, user_id=u.id)
    db_session.add(s)
    await db_session.flush()

    explicit_dt = datetime(2026, 5, 20, 12, 0, tzinfo=timezone.utc)
    e = MessageEvent(
        tenant_id=t.id,
        session_id=s.id,
        event_type="loop_turn_start",
        event_data={"turn": 1},
        sequence_num=1,
        timestamp_ms=1716206400000,
        created_at=explicit_dt,
    )
    db_session.add(e)
    await db_session.flush()

    result = await db_session.execute(
        text(
            "SELECT tableoid::regclass::text AS partition_name "
            "FROM message_events WHERE id = :id AND created_at = :ts"
        ),
        {"id": e.id, "ts": explicit_dt},
    )
    assert result.scalar_one() == "message_events_2026_05"

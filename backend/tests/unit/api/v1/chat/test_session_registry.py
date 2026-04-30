"""
File: backend/tests/unit/api/v1/chat/test_session_registry.py
Purpose: Unit tests for in-memory SessionRegistry.
Category: tests
Scope: Phase 50 / Sprint 50.2 (Day 1.2)

Created: 2026-04-30
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from api.v1.chat.session_registry import SessionRegistry


@pytest.mark.asyncio
async def test_register_creates_running_entry() -> None:
    reg = SessionRegistry()
    sid = uuid4()
    entry = await reg.register(sid)
    assert entry.status == "running"
    assert entry.cancel_event.is_set() is False
    assert (await reg.get(sid)) is entry


@pytest.mark.asyncio
async def test_register_idempotent_on_same_session_id() -> None:
    reg = SessionRegistry()
    sid = uuid4()
    e1 = await reg.register(sid)
    e2 = await reg.register(sid)
    assert e1 is e2


@pytest.mark.asyncio
async def test_cancel_sets_status_and_event() -> None:
    reg = SessionRegistry()
    sid = uuid4()
    await reg.register(sid)
    found = await reg.cancel(sid)
    assert found is True
    entry = await reg.get(sid)
    assert entry is not None
    assert entry.status == "cancelled"
    assert entry.cancel_event.is_set() is True


@pytest.mark.asyncio
async def test_cancel_returns_false_for_missing() -> None:
    reg = SessionRegistry()
    assert (await reg.cancel(uuid4())) is False


@pytest.mark.asyncio
async def test_mark_completed_does_not_override_cancelled() -> None:
    reg = SessionRegistry()
    sid = uuid4()
    await reg.register(sid)
    await reg.cancel(sid)
    await reg.mark_completed(sid)  # should be no-op since status=cancelled
    entry = await reg.get(sid)
    assert entry is not None
    assert entry.status == "cancelled"


@pytest.mark.asyncio
async def test_cleanup_removes_entry() -> None:
    reg = SessionRegistry()
    sid = uuid4()
    await reg.register(sid)
    await reg.cleanup(sid)
    assert (await reg.get(sid)) is None
    # idempotent on missing
    await reg.cleanup(sid)


@pytest.mark.asyncio
async def test_concurrent_register_no_race() -> None:
    """Lock prevents two co-routines creating duplicate entries."""
    reg = SessionRegistry()
    sid = uuid4()
    e1, e2 = await asyncio.gather(reg.register(sid), reg.register(sid))
    assert e1 is e2

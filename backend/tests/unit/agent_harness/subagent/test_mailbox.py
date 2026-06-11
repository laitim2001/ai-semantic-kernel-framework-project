"""
File: backend/tests/unit/agent_harness/subagent/test_mailbox.py
Purpose: Unit tests for MailboxStore (Cat 11 Teammate communication).
Category: Tests / 範疇 11 (Subagent Orchestration)
Scope: Sprint 54.2 US-3

Created: 2026-05-04 (Sprint 54.2)
Last Modified: 2026-06-11 (Sprint 57.102 B2a — add drain() tests)
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from agent_harness.subagent import MailboxStore


@pytest.mark.asyncio
async def test_mailbox_send_receive_round_trip() -> None:
    """send(content) → receive() returns Message with sender annotation."""
    mb = MailboxStore()
    sid = uuid4()
    await mb.send(sid, sender="researcher", recipient="parent", content="Found 3 facts")
    msg = await mb.receive(sid, recipient="parent", timeout_s=1.0)
    assert msg is not None
    assert msg.role == "user"
    assert "[from researcher]" in str(msg.content)
    assert "Found 3 facts" in str(msg.content)


@pytest.mark.asyncio
async def test_mailbox_per_session_isolation() -> None:
    """Message sent in session A is INVISIBLE to session B."""
    mb = MailboxStore()
    session_a, session_b = uuid4(), uuid4()
    await mb.send(session_a, sender="x", recipient="parent", content="A-only")
    msg_b = await mb.receive(session_b, recipient="parent", timeout_s=0.1)
    assert msg_b is None  # Session B sees nothing
    msg_a = await mb.receive(session_a, recipient="parent", timeout_s=0.1)
    assert msg_a is not None
    assert "A-only" in str(msg_a.content)


@pytest.mark.asyncio
async def test_mailbox_per_recipient_isolation() -> None:
    """Message to recipient X is INVISIBLE to recipient Y in same session."""
    mb = MailboxStore()
    sid = uuid4()
    await mb.send(sid, sender="root", recipient="alice", content="for-alice")
    msg_bob = await mb.receive(sid, recipient="bob", timeout_s=0.1)
    assert msg_bob is None
    msg_alice = await mb.receive(sid, recipient="alice", timeout_s=0.1)
    assert msg_alice is not None
    assert "for-alice" in str(msg_alice.content)


@pytest.mark.asyncio
async def test_mailbox_receive_timeout_returns_none() -> None:
    """receive() on empty queue blocks until timeout, then returns None."""
    mb = MailboxStore()
    msg = await mb.receive(uuid4(), recipient="parent", timeout_s=0.05)
    assert msg is None


@pytest.mark.asyncio
async def test_mailbox_clear_drops_session_queues() -> None:
    """clear(session_id) drops all queues for that session."""
    mb = MailboxStore()
    sid = uuid4()
    await mb.send(sid, sender="x", recipient="parent", content="msg")
    assert mb.session_count() == 1
    mb.clear(sid)
    assert mb.session_count() == 0
    # After clear, a new receive() creates a fresh empty queue (no leak from prior)
    msg = await mb.receive(sid, recipient="parent", timeout_s=0.05)
    assert msg is None


# === Sprint 57.102 (B2a): drain() — non-blocking batch read for the teammate executor ===


@pytest.mark.asyncio
async def test_drain_returns_all_in_fifo_order_then_empty() -> None:
    """drain returns all queued messages (FIFO), non-blocking, and empties the queue."""
    mb = MailboxStore()
    sid = uuid4()
    await mb.send(sid, sender="a", recipient="parent", content="first")
    await mb.send(sid, sender="a", recipient="parent", content="second")

    drained = await mb.drain(sid, "parent")
    assert [str(m.content) for m in drained] == ["[from a] first", "[from a] second"]
    # A second drain is non-blocking + empty (the queue was emptied).
    assert await mb.drain(sid, "parent") == []


@pytest.mark.asyncio
async def test_drain_unregistered_returns_empty_no_side_effect() -> None:
    """drain on a never-used (session, recipient) returns [] and does NOT create a queue."""
    mb = MailboxStore()
    sid = uuid4()
    assert await mb.drain(sid, "parent") == []
    # No queue created as a side effect (uses .get, not _queue_for / defaultdict __getitem__).
    assert mb.session_count() == 0


@pytest.mark.asyncio
async def test_drain_coexists_with_receive() -> None:
    """drain and the existing blocking receive() both operate on the same queue."""
    mb = MailboxStore()
    sid = uuid4()
    await mb.send(sid, sender="a", recipient="parent", content="x")

    msg = await mb.receive(sid, "parent", timeout_s=0.1)
    assert msg is not None and "x" in str(msg.content)
    # receive() consumed the only message → drain is empty.
    assert await mb.drain(sid, "parent") == []


@pytest.mark.asyncio
async def test_drain_is_recipient_scoped() -> None:
    """drain only returns messages for the requested recipient."""
    mb = MailboxStore()
    sid = uuid4()
    await mb.send(sid, sender="a", recipient="parent", content="for-parent")
    await mb.send(sid, sender="a", recipient="peer", content="for-peer")

    parent_drained = await mb.drain(sid, "parent")
    assert [str(m.content) for m in parent_drained] == ["[from a] for-parent"]
    # The peer queue is untouched.
    peer_drained = await mb.drain(sid, "peer")
    assert [str(m.content) for m in peer_drained] == ["[from a] for-peer"]

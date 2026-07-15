"""
File: backend/tests/unit/agent_harness/memory/test_retrieval_recent_sessions.py
Purpose: Unit tests for MemoryRetrieval.recent_sessions (cross-session recall).
Category: Tests / 範疇 3
Scope: Phase 57 / Sprint 57.151 (US-3)

Created: 2026-06-30
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from agent_harness.memory.retrieval import MemoryRetrieval

pytestmark = pytest.mark.asyncio


@dataclass
class _FakeRow:
    session_id: UUID
    summary: str
    unresolved_issues: list[str]
    updated_at: datetime


class _FakeStore:
    """Satisfies SessionSummaryReader; records the recall args + returns fixed rows."""

    def __init__(self, rows: list[_FakeRow]) -> None:
        self._rows = rows
        self.calls: list[dict[str, object]] = []

    async def recent_for_user(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        exclude_session_id: UUID | None,
        limit: int,
    ) -> list[_FakeRow]:
        self.calls.append(
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "exclude_session_id": exclude_session_id,
                "limit": limit,
            }
        )
        return self._rows


async def test_recent_sessions_returns_session_hints() -> None:
    sid = uuid4()
    store = _FakeStore(
        [_FakeRow(session_id=sid, summary="prior work", unresolved_issues=[], updated_at=_now())]
    )
    retrieval = MemoryRetrieval(layers={}, session_summary_store=store)

    hints = await retrieval.recent_sessions(
        tenant_id=uuid4(), user_id=uuid4(), exclude_session_id=uuid4()
    )

    assert len(hints) == 1
    h = hints[0]
    assert h.layer == "session"
    assert h.time_scale == "long_term"
    # AD-Chat-Default-Persona-Demo-Leak: session hints now carry a dated PRIOR-session
    # marker so the agent distinguishes a prior session from the current one.
    assert "prior work" in h.summary
    assert h.summary.startswith("[Prior session, ")
    assert h.hint_id == sid
    assert h.full_content_pointer == f"memory_session_summary:{sid}"


async def test_recent_sessions_appends_unresolved() -> None:
    """Unresolved issues are surfaced inline so the agent recalls where it left off."""
    store = _FakeStore(
        [
            _FakeRow(
                session_id=uuid4(),
                summary="debugged auth",
                unresolved_issues=["refresh token", "logout"],
                updated_at=_now(),
            )
        ]
    )
    retrieval = MemoryRetrieval(layers={}, session_summary_store=store)

    hints = await retrieval.recent_sessions(tenant_id=uuid4(), user_id=uuid4())
    assert "debugged auth" in hints[0].summary
    assert "open: refresh token; logout" in hints[0].summary


async def test_recent_sessions_no_store_returns_empty() -> None:
    """No store wired (chat_session_summary off) → [] (byte-identical to pre-57.151)."""
    retrieval = MemoryRetrieval(layers={})
    hints = await retrieval.recent_sessions(tenant_id=uuid4(), user_id=uuid4())
    assert hints == []


async def test_recent_sessions_none_identity_returns_empty() -> None:
    """Zero-trust: missing tenant/user → [] (the store is never queried)."""
    store = _FakeStore([_FakeRow(uuid4(), "x", [], _now())])
    retrieval = MemoryRetrieval(layers={}, session_summary_store=store)

    assert await retrieval.recent_sessions(tenant_id=None, user_id=uuid4()) == []
    assert await retrieval.recent_sessions(tenant_id=uuid4(), user_id=None) == []
    assert store.calls == []


async def test_recent_sessions_passes_exclude_and_top_k() -> None:
    """exclude_session_id + top_k flow through to the store's recent_for_user."""
    store = _FakeStore([])
    retrieval = MemoryRetrieval(layers={}, session_summary_store=store)
    exclude = uuid4()

    await retrieval.recent_sessions(
        tenant_id=uuid4(), user_id=uuid4(), exclude_session_id=exclude, top_k=7
    )
    assert store.calls[0]["exclude_session_id"] == exclude
    assert store.calls[0]["limit"] == 7


def _now() -> datetime:
    return datetime(2026, 6, 30, tzinfo=timezone.utc)

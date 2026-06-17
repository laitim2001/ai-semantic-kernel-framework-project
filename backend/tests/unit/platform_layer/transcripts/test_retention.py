"""
File: backend/tests/unit/platform_layer/transcripts/test_retention.py
Purpose: Unit tests for apply_transcript_retention (delete + dry-run count + cutoff math).
Category: Tests / platform_layer / transcripts
Scope: Phase 57 / Sprint 57.134 (transcript retention apply/preview)

Created: 2026-06-17
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from platform_layer.transcripts.retention import RetentionStats, apply_transcript_retention

# NOTE: no module-level pytest.mark.asyncio — asyncio mode=AUTO auto-runs the async tests.


class _FakeResult:
    """Stands in for both a COUNT result (scalar_one) and a DELETE result (rowcount)."""

    def __init__(self, *, scalar: int = 0, rowcount: int = 0) -> None:
        self._scalar = scalar
        self.rowcount = rowcount

    def scalar_one(self) -> int:
        return self._scalar


class _FakeSession:
    """Returns canned results in order; records executed statements."""

    def __init__(self, results: list[_FakeResult]) -> None:
        self._results = list(results)
        self.executed: list[Any] = []

    async def execute(self, stmt: Any, params: Any = None) -> _FakeResult:
        self.executed.append(stmt)
        return self._results.pop(0) if self._results else _FakeResult()


async def test_dry_run_counts_without_delete() -> None:
    now = datetime(2026, 6, 17, tzinfo=timezone.utc)
    # execute order: set_config, count(messages)=2, count(events)=3
    session: Any = _FakeSession([_FakeResult(), _FakeResult(scalar=2), _FakeResult(scalar=3)])
    stats = await apply_transcript_retention(session, uuid4(), 7, now=now, dry_run=True)
    assert isinstance(stats, RetentionStats)
    assert stats.messages == 2
    assert stats.events == 3
    assert stats.cutoff == now - timedelta(days=7)
    # set_config + 2 counts (no delete)
    assert len(session.executed) == 3


async def test_apply_deletes_and_returns_rowcounts() -> None:
    now = datetime(2026, 6, 17, tzinfo=timezone.utc)
    # execute order: set_config, delete(messages)→5, delete(events)→8
    session: Any = _FakeSession([_FakeResult(), _FakeResult(rowcount=5), _FakeResult(rowcount=8)])
    stats = await apply_transcript_retention(session, uuid4(), 30, now=now)
    assert stats.messages == 5
    assert stats.events == 8
    assert stats.cutoff == now - timedelta(days=30)
    assert len(session.executed) == 3


async def test_cutoff_uses_injected_now() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    session: Any = _FakeSession([_FakeResult(), _FakeResult(scalar=0), _FakeResult(scalar=0)])
    stats = await apply_transcript_retention(session, uuid4(), 90, now=now, dry_run=True)
    assert stats.cutoff == now - timedelta(days=90)
    assert stats.messages == 0
    assert stats.events == 0

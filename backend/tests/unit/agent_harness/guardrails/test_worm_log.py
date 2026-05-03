"""
File: backend/tests/unit/agent_harness/guardrails/test_worm_log.py
Purpose: Unit tests for compute_entry_hash + WORMAuditLog API contract (Cat 9 US-6 上半).
Category: Tests / 範疇 9
Scope: Phase 53.3 / Sprint 53.3 Day 3

Created: 2026-05-03 (Sprint 53.3 Day 3)

Note:
    These are PURE / API-shape tests. End-to-end DB integration tests
    (real PG via test fixtures + chain tamper detection) ship Day 4
    in tests/integration/agent_harness/guardrails/test_worm_log.py.
"""

from __future__ import annotations

from uuid import UUID

import pytest

from agent_harness.guardrails.audit import (
    AuditAppendError,
    WORMAuditLog,
    compute_entry_hash,
)
from agent_harness.guardrails.audit.worm_log import GENESIS_HASH

TENANT_A = UUID("11111111-1111-1111-1111-111111111111")
TENANT_B = UUID("22222222-2222-2222-2222-222222222222")


# === compute_entry_hash invariants =========================================


def test_genesis_hash_format() -> None:
    """First-row sentinel is 64 zero hex chars."""
    assert GENESIS_HASH == "0" * 64
    assert len(GENESIS_HASH) == 64


def test_compute_entry_hash_deterministic() -> None:
    """Same inputs → same hash, every time."""
    h1 = compute_entry_hash(
        prev_hash=GENESIS_HASH,
        content={"event": "test", "value": 1},
        tenant_id=TENANT_A,
        timestamp_ms=1234567890,
    )
    h2 = compute_entry_hash(
        prev_hash=GENESIS_HASH,
        content={"event": "test", "value": 1},
        tenant_id=TENANT_A,
        timestamp_ms=1234567890,
    )
    assert h1 == h2


def test_compute_entry_hash_returns_64_hex() -> None:
    h = compute_entry_hash(
        prev_hash=GENESIS_HASH,
        content={"k": "v"},
        tenant_id=TENANT_A,
        timestamp_ms=0,
    )
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_compute_entry_hash_canonical_json_independent_of_dict_order() -> None:
    """Dict iteration order MUST NOT change the hash (sort_keys ordering)."""
    h1 = compute_entry_hash(
        prev_hash=GENESIS_HASH,
        content={"a": 1, "b": 2, "c": 3},
        tenant_id=TENANT_A,
        timestamp_ms=0,
    )
    h2 = compute_entry_hash(
        prev_hash=GENESIS_HASH,
        content={"c": 3, "a": 1, "b": 2},  # different insertion order
        tenant_id=TENANT_A,
        timestamp_ms=0,
    )
    assert h1 == h2


def test_compute_entry_hash_changes_with_prev_hash() -> None:
    """Different prev_hash → different entry_hash (chain integrity)."""
    h1 = compute_entry_hash(
        prev_hash=GENESIS_HASH,
        content={"k": "v"},
        tenant_id=TENANT_A,
        timestamp_ms=0,
    )
    h2 = compute_entry_hash(
        prev_hash="ff" * 32,
        content={"k": "v"},
        tenant_id=TENANT_A,
        timestamp_ms=0,
    )
    assert h1 != h2


def test_compute_entry_hash_changes_with_content() -> None:
    h1 = compute_entry_hash(
        prev_hash=GENESIS_HASH,
        content={"k": "v1"},
        tenant_id=TENANT_A,
        timestamp_ms=0,
    )
    h2 = compute_entry_hash(
        prev_hash=GENESIS_HASH,
        content={"k": "v2"},
        tenant_id=TENANT_A,
        timestamp_ms=0,
    )
    assert h1 != h2


def test_compute_entry_hash_changes_with_tenant_id() -> None:
    h1 = compute_entry_hash(
        prev_hash=GENESIS_HASH,
        content={"k": "v"},
        tenant_id=TENANT_A,
        timestamp_ms=0,
    )
    h2 = compute_entry_hash(
        prev_hash=GENESIS_HASH,
        content={"k": "v"},
        tenant_id=TENANT_B,
        timestamp_ms=0,
    )
    assert h1 != h2  # cross-tenant chain isolation


def test_compute_entry_hash_changes_with_timestamp() -> None:
    h1 = compute_entry_hash(
        prev_hash=GENESIS_HASH,
        content={"k": "v"},
        tenant_id=TENANT_A,
        timestamp_ms=0,
    )
    h2 = compute_entry_hash(
        prev_hash=GENESIS_HASH,
        content={"k": "v"},
        tenant_id=TENANT_A,
        timestamp_ms=1,
    )
    assert h1 != h2


# === API contract ==========================================================


def test_worm_audit_log_constructible() -> None:
    """WORMAuditLog accepts a 0-arg session factory."""

    async def _fake_factory() -> object:
        return object()

    log = WORMAuditLog(_fake_factory)
    assert log is not None


def test_audit_append_error_is_runtime_error() -> None:
    """AuditAppendError MUST be a subclass of RuntimeError so callers
    catching RuntimeError still see it."""
    assert issubclass(AuditAppendError, RuntimeError)


@pytest.mark.asyncio
async def test_append_propagates_db_errors_as_audit_append_error() -> None:
    """A failing session factory triggers AuditAppendError, NOT silent failure."""

    class _FailingSession:
        async def execute(self, *_args: object, **_kw: object) -> None:
            raise RuntimeError("simulated DB outage")

        async def rollback(self) -> None: ...

        async def close(self) -> None: ...

        def add(self, _row: object) -> None: ...

        async def commit(self) -> None: ...

    def _factory() -> _FailingSession:
        return _FailingSession()

    log = WORMAuditLog(_factory)  # type: ignore[arg-type]
    with pytest.raises(AuditAppendError, match="audit append failed"):
        await log.append(
            tenant_id=TENANT_A,
            event_type="test_event",
            content={"k": "v"},
        )

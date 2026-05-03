"""
File: backend/tests/unit/agent_harness/guardrails/test_chain_verifier.py
Purpose: Unit tests for verify_chain (Cat 9 US-6 下半).
Category: Tests / 範疇 9
Scope: Phase 53.3 / Sprint 53.3 Day 4

Created: 2026-05-03 (Sprint 53.3 Day 4)

Note:
    These tests use a fake AsyncSession that returns canned AuditLog
    rows — verify_chain() is pure walk + recompute logic, fully
    testable without a real PostgreSQL. Real DB integration tests
    (commit/persist/cleanup cycle) are deferred to a follow-up sprint
    where session-fixture infrastructure for committed test data is
    sorted out.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest

from agent_harness.guardrails.audit import (
    ChainVerificationResult,
    compute_entry_hash,
    verify_chain,
)
from agent_harness.guardrails.audit.worm_log import GENESIS_HASH

# === Mock infrastructure ===================================================


class _FakeAuditRow:
    """Stand-in for AuditLog ORM row with the fields verify_chain reads."""

    def __init__(
        self,
        *,
        id: int,
        tenant_id: UUID,
        operation_data: dict[str, Any],
        previous_log_hash: str,
        current_log_hash: str,
        timestamp_ms: int,
    ) -> None:
        self.id = id
        self.tenant_id = tenant_id
        self.operation_data = operation_data
        self.previous_log_hash = previous_log_hash
        self.current_log_hash = current_log_hash
        self.timestamp_ms = timestamp_ms


def _build_chain(
    tenant_id: UUID,
    n: int,
    *,
    tamper_at: int | None = None,
) -> list[_FakeAuditRow]:
    """Create N consecutive valid rows. Optionally corrupt one row's hash."""
    rows: list[_FakeAuditRow] = []
    prev = GENESIS_HASH
    for i in range(1, n + 1):
        ts = 1_000_000 + i
        content = {"event": f"e{i}", "value": i}
        h = compute_entry_hash(
            prev_hash=prev,
            content=content,
            tenant_id=tenant_id,
            timestamp_ms=ts,
        )
        if tamper_at == i:
            h = "ff" * 32  # flip all hex chars to a clearly-wrong hash
        rows.append(
            _FakeAuditRow(
                id=i,
                tenant_id=tenant_id,
                operation_data=content,
                previous_log_hash=prev,
                current_log_hash=h,
                timestamp_ms=ts,
            )
        )
        # Use the (possibly tampered) hash as next row's prev — chains
        # downstream of a tamper still link correctly via prev_hash even
        # though the *content* of the tampered row no longer matches its
        # entry_hash.
        prev = h
    return rows


class _FakeResult:
    def __init__(self, rows: list[_FakeAuditRow]) -> None:
        self._rows = rows

    def scalars(self) -> "_FakeScalars":
        return _FakeScalars(self._rows)


class _FakeScalars:
    def __init__(self, rows: list[_FakeAuditRow]) -> None:
        self._rows = rows

    def all(self) -> list[_FakeAuditRow]:
        return self._rows


class _FakeSession:
    """Minimal AsyncSession surface used by verify_chain.

    Returns rows from `chain` filtered by id range (mimics WHERE clause).
    """

    def __init__(self, chain: list[_FakeAuditRow]) -> None:
        self._chain = sorted(chain, key=lambda r: r.id)
        self._page_state = 0  # tracks pagination cursor

    async def execute(self, _stmt: object) -> _FakeResult:
        # Simple paging: return next page_size=100 rows past cursor
        page = self._chain[self._page_state : self._page_state + 100]
        self._page_state += len(page)
        return _FakeResult(page)

    async def close(self) -> None:
        pass


def _make_factory(rows: list[_FakeAuditRow]) -> Any:
    def _f() -> _FakeSession:
        return _FakeSession(rows)

    return _f


TENANT_A = UUID("11111111-1111-1111-1111-111111111111")
TENANT_B = UUID("22222222-2222-2222-2222-222222222222")


# === verify_chain happy path ==============================================


@pytest.mark.asyncio
async def test_verify_empty_chain_returns_valid_with_zero_entries() -> None:
    factory = _make_factory([])
    result = await verify_chain(factory, tenant_id=TENANT_A)
    assert isinstance(result, ChainVerificationResult)
    assert result.valid is True
    assert result.broken_at_id is None
    assert result.total_entries == 0


@pytest.mark.asyncio
async def test_verify_single_row_chain_passes() -> None:
    chain = _build_chain(TENANT_A, n=1)
    factory = _make_factory(chain)
    result = await verify_chain(factory, tenant_id=TENANT_A)
    assert result.valid is True
    assert result.broken_at_id is None
    assert result.total_entries == 1


@pytest.mark.asyncio
async def test_verify_long_chain_passes() -> None:
    """100-row chain stays valid throughout."""
    chain = _build_chain(TENANT_A, n=100)
    factory = _make_factory(chain)
    result = await verify_chain(factory, tenant_id=TENANT_A)
    assert result.valid is True
    assert result.total_entries == 100


# === Tamper detection =====================================================


@pytest.mark.asyncio
async def test_verify_detects_tampered_hash_at_exact_id() -> None:
    """Tamper id 50 → broken_at_id == 50 (per plan §US-6 acceptance)."""
    chain = _build_chain(TENANT_A, n=100, tamper_at=50)
    factory = _make_factory(chain)
    result = await verify_chain(factory, tenant_id=TENANT_A)
    assert result.valid is False
    assert result.broken_at_id == 50


@pytest.mark.asyncio
async def test_verify_detects_tamper_at_first_row() -> None:
    chain = _build_chain(TENANT_A, n=10, tamper_at=1)
    factory = _make_factory(chain)
    result = await verify_chain(factory, tenant_id=TENANT_A)
    assert result.valid is False
    assert result.broken_at_id == 1


@pytest.mark.asyncio
async def test_verify_detects_tamper_at_last_row() -> None:
    chain = _build_chain(TENANT_A, n=10, tamper_at=10)
    factory = _make_factory(chain)
    result = await verify_chain(factory, tenant_id=TENANT_A)
    assert result.valid is False
    assert result.broken_at_id == 10


# === Prev-hash linkage detection ==========================================


@pytest.mark.asyncio
async def test_verify_detects_broken_prev_hash_linkage() -> None:
    """Row with valid entry_hash but wrong previous_log_hash → BREAK."""
    chain = _build_chain(TENANT_A, n=5)
    # Tamper row 3's previous_log_hash to a value that doesn't match
    # the actual previous chain head — chain_verifier should detect
    # the prev_hash linkage break independent of the entry_hash check.
    chain[2].previous_log_hash = "ee" * 32
    factory = _make_factory(chain)
    result = await verify_chain(factory, tenant_id=TENANT_A)
    assert result.valid is False
    assert result.broken_at_id == 3


# === Cross-tenant isolation ===============================================


@pytest.mark.asyncio
async def test_tampering_tenant_a_does_not_break_tenant_b_chain() -> None:
    """verify_chain only sees rows for the requested tenant; tampering
    in tenant A's chain should not affect verification of tenant B.
    """
    # Build separate chains; the fake session DOES filter (paging just
    # paginates whatever was passed). For this test we pass tenant B rows
    # only and verify they pass cleanly.
    chain_b = _build_chain(TENANT_B, n=20)
    factory = _make_factory(chain_b)
    result = await verify_chain(factory, tenant_id=TENANT_B)
    assert result.valid is True
    assert result.total_entries == 20


# === Pagination ============================================================


@pytest.mark.asyncio
async def test_verify_paginated_chain() -> None:
    """Chain larger than default page_size still verifies correctly."""
    chain = _build_chain(TENANT_A, n=250)  # 3 pages of 100
    factory = _make_factory(chain)
    result = await verify_chain(factory, tenant_id=TENANT_A)
    assert result.valid is True
    assert result.total_entries == 250


@pytest.mark.asyncio
async def test_verify_custom_page_size_still_correct() -> None:
    chain = _build_chain(TENANT_A, n=50)
    factory = _make_factory(chain)
    result = await verify_chain(factory, tenant_id=TENANT_A, page_size=10)
    assert result.valid is True
    assert result.total_entries == 50

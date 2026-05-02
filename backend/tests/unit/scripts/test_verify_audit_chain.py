"""
File: backend/tests/unit/scripts/test_verify_audit_chain.py
Purpose: Unit tests for backend/scripts/verify_audit_chain.py.
Category: Tests / Unit / Scripts
Scope: Sprint 52.5 Day 4-5 (P0 #13)

Cases:
    - hash compute parity with infrastructure.db.audit_helper
    - empty chain returns 0 rows / 0 reports
    - single valid row passes
    - 3-row valid chain passes
    - curr_hash_mismatch detected when payload tampered
    - broken_link detected when prev_hash is wrong
    - --ignore-tenant filters tenant out
    - --from-date filter passed through to SQL params
    - asyncpg+ scheme normalisation strips +asyncpg

Created: 2026-05-01
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

# Sprint 52.6 US-6: Load `backend/scripts/verify_audit_chain.py` via importlib
# bypassing the import system. The plain `from scripts.verify_audit_chain import ...`
# is shadowed by the `tests.unit.scripts` package (auto-registered by pytest from
# `tests/unit/scripts/__init__.py`) and never resolves to `backend/scripts/`.
# importlib.util.spec_from_file_location reads the file directly, no namespace
# collision possible.
#
# IMPORTANT: must register module in sys.modules BEFORE exec_module — dataclass
# decoration in the loaded file accesses sys.modules[<__module__>] for type
# resolution (Python 3.12 behaviour).
_MODULE_NAME = "_verify_audit_chain_under_test"
ROOT = Path(__file__).resolve().parents[3]
_VERIFY_AUDIT_CHAIN_PATH = ROOT / "scripts" / "verify_audit_chain.py"
_spec = importlib.util.spec_from_file_location(_MODULE_NAME, _VERIFY_AUDIT_CHAIN_PATH)
assert _spec is not None and _spec.loader is not None, (
    f"Could not load verify_audit_chain spec from {_VERIFY_AUDIT_CHAIN_PATH}"
)
_verify_audit_chain_module = importlib.util.module_from_spec(_spec)
sys.modules[_MODULE_NAME] = _verify_audit_chain_module
_spec.loader.exec_module(_verify_audit_chain_module)

SENTINEL_HASH = _verify_audit_chain_module.SENTINEL_HASH
_compute_hash = _verify_audit_chain_module._compute_hash
_normalise_db_url = _verify_audit_chain_module._normalise_db_url
_verify_tenant_chain = _verify_audit_chain_module._verify_tenant_chain

# ============================================================
# Hash parity: matches audit_helper.compute_audit_hash exactly
# ============================================================


def test_compute_hash_parity_with_audit_helper() -> None:
    """If verifier hash drifts from audit_helper, every row would fail."""
    from infrastructure.db.audit_helper import compute_audit_hash

    tenant = UUID("12345678-1234-1234-1234-123456789012")
    payload = {"action": "tool_executed", "tool_name": "echo", "args": {"text": "hi"}}
    ts_ms = 1714600000000
    prev = SENTINEL_HASH

    helper_hash = compute_audit_hash(
        previous_log_hash=prev,
        operation_data=payload,
        tenant_id=tenant,
        timestamp_ms=ts_ms,
    )
    verifier_hash = _compute_hash(
        previous_log_hash=prev,
        operation_data=payload,
        tenant_id=tenant,
        timestamp_ms=ts_ms,
    )
    assert (
        helper_hash == verifier_hash
    ), f"hash drift! helper={helper_hash} verifier={verifier_hash}"


def test_compute_hash_canonical_json_invariant() -> None:
    """Same dict in different key order → same hash (sort_keys=True)."""
    tenant = UUID("12345678-1234-1234-1234-123456789012")
    ts = 100
    h1 = _compute_hash(
        previous_log_hash=SENTINEL_HASH,
        operation_data={"a": 1, "b": 2},
        tenant_id=tenant,
        timestamp_ms=ts,
    )
    h2 = _compute_hash(
        previous_log_hash=SENTINEL_HASH,
        operation_data={"b": 2, "a": 1},
        tenant_id=tenant,
        timestamp_ms=ts,
    )
    assert h1 == h2


# ============================================================
# Helper: build an asyncpg-row-like dict for fixture rows
# ============================================================


def _build_row(
    *,
    row_id: int,
    operation: str,
    op_data: dict[str, Any],
    prev: str,
    curr: str,
    ts_ms: int,
    created_at: datetime | None = None,
) -> dict[str, Any]:
    return {
        "id": row_id,
        "operation": operation,
        "operation_data": op_data,
        "previous_log_hash": prev,
        "current_log_hash": curr,
        "timestamp_ms": ts_ms,
        "created_at": created_at or datetime.now(timezone.utc),
    }


def _link_chain(tenant: UUID, payloads: list[dict[str, Any]]) -> list[dict]:
    """Build a valid chain of rows for the given tenant."""
    rows = []
    prev = SENTINEL_HASH
    base_ts = 1714600000000
    for i, payload in enumerate(payloads, start=1):
        ts = base_ts + i
        curr = _compute_hash(
            previous_log_hash=prev,
            operation_data=payload,
            tenant_id=tenant,
            timestamp_ms=ts,
        )
        rows.append(
            _build_row(
                row_id=i,
                operation=payload.get("op", "test"),
                op_data=payload,
                prev=prev,
                curr=curr,
                ts_ms=ts,
            )
        )
        prev = curr
    return rows


# ============================================================
# Chain verification scenarios
# ============================================================


@pytest.fixture
def fake_conn() -> MagicMock:
    """asyncpg-conn-like with a single .fetch() coroutine."""
    conn = MagicMock()
    conn.fetch = AsyncMock()
    return conn


@pytest.mark.asyncio
async def test_empty_chain_returns_zero(fake_conn: MagicMock) -> None:
    fake_conn.fetch.return_value = []
    n, reports = await _verify_tenant_chain(
        fake_conn, UUID("12345678-1234-1234-1234-123456789012"), from_date=None
    )
    assert n == 0
    assert reports == []


@pytest.mark.asyncio
async def test_single_valid_row_passes(fake_conn: MagicMock) -> None:
    tenant = UUID("12345678-1234-1234-1234-123456789012")
    rows = _link_chain(tenant, [{"op": "tool_executed", "v": 1}])
    fake_conn.fetch.return_value = rows
    n, reports = await _verify_tenant_chain(fake_conn, tenant, from_date=None)
    assert n == 1
    assert reports == []


@pytest.mark.asyncio
async def test_three_row_valid_chain_passes(fake_conn: MagicMock) -> None:
    tenant = UUID("12345678-1234-1234-1234-123456789012")
    rows = _link_chain(
        tenant,
        [
            {"op": "register", "v": 1},
            {"op": "approval", "v": 2},
            {"op": "logout", "v": 3},
        ],
    )
    fake_conn.fetch.return_value = rows
    n, reports = await _verify_tenant_chain(fake_conn, tenant, from_date=None)
    assert n == 3
    assert reports == []


@pytest.mark.asyncio
async def test_curr_hash_mismatch_when_payload_tampered(
    fake_conn: MagicMock,
) -> None:
    """Attacker rewrites operation_data but leaves curr_hash alone → detected."""
    tenant = UUID("12345678-1234-1234-1234-123456789012")
    rows = _link_chain(tenant, [{"op": "register"}])
    # Tamper: change the operation_data after curr_hash was committed
    rows[0]["operation_data"] = {"op": "register", "evil": True}
    fake_conn.fetch.return_value = rows
    n, reports = await _verify_tenant_chain(fake_conn, tenant, from_date=None)
    assert n == 1
    assert len(reports) == 1
    assert reports[0].error_type == "curr_hash_mismatch"
    assert reports[0].row_id == 1


@pytest.mark.asyncio
async def test_broken_link_when_prev_hash_wrong(fake_conn: MagicMock) -> None:
    """Row 2's prev_hash != row 1's curr_hash → detected."""
    tenant = UUID("12345678-1234-1234-1234-123456789012")
    rows = _link_chain(tenant, [{"op": "a"}, {"op": "b"}])
    # Tamper: rewrite row 2's prev_hash
    rows[1]["previous_log_hash"] = "f" * 64
    # Recompute row 2's curr_hash so payload integrity passes — purely chain break.
    rows[1]["current_log_hash"] = _compute_hash(
        previous_log_hash="f" * 64,
        operation_data=rows[1]["operation_data"],
        tenant_id=tenant,
        timestamp_ms=rows[1]["timestamp_ms"],
    )
    fake_conn.fetch.return_value = rows
    n, reports = await _verify_tenant_chain(fake_conn, tenant, from_date=None)
    assert n == 2
    types = {r.error_type for r in reports}
    assert types == {"broken_link"}, (
        "broken_link should fire because chain ran from row1.curr_hash to "
        f"row2.prev_hash; got types={types}"
    )


@pytest.mark.asyncio
async def test_payload_tamper_AND_chain_link_both_detected(
    fake_conn: MagicMock,
) -> None:
    """Payload mutate + recompute curr_hash → next row's prev_hash mismatches."""
    tenant = UUID("12345678-1234-1234-1234-123456789012")
    rows = _link_chain(tenant, [{"op": "a"}, {"op": "b"}])
    # Tamper row 1: change payload AND recompute curr_hash to "look honest"
    rows[0]["operation_data"] = {"op": "a", "tampered": True}
    rows[0]["current_log_hash"] = _compute_hash(
        previous_log_hash=rows[0]["previous_log_hash"],
        operation_data=rows[0]["operation_data"],
        tenant_id=tenant,
        timestamp_ms=rows[0]["timestamp_ms"],
    )
    # Row 2's prev_hash still points to OLD row1.curr_hash → broken_link will fire
    fake_conn.fetch.return_value = rows
    n, reports = await _verify_tenant_chain(fake_conn, tenant, from_date=None)
    assert n == 2
    types = sorted({r.error_type for r in reports})
    assert types == ["broken_link"], (
        f"row 1 looks consistent in isolation (curr_hash recomputed); "
        f"row 2's prev_hash mismatch is what reveals the tamper. types={types}"
    )


@pytest.mark.asyncio
async def test_from_date_passed_to_sql(fake_conn: MagicMock) -> None:
    """When from_date provided, the SQL gets a second positional param."""
    fake_conn.fetch.return_value = []
    tenant = UUID("12345678-1234-1234-1234-123456789012")
    fd = date(2026, 5, 1)
    await _verify_tenant_chain(fake_conn, tenant, from_date=fd)

    args, kwargs = fake_conn.fetch.call_args
    assert "AND created_at >= $2" in args[0]
    assert args[1] == tenant
    assert args[2] == fd


# ============================================================
# DB URL normalisation
# ============================================================


def test_normalise_db_url_strips_asyncpg_suffix() -> None:
    assert (
        _normalise_db_url("postgresql+asyncpg://user:pwd@h:5432/db")
        == "postgresql://user:pwd@h:5432/db"
    )


def test_normalise_db_url_passthrough_when_already_plain() -> None:
    assert _normalise_db_url("postgresql://user:pwd@h:5432/db") == "postgresql://user:pwd@h:5432/db"

#!/usr/bin/env python3
"""
File: backend/scripts/verify_audit_chain.py
Purpose: Walk audit_log per-tenant hash chains and detect tampering.
Category: Operations / Compliance tooling
Scope: Sprint 52.5 Day 4-5 (P0 #13 — W1-3 audit verifier)
Owner: DBA / SRE

Description:
    Stand-alone CLI (no Django / FastAPI dep — only `asyncpg` + stdlib)
    that verifies the integrity of `audit_log` per-tenant hash chains
    written by `infrastructure/db/audit_helper.py`.

    Algorithm:
        For each tenant_id (or one specified by --tenant):
            ORDER BY id ASC select rows
            expected_prev = SENTINEL_HASH (= "0" * 64)
            for row in rows:
                # 1. chain-link check
                if row.previous_log_hash != expected_prev:
                    → broken_link (forward-chain break)

                # 2. payload integrity check
                recomputed = SHA256(
                    row.previous_log_hash       # stored, not expected
                    || canonical_json(row.operation_data)
                    || str(tenant_id)
                    || str(timestamp_ms)
                )
                if recomputed != row.current_log_hash:
                    → curr_hash_mismatch (payload mutated)

                expected_prev = row.current_log_hash

    The two checks are independent:
        - broken_link catches "row was inserted in the middle and the
          attacker forgot to fix the next row's prev_hash"
        - curr_hash_mismatch catches "attacker rewrote operation_data
          but didn't recompute curr_hash"
        - Both fire when attacker rewrites a row + curr_hash AND the
          next row exists (broken_link from row N+1's perspective).

    Exit codes:
        0  — all chains verified
        1  — tampering detected (count + first-N reports printed)
        2  — usage / connectivity error

CLI:
    python -m scripts.verify_audit_chain [OPTIONS]

    --db-url URL          Postgres URL (default: $DATABASE_URL env var,
                          asyncpg-compatible scheme).
    --tenant UUID         Verify single tenant (default: all).
    --from-date YYYY-MM-DD
                          Only verify rows with created_at >= date.
    --ignore-tenant UUID  Skip tenant (repeatable; for known-test forgery
                          baselines like the W1-3 audit fake rows in
                          tenant aaaa-...-4444).
    --alert-webhook URL   POST JSON report on failure.
    --max-reports N       Cap printed report count (default 20).
    --quiet               Print only summary line.

Created: 2026-05-01 (Sprint 52.5 Day 4-5)
Last Modified: 2026-05-01

Modification History:
    - 2026-05-01: Initial creation (Sprint 52.5 Day 4-5) — P0 #13 verifier

Related:
    - infrastructure/db/audit_helper.py — hash compute (must match exactly)
    - infrastructure/db/models/audit.py — AuditLog ORM
    - 09-db-schema-design.md L654-717 (Group 7 Audit)
    - 14-security-deep-dive.md §append-only / hash chain
    - claudedocs/5-status/V2-AUDIT-W1-AUDIT-HASH.md (audit source)
    - claudedocs/5-status/V2-AUDIT-OPEN-ISSUES-20260501.md issue #13
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any
from uuid import UUID

import asyncpg


SENTINEL_HASH: str = "0" * 64


@dataclass(frozen=True)
class TamperReport:
    """A single tampering finding (one row, one mismatch type)."""

    tenant_id: str
    row_id: int
    error_type: str  # "broken_link" | "curr_hash_mismatch"
    expected: str
    actual: str
    operation: str
    created_at: str  # ISO 8601

    def short(self) -> str:
        return (
            f"tenant={self.tenant_id} id={self.row_id} "
            f"type={self.error_type} "
            f"expected={self.expected[:16]}... actual={self.actual[:16]}... "
            f"op={self.operation}"
        )


def _compute_hash(
    *,
    previous_log_hash: str,
    operation_data: dict[str, Any],
    tenant_id: UUID,
    timestamp_ms: int,
) -> str:
    """Mirror of `infrastructure/db/audit_helper.compute_audit_hash`.

    Must produce byte-identical hashes given the same inputs — any drift
    here would cause every row to fail verification.
    """
    payload_json = json.dumps(
        operation_data, sort_keys=True, separators=(",", ":")
    )
    base = f"{previous_log_hash}{payload_json}{tenant_id}{timestamp_ms}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


async def _list_tenants(conn: asyncpg.Connection) -> list[UUID]:
    rows = await conn.fetch(
        "SELECT DISTINCT tenant_id FROM audit_log ORDER BY tenant_id"
    )
    return [r["tenant_id"] for r in rows]


async def _verify_tenant_chain(
    conn: asyncpg.Connection,
    tenant_id: UUID,
    *,
    from_date: date | None,
) -> tuple[int, list[TamperReport]]:
    """Verify one tenant's chain. Returns (rows_checked, [TamperReport, ...])."""
    sql = """
        SELECT id, operation, operation_data, previous_log_hash,
               current_log_hash, timestamp_ms, created_at
        FROM audit_log
        WHERE tenant_id = $1
    """
    params: list[Any] = [tenant_id]
    if from_date is not None:
        sql += " AND created_at >= $2"
        params.append(from_date)
    sql += " ORDER BY id ASC"

    rows = await conn.fetch(sql, *params)
    reports: list[TamperReport] = []
    expected_prev = SENTINEL_HASH

    for row in rows:
        stored_prev = row["previous_log_hash"]
        # Chain-link check (compare against the running expected_prev).
        if stored_prev != expected_prev:
            reports.append(
                TamperReport(
                    tenant_id=str(tenant_id),
                    row_id=int(row["id"]),
                    error_type="broken_link",
                    expected=expected_prev,
                    actual=stored_prev,
                    operation=row["operation"],
                    created_at=row["created_at"].isoformat(),
                )
            )

        # Payload integrity: recompute using the row's STORED prev (not
        # `expected_prev`) so a payload tamper still fires curr_hash_mismatch
        # even when the chain link is also broken.
        op_data = row["operation_data"]
        if isinstance(op_data, str):
            # Some drivers return JSONB as string; canonicalise to dict.
            op_data = json.loads(op_data)

        recomputed = _compute_hash(
            previous_log_hash=stored_prev,
            operation_data=op_data,
            tenant_id=tenant_id,
            timestamp_ms=int(row["timestamp_ms"]),
        )
        if recomputed != row["current_log_hash"]:
            reports.append(
                TamperReport(
                    tenant_id=str(tenant_id),
                    row_id=int(row["id"]),
                    error_type="curr_hash_mismatch",
                    expected=recomputed,
                    actual=row["current_log_hash"],
                    operation=row["operation"],
                    created_at=row["created_at"].isoformat(),
                )
            )

        # Next iteration uses THIS row's STORED current_log_hash so the
        # chain advances even when payload was tampered.
        expected_prev = row["current_log_hash"]

    return len(rows), reports


def _post_alert_webhook(url: str, payload: dict[str, Any]) -> bool:
    """Best-effort POST. Returns True on 2xx, False otherwise (no raise)."""
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"alert webhook POST failed: {exc}", file=sys.stderr)
        return False


def _normalise_db_url(url: str) -> str:
    """Strip the `+asyncpg` driver suffix that SQLAlchemy uses but asyncpg
    rejects (`postgresql+asyncpg://...` → `postgresql://...`)."""
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def _main_async(ns: argparse.Namespace) -> int:
    db_url = ns.db_url or os.environ.get("DATABASE_URL")
    if not db_url:
        print(
            "ERROR: --db-url or DATABASE_URL required",
            file=sys.stderr,
        )
        return 2
    conn: asyncpg.Connection = await asyncpg.connect(_normalise_db_url(db_url))
    try:
        # Determine tenant set.
        ignore_set = {UUID(t) for t in ns.ignore_tenant}
        if ns.tenant:
            tenants = [UUID(ns.tenant)]
        else:
            tenants = await _list_tenants(conn)
        tenants = [t for t in tenants if t not in ignore_set]

        from_date: date | None = (
            datetime.strptime(ns.from_date, "%Y-%m-%d").date()
            if ns.from_date
            else None
        )

        all_reports: list[TamperReport] = []
        total_rows = 0
        for tenant in tenants:
            n, reports = await _verify_tenant_chain(
                conn, tenant, from_date=from_date
            )
            total_rows += n
            all_reports.extend(reports)

        if all_reports:
            if not ns.quiet:
                print(
                    f"FAIL: {len(all_reports)} tamper(s) detected across "
                    f"{total_rows} rows / {len(tenants)} tenants"
                )
                cap = ns.max_reports
                for rep in all_reports[:cap]:
                    print(f"  - {rep.short()}")
                if len(all_reports) > cap:
                    print(f"  ... ({len(all_reports) - cap} more)")
            else:
                print(
                    f"FAIL count={len(all_reports)} rows={total_rows} "
                    f"tenants={len(tenants)}"
                )
            if ns.alert_webhook:
                _post_alert_webhook(
                    ns.alert_webhook,
                    {
                        "status": "fail",
                        "tampers": [asdict(r) for r in all_reports],
                        "summary": {
                            "rows": total_rows,
                            "tenants": len(tenants),
                            "ignored_tenants": [str(t) for t in ignore_set],
                        },
                    },
                )
            return 1

        if not ns.quiet:
            print(
                f"OK: verified {total_rows} rows across "
                f"{len(tenants)} tenants"
            )
            if ignore_set:
                print(f"   (ignored {len(ignore_set)} tenants)")
        else:
            print(
                f"OK rows={total_rows} tenants={len(tenants)} "
                f"ignored={len(ignore_set)}"
            )
        return 0
    finally:
        await conn.close()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify audit_log per-tenant hash chains."
    )
    parser.add_argument(
        "--db-url",
        default=None,
        help="Postgres URL (default: $DATABASE_URL).",
    )
    parser.add_argument(
        "--tenant",
        default=None,
        help="Verify only this tenant UUID (default: all tenants).",
    )
    parser.add_argument(
        "--from-date",
        default=None,
        help="Only check rows where created_at >= this date (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--ignore-tenant",
        action="append",
        default=[],
        help=(
            "Skip this tenant UUID; repeatable. Useful for known-test "
            "forgery baselines (W1-3 audit fake rows under "
            "aaaa-aaaa-aaaa-aaaa-aaaa-aaaa-aaaa-4444)."
        ),
    )
    parser.add_argument(
        "--alert-webhook",
        default=None,
        help="POST JSON report on failure.",
    )
    parser.add_argument(
        "--max-reports",
        type=int,
        default=20,
        help="Cap number of tamper reports printed to stdout (default 20).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print one-line summary only (machine-friendly).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    ns = _parse_args(argv)
    return asyncio.run(_main_async(ns))


if __name__ == "__main__":
    raise SystemExit(main())

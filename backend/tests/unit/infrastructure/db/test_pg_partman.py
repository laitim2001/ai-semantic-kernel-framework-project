"""Test 0010 pg_partman migration metadata + ops-runbook docs.

Sprint 49.4 Day 4.6.

Why this is a unit test (not integration):
    The dev docker compose still uses postgres:16-alpine until users rebuild
    via `docker compose build postgres`. We can't reliably exec the migration
    in CI without orchestrating the new image first.

    What we CAN verify:
    - Migration file exists with correct revision IDs
    - upgrade() and downgrade() are present + safe (uses IF NOT EXISTS / IF EXISTS)
    - The ops runbook explains create_parent() invocation
    - 0010 follows 0009 in the revision chain
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_migration() -> object:
    repo_root = Path(__file__).resolve().parents[5]
    path = (
        repo_root
        / "backend"
        / "src"
        / "infrastructure"
        / "db"
        / "migrations"
        / "versions"
        / "0010_pg_partman.py"
    )
    spec = importlib.util.spec_from_file_location("mig_0010", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    # alembic.op import would resolve; for unit test we don't actually call upgrade()
    spec.loader.exec_module(mod)
    return mod


def test_migration_metadata_correct() -> None:
    mod = _load_migration()
    assert mod.revision == "0010_pg_partman"  # type: ignore[attr-defined]
    assert mod.down_revision == "0009_rls_policies"  # type: ignore[attr-defined]


def test_upgrade_uses_idempotent_create_extension() -> None:
    """upgrade() must use IF NOT EXISTS so partial re-runs are safe."""
    repo_root = Path(__file__).resolve().parents[5]
    path = (
        repo_root
        / "backend"
        / "src"
        / "infrastructure"
        / "db"
        / "migrations"
        / "versions"
        / "0010_pg_partman.py"
    )
    text = path.read_text(encoding="utf-8")
    assert "CREATE EXTENSION IF NOT EXISTS pg_partman" in text


def test_downgrade_uses_idempotent_drop() -> None:
    repo_root = Path(__file__).resolve().parents[5]
    path = (
        repo_root
        / "backend"
        / "src"
        / "infrastructure"
        / "db"
        / "migrations"
        / "versions"
        / "0010_pg_partman.py"
    )
    text = path.read_text(encoding="utf-8")
    assert "DROP EXTENSION IF EXISTS pg_partman" in text


def test_ops_runbook_documents_create_parent() -> None:
    """Module docstring must explain how to register messages / message_events."""
    mod = _load_migration()
    doc = mod.__doc__ or ""
    assert "create_parent" in doc
    assert "messages" in doc
    assert "message_events" in doc
    assert "p_premake" in doc

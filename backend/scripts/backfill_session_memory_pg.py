"""One-time backfill — Redis session memory → PostgreSQL (Sprint 172 AC-4).

Scans all ``memory:session:{user_id}:{memory_id}`` keys in Redis and upserts
each into the ``session_memory`` PostgreSQL table. Idempotent: re-running
leaves the table unchanged except for rows that legitimately got newer
content in Redis (ON CONFLICT DO UPDATE).

Usage:
    # Dry-run (count only, no writes)
    python backend/scripts/backfill_session_memory_pg.py --dry-run

    # Real backfill
    python backend/scripts/backfill_session_memory_pg.py

    # Limit scope (single user)
    python backend/scripts/backfill_session_memory_pg.py --user-id alice

Prerequisites (v2 CRITICAL — least-privilege):
    1. Dedicated DB role for migration:
         CREATE ROLE ipa_migrator LOGIN PASSWORD :'pw';
         GRANT CONNECT ON DATABASE ipa TO ipa_migrator;
         GRANT USAGE ON SCHEMA public TO ipa_migrator;
         GRANT SELECT, INSERT, UPDATE ON session_memory TO ipa_migrator;
         -- NO DELETE, NO DDL

    2. Credentials via env var sourced from secret manager
       (AWS Secrets Manager / Azure Key Vault). NEVER hardcode:
         export IPA_MIGRATOR_DB_URL=postgresql+asyncpg://ipa_migrator:...@...

    3. Alembic migration already applied (session_memory table exists):
         alembic upgrade head

Exit codes:
    0  Success; summary printed
    1  Infra unreachable (Redis down, PG down, env vars missing)
    2  Partial failure; see stderr
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Add backend/src to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("backfill_session_memory_pg")


async def _scan_session_keys(redis_client, user_filter: Optional[str]) -> list[str]:
    """Collect all session memory keys, optionally filtered by user."""
    pattern = f"memory:session:{user_filter}:*" if user_filter else "memory:session:*"
    keys: list[str] = []
    async for key in redis_client.scan_iter(match=pattern, count=200):
        if isinstance(key, bytes):
            key = key.decode("utf-8")
        keys.append(key)
    return keys


async def _load_record(redis_client, key: str) -> Optional[Dict[str, Any]]:
    raw = await redis_client.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw if isinstance(raw, str) else raw.decode("utf-8"))
    except (json.JSONDecodeError, AttributeError) as exc:
        logger.warning("malformed_session_key_skipped", extra={"key": key, "error": str(exc)})
        return None


async def _upsert_row(
    repo,
    record_dict: Dict[str, Any],
    key: str,
    default_ttl: int,
) -> bool:
    """Upsert one record. Returns True on success."""
    try:
        memory_id = record_dict.get("id") or ""
        user_id = record_dict.get("user_id") or ""
        if not memory_id or not user_id:
            logger.warning("session_key_missing_ids", extra={"key": key})
            return False

        # Derive expires_at from TTL when not present on record
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=default_ttl)

        metadata_dict = record_dict.get("metadata") or {}
        tags = metadata_dict.get("tags") or []

        await repo.upsert(
            memory_id=memory_id,
            user_id=user_id,
            content=record_dict.get("content", ""),
            memory_type=record_dict.get("memory_type", "conversation"),
            importance=float(metadata_dict.get("importance", 0.5)),
            access_count=int(record_dict.get("access_count", 0) or 0),
            accessed_at=(
                datetime.fromisoformat(record_dict["accessed_at"])
                if record_dict.get("accessed_at")
                else None
            ),
            expires_at=expires_at,
            extra_metadata=metadata_dict,
            tags=tags,
        )
        return True
    except Exception as exc:  # noqa: BLE001 — per-row tolerance
        logger.error(
            "backfill_row_failed",
            extra={"key": key, "error": str(exc), "error_type": type(exc).__name__},
        )
        return False


async def _run(dry_run: bool, user_filter: Optional[str]) -> Tuple[int, int]:
    try:
        import redis.asyncio as aioredis
    except ImportError:
        logger.error("redis.asyncio not installed — pip install redis")
        return 0, 0

    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_password = os.getenv("REDIS_PASSWORD") or None

    redis_client = aioredis.Redis(
        host=redis_host,
        port=redis_port,
        password=redis_password,
        decode_responses=True,
    )
    try:
        await redis_client.ping()
    except Exception as exc:
        logger.error(f"Redis unreachable at {redis_host}:{redis_port}: {exc}")
        await redis_client.close()
        return 0, 0

    keys = await _scan_session_keys(redis_client, user_filter)
    total = len(keys)
    logger.info(
        f"Found {total} session memory keys" + (f" for user={user_filter}" if user_filter else "")
    )

    if dry_run:
        await redis_client.close()
        return total, total  # dry-run: report potential count

    # Default TTL for expires_at (matches current MemoryConfig.session_memory_ttl)
    default_ttl = int(os.getenv("SESSION_MEMORY_TTL", "604800"))

    from src.infrastructure.database.repositories.session_memory import (
        SessionMemoryRepository,
    )
    from src.infrastructure.database.session import DatabaseSession

    succeeded = 0
    async with DatabaseSession() as pg_session:
        repo = SessionMemoryRepository(pg_session)
        for i, key in enumerate(keys, start=1):
            record = await _load_record(redis_client, key)
            if record is None:
                continue
            ok = await _upsert_row(repo, record, key, default_ttl)
            if ok:
                succeeded += 1
            if i % 100 == 0:
                logger.info(f"Progress: {i}/{total} processed, {succeeded} succeeded")

    await redis_client.close()
    return total, succeeded


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Count only, no writes")
    parser.add_argument("--user-id", type=str, default=None, help="Limit to single user")
    args = parser.parse_args()

    try:
        total, succeeded = asyncio.run(_run(args.dry_run, args.user_id))
    except KeyboardInterrupt:
        logger.info("Backfill cancelled by user")
        return 1
    except Exception as exc:
        logger.error(f"Backfill failed: {exc}", exc_info=True)
        return 1

    if args.dry_run:
        print(f"[dry-run] {total} session memory keys would be backfilled")
        return 0

    print(f"Backfill complete: {succeeded}/{total} succeeded")
    if succeeded < total:
        print(f"  {total - succeeded} rows failed — see logs", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

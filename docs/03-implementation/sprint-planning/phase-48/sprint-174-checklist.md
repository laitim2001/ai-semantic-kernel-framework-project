# Sprint 174 Checklist — Bitemporal Support

**Sprint**: 174
**Branch**: `research/memory-system-enterprise`
**Plan**: [sprint-174-plan.md](sprint-174-plan.md)

---

## Backend — Schema

- [ ] `MemoryEntry` adds `event_time`, `ingestion_time`, `claimed_event_time`, `superseded_at`, `superseded_by`
- [ ] Alembic migration ALTER `session_memory` with new cols
- [ ] Backfill legacy rows: `event_time = created_at`, `ingestion_time = created_at`
- [ ] Index `(org_id, event_time)` for as-of queries
- [ ] Qdrant payload additions: `event_time`, `ingestion_time`, `superseded_at` as ISO8601

## Backend — As-Of Query

- [ ] `UnifiedMemoryManager.search_as_of(query, scope, as_of_time)` method
- [ ] PostgreSQL filter: `event_time <= as_of AND (superseded_at IS NULL OR superseded_at > as_of)`
- [ ] Qdrant payload filter equivalent
- [ ] `GET /api/v1/memory/search?as_of=...` endpoint
- [ ] RBAC check: `auditor` role required
- [ ] 1min result cache by `(query, scope_hash, as_of)` key

## Backend — Event Time Integrity

- [ ] Pydantic memory create schema rejects `event_time` field (422)
- [ ] `claimed_event_time` field accepted but stored separately
- [ ] Default `event_time = ingestion_time`
- [ ] Signed source event hook: use signed timestamp if valid

## Backend — Supersede Flow

- [ ] `supersede(old_memory_id, new_entry)` helper method
- [ ] Old entry: `superseded_at = new.event_time`, `superseded_by = new.memory_id`
- [ ] Default search returns new; `search_as_of` < supersede point returns old

## Backend — Backfill Scripts

- [ ] `scripts/backfill_bitemporal_pg.py` — fills `event_time` in session_memory
- [ ] `scripts/backfill_bitemporal_qdrant.py` — fills payload in Qdrant points
- [ ] Both idempotent (SQL DEFAULT / Qdrant SET payload)
- [ ] Dry-run + apply modes

## Tests — Unit

- [ ] `test_bitemporal_types.py` — field defaults, validation
- [ ] `test_event_time_integrity.py` — body `event_time` → 422
- [ ] `test_event_time_integrity.py` — `claimed_event_time` stored, unused
- [ ] `test_search_as_of.py` — returns correct set for various as-of windows
- [ ] `test_search_as_of.py` — RBAC: non-auditor gets 403
- [ ] `test_supersede_flow.py` — old entry queryable historically
- [ ] `test_supersede_flow.py` — new entry is default search result

## Tests — Integration

- [ ] `test_bitemporal_policy_change.py` — policy at t1 → change at t2 → as_of=t1.5 returns v1, as_of=t3 returns v2
- [ ] `test_backfill_bitemporal.py` — run scripts twice, count unchanged

## Tests — Security

- [ ] `test_event_time_forgery.py` — body forgery attempt: `event_time=2020-01-01` → 422 or silently ignored
- [ ] `test_event_time_forgery.py` — webhook signed timestamp within payload IS used

## Verification

- [ ] All Python files pass `black`, `isort`, `flake8`, `mypy`
- [ ] Alembic migration up + down
- [ ] `pytest backend/tests/unit/integrations/memory/test_bitemporal_types.py test_event_time_integrity.py test_search_as_of.py test_supersede_flow.py -v`
- [ ] `pytest backend/tests/integration/memory/test_bitemporal_policy_change.py -v`
- [ ] `pytest backend/tests/security/test_event_time_forgery.py -v`
- [ ] Manual: create memory at t1 → update at t2 → call `/search?as_of=t1.5` → returns v1 content
- [ ] Manual: verify Qdrant payload has `event_time` via `scroll` after backfill

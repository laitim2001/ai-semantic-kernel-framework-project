# Sprint 177a Checklist — GDPR + Saga + Audit Chain (Compliance Critical)

**Sprint**: 177a (split from original Sprint 177 after Batch 4 RED verdict)
**Branch**: `research/memory-system-enterprise`
**Plan**: [sprint-177a-plan.md](sprint-177a-plan.md)

---

## Backend — Forgotten Users Tombstone

- [ ] `domain/auth/models/forgotten_user.py` ORM model with `user_id_hash`, `org_id`, `forgotten_at`, `reason`, `audit_chain_id`
- [ ] Unique constraint `(org_id, user_id_hash)` to prevent duplicate tombstones
- [ ] Index `(org_id, user_id_hash)` for fast lookup
- [ ] `ForgottenUserRepository` with `list_by_org()`, `exists(org, user_hash)`, `insert()`
- [ ] Alembic migration

## Backend — GDPR Saga Service

- [ ] `domain/auth/services/gdpr_service.py` with `forget_user(user_id, scope, requester, confirm_token, approver)`
- [ ] Confirm token validation (signed, time-bound)
- [ ] Two-person approval check for sensitive users
- [ ] Audit-row-first (`status=pending`) before any deletion
- [ ] Per-layer delete: Redis / PG / Qdrant / mem0 with independent try/except
- [ ] Per-layer status map `{completed | failed:reason}`
- [ ] Retry queue enqueue for failed layers
- [ ] Tombstone write after delete attempts
- [ ] Audit finalize with per-layer status
- [ ] `ForgetReport` dataclass returned
- [ ] HTTP status: 200 if all complete, 202 if any pending retry

## Backend — Retry Worker

- [ ] `gdpr_retry_worker.py` background consumer of `gdpr_retry_queue`
- [ ] Exponential backoff per retry attempt
- [ ] Max retry count = 5, alert ops on exceed
- [ ] Audit row updated on successful retry
- [ ] Metric: `gdpr_retry_total{layer, status}`

## Backend — Audit Chain

- [ ] `domain/auth/models/gdpr_audit_log.py` ORM with sequence, hmac, prev_hash, payload_hash, status, per_layer_status
- [ ] Unique constraint on `sequence` column
- [ ] Index on sequence
- [ ] KMS pepper fetch helper (`infrastructure/kms/audit_pepper.py`) with brief cache
- [ ] Write path uses `SET TRANSACTION ISOLATION LEVEL SERIALIZABLE`
- [ ] Write path acquires `pg_advisory_xact_lock`
- [ ] HMAC computed: `HMAC-SHA256(prev_hash || payload_hash, pepper)`
- [ ] `write_pending()` + `finalize(audit_id, status_map)` methods
- [ ] Chain verification helper: `verify_chain(from_sequence, to_sequence)`

## Backend — Append-Only Enforcement

- [ ] Alembic migration creates `prevent_audit_modification()` PG function
- [ ] Trigger `gdpr_audit_append_only` on UPDATE/DELETE → RAISE EXCEPTION
- [ ] Separate role `gdpr_audit_writer` with INSERT-only grant
- [ ] REVOKE UPDATE/DELETE from PUBLIC and application role
- [ ] WAL archival config documented (S3 WORM target for forensic recovery)

## Backend — Merkle Anchor

- [ ] `merkle_anchor_job.py` nightly cron
- [ ] Collects past 24h audit rows
- [ ] Builds Merkle tree from `hmac` values
- [ ] Writes root to S3 with `ObjectLockMode=COMPLIANCE`, `ObjectLockRetainUntilDate=+7yr`
- [ ] Verification script `verify_merkle_anchor.py` for audit/compliance queries
- [ ] Metric: `merkle_anchor_written_total`, `merkle_anchor_row_count`

## Backend — Signed Confirm Token + Maker/Checker

- [ ] `POST /api/v1/users/{user_id}/forget/prepare` endpoint
- [ ] RBAC: `gdpr-operator` or `admin` role required
- [ ] KMS-signed token with `{user_id, op, exp (+5min), nonce}`
- [ ] `DELETE /api/v1/users/{user_id}/memory?confirm_token=...&approver_token=...`
- [ ] Token signature + expiration validated
- [ ] Two-person requirement detected (sensitive user list) → both tokens required
- [ ] Self-approval (same requester + approver) rejected with 400

## Backend — DLQ Retention with SOX Awareness

- [ ] `DLQEventCategory` enum: OPERATIONAL / AUTH / GDPR / SECURITY
- [ ] `RETENTION_POLICY` dict mapping category → (redact_after, delete_after)
- [ ] `dlq_maintenance.py` background task runs hourly
- [ ] Redact logic: SHA-256 hash PII fields (`user_id`, `content`)
- [ ] Delete logic: entries older than `delete_after` removed (except indefinite)
- [ ] Event classifier: maps DLQ source module to category (auth/security/gdpr/operational)
- [ ] `DLQ_*_RETENTION_DAYS` config vars in settings

## Backend — Bitemporal Integration (consumes Sprint 174 v2)

- [ ] `UnifiedMemoryManager.search_as_of()` modified to filter against `forgotten_users` tombstone
- [ ] Filter applied at query layer (no bypass via raw SQL)
- [ ] AC-4 (Sprint 174 v2) now includes forgotten-users filter

## Tests — GDPR Compliance

- [ ] `test_gdpr_forget_user_full.py` — 4-layer deletion + tombstone + audit
- [ ] `test_gdpr_forget_partial_failure.py` — Qdrant down → 202 + retry queue entry
- [ ] `test_gdpr_forget_partial_retry_succeeds.py` — simulated retry → all layers eventually complete
- [ ] `test_as_of_filters_forgotten.py` — bitemporal `as_of` excludes forgotten users
- [ ] `test_2p_approval.py` — self-approval rejected; dual-principal approval accepted

## Tests — Audit Chain

- [ ] `test_audit_chain_integrity.py` — 100 sequential writes, each HMAC verified
- [ ] `test_audit_chain_concurrent.py` — 10 parallel writes, unique sequences + chain intact
- [ ] `test_audit_chain_tamper_detection.py` — modify payload, verify fails
- [ ] `test_audit_chain_1000_row.py` — scale test, full verification runs < 10s

## Tests — Append-Only

- [ ] `test_append_only_trigger.py` — UPDATE raises PG exception
- [ ] `test_append_only_trigger.py` — DELETE raises
- [ ] `test_audit_writer_role.py` — INSERT succeeds, UPDATE fails with explicit privilege error

## Tests — DLQ Retention

- [ ] `test_dlq_retention_operational.py` — freezegun +31d → redacted; +91d → deleted
- [ ] `test_dlq_retention_auth.py` — +91d → redacted; +7yr-1d → still present; +7yr+1d → deleted
- [ ] `test_dlq_retention_gdpr.py` — indefinite retention, no redact, no delete

## Tests — Merkle Anchor

- [ ] `test_merkle_anchor_daily.py` — mock S3, verify write with correct lock settings
- [ ] `test_merkle_verification.py` — tamper one row → Merkle verification fails

## Verification

- [ ] All Python files pass `black`, `isort`, `flake8`, `mypy`
- [ ] Alembic: `upgrade head` + `downgrade -1` both work
- [ ] `pytest backend/tests/integration/security/ -v` — all GDPR tests pass
- [ ] `pytest backend/tests/compliance/ -v` (new category) — append-only, audit chain, retention
- [ ] Audit chain integrity run: `python scripts/verify_audit_chain.py --from 1 --to 1000` passes
- [ ] Manual: issue forget → check all 4 layers + tombstone + audit + Merkle queue
- [ ] Manual: attempt `UPDATE gdpr_audit_log ...` via psql → error thrown
- [ ] Sign-off table filled: backend-lead + sec-lead + compliance officer

## Phase 48 Exit Gate (blocks Phase 48 close)

- [ ] All 12 ACs in sprint-177a-plan.md passed
- [ ] All compliance tests pass (no skips)
- [ ] Merkle anchor scheduled job running in staging
- [ ] DPIA draft scheduled for Sprint 177b / Phase 49
- [ ] Sign-off signatures captured in git-tracked document

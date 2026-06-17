# 39 — Transcript Retention (apply + preview on the canonical tenants.retention_days)

**Purpose**: Spike design note for Sprint 57.134 — per-tenant transcript retention enforcement (delete `messages` + `message_events` older than the tenant's retention window) + a dry-run preview, built on the EXISTING `tenants.retention_days` column.
**Category / Scope**: platform_layer.transcripts (data lifecycle) / Phase 57 / Sprint 57.134
**Created**: 2026-06-17
**Status**: Active
**Verified ratio**: ~95% (every invariant below has a file:line + a passing test or a drive-through; the deferred items are explicitly fenced)

> **Modification History**
> - 2026-06-17: Initial creation (Sprint 57.134) — extracted from the shipped apply/preview implementation

---

## 1. Spike Summary — what was built + the pivot

**User story**: As a platform admin, I want to enforce a tenant's transcript retention window (delete chat transcripts older than N days) and preview the impact first.

Shipped (backend-only, NO migration):
- `apply_transcript_retention(db, tenant_id, retention_days, *, now, dry_run)` — `backend/src/platform_layer/transcripts/retention.py:71`.
- POST `/{tenant_id}/transcript-retention/apply` — `backend/src/api/v1/admin/tenants.py:1922` (reads `tenant.retention_days`, deletes, audits, commits).
- GET `/{tenant_id}/transcript-retention/preview` — `backend/src/api/v1/admin/tenants.py:1893` (dry-run COUNT, no commit).

**The pivot** (Day-1, user-approved): the plan first added a parallel `meta_data["transcript_retention"]` config; a Day-1 read found `Tenant.retention_days` already exists → the parallel config was an AP-6 violation, dropped. The retention *window* is the canonical column; this slice adds only the *enforcement* + *preview*.

## 2. Decision Matrix

| Option (recon) | Config source | Scheduling | Drive-through-able | Decision |
|----------------|---------------|------------|--------------------|----------|
| A. parallel `meta_data` config + apply | NEW JSONB key | manual | yes | ❌ AP-6 parallel config (dropped Day-1) |
| **A′ (shipped). canonical `retention_days` + apply + preview** | **existing `tenants.retention_days`** | manual (apply POST) + dry-run preview | **yes (preview safe, apply on throwaway)** | ✅ user pick "Pivot + preview" |
| C. config + scheduled background job | column | poll loop (billing-drainer mirror) | hard (clock/trigger) | deferred (follow-on) |
| D. partition-drop (pg_partman) | column | DB extension | hard (prod data migration) | deferred (Ops slice) |

WHY A′: the retention window already has a canonical home (`tenants.retention_days`, Sprint 57.46, `identity.py:156`); building a second config duplicates state that can drift (AP-6). Manual apply + a dry-run preview is fully verifiable now (the preview is the safe drive-through path the user requested); the scheduled job is mechanical once deletion is proven.

## 3. Verified Invariants (file:line + test/drive-through)

- **Config is the canonical column**: `Tenant.retention_days` `Mapped[int]` NOT NULL default 90, settable via PATCH `/tenants/{id}` (`api/v1/admin/tenants.py:645` `Field(None, ge=1, le=3650)` → `:718`). Drive-through Leg-1 PATCH 90→1→90 moved the preview cutoff `identity.py:156`.
- **Deletion window**: `cutoff = now - timedelta(days=retention_days)`; deletes `created_at < cutoff` on both tables (`retention.py:96,100,105`). Test `test_apply_deletes_old_keeps_recent` (old now-60d deleted, recent now-5d kept).
- **Tenant isolation**: explicit `WHERE tenant_id` (`retention.py:101,106`) + `SET LOCAL app.tenant_id` (`retention.py:91`) for the FORCE'd RLS (`migrations/0009_rls_policies.py:97`). Test `test_apply_multi_tenant_isolation` (tenant A apply leaves tenant B's row). Drive-through Leg-2 deleted only the throwaway tenant's old row.
- **Dry-run preview never mutates**: `dry_run=True` → COUNT path (`retention.py:98`), endpoint does not commit (`tenants.py:1893`). Test `test_preview_counts_without_deleting` (both rows still present after).
- **Admin-gated + 404 cross-tenant**: `require_admin_platform_role` + `_load_tenant_or_404` on both endpoints. Tests `test_apply_requires_admin_role` / `*_tenant_not_found`.
- **Audited**: `append_audit("tenant_transcript_retention_apply", {retention_days, cutoff, deleted_*})` (`tenants.py:1939`). Test `test_apply_audit_chain_emitted`.

**Verification command**: `cd backend && pytest tests/unit/platform_layer/transcripts/test_retention.py tests/integration/api/test_admin_transcript_retention.py -q` (10 passed). Drive-through: `docs/.../sprint-57-134/artifacts/drivethrough-results.md` + `seed_drivethrough.py`.

## 4. Cross-Category Contracts

No new contract / ABC / wire event → no `17-cross-category-interfaces.md` entry. Consumes the existing `Tenant.retention_days` column + the `Message`/`MessageEvent` ORM + `append_audit`. Provider-neutral (no SDK / agent_harness import; `check_llm_sdk_leak` + `check_cross_category_import` green).

## 5. Open Invariants (DEFERRED — NOT verified this slice)

- **Scheduled enforcement**: no background job runs apply automatically; retention is manual-apply only. Follow-on: mirror the billing-outbox drainer (`api/main.py:267-336`).
- **Partition lifecycle**: `messages`/`message_events` have 3 static monthly partitions (2026-04/05/06, `migrations/0002:175-238`); no `*_default` + pg_partman not activated (`migrations/0010`). Post-2026-06 writes + partition-drop are an ADJACENT gap (Option D / Ops), orthogonal to this DELETE (which acts on the parent across partitions).
- **FE surface**: no Tenant Settings retention tab; the surface this slice is the admin API.
- **GDPR per-user erasure**: separate; no existing code.

## 6. Rollback

Pure-additive backend (1 new module + 2 endpoints + tests; NO migration, NO schema change). Rollback = revert the 2 commits (delete `platform_layer/transcripts/` + the `tenants.py` transcript-retention block + the 2 tests + the conftest sweep line). No data migration to undo; `tenants.retention_days` is untouched (pre-existing). Estimated < 30 min.

## 7. References

- `backend/src/platform_layer/transcripts/retention.py` — apply/preview core
- `backend/src/api/v1/admin/tenants.py:1865+` — the apply POST + preview GET
- `backend/src/infrastructure/db/models/identity.py:156` — `Tenant.retention_days` (canonical column)
- `backend/src/infrastructure/db/migrations/versions/0009_rls_policies.py:97` — FORCE RLS (drives the SET LOCAL)
- `claudedocs/4-changes/feature-changes/CHANGE-101-transcript-retention.md`
- `.claude/rules/multi-tenant-data.md` — tenant-isolation 鐵律 (the WHERE + RLS handling)

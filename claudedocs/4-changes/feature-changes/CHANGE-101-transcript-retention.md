# CHANGE-101: per-tenant transcript retention (apply + preview)

**Date**: 2026-06-17
**Sprint**: 57.134
**Scope**: Backend — `platform_layer/transcripts` (data lifecycle) + admin API; closes the transcript-retention (57.125 deferred infra) Option-A slice

## Problem

`messages` (57.127) + `message_events` (57.125) accumulate forever — zero retention / TTL / cleanup anywhere. A tenant needs "keep transcripts for N days" enforced.

## Root Cause

No retention enforcement existed. The per-tenant retention *window* config, however, ALREADY existed as `tenants.retention_days` (Sprint 57.46 SaaS settings; NOT NULL default 90; settable via admin PATCH `/tenants/{id}`, range 1-3650) — only the *enforcement* (deletion) was missing.

## Solution

**Day-1 pivot** (user-approved AskUserQuestion): the plan originally added a parallel `meta_data["transcript_retention"]` config; a Day-1 read found the canonical `tenants.retention_days` column → building a second config would violate AP-6 (parallel config). Dropped the parallel config; shipped enforcement on the canonical column + a dry-run preview.

Backend-only (NO migration — config is the existing column, deletion is a DELETE query):
- `platform_layer/transcripts/retention.py` — `apply_transcript_retention(db, tenant_id, retention_days, *, now, dry_run) -> RetentionStats`: `cutoff = now - retention_days`; deletes (or, dry_run, COUNTs) `messages` + `message_events` `WHERE tenant_id AND created_at < cutoff`. Sets `app.tenant_id` (set_config local) for the FORCE'd RLS on those tables (migration 0009) + explicit `WHERE tenant_id` = correct whether RLS is enforced (prod non-owner role) or bypassed (dev owner).
- `api/v1/admin/tenants.py` — POST `/{tenant_id}/transcript-retention/apply` (reads `tenant.retention_days`, deletes, audits `tenant_transcript_retention_apply`, commits) + GET `/{tenant_id}/transcript-retention/preview` (dry-run COUNT, no commit). Both `require_admin_platform_role` + `_load_tenant_or_404`.

Deferred (→ follow-ons): the scheduled background cleanup job (mirror the billing-outbox drainer), partition-drop / pg_partman activation, a FE Tenant Settings retention tab.

## Verification

- **Gates**: mypy `src` 0/374 · run_all 10/10 · backend pytest **2741 passed / 5 skip** (baseline 2731 +10: 3 unit + 7 integration) · black/isort/flake8 clean · LLM-SDK-leak clean. FE untouched.
- **Integration (real PostgreSQL)**: apply deletes rows < cutoff, keeps within-window rows, **multi-tenant isolation** (tenant A apply leaves tenant B's rows), audit chain; preview dry-run counts without deleting; cross-tenant 404. Backdated seeded rows (now-60d / now-5d).
- **Drive-through PASS** (real running uvicorn PID 55768 + real admin auth dan@acme.com platform_admin + real DB; `docs/.../sprint-57-134/artifacts/drivethrough-results.md`): Leg-1 preview on acme-prod (non-destructive; PATCH retention_days 90→1→90, cutoff tracks; would_delete 0 = no real old transcripts). Leg-2 apply on a throwaway tenant (DESTRUCTIVE primary path): preview would_delete 1/1 → apply deleted 1/1 → preview_after 0/0 → DB REMAINING_MESSAGES=1 (recent survived) → tenant cleaned up.

## Impact

Backend. First transcript-retention enforcement. Reuses the canonical `tenants.retention_days` (no parallel config). Design note 39 (new domain). NO migration. The destructive apply is admin-gated + tenant-scoped + RLS-safe.

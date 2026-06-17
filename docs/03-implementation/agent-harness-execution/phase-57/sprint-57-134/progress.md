# Sprint 57.134 Progress — per-tenant transcript retention (config + manual apply)

[Plan](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-134-plan.md) · [Checklist](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-134-checklist.md)

---

## Day 0 — Plan-vs-Repo Verify (三-prong) + Branch — 2026-06-17

### Drift findings (against `main` HEAD `631f599a`)

| ID | Finding | Implication |
|----|---------|-------------|
| **D-no-retention** | ✅ GREEN — zero existing retention/purge/cleanup/DROP-PARTITION in app code (Explore + grep) | New domain, no collision. |
| **D-rls-delete** | 🔴 CONFIRMED — `messages` + `message_events` (+ `audit_log`) have `FORCE ROW LEVEL SECURITY` (`0009_rls_policies.py:97`); policy USING `current_setting('app.tenant_id', true)::uuid`. Admin endpoints use **plain `get_db_session`** (`tenants.py:311`), which does NOT set app.tenant_id. | apply DELETE + the audit INSERT MUST `set_config('app.tenant_id', tid, true)` (SET LOCAL) inside the txn → correct under enforced RLS; harmless if the app role bypasses RLS (dev). Plus explicit `WHERE tenant_id` = safe either way. (The `tenants` registry table has NO RLS — that's why harness-policy upsert works without a SET.) |
| **D-meta-data-key** | ✅ GREEN — `transcript_retention` not found anywhere → free `tenant.meta_data` key (no collision with model_policy/harness_policy/quota_overrides/rate_limits). | |
| **D-append-audit-sig** | ✅ `append_audit(session, *, tenant_id, operation, resource_type, operation_data, user_id=None, session_id=None, resource_id=None, operation_result=None, timestamp_ms=None)` (`audit_helper.py:90`). `_load_tenant_or_404` + `require_admin_platform_role` already imported in tenants.py. | Mirror the harness-policy upsert call exactly. |
| **D-default-partition** | `messages`/`message_events` = 3 static monthly partitions 2026-04/05/06 (`0002:175-238`), NO `*_default` in 0002. Today's (2026-06-17) chat writes succeed → the June partition covers now. | The retention DELETE acts on the parent across all partitions regardless. Post-2026-06 writes need a default/new partition — an ADJACENT partition-management gap (note in design note; → follow-on / Option D, NOT this slice). |

**Go/no-go**: D-rls-delete + D-meta-data-key resolved → proceed. RLS handling designed (SET LOCAL app.tenant_id + explicit WHERE). 0% scope shift.

**Branch**: `git checkout -b feature/sprint-57-134-transcript-retention` from `main` `631f599a`.

---

## Day 1 — Implementation + the major pivot — 2026-06-17

### 🔴 D-existing-retention-days PIVOT (mid-implementation Day-0 escape → caught + corrected)

After writing the planned `meta_data["transcript_retention"]` config (policy + resolver + cache + PUT/GET), a deeper read of `identity.py` surfaced that **`Tenant.retention_days` ALREADY EXISTS** (Sprint 57.46 SaaS settings; `nullable=False default=90`) and is ALREADY settable via the admin **PATCH `/tenants/{id}`** (`tenants.py:645/715-719`, range 1-3650) + returned in `TenantResponse`. My new config was a **parallel config** → AP-6 violation + "check existing before building". (Lesson: my Day-0 D-meta-data-key grepped the `transcript_retention` KEY but not for an existing `retention_days` COLUMN — the AD-Plan content-verify gap.)

**User pick (AskUserQuestion)**: "Pivot + 補一個 GET apply-preview". Pivoted:
- DROPPED `retention_policy.py` (the parallel policy/resolver/cache) + the config PUT/GET + schemas.
- Module → `retention.py`: just `RetentionStats` + `apply_transcript_retention(db, tenant_id, retention_days, *, now, dry_run)` reading the canonical column.
- Added a **dry-run** mode (COUNT, no mutation) → the `preview` GET.

### Final code (backend-only; NO migration)
- `platform_layer/transcripts/retention.py` — `apply_transcript_retention` (delete or dry-run count); SET LOCAL `app.tenant_id` for FORCE'd RLS + explicit WHERE tenant_id.
- `api/v1/admin/tenants.py` — `TranscriptRetentionApplyResponse` + `TranscriptRetentionPreviewResponse`; POST `…/transcript-retention/apply` (reads `tenant.retention_days`, deletes, audits, commits) + GET `…/transcript-retention/preview` (dry-run count, no commit).
- `__init__.py`.

---

## Day 2 — Tests + full gate — 2026-06-17

- Unit `tests/unit/platform_layer/transcripts/test_retention.py` (+3): dry-run counts / apply rowcounts / cutoff math (fake session).
- Integration `tests/integration/api/test_admin_transcript_retention.py` (+7): apply auth/404 + delete-old-keep-recent + **multi-tenant isolation** (tenant A apply leaves tenant B) + audit chain; preview dry-run (no delete) + 404. Seeds real Tenant→User→Session→Message/MessageEvent with backdated created_at (now-60d / now-5d).
- conftest: `TRANSCRIPTRET_%` committed-tenant sweep (CASCADE).
- **Gates**: mypy `src` **0/374** · run_all **10/10** · backend pytest **2741 passed / 5 skip** (baseline 2731 +10) · black/isort/flake8 clean · LLM-SDK-leak clean. FE untouched.
- Fixed 4 mypy (rowcount via getattr / `model: Any`) + 9 flake8 E501 (docstrings + test session typed `Any`).

---

## Day 3 — Drive-through — 2026-06-17

Real running uvicorn (clean restart PID 55768 with new routes) + real admin auth (dev-login dan@acme.com platform_admin, httpOnly cookie via Vite `/api` proxy) + real PostgreSQL. Full detail + tables: `artifacts/drivethrough-results.md`.

- **Leg 1 — preview on acme-prod (non-destructive)**: GET preview (retention 90) → cutoff 2026-03-19, would_delete 0/0; PATCH retention_days 90→1 → cutoff tracks to 2026-06-16; reset → 90. ✅ Route registered + admin auth + reads canonical `retention_days` + config-responsive + non-destructive. (0 because acme-prod has no transcripts older than the cutoff — real data is today / pre-57.127 0-turn.)
- **Leg 2 — apply on a throwaway tenant (DESTRUCTIVE primary path)**: seeded old (now-60d) + recent (now-5d), retention 30. preview → would_delete **1/1**; POST apply → **deleted 1/1**; preview_after → 0/0; DB `REMAINING_MESSAGES=1` (recent survived). ✅ Destructive primary path driven end-to-end through the real server+auth+DB; old deleted, recent kept, counts match. Throwaway tenant cleaned up (CASCADE + WORM toggle).

**Verdict**: Drive-through PASS (preview + apply both driven on the real server). Complements the 7 integration tests (real DB, isolation, audit).

---

## Day 4 — CHANGE-101 + design note + closeout — 2026-06-17

- CHANGE-101 + design note (new domain: retention contract + deletion/RLS semantics + scheduling deferral) + retrospective Q1-Q7 + navigators + calibration.

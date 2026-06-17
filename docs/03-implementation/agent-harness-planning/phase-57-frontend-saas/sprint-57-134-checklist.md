# Sprint 57.134 — Checklist (per-tenant transcript retention: apply + preview on canonical retention_days)

[Plan](./sprint-57-134-plan.md)

> **🔴 DAY-1 PIVOT** (user-approved): `Tenant.retention_days` already exists (Sprint 57.46) → dropped the parallel `meta_data["transcript_retention"]` config; shipped = apply POST + dry-run preview GET on the canonical column. Superseded config tasks below marked **SUPERSEDED** (not deleted — audit trail).

---

## Day 0 — Plan-vs-Repo Verify (三-prong) + Branch

### 0.1 Three-prong Day-0 verify (against `main` HEAD `631f599a`)
- [x] **Prong 1 — path verify**: `harness_policy.py` + `tenants.py` + `sessions.py` present; `platform_layer/transcripts/` free; `CHANGE-101` free
- [x] **Prong 2 — content verify** (drift → progress.md):
  - [x] **D-no-retention** — zero existing retention/purge/cleanup ✅
  - [x] **D-rls-delete** — `messages`/`message_events`/`audit_log` are `FORCE ROW LEVEL SECURITY` (`0009:97`); admin uses plain `get_db_session` → apply needs `SET LOCAL app.tenant_id` ✅
  - [x] **D-meta-data-key** — `transcript_retention` key free ✅ (BUT missed the existing `retention_days` COLUMN → Day-1 pivot; lesson logged)
  - [x] **D-existing-retention-days** (Day-1) — 🔴 `Tenant.retention_days` EXISTS (Sprint 57.46, PATCH-settable) → PIVOT
  - [x] **D-default-partition** — 3 static monthly partitions (no default in 0002); DELETE acts on parent regardless ✅
  - [x] **D-append-audit-sig** — `append_audit(session, *, tenant_id, operation, …)` confirmed ✅
- [x] **Prong 3 — schema verify**: N/A (no migration — canonical column + DELETE query)
- [x] **D-baselines** — pytest 2731+5skip · mypy 0/374 · run_all 10/10
- [x] **Catalog drift** — progress.md Day-0 table
- [x] **Go/no-go** — proceed (pivot mid-Day-1, user-approved)

### 0.2 Branch
- [x] `git checkout -b feature/sprint-57-134-transcript-retention` (from `main` `631f599a`)

---

## Day 1 — Apply core (US-2 + US-3) + the pivot

### 1.1 ~~Policy + resolver~~ **SUPERSEDED by pivot**
- [x] ~~TranscriptRetentionPolicy + from_dict/to_dict + cache + resolver~~ **SUPERSEDED** — canonical `tenants.retention_days` used instead (no policy object); `retention_policy.py` written then DROPPED

### 1.2 Apply + dry-run — `platform_layer/transcripts/retention.py`
- [x] **`apply_transcript_retention(db, tenant_id, retention_days, *, now, dry_run)` → `RetentionStats`**
  - cutoff = now - retention_days; SET LOCAL app.tenant_id; dry_run → COUNT, else DELETE messages + message_events `WHERE tenant_id AND created_at < cutoff` ✅
- [x] **`__init__.py`** ✅

### 1.x Partial gate
- [x] mypy `src` 0/374 (fixed rowcount via getattr + `model: Any`) · black/isort/flake8 on the module ✅

---

## Day 2 — Admin endpoints + tests (US-1 + US-3 + full gate)

### 2.1 Admin endpoints — `api/v1/admin/tenants.py`
- [x] ~~PUT/GET `/transcript-retention` config~~ **SUPERSEDED** — config is the existing PATCH `/tenants/{id}` retention_days
- [x] **POST `/{tenant_id}/transcript-retention/apply`** (reads `tenant.retention_days`, deletes, `append_audit`, commit) ✅
- [x] **GET `/{tenant_id}/transcript-retention/preview`** (dry-run count, no commit) ✅
  - DoD: cross-tenant → 404 (`_load_tenant_or_404`); `require_admin_platform_role` ✅

### 2.2 Tests
- [x] **unit `test_retention.py`** (+3) — dry-run count / apply rowcounts / cutoff (fake session) ✅
- [x] **integration `test_admin_transcript_retention.py`** (+7) — apply auth/404 + delete-old-keep-recent + **multi-tenant isolation** + audit; preview dry-run (no delete) + 404; real seeded backdated rows ✅
- [x] conftest `TRANSCRIPTRET_%` sweep (CASCADE) ✅

### 2.x Full gate
- [x] mypy 0/374 · run_all 10/10 · backend pytest **2741 passed/5 skip** (+10) · black/isort/flake8 clean · LLM-SDK-leak clean · FE untouched ✅

---

## Day 3 — Drive-through (US-4) — real admin API + real backend + real DB

### 3.1 Clean restart (Risk Class E)
- [x] restarted backend → PID 55768 (new routes loaded; sole port owner) ✅

### 3.2 Drive-through (MANDATORY — real server + real auth + real DB)
- [x] **Leg 1 preview (acme-prod, non-destructive)**: GET preview retention 90 → cutoff 2026-03-19 / 0; PATCH 90→1 → cutoff 2026-06-16; reset → 90 ✅ (route+auth+canonical-read+config-responsive; 0 = no real old transcripts)
- [x] **Leg 2 apply (throwaway tenant, DESTRUCTIVE primary path)**: seeded old(now-60d)+recent(now-5d) retention 30 → preview would_delete **1/1** → POST apply **deleted 1/1** → preview_after 0/0 → DB REMAINING_MESSAGES=1 (recent survived) → cleanup ✅
- [x] Evidence → `artifacts/drivethrough-results.md` + `seed_drivethrough.py`; observed-vs-intended → progress.md Day 3 ✅

---

## Day 4 — CHANGE-101 + design note + closeout

### 4.1 CHANGE-101 + design note (NEW domain)
- [x] **`CHANGE-101-transcript-retention.md`** (gap + pivot + apply/preview + drive-through)
- [x] **design note `39-transcript-retention.md`** (8-point gate): retention contract / deletion + RLS semantics / scheduling + partition deferral / verified-vs-deferred / rollback

### 4.2 Closeout
- [x] retrospective.md Q1-Q7 + calibration (`transcript-retention-apply-spike` 0.60, 1st data point)
- [x] Final gate sweep: mypy · run_all · pytest · black/isort/flake8 · LLM-SDK-leak
- [x] Navigators: CLAUDE.md Current-Sprint + Last-Updated · MEMORY.md pointer + subfile · next-phase-candidates · sprint-workflow matrix (NEW class)
- [x] Anti-pattern self-check (retro Q5): AP-2/3/4/6/8/11 → 0 violations; v2 lints 10/10
- [ ] **Commit** → ⏳ PR push + open → CI → merge: PENDING USER CONFIRMATION → post-merge status flip after gh-verified MERGED

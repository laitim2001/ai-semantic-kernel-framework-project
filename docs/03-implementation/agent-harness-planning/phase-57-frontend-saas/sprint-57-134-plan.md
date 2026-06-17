# Sprint 57.134 Plan — per-tenant transcript retention (config + manual apply endpoint)

**Summary**: First transcript-retention slice (none exists today — transcripts accumulate forever). Adds a per-tenant `TranscriptRetentionPolicy` (`retention_days`) stored in `tenant.meta_data["transcript_retention"]` behind a TTL-cached resolver (mirrors `HarnessPolicy`/`model_policy`), an admin PUT/GET, and a manual admin **"apply retention now"** POST that deletes `messages` + `message_events` rows older than the tenant's `retention_days`. Backend-only — config lives in JSONB and deletion is a DELETE query → **NO migration**. The scheduled background cleanup job (mirror the billing-outbox drainer) is DEFERRED to a follow-on (per the user's Option-A scope pick; the manual apply makes this slice deterministically verifiable). NEW-domain → a **design note IS required** (retention contract + deletion/RLS semantics + scheduling deferral). Drive-through is via the **real admin API + real DB** (verify rows deleted + tenant-isolation) — there is no FE surface this slice (a Tenant Settings tab is a follow-on), so the drive-through is honestly labeled "real-backend (API + DB), not UI-driven".

> **🔴 DAY-1 PIVOT (user-approved AskUserQuestion 2026-06-17: "Pivot + 補一個 GET apply-preview")**: a deeper Day-1 read found `Tenant.retention_days` ALREADY EXISTS (Sprint 57.46 SaaS settings; settable via PATCH `/tenants/{id}`). The §0/§3 below as originally drafted describe a NEW `meta_data["transcript_retention"]` config — that was a PARALLEL config (AP-6) and was **DROPPED**. The shipped design uses the **canonical `tenants.retention_days` column** + only an **apply POST + a dry-run preview GET** (no new config endpoint). This banner preserves the original plan as an audit trail (per AP-2 — what was planned vs shipped); the shipped shape + rationale are in `progress.md` Day 1 + the design note. §3.1-3.2 (TranscriptRetentionPolicy / resolver / cache / meta_data PUT/GET) are SUPERSEDED; §3.2 apply + the RLS handling + the drive-through stand.

**Status**: Approved-to-execute (user 2026-06-17 AskUserQuestion: "A. 每租戶 retention_days config + 手動 apply 端點（推薦）" — the OTHER user-named bucket-C item from "Inspector token-sweep leg、transcript retention(57.125)", now Sprint 57.134; then the Day-1 pivot above).
**Branch**: `feature/sprint-57-134-transcript-retention`
**Base**: `main` HEAD `631f599a` (Sprint 57.133 flip PR #313 merged)
**Slice**: transcript retention (57.125 deferred infra) — Option A (config + manual apply); scheduled job + partition-drop are separate follow-ons.
**Scope decisions**: (a) `TranscriptRetentionPolicy` is a single-field (`retention_days: int | None`) sparse value object in `tenant.meta_data["transcript_retention"]` (mirror `HarnessPolicy`'s round-trip + TTL cache + resolver + invalidate). (b) apply = a DELETE on BOTH `messages` + `message_events` `WHERE tenant_id = :tid AND created_at < (now − retention_days)`, run inside the txn with `SET LOCAL app.tenant_id = :tid` so the cross-tenant admin DELETE satisfies RLS (Day-0 D-rls-delete confirms whether SET is needed or the app role bypasses RLS). (c) scheduled automation + partition-drop + a FE tab are OUT (→ §9). (d) NO migration (JSONB config + DELETE query).

---

## 0. Background

### The gap (transcript retention — 57.125 deferred infra)

`messages` (Sprint 57.127 ledger) and `message_events` (Sprint 57.125 SSE replay) accumulate **forever** — there is zero retention / TTL / cleanup / purge logic anywhere in the backend. pg_partman is installed (migration 0010) but never activated (no `create_parent`), so partitions are neither auto-created nor auto-dropped.

### Why it matters (the missing capability)

Unbounded transcript growth is a storage-cost + compliance (data-minimisation) liability. A tenant needs to express "keep my chat transcripts for N days" and have old rows actually deleted. This slice delivers the per-tenant policy + a deterministic manual enforcement; a scheduled job is the natural follow-on.

### Root cause (recon code read, file:line; ALL re-verified §checklist 0.1)

| Layer | Reality (on `main` HEAD `631f599a`) | Anchor |
|-------|--------------------------------------|--------|
| transcript tables | `messages` + `message_events` both `PARTITIONED BY RANGE (created_at)`, tenant-scoped (`TenantScopedMixin`), have `created_at` NOT NULL | `infrastructure/db/models/sessions.py:163-217` (Message) + `:223-267` (MessageEvent) |
| RLS | both tables have `tenant_isolation_*` RLS policies (`app.tenant_id`) | `migrations/versions/0009_rls_policies.py:80-100` |
| retention today | NONE — no retention/expiry/cleanup/purge/DROP-PARTITION anywhere | grep (Day-0 D-no-retention) |
| per-tenant config pattern | `HarnessPolicy` = sparse JSONB in `tenant.meta_data` + `from_dict`/`to_dict` + TTL cache + `resolve_*` + `invalidate_*` + `reset_*` | `platform_layer/governance/harness_policy.py:102-247` |
| admin endpoint pattern | PUT/GET `/{tenant_id}/harness-policy`: `_validate` → `_load_tenant_or_404` → candidate→sparse → `new_meta` → flush → `append_audit` → commit → refresh → `invalidate` → `_project` | `api/v1/admin/tenants.py:1782-1862` (Pydantic schemas defined in-file) |
| job infra (deferred) | billing-outbox drainer = proven async poll loop (the follow-on's mirror) | `api/main.py:267-336` + `platform_layer/billing/billing_outbox.py` |

→ Mirror `HarnessPolicy` (single int field) for the config; mirror the harness-policy admin PUT/GET for the endpoints; add a POST `…/apply` that DELETEs by age on both tables under the target tenant's RLS context. No migration.

### The design (backend: 1 new module + admin PUT/GET/apply + tests + design note)

```
platform_layer/transcripts/retention_policy.py   (mirror harness_policy.py, single field)
  @dataclass(frozen=True) TranscriptRetentionPolicy: retention_days: int | None = None
    from_dict / to_dict / is_empty
  _TranscriptRetentionPolicyCache (TTL, injectable clock)  +  module _cache
  resolve_tenant_transcript_retention_policy(db, tenant_id) -> policy   (fail-open empty)
  invalidate_tenant_transcript_retention_policy(tenant_id)
  reset_transcript_retention_policy_cache()                 (Risk Class C test hook)
  apply_transcript_retention(db, tenant_id, retention_days, *, now) -> RetentionDeleteStats
    cutoff = now - timedelta(days=retention_days)
    SET LOCAL app.tenant_id = :tid   (RLS — D-rls-delete)
    DELETE messages       WHERE tenant_id=:tid AND created_at < :cutoff   -> rowcount
    DELETE message_events WHERE tenant_id=:tid AND created_at < :cutoff   -> rowcount

api/v1/admin/tenants.py  (mirror harness-policy block)
  TranscriptRetentionUpsertRequest { retention_days: int | None (ge=1) }  extra="forbid"
  TranscriptRetentionResponse { retention_days: int | None }
  TranscriptRetentionApplyResponse { retention_days, cutoff, deleted_messages, deleted_events }
  PUT  /{tenant_id}/transcript-retention   (upsert meta_data["transcript_retention"] + audit + invalidate)
  GET  /{tenant_id}/transcript-retention   (read-only)
  POST /{tenant_id}/transcript-retention/apply  (resolve policy → apply_transcript_retention → audit → 200)
```

WHY manual-apply now, scheduled-later: the deletion + per-tenant policy + RLS semantics are the risky core and are fully drive-through-able via a manual endpoint (deterministic — no clock simulation). The scheduled poll loop is mechanical once the deletion is proven; deferring it keeps this slice thin AND honours the project's drive-through constraint (a scheduled job is hard to drive-through).

### Ground truth (recon head-start — code read on `main` HEAD `631f599a`; ALL re-verified §checklist 0.1)

- `platform_layer/governance/harness_policy.py:102-247` — the exact dataclass + cache + resolver + invalidate + reset shape to mirror (single int field is simpler).
- `api/v1/admin/tenants.py:1782-1862` — the admin PUT/GET body (candidate→sparse→new_meta→flush→`append_audit`→commit→refresh→invalidate→`_project`); `append_audit` + `_load_tenant_or_404` + `require_admin_platform_role` helpers; Pydantic schemas defined in-file.
- `infrastructure/db/models/sessions.py:163-267` — `Message` + `MessageEvent` columns (`tenant_id`, `created_at`); composite PK includes `created_at` (partition key).
- `migrations/versions/0009_rls_policies.py:80-100` — `tenant_isolation_messages` / `_message_events` RLS (drives D-rls-delete + the `SET LOCAL app.tenant_id` design).

**Baselines (57.133 closeout)**: backend pytest 2731 (+5 skip) · mypy 0/372 · run_all 10/10 · wire 25 · (Vitest 915 / mockup 51 — FE untouched this sprint). Re-verify Day-0.

### STALE / drift findings (Day-0; full detail → progress.md — placeholder, filled in §checklist 0.1)

- **D-no-retention** — grep confirms zero existing retention/purge/cleanup before adding (no name collision; new domain).
- **D-rls-delete** — verify whether the app DB role is FORCE'd under RLS / bypasses it: read `0009_rls_policies.py` for `FORCE ROW LEVEL SECURITY` + how the app connects; confirm the apply DELETE needs `SET LOCAL app.tenant_id` (design assumes yes = safe either way).
- **D-meta-data-key** — confirm `transcript_retention` is a free key in `tenant.meta_data` (no existing key collision with model_policy/harness_policy/quota_overrides/rate_limits).
- **D-default-partition** — confirm whether a `*_default` partition exists for `messages`/`message_events` (Explore saw only the 3 static 2026-04/05/06 partitions in 0002; the apply DELETE works on the parent regardless, but note the post-2026-06 write reality for the design note).
- **D-append-audit-sig** — confirm `append_audit` signature + `_load_tenant_or_404` + `require_admin_platform_role` import paths.

## 1. Sprint Goal

Deliver per-tenant transcript retention: a `retention_days` policy (JSONB + TTL-cached resolver) with admin PUT/GET, and a manual apply endpoint that deletes `messages` + `message_events` older than the tenant's retention window — proving real deletion + tenant-isolation end-to-end. Proven by backend pytest (resolver + apply + admin endpoints incl. multi-tenant isolation) + mypy/run_all clean + a MANDATORY drive-through via the real admin API + real DB (set `retention_days`, POST apply, verify that tenant's old rows deleted while another tenant's survive). CHANGE-101 + a design note (new domain). NO migration.

## 2. User Stories

- **US-1** (config): 作為平台 admin，我希望為某租戶設定 `retention_days`，以便表達該租戶的 transcript 保留窗口。
- **US-2** (resolver): 作為後端，我希望以 TTL cache 解析租戶的保留政策（fail-open），以便 apply 與未來排程都能讀到一致政策。
- **US-3** (apply): 作為平台 admin，我希望手動觸發「立即套用保留」，以便刪除該租戶超過保留窗口的 `messages` + `message_events`（嚴格 tenant-scoped）。
- **US-4** (drive-through MANDATORY): 作為驗收者，我希望透過真 admin API + 真 DB 設定+套用+核驗刪除與跨租戶隔離，以便確認真的刪到且不誤刪他租戶。
- **US-5** (closeout): CHANGE-101 + design note + retrospective + navigators。

## 3. Technical Specifications

### 3.0 Architecture (backend-only; NO migration / no LLM / no FE / no wire)

```
NEW   backend/src/platform_layer/transcripts/__init__.py
NEW   backend/src/platform_layer/transcripts/retention_policy.py   (policy + cache + resolver + apply)
EDIT  backend/src/api/v1/admin/tenants.py                          (3 Pydantic + _validate + _project + PUT/GET/apply)
NEW   backend/tests/unit/platform_layer/transcripts/test_retention_policy.py
NEW   backend/tests/integration/admin/test_transcript_retention.py (or extend existing admin test)
NEW   docs/.../<NN>-transcript-retention.md                        (spike design note)
UNTOUCHED  migrations/** · agent_harness/** · frontend/** · wire schema
```

### 3.1 Policy + resolver (US-1/US-2) — `platform_layer/transcripts/retention_policy.py`

- `TranscriptRetentionPolicy(retention_days: int | None = None)` frozen; `from_dict` (coerce a positive int, else None) / `to_dict` (drop None) / `is_empty`.
- `_TranscriptRetentionPolicyCache` + module `_cache` + `resolve_tenant_transcript_retention_policy(db, tenant_id)` (fail-open empty; reads `tenant.meta_data["transcript_retention"]`) + `invalidate_*` + `reset_*` — byte-pattern mirror of `harness_policy.py` (Risk Class C reset hook).

### 3.2 Apply (US-3) — same module

- `apply_transcript_retention(db, tenant_id, retention_days, *, now) -> RetentionDeleteStats(deleted_messages, deleted_events, cutoff)`: compute `cutoff = now - timedelta(days=retention_days)`; `SET LOCAL app.tenant_id = :tid` (RLS); two `DELETE … WHERE tenant_id=:tid AND created_at < :cutoff` (messages + message_events); return rowcounts. `now` injectable for deterministic tests. No-op (0/0) when `retention_days` is None.

### 3.3 Admin endpoints (US-1/US-3) — `api/v1/admin/tenants.py`

- Mirror the harness-policy block: `TranscriptRetentionUpsertRequest` (`retention_days: int | None`, `Field(ge=1)`, `extra="forbid"`) + `TranscriptRetentionResponse` + `TranscriptRetentionApplyResponse`; `_validate_transcript_retention` + `_project_transcript_retention`; PUT (upsert meta_data + `append_audit("tenant_transcript_retention_upsert")` + `invalidate`), GET (read-only), POST `…/apply` (resolve → `apply_transcript_retention` → `append_audit("tenant_transcript_retention_apply", {deleted_messages, deleted_events, cutoff})` → 200). All `require_admin_platform_role` + `_load_tenant_or_404` (cross-tenant → 404).

### 3.x What is explicitly NOT done

- No scheduled background cleanup job (the billing-drainer mirror) — follow-on; this slice is manual-apply only.
- No partition-drop / pg_partman activation (Option D, separate Ops slice).
- No FE Tenant Settings tab — the surface this slice is the admin API; a UI tab is a follow-on.
- No GDPR per-user erasure (separate; no existing code).

### 3.y Validation (US-1..US-5)

Gates: backend pytest 2731 + new · mypy `src` 0/372 · run_all 10/10 · black/isort/flake8 clean · LLM-SDK-leak clean. FE untouched (Vitest 915 / mockup 51 unchanged, not re-run). Plus the §3 drive-through (MANDATORY — real admin API + real DB).

## 4. File Change List

| # | File | Action |
|---|------|--------|
| 1 | `backend/src/platform_layer/transcripts/__init__.py` | NEW |
| 2 | `backend/src/platform_layer/transcripts/retention_policy.py` | NEW (policy + cache + resolver + apply) |
| 3 | `backend/src/api/v1/admin/tenants.py` | EDIT (3 Pydantic + _validate + _project + PUT/GET/apply) |
| 4 | `backend/tests/unit/platform_layer/transcripts/test_retention_policy.py` | NEW |
| 5 | `backend/tests/integration/admin/test_transcript_retention.py` | NEW |
| 6 | `docs/03-implementation/agent-harness-planning/<NN>-transcript-retention.md` | NEW (design note) |
| 7 | `claudedocs/4-changes/feature-changes/CHANGE-101-*.md` | NEW |
| — | `migrations/**` · `agent_harness/**` · `frontend/**` | **UNTOUCHED** |

## 5. Acceptance Criteria

1. `TranscriptRetentionPolicy` round-trips via `from_dict`/`to_dict`; resolver is TTL-cached + fail-open; unit-tested.
2. `apply_transcript_retention` deletes only rows `< cutoff` for the given tenant; a different tenant's rows + within-window rows survive; no-policy = no-op; unit-tested with an injected `now`.
3. Admin PUT/GET/apply: PUT stores `retention_days` + invalidates; GET reads it back; POST apply returns `{deleted_messages, deleted_events, cutoff}`; 422 on `retention_days < 1` / unknown field; cross-tenant → 404; multi-tenant isolation test (tenant A apply does not touch tenant B).
4. **Drive-through PASS (MANDATORY, real admin API + real backend + real DB)** — PUT `retention_days=N` for a tenant, POST apply, verify in DB that that tenant's `messages`/`message_events` with `created_at < cutoff` are gone while recent + another tenant's rows remain; counts match the response. (Honestly labeled real-backend API+DB — NO FE surface this slice.) Evidence in progress.md.
5. CHANGE-101 + design note (8-point gate); calibration recorded; navigators + next-phase-candidates updated. NO migration.

## 6. Deliverables

- [ ] US-1/US-2 policy + TTL resolver (mirror HarnessPolicy)
- [ ] US-3 apply (DELETE by age, RLS-safe, tenant-scoped)
- [ ] US-1/US-3 admin PUT/GET/apply endpoints
- [ ] US-4 drive-through PASS (real admin API + DB, multi-tenant isolation)
- [ ] US-5 CHANGE-101 + design note + closeout

## 7. Workload Calibration

- Scope class **`transcript-retention-config-and-apply-spike` 0.60** (NEW class, 1st data point). New-domain backend spike: the config half byte-mirrors `config-tiering-model-policy-spike` 0.60; the apply half adds a bounded DELETE-by-age on partitioned RLS tables with tenant-isolation. Pending 2-3 sprint validation.
- **Agent-delegated: no** (parent-direct; multi-tenant deletion semantics + RLS warrant careful parent execution). `agent_factor` 1.0 → 3-segment form.
- Bottom-up est ~8.3 hr (policy ~1.0, apply ~1.0, admin+schemas ~1.5, tests ~2.0, design note ~0.8, drive-through ~1.5, closeout ~0.5) → class-calibrated commit ~5.0 hr (mult 0.60). Day-4 retro Q2 verifies.

## 8. Dependencies & Risks

| Risk | Mitigation |
|------|------------|
| RLS blocks the cross-tenant admin DELETE (admin's JWT tenant ≠ target) | `SET LOCAL app.tenant_id = :tid` inside the apply txn before DELETE (safe whether RLS is FORCE'd or the app role bypasses it); D-rls-delete confirms the reality + the integration test asserts real deletion |
| Module-level `_cache` singleton across test event loops (Risk Class C) | `reset_transcript_retention_policy_cache()` hook + autouse reset in the suite (mirror harness_policy testing pattern) |
| Mass DELETE on partitioned tables is slow / locks | bounded per-tenant + `created_at` index; manual-apply (not a hot path); batching is a follow-on concern noted in the design note |
| `meta_data` key collision | D-meta-data-key grep confirms `transcript_retention` is free |
| Cross-platform mypy `unused-ignore` | per `code-quality.md` dual-ignore pattern if it surfaces (Risk Class B) |

## 9. Out of Scope (this sprint; → separate slices / ADs)

- Scheduled background cleanup job (mirror billing-outbox drainer) — the natural follow-on once deletion is proven.
- Partition-drop automation / pg_partman activation (Option D) — separate Ops slice.
- A FE Tenant Settings "Retention" tab — follow-on (this slice's surface is the admin API).
- GDPR per-user erasure; `messages`/`message_events` ledger consolidation; `turn_num` cross-send counter — pre-existing deferred infra.

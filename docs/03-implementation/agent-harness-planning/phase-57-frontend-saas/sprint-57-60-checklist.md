# Sprint 57.60 — Checklist

Plan: [`sprint-57-60-plan.md`](./sprint-57-60-plan.md)

**Class**: `medium-backend` 0.80 (single-domain backend cleanup; surgical fallback removal + 1 data-cleanup migration)
**Agent-delegated**: yes (single code-implementer agent — small surgical sprint)
**Agent-factor**: `mechanical-pattern-reuse-heavy` 0.30 (5 near-identical fallback removals; Day 0 may refine to 0.45 `port-style`)
**Template**: mirrors `sprint-57-59-checklist.md` Day 0-2 structure

---

## Day 0 — Plan + 三-Prong Verify

### 0.1 Plan + Checklist Drafting
- [x] **Draft `sprint-57-60-plan.md` v1** (9-section; scope cleanup of 57.59 transitional meta_data layer)
- [x] **Draft `sprint-57-60-checklist.md` v1** (this file)
- [x] **User approve plan v1** — gate before Day 0 三-Prong ✅ (approved 2026-05-29)

### 0.8 Day 0 三-Prong Verify (Step 2.5 mandatory — Content Prong CRITICAL: fallback-removal safety invariant)

#### Prong 1 — Path Verify
- [x] **D-DAY0-A**: `0020_clear_rate_limits_meta_data.py` NOT exist yet (NEW)
  - Verify: `ls backend/src/infrastructure/db/migrations/versions/ | grep 0020` → empty
- [x] **D-DAY0-B**: 3 edit-target source files present (`api/v1/admin/tenants.py`, `platform_layer/middleware/rate_limit.py`, `platform_layer/tenant/tool_rate_limit_gate.py`)
- [x] **D-DAY0-C**: `platform_layer/tenant/rate_limit_config_store.py` present (`_project_config_to_item` = reference for `0020` downgrade inline projection)
- [x] **D-DAY0-D**: 57.59 test files present (`test_admin_tenant_rate_limits_table.py`, `test_rate_limit_usage_persistence.py`)

#### Prong 2 — Content Verify
- [x] **D-DAY0-E** (🔴 CRITICAL — fallback-removal safety invariant §2.6 R1): `0019` `upgrade()` data-migration reads ALL tenants with `meta_data ? 'rate_limits'` unconditionally (no skip / no flag-gate) → confirm every existing config row was migrated to `rate_limit_configs` before removing the fallback
  - Verify: read `0019_rate_limit_configs.py` `upgrade()` data-migration loop
- [x] **D-DAY0-F**: exact fallback block shape + line numbers at 4 read sites (#1 GET L1390-91 / #2 usage GET L1602 / #3 middleware L188-193 / #4 gate L136-141) + dual-write block (#5 PUT L1492-97); confirm removal boundaries
- [x] **D-DAY0-G**: enumerate ALL tests seeding `meta_data["rate_limits"]` (so none break silently)
  - Verify: `grep -rn "meta_data.*rate_limits\|rate_limits.*meta_data" backend/tests/`
- [x] **D-DAY0-H**: `_inline_parse` in `0019` (label→resource_type + "N / unit"→quota,window_type) → derive inverse `_inline_project` (resource_type,window_type,quota → {label, value "N / unit"}) for `0020` downgrade
- [x] **D-DAY0-I**: `DEFAULT_RATE_LIMITS` shape (`tenants.py:1354`) + confirm GET display paths fall to DEFAULT while enforcement paths (middleware/gate) fall to `[]` (asymmetry preserved)
- [x] **D-DAY0-J**: orphan check (Karpathy §3) — after fallback removal, is the `tenant`/`meta_data` ORM fetch still referenced at each of the 4 read sites + PUT? (drop only orphans THIS sprint creates)

#### Prong 3 — Schema Verify (data-only migration — no new table, no RLS change)
- [x] **D-DAY0-K**: Alembic head — `ls backend/src/infrastructure/db/migrations/versions/ | sort -V | tail -3` → confirm head = `0019` → next = `0020`
- [x] **D-DAY0-L**: `rate_limit_configs` columns (`tenant_id, resource_type, window_type, quota`) for the `0020` downgrade reverse-projection SELECT
- [x] **D-DAY0-M**: JSONB ops availability — `meta_data - 'rate_limits'` (minus-key) for upgrade + `jsonb_set` for downgrade; confirm pattern precedent (Sprint 57.56 quota_overrides `dict()` ORM path or raw SQL elsewhere)
- [x] **D-DAY0-N**: no RLS policy change (data-only migration, 0 new table) → `check_rls_policies` 20 tables unchanged

#### Day 0 Drift Catalog + go/no-go
- [x] **Catalog findings** in `progress.md` Day 0 entry — 14 checks (11 GREEN + 3 NOTABLE/DRIFT + 0 CRITICAL-blocker)
- [x] **Decide go/no-go** — ≤20% shift → **GO for Day 1** (3 plan micro-amendments: §4.3 physical-column `"metadata"` + §5 +1 test file `test_admin_tenant_rate_limits.py` + §8 R2 drift note)

### 0.9 Branch + Day 0 commit
- [x] **Create feature branch** `feature/sprint-57-60-rate-limits-metadata-cleanup` (from main `4ad51828`)
- [ ] **Day 0 commit** (plan + checklist + progress.md Day 0 entry)

---

## Day 1 — Implementation (Agent-Delegated: yes — single agent)

### 1.1 US-1 — Remove meta_data read-fallback (4 sites) + PUT dual-write (1 site)
- [ ] **EDIT** `api/v1/admin/tenants.py` — remove GET fallback (#1 L1390-91) → config → DEFAULT
- [ ] **EDIT** `api/v1/admin/tenants.py` — remove usage GET fallback (#2 L1602) → config → DEFAULT
- [ ] **EDIT** `api/v1/admin/tenants.py` — remove PUT dual-write (#5 L1492-97) → config write only; audit unchanged
- [ ] **EDIT** `platform_layer/middleware/rate_limit.py` — `_load_rate_limits` remove fallback (#3 L188-193) → config → `[]`; drop orphaned tenant fetch if unused
- [ ] **EDIT** `platform_layer/tenant/tool_rate_limit_gate.py` — `_load_tool_limits` remove fallback (#4 L136-141) → config → `[]`; drop orphan if unused
- [ ] **EDIT** file-header MHist (3 source files) + remove/update inline "AD-RateLimits-MetaData-Cleanup-Phase58" comments (AD now closed)
- [ ] **CONVERT** `test_admin_tenant_rate_limits_table.py` — fallback-path assertions → config-only steady-state (no delete)
- [ ] **CONVERT** `test_rate_limit_usage_persistence.py` — fallback-path assertions → config-only (no delete)
- [ ] **NEW** ~2-4 pytest: seed meta_data + empty config → GET returns DEFAULT (not meta_data) + PUT does not write meta_data
- [ ] **Verify**: pytest US-1 green + API shapes unchanged

### 1.2 US-2 — Alembic `0020` clear stored JSONB + reverse-populate downgrade
- [ ] **NEW** `0020_clear_rate_limits_meta_data.py` — upgrade strips `meta_data - 'rate_limits'` (idempotent) + downgrade inline-projects `rate_limit_configs` → `meta_data["rate_limits"]`
- [ ] **NEW** `test_clear_rate_limits_meta_data_migration.py` (~3-4 tests): upgrade clears key + idempotent on un-seeded + downgrade reverse-populates + multi-tenant isolation
- [ ] **Verify**: migration `up → down → up` clean (head `0020`) + `check_rls_policies` 20 tables unchanged

### 1.3 Day 1 Validation Sweep — ALL GREEN
- [ ] **pytest full**: 1840 → ~1842+ (NO regressions)
- [ ] **mypy --strict**: 0 errors
- [ ] **9/9 V2 lints** (incl. `check_rls_policies` 20 tables + `check_llm_sdk_leak`)
- [ ] **Vitest 675 unchanged** (0 frontend files touched — API shapes preserved)
- [ ] **HEX_OKLCH baseline 48** + DUAL CLEAN 22/22 PARITY 16 consec
- [ ] **LLM SDK leak 0** + Vite build clean

### 1.4 Day 1 commit
- [ ] **Commit all Day 1 work**

---

## Day 2 — Closeout (parent assistant)

### 2.1 Final Validation Sweep
- [ ] **Re-run Day 1.3 checks** sanity
- [ ] **mockup-fidelity DUAL CLEAN 22/22 PARITY 16 consecutive 57.45-57.60** (0 frontend touched)

### 2.2 Retrospective (Q1-Q6; Q7 N/A SKIP — refactor/cleanup NOT spike)
- [ ] **NEW** `retrospective.md` (Q1-Q6 + calibration `mechanical-pattern-reuse-heavy` 0.30 1st forward application + AD closure)

### 2.3 sprint-workflow.md updates
- [ ] MHist 1-line + `medium-backend` 0.80 11th data point + `mechanical-pattern-reuse-heavy` 0.30 forward-application data point

### 2.4 PROMOTIONS (Prong codify — if Day 0 confirms 2 data points each)
- [ ] Codify `AD-Day0-Prong3-Physical-Column-Read` + `AD-Day0-Prong2-Nested-Shape-Read` into `sprint-workflow.md §Step 2.5` Drift Class table (both 2 data points 57.58+57.59) — OR carry to 57.61 if scope tight

### 2.5 Memory + index
- [ ] **NEW** `memory/project_phase57_60_rate_limits_metadata_cleanup.md` (user-home)
- [ ] **EDIT** `memory/MEMORY.md` — quality pointer

### 2.6 CLAUDE.md (navigator-only)
- [ ] Current Sprint row + Last Updated footer

### 2.7 next-phase-candidates.md
- [ ] Sprint 57.60 Carryover section: MetaData-Cleanup CLOSED + carryovers (SyntaxValidation / Alerting / Tier-3 0.45 deferred to 57.61)

### 2.8 REFACTOR-004 record
- [ ] **NEW** `REFACTOR-004-sprint-57-60-rate-limits-metadata-cleanup.md`

### 2.9 PR + merge (user action)
- [ ] Push branch + open PR (title: `refactor(rate-limits, sprint-57-60): retire transitional meta_data fallback + dual-write — close AD-RateLimits-MetaData-Cleanup-Phase58`)
- [ ] Wait CI (5 required green) → user merge → branch cleanup

### 2.10 Final closeout
- [ ] Day 2 commit (all docs)
- [ ] Verify working tree clean on main after merge
- [ ] Mark Sprint 57.60 CLOSED in next-phase-candidates.md

---

## Open items / 🚧 Deferred (updated end of Day 0 三-Prong)

(Only `[ ]` → `[x]` allowed; never delete unchecked. 🚧 markers acceptable with reason.)

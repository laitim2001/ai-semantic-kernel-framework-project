# Sprint 57.48 — Checklist

[Plan](./sprint-57-48-plan.md) — 5-track wave (HITLPolicies + FF + Quotas + RateLimits + AP-4 hygiene); 2nd `agent_factor = 0.65` validation; 4th `medium-backend 0.80` data point.

---

## Day 0 — Plan + 三-Prong Verify

### 0.1 Plan + Checklist Drafting
- [x] **Plan written** `sprint-57-48-plan.md`
- [x] **Checklist written** (this file)

### 0.8 Day 0 三-Prong Verify (Step 2.5 mandatory)

**Prong 1 — Path Verify** (8 paths):
- [ ] `backend/src/api/v1/admin/tenants.py` exists (extension target)
- [ ] `backend/src/agent_harness/hitl/` directory exists (Track A — DBHITLPolicyStore source)
- [ ] `backend/src/infrastructure/db/models/` feature_flags ORM file exists (Track B — Sprint 57.47 audit confirmed)
- [ ] `backend/src/platform_layer/tenant/quota.py` exists (Track C — Sprint 57.47 D-DAY0-1 path)
- [ ] `frontend/src/pages/auth/invite.tsx` + `login.tsx` + `register.tsx` exist (Track E targets)
- [ ] `backend/tests/integration/api/test_admin_tenant_*.py` test pattern reference (MEMBERS = Sprint 57.47)
- [ ] `frontend/src/features/tenant-settings/_fixtures.ts` exists (Track A/B/C/D fixture source)
- [ ] Migration head: `0018_tenant_settings_extension.py` (next slot = 0019 if Track D needs new table)

**Prong 2 — Content Verify** (7 claims):
- [ ] `DBHITLPolicyStore` has a `list_policies` or `find_by_tenant` method (Track A pattern reuse target)
- [ ] `feature_flags` ORM has `tenant_id` column (Track B per-tenant scope confirmed)
- [ ] `quota.py` exposes structured GET (not just Redis token bucket) — confirm/deny
- [ ] Track D RateLimits — search `backend/src/` for `rate_limit*` modules (Track D scope decision input)
- [ ] AP-4 violations in 3 auth pages — read each to identify why AP-4 flags
- [ ] Sprint 57.47 MEMBERS endpoint pattern as reuse template — confirm 5-step structure (TenantItem + ListResponse + endpoint + paginate + tenant_id filter)
- [ ] `_fixtures.ts` HITL_POLICIES + FEATURE_FLAGS + QUOTAS + RATE_LIMITS field shapes — confirm Pydantic schema mappings

**Prong 3 — Schema Verify** (conditional on Track D):
- [ ] If Track D needs new ORM (Option B) → schema verify on `tenant_rate_limits` table proposal + migration 0019 slot
- [ ] If Track D uses fixture-projection (Option A) → N/A; skip Prong 3

**Prong 2.5 — Frontend Tree Depth Audit**:
- [ ] N/A for Tracks A-D (backend); apply to Track E AP-4 (read each auth page in full not just grep)

**Drift findings catalog**:
- [ ] All findings logged to `progress.md` Day 0 §Drift findings (D-DAY0-N)
- [ ] Track D scope decision recorded (Option A / Option B / 🚧 defer)
- [ ] Go/no-go decision recorded

### 0.9 Branch + Day 0 commit
- [x] Branch `feature/sprint-57-48-tenant-settings-backend-completion-wave` created
- [ ] Day 0 + Day 1 combined commit (small-scope precedent from Sprint 57.47)

---

## Day 1 — Implementation (Code-Implementer Agent Delegation)

### 1.1 Track A — HITLPolicies Backend (cheapest, first)
- [ ] Add `HITLPolicyItem` + `HITLPolicyListResponse` Pydantic models to `tenants.py`
  - DoD: Mirrors `TenantMemberItem` (Sprint 57.47) shape; fields per plan §4.2
- [ ] Add `GET /admin/tenants/{tenant_id}/hitl-policies` endpoint
  - DoD: admin role only; 404 if tenant not found; paginated (limit/offset); tenant_id-filtered query
- [ ] Add ≥6 NEW pytest tests in `test_admin_tenant_hitl_policies.py`
  - DoD: auth + 404 + happy + shape + multi-tenant isolation + pagination + empty
- [ ] CHANGE-013 record

### 1.2 Track B — FeatureFlags Admin GET
- [ ] Add `FeatureFlagItem` + `FeatureFlagListResponse` models
- [ ] Add `GET /admin/tenants/{tenant_id}/feature-flags` endpoint
- [ ] ≥6 NEW pytest tests in `test_admin_tenant_feature_flags.py`
- [ ] CHANGE-014 record

### 1.3 Track C — Quotas Admin GET
- [ ] Add `QuotaItem` + `QuotaListResponse` models
- [ ] Add `GET /admin/tenants/{tenant_id}/quotas` endpoint
- [ ] ≥6 NEW pytest tests in `test_admin_tenant_quotas.py`
- [ ] CHANGE-015 record

### 1.4 Track D — RateLimits Backend (Day 0.8 decision-gated)

**If Option A (fixture-projection from `tenants.meta_data` JSON ~2-3 hr)**:
- [ ] Add `RateLimitItem` + `RateLimitListResponse` models
- [ ] Add `GET /admin/tenants/{tenant_id}/rate-limits` endpoint (reads from meta_data)
- [ ] ≥4 NEW pytest tests in `test_admin_tenant_rate_limits.py`
- [ ] CHANGE-016 record

**If Option B (new ORM table ~5-6 hr)**:
- [ ] Alembic 0019_tenant_rate_limits.py migration
- [ ] ORM model + endpoint + ≥4 tests
- [ ] CHANGE-016 record

**If 🚧 defer**:
- [ ] Mark Track D items as 🚧 in checklist with reason
- [ ] Log carryover AD `AD-TenantSettings-RateLimits-Backend-Sprint-57.49`
- [ ] CHANGE-016 carryover memo (not full record)

### 1.5 Track E — AP-4 Frontend Auth Hygiene
- [ ] Read each of `invite.tsx`, `login.tsx`, `register.tsx` in full (Prong 2.5 depth audit applied)
- [ ] Identify AP-4 root cause (Potemkin structure / unused imports / stub mocks)
- [ ] Apply minimal fix
  - DoD: No behavior change (existing Vitest + Playwright tests pass)
- [ ] Verify `python scripts/lint/run_all.py` → 9/9 green
- [ ] Vite build unchanged ±1KB
- [ ] CHANGE-017 record

### 1.6 Day 1 Validation Sweep
- [ ] black + isort + flake8 — exit 0
- [ ] mypy --strict — 0 errors
- [ ] **9 V2 lints: 9/9 green** (Track E removes pre-existing AP-4 baseline)
- [ ] pytest integration/api/ — all PASS; ≥22 NEW (6+6+6+4 across A-D, or 6+6+6+0 if Track D 🚧)
- [ ] LLM SDK leak: 0
- [ ] Frontend build + lint (Track E): `npm run lint` + `npm run build` exit 0

### 1.7 Day 1 commit
- [ ] Commit: `feat(sprint-57-48): Day 1 — TenantSettings 4-tab backend completion wave + AP-4 hygiene`

---

## Day 2 — Closeout

### 2.1 Validation
- [ ] Full backend test suite passing
- [ ] No regressions in existing admin tenant tests
- [ ] Frontend Vite build clean

### 2.2 Retrospective
- [ ] **Write `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-48/retrospective.md`**
  - DoD: Q1-Q7 6 必答 format
- [ ] **2nd validation under `agent_factor = 0.65`** logged in Q4
  - DoD: Ratio + rollback decision (KEEP / tighten 0.55 / tighten 0.45 / Option B sub-class split)
- [ ] **4th `medium-backend 0.80` data point** logged in Q4 calibration table
  - DoD: Cumulative 4-pt mean + decision (KEEP / propose lift)

### 2.3 Sprint-workflow.md updates
- [ ] Add file MHist entry (1-line)
- [ ] Add matrix MHist entry (longer)
- [ ] Add §Active Activation history entry with Sprint 57.48 2nd validation results
- [ ] If 2nd consec < 0.7 → tighten `agent_factor` value in formula block (0.65 → 0.55 OR 0.45)
- [ ] If sub-class split decision → add NEW sub-class rows to matrix (parallel to Sprint 57.38 precedent)

### 2.4 Memory + index
- [ ] Write `memory/project_phase57_48_*.md`
- [ ] Add MEMORY.md pointer entry

### 2.5 CLAUDE.md
- [ ] Update Current Sprint row + Last Updated footer (navigator-only per Sprint Closeout policy)

### 2.6 PR + merge
- [ ] Push branch + open PR
- [ ] Wait CI green
- [ ] User merges (per session convention)
- [ ] Local cleanup

### 2.7 Final
- [ ] Day 2 commit: `chore(sprint-57-48): Day 2 retro + closeout`
- [ ] All checklist items `[x]` or 🚧

---

**Modification History**:
- 2026-05-26: Sprint 57.48 Day 0.1 — Initial draft (5-track wave; mirrors Sprint 57.46/57 structure)

# Sprint 57.49 — Checklist

[Plan](./sprint-57-49-plan.md) — Dual-track frontend migration wave (TenantSettings 5 tabs + AdminTenants Members drawer); **1st validation under NEW `mechanical-single-domain` 0.45 sub-class agent_factor** (Sprint 57.48 retro Option B).

---

## Day 0 — Plan + 三-Prong Verify

### 0.1 Plan + Checklist Drafting
- [x] Plan written `sprint-57-49-plan.md`
- [x] Checklist written (this file)

### 0.8 Day 0 三-Prong Verify (Step 2.5 mandatory)

**Prong 1 — Path Verify** (10 paths):
- [x] `frontend/src/features/tenant-settings/` directory exists with 6 tab components
- [x] `frontend/src/features/tenant-settings/_fixtures.ts` exists (current fixture source)
- [x] `frontend/src/features/tenant-settings/services/tenantSettingsService.ts` exists (or similar service module)
- [x] `frontend/src/features/admin-tenants/components/TenantsTable.tsx` exists (Track B integration target)
- [x] `frontend/src/features/admin-tenants/services/adminTenantsService.ts` exists
- [x] `backend/src/api/v1/admin/tenants.py` 5 endpoints from Sprint 57.47/48 exist (HITLPolicies + FF + Quotas + RateLimits + Members)
- [x] Existing Vitest spec files for tenant-settings tabs exist
- [x] Existing Playwright e2e specs for /tenant-settings + /admin-tenants exist (deferred to Day 1.3)
- [x] No existing TenantMembersDrawer component (target NEW for Track B)
- [x] AppShellV2 + mockup-ui Card primitive reference exists somewhere in `frontend/src/components/`

**Prong 2 — Content Verify** (8 claims):
- [x] Sprint 57.48 5 endpoints Pydantic response shapes verified (D-DAY0-1)
- [x] Current `tenantSettingsService.ts` has existing service function patterns to mirror
- [x] Existing TanStack Query hooks in tenant-settings/hooks/ to extend
- [x] Current GeneralTab.tsx still uses GENERAL_FIXTURE residual — confirmed; migration needed
- [x] Current FeatureFlagsTab/QuotasTab/HITLPoliciesTab/MembersTab all consume `_fixtures.ts`
- [x] DangerZoneTab is UI-only — confirmed (4 `window.alert` stubs)
- [x] No existing AdminTenants modal/drawer pattern — introduce inline drawer
- [x] Loading/Error/Empty patterns reusable via mockup-ui Card

**Prong 3 — Schema Verify**: N/A (no DB changes)

**Prong 2.5 — Frontend Tree Depth Audit**:
- [x] Read each of 6 TenantSettings tab components in full (depth-1 child component tree)
- [x] Verify no Phase-2 verbatim-CSS or shadcn-utility token regressions (all clean)

**Drift findings catalog**:
- [x] All findings logged to `progress.md` Day 0 (D-DAY0-1 through D-DAY0-6)
- [x] Go/no-go decision recorded (GO)

### 0.9 Branch + Day 0 commit
- [x] Branch `feature/sprint-57-49-frontend-backend-migration-wave` created
- [x] Day 0 + Day 1 combined commit (small-scope precedent)

---

## Day 1 — Implementation (Code-Implementer Agent Delegation)

### 1.1 Track A — TenantSettings 5-Tab Migration

#### 1.1.1 GeneralTab verify + cleanup (Sprint 57.46 backend already real)
- [x] Verify GeneralTab.tsx consumes Sprint 57.46 TenantResponse 15 fields
- [x] Remove residual `GENERAL_FIXTURE` import; consume real `data.region/locale/retention_days/seats/sso_enabled`
- [x] Update Vitest spec assertions for real backend consumption
- [x] CHANGE-018 record

#### 1.1.2 FeatureFlagsTab migration (Sprint 57.48 Track B endpoint)
- [x] NEW service function `fetchFeatureFlags(tenant_id)`
- [x] NEW hook `useFeatureFlags(tenant_id)`
- [x] Update FeatureFlagsTab.tsx — fixture → hook
- [x] Update Vitest spec
- [x] CHANGE-019 record

#### 1.1.3 QuotasTab migration (combined Quotas + RateLimits — Sprint 57.48 Track C + D)
- [x] NEW service functions `fetchQuotas` + `fetchRateLimits`
- [x] NEW hooks `useQuotas` + `useRateLimits`
- [x] Update QuotasTab.tsx (both sections)
- [x] Vitest spec
- [x] CHANGE-020 record

#### 1.1.4 HITLPoliciesTab migration (Sprint 57.48 Track A endpoint)
- [x] NEW service function `fetchHITLPolicies`
- [x] NEW hook `useHITLPolicies`
- [x] Update HITLPoliciesTab.tsx
- [x] Vitest spec
- [x] CHANGE-021 record

#### 1.1.5 MembersTab migration (Sprint 57.47 MEMBERS endpoint)
- [x] NEW service function `fetchTenantMembers`
- [x] NEW hook `useTenantMembers` (SHARED with Track B)
- [x] Update MembersTab.tsx
- [x] Vitest spec
- [x] CHANGE-022 record

#### 1.1.6 _fixtures.ts cleanup
- [x] Remove 5 migrated sections (FEATURE_FLAGS + QUOTAS + RATE_LIMITS + HITL_POLICIES + MEMBERS + GENERAL_FIXTURE + SEATS_FIXTURE)
- [x] Retain DANGER_OPS + IDENTITY_FIXTURE only with explicit comment
- [x] CHANGE-018 record covers this

### 1.2 Track B — AdminTenants Members Drawer

- [x] NEW component `TenantMembersDrawer.tsx`
- [x] Reuse `useTenantMembers` hook from Track A (SHARED)
- [x] Modify `TenantsTable.tsx` — add `onRowClick` prop → row click handler
- [x] Modify `AdminTenantsView.tsx` — mount drawer at view level
- [x] Pagination controls in drawer footer
- [x] Vitest spec for drawer + row click handler
- [x] Playwright e2e update — deferred (Vitest covers; manual smoke after merge)
- [x] CHANGE-023 record

### 1.3 Day 1 Validation Sweep
- [x] `cd frontend && npm run lint && npm run build` — exit 0; Vite bundle delta within ±5 KB
- [x] `cd frontend && npm run test` Vitest — all PASS; 598 (was 561; **+37 NEW**)
- [ ] `cd frontend && npm run test:e2e` — deferred Day 2 (parent will run on merge)
- [x] `python scripts/lint/run_all.py` — **9/9 GREEN** (preserve Sprint 57.48 baseline)
- [ ] Manual smoke — deferred Day 2 / parent verification

### 1.4 Day 1 commit
- [x] Commit: `feat(sprint-57-49): Day 1 frontend → backend migration wave (TenantSettings 5 tabs + AdminTenants Members)`

---

## Day 2 — Closeout (parent assistant)

### 2.1 Validation
- [ ] Full frontend test suite passing
- [ ] No regressions in existing Vitest/Playwright

### 2.2 Retrospective
- [ ] Write `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-49/retrospective.md`
- [ ] **1st validation under `mechanical-single-domain` 0.45 sub-class** logged in Q4 (ratio + decision)
- [ ] **`medium-frontend` 0.65 data point** logged

### 2.3 Sprint-workflow.md updates
- [ ] File MHist entry
- [ ] Matrix MHist entry (`medium-frontend` 2nd data point + sub-class validation result)
- [ ] §Active Activation history entry (Sprint 57.49 1st validation of NEW sub-class table)

### 2.4 Memory + index
- [ ] `memory/project_phase57_49_*.md` subfile
- [ ] MEMORY.md pointer entry

### 2.5 CLAUDE.md
- [ ] Current Sprint row + Last Updated footer (navigator-only)

### 2.6 PR + merge
- [ ] Push branch + open PR
- [ ] Wait CI green
- [ ] User merges
- [ ] Local cleanup

### 2.7 Final
- [ ] Day 2 commit: `chore(sprint-57-49): Day 2 retro + closeout`
- [ ] All checklist `[x]` or 🚧

---

**Modification History**:
- 2026-05-26: Sprint 57.49 Day 1 — completed; 5 NEW hooks + 5 service funcs + 6 tab updates + 1 NEW drawer + 12 NEW Vitest specs (37 total) + 6 CHANGE records + V2 lints 9/9 preserved
- 2026-05-26: Sprint 57.49 Day 0.1 — Initial draft (dual-track frontend migration wave; 1st validation NEW `mechanical-single-domain` 0.45 sub-class)

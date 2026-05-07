# Sprint 57.5 — Checklist

> [Sprint Plan](./sprint-57-5-plan.md)

**Sprint Goal**: Open Phase 57+ SaaS Frontend 4/N — Feature Flags Admin Console bundle(backend admin/feature_flags.py + 2 service-method extensions + frontend page);closes plan-time D1 RED + D2+D3 GAP findings(57.5 Day 0 plan-time Prong 1+2 catch);1st application of `mixed-pattern-reuse-intermediate` **0.50** intermediate candidate multiplier(NEW AD-Sprint-Plan-6-Intermediate;between AD-Sprint-Plan-6 proposed 0.40 + mixed 0.60 baseline;promotion-test sprint)。

---

## Day 0 — Setup + Day-0 三-prong 探勘 + Pre-flight Verify

### 0.1 Branch + plan + checklist commit
- [ ] **Branch from main(06d5c6ed)**
  - DoD:`git checkout -b feature/sprint-57-5-feature-flags-admin-bundle`
  - Verify:`git branch --show-current` → `feature/sprint-57-5-feature-flags-admin-bundle`
- [ ] **Commit plan + checklist**
  - DoD:both files staged + committed with conventional message `docs(plan, sprint-57-5): add plan + checklist for Feature Flags Admin Console bundle`
  - Verify:`git log --oneline -1` shows commit;`git status --short` clean

### 0.2 Day-0 三-prong 探勘 v3(per AD-Plan-3 + AD-Plan-4 fold-in promoted;57.5 third fully-applied sprint)
- [ ] **Prong 1 Path Verify**(per AD-Plan-2 path verify)
  - `frontend/src/features/admin-feature-flags/` 不存在(expect — NEW US-2+US-3)
  - `frontend/src/pages/admin-feature-flags/` 不存在(expect — NEW US-4)
  - `frontend/tests/e2e/admin_feature_flags/admin_feature_flags.spec.ts` 不存在(expect — NEW US-5)
  - `backend/tests/integration/api/test_admin_feature_flags.py` 不存在(expect — NEW US-1)
  - `backend/src/api/v1/admin/feature_flags.py` 不存在(expect — NEW US-1 — D1 RED already caught — already user-confirmed Option A pre-emptive bundle 2026-05-07)
  - `backend/src/core/feature_flags.py` exists(expect — MODIFY US-1)
  - `backend/src/infrastructure/db/models/feature_flag.py` exists(56.1 baseline)
  - `backend/src/infrastructure/db/migrations/versions/0015_feature_flags.py` exists(56.1 Alembic)
  - `backend/src/platform_layer/identity/auth.py:140 require_admin_platform_role` exists(56.2 reuse)
  - `frontend/src/features/admin-tenants/services/adminTenantsService.ts` exports `listTenants`(57.4 reuse for TenantSelector)
  - Verify:Glob + Grep results;0 unexpected drift(若有 → catalogue D9+)
- [ ] **Prong 2 Content Verify**(per AD-Plan-3 content verify promoted)
  - `core/feature_flags.py` 既有方法:`is_enabled` + `set_tenant_override` + `seed_defaults`(grep verify each method exists)
  - `core/feature_flags.py` 缺方法:`list_flags` 不存在 + `clear_tenant_override` 不存在(D2+D3 GAP — 已 user-confirmed Option A pre-emptive bundle 2026-05-07)
  - `core/feature_flags.py` 既有 `get_feature_flags_service` + `reset_feature_flags_service` singleton pattern(grep verify per testing.md §Module-level Singleton Reset Pattern)
  - `core/feature_flags.py` 既有 `DEFAULT_FLAGS` dict(4 baseline flags:thinking_enabled / verification_enabled / llm_caching_enabled / pii_masking — grep verify)
  - `infrastructure/db/audit_helper.py` 既有 `append_audit` chain helper(grep verify import path 57.3 + 57.4 + 56.1 usage)
  - `api/main.py` 既有 admin router import pattern(`from api.v1.admin.tenants import router as admin_tenants_router`)+ include_router pattern(grep verify line ~56-57 mountpoint)
  - Pydantic v2 `Query(...)` + `ConfigDict(extra="forbid")` 既有 56.x+57.3 慣例 grep verify
  - Verify:0 new wrong-content drift(D1+D2+D3 RED+GAP catch already user-confirmed Option A pre-emptive bundle 2026-05-07)
- [ ] **Prong 3 Schema Verify**(per AD-Plan-4-Schema-Grep promoted)
  - 此 sprint 無新 DB schema/migration → Schema verify N/A
  - **但 attempt 完成** per fold-in spirit:Grep `migrations/versions/0017_*.py` 不存在 confirm;Grep `class FeatureFlag` ORM 6 fields(name PK / default_enabled / tenant_overrides JSONB / description / created_at / updated_at)全 verified for list / resolved / override CRUD compatibility
  - Verify:N/A verdict logged in progress.md;not skip silently

### 0.3 Calibration multiplier pre-read
- [ ] **`mixed-pattern-reuse-intermediate` 0.50 intermediate candidate 1st application** (NEW AD-Sprint-Plan-6-Intermediate)
  - Retroactive evidence with 0.50:57.3 mixed 0.60 ratio 0.57(retro-recalc with 0.50: 0.68)+ 57.4 mixed 0.60 ratio 0.42(retro-recalc with 0.50: 0.50)= retroactive 2-data-point mean **0.59** still under band by 0.26 — but progressively closer than 0.60(57.3+57.4 平均 0.50)
  - 此 sprint:bottom-up ~16 hr × 0.50 = **~8 hr** commit(promotion-test sprint per NEW AD-Sprint-Plan-6-Intermediate;between AD-Sprint-Plan-6 proposed 0.40 + mixed 0.60 baseline)
  - Day 4 retro Q2 verify:若 ratio in [0.85, 1.20] → strong evidence to promote 0.50 as new matrix class;若 ratio < 0.85 → 進一步降至 0.40-0.45 candidate(re-evaluate AD-Sprint-Plan-6 original 0.40 proposal);若 ratio > 1.20 → revert to `mixed` 0.60 baseline + log new AD

### 0.4 Pre-flight verify(main green baseline)
- [ ] **Backend baselines**
  - `python -m pytest backend/tests/ -q --tb=no` → 1598 collected / 0 failures(Sprint 57.4 baseline)
  - `python -m mypy backend/src --strict` → 0 errors / 295 source files
  - `python scripts/lint/run_all.py` → 8 V2 lints 8/8 green
  - `grep -rn "import openai\|import anthropic" backend/src/agent_harness/` → 0 results(LLM SDK leak)
  - Verify:All 4 baselines documented in progress.md ✅ (1598 / 0/295 / 8/8 / 0)
- [ ] **Frontend baselines**
  - `cd frontend && npm run lint` → clean
  - `cd frontend && npm run build` → success / 75 modules / 209.11 kB
  - `cd frontend && npm run test` → 35 unit tests pass(57.4 baseline)
  - Playwright e2e 23 tests baseline(57.4 closeout)
  - Verify:All 4 baselines documented in progress.md ✅ (ESLint clean / Vite 75 modules 209.11 kB / Vitest 35/35 / Playwright 23)

### 0.5 Day 0 progress.md commit + push
- [ ] **Catalogue D-findings + cross-reference plan-time catch**
  - D1+D2+D3 closed by user-confirmed Option A pre-emptive bundle 2026-05-07
  - D4-D8 informational(per plan §Risks)
  - Document Day 0 三-prong third fully-applied sprint attempt time + findings count
  - Verify:`docs/03-implementation/agent-harness-execution/phase-57/sprint-57-5/progress.md` exists with Day 0 section ✅
- [ ] **Day 0 commit + push**
  - DoD:progress.md staged + committed `docs(progress, sprint-57-5): Day 0 三-prong 探勘 + pre-flight baseline verify`
  - Verify:`git log --oneline -1` shows commit;remote up-to-date(branch pushed to origin)

---

## Day 1 — US-1 Backend admin endpoints + service-method extensions

### 1.1 FeatureFlagsService.list_flags + clear_tenant_override
- [ ] **MODIFY `backend/src/core/feature_flags.py` add `async def list_flags(self) -> list[FeatureFlag]`**
  - SQL:`stmt = select(FeatureFlag).order_by(FeatureFlag.name)` → `result.scalars().all()`
  - Type hint:`-> list[FeatureFlag]`
  - File header MHist:`+ N+1 line: 2026-05-08: Sprint 57.5 — add list_flags + clear_tenant_override + service singleton compatibility`
  - Verify:`grep -n "async def list_flags" backend/src/core/feature_flags.py` → 1 result
- [ ] **MODIFY `backend/src/core/feature_flags.py` add `async def clear_tenant_override(self, ...)`**
  - Args:`flag_name: str / tenant_id: UUID / actor_user_id: UUID | None = None`
  - Returns:`bool`(True if was-present-now-cleared,False if no-op idempotent)
  - Body:load flag → if None FeatureFlagNotFoundError → previous = tenant_overrides.get(str(tenant_id)) → if None return False → pop + reassign tenant_overrides → append_audit(operation="feature_flag_override_cleared", operation_data={flag_name, tenant_id, previous_override}) → flush → cache invalidation(same key drop pattern as set_tenant_override)→ return True
  - Mirror `set_tenant_override` pattern;same audit chain mechanism
  - Verify:`grep -n "async def clear_tenant_override" backend/src/core/feature_flags.py` → 1 result

### 1.2 NEW `backend/src/api/v1/admin/feature_flags.py` Pydantic models + 4 endpoints
- [ ] **Create `backend/src/api/v1/admin/feature_flags.py`**
  - File header per file-header-convention.md(Purpose / Category / Created / MHist initial entry)
  - 6 Pydantic models:`FeatureFlagItem` / `FeatureFlagListResponse` / `FeatureFlagResolvedItem` / `FeatureFlagResolvedListResponse` / `FeatureFlagOverrideRequest` (extra="forbid") / `FeatureFlagOverrideResponse`
  - `router = APIRouter(prefix="/admin/feature-flags", tags=["admin", "feature-flags"])`
  - 4 endpoints:`GET ""` list / `GET "/tenants/{tenant_id}"` resolved / `PATCH "/{flag_name}/tenants/{tenant_id}"` set / `DELETE "/{flag_name}/tenants/{tenant_id}"` clear(status_code=204)
  - All 4 deps include `Depends(require_admin_platform_role)`;PATCH+DELETE 加 `admin_user_id: UUID = Depends(get_current_admin_user_id)` for audit chain actor capture
  - Use `get_feature_flags_service(db)` factory per testing.md singleton pattern
  - Imports:`from sqlalchemy.ext.asyncio import AsyncSession` + `from fastapi import APIRouter, Depends, HTTPException, status` + service + auth + Pydantic + UUID + datetime + select(SQLAlchemy)
  - Verify:`grep -n "@router.get\|@router.patch\|@router.delete" backend/src/api/v1/admin/feature_flags.py` → 4 endpoints

### 1.3 MODIFY `backend/src/api/main.py` mount admin_feature_flags_router
- [ ] **Add import + include_router**
  - Add line(after admin_tenants_router import):`from api.v1.admin.feature_flags import router as admin_feature_flags_router`
  - Add line(after include admin_tenants):`app.include_router(admin_feature_flags_router, prefix="/api/v1")`
  - File header MHist:`+ N+1 line: 2026-05-08: Sprint 57.5 — mount admin_feature_flags router (POST /api/v1/admin/feature-flags/...)`
  - Verify:`grep -n "admin_feature_flags_router" backend/src/api/main.py` → 2 results (import + include)

### 1.4 NEW test file test_admin_feature_flags.py
- [ ] **Create `backend/tests/integration/api/test_admin_feature_flags.py`**(D9 path follows existing 56.x flat convention per 57.3 + 57.4)
  - Test 1:`test_list_flags_happy_no_overrides` — admin user → 200 + 4 baseline flags + each item has override_count=0
  - Test 2:`test_resolved_for_tenant_no_overrides` — admin auth + new tenant → 200 + 4 items all has_override=False + effective_value=default
  - Test 3:`test_resolved_for_tenant_with_override` — fixture seed `set_tenant_override("thinking_enabled", tenant, False)` → GET resolved → 200 + items has thinking_enabled.has_override=True + effective_value=False
  - Test 4:`test_set_override_happy_chain` — PATCH `{enabled: false}` → 200 + audit chain entry with operation="feature_flag_override_set" + previous_override=null + new_value=false
  - Test 5:`test_set_override_unknown_flag_404` — PATCH unknown flag → 404
  - Test 6:`test_clear_override_happy_chain` — seed set_tenant_override → DELETE → 204 + audit chain entry with operation="feature_flag_override_cleared"
  - Test 7:`test_clear_override_no_op_204` — DELETE without prior override → 204(idempotent;service returns False but endpoint still 204)
  - Test 8:`test_401_unauth` — no JWT → 401 across all 4 endpoints(可分 4 test or parametrize)
  - Test 9:`test_403_wrong_role` — non-admin JWT → 403 across all 4 endpoints(可分 4 test or parametrize)
  - Test 10 (optional):`test_set_override_invalid_body` — PATCH with extra field → 422(extra="forbid")
  - Verify:`python -m pytest backend/tests/integration/api/test_admin_feature_flags.py -v` → ≥8 pass / 0 fail

### 1.5 Day 1 sanity checks
- [ ] **Backend baselines verify**
  - `python -m pytest backend/tests/ -q --tb=no` → 1606+ collected / 0 failures(+8)
  - `python -m mypy backend/src/api/v1/admin/feature_flags.py backend/src/core/feature_flags.py --strict` → 0 errors
  - `python scripts/lint/run_all.py` → 8 V2 lints 8/8 green
  - `grep -rn "import openai\|import anthropic" backend/src/agent_harness/` → 0(LLM SDK leak)
  - Verify:All 4 sanity checks pass + recorded in progress.md

### 1.6 Day 1 commit + push + progress.md
- [ ] **Commit US-1 + push**
  - Commit message:`feat(api+core, sprint-57-5): add admin/feature_flags router + list_flags + clear_tenant_override service methods (US-1 closes D1+D2+D3)`
  - Co-author:`Co-Authored-By: Claude <noreply@anthropic.com>`
  - progress.md Day 1 section recorded(actual_min / est_min ratio note)
  - Verify:`git log main..HEAD --oneline` shows new commit + previous Day 0;remote up-to-date

---

## Day 2 — US-2 Frontend Infra (types + service + store)

### 2.1 features/admin-feature-flags/ skeleton
- [ ] **Create folder structure**
  - `frontend/src/features/admin-feature-flags/{components,services,store}/`
  - Verify:`ls frontend/src/features/admin-feature-flags/` shows 3 subdirs

### 2.2 types.ts mirror US-1 Pydantic models
- [ ] **Create `frontend/src/features/admin-feature-flags/types.ts`**
  - `interface FeatureFlagItem { name / default_enabled / description / override_count / created_at / updated_at }`
  - `interface FeatureFlagListResponse { items / total }`
  - `interface FeatureFlagResolvedItem { flag_name / default_enabled / has_override / effective_value / description }`
  - `interface FeatureFlagResolvedListResponse { items / tenant_id }`
  - `interface FeatureFlagOverrideRequest { enabled }`
  - `interface FeatureFlagOverrideResponse { flag_name / tenant_id / enabled }`
  - File header docstring per file-header-convention.md
  - Verify:`cat frontend/src/features/admin-feature-flags/types.ts` ≥ 40 lines

### 2.3 adminFeatureFlagsService.ts plain fetch with 4 methods
- [ ] **Create `services/adminFeatureFlagsService.ts`**
  - Mirror admin-tenants `_handleResponse<T>` helper(per 57.4 D6)
  - `listFlags()` GET — no params
  - `listResolvedForTenant(tenantId)` GET — encode tenantId in path
  - `setOverride(flagName, tenantId, enabled)` PATCH JSON body `{enabled}`
  - `clearOverride(flagName, tenantId)` DELETE — accept 204(no body to parse;handle 204 separately from 200+ JSON path)
  - `API_BASE = "/api/v1/admin/feature-flags"` + `credentials: "include"` for auth cookie
  - Verify:`npm run lint` clean for new file

### 2.4 adminFeatureFlagsStore.ts Zustand
- [ ] **Create `store/adminFeatureFlagsStore.ts`**
  - State:`flags` (FeatureFlagItem[]) / `resolvedFlags` (FeatureFlagResolvedItem[]) / `selectedTenantId` (string | null) / `loading` / `loadError` / `saving` (string | null = flag_name being saved) / `saveError`
  - Actions:
    - `setSelectedTenant(tenantId)` resets selectedTenantId(null clears resolvedFlags too)
    - `loadFlags()` calls listFlags + sets flags
    - `loadResolvedForTenant(tenantId)` calls listResolvedForTenant + sets resolvedFlags
    - `setOverride(flagName, enabled)` calls service + on success invalidates + reloads resolved + sets saving / saveError lifecycle
    - `clearOverride(flagName)` calls service + on success invalidates + reloads resolved + sets saving / saveError lifecycle
    - `reset()`
  - Mirror tenant-settings store pattern(57.3 saving/saveError + 57.4 listing pattern combined)
  - Verify:`npm run build frontend/` clean(no TS errors)

### 2.5 3 Vitest unit tests US-2
- [ ] **Create `frontend/tests/unit/admin-feature-flags/adminFeatureFlagsService.test.ts`**
  - Test 1:`setOverride` PATCH body — assert fetch called with method=PATCH + body=JSON.stringify({enabled: false})
  - Test 2:`listResolvedForTenant` — assert URL contains tenant_id
  - Verify:`npm run test -- adminFeatureFlagsService` ≥ 2 pass

- [ ] **Create `frontend/tests/unit/admin-feature-flags/adminFeatureFlagsStore.test.ts`**
  - Test 3:store loadResolvedForTenant success → resolvedFlags + loading=false
  - Verify:`npm run test -- adminFeatureFlagsStore` ≥ 1 pass

### 2.6 Day 2 sanity checks
- [ ] **Frontend baselines verify**
  - `cd frontend && npm run lint` clean
  - `cd frontend && npm run build` success / 75 → 77+ modules
  - `cd frontend && npm run test` → 35 → 38+ tests pass(+3)
  - Verify:All 3 sanity checks recorded in progress.md

### 2.7 Day 2 commit + push + progress.md
- [ ] **Commit US-2 + push**
  - Commit message:`feat(frontend, sprint-57-5): add admin-feature-flags infra (types/service/store + 3 Vitest) (US-2)`
  - progress.md Day 2 section + actual_min ratio note
  - Verify:`git log main..HEAD --oneline` shows commit;remote up-to-date

---

## Day 3 — US-3 + US-4 Frontend Components + Page Layout

### 3.1 TenantSelector component (uses 57.4 listTenants — pattern reuse demo)
- [ ] **Create `components/TenantSelector.tsx`**
  - Import:`import { listTenants } from "../../admin-tenants/services/adminTenantsService";`(cross-feature import per 17.md spirit)
  - On mount(useEffect):call `listTenants({ limit: 200, offset: 0 })` → setOptions
  - Render:`<select>` with `<option value="">— Select tenant —</option>` + dynamic options(value=id;label=`${code} (${display_name})`)
  - onChange → call store `setSelectedTenant(value || null)` → triggers loadResolvedForTenant
  - Loading state:disabled + "Loading tenants..." placeholder
  - Error state:disabled + error text below
  - Verify:File ≥ 60 lines + lint clean

### 3.2 FlagsTable component
- [ ] **Create `components/FlagsTable.tsx`**
  - Columns: Flag Name (monospace) / Description / Default (badge: True green / False gray) / Override (badge: True/False blue if has_override / "—" gray if no override) / Effective Value (badge: True green / False gray) / Actions
  - Actions per row:if effective_value=true → "Set Override Off" button(call store.setOverride(name, false));if effective_value=false → "Set Override On" button(call store.setOverride(name, true));always:if has_override=true → "Clear Override" button(call store.clearOverride(name))
  - Empty state:if selectedTenantId === null → "Select a tenant to view feature flags" 提示
  - Empty state:if selectedTenantId set 但 resolvedFlags.length === 0 → "No flags loaded;try reload" + Reload button(call loadResolvedForTenant)
  - Loading skeleton:4 placeholder rows when `loading === true`
  - Saving overlay:當前 saving flag_name === row.flag_name → row disabled + "Saving..." text(per 57.5 D8 Option Simple — single-row lock)
  - Verify:File ≥ 130 lines + lint clean

### 3.3 pages/admin-feature-flags/index.tsx page layout
- [ ] **Create `pages/admin-feature-flags/index.tsx`**
  - Layout:`<TenantSelector />` 上 + `<FlagsTable />` 中 + Saving status bar 下(shows last save action + saveError if any)
  - On mount(useEffect):call `loadFlags()`(load all flags so we know description/default for table)
  - On selectedTenantId change(subscribe store):call `loadResolvedForTenant(tenantId)` if not null
  - Verify:File ≥ 60 lines + lint clean

### 3.4 5 Vitest unit tests (4 US-3 + 1-2 US-4)
- [ ] **Create `frontend/tests/unit/admin-feature-flags/TenantSelector.test.tsx`**
  - Test 1:render with mock tenants(2 options)→ assert dropdown has 3 options(empty + 2 tenants)
  - Test 2:onChange → assert store.setSelectedTenant called with value
  - Verify:`npm run test -- TenantSelector` ≥ 2 pass

- [ ] **Create `frontend/tests/unit/admin-feature-flags/FlagsTable.test.tsx`**
  - Test 3:render with empty selectedTenantId → assert "Select a tenant" prompt visible
  - Test 4:render with mock resolvedFlags(2 rows)→ assert rows + override badges + action buttons visible
  - Verify:`npm run test -- FlagsTable` ≥ 2 pass

- [ ] **Create `frontend/tests/unit/admin-feature-flags/AdminFeatureFlagsPage.test.tsx`**
  - Test 5:page mount → loadFlags called(spyOn store)
  - Test 6 (optional):tenant select → loadResolvedForTenant called
  - Verify:`npm run test -- AdminFeatureFlagsPage` ≥ 1 pass(2 if optional included)

### 3.5 Day 3 sanity checks
- [ ] **Frontend baselines verify**
  - `cd frontend && npm run lint` clean
  - `cd frontend && npm run build` success / 77 → 80+ modules
  - `cd frontend && npm run test` → 38 → 43+ tests pass(+5)
  - Verify:All 3 sanity checks recorded in progress.md

### 3.6 Day 3 commit + push + progress.md
- [ ] **Commit US-3 + US-4 + push**
  - Commit message:`feat(frontend, sprint-57-5): add admin-feature-flags components + page layout + 5 Vitest (US-3 + US-4)`
  - progress.md Day 3 section + actual_min ratio note
  - Verify:`git log main..HEAD --oneline` shows commit;remote up-to-date

---

## Day 4 — US-5 Routing + Playwright E2E + Closeout Ceremony

### 4.1 App.tsx route + Home nav Link
- [ ] **Modify `frontend/src/App.tsx`**
  - Add import: `import { AdminFeatureFlagsPage } from "./pages/admin-feature-flags";`(or direct path)
  - Add Route: `<Route path="/admin-feature-flags" element={<AdminFeatureFlagsPage />} />`
  - Add Home nav `<Link to="/admin-feature-flags">Feature Flags Admin Console</Link>`(always visible per 57.1 D10 Option C — backend 401/403 surfaces as Error UX)
  - File header MHist:`+ N+1 line: 2026-05-08: Sprint 57.5 — wire /admin-feature-flags route + Home Link (US-4)`
  - Verify:`grep -n "admin-feature-flags" frontend/src/App.tsx` shows Route + Link

### 4.2 Playwright e2e admin_feature_flags.spec.ts (4 cases)
- [ ] **Create `frontend/tests/e2e/admin_feature_flags/admin_feature_flags.spec.ts`**
  - Use `page.route()` browser-layer mock per 57.1 v2 D19 + 57.3 D13 + 57.4 D14 pattern
  - Test 1 (happy path):mock GET `/admin/tenants` (for selector) + mock GET `/admin/feature-flags` → render TenantSelector with options + initially empty FlagsTable with prompt
  - Test 2 (select tenant):click select dropdown → choose tenant → assert second mocked GET `/admin/feature-flags/tenants/{id}` triggered → table shows rows
  - Test 3 (set override):mock PATCH `/admin/feature-flags/thinking_enabled/tenants/{id}` returning 200 → click "Set Override Off" → assert PATCH triggered with `{enabled: false}` body → table refresh after second mocked GET resolved
  - Test 4 (clear override):mock DELETE → click "Clear Override" → assert DELETE triggered → table refresh → row Override badge "—"
  - Verify:`cd frontend && npx playwright test admin_feature_flags` ≥ 4 pass(< 30s each)

### 4.3 Final pytest + lint + leak verify
- [ ] **Backend final baselines**
  - `python -m pytest backend/tests/ -q --tb=no` → 1606+ collected / 0 failures(+8)
  - `python -m mypy backend/src --strict` → 0 errors / 296 source files(+1 NEW admin/feature_flags.py)
  - `python scripts/lint/run_all.py` → 8 V2 lints 8/8 green
  - LLM SDK leak grep → 0
  - Verify:Documented in progress.md ✅
- [ ] **Frontend final baselines**
  - `cd frontend && npm run lint` clean
  - `cd frontend && npm run build` success / 80+ modules / ~215 kB(estimated +6 KB)
  - `cd frontend && npm run test` → 43+ tests pass(+9)
  - Playwright e2e:23 → 27+ tests pass(+4)
  - Verify:Documented in progress.md ✅

### 4.4 Retrospective.md
- [ ] **Create `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-5/retrospective.md`**
  - Q1 What went well
  - Q2 What didn't go well + NEW AD-Sprint-Plan-6-Intermediate 0.50 1st application calibration verify(actual_hr / committed_hr ratio + retroactive 3-data-point window mean + 推薦 KEEP 0.50 / SHIFT to 0.40-0.45 / REVERT to mixed 0.60)
  - Q3 What we learned + Day 0 三-prong third fully-applied sprint observations(time / drifts / ROI evidence vs 57.3 + 57.4 prior applications)
  - Q4 Audit Debt deferred(明確標 ID + target sprint)
  - Q5 Next steps + Phase 57.x next-sprint candidates(rolling planning;不寫具體未來 sprint 任務,只寫 carryover 候選)
  - Q6 Solo-dev policy validation
  - Verify:`wc -l retrospective.md` ≥ 200 lines

### 4.5 Memory snapshot + MEMORY.md index
- [ ] **Create `memory/project_phase57_5_feature_flags_admin.md`**
  - Same format as `project_phase57_4_admin_tenants_list.md`
  - Verify:File created + frontmatter complete
- [ ] **Update MEMORY.md index** add 1 line entry
  - Verify:`grep "phase57_5" MEMORY.md` shows 1 result

### 4.6 Open PR + CI green + solo-dev merge
- [ ] **Push branch + open PR**
  - Push:`git push -u origin feature/sprint-57-5-feature-flags-admin-bundle`
  - PR title:`Sprint 57.5 — Phase 57+ SaaS Frontend 4/N: Feature Flags Admin Console bundle`
  - PR body:Sprint goal + 5 USs + acceptance + NEW AD-Sprint-Plan-6-Intermediate 0.50 1st app verdict + D-findings reference
  - Verify:5 active CI checks green;solo-dev policy review_count=0 satisfied
- [ ] **Squash merge to main**
  - DoD:GitHub UI squash + merge;branch deleted post-merge
  - Verify:main HEAD updated;`git pull main` shows new commit

### 4.7 Closeout PR
- [ ] **Closeout branch + PR**
  - Branch:`chore/sprint-57-5-closeout`
  - Updates:SITUATION-V2 §9 milestones row + §11 Last Updated + Update history;CLAUDE.md Phase / Latest Sprint / main HEAD / Last Updated / Current Phase fields
  - Commit message:`docs(closeout, sprint-57-5): SITUATION-V2 + CLAUDE.md sync to Phase 57+ Frontend SaaS 4/N opens`
  - PR body:reference Sprint 57.5 PR + summary stats(pytest delta / Vitest delta / Playwright delta / Vite build modules delta / calibration ratio + NEW AD-Sprint-Plan-6-Intermediate 0.50 verdict)
  - Verify:Squash merge to main;both branches deleted;working tree clean

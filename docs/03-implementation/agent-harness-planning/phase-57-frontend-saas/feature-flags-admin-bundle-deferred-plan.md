# Sprint 57.5 — Phase 57+ SaaS Frontend 4th: Feature Flags Admin Console Bundle (backend admin endpoints + frontend tenant-selector + flags table)

> **Sprint Type**: Phase 57+ fourth sprint — **intermediate `mixed-pattern-reuse` 0.50 candidate** scope class(中間 candidate 介於 AD-Sprint-Plan-6 0.40 提議 與 mixed 0.60 baseline 之間;**1st application** — promotion-test sprint);bundle 1 backend admin endpoint set(GET list + GET resolved-per-tenant + PATCH override + DELETE override)+ 1 frontend Feature Flags Admin Console page;closes plan-time Prong 1+2 D1 RED finding(backend admin feature_flags endpoints 完全 0)+ D2+D3 service-method gaps;heavy pattern reuse from 57.4 admin-tenants infra + 57.4 listTenants service for tenant selector dropdown
> **Owner Categories**: §Frontend (16-frontend-design.md §Feature Flags Admin Console) / §Backend Admin API (NEW `admin/feature_flags.py` mirror 57.4 admin/tenants.py pattern) / consumes 56.1 FeatureFlagsService + FeatureFlag ORM + 56.2 require_admin_platform_role + 57.4 admin-tenants types/service/store/components scaffold + 57.4 listTenants for tenant selector
> **Phase**: 57 (Frontend SaaS — 4/N sprint;follow-on candidates per Sprint 57.4 retrospective Q5: Onboarding self-serve wizard / Audit log frontend view / Compliance partial GDPR / DR + WAL streaming / SaaS Stage 2 / AD-Cat10-VisualVerifier+Frontend-Panel / AD-Cat11-Multiturn+SSEEvents+ParentCtx / AD-CI-6 Phase 58;rolling planning per .claude/rules/sprint-workflow.md)
> **Workload**: 5 days (Day 0-4); bottom-up est ~16 hr → calibrated commit **~8 hr** (multiplier **0.50** intermediate candidate — Sprint 57.5 為 1st application of `mixed-pattern-reuse-intermediate` 0.50 between AD-Sprint-Plan-6 proposed 0.40 and mixed 0.60 baseline;2-data-point retroactive evidence with 0.50:57.3 ratio 0.68 + 57.4 ratio 0.50 平均 0.59 still under band — 0.50 比 0.40 保守 並 避免預限進一步偏差;若 ratio in [0.85, 1.20] → strong evidence to promote 0.50 as new class;若 ratio < 0.85 → 進一步降至 0.40-0.45 candidate;若 ratio > 1.20 → revert to `mixed` 0.60 baseline)
> **Branch**: `feature/sprint-57-5-feature-flags-admin-bundle`
> **Plan Authority**: This document (per CLAUDE.md §Sprint Execution Workflow)
> **Roadmap Source**: 16-frontend-design.md §Feature Flags Admin Console + 56.1 US-4 FeatureFlagsService backend ship + Sprint 57.4 retrospective Q5 (Phase 57.5 candidate scope user-approved 2026-05-07 "Feature flags admin UI") + plan-time Prong 1+2 探勘 D1 RED + D2+D3 GAP 已 caught (backend admin feature_flags surface 完全 0;FeatureFlagsService 缺 list_flags + clear_tenant_override 兩 method)
> **AD logging (sub-scope)**: NEW AD-Sprint-Plan-6-Intermediate `mixed-pattern-reuse-intermediate` 0.50 1st application(promotion-test sprint;between AD-Sprint-Plan-6 proposed 0.40 + mixed 0.60 baseline;若 in band → 1st data point of new intermediate class;若 < 0.85 → 證據降至 0.40-0.45;若 > 1.20 → revert to mixed 0.60);Day 0 三-prong 探勘 v3 — Path + Content + Schema all attempted(Schema verdict = N/A 但 attempt 完成);third fully-applied 三-prong sprint(57.3 1st + 57.4 2nd + 57.5 3rd);ROI evidence accumulating

---

## Sprint Goal

Open the **Feature Flags Admin Console UX surface** for Phase 57+ SaaS Frontend by bundling 1 backend admin endpoint set + 1 frontend page in a single mixed-pattern-reuse sprint:

- **US-1**: Backend `admin/feature_flags.py` NEW router file with 4 endpoints — `GET ""` list all flags + override_count / `GET "/tenants/{tenant_id}"` resolved-per-tenant view / `PATCH "/{flag_name}/tenants/{tenant_id}"` set override / `DELETE "/{flag_name}/tenants/{tenant_id}"` clear override;NEW service methods `FeatureFlagsService.list_flags` + `clear_tenant_override`(audit chain on both write paths);Pydantic FeatureFlagItem + FeatureFlagListResponse + FeatureFlagResolvedItem + FeatureFlagOverrideRequest;`require_admin_platform_role` per 56.2 RBAC pattern;mount router in api/main.py;8-10 unit + integration tests
- **US-2**: Frontend `frontend/src/features/admin-feature-flags/` infra — service + store + types mirroring 57.4 admin-tenants pattern(plain fetch + `_handleResponse<T>` + Zustand;query state + flags list + resolved-per-tenant + saving lifecycle);types.ts mirror US-1 Pydantic responses + Request body;3 Vitest unit tests
- **US-3**: Frontend `features/admin-feature-flags/components/` — `TenantSelector.tsx`(dropdown using `listTenants` from 57.4 admin-tenants service — **cross-feature pattern reuse demo**)+ `FlagsTable.tsx`(rows: Flag Name / Default badge / Tenant Override badge / Effective Value badge / Actions:Set Override + Clear Override buttons);empty state when no tenant selected;loading skeleton when resolved list loading;3-4 Vitest unit tests
- **US-4**: Frontend `pages/admin-feature-flags/index.tsx`(layout: TenantSelector top + FlagsTable middle + Saving status bar bottom);on tenant select → loadResolved(tenantId);on toggle action → setOverride/clearOverride + reload;App.tsx add `/admin-feature-flags` route + Home Link(always visible per 57.1 D10 Option C);1-2 Vitest unit tests
- **US-5**: Playwright e2e + closeout — 4 e2e specs(`admin_feature_flags.spec.ts`):happy(load → tenant select → flags resolved)+ set override(click toggle → PATCH triggered → table refresh)+ clear override(click Clear → DELETE triggered → table refresh)+ empty state(no tenant selected → see "Select tenant to view flags" prompt);retrospective(6 必答 + AD-Sprint-Plan-6 1st application calibration verify + Phase 57.x next-sprint candidates Q5)+ memory snapshot + SITUATION-V2 + CLAUDE.md sync

Sprint 結束後:
- (a) **Feature Flags Admin Console 主流量 functional** — admin user 可 browse `/admin-feature-flags` → select target tenant from dropdown → see all 4 baseline flags resolved with override badges → click Set/Clear Override → audit chain logs the change → table refreshes
- (b) **Backend admin/feature_flags.py 補齊 R+U+D surface** — 從 0 endpoint → 4 endpoints;為後續 admin operations(impersonation / audit trace / compliance dashboard)鋪 listFlags + tenant-resolved + override CRUD pattern
- (c) **NEW AD-Sprint-Plan-6-Intermediate 0.50 candidate 1st-data-point validation** — 若 ratio in [0.85, 1.20] band → strong evidence to promote `mixed-pattern-reuse-intermediate` 0.50 multiplier as new matrix class(可選擇進一步合併到 AD-Sprint-Plan-6 family);若 ratio < 0.85 → 證據支持降至 0.40-0.45 (re-evaluate AD-Sprint-Plan-6 original 0.40 proposal);若 ratio > 1.20 → revert to `mixed` 0.60 + log new AD
- (d) **D1+D2+D3 RED+GAP findings plan-time closed** — Day 0 plan-time Prong 1+2 catch(backend admin feature_flags surface 完全 0 + FeatureFlagsService 缺 list_flags + clear_tenant_override);Option A pre-emptive bundle 解決真正 backend gap;為後續 admin operations 鋪通用 endpoint+service-method pattern
- (e) **Frontend SaaS 4/N rolling planning continues** — Sprint 57.5 retro Q5 列出 Phase 57.x candidate scope(Onboarding self-serve wizard requires backend self-serve API design / Audit log frontend view / Compliance partial GDPR / DR / SaaS Stage 2);user approval required per rolling planning 紀律

**主流量驗收標準**:
- `npm run dev` → admin user browse `/admin-feature-flags` → see TenantSelector + initially empty FlagsTable with "Select tenant to view flags" prompt
- `npm run dev` → admin user select tenant from dropdown → FlagsTable refreshes with 4 baseline flags + each row shows Default + Override badge(if any)+ Effective Value
- `npm run dev` → admin user click "Set Override = Off" on `thinking_enabled` → confirm dialog → PATCH → table refreshes with Override badge "Off" + Effective Value "Off"
- `npm run dev` → admin user click "Clear Override" on `thinking_enabled` → confirm dialog → DELETE → table refreshes with Override badge "—" + Effective Value reverts to default
- `pytest backend/tests/integration/api/test_admin_feature_flags.py` ≥ 8 new tests pass
- Playwright e2e 4 tests pass(happy + set + clear + empty)< 30s each
- `npm run lint && npm run build` clean
- `npm run test` (Vitest unit) ≥ 9 new tests pass
- Backend pytest baseline 1598 → 1606+(+8 from US-1)
- 8 V2 lints baseline 8/8 unchanged

---

## Background

### V2 進度

- **22/22 sprints (100%) main progress completed** + **Phase 56-58 SaaS Stage 1 3/3 ✅ CLOSED** (Sprint 56.3) + **Phase 57+ Frontend SaaS 3/N completed**(Sprint 57.1 v2 Cost+SLA dashboards + Sprint 57.3 Tenant Settings bundle + Sprint 57.4 Admin Tenants Console list bundle)
- main HEAD: `06d5c6ed` (Sprint 57.4 closeout PR #111) — Day 0 verified
- pytest baseline 1598 / mypy --strict 0/295 source files / 8 V2 lints 8/8 green / LLM SDK leak 0
- Vitest baseline 35 / Playwright e2e baseline 23 / Vite build 75 modules / 209.11 kB
- 57.4 calibration `mixed` 0.60 mid-band 4th application ratio **0.42** under band by 0.43(4-data-point mean **0.79 ⬇️ below band**)→ AD-Sprint-Plan-6 logged proposing split `mixed-greenfield` (0.60 retained for novel scope) vs `mixed-pattern-reuse` (~0.40 for sprints extending established frontend feature folder)
- 15-sprint cumulative window 8/15 (53%) further dropped below 60% threshold for second consecutive sprint after 57.3 first dip
- **本 sprint = Phase 57+ SaaS Frontend 第 4 個 sprint**(4/N rolling;57.1 v2 Cost+SLA + 57.3 Tenant Settings + 57.4 Admin Tenants list delivered;57.5 Feature Flags Admin Console)

### 為什麼 57.5 是 intermediate `mixed-pattern-reuse-intermediate` 0.50 1st application 而非 0.60 baseline 或 0.40 AD-Sprint-Plan-6 proposal

User approved 2026-05-07 "Feature flags admin UI" + scope class `mixed-pattern-reuse-intermediate` 0.50(中間 candidate;Phase 57.5 1st candidate per 57.4 retrospective Q5);Day 0 plan-time Prong 1+2 探勘 confirmed:

1. **57.5 plan-time Prong 1+2 catch** — backend `admin/feature_flags.py` 完全不存在(類比 57.4 D1 RED finding);FeatureFlagsService 缺 `list_flags()` + `clear_tenant_override()` 兩 method(D2+D3 GAP);plan-time Day 0 探勘 fully applied 三-prong 第 3 次 fully-applied sprint(57.3 1st + 57.4 2nd + 57.5 3rd)
2. **Heavy pattern reuse from 57.4** — 57.4 admin-tenants frontend infra(types/service/store/components/page-layout/Playwright pattern)is the established pattern;Sprint 57.5 cloned scaffold mostly mirror;**TenantSelector.tsx will directly use `listTenants` from 57.4 admin-tenants service** — cross-feature pattern reuse demo per 17.md spirit
3. **0.50 intermediate candidate rationale** — Sprint 57.5 是 1st application of intermediate 0.50 multiplier(介於 AD-Sprint-Plan-6 proposed 0.40 + mixed 0.60 baseline);user-approved 2026-05-07;比 0.40 保守(避免預限進一步偏差)+ 比 0.60 進取(承認 pattern reuse acceleration);retroactive evidence with 0.50 multiplier:57.3 ratio 0.68 + 57.4 ratio 0.50 = 平均 0.59 仍 under band by 0.26 — but progressively closer than 0.60(57.3+57.4 平均 0.50)
4. **Conservative endpoint scope** — 4 endpoints only(GET list + GET resolved + PATCH set + DELETE clear);no list-pagination(only 4 baseline flags + future flags rarely > 20 globally;non-paginated keeps endpoint simple);no per-flag history/audit-trail UI(Phase 58+ if requested)
5. **AD-Plan-3 + AD-Plan-4 兩+三 prong already fold-in to sprint-workflow.md §Step 2.5 (Sprint 55.6 + 57.1 v2)** — 此 sprint 為 third fully-applied Day 0 三-prong 探勘 sprint;ROI evidence 累積 → Sprint 58+ 可考慮 evaluate 三-prong 為 standard practice

### 既有結構(Day 0 plan-time 探勘 grep 已驗證以下事實)

✅ **以下 layout 是 plan-time 已 verified via Day 0 三-prong 探勘**:

```
backend/src/api/v1/admin/                          # ✅ 56.1+56.2+56.3+57.3+57.4 既有
├── tenants.py                                     # ✅ existing (57.4 with GET "" list endpoint)
├── cost_summary.py                                # ✅ existing (56.3)
├── sla_reports.py                                 # ✅ existing (56.3)
└── feature_flags.py                               # ❌ NEW (US-1 — admin REST endpoint set)

backend/src/core/feature_flags.py                  # ✅ 56.1 existing
├── class FeatureFlagsService                      # ⚠️ MODIFY (US-1: add list_flags + clear_tenant_override)
│   ├── async is_enabled(flag, tenant_id)          # ✅ existing
│   ├── async set_tenant_override(...)             # ✅ existing
│   ├── async seed_defaults(...)                   # ✅ existing
│   ├── async list_flags()                         # ❌ NEW (US-1 — list all rows)
│   └── async clear_tenant_override(...)           # ❌ NEW (US-1 — pop from JSONB + audit)
├── DEFAULT_FLAGS dict                             # ✅ existing (4 baseline flags)
└── get_feature_flags_service / reset_*            # ✅ existing (singleton pattern)

backend/src/infrastructure/db/models/feature_flag.py  # ✅ 56.1 existing (no migration needed)
└── class FeatureFlag                              # ✅ existing (name PK + default_enabled + tenant_overrides JSONB + description)

backend/src/api/main.py                            # ⚠️ MODIFY (US-1: import + include admin_feature_flags_router)

backend/src/platform_layer/identity/auth.py        # ✅ 56.2 existing
└── require_admin_platform_role                    # ✅ existing reusable

frontend/src/                                      # ✅ 57.1 v2 + 57.3 + 57.4 既有 + Vitest setup
├── features/
│   ├── chat_v2/                                   # ✅ existing
│   ├── governance/                                # ✅ existing (53.5)
│   ├── cost-dashboard/                            # ✅ existing (57.1 v2)
│   ├── sla-dashboard/                             # ✅ existing (57.1 v2)
│   ├── tenant-settings/                           # ✅ existing (57.3)
│   ├── admin-tenants/                             # ✅ existing (57.4 — listTenants reusable for selector)
│   └── admin-feature-flags/                       # ❌ NEW (US-2 + US-3 + US-4)
│       ├── components/TenantSelector.tsx          # ❌ NEW (uses 57.4 listTenants — pattern reuse demo)
│       ├── components/FlagsTable.tsx              # ❌ NEW
│       ├── services/adminFeatureFlagsService.ts   # ❌ NEW (4 fetch methods)
│       ├── store/adminFeatureFlagsStore.ts        # ❌ NEW (Zustand)
│       └── types.ts                               # ❌ NEW (mirror US-1 Pydantic responses)
├── pages/
│   ├── chat-v2/index.tsx                          # ✅ existing
│   ├── governance/index.tsx                       # ✅ existing
│   ├── verification/index.tsx                     # ✅ existing
│   ├── cost-dashboard/index.tsx                   # ✅ existing
│   ├── sla-dashboard/index.tsx                    # ✅ existing
│   ├── tenant-settings/index.tsx                  # ✅ existing (57.3)
│   ├── admin-tenants/index.tsx                    # ✅ existing (57.4)
│   └── admin-feature-flags/index.tsx              # ❌ NEW (US-4)
└── App.tsx                                        # ⚠️ MODIFY (US-4: add 1 route + 1 nav link)

frontend/tests/                                     # ✅ existing (57.1 v2 + 57.3 + 57.4 setup)
├── e2e/
│   ├── chat/, governance/, cost_dashboard/, sla_dashboard/, tenant-settings/, admin_tenants/  # ✅ existing
│   └── admin_feature_flags/admin_feature_flags.spec.ts  # ❌ NEW (US-5)
└── unit/  (Vitest)                                 # ✅ existing (35 tests baseline)
```

### Sprint 57.4 retrospective Q5 對齊確認

Sprint 57.4 retrospective Q5 列出 Phase 57.x candidate scope:
- Onboarding self-serve wizard ⛔ defer pending backend self-serve API design
- **Feature flags admin UI** ✅ **此 sprint US-1~US-5(scope class `mixed-pattern-reuse` 0.40 candidate 1st application;consume 56.1 backend × pattern reuse from 57.4 admin-tenants infra)**
- Audit log frontend view ⛔ defer Phase 57.x
- Compliance partial GDPR (medium-backend) ⛔ defer Phase 57.x
- DR + WAL streaming (large multi-domain) ⛔ defer Phase 57.x
- SaaS Stage 2 Stripe + 月結 ⛔ defer Phase 57++
- AD-Cat10-VisualVerifier + Frontend-Panel ⛔ defer Phase 57.x Group F
- AD-Cat11-Multiturn / SSEEvents / ParentCtx ⛔ defer Phase 57.x Cat 11 bundle
- AD-CI-6 production launch ⛔ defer Phase 58 dedicated sprint

### V2 紀律 9 項對齊確認

1. **Server-Side First** ✅ Backend admin endpoints 完全 server-side;tenant_id 由 path param 接受 + JWT super-admin RBAC 驗證(super-admin override any tenant flag is legit per 56.2 RBAC pattern + audit chain logs the actor for traceability)
2. **LLM Provider Neutrality** ✅ 此 sprint 不動 LLM 鏈路
3. **CC Reference 不照搬** ✅ Feature flags admin 為標準 SaaS admin console pattern;plain fetch + Zustand stack 既有
4. **17.md Single-source** ✅ 此 sprint 不新增 cross-category interface;FeatureFlagItem + FeatureFlagListResponse + FeatureFlagResolvedItem 為 admin API 內部 DTO,non-cross-category;不影響 17.md;Pattern reuse from 57.4 listTenants 在 frontend `features/admin-tenants/services/` 已 export — 透過 import 即用,不重複定義
5. **11+1 範疇歸屬** ✅ US-1 §API admin layer + Core service(non-範疇 — `core/feature_flags.py` 跨 cross-cutting service)+ US-2~US-5 全 §Frontend(16-frontend-design.md);無範疇 1-12 backend module 變更;每檔案明確歸屬;無 AP-3
6. **04 anti-patterns** ✅ AP-3 範疇歸屬合規 / AP-4(Potemkin)— 全有實際 wire-up + Playwright e2e + backend pytest 強制驗證 / AP-6(Hybrid Bridge Debt)— 不為 Stage 2 預寫 abstraction;list 嚴格限制無 pagination(non-paginated since flag count rarely > 20 globally);不暴露 list-vs-detail 跨界 logic / AP-9(Verification)— Pydantic v2 query/body validation + Playwright + 422 invalid body test 強制 verify / AP-11(命名一致)— `admin-feature-flags` consistent naming(對齊 backend `admin/feature_flags.py` 路徑 + frontend `pages/admin-feature-flags/`)
7. **Sprint workflow** ✅ plan → checklist → Day 0 三-prong 探勘(Path + Content + Schema all DONE)→ code → progress → retro;本文件依 57.4 plan 結構鏡射(11 sections + metadata block / 5 days Day 0-4)
8. **File header convention** ✅ 所有 new 檔案含 file header docstring;modify 檔案加 Modification History entry;MHist 1-line max per AD-Lint-3 + char-count guidance per AD-Lint-MHist-Verbosity
9. **Multi-tenant rule** ✅ feature_flags 表為 registry 表(non-TenantScopedMixin per 56.1 baseline whitelist);US-1 admin endpoints 安全靠 require_admin_platform_role super-admin RBAC + audit chain on PATCH/DELETE;non-admin 401/403;RLS check 8 V2 lint check_rls_policies 不適用 feature_flags 表(已 whitelisted per 56.1 baseline)

---

## User Stories

### US-1: Backend admin/feature_flags.py + service-method extensions

**As** a SaaS platform super-admin
**I want** REST endpoints to list all feature flags + view resolved-per-tenant + set/clear per-tenant overrides
**So that** I can manage feature flag rollout per tenant from web UI without DB tools,with audit chain entry on every override change

**Acceptance**:
- NEW file `backend/src/api/v1/admin/feature_flags.py` (~200 LOC) with:
  - Pydantic `FeatureFlagItem`(name / default_enabled / description / override_count / created_at / updated_at)
  - Pydantic `FeatureFlagListResponse`(items: list[FeatureFlagItem] / total: int)
  - Pydantic `FeatureFlagResolvedItem`(flag_name / default_enabled / has_override / effective_value / description)
  - Pydantic `FeatureFlagResolvedListResponse`(items: list[FeatureFlagResolvedItem] / tenant_id: UUID)
  - Pydantic `FeatureFlagOverrideRequest`(enabled: bool;`extra="forbid"` rejects unknown fields)
  - Pydantic `FeatureFlagOverrideResponse`(flag_name / tenant_id / enabled)
  - `@router.get("", response_model=FeatureFlagListResponse)` — list all flags;deps `require_admin_platform_role`
  - `@router.get("/tenants/{tenant_id}", response_model=FeatureFlagResolvedListResponse)` — resolved view per tenant
  - `@router.patch("/{flag_name}/tenants/{tenant_id}", response_model=FeatureFlagOverrideResponse)` — set override + audit
  - `@router.delete("/{flag_name}/tenants/{tenant_id}", status_code=204)` — clear override + audit
  - `router = APIRouter(prefix="/admin/feature-flags", tags=["admin", "feature-flags"])`
  - Mount in `backend/src/api/main.py` via `admin_feature_flags_router` import + `app.include_router(admin_feature_flags_router, prefix="/api/v1")`
- MODIFY `backend/src/core/feature_flags.py` (+30 LOC):
  - Add `async def list_flags(self) -> list[FeatureFlag]:` — returns all rows ORDER BY name ASC
  - Add `async def clear_tenant_override(self, flag_name, tenant_id, actor_user_id) -> bool:` — pops `tenant_overrides[str(tenant_id)]` + audit(operation="feature_flag_override_cleared")+ flush + cache invalidation;returns True if was-present-now-cleared,False if no-op(was already absent)
- NEW test file `backend/tests/integration/api/test_admin_feature_flags.py` (~250 LOC) with 8-10 tests:
  - Test 1:`test_list_flags_happy` — admin auth → 200 + 4 baseline flags + override_count
  - Test 2:`test_resolved_for_tenant_no_overrides` — admin auth + new tenant → 200 + 4 items all has_override=False + effective_value=default
  - Test 3:`test_resolved_for_tenant_with_override` — seed override `thinking_enabled=False` for tenant → 200 + has_override=True + effective_value=False
  - Test 4:`test_set_override_happy_chain` — PATCH with `enabled=False` → 200 + audit chain entry with operation="feature_flag_override_set" + previous_override + new_value
  - Test 5:`test_set_override_unknown_flag_404` — PATCH unknown flag → 404
  - Test 6:`test_clear_override_happy_chain` — seed override → DELETE → 204 + audit chain entry with operation="feature_flag_override_cleared"
  - Test 7:`test_clear_override_no_op_204` — DELETE without prior override → 204(idempotent;service returns False;endpoint still 204)
  - Test 8:`test_401_unauth` — no JWT → 401 across all 4 endpoints
  - Test 9:`test_403_wrong_role` — non-admin JWT → 403 across all 4 endpoints
  - Test 10 (optional):`test_set_override_invalid_body` — PATCH with extra field → 422(extra="forbid")
- `python -m pytest backend/tests/integration/api/test_admin_feature_flags.py` ≥ 8 pass
- Backend pytest baseline 1598 → 1606+

### US-2: Frontend Admin Feature Flags Infrastructure

**As** the React app
**I want** per-feature folder skeleton for admin-feature-flags mirroring 57.4 admin-tenants pattern(infra reuse from 57.4)
**So that** Feature Flags Admin Console UI has consistent code organization,types match US-1 responses,store handles flags+resolved+saving lifecycle

**Acceptance**:
- `frontend/src/features/admin-feature-flags/` skeleton:components/ services/ store/ types.ts
- `types.ts`:mirror US-1 4 Pydantic models + Request body interface;import UUID type from existing pattern
- `adminFeatureFlagsService.ts`:`listFlags()` / `listResolvedForTenant(tenantId)` / `setOverride(flagName, tenantId, enabled)` / `clearOverride(flagName, tenantId)`;mirror `adminTenantsService.ts` plain fetch + `_handleResponse<T>` pattern;`API_BASE = "/api/v1/admin/feature-flags"`
- `adminFeatureFlagsStore.ts`:Zustand state(`flags / resolvedFlags / selectedTenantId / loading / loadError / saving / saveError`;actions:`setSelectedTenant / loadFlags / loadResolvedForTenant / setOverride / clearOverride / reset`);mirror tenant-settings store pattern(saving/saveError lifecycle for write operations)
- 3 Vitest unit tests:listFlags happy + setOverride PATCH body + store loadResolvedForTenant action

### US-3: Frontend Components (TenantSelector + FlagsTable)

**As** a SaaS platform super-admin
**I want** a tenant dropdown using 57.4 admin-tenants list + a flags table with override badges + Set/Clear action buttons
**So that** I can manage flag rollout per tenant with one screen

**Acceptance**:
- `frontend/src/features/admin-feature-flags/components/TenantSelector.tsx`:
  - Uses `listTenants` from `../../admin-tenants/services/adminTenantsService`(cross-feature import — pattern reuse demo per 17.md spirit)
  - Calls `listTenants({ limit: 200, offset: 0 })` on mount(no filter — show all up to 200)
  - Native HTML `<select>` with `<option value="">— Select tenant —</option>` + dynamic options from response
  - onChange → store `setSelectedTenant(tenantId)` → triggers loadResolvedForTenant
  - Loading state:disabled + "Loading tenants..." placeholder
  - Error state:disabled + error text below
- `frontend/src/features/admin-feature-flags/components/FlagsTable.tsx`:
  - Columns: Flag Name (monospace) / Description / Default (badge: True green / False gray) / Override (badge: True/False blue if has_override / "—" gray if no override) / Effective Value (badge: True green / False gray) / Actions (Set Override Off button if effective=True OR Set Override On button if effective=False;Clear Override button always visible if has_override=True)
  - Empty state:若 selectedTenantId === null → "Select a tenant to view feature flags" 提示
  - Empty state:若 selectedTenantId set 但 resolvedFlags.length === 0 → "No flags loaded;try reload" + Reload button
  - Loading skeleton:4 placeholder rows when `loading === true`
  - Saving overlay:row-level disabled + "Saving..." text on the actively-saving row
- 4 Vitest unit tests:TenantSelector renders dropdown options + onChange triggers setSelectedTenant + FlagsTable empty state(no tenant)+ FlagsTable renders rows with effective + override badges

### US-4: Frontend Page + Routing

**As** the V2 sprint executor
**I want** App.tsx route + Home nav + page wrapper combining TenantSelector + FlagsTable
**So that** Feature Flags Admin Console is reachable from app

**Acceptance**:
- `frontend/src/pages/admin-feature-flags/index.tsx` page wrapper:
  - Layout:TenantSelector top + FlagsTable middle + Saving status bar bottom(shows last save timestamp + saveError if any)
  - On mount:loadFlags()(load all flags so we know description/default for table even before tenant selected)
  - On selectedTenantId change:loadResolvedForTenant(tenantId)
- `frontend/src/App.tsx`:add `<Route path="/admin-feature-flags" element={<AdminFeatureFlagsPage />} />`
- Home page nav:add `<Link to="/admin-feature-flags">Feature Flags Admin Console</Link>` — always visible per 57.1 D10 Option C
- 1-2 Vitest unit tests:page mount → loadFlags called + tenant select → loadResolvedForTenant called

### US-5: Playwright E2E + Closeout Ceremony

**As** the V2 sprint executor
**I want** Playwright e2e tests + retrospective + AD-Sprint-Plan-6 1st application calibration verify
**So that** Sprint 57.5 closes Phase 57+ SaaS Frontend 4/N with full audit trail

**Acceptance**:
- `frontend/tests/e2e/admin_feature_flags/admin_feature_flags.spec.ts`(4 cases via `page.route()` browser-layer mock per 57.1 v2 D19 + 57.3 D13 + 57.4 D14 pattern):
  - happy path:admin auth → load `/admin-feature-flags` → assert TenantSelector shows options + initially empty FlagsTable with prompt
  - select tenant → assert second mocked GET `/tenants/{id}` triggered → table shows 4 rows with badges
  - set override:click "Set Override Off" on `thinking_enabled` → assert PATCH triggered with `enabled=false` body → table refreshes with Override badge "False"
  - clear override:click "Clear Override" on row with override → assert DELETE triggered → table refreshes with Override badge "—"
- retrospective.md(6 必答 + AD-Sprint-Plan-6 1st application calibration verify + Phase 57.x next-sprint candidates Q5 + Day 0 三-prong third fully-applied sprint observations)
- Memory snapshot `memory/project_phase57_5_feature_flags_admin.md`
- SITUATION-V2 §9 + CLAUDE.md sync to **Phase 57+ SaaS Frontend 4/N (Sprint 57.5 closed — Feature Flags Admin Console bundle)**

---

## Technical Specifications

### Backend Endpoint Pattern (mirror 57.4 admin/tenants.py)

```python
# backend/src/api/v1/admin/feature_flags.py — NEW file

class FeatureFlagItem(BaseModel):
    """Lightweight item for feature flag list view."""
    name: str
    default_enabled: bool
    description: str | None
    override_count: int  # len(tenant_overrides)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=False)


class FeatureFlagListResponse(BaseModel):
    items: list[FeatureFlagItem]
    total: int


class FeatureFlagResolvedItem(BaseModel):
    """Resolved view for one (flag, tenant) pair."""
    flag_name: str
    default_enabled: bool
    has_override: bool
    effective_value: bool
    description: str | None


class FeatureFlagResolvedListResponse(BaseModel):
    items: list[FeatureFlagResolvedItem]
    tenant_id: UUID


class FeatureFlagOverrideRequest(BaseModel):
    enabled: bool

    model_config = ConfigDict(extra="forbid")


class FeatureFlagOverrideResponse(BaseModel):
    flag_name: str
    tenant_id: UUID
    enabled: bool


router = APIRouter(prefix="/admin/feature-flags", tags=["admin", "feature-flags"])


@router.get("", response_model=FeatureFlagListResponse,
            dependencies=[Depends(require_admin_platform_role)])
async def list_feature_flags(
    db: AsyncSession = Depends(get_db_session),
) -> FeatureFlagListResponse:
    service = get_feature_flags_service(db)
    flags = await service.list_flags()
    items = [
        FeatureFlagItem(
            name=f.name,
            default_enabled=f.default_enabled,
            description=f.description,
            override_count=len(f.tenant_overrides),
            created_at=f.created_at,
            updated_at=f.updated_at,
        )
        for f in flags
    ]
    return FeatureFlagListResponse(items=items, total=len(items))


@router.get("/tenants/{tenant_id}", response_model=FeatureFlagResolvedListResponse,
            dependencies=[Depends(require_admin_platform_role)])
async def list_resolved_for_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> FeatureFlagResolvedListResponse: ...


@router.patch("/{flag_name}/tenants/{tenant_id}",
              response_model=FeatureFlagOverrideResponse,
              dependencies=[Depends(require_admin_platform_role)])
async def set_override(
    flag_name: str,
    tenant_id: UUID,
    body: FeatureFlagOverrideRequest,
    admin_user_id: UUID = Depends(get_current_admin_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> FeatureFlagOverrideResponse: ...


@router.delete("/{flag_name}/tenants/{tenant_id}", status_code=204,
               dependencies=[Depends(require_admin_platform_role)])
async def clear_override(
    flag_name: str,
    tenant_id: UUID,
    admin_user_id: UUID = Depends(get_current_admin_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> None: ...
```

### Service Method Extensions (mirror existing set_tenant_override)

```python
# backend/src/core/feature_flags.py — modify existing class

async def list_flags(self) -> list[FeatureFlag]:
    """Return all flag rows ORDER BY name ASC."""
    stmt = select(FeatureFlag).order_by(FeatureFlag.name)
    result = await self._session.execute(stmt)
    return list(result.scalars().all())


async def clear_tenant_override(
    self,
    flag_name: str,
    tenant_id: UUID,
    actor_user_id: UUID | None = None,
) -> bool:
    """Pop per-tenant override + audit. Returns True if cleared, False if no-op."""
    flag = await self._load(flag_name)
    if flag is None:
        raise FeatureFlagNotFoundError(
            f"flag '{flag_name}' not in registry; cannot clear unknown flag"
        )
    previous = flag.tenant_overrides.get(str(tenant_id))
    if previous is None:
        return False  # no-op (idempotent for endpoint 204)
    new_overrides = dict(flag.tenant_overrides)
    new_overrides.pop(str(tenant_id))
    flag.tenant_overrides = new_overrides
    await append_audit(
        self._session,
        tenant_id=tenant_id,
        user_id=actor_user_id,
        operation="feature_flag_override_cleared",
        resource_type="feature_flag",
        resource_id=flag_name,
        operation_data={
            "flag_name": flag_name,
            "tenant_id": str(tenant_id),
            "previous_override": previous,
        },
        operation_result="success",
    )
    await self._session.flush()
    keys_to_drop = [k for k in self._resolved_cache if k[0] == flag_name]
    for k in keys_to_drop:
        self._resolved_cache.pop(k, None)
    return True
```

### Service Pattern (mirror 57.4 adminTenantsService.ts)

```typescript
// frontend/src/features/admin-feature-flags/services/adminFeatureFlagsService.ts

const API_BASE = "/api/v1/admin/feature-flags";

async function _handleResponse<T>(response: Response): Promise<T> { /* mirror 57.4 */ }

export async function listFlags(): Promise<FeatureFlagListResponse> {
  const response = await fetch(`${API_BASE}`, { credentials: "include" });
  return _handleResponse<FeatureFlagListResponse>(response);
}

export async function listResolvedForTenant(
  tenantId: string,
): Promise<FeatureFlagResolvedListResponse> {
  const response = await fetch(`${API_BASE}/tenants/${tenantId}`, { credentials: "include" });
  return _handleResponse<FeatureFlagResolvedListResponse>(response);
}

export async function setOverride(
  flagName: string,
  tenantId: string,
  enabled: boolean,
): Promise<FeatureFlagOverrideResponse> {
  const response = await fetch(
    `${API_BASE}/${flagName}/tenants/${tenantId}`,
    {
      method: "PATCH",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    },
  );
  return _handleResponse<FeatureFlagOverrideResponse>(response);
}

export async function clearOverride(flagName: string, tenantId: string): Promise<void> {
  const response = await fetch(
    `${API_BASE}/${flagName}/tenants/${tenantId}`,
    { method: "DELETE", credentials: "include" },
  );
  if (!response.ok && response.status !== 204) {
    throw new Error(`HTTP ${response.status}`);
  }
}
```

### Risk Class A/B/C — A retired, B+C still N/A

- Risk Class A: paths-filter retired by 55.6 Option Z;此 sprint 不適用
- Risk Class B: cross-platform mypy unused-ignore — 此 sprint 涉及 backend(US-1);若 import drift(`from sqlalchemy import select` 既有 56.x 用過;低概率)→ 套 `# type: ignore[import-not-found, unused-ignore]` 雙 code per code-quality.md;mitigation 於 Day 1 sanity check 階段
- Risk Class C: module-level singleton — `core/feature_flags.py` has `get_feature_flags_service / reset_feature_flags_service` 既有 56.1 baseline;57.4 + 53.6 integration suite already 含 autouse `_reset_module_singletons` fixture(per testing.md §Module-level Singleton Reset Pattern);Day 1 sanity check verify

### Day 0 三-prong 探勘 v3 capture (third fully-applied sprint)

Sprint 57.5 是 Day 0 三-prong 探勘 third fully-applied sprint(Path + Content + Schema all attempted;Schema verdict = N/A 但 attempt 完成):
- Prong 1 Path Verify ✅ done — 5 backend file existence checks + 6 frontend folder existence checks
- Prong 2 Content Verify ✅ done — 6 backend assertion grep checks(D1 RED catch — `admin/feature_flags.py` 不存在 / D2 GAP — `FeatureFlagsService.list_flags` 不存在 / D3 GAP — `FeatureFlagsService.clear_tenant_override` 不存在)
- Prong 3 Schema Verify ✅ N/A — 無新 DB schema/migration;但 attempt 完成(per fold-in spirit;Alembic 0015 + FeatureFlag ORM 6 fields verified for list / resolved / override CRUD compatibility)

**ROI:** D1+D2+D3 catch via Prong 1+2 (~40 min cost) prevented 6-10 hr Day 1+ rework(類比 57.3+57.4 Day 0 catch ROI);**ROI ≈ 9-15×**;Sprint 57.5 為 third fully-applied 三-prong sprint;ROI evidence 累積 → Sprint 58+ 可考慮 evaluate 三-prong 為 standard practice

---

## Acceptance Criteria

### Sprint-Wide

- [ ] V2 主進度 22/22 (100%) 不變;Phase 56-58 SaaS Stage 1 backend 3/3 不變;Phase 57+ Frontend SaaS 3/N → 4/N
- [ ] All 8 V2 lints green (新 backend code 不違反 LLM SDK / promptbuilder / sole_mutator / RLS gaps lints)
- [ ] Backend pytest baseline 1598 → 1606+ (≥+8 from US-1)
- [ ] Backend mypy --strict 0 errors (1 NEW source file `admin/feature_flags.py` + 1 modify `core/feature_flags.py` → 296 source files)
- [ ] Backend LLM SDK leak: 0 不變
- [ ] Anti-pattern checklist 11 項對齊
- [ ] 5 active CI checks green(含 Frontend E2E chromium headless per 53.7 baseline)
- [ ] Frontend `npm run lint && npm run build` clean
- [ ] Frontend Vitest ≥+9 new tests pass(3 US-2 + 4 US-3 + 1-2 US-4)
- [ ] Playwright e2e ≥4 tests pass(happy + select-tenant + set + clear + empty)
- [ ] NEW AD-Sprint-Plan-6-Intermediate `mixed-pattern-reuse-intermediate` 0.50 1st application captured + verdict logged in retro Q2
- [ ] D1 RED + D2+D3 GAP findings plan-time closed(US-1 backend admin endpoints + 2 service methods production-ready)
- [ ] Day 0 三-prong 探勘 third fully-applied sprint observations documented in retro Q3

### Per-User-Story

詳見 §User Stories acceptance per US.

---

## Day-by-Day Plan

### Day 0 — Setup + Day-0 三-prong 探勘 + Pre-flight Verify

- 0.1 Branch + plan + checklist commit
- 0.2 Day-0 三-prong 探勘(per AD-Plan-3 + AD-Plan-4 fold-in promoted)— **Prong 1 Path Verify**:`features/admin-feature-flags/` + `pages/admin-feature-flags/` + `tests/e2e/admin_feature_flags/` 不存在(expect)/ `core/feature_flags.py` exists / `infrastructure/db/models/feature_flag.py` exists / `migrations/versions/0015_feature_flags.py` exists / `admin/feature_flags.py` 不存在(expect — D1 RED);**Prong 2 Content Verify**:`core/feature_flags.py` 確認 `is_enabled` + `set_tenant_override` + `seed_defaults` 存在 / 確認 `list_flags` + `clear_tenant_override` **不存在**(D2+D3 GAP — already user-confirmed Option A pre-emptive bundle);`api/main.py` 檢查 admin router import pattern;`require_admin_platform_role` exists at auth.py:140;**Prong 3 Schema Verify**:N/A 此 sprint(無新 DB schema/migration;但 attempt 完成 per fold-in spirit;FeatureFlag ORM 6 fields all reusable for list/resolved/override CRUD)
- 0.3 Calibration multiplier pre-read(`mixed-pattern-reuse-intermediate` **0.50** intermediate candidate 1st application — between AD-Sprint-Plan-6 proposed 0.40 + mixed 0.60 baseline;若 ratio in [0.85, 1.20] → strong evidence to promote 0.50 as new matrix class;若 < 0.85 → 證據降至 0.40-0.45;若 > 1.20 → revert to `mixed` 0.60 + log new AD)
- 0.4 Pre-flight verify(backend pytest baseline 1598 / 8 V2 lints baseline / mypy baseline / LLM SDK leak baseline / frontend Vitest 35 + Playwright 23 + Vite build 75 modules / 209.11 kB)
- 0.5 Day 0 progress.md commit + push;catalogue D-findings(D1 RED + D2+D3 GAP closed by Option A pre-emptive bundle;D4-D8 informational);若 scope shift > 20% revise plan §Risks per AD-Plan-1 audit-trail

### Day 1 — US-1 Backend admin endpoints + service-method extensions

- 1.1 MODIFY `core/feature_flags.py`:add `async def list_flags(self) -> list[FeatureFlag]` + `async def clear_tenant_override(self, ...) -> bool`(audit chain + cache invalidation;mirror set_tenant_override pattern)
- 1.2 NEW `api/v1/admin/feature_flags.py`:6 Pydantic models + 4 endpoints + router
- 1.3 MODIFY `api/main.py`:import + include admin_feature_flags_router
- 1.4 NEW test file `backend/tests/integration/api/test_admin_feature_flags.py`(8-10 tests:list_happy / resolved_no_overrides / resolved_with_override / set_chain / set_unknown_404 / clear_chain / clear_no_op_204 / 401 / 403 / invalid_body_422)
- 1.5 Day 1 sanity checks:`pytest test_admin_feature_flags.py` pass / `mypy --strict admin/feature_flags.py + core/feature_flags.py` clean / 8 V2 lints unchanged
- 1.6 Day 1 commit + push + progress.md

### Day 2 — US-2 Frontend Infra (types + service + store)

- 2.1 `frontend/src/features/admin-feature-flags/` skeleton(components/ services/ store/ types.ts)
- 2.2 `types.ts` mirror US-1 4 Pydantic models + Request body interface
- 2.3 `adminFeatureFlagsService.ts` 4 fetch methods(listFlags / listResolvedForTenant / setOverride PATCH / clearOverride DELETE)+ `_handleResponse<T>` helper
- 2.4 `adminFeatureFlagsStore.ts` Zustand store(flags + resolvedFlags + selectedTenantId + loading + saving 狀態 + 6 actions)
- 2.5 3 Vitest unit tests US-2(listFlags happy + setOverride PATCH body + store loadResolvedForTenant action)
- 2.6 Day 2 sanity checks:`npm run lint && npm run build` + Vitest pass
- 2.7 Day 2 commit + push + progress.md

### Day 3 — US-3 + US-4 Frontend Components + Page Layout

- 3.1 `TenantSelector.tsx`(uses 57.4 listTenants — cross-feature import demo + onChange triggers store.setSelectedTenant)
- 3.2 `FlagsTable.tsx`(rows + 3 badges + Set/Clear action buttons + empty states + loading skeleton + saving overlay)
- 3.3 `pages/admin-feature-flags/index.tsx` page wrapper(layout TenantSelector top + FlagsTable middle + Saving status bar bottom + on mount loadFlags + on tenant change loadResolvedForTenant)
- 3.4 5 Vitest unit tests(4 US-3 TenantSelector + FlagsTable + 1-2 US-4 page mount + tenant select)
- 3.5 Day 3 sanity checks:`npm run lint && npm run build` + Vitest pass
- 3.6 Day 3 commit + push + progress.md

### Day 4 — US-5 Routing + Playwright E2E + Closeout Ceremony

- 4.1 App.tsx route `/admin-feature-flags` + Home nav `<Link>`(always visible per 57.1 D10 Option C)
- 4.2 Playwright e2e `admin_feature_flags.spec.ts`(4 cases:happy + select-tenant + set + clear)
- 4.3 Final pytest + lint + leak verify(backend 1598 → 1606+ / mypy 0 / 8 V2 lints / LLM SDK 0 / frontend lint+build + Vitest 35 → 44+ + Playwright 23 → 27+)
- 4.4 Retrospective.md(6 必答 + AD-Sprint-Plan-6 1st application calibration verify + Day 0 三-prong third fully-applied sprint observations + Phase 57.x next-sprint candidates Q5)
- 4.5 Memory snapshot `memory/project_phase57_5_feature_flags_admin.md` + MEMORY.md index update
- 4.6 Open PR + CI green + solo-dev merge to main
- 4.7 Closeout PR(SITUATION-V2 §9 + CLAUDE.md sync to **Phase 57+ SaaS Frontend 4/N (Sprint 57.5 closed — Feature Flags Admin Console bundle)**)

---

## File Change List

| File | Status | Lines (est) |
|------|--------|-------------|
| `backend/src/api/v1/admin/feature_flags.py` | NEW | ~200 (6 Pydantic + 4 endpoints + router) |
| `backend/src/core/feature_flags.py` | MODIFIED | +35 (list_flags + clear_tenant_override + MHist) |
| `backend/src/api/main.py` | MODIFIED | +2 (import + include_router) |
| `backend/tests/integration/api/test_admin_feature_flags.py` | NEW | ~250 |
| `frontend/src/features/admin-feature-flags/types.ts` | NEW | ~50 |
| `frontend/src/features/admin-feature-flags/services/adminFeatureFlagsService.ts` | NEW | ~75 |
| `frontend/src/features/admin-feature-flags/store/adminFeatureFlagsStore.ts` | NEW | ~110 |
| `frontend/src/features/admin-feature-flags/components/TenantSelector.tsx` | NEW | ~70 |
| `frontend/src/features/admin-feature-flags/components/FlagsTable.tsx` | NEW | ~160 |
| `frontend/src/pages/admin-feature-flags/index.tsx` | NEW | ~70 |
| `frontend/src/App.tsx` | MODIFIED | +6 (1 Route + 1 Link) |
| `frontend/tests/e2e/admin_feature_flags/admin_feature_flags.spec.ts` | NEW | ~160 |
| Vitest unit tests (~9 new across 5 files) | NEW | ~320 |
| `docs/.../sprint-57-5/{progress,retrospective}.md` | NEW | ~600 |
| `memory/project_phase57_5_feature_flags_admin.md` | NEW | ~60 |

**Total**: ~750 source LOC + ~570 test LOC + ~660 docs LOC

---

## Dependencies & Risks

### Dependencies (must exist before code starts)

- ✅ Phase 56.1 backend `FeatureFlag` ORM (feature_flag.py) — Day 0 verified
- ✅ Phase 56.1 backend `FeatureFlagsService` with `is_enabled` + `set_tenant_override` + `seed_defaults` — Day 0 verified
- ✅ Phase 56.1 Alembic 0015 + 4 baseline default flags seeded via `seed_defaults` — Day 0 verified
- ✅ Phase 56.2 backend `require_admin_platform_role` auth dep (auth.py:140) — Day 0 verified
- ✅ Phase 56.2 backend `get_current_admin_user_id` (auth.py) — verify Day 0 (audit chain actor capture)
- ✅ Phase 57.4 backend `admin/tenants.py` GET `""` list endpoint (used as router pattern reference) — Day 0 verified
- ✅ Phase 57.4 frontend `admin-tenants/services/adminTenantsService.ts` exports `listTenants` — Day 0 verified(reused for TenantSelector dropdown)
- ✅ Phase 57.1 v2 frontend Vitest setup — Day 0 verified
- ✅ Phase 53.6 frontend Playwright auth fixture pattern reusable — Day 0 verified

### Risk Classes (per sprint-workflow.md §Common Risk Classes)

**Risk Class A (paths-filter vs required_status_checks)**: 已 closed by 55.6 Option Z (paths-filter retired 永久);此 sprint 不適用。

**Risk Class B (cross-platform mypy unused-ignore)**: 低概率 — 此 sprint backend 全用既有依賴(SQLAlchemy 2.x async / FastAPI / Pydantic v2 / 56.x audit_helper);若新 import 在 Linux runner drift → 套 `# type: ignore[import-not-found, unused-ignore]` 雙 code per code-quality.md;mitigation 於 Day 1 sanity check 階段。

**Risk Class C (module-level singleton across event loops)**: 中概率 — `core/feature_flags.py` has module-level singleton via `get_feature_flags_service / reset_feature_flags_service`;57.4+53.6 integration suite already 含 autouse `_reset_module_singletons` fixture(per testing.md §Module-level Singleton Reset Pattern;Sprint 53.6 Day 4 ServiceFactory consolidation pattern reusable);Day 1 sanity check 階段 verify 0 cascade failures。

### Day 0 三-prong 探勘 D-findings v3 (catalogued during Day 0)

**D1** 🔴 RED — `backend/src/api/v1/admin/feature_flags.py` 完全不存在(0 admin REST endpoints for feature flags;類比 57.4 D1 RED finding)。**Closed by Option A pre-emptive bundle**(user-approved 2026-05-07 — bundle 1 backend admin router file + 1 frontend Feature Flags Admin Console page 解決真正 backend gap)。Implication:此 sprint US-1 backend scope ~3-4 hr;multiplier `mixed-pattern-reuse-intermediate` 0.50 1st application(promotion-test sprint per NEW AD-Sprint-Plan-6-Intermediate;between AD-Sprint-Plan-6 proposed 0.40 + mixed 0.60 baseline)。

**D2** 🔴 RED — `FeatureFlagsService.list_flags()` method 不存在;為 admin GET list endpoint 必要 service method。**Closed by Option A pre-emptive bundle**(同 D1)。Implication:US-1 修改 `core/feature_flags.py` 加 ~10 LOC list_flags + reuse `select(FeatureFlag).order_by(name)` pattern。

**D3** 🔴 RED — `FeatureFlagsService.clear_tenant_override()` method 不存在;為 admin DELETE override endpoint 必要 service method;current set_tenant_override 只能 set True/False,不能 pop from JSONB。**Closed by Option A pre-emptive bundle**(同 D1)。Implication:US-1 修改 `core/feature_flags.py` 加 ~25 LOC clear_tenant_override(mirror set_tenant_override audit chain pattern;new audit operation="feature_flag_override_cleared");idempotent return bool(was_present)pattern for endpoint 204 idempotent。

**D4** 🟢 GREEN — `require_admin_platform_role` exists at `auth.py:140`(56.2 RBAC pattern reused by 57.3 + 57.4)。Implication:US-1 4 endpoints reuse;auth pattern 一致無需新增;`get_current_admin_user_id` for audit chain actor capture 可從 `auth.py` import(同 57.3 admin/tenants.py PATCH pattern)。

**D5** 🟢 GREEN — Phase 57.4 frontend `admin-tenants/services/adminTenantsService.ts` exports `listTenants` — Day 0 verified;TenantSelector.tsx 直接 import 即用。Implication:US-3 TenantSelector ~30 min(pattern reuse 高);demonstrate cross-feature import per 17.md spirit + AP-11 命名一致;**這就是 mixed-pattern-reuse-intermediate 0.50 multiplier 可介於 0.40 與 0.60 之間的根本理由**(承認 pattern reuse 但保留 conservative buffer)。

**D6** 🟢 GREEN — Phase 57.4 frontend `admin-tenants/{types,services,store}/` skeleton pattern reusable for adminFeatureFlagsStore;Zustand + plain fetch + saving/saveError state pattern from 57.3 tenant-settings(write operations)+ 57.4 admin-tenants(read operations)結合 saving lifecycle(set + clear actions)。Implication:US-2 store 開發 ~40-50 min(pattern reuse 高);無新概念;saving + saveError 模式 from 57.3 PATCH + 57.4 list combined。

**D7** 🟠 YELLOW — clear_tenant_override 的 idempotent 行為 + endpoint 204 status — endpoint 即使 service returns False(no-op)still 204(idempotent);避免 client retry 收到 404 confusion;but the service-level distinction matters for unit test(test_clear_no_op_204 specifically asserts service returns False but endpoint 204)。Implication:Day 1 unit test 須明確分開 service-level + endpoint-level idempotent semantics。

**D8** 🟠 YELLOW — Saving overlay UX(US-3 FlagsTable)— row-level "Saving..." 而非 page-level;如果 admin 同時 toggle 兩 row(rapid clicks)→ 第二 click 應 disabled until 第一 PATCH 完成 OR queue;為避免 over-engineer,Day 3 first-thing 確認 UX:simplest = single-row saving lock(其他 row 暫不 disabled,store-level saving lock 只擋 same-row 重複 click)。Implication:Day 3 確認 UX 設計(Option Simple = single-row lock;Option Strict = page-level lock during any save);**Default Option Simple** 因為 admin 通常逐 flag 操作,row-level lock 足夠。

**Cumulative scope shift** = 0%(D1+D2+D3 RED 全已 user-confirmed Option A pre-emptive bundle 2026-05-07,Day 0 plan-time catch;non Day-1 surprise)。`mixed-pattern-reuse-intermediate` 0.50 1st application;**~8 hr commit** for ~16 hr bottom-up est。< 50% threshold per AD-Plan-1(若 > 50% 則 abort);user-confirmed Option A + 0.50 multiplier 2026-05-07 → 繼續 Day 1+;no plan re-version required mid-sprint。

### Sprint-specific Risks

| Risk | Mitigation |
|------|-----------|
| 4 baseline flags + future flags 數量增長 → list endpoint 需 pagination | 此 sprint 範圍內 flags 通常 < 20 globally(global registry,not per-tenant);non-paginated;Phase 58+ 若 flags > 50 再評估加 pagination(類比 57.4 admin tenants list pagination pattern reusable when needed) |
| TenantSelector 載入 200 tenants 過多 → dropdown 操作不便 | 此 sprint 範圍內 tenants 通常 < 100 rows(per-instance SaaS);Day 0 假設;若用戶反映 → Phase 58+ 加 search input + on-demand load(類比 57.4 admin-tenants 內部 search;同樣 reusable) |
| Vitest unit test 對 Zustand store async 的測試需要 `vi.mocked` adminFeatureFlagsService methods | 既有 57.4 admin-tenants store 測試 pattern reusable;Day 2 直接 follow |
| Frontend bundle size 增量(~80 modules vs 75 baseline) | 控制 +5-6 modules;< 5% size 增加;Vite tree-shaking 應自動處理 |
| NEW AD-Sprint-Plan-6-Intermediate 0.50 1st application — 若 ratio outside band → 需 revert AD + log new AD | Day 4 retro Q2 explicitly verify;若 ratio in [0.85, 1.20] → 0.50 promoted as new matrix class;若 ratio < 0.85 → 進一步降至 0.40-0.45 candidate(re-evaluate AD-Sprint-Plan-6 original 0.40 proposal);若 ratio > 1.20 → revert to `mixed` 0.60 baseline + log new AD |

---

## Definition of Done

詳見 §Acceptance Criteria — Sprint-Wide。

---

## References

- 16-frontend-design.md §Feature Flags Admin Console (per Phase 57+ candidate scope)
- 56.1 Feature Flags backend ship (FeatureFlagsService + FeatureFlag ORM + Alembic 0015 + 4 baseline default flags)
- 56.2 RBAC pattern (require_admin_platform_role + get_current_admin_user_id)
- 57.3 admin tenants single CRUD (audit chain on PATCH pattern reusable for set/clear override)
- 57.4 admin tenants list bundle (router + Pydantic + 8 V2 lints + listTenants frontend service reusable)
- 53.5/53.6 Frontend governance + Playwright e2e patterns
- 57.1 v2 frontend cost-dashboard + sla-dashboard infra patterns
- NEW AD-Sprint-Plan-6-Intermediate `mixed-pattern-reuse-intermediate` 0.50 multiplier (1st application — promotion-test sprint;between AD-Sprint-Plan-6 proposed 0.40 + mixed 0.60 baseline)
- AD-Plan-3 + AD-Plan-4 sprint-workflow.md §Step 2.5 Prong 2 + 3 (promoted Sprint 55.6 + 57.1 v2 fold-in)
- .claude/rules/sprint-workflow.md §Common Risk Classes
- .claude/rules/testing.md §Module-level Singleton Reset Pattern (FeatureFlagsService singleton)
- .claude/rules/multi-tenant-data.md (registry table exception — feature_flags whitelisted)
- Sprint 57.4 plan + checklist (format template — 11 sections + metadata block / 5 days Day 0-4)

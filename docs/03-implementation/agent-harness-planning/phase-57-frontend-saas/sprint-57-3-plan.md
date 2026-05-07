# Sprint 57.3 — Phase 57+ SaaS Frontend 2nd: Tenant Settings Bundle (backend CRUD + frontend UI)

> **Sprint Type**: Phase 57+ second sprint — mixed scope class (backend + frontend bundle) for first admin tenant CRUD UX over 56.1 lifecycle stack;closes Day 0 D1 RED finding(backend admin tenants.py 無 GET/PUT/PATCH for entity);3rd application of `mixed` 0.60 multiplier
> **Owner Categories**: §Frontend (16-frontend-design.md §Tenant Settings) / §Backend Admin API (extends 56.1 admin tenants endpoint set) / consumes 56.1 Tenant ORM + lifecycle + 56.2 RBAC + 53.5/53.6 audit chain
> **Phase**: 57 (Frontend SaaS — 2/N sprint;follow-on candidates: Admin tenant console list / Onboarding self-serve wizard (still requires backend re-design) / DR / GDPR;rolling planning per .claude/rules/sprint-workflow.md)
> **Workload**: 5 days (Day 0-4); bottom-up est ~17 hr → calibrated commit **~10 hr** (multiplier **0.60** per AD-Sprint-Plan-4 scope-class matrix `mixed` 3rd application;mixed 2-data-point mean **1.09** ✅ in band → KEEP 0.60 mid-band;若 ratio outside [0.85, 1.20] → AD-Sprint-Plan-N+1 logged)
> **Branch**: `feature/sprint-57-3-tenant-settings-bundle`
> **Plan Authority**: This document (per CLAUDE.md §Sprint Execution Workflow)
> **Roadmap Source**: 16-frontend-design.md §Tenant Settings + 56.1 admin tenants endpoint set + Sprint 57.2 retrospective Q5 (Phase 57+ candidate scope user-approved 2026-05-07) + Sprint 57.3 v1 Day 0 探勘 Option B pivot user-approved 2026-05-07 (D1 RED — backend admin tenants.py missing GET/PUT/PATCH for entity)
> **AD logging (sub-scope)**: AD-Sprint-Plan-4 scope-class matrix `mixed` 3rd application(2-data-point mean 1.09 KEEP 0.60 mid-band); Day 0 兩-prong 探勘 Prong 3 Schema Verify N/A this sprint(無新 DB schema/migration — 純 endpoint 暴露 + frontend UI)

---

## Sprint Goal

Open the **first admin tenant CRUD UX surface** for Phase 57+ SaaS Frontend by bundling 2 backend admin endpoints + 1 frontend Tenant Settings page in a single mixed-scope sprint:

- **US-1**: Backend `GET /admin/tenants/{tenant_id}` — read full tenant entity(id / code / display_name / state / plan / provisioning_progress / onboarding_progress / meta_data / created_at / updated_at);require_admin_platform_role per 56.2 RBAC pattern;reuses `_load_tenant_or_404` helper from `tenants.py:167`;Pydantic TenantResponse mirrors ORM fields read-only;5-7 unit + integration tests
- **US-2**: Backend `PATCH /admin/tenants/{tenant_id}` — partial update for **display_name** + **meta_data**(JSONB)只;immutable fields(id / code / state / plan / created_at)拒絕(422 if attempted);state changes 必走 TenantLifecycle.transition(per VALID_TRANSITIONS in lifecycle.py:63);audit chain entry per 53.5/53.6 `append_audit` pattern with action="tenant_settings_updated";5-7 unit + integration tests
- **US-3**: Frontend `frontend/src/features/tenant-settings/` infra — service + store + types mirroring cost-dashboard pattern(plain fetch + `_handleResponse<T>` + Zustand;per v1 D4+D6);types.ts mirror 56.1 TenantState + TenantPlan enum + 57.3 US-1 TenantResponse Pydantic;3 Vitest unit tests
- **US-4**: Frontend `pages/tenant-settings/index.tsx` + `features/tenant-settings/components/TenantSettingsView.tsx`(read view: code / display_name / state / plan / created_at / progress) + `TenantSettingsEditForm.tsx`(edit form: display_name text input + meta_data JSON textarea with parse validate);loading + error UX mirror governance pattern;optimistic update + invalidate-on-error pattern;3 Vitest unit tests(form submit / JSON validate / store action)
- **US-5**: Routing + Playwright e2e + closeout — App.tsx 加 `/tenant-settings/*` wildcard route + Home nav link(always visible per 57.1 D10 Option C);2 Playwright e2e specs(`tenant_settings_view.spec.ts` happy + error;`tenant_settings_edit.spec.ts` happy + 422 immutable field error path);retrospective(6 必答 + AD-Sprint-Plan-4 mixed 3rd app verify + Phase 57+ next-sprint candidates Q5)+ memory snapshot + SITUATION-V2 + CLAUDE.md sync

Sprint 結束後:
- (a) **Tenant Settings 主流量 functional** — admin user 可 browse `/tenant-settings/{tenant_id}` → 看 tenant 全欄位 → 編輯 display_name + meta_data → 儲存後 backend audit log 寫入 + UI 即時更新
- (b) **Backend admin tenants.py 完整 CRUD R+U** — GET + PATCH 補齐 56.1 missing surface;為後續 Admin tenant console / Onboarding self-serve API 鋪路
- (c) **AD-Sprint-Plan-4 `mixed` 3rd-data-point** — 2-data-point mean 1.09 in band;若 ratio in band → 3-data-point window 形成 mid-band 穩定信號(若連續 3 in-band 可考慮 evaluate band tightening per matrix 紀律)
- (d) **D1 RED finding 完全 closed** — Sprint 57.3 v1 Day 0 探勘 揭露 backend missing endpoints;Option B pivot user-approved → bundle 解決
- (e) **Frontend SaaS 2/N rolling planning continues** — Sprint 57.3 retro Q5 列出 Phase 57.x candidate scope(Admin tenant console / Onboarding self-serve wizard requires backend self-serve API design / Tenant Settings list view 跨 tenant / DR / GDPR);user approval required per rolling planning 紀律

**主流量驗收標準**:
- `npm run dev` → admin user browse `/tenant-settings/{tenant_id}` → see all 9 read-only fields(id / code / display_name / state / plan / provisioning_progress / onboarding_progress / meta_data / created_at)
- `npm run dev` → admin user edit display_name + meta_data → submit → 200 OK + UI shows new values + backend audit_log 寫入 entry
- `npm run dev` → admin user attempts edit immutable field via dev console patch payload → backend 422 + frontend error UX
- `pytest backend/tests/integration/api/v1/admin/test_tenant_get.py + test_tenant_patch.py` ≥ 10 new tests pass
- Playwright e2e 4 tests pass(2 happy + 2 error)< 30s each
- `npm run lint && npm run build` clean
- `npm run test` (Vitest unit) ≥ 6 new tests pass
- Backend pytest baseline 1574 → 1584+(+10 from US-1+US-2)
- 8 V2 lints baseline 8/8 unchanged

---

## Background

### V2 進度

- **22/22 sprints (100%) main progress completed** + **Phase 56-58 SaaS Stage 1 3/3 ✅ CLOSED** (Sprint 56.3) + **Phase 57+ Frontend SaaS 1/N opened**(Sprint 57.1 v2 Cost + SLA dashboards) + **Phase 57+ Audit Cycle Lvl 2** ✅(Sprint 57.2 carryover bundle)
- main HEAD: `57a5daaf` (Sprint 57.2 closeout PR #107) — Day 0 verified
- pytest baseline 1574 / mypy --strict 0/295 source files / 8 V2 lints 8/8 green / LLM SDK leak 0
- 57.2 calibration `large multi-domain` 0.55 mid-band 3rd application ratio **0.77** (3-data-point mean **0.94 ✅** in band — KEEP 0.55)
- 13-sprint cumulative window 8/13 (61.5%) in-band sustained ≥ 60% threshold for 4th consecutive sprint
- **本 sprint = Phase 57+ SaaS Frontend 第 2 個 sprint v1**(2/N rolling;57.1 v1 onboarding wizard plan aborted Day 0 D7;57.1 v2 Cost+SLA dashboards delivered)

### 為什麼 57.3 是 Tenant Settings bundle 而非純 frontend

User approved 2026-05-07 Option B(`backend tenant CRUD endpoints + frontend Tenant Settings page bundle` — pivot from naive medium-frontend assumption):

1. **57.3 v1 abort root cause** — Day 0 Prong 2 content verify D1 揭露 56.1 admin tenants.py 只有 POST create + GET/POST onboarding,**沒有** GET/PUT/PATCH for tenant entity;Tenant Settings page UI 必要的 read+update endpoints 完全不存在;類比 57.1 v1 onboarding API model mismatch
2. **Option B pivot 解決真正 backend gap** — 而非 abort;新增 GET + PATCH 後 future Admin tenant console / list view / Onboarding self-serve UI 全可重用;ROI 高
3. **Mixed scope class 4th data point** — `mixed` 多 backend + frontend 比例對於 Phase 57+ 持續 frontend SaaS 推進是常見組合;補強 calibration matrix mixed 軸從 2-data-point → 3-data-point window
4. **Conservative PATCH scope** — 為避免 57.3 v1-style 過度推測,US-2 PATCH 僅暴露 display_name + meta_data;plan / state 等 lifecycle field 走既有 56.1 ProvisioningWorkflow + TenantLifecycle.transition;不在 settings endpoint 跨界
5. **AD-Plan-3 兩-prong + AD-Plan-4-Schema-Grep 已 fold-in to sprint-workflow.md §Step 2.5** — Sprint 57.1 v2 已 fold-in;此 sprint 為第 1 個 fully-applied Day 0 三-prong 探勘 sprint(Path + Content + Schema);可作為 process AD 規範實效驗證(預期 D-findings 質量 + 數量都會更高)

### 既有結構(Day 0 探勘 grep 已驗證以下事實)

✅ **以下 layout 是 plan-time 已 verified via Day 0 兩-prong 探勘**:

```
backend/src/api/v1/admin/                          # ✅ 56.1+56.2+56.3 既有
├── tenants.py                                     # ⚠️ MODIFY (US-1 + US-2: add GET + PATCH)
│   ├── @router.post("/")                          # ✅ existing (56.1 create_tenant)
│   ├── @router.get("/{id}/onboarding/")           # ✅ existing (56.1)
│   ├── @router.post("/{id}/onboarding/{step}")    # ✅ existing (56.1)
│   ├── @router.get("/{id}")                       # ❌ NEW (US-1)
│   ├── @router.patch("/{id}")                     # ❌ NEW (US-2)
│   ├── _load_tenant_or_404                        # ✅ existing (56.1) reusable
│   ├── class TenantResponse                       # ❌ NEW (US-1)
│   └── class TenantUpdateRequest                  # ❌ NEW (US-2)
├── cost_summary.py                                # ✅ existing (56.3)
└── sla_reports.py                                 # ✅ existing (56.3)

backend/src/platform_layer/identity/auth.py        # ✅ 56.2 existing
└── require_admin_platform_role                    # ✅ existing reusable

backend/src/platform_layer/tenant/                 # ✅ 56.1 existing
├── lifecycle.py                                   # ✅ existing (VALID_TRANSITIONS guard)
└── provisioning.py                                # ✅ existing

backend/src/infrastructure/db/audit_helper.py      # ✅ 53.5/53.6 existing
└── append_audit                                   # ✅ existing reusable

backend/src/infrastructure/db/models/identity.py   # ✅ 56.1 existing (no migration needed)
└── class Tenant                                   # ✅ existing fields all read-able

frontend/src/                                      # ✅ 57.1 v2 既有 + Vitest setup
├── features/
│   ├── chat_v2/                                   # ✅ existing
│   ├── governance/                                # ✅ existing (53.5)
│   ├── cost-dashboard/                            # ✅ existing (57.1 v2)
│   ├── sla-dashboard/                             # ✅ existing (57.1 v2)
│   ├── shared/components/MonthPicker.tsx          # ✅ existing (57.1 v2 — but tenant-settings 不需 month picker)
│   └── tenant-settings/                           # ❌ NEW (US-3 + US-4)
│       ├── components/TenantSettingsView.tsx      # ❌ NEW
│       ├── components/TenantSettingsEditForm.tsx  # ❌ NEW
│       ├── services/tenantSettingsService.ts      # ❌ NEW (plain fetch + _handleResponse)
│       ├── store/tenantSettingsStore.ts           # ❌ NEW (Zustand)
│       └── types.ts                               # ❌ NEW (mirror US-1 TenantResponse)
├── pages/
│   ├── chat-v2/index.tsx                          # ✅ existing
│   ├── governance/index.tsx                       # ✅ existing
│   ├── verification/index.tsx                     # ✅ existing
│   ├── cost-dashboard/index.tsx                   # ✅ existing
│   ├── sla-dashboard/index.tsx                    # ✅ existing
│   └── tenant-settings/index.tsx                  # ❌ NEW (US-4)
└── App.tsx                                        # ⚠️ MODIFY (US-5: add 1 wildcard route + 1 nav link)

frontend/tests/                                     # ✅ existing (57.1 v2 Vitest setup)
├── e2e/
│   ├── chat/, governance/, cost_dashboard/, sla_dashboard/  # ✅ existing
│   ├── tenant_settings_view.spec.ts                # ❌ NEW (US-5)
│   └── tenant_settings_edit.spec.ts                # ❌ NEW (US-5)
└── unit/  (Vitest)                                 # ✅ existing (57.1 v2)
```

### Sprint 57.2 retrospective Q5 對齐確認

Sprint 57.2 retrospective Q5 列出 Phase 57+ candidate scope:
- Tenant Settings page (medium-frontend ~10 hr × 0.65) ✅ **此 sprint US-1~US-5(pivoted to mixed bundle 0.60 per Day 0 D1)**
- Admin tenant console (medium-frontend ~12-15 hr) ⛔ defer Phase 57.x
- Onboarding self-serve wizard ⛔ defer pending backend self-serve API
- DR + WAL streaming (large multi-domain) ⛔ defer Phase 57.x
- Compliance partial GDPR (medium-backend) ⛔ defer Phase 57.x
- SaaS Stage 2 Stripe + 月結 ⛔ defer Phase 57++
- AD-Cat10-VisualVerifier + Frontend-Panel ⛔ defer Phase 57.x Group F
- AD-Cat11-Multiturn / SSEEvents / ParentCtx ⛔ defer Phase 57.x Cat 11 bundle
- AD-CI-6 production launch ⛔ defer Phase 58 dedicated sprint

### V2 紀律 9 項對齐確認

1. **Server-Side First** ✅ Backend GET + PATCH 完全 server-side;tenant_id 由 require_admin_platform_role JWT 驗證 + path param 驗證(per 56.2 RBAC pattern + 56.1 _load_tenant_or_404)
2. **LLM Provider Neutrality** ✅ 此 sprint 不動 LLM 鏈路
3. **CC Reference 不照搬** ✅ Tenant Settings 為標準 SaaS admin UX pattern;plain fetch + Zustand stack 既有
4. **17.md Single-source** ✅ 此 sprint 不新增 cross-category interface;TenantResponse + TenantUpdateRequest 為 admin API 內部 DTO,non-cross-category;不影響 17.md
5. **11+1 範疇歸屬** ✅ US-1~US-2 全 §API admin layer(non-範疇)+ US-3~US-5 全 §Frontend(16-frontend-design.md);無範疇 1-12 backend module 變更;每檔案明確歸屬;無 AP-3
6. **04 anti-patterns** ✅ AP-3 範疇歸屬合規 / AP-4(Potemkin)— 全有實際 wire-up + Playwright e2e + backend pytest 強制驗證 / AP-6(Hybrid Bridge Debt)— 不為 Stage 2 預寫 abstraction;PATCH 嚴格限制 editable fields / AP-9(Verification)— audit chain + Playwright + 422 immutable test 強制 verify / AP-11(命名一致)— `tenant-settings` consistent naming
7. **Sprint workflow** ✅ plan → checklist → Day 0 三-prong 探勘(Path + Content + Schema all DONE)→ code → progress → retro;本文件依 57.1 v2 plan 結構鏡射(14 sections / 5 days Day 0-4)
8. **File header convention** ✅ 所有 new 檔案含 file header docstring;modify 檔案加 Modification History entry;MHist 1-line max per AD-Lint-3 + char-count guidance per AD-Lint-MHist-Verbosity
9. **Multi-tenant rule** ✅ tenants 表本身非 TenantScopedMixin(它**就是** tenant);安全靠 require_admin_platform_role + path param tenant_id 與 JWT super-admin role 雙重 check;non-admin 401/403 + RLS check 8 V2 lint check_rls_policies 不適用 tenants 表 per D6

---

## User Stories

### US-1: Backend GET /admin/tenants/{tenant_id}

**As** a SaaS platform super-admin
**I want** a single endpoint that returns the full tenant entity (all 9 ORM fields) given tenant_id
**So that** I can view tenant configuration without inspecting DB directly,and frontend Tenant Settings page can render the read view

**Acceptance**:
- `backend/src/api/v1/admin/tenants.py` 新增 `@router.get("/{tenant_id}", response_model=TenantResponse)` endpoint
- Pydantic `TenantResponse` mirrors ORM fields:`id` (UUID) / `code` (str, immutable) / `display_name` (str) / `state` (TenantState enum value) / `plan` (TenantPlan enum value) / `provisioning_progress` (dict) / `onboarding_progress` (dict) / `meta_data` (dict) / `created_at` (datetime) / `updated_at` (datetime)
- Auth dependency:`require_admin_platform_role` per 56.2 RBAC pattern(super-admin only;non-platform-admin → 401/403)
- Reuses `_load_tenant_or_404` helper from `tenants.py:167`(404 if tenant_id not found)
- 5-7 tests:happy path + 401 unauth + 403 wrong role + 404 not found + 200 with all fields populated
- `pytest backend/tests/integration/api/v1/admin/test_tenant_get.py` pass
- Backend pytest baseline 1574 → 1579+

### US-2: Backend PATCH /admin/tenants/{tenant_id}

**As** a SaaS platform super-admin
**I want** a partial update endpoint that allows editing display_name + meta_data (JSONB) only,with audit chain logging
**So that** I can update tenant settings safely(immutable fields rejected;state/plan changes go through dedicated lifecycle endpoint)

**Acceptance**:
- `backend/src/api/v1/admin/tenants.py` 新增 `@router.patch("/{tenant_id}", response_model=TenantResponse)` endpoint
- Pydantic `TenantUpdateRequest` 只含 `display_name: str | None = None` + `meta_data: dict | None = None`(其他欄位 ORM 拒絕通過 Pydantic 解析 → 422)
- Editable fields validated:
  - `display_name`:non-empty + max 256 chars(per ORM constraint)
  - `meta_data`:dict (JSON validated by Pydantic);max 10 KB serialized(防範濫用)
- Immutable fields enforcement:若 request body 含 `id` / `code` / `state` / `plan` / `created_at` etc.,Pydantic `extra="forbid"` 拒絕 → 422 Unprocessable Entity
- Audit chain entry per 53.5/53.6 pattern:`await append_audit(db, tenant_id=tenant_id, action="tenant_settings_updated", actor_user_id=admin_user_id, details={"changed_fields": [...], "old_values": {...}, "new_values": {...}})`
- updated_at field auto-bumped via SQLAlchemy onupdate
- 5-7 tests:happy path display_name only + happy path meta_data only + happy path both + 422 immutable field attempt + 422 display_name too long + 401/403/404 errors + audit log assertion
- `pytest backend/tests/integration/api/v1/admin/test_tenant_patch.py` pass
- Backend pytest baseline 1579 → 1584+

### US-3: Frontend Tenant Settings Infrastructure

**As** the React app
**I want** per-feature folder skeleton for tenant-settings mirroring cost-dashboard pattern(infra reuse from 57.1 v2)
**So that** Tenant Settings UI has consistent code organization,types match US-1 TenantResponse,store handles read+update lifecycle

**Acceptance**:
- `frontend/src/features/tenant-settings/` skeleton:components/ services/ store/ types.ts
- `types.ts`:mirror US-1 TenantResponse(`TenantState` enum / `TenantPlan` enum / `TenantSettingsResponse` interface)+ US-2 TenantUpdateRequest interface
- `tenantSettingsService.ts`:`fetchTenantSettings(tenantId)` + `updateTenantSettings(tenantId, payload)` mirror `costService.ts` plain fetch + `_handleResponse<T>` pattern;`API_BASE = "/api/v1/admin"`
- `tenantSettingsStore.ts`:Zustand state(`tenantId / data / loading / error / saving / saveError`;actions:`loadData / saveDisplayName / saveMetaData / reset`);optimistic update on save + invalidate-on-error;mirror cost-dashboard chatStore pattern
- 3 Vitest unit tests:fetchTenantSettings happy + updateTenantSettings happy + store loadData action

### US-4: Frontend Tenant Settings Page (View + Edit)

**As** a SaaS platform super-admin
**I want** a Tenant Settings page that displays all tenant fields read-only AND lets me edit display_name + meta_data inline
**So that** I can manage tenant configuration via web UI without DB tools

**Acceptance**:
- `frontend/src/pages/tenant-settings/index.tsx` page wrapper(Routes + Route index → TenantSettingsView)
- `frontend/src/features/tenant-settings/components/TenantSettingsView.tsx`:
  - URL pattern:`/tenant-settings/{tenant_id}`(via React Router param)
  - Read sections:Tenant ID(badge)+ Code(immutable label)+ State(badge color: ACTIVE green / PROVISIONING yellow / OTHER gray)+ Plan(badge color: enterprise blue / standard gray)+ created_at + updated_at
  - Provisioning + Onboarding progress collapsed JSON(read-only `<pre>` block)
  - Edit toggle button → switches to TenantSettingsEditForm
- `TenantSettingsEditForm.tsx`:
  - display_name text input(max 256 chars validation)
  - meta_data JSON textarea(parse + validate on blur;invalid JSON → red error message + disable save)
  - Save button(disabled while loading);Cancel button(reverts to view mode)
  - Submit:call store.saveDisplayName + store.saveMetaData;optimistic UI update;error → rollback + show error
- Loading skeleton + error retry button per governance pattern
- 3 Vitest unit tests:TenantSettingsView render with mock data + TenantSettingsEditForm submit valid + TenantSettingsEditForm JSON validate invalid

### US-5: Routing + Playwright E2E + Closeout Ceremony

**As** the V2 sprint executor
**I want** App.tsx wildcard route + Home nav + Playwright e2e tests + retrospective + AD-Sprint-Plan-4 mixed 3rd app calibration verify
**So that** Sprint 57.3 closes Phase 57+ SaaS Frontend 2/N with full audit trail

**Acceptance**:
- `frontend/src/App.tsx`:add `<Route path="/tenant-settings/*" element={<TenantSettingsPage />} />`
- Home page nav:add `<Link to="/tenant-settings/{TENANT_ID}">Tenant Settings</Link>` — always visible per 57.1 D10 Option C(no frontend role gate;backend 401/403 surfaces as Error UX)
- `frontend/tests/e2e/tenant_settings_view.spec.ts`:
  - happy path:admin auth → load `/tenant-settings/{tenant_id}` → assert all read fields visible
  - error path:backend 500 → retry button + recovery on mock 200
- `frontend/tests/e2e/tenant_settings_edit.spec.ts`:
  - happy path:admin auth → click edit → modify display_name → save → assert UI updates + new value rendered
  - error path:edit + submit invalid meta_data JSON → assert disabled save button + red error message
- retrospective.md(6 必答 + AD-Sprint-Plan-4 mixed 3rd app calibration verify + Phase 57.x next-sprint candidates Q5 + Day 0 三-prong 探勘 first fully-applied sprint observations)
- Memory snapshot `memory/project_phase57_3_tenant_settings.md`
- SITUATION-V2 §9 + CLAUDE.md sync to **Phase 57+ SaaS Frontend 2/N (Sprint 57.3 closed — Tenant Settings bundle)**

---

## Technical Specifications

### Backend Endpoint Pattern (mirror 56.1 + 56.2 + 56.3)

```python
# backend/src/api/v1/admin/tenants.py — NEW additions

class TenantResponse(BaseModel):
    """Read-only response for GET /admin/tenants/{id}."""
    id: UUID
    code: str
    display_name: str
    state: TenantState
    plan: TenantPlan
    provisioning_progress: dict[str, Any]
    onboarding_progress: dict[str, Any]
    meta_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TenantUpdateRequest(BaseModel):
    """PATCH partial update — display_name + meta_data only.

    Pydantic extra='forbid' rejects any other field with 422.
    """
    display_name: str | None = Field(None, min_length=1, max_length=256)
    meta_data: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid")


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    _admin_user_id: UUID = Depends(require_admin_platform_role),
) -> TenantResponse:
    tenant = await _load_tenant_or_404(db, tenant_id)
    return TenantResponse.model_validate(tenant)


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID,
    request: TenantUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    admin_user_id: UUID = Depends(require_admin_platform_role),
) -> TenantResponse:
    tenant = await _load_tenant_or_404(db, tenant_id)

    changed_fields: list[str] = []
    old_values: dict[str, Any] = {}
    new_values: dict[str, Any] = {}

    if request.display_name is not None and request.display_name != tenant.display_name:
        old_values["display_name"] = tenant.display_name
        new_values["display_name"] = request.display_name
        tenant.display_name = request.display_name
        changed_fields.append("display_name")

    if request.meta_data is not None and request.meta_data != tenant.meta_data:
        old_values["meta_data"] = tenant.meta_data
        new_values["meta_data"] = request.meta_data
        tenant.meta_data = request.meta_data
        changed_fields.append("meta_data")

    if not changed_fields:
        return TenantResponse.model_validate(tenant)  # no-op, skip audit

    await db.flush()  # bump updated_at

    await append_audit(
        db,
        tenant_id=tenant_id,
        action="tenant_settings_updated",
        actor_user_id=admin_user_id,
        details={
            "changed_fields": changed_fields,
            "old_values": old_values,
            "new_values": new_values,
        },
    )
    await db.commit()

    return TenantResponse.model_validate(tenant)
```

### Service Pattern (mirror 57.1 v2 costService.ts)

```typescript
// frontend/src/features/tenant-settings/services/tenantSettingsService.ts
import type { TenantSettingsResponse, TenantUpdateRequest } from "../types";

const API_BASE = "/api/v1/admin";

async function _handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch { /* ignore */ }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

export async function fetchTenantSettings(tenantId: string): Promise<TenantSettingsResponse> {
  const response = await fetch(
    `${API_BASE}/tenants/${tenantId}`,
    { credentials: "include" },
  );
  return _handleResponse<TenantSettingsResponse>(response);
}

export async function updateTenantSettings(
  tenantId: string,
  payload: TenantUpdateRequest,
): Promise<TenantSettingsResponse> {
  const response = await fetch(
    `${API_BASE}/tenants/${tenantId}`,
    {
      method: "PATCH",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
  return _handleResponse<TenantSettingsResponse>(response);
}
```

### Zustand Store Pattern (mirror 57.1 v2 costStore.ts)

```typescript
// frontend/src/features/tenant-settings/store/tenantSettingsStore.ts
import { create } from "zustand";
import type { TenantSettingsResponse, TenantUpdateRequest } from "../types";
import { fetchTenantSettings, updateTenantSettings } from "../services/tenantSettingsService";

interface TenantSettingsState {
  tenantId: string | null;
  data: TenantSettingsResponse | null;
  loading: boolean;
  error: string | null;
  saving: boolean;
  saveError: string | null;
  setTenantId: (tenantId: string) => void;
  loadData: () => Promise<void>;
  save: (payload: TenantUpdateRequest) => Promise<void>;
  reset: () => void;
}

export const useTenantSettingsStore = create<TenantSettingsState>((set, get) => ({
  tenantId: null,
  data: null,
  loading: false,
  error: null,
  saving: false,
  saveError: null,
  setTenantId: (tenantId) => set({ tenantId, data: null }),
  loadData: async () => {
    const tenantId = get().tenantId;
    if (!tenantId) return;
    set({ loading: true, error: null });
    try {
      const data = await fetchTenantSettings(tenantId);
      set({ data, loading: false });
    } catch (err) {
      set({ error: (err as Error).message, loading: false });
    }
  },
  save: async (payload) => {
    const tenantId = get().tenantId;
    if (!tenantId) return;
    set({ saving: true, saveError: null });
    try {
      const data = await updateTenantSettings(tenantId, payload);
      set({ data, saving: false });
    } catch (err) {
      set({ saveError: (err as Error).message, saving: false });
    }
  },
  reset: () => set({ data: null, loading: false, error: null, saving: false, saveError: null }),
}));
```

### Risk Class A/B/C — A retired, B+C still N/A

- Risk Class A: paths-filter retired by 55.6 Option Z;此 sprint 不適用
- Risk Class B: cross-platform mypy unused-ignore — 此 sprint 涉及 backend(US-1+US-2);若 import drift → 套 `# type: ignore[import-not-found, unused-ignore]` 雙 code per code-quality.md;低概率(全用既有依賴 + 現有 helper)
- Risk Class C: module-level singleton — backend 部分若 audit_helper.py 涉及 module-level cache(56.x ServiceFactory pattern);US-2 PATCH endpoint integration test 應在 `tests/integration/api/v1/admin/conftest.py` 用 autouse `_reset_module_singletons` fixture per testing.md §Module-level Singleton Reset Pattern

### Day 0 三-prong 探勘 v2 capture (first fully-applied sprint)

Sprint 57.3 是 Day 0 三-prong 探勘 first fully-applied sprint(Path + Content + Schema all attempted;Schema verdict = N/A 但 attempt 完成):
- Prong 1 Path Verify ✅ done — 8 frontend folder existence checks
- Prong 2 Content Verify ✅ done — 7 backend assertion grep checks(D1 RED catch)
- Prong 3 Schema Verify ✅ N/A — 無新 DB schema/migration;但 attempt 完成(per fold-in spirit)

**ROI:** D1 catch via Prong 2 (~30 min cost) prevented 8-12 hr Day 1+ rework(類比 57.1 v1 abort 8-10 hr);**ROI ≈ 16-24×**(7-8× 為 55.6 Option H pattern + 2× 為 Schema-Grep 56.3 pattern;3-Prong fully-applied 為新 ROI multiplier)

---

## Acceptance Criteria

### Sprint-Wide

- [ ] V2 主進度 22/22 (100%) 不變;Phase 56-58 SaaS Stage 1 backend 3/3 不變;Phase 57+ Frontend SaaS 1/N → 2/N
- [ ] All 8 V2 lints green (新 backend code 不違反 LLM SDK / promptbuilder / sole_mutator / RLS gaps lints)
- [ ] Backend pytest baseline 1574 → 1584+ (≥+10 from US-1+US-2)
- [ ] Backend mypy --strict 0 errors (新增 ~3-4 source files;需 295 → 297+)
- [ ] Backend LLM SDK leak: 0 不變
- [ ] Anti-pattern checklist 11 項對齐
- [ ] 5 active CI checks green(含 Frontend E2E chromium headless per 53.7 baseline)
- [ ] Frontend `npm run lint && npm run build` clean
- [ ] Frontend Vitest ≥+6 new tests pass(3 US-3 + 3 US-4)
- [ ] Playwright e2e 4 tests pass(2 view + 2 edit happy/error)
- [ ] Audit chain test:US-2 PATCH 後 audit_log 有對應 entry with action="tenant_settings_updated"
- [ ] AD-Sprint-Plan-4 `mixed` 3rd application captured + verdict logged in retro Q2
- [ ] D1 RED finding fully closed(US-1 + US-2 backend endpoints production-ready)
- [ ] Day 0 三-prong 探勘 first fully-applied sprint observations documented in retro Q3

### Per-User-Story

詳見 §User Stories acceptance per US.

---

## Day-by-Day Plan

### Day 0 — Setup + Day-0 三-prong 探勘 + Pre-flight Verify

- 0.1 Branch + plan + checklist commit
- 0.2 Day-0 三-prong 探勘(per AD-Plan-3 + AD-Plan-4 fold-in promoted)— **Prong 1 Path Verify**:`features/tenant-settings/` + `pages/tenant-settings/` + `tests/e2e/tenant_settings_*.spec.ts` 不存在(expect)/ admin endpoint helpers `_load_tenant_or_404` 已存在 / auth helper `require_admin_platform_role` 已存在 / `append_audit` 已存在;**Prong 2 Content Verify**:`api/v1/admin/tenants.py` GET/PUT/PATCH 不存在(D1 RED already caught — 已 user-confirmed Option B pivot)/ TenantPlan + TenantState enum 已定義 / VALID_TRANSITIONS guard 已存在 / append_audit signature 完整 reusable;**Prong 3 Schema Verify**:N/A 此 sprint(無新 DB schema/migration;但 attempt 完成 per fold-in spirit)
- 0.3 Calibration multiplier pre-read(`mixed` 0.60 mid-band 3rd application;2-data-point mean 1.09 KEEP per AD-Sprint-Plan-4 matrix;若 ratio in band → 3rd data point;3-data-point window opens;若 outside → AD-Sprint-Plan-N+1 logged)
- 0.4 Pre-flight verify(backend pytest baseline 1574 / 8 V2 lints baseline / mypy baseline / LLM SDK leak baseline / frontend `npm run build` baseline / Playwright config sanity)
- 0.5 Day 0 progress.md commit + push;catalogue D-findings(D1 closed by Option B;D2-D8 informational);若 scope shift > 20% revise plan §Risks per AD-Plan-1 audit-trail

### Day 1 — US-1 Backend GET endpoint

- 1.1 Add `class TenantResponse(BaseModel)` with all 9 ORM-mirror fields + `from_attributes=True`
- 1.2 Add `@router.get("/{tenant_id}", response_model=TenantResponse)` endpoint with `require_admin_platform_role` + `_load_tenant_or_404`
- 1.3 NEW test file `backend/tests/integration/api/v1/admin/test_tenant_get.py`(5-7 tests:happy path with all fields / 401 unauth / 403 wrong role / 404 not found / response shape assertion)
- 1.4 Day 1 sanity checks:`pytest backend/tests/integration/api/v1/admin/test_tenant_get.py` pass / `mypy --strict backend/src/api/v1/admin/tenants.py` clean / 8 V2 lints unchanged
- 1.5 Day 1 commit + push + progress.md

### Day 2 — US-2 Backend PATCH endpoint

- 2.1 Add `class TenantUpdateRequest(BaseModel)` with `extra="forbid"` + `display_name + meta_data` Field constraints
- 2.2 Add `@router.patch("/{tenant_id}", response_model=TenantResponse)` endpoint with audit chain entry
- 2.3 NEW test file `backend/tests/integration/api/v1/admin/test_tenant_patch.py`(5-7 tests:happy path display_name only + happy path meta_data only + happy path both + 422 immutable field attempt + 422 display_name too long + 401/403/404 + audit_log assertion)
- 2.4 Module-level singleton reset pattern verify per testing.md(若 audit_helper 有 module-level cache → autouse fixture in conftest.py;低風險但須 check)
- 2.5 Day 2 sanity checks:`pytest backend/tests/integration/api/v1/admin/test_tenant_patch.py` pass / mypy / lints
- 2.6 Day 2 commit + push + progress.md

### Day 3 — US-3 Frontend Infra + US-4 Page Display + Edit Form

- 3.1 `frontend/src/features/tenant-settings/` skeleton(components/ services/ store/ types.ts)
- 3.2 `types.ts` mirror US-1 TenantResponse + US-2 TenantUpdateRequest interface
- 3.3 `tenantSettingsService.ts` plain fetch + `_handleResponse<T>` helper(mirror costService)
- 3.4 `tenantSettingsStore.ts` Zustand store(loadData + save actions + saving/saveError state)
- 3.5 3 Vitest unit tests US-3(fetchTenantSettings happy + updateTenantSettings happy + store loadData action)
- 3.6 `frontend/src/pages/tenant-settings/index.tsx` page wrapper
- 3.7 `TenantSettingsView.tsx`(read view: 5 fields + state/plan badges + JSON `<pre>` for progress + edit toggle button)
- 3.8 `TenantSettingsEditForm.tsx`(display_name input + meta_data JSON textarea with parse validate + save/cancel buttons)
- 3.9 3 Vitest unit tests US-4(View render with mock + Form submit valid + Form JSON validate invalid)
- 3.10 Day 3 sanity checks:`npm run lint && npm run build` + Vitest pass
- 3.11 Day 3 commit + push + progress.md

### Day 4 — US-5 Routing + Playwright E2E + Closeout Ceremony

- 4.1 App.tsx wildcard route `/tenant-settings/*` + Home nav `<Link>`(always visible per 57.1 D10 Option C)
- 4.2 Playwright e2e `tenant_settings_view.spec.ts`(happy + error)
- 4.3 Playwright e2e `tenant_settings_edit.spec.ts`(happy edit + invalid JSON validate)
- 4.4 Final pytest + lint + leak verify(backend 1574 → 1584+ / mypy 0 / 8 V2 lints / LLM SDK 0 / frontend lint+build)
- 4.5 Retrospective.md(6 必答 + AD-Sprint-Plan-4 mixed 3rd app verify + Day 0 三-prong first fully-applied sprint observations + Phase 57.x next-sprint candidates Q5)
- 4.6 Memory snapshot `memory/project_phase57_3_tenant_settings.md` + MEMORY.md index update
- 4.7 Open PR + CI green + solo-dev merge to main
- 4.8 Closeout PR(SITUATION-V2 §9 + CLAUDE.md sync to **Phase 57+ SaaS Frontend 2/N (Sprint 57.3 closed — Tenant Settings bundle)**)

---

## File Change List

| File | Status | Lines (est) |
|------|--------|-------------|
| `backend/src/api/v1/admin/tenants.py` | MODIFIED | +150 (TenantResponse + TenantUpdateRequest + 2 endpoints) |
| `backend/tests/integration/api/v1/admin/test_tenant_get.py` | NEW | ~120 |
| `backend/tests/integration/api/v1/admin/test_tenant_patch.py` | NEW | ~180 |
| `frontend/src/features/tenant-settings/types.ts` | NEW | ~40 |
| `frontend/src/features/tenant-settings/services/tenantSettingsService.ts` | NEW | ~60 |
| `frontend/src/features/tenant-settings/store/tenantSettingsStore.ts` | NEW | ~80 |
| `frontend/src/features/tenant-settings/components/TenantSettingsView.tsx` | NEW | ~120 |
| `frontend/src/features/tenant-settings/components/TenantSettingsEditForm.tsx` | NEW | ~140 |
| `frontend/src/pages/tenant-settings/index.tsx` | NEW | ~25 |
| `frontend/src/App.tsx` | MODIFIED | +8 (1 Route + 1 Link) |
| `frontend/tests/e2e/tenant_settings_view.spec.ts` | NEW | ~80 |
| `frontend/tests/e2e/tenant_settings_edit.spec.ts` | NEW | ~100 |
| Vitest unit tests (~6 new) | NEW | ~250 |
| `docs/.../sprint-57-3/{progress,retrospective}.md` | NEW | ~600 |
| `memory/project_phase57_3_tenant_settings.md` | NEW | ~60 |

**Total**: ~700 source LOC + ~610 test LOC + ~660 docs LOC

---

## Dependencies & Risks

### Dependencies (must exist before code starts)

- ✅ Phase 56.1 backend Tenant ORM model `class Tenant` (identity.py:98) — Day 0 verified
- ✅ Phase 56.1 backend `_load_tenant_or_404` helper (tenants.py:167) — Day 0 verified
- ✅ Phase 56.1 backend `VALID_TRANSITIONS` + TenantLifecycle (lifecycle.py:63) — Day 0 verified
- ✅ Phase 56.2 backend `require_admin_platform_role` auth dep (auth.py:140) — Day 0 verified
- ✅ Phase 53.5/53.6 backend `append_audit` helper (audit_helper.py:90) — Day 0 verified
- ✅ Phase 57.1 v2 frontend cost-dashboard service+store pattern reusable — Day 0 verified
- ✅ Phase 57.1 v2 frontend Vitest setup — Day 0 verified
- ✅ Phase 53.6 frontend Playwright auth fixture pattern reusable — Day 0 verified

### Risk Classes (per sprint-workflow.md §Common Risk Classes)

**Risk Class A (paths-filter vs required_status_checks)**: 已 closed by 55.6 Option Z (paths-filter retired 永久);此 sprint 不適用。

**Risk Class B (cross-platform mypy unused-ignore)**: 低概率 — 此 sprint backend 全用既有依賴(SQLAlchemy / FastAPI / Pydantic v2 / append_audit);若新 import drift → 套 `# type: ignore[import-not-found, unused-ignore]` 雙 code per code-quality.md;mitigation 於 Day 1+2 sanity check 階段。

**Risk Class C (module-level singleton across event loops)**: 低概率 — 此 sprint backend 不引入新 module-level singleton;但 US-2 PATCH 整合測試需 autouse `_reset_service_factory` if integration suite already has fixture(per 56.x); Day 2 sanity check 階段 verify。

### Day 0 三-prong 探勘 D-findings v2 (catalogued during Day 0)

**D1** 🔴 RED — backend admin tenants.py 沒 GET/PUT/PATCH for tenant entity;**Closed by Option B pivot**(user-confirmed 2026-05-07 — bundle 2 backend endpoints + frontend UI 解決真正 backend gap)。Implication:此 sprint 多了 US-1+US-2 backend scope ~5-6 hr;multiplier shift `medium-frontend` 0.65 → `mixed` 0.60。

**D2** 🟢 GREEN — `require_admin_platform_role` exists at `auth.py:140`(56.2 RBAC pattern)。Implication:US-1 + US-2 endpoints reuse;與 sla_reports + cost_summary 一致;auth pattern 一致無需新增。

**D3** 🟢 GREEN — `VALID_TRANSITIONS` enforced via TenantLifecycle in `lifecycle.py:63`。Implication:US-2 PATCH endpoint 不暴露 state/plan editing;Pydantic `extra="forbid"` 即可拒絕跨界 request;不需在 PATCH endpoint 內額外 transition 檢查 logic。

**D4** 🟢 GREEN — `append_audit` exists at `infrastructure/db/audit_helper.py:90`(53.5/53.6 establishment)。Implication:US-2 PATCH audit chain entry pattern reusable;tests 套 audit_log row count assertion 即可。

**D5** 🟢 GREEN — `_load_tenant_or_404` already exists in `tenants.py:167`。Implication:US-1 + US-2 endpoints reuse helper;無 duplicate;404 行為一致。

**D6** 🟠 YELLOW — tenants 表本身**無 RLS policy**(非 TenantScopedMixin — 它**就是** tenant)。Implication:8 V2 lint check_rls_policies 不適用 tenants 表(已 whitelisted per 56.1 US-5 baseline 0 gaps);US-1 + US-2 endpoints 安全靠 require_admin_platform_role 雙重 check(JWT super-admin role + path tenant_id verification via _load_tenant_or_404);非 RLS 隔離。

**D7** 🟢 GREEN — TenantPlan + TenantState enum 已定義(identity.py:73 + 88)。Implication:US-1 TenantResponse Pydantic 直接 mirror enum value;Schema-Grep Prong 3 = N/A this sprint(無新 column / table / migration);但 attempt 完成 per fold-in spirit。

**D8** 🟠 YELLOW — TenantPlan upgrade 邏輯(56.1 PlanLoader)需走 separate workflow(非此 sprint 範圍)。Implication:US-2 PATCH endpoint 嚴格限 display_name + meta_data;plan / state 等 lifecycle field 未來若需要 web UI editing → separate sprint design dedicated lifecycle endpoint(per AP-6 不為未來預寫 abstraction)。

**Cumulative scope shift** = +backend 5-6 hr(D1 → US-1+US-2)= **+33-40%** vs naive medium-frontend 假設(~10 hr × 0.65)→ pivot to `mixed` 0.60(2-data-point mean 1.09)→ ~17 hr × 0.60 = ~10 hr;< 50% threshold per AD-Plan-1(若 > 50% 則 abort);user-confirmed Option B 2026-05-07 → 繼續 Day 1+;no plan re-version required mid-sprint。

### Sprint-specific Risks

| Risk | Mitigation |
|------|-----------|
| US-2 PATCH endpoint Pydantic `extra="forbid"` 行為與 plan 假設不符 | Day 2 first thing: write 422 immutable test;若 Pydantic v2 行為與 v1 不一致 → adjust strategy(per 56.1 + 56.2 已用 Pydantic v2 慣例;低風險) |
| audit_helper.append_audit signature 與 plan 假設不符 | Day 2 first thing: read audit_helper.py 確認;若 signature drift → adjust US-2 call;低風險(53.6 production wiring 已穩定 6 個月) |
| Pydantic v2 `model_config = ConfigDict(from_attributes=True)` ORM 序列化失敗 | Day 1 first thing:test_tenant_get.py 第 1 個 test → response shape 完整 assertion;若 enum value 序列化異常 → 套 `field_serializer` |
| US-4 frontend JSON textarea validation UX 太嚴 | meta_data JSON 解析 invalid 即 disable save + 紅色 message;如太激進 → debounce parse 500ms;Day 3 manual smoke 階段 verify |
| Playwright e2e admin auth fixture 重用問題 | Mirror 53.6 + 57.1 v2 既有 e2e auth fixture pattern;若 fixtures/admin_auth.ts 不存在 → US-5 scope +30 min add fixture |
| `mixed` 0.60 mult 3rd app ratio outside band | 若 ratio > 1.20 → AD-Sprint-Plan-N+1 raise(0.60 → 0.70);若 < 0.85 → AD-Sprint-Plan-N+1 reduce(0.60 → 0.50);each case logged in retro Q2 |
| Day 0 三-prong 探勘 first fully-applied sprint 過度 over-engineer | 嚴格遵守 §Step 2.5 Prong 1+2+3 既有 grep query patterns table;不新增 prong;Schema-Grep N/A 即停止;不重新發明 |

---

## Workload

> **Bottom-up est ~17 hr → calibrated commit ~10 hr (multiplier 0.60 per AD-Sprint-Plan-4 scope-class matrix `mixed` 3rd application;2-data-point mean 1.09 ✅ in band → KEEP 0.60 mid-band)**
> **13-sprint window 8/13 (61.5%) in-band(`mixed` 2-data-point: 53.7=1.01 / 56.2=1.17;mean 1.09 ✅)** — 此 sprint 為 `mixed` 3rd application;若 ratio in band → 3-data-point window 形成 mid-band 穩定信號

| US | Bottom-up (hr) |
|----|---------------|
| US-1 Backend GET /admin/tenants/{id}(TenantResponse Pydantic + endpoint + 5-7 tests + mypy/lint sanity) | 2 |
| US-2 Backend PATCH /admin/tenants/{id}(TenantUpdateRequest + endpoint + audit chain + 5-7 tests + immutable field guard) | 4 |
| US-3 Frontend infra(skeleton + types + service + store + 3 Vitest tests) | 3 |
| US-4 Frontend page(View + EditForm + JSON validate + 3 Vitest tests) | 5 |
| US-5 Routing + Home nav + 4 Playwright e2e + closeout(retro + ceremony + memory + closeout PR) | 3 |
| **Total bottom-up** | **17** |
| **× 0.60 calibrated** | **10.2 ≈ 10** |

Day 4 retrospective Q2 must verify: `actual_total_hr / 10 → ratio` compared to [0.85, 1.20] band;document delta + log calibration verdict for `mixed` class 3rd data point;若 ratio in band → 3-data-point window opens(mean 跟 1.09 比;若 mean < 1.05 in next 1-2 sprints → consider reduce to 0.55 mid-band);若 outside → AD-Sprint-Plan-N+1 logged。

---

## Out of Scope

- ❌ Plan / state editing via Tenant Settings UI — defer to dedicated lifecycle endpoint(per 56.1 ProvisioningWorkflow + TenantLifecycle.transition;separate sprint)
- ❌ Tenant列表 / cross-tenant aggregation view — Phase 57.x Admin tenant console sprint
- ❌ Tenant create / delete UI — backend POST 已 56.1 / DELETE 不存在(soft-delete 透過 state transition);UI 留 separate sprint
- ❌ Onboarding wizard self-serve — defer pending backend self-serve API design
- ❌ Feature flags admin UI — backend FeatureFlagsService 存在 core/ 但無 HTTP endpoint;separate sprint
- ❌ Tenant settings change history view(audit log frontend)— governance audit log endpoint 已 53.5 / 53.6 / 53.7;UI render 留 Phase 57.x
- ❌ Tenant settings export to CSV / JSON — Phase 57++
- ❌ Multi-tenant tenant switcher(super-admin 多 tenant 切換)— Phase 57++ Admin tenant console
- ❌ Tenant settings WebSocket / real-time sync — Phase 57++
- ❌ i18n / localization — 此 sprint English-only
- ❌ WCAG accessibility full audit — basic keyboard nav + label association 即可
- ❌ Mobile responsive — desktop-first
- ❌ Stripe checkout / 月結 invoice UI — Phase 57++ Stage 2
- ❌ Customer-facing Status Page — Phase 57++ Stage 2
- ❌ AD-Cat10-VisualVerifier + Frontend-Panel — Phase 57.x Group F dedicated sprint
- ❌ AD-Cat11-Multiturn / SSEEvents / ParentCtx — Phase 57.x Cat 11 enhancement sprint
- ❌ AD-CI-6 production launch — Phase 58 dedicated sprint after Azure provisioning

---

## AD Carryover Sub-Scope

### AD-Sprint-Plan-4 `mixed` 3rd application

**Source**: Sprint 55.3 retrospective Q2 (calibration matrix proposed) → 53.7 mixed 0.55 1st app ratio 1.01 + 56.2 mixed 0.60 2nd app ratio 1.17 → 2-data-point mean 1.09 ✅;此 sprint 為 3rd application(57.3 v1 Day 0 D1 RED → Option B pivot 從 medium-frontend 改 mixed)

**Closure plan**:
1. Sprint 57.3 plan §Workload uses **0.60** for `mixed` class (3rd application;2-data-point mean 1.09 KEEP mid-band)
2. Day 4 retrospective Q2 computes `actual / 10`
3. If ratio ∈ [0.85, 1.20] → record `mixed` 3-data-point baseline;若 3-data-point mean < 1.05 → consider AD-Sprint-Plan-N+1 reduce to 0.55(mid-band tightening);若 ≥ 1.05 → KEEP 0.60
4. If ratio < 0.85 → log AD-Sprint-Plan-N+1 (lower 0.60 → 0.50 for next mixed sprint)
5. If ratio > 1.20 → log AD-Sprint-Plan-N+1 (raise 0.60 → 0.70)
6. Update CLAUDE.md Last Updated entry with calibration window(mixed class 3-data-point established)

### Day 0 三-prong 探勘 first fully-applied sprint observations

**Source**: Sprint 55.6 promoted AD-Plan-3 to validated rule(2-prong);Sprint 56.3 evidence promoted AD-Plan-4-Schema-Grep;Sprint 57.1 v2 folded both into sprint-workflow.md §Step 2.5 as 3-prong model;**Sprint 57.3 是 first sprint with all 3 prongs attempted Day 0**(Path + Content + Schema Verdict N/A but attempted)

**Closure plan**:
1. Sprint 57.3 Day 0 progress.md catalogues attempt + verdict for each prong
2. retrospective Q3 sub-section "Day 0 三-prong 探勘 first fully-applied sprint":
   - Prong 1 Path Verify time spent + findings count
   - Prong 2 Content Verify time spent + findings count(D1 RED catch ROI evidence)
   - Prong 3 Schema Verify attempt(N/A this sprint)+ confirm 自然 fall-through
   - Cumulative ROI:catalogue actual time saved vs naive plan(類比 57.1 v1 abort 8-10 hr loss 對比 57.3 Day 0 ~30 min cost catching D1)
3. retrospective Q4 actionable improvement(若 Schema-Grep 在 N/A sprint 仍 attempt 就花太多時間 → 補充 §Step 2.5 Prong 3 「快速 N/A 判斷標準」list)

### Phase 57+ Frontend SaaS rolling planning continues

**Source**: 57.2 retro Q5 listed Phase 57+ candidate scope;57.3 confirmed as user-approved Tenant Settings bundle;**不**預寫 57.4 / 57.5 plan(rolling 紀律)

**Closure plan**:
1. Sprint 57.3 closure → Phase 57+ Frontend SaaS 2/N(N depends on rolling user approval)
2. retrospective.md Q5 lists Phase 57.x updated candidate scope based on 57.3 learnings:
   - Admin tenant console list view(medium-frontend ~12-15 hr × 0.65)— extends Tenant Settings to multi-tenant
   - Onboarding self-serve wizard — still defer pending backend self-serve API design
   - Feature flags admin UI(small-frontend ~5-8 hr × 0.65)— FeatureFlagsService 56.1 backend complete;UI gap
   - Audit log frontend view(small-frontend ~5-8 hr × 0.65)— governance/audit-query 53.5+ backend complete;UI gap
   - DR + WAL streaming(backend large multi-domain)— invisible-to-customer
   - GDPR partial(backend medium-backend)— EU pipeline driven
   - SaaS Stage 2(Stripe / 月結 / Status Page)— 多 sprint
3. User approval required per rolling planning 紀律;此 retro 不寫 57.4 plan task detail
4. Memory snapshot `memory/project_phase57_3_tenant_settings.md` + Phase 57+ Frontend SaaS summary entry to MEMORY.md index

---

## Definition of Done

- [ ] All 5 USs acceptance criteria met
- [ ] Backend `pytest` baseline 1574 → 1584+ (≥+10 from US-1+US-2)
- [ ] Backend `mypy --strict` 0 errors;source files 295 → 297+
- [ ] 8 V2 lints green(全包括 RLS gaps + sole_mutator + LLM SDK + promptbuilder)
- [ ] LLM SDK leak: 0 不變
- [ ] Frontend `npm run lint && npm run build` clean
- [ ] Frontend Vitest ≥+6 new tests pass(3 US-3 + 3 US-4)
- [ ] Playwright e2e 4 tests pass(2 view + 2 edit happy/error)
- [ ] Audit chain test:US-2 PATCH 後 audit_log 確認有 entry with action="tenant_settings_updated"
- [ ] Anti-pattern checklist 11 項對齐
- [ ] AD-Sprint-Plan-4 `mixed` 3rd application captured + verdict logged
- [ ] D1 RED finding fully closed(US-1 + US-2 backend endpoints production-ready)
- [ ] Day 0 三-prong 探勘 first fully-applied sprint observations documented in retro Q3
- [ ] PR opened, CI green (5 active checks 含 Frontend E2E chromium headless), solo-dev merged to main
- [ ] Closeout PR merged
- [ ] SITUATION-V2 + memory + CLAUDE.md updated to **Phase 57+ Frontend SaaS 2/N (Sprint 57.3 closed — Tenant Settings bundle)**
- [ ] Phase 57.x next-sprint candidates documented in retrospective Q5 (user approval required per rolling planning)

---

## References

- 16-frontend-design.md §Tenant Settings(authoritative spec for Tenant Settings page)
- 14-security-deep-dive.md §RBAC + §multi-tenant tenant_id propagation + §audit chain
- 09-db-schema-design.md(Tenant ORM model + meta_data JSONB field)
- 17-cross-category-interfaces.md(此 sprint 不新增 cross-category interface;消費既有 admin API + audit chain)
- 10-server-side-philosophy.md §原則 1 Server-Side First(tenant_id 由 backend 注入 + admin role 驗證)
- .claude/rules/sprint-workflow.md §Step 2.5 Day-0 三-prong 探勘 + §Common Risk Classes
- .claude/rules/file-header-convention.md(MHist 1-line max per AD-Lint-3 + char-count guidance per AD-Lint-MHist-Verbosity)
- .claude/rules/multi-tenant-data.md(tenant_id 強制 + RLS policy + audit chain)
- .claude/rules/code-quality.md(black + isort + mypy + flake8 + cross-platform unused-ignore pattern)
- .claude/rules/testing.md §Module-level Singleton Reset Pattern + §Pytest discovery
- Sprint 56.1 plan(Tenant ORM + lifecycle + provisioning + admin tenants endpoint set 既有)
- Sprint 56.2 plan(require_admin_platform_role 既有 + RBAC dependency pattern)
- Sprint 53.5 plan(governance frontend pattern + append_audit chain)
- Sprint 53.6 plan(chat_v2 frontend pattern + Playwright e2e auth fixture)
- Sprint 57.1 v2 plan + checklist (format template per AD-Sprint-Plan-1 + AD-Lint-2)
- Sprint 57.2 retrospective Q5 (Phase 57+ candidate scope user approval 2026-05-07)
- Sprint 57.3 v1 Day 0 探勘(aborted 2026-05-07 due to D1 RED — git history audit trail in this plan §Background + §Risks D1)

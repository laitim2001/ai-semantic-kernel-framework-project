# Sprint 57.1 — Phase 57+ SaaS Frontend 1st: Cost + SLA Dual Dashboard Bundle

> **Sprint Type**: Phase 57+ first sprint — SaaS Stage 1 frontend visible UX over Phase 56-58 backend stack;first medium-frontend scope class application;bundle 2 small dashboards into 1 medium sprint
> **Owner Categories**: §Frontend (16-frontend-design.md) / §SaaS Stage 1 frontend visibility (Phase 56-58 backend → first customer-facing UX) / consumes 56.3 SLA Monitor + Cost Ledger admin endpoints
> **Phase**: 57 (Frontend SaaS — 1/N sprint;follow-on candidates: Tenant Settings page / Onboarding self-serve wizard (requires backend re-design) / DR / GDPR;rolling planning per .claude/rules/sprint-workflow.md)
> **Workload**: 5 days (Day 0-4); bottom-up est ~16 hr → calibrated commit **~10 hr** (multiplier **0.65** per AD-Sprint-Plan-4 scope-class matrix `medium-frontend` 1st application baseline mid-band 0.60-0.70 — first data point;若 ratio ∈ [0.85, 1.20] band → 2-data-point window starts;若 outside → AD-Sprint-Plan-8 logged)
> **Branch**: `feature/sprint-57-1-cost-sla-dashboards`
> **Plan Authority**: This document (per CLAUDE.md §Sprint Execution Workflow)
> **Roadmap Source**: 16-frontend-design.md §Cost dashboard + §SLA dashboard + 15-saas-readiness.md §SaaS Stage 1 visibility + Sprint 56.3 retrospective Q5 (Phase 57+ candidate scope user-approved 2026-05-06) + Sprint 57.1 v1 abort 2026-05-06 (D7 onboarding API model mismatch user-redirected to Option D dual dashboard bundle)
> **AD logging (sub-scope)**: AD-Sprint-Plan-4 scope-class matrix `medium-frontend` 1st application baseline (no prior data point;0.65 mid-band starting convention);AD-Plan-4-Schema-Grep fold-in to sprint-workflow.md §Step 2.5 Prong 3 (promoted Sprint 55.6 / 3rd data point evidence Sprint 56.3 D6 — ~30-45 min process AD piggyback Day 0)

---

## Sprint Goal

Open the **first customer-facing UX surface** for Phase 56-58 SaaS Stage 1 backend stack by delivering 2 admin dashboards consuming 56.3 SLA Monitor + Cost Ledger endpoints in a single React + Playwright-validated bundle:

- **US-1**: Shared frontend dashboard infrastructure — `frontend/src/features/cost-dashboard/` + `frontend/src/features/sla-dashboard/` skeleton folders mirroring chat_v2 + governance per-feature folder pattern;shared `MonthPicker.tsx` component;admin role display gate(若非 ADMIN_TENANT / ADMIN_PLATFORM → show 403 message + back link);types.ts per feature
- **US-2**: Cost Dashboard — `pages/cost-dashboard/index.tsx` + `features/cost-dashboard/components/CostOverview.tsx`;consumes `GET /api/v1/admin/tenants/{tenant_id}/cost-summary?month=YYYY-MM`(56.3 endpoint);displays month total + per-cost-type breakdown(LLM input / LLM output / tool calls)+ per-provider breakdown(azure_openai / anthropic);loading + error UX;Zustand store(`costStore.ts`)+ service(`costService.ts`)
- **US-3**: SLA Dashboard — `pages/sla-dashboard/index.tsx` + `features/sla-dashboard/components/SLAOverview.tsx`;consumes `GET /api/v1/admin/tenants/{tenant_id}/sla-report?month=YYYY-MM`(56.3 endpoint);displays availability % / API p99 / loop p99(3 categories: 簡單/中等/複雜)/ HITL queue notification p99 / violations count;tier threshold 標記(Standard 99.5% / Enterprise 99.9% pass/fail visual);Zustand store(`slaStore.ts`)+ service(`slaService.ts`)
- **US-4**: Routing + App integration — App.tsx 加 `/cost-dashboard/*` + `/sla-dashboard/*` wildcard routes(per chat_v2 / governance / verification 既有 pattern);Home page nav 加 2 個 dashboard links(role-gated display);無新 BrowserRouter 結構變動
- **US-5**: Playwright e2e + closeout — 2 specs(`cost_dashboard.spec.ts` + `sla_dashboard.spec.ts`);各含 happy path(admin auth → load dashboard → see data)+ 1 error path(backend 500 retry recovery);retrospective + medium-frontend 1st app calibration verify + AD-Plan-4-Schema-Grep fold-in(Day 0 piggyback)+ Phase 57+ next-sprint candidates Q5

Sprint 結束後:
- (a) **Cost + SLA Dashboard 主流量 functional** — admin user 可 browse `/cost-dashboard` + `/sla-dashboard` → 選月份 → 看 56.3 backend 真實 metrics + cost ledger entries
- (b) **Frontend SaaS Stage 1 visible** — V2 22/22 + Phase 56-58 backend 3/3 第一次有 customer-facing UX surface(此前皆 backend-only)
- (c) **AD-Sprint-Plan-4 `medium-frontend` 1-data-point baseline** — 第一次 frontend sprint;若 ratio ∈ band → 1-data-point window opens(56.3 large multi-domain pattern);若 outside → AD-Sprint-Plan-8 logged
- (d) **AD-Plan-4-Schema-Grep fold-in done** — sprint-workflow.md §Step 2.5 含 Prong 3 Schema Verify formal section + 56.1 + 56.3 + 後續 sprints 共用此規範
- (e) **v1 abort audit trail captured** — Sprint 57.1 v1 onboarding wizard plan abort due to D7 backend model mismatch(self-serve assumption vs admin-driven reality);此 sprint v2 plan §Background + retrospective Q1 retain lesson 「跨域起草 plan-time grep 應更密」
- (f) **Phase 57+ rolling planning continues** — Sprint 57.1 retro Q5 列出 Phase 57+ 候選 next sprints(Onboarding 重設計需 backend self-serve API / Tenant Settings / DR / GDPR / Stripe);user approval required per rolling planning 紀律,**不寫** Sprint 57.2 plan task detail

**主流量驗收標準**:
- `npm run dev` → admin user browse `/cost-dashboard` → 選月份 → see total / per-cost-type / per-provider breakdown
- `npm run dev` → admin user browse `/sla-dashboard` → 選月份 → see availability + 4 latency metrics + violations count
- 56.3 backend `GET /admin/tenants/{id}/cost-summary` + `/sla-report` endpoints 收到正確 month query param + 返回正確 JSON(已存在 backend test 覆蓋 56.3)
- Playwright e2e 4 tests pass(2 happy + 2 error)< 30s each
- `npm run lint && npm run build` clean
- `npm run test` (Vitest unit) ≥ 6 new tests pass
- Backend pytest baseline 1557 unchanged(此 sprint 不動 backend)
- 8 V2 lints baseline unchanged

---

## Background

### V2 進度

- **22/22 sprints (100%) main progress completed** + **Phase 56-58 SaaS Stage 1 3/3 ✅ CLOSED** (Sprint 56.3 closed 2026-05-06)
- main HEAD: `55d2c157` (Sprint 56.3 closeout PR #102) — Day 0 verified
- pytest baseline 1557 / mypy --strict 0/293 source files / 8 V2 lints 8/8 green
- 56.3 calibration `large multi-domain` 0.55 mid-band 2nd application ratio **1.04 ✅** in band — `large multi-domain` 2-data-point mean 1.02 (KEEP 0.55 per AD-Sprint-Plan-4)
- 11-sprint window 7/11 in-band (53.7=1.01 / 55.2=1.10 / 55.5=1.14 / 55.6=0.92 / 56.1=1.00 / 56.2=1.17 / 56.3=1.04) — sustained ≥ 60% threshold for 2nd consecutive sprint
- **本 sprint = Phase 57+ SaaS Frontend 第 1 個 sprint v2** (1/N rolling;v1 onboarding wizard plan aborted 2026-05-06 Day 0 due to D7 backend model mismatch;user redirected to Option D dual dashboard bundle)

### 為什麼 57.1 v2 是 Cost + SLA dual dashboard bundle 而非 onboarding wizard / dashboards 單個

User approved 2026-05-06 session Option D(`Cost + SLA dual dashboard bundle` — abort onboarding wizard + redirect to 56.3 endpoints frontend visibility):

1. **v1 onboarding wizard abort root cause** — Day 0 Prong 2 content verify D7 揭露 56.1 onboarding API 實際是 admin-driven `POST /admin/tenants/` + `POST /admin/tenants/{id}/onboarding/{step}` 多步 advance(super-admin 逐步推進已有租戶),非 plan 假設的 self-serve `POST /onboarding/start` + `/complete` 模型;UX 模型差距 > 50% scope shift → abort + redraft per AD-Plan-1 sprint-workflow.md
2. **Cost + SLA dashboards 直接消費 56.3 已 production 的 endpoints** — `GET /admin/tenants/{tenant_id}/cost-summary` + `/sla-report` 56.3 已 closed;無 backend 變更需求;最低 dependency risk
3. **Bundle 落 medium-frontend 區間** — 單獨 cost dashboard ~5-8 hr / 單獨 sla dashboard ~5-8 hr / 共享 infra ~2 hr → bundle ~16 hr 落 medium-frontend (AD-Sprint-Plan-4 matrix 0.60-0.70 band);1st application baseline 取 0.65 mid-band
4. **校準 medium-frontend class 仍達成 v1 目標** — calibration matrix 4 active classes(audit 0.40 / mixed 0.60 / medium-backend 0.80 / large multi-domain 0.55)補完 frontend baseline;5 軸完整
5. **Onboarding 重設計 defer 至 Phase 57+ backend self-serve API design** — 自助 onboarding 涉及 unauth signup / email verification / PENDING tenant lifecycle / admin verify approval flow;屬 SaaS Stage 2 scope;此 sprint 不嘗試
6. **AD-Plan-4-Schema-Grep fold-in 仍 piggyback Day 0** — 此 sprint 不動 DB schema(全 frontend),Schema-Grep prong N/A 此 sprint 自身;但 fold-in to sprint-workflow.md §Step 2.5 Prong 3 是 mandatory process AD per 55.6 promotion + 56.3 D6 evidence;~30-45 min Day 0 piggyback

### 既有結構(Day 0 探勘 grep 將驗證以下假設;含 v1 已 verified findings)

⚠️ **以下 layout 是 plan-time 推斷;Day 0 grep 將 confirm 或 catalogue 為 D-finding**:

```
frontend/src/                                   # ✅ v1 D1-D6 已 verified;per-feature folder pattern
├── features/
│   ├── chat_v2/                                # ✅ existing (53.6)
│   ├── governance/                             # ✅ existing (53.5)
│   ├── cost-dashboard/                         # ❌ NEW (US-1 + US-2)
│   │   ├── components/CostOverview.tsx         # ❌ NEW
│   │   ├── components/CostBreakdownTable.tsx   # ❌ NEW
│   │   ├── services/costService.ts             # ❌ NEW (plain fetch + API_BASE per v1 D6)
│   │   ├── store/costStore.ts                  # ❌ NEW (Zustand per v1 D4 — no React Query)
│   │   └── types.ts                            # ❌ NEW
│   ├── sla-dashboard/                          # ❌ NEW (US-1 + US-3)
│   │   ├── components/SLAOverview.tsx          # ❌ NEW
│   │   ├── components/SLAMetricsCard.tsx       # ❌ NEW
│   │   ├── services/slaService.ts              # ❌ NEW
│   │   ├── store/slaStore.ts                   # ❌ NEW
│   │   └── types.ts                            # ❌ NEW
│   └── shared/                                 # ⚠️ verify Day 0;若無 → create OR put MonthPicker in cost-dashboard 共用
│       └── components/MonthPicker.tsx          # ❌ NEW (US-1 shared)
├── pages/
│   ├── chat-v2/index.tsx                       # ✅ existing (53.6)
│   ├── governance/index.tsx                    # ✅ existing (53.5)
│   ├── verification/index.tsx                  # ✅ existing
│   ├── cost-dashboard/index.tsx                # ❌ NEW (US-2)
│   └── sla-dashboard/index.tsx                 # ❌ NEW (US-3)
└── App.tsx                                     # ⚠️ MODIFY (US-4: add 2 wildcard routes + 2 nav links)

frontend/tests/
├── e2e/
│   ├── chat/, governance/                      # ✅ existing
│   ├── fixtures/                               # ✅ existing
│   ├── smoke.spec.ts                           # ✅ existing
│   ├── cost_dashboard.spec.ts                  # ❌ NEW (US-5)
│   └── sla_dashboard.spec.ts                   # ❌ NEW (US-5)
└── (Vitest unit tests location TBD per Day 0 verify — no existing pattern observed in v1探勘)
```

### Sprint 56.3 retrospective Q5 對齐確認

Sprint 56.3 retrospective Q5 列出 Phase 57+ candidate scope:
- Citus PoC standalone worktree (large research ~9-12 hr) ⛔ defer Phase 57+
- DR + WAL streaming (large multi-domain ~14-18 hr) ⛔ defer Phase 57+
- Compliance partial GDPR (medium-backend ~10-13 hr) ⛔ defer Phase 57+
- Frontend Onboarding Wizard UI ⛔ aborted 2026-05-06 v1 due to D7 backend model mismatch;defer Phase 57+ pending backend self-serve API design
- **Cost dashboard (small-frontend ~5-8 hr) ✅ 此 sprint US-2(bundle 化)**
- **SLA dashboard (small-frontend ~5-8 hr) ✅ 此 sprint US-3(bundle 化)**
- SaaS Stage 2 (Stripe / 月結 invoice / Status Page) ⛔ defer Phase 57++

### V2 紀律 9 項對齐確認

1. **Server-Side First** ✅ Cost + SLA dashboards 完全 frontend SPA;backend 56.3 admin endpoints 已 server-side;tenant_id 由 backend session-derive;auth via Bearer JWT(`require_admin_tenant_role` 既有)
2. **LLM Provider Neutrality** ✅ 此 sprint 不動 LLM 鏈路;dashboards 不呼叫 LLM API
3. **CC Reference 不照搬** ✅ Dashboards 為標準 SaaS UX pattern(non-CC);plain fetch + Zustand stack 既有(per v1 D4 — no React Query)
4. **17.md Single-source** ✅ 此 sprint 不新增 cross-category interface;SLA + Cost endpoint contracts 已 56.3 backend openapi schema 定義
5. **11+1 範疇歸屬** ✅ US-1~US-5 全 §Frontend(16-frontend-design.md);無範疇 1-12 backend module 變更;每檔案明確歸屬;無 AP-3
6. **04 anti-patterns** ✅ AP-3 範疇歸屬合規 / AP-4(Potemkin)— Dashboards 全有實際 wire-up + Playwright e2e 測試 / AP-6(Hybrid Bridge Debt)— 不為 Stage 2 預寫 abstraction / AP-9(Verification)— Playwright e2e 強制 verify 主流量 / AP-11(命名一致)— `cost-dashboard` / `sla-dashboard` 一致無 _v1 / _v2 後綴(雖然此 sprint 是 plan v2,but content scope is fresh — 非命名衝突)
7. **Sprint workflow** ✅ plan → checklist → Day 0 探勘(2 prongs;Schema-Grep N/A 但 fold-in to sprint-workflow.md is task)→ code → progress → retro;本文件依 56.3 plan 結構鏡射(14 sections / 5 days Day 0-4)
8. **File header convention** ✅ 所有 new 檔案含 file header docstring;modify 檔案加 Modification History entry;MHist 1-line max per AD-Lint-3
9. **Multi-tenant rule** ✅ Frontend 不直接讀寫 DB;tenant_id 由 backend JWT 注入(per 鐵律 3 API endpoint dependency);56.3 endpoints 已套用 RLS + tenant_isolation policy

---

## User Stories

### US-1: Shared Frontend Dashboard Infrastructure + Vitest Setup

**As** a SaaS platform admin
**I want** per-feature folder skeletons + MonthPicker + Vitest config(per D11 — 前端原無 unit test infra)mirroring chat_v2 + governance pattern
**So that** Cost + SLA dashboards have consistent UX chrome,code organization aligns with v1 D-findings(per-feature folder + plain fetch + Zustand),AND Vitest infra 為後續 frontend sprint 鋪路

**Acceptance**:
- `frontend/src/features/cost-dashboard/` + `sla-dashboard/` skeleton folders(components / services / store / types.ts)
- MonthPicker.tsx 位置 per Day 0 verdict(features/shared/components/ OR cost-dashboard/components/ 共用 import)
- types.ts per feature(CostSummaryResponse mirror 56.3 nested 2-level by_type per D9;SLAReportResponse mirror 56.3 flat fields per Day 0 verify)
- ~~Admin role display gate helper~~ — drop per D10 Option C(前端無 auth 機制;backend 56.3 endpoints 已 enforce `require_admin_platform_role`;前端僅顯示 401/403 error UX)
- **Vitest config + setup**(per D11 piggyback Day 0 OR Day 1 start):add vitest dev dependency + `vite.config.ts` test settings + `npm run test` script;1 smoke test 驗證 setup 工作
- DoD:Vitest can run + 0 errors

### US-2: Cost Dashboard

**As** a SaaS platform admin
**I want** a dashboard showing month-by-month cost breakdown by cost_type + sub_type
**So that** I can verify per-tenant LLM + tool spend matches expected billing per 56.3 Cost Ledger entries

**Acceptance**:
- `frontend/src/pages/cost-dashboard/index.tsx` page wrapper
- `frontend/src/features/cost-dashboard/components/CostOverview.tsx`(月份 picker + 總額 + per-cost-type breakdown 表)
- `CostBreakdownTable.tsx` table component(rows: cost_type [llm_input / llm_output / tool] + sub_type [provider_model / tool_name] + quantity + unit_cost_usd + total_cost_usd)
- `costService.ts` plain fetch + `_handleResponse<T>` helper mirroring governanceService.ts pattern;`API_BASE = "/api/v1/admin"`;`fetchCostSummary(tenantId, month)` function
- `costStore.ts` Zustand store(currentMonth / data / loading / error / fetchCostSummary action)
- Loading skeleton + error retry button per governanceService UX
- 2 unit tests(store action + service mock)

### US-3: SLA Dashboard

**As** a SaaS platform admin
**I want** a dashboard showing month SLA report with availability + 4 latency p99 categories + violations count
**So that** I can verify per-tenant SLA commitment(Standard 99.5% / Enterprise 99.9%)visually

**Acceptance**:
- `frontend/src/pages/sla-dashboard/index.tsx` page wrapper
- `frontend/src/features/sla-dashboard/components/SLAOverview.tsx`(月份 picker + 4 SLAMetricsCard 顯示)
- `SLAMetricsCard.tsx` card component(metric name / value / threshold / pass-fail color indicator)
- `slaService.ts` plain fetch mirroring costService pattern;`fetchSLAReport(tenantId, month)`
- `slaStore.ts` Zustand store
- Tier-aware threshold display(若 tenant.plan === Enterprise → 99.9% threshold;else Standard 99.5%)— Day 0 verify tenant plan field accessibility
- Violations count badge(red if > 0;green if 0)
- 2 unit tests(store action + threshold logic)

### US-4: Routing + App Integration

**As** the React app
**I want** 2 new wildcard routes + 2 nav links
**So that** admins can access dashboards without manual URL entry

**Acceptance**:
- `frontend/src/App.tsx` add `<Route path="/cost-dashboard/*" element={<CostDashboardPage />} />` + `<Route path="/sla-dashboard/*" element={<SLADashboardPage />} />`
- Home page(App.tsx Home component)add 2 nav `<Link>` entries — **always visible**(per D10 Option C:無前端 role gate;非授權用戶按下 link 後由 backend 401/403 + 前端 error UX 處理)
- ~~1 unit test for routing pattern~~ — drop per Option C(沒有 role logic 需測試;routing pattern 既有 chat-v2 / governance / verification 已驗證)

### US-5: Playwright E2E + Closeout Ceremony

**As** the V2 sprint executor
**I want** Playwright happy + error path tests for 2 dashboards + retrospective + AD-Sprint-Plan-4 medium-frontend 1st app calibration verify + AD-Plan-4-Schema-Grep fold-in to sprint-workflow.md §Step 2.5
**So that** Sprint 57.1 v2 closes Phase 57+ Frontend SaaS 1st sprint with full audit trail

**Acceptance**:
- `frontend/tests/e2e/cost_dashboard.spec.ts`:
  - happy path:admin auth → load `/cost-dashboard?month=2026-04` → assert total + table rows visible
  - error path:backend 500 → retry button + recovery on mock 200
- `frontend/tests/e2e/sla_dashboard.spec.ts`:
  - happy path:admin auth → load `/sla-dashboard?month=2026-04` → assert 4 metric cards visible
  - error path:backend 500 → retry recovery
- AD-Plan-4-Schema-Grep fold-in:edit `.claude/rules/sprint-workflow.md` §Step 2.5 to add Prong 3 Schema Verify formal section + 56.1 D26+D27 + 56.3 D6 evidence references + bump file MHist 1-line
- retrospective.md(6 必答 + AD-Sprint-Plan-4 medium-frontend 1st app calibration verify + v1 abort lesson Q1 sub-section + Phase 57+ next-sprint candidates Q5)
- Memory snapshot `memory/project_phase57_1_cost_sla_dashboards.md`
- SITUATION-V2 §9 + CLAUDE.md sync to **Phase 57+ SaaS Frontend 1/N (Sprint 57.1 closed — Cost + SLA dual dashboard bundle)**

---

## Technical Specifications

### Service Pattern (mirror 53.5 governanceService.ts;per v1 D6 plain fetch)

```typescript
// frontend/src/features/cost-dashboard/services/costService.ts
import type { CostSummaryResponse } from "../types";

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

export async function fetchCostSummary(
  tenantId: string,
  month: string,  // "YYYY-MM"
): Promise<CostSummaryResponse> {
  const response = await fetch(
    `${API_BASE}/tenants/${tenantId}/cost-summary?month=${month}`,
    { credentials: "include" },
  );
  return _handleResponse<CostSummaryResponse>(response);
}
```

### Zustand Store Pattern (mirror chat_v2/chatStore.ts)

```typescript
// frontend/src/features/cost-dashboard/store/costStore.ts
import { create } from "zustand";
import type { CostSummaryResponse } from "../types";
import { fetchCostSummary } from "../services/costService";

interface CostState {
  currentMonth: string;  // "YYYY-MM"
  data: CostSummaryResponse | null;
  loading: boolean;
  error: string | null;
  setMonth: (month: string) => void;
  loadData: (tenantId: string) => Promise<void>;
  reset: () => void;
}

export const useCostStore = create<CostState>((set, get) => ({
  currentMonth: new Date().toISOString().substring(0, 7),
  data: null,
  loading: false,
  error: null,
  setMonth: (month) => set({ currentMonth: month, data: null }),
  loadData: async (tenantId) => {
    set({ loading: true, error: null });
    try {
      const data = await fetchCostSummary(tenantId, get().currentMonth);
      set({ data, loading: false });
    } catch (err) {
      set({ error: (err as Error).message, loading: false });
    }
  },
  reset: () => set({ data: null, loading: false, error: null }),
}));
```

### Page Wrapper Pattern (mirror pages/governance/index.tsx)

```typescript
// frontend/src/pages/cost-dashboard/index.tsx
import { Routes, Route } from "react-router-dom";
import { CostOverview } from "../../features/cost-dashboard/components/CostOverview";

export default function CostDashboardPage() {
  return (
    <Routes>
      <Route index element={<CostOverview />} />
    </Routes>
  );
}
```

### Risk Class A/B/C all N/A

- Risk Class A: paths-filter retired by 55.6 Option Z;此 sprint 不適用
- Risk Class B: cross-platform mypy unused-ignore — N/A frontend-only
- Risk Class C: module-level singleton — N/A frontend (Zustand component-tree-scoped;Playwright per-test isolation)

### v1 Abort Lesson Capture

Sprint 57.1 v1(onboarding wizard)plan 起草 over-relied on memory snapshot 模糊術語(「onboarding API」)+ 標準 SaaS lens 假設 self-serve;Day 0 Prong 2 content verify D7 揭露 56.1 是 admin-driven multi-step advance 模型;> 50% scope shift → abort + redraft per AD-Plan-1。Lesson:跨域(frontend vs backend)plan-time grep should be MORE thorough,not less;memory 對 frontend 細節幾乎為零(governance + chat_v2 模式從未進過 memory snapshot)。

---

## Acceptance Criteria

### Sprint-Wide

- [ ] V2 主進度 22/22 (100%) 不變;Phase 56-58 SaaS Stage 1 backend 3/3 不變;Phase 57+ Frontend SaaS 1/N 啟動
- [ ] All 8 V2 lints green (frontend changes 不影響 backend lints)
- [ ] Backend pytest baseline 1557 不變
- [ ] Backend mypy --strict 0 errors 不變
- [ ] Backend LLM SDK leak: 0 不變
- [ ] Anti-pattern checklist 11 項對齐
- [ ] 5 active CI checks green(含 Frontend E2E chromium headless per 53.7 baseline)
- [ ] Frontend `npm run lint && npm run build` clean
- [ ] Frontend Vitest config + setup added(per D11 — 前端原無 Vitest);`npm run test` ≥ 3 new unit tests pass(cost store + cost service + sla store)
- [ ] Playwright e2e 4 tests pass(2 happy + 2 error paths)
- [ ] AD-Sprint-Plan-4 `medium-frontend` 1st application captured + verdict logged in retro Q2
- [ ] AD-Plan-4-Schema-Grep fold-in to sprint-workflow.md §Step 2.5 Prong 3 done(formal section + evidence references + MHist bump)
- [ ] v1 abort lesson captured in retro Q1(跨域 plan-time grep 應更密)
- [ ] D8-D13 Day 0 探勘 v2 D-findings catalogued in progress.md + plan §Risks updated(scope shift ~5% within band per Option C)

### Per-User-Story

詳見 §User Stories acceptance per US.

---

## Day-by-Day Plan

### Day 0 — Setup + Day-0 兩-prong 探勘 v2 + AD-Plan-4 fold-in + Pre-flight Verify

- 0.1 Branch + plan + checklist commit
- 0.2 Day-0 兩-prong 探勘 v2(per AD-Plan-3 promoted)— **Prong 1 Path Verify**:`frontend/src/features/cost-dashboard/` + `sla-dashboard/` 不存在(expect)/ `frontend/src/features/shared/` 是否已存在(若無 → MonthPicker 放 cost-dashboard 並由 sla-dashboard import)/ `frontend/src/pages/cost-dashboard/` + `sla-dashboard/` 不存在(expect)/ `frontend/tests/e2e/cost_dashboard.spec.ts` + `sla_dashboard.spec.ts` 不存在(expect)/ Vitest config 是否存在 + test 路徑慣例(若無 unit test infra → 加 setup 是 US-5 scope);**Prong 2 Content Verify**:56.3 backend `GET /admin/tenants/{id}/cost-summary` + `/sla-report` endpoints 真實簽名(grep `backend/src/api/v1/admin/cost_summary.py` + `backend/src/api/v1/admin/sla_reports.py`)/ Pydantic Response models(CostSummaryResponse / SLAReportResponse fields)/ 53.5 governanceService.ts plain fetch + `_handleResponse<T>` helper pattern 完整 reusable / chat_v2 chatStore.ts Zustand pattern 完整 reusable / App.tsx wildcard route pattern + Home Link nav pattern / admin role 前端判斷既有 hook(若無 → US-1 含 simple inline check)/ tenant.plan field 可取(若無 → SLA threshold 顯示 fallback 通用 99.5%)
- 0.3 **AD-Plan-4-Schema-Grep fold-in to sprint-workflow.md §Step 2.5 Prong 3** — edit `.claude/rules/sprint-workflow.md`;add formal "Prong 3 Schema Verify" subsection with description + grep query patterns table for column-level drift + ROI evidence (56.1 D26+D27 + 56.3 D6) + bump file MHist 1-line entry;commit as separate piggyback commit
- 0.4 Calibration multiplier pre-read(11-sprint window 7/11 in-band per 56.3 retro;`medium-frontend` 0-data-point 1st application;此 sprint 取 0.65 mid-band per 0.60-0.70 starting convention)
- 0.5 Pre-flight verify(backend pytest baseline 1557 / 8 V2 lints baseline / mypy baseline / LLM SDK leak baseline / frontend `npm run build` baseline / Playwright config sanity)
- 0.6 Day 0 progress.md commit + push;catalogue D-findings + v1 abort cross-reference;若 scope shift > 20% revise plan §Risks per AD-Plan-1 audit-trail

### Day 1 — US-1 Shared Infra + US-2 Cost Dashboard

- 1.1 `frontend/src/features/cost-dashboard/` skeleton(components/ services/ store/ types.ts)
- 1.2 `frontend/src/features/sla-dashboard/` skeleton(同上)
- 1.3 MonthPicker.tsx(features/shared/components/ OR cost-dashboard/components/ 視 Day 0 verdict)
- 1.4 `costService.ts` fetchCostSummary + _handleResponse helper
- 1.5 `costStore.ts` Zustand store + loadData action + types.ts
- 1.6 `CostOverview.tsx` + `CostBreakdownTable.tsx` 組件
- 1.7 `pages/cost-dashboard/index.tsx` page wrapper
- 1.8 1 Vitest unit test US-1 (MonthPicker)+ 2 Vitest unit test US-2(costStore action + costService mock)
- 1.9 `npm run lint && npm run build` clean
- 1.10 Day 1 progress.md + commit + push

### Day 2 — US-3 SLA Dashboard

- 2.1 `slaService.ts` fetchSLAReport + reuse _handleResponse helper(若 helper extract 為 shared util — Day 1 學習 decision)
- 2.2 `slaStore.ts` Zustand store + loadData action + types.ts
- 2.3 `SLAOverview.tsx` + `SLAMetricsCard.tsx` 組件
- 2.4 Tier-aware threshold display logic(讀 tenant.plan field 或 fallback 99.5%)
- 2.5 Violations count badge
- 2.6 `pages/sla-dashboard/index.tsx` page wrapper
- 2.7 2 Vitest unit test US-3(slaStore action + threshold logic)
- 2.8 `npm run lint && npm run build` clean
- 2.9 Day 2 progress.md + commit + push

### Day 3 — US-4 Routing + App Integration + Buffer

- 3.1 `frontend/src/App.tsx` add 2 wildcard routes(`/cost-dashboard/*` + `/sla-dashboard/*`)
- 3.2 Home page nav add 2 `<Link>` entries(role-gated display)
- 3.3 admin role 前端 display gate helper(useIsAdmin hook OR inline based on Day 0 verdict)
- 3.4 Update App.tsx file header MHist — `Sprint 57.1 — add /cost-dashboard + /sla-dashboard routes (US-4)`
- 3.5 1 Vitest unit test US-4(routing pattern smoke;Home renders nav links when admin)
- 3.6 Manual smoke test:start dev server + browse 2 dashboards + verify network calls hit 56.3 endpoints
- 3.7 Buffer for Day 1 / Day 2 follow-ups(若 e2e 預估 sprint Day 4 太緊 → Day 3 開始 e2e helper setup)
- 3.8 `npm run lint && npm run build` clean
- 3.9 Day 3 progress.md + commit + push

### Day 4 — US-5 Playwright E2E + Closeout Ceremony

- 4.1 `frontend/tests/e2e/cost_dashboard.spec.ts`(happy + error)
- 4.2 `frontend/tests/e2e/sla_dashboard.spec.ts`(happy + error)
- 4.3 Final pytest(backend baseline)+ frontend lint + build + Vitest + Playwright + LLM SDK leak verify
- 4.4 retrospective.md(6 必答 + AD-Sprint-Plan-4 medium-frontend 1st app calibration verify + v1 abort lesson Q1 sub-section + AD-Plan-4-Schema-Grep fold-in confirmation + Phase 57+ next-sprint candidates Q5)
- 4.5 Memory snapshot `memory/project_phase57_1_cost_sla_dashboards.md`
- 4.6 Open PR → CI green → solo-dev squash merge to main
- 4.7 Closeout PR(SITUATION-V2 §9 + CLAUDE.md + memory MEMORY.md index)
- 4.8 Final push + Phase 57+ Frontend SaaS 1/N ceremony note

---

## File Change List

| File | Status | Lines (est) |
|------|--------|-------------|
| `frontend/src/features/cost-dashboard/components/CostOverview.tsx` | NEW | ~80 |
| `frontend/src/features/cost-dashboard/components/CostBreakdownTable.tsx` | NEW | ~80 |
| `frontend/src/features/cost-dashboard/services/costService.ts` | NEW | ~50 |
| `frontend/src/features/cost-dashboard/store/costStore.ts` | NEW | ~60 |
| `frontend/src/features/cost-dashboard/types.ts` | NEW | ~30 |
| `frontend/src/features/sla-dashboard/components/SLAOverview.tsx` | NEW | ~80 |
| `frontend/src/features/sla-dashboard/components/SLAMetricsCard.tsx` | NEW | ~60 |
| `frontend/src/features/sla-dashboard/services/slaService.ts` | NEW | ~50 |
| `frontend/src/features/sla-dashboard/store/slaStore.ts` | NEW | ~60 |
| `frontend/src/features/sla-dashboard/types.ts` | NEW | ~30 |
| `frontend/src/features/shared/components/MonthPicker.tsx` (or cost-dashboard 共用) | NEW | ~50 |
| `frontend/src/pages/cost-dashboard/index.tsx` | NEW | ~30 |
| `frontend/src/pages/sla-dashboard/index.tsx` | NEW | ~30 |
| `frontend/src/App.tsx` | MODIFIED | +15 |
| `frontend/tests/e2e/cost_dashboard.spec.ts` | NEW | ~100 |
| `frontend/tests/e2e/sla_dashboard.spec.ts` | NEW | ~100 |
| Vitest unit tests (~6 new) | NEW | ~250 |
| `.claude/rules/sprint-workflow.md` | MODIFIED (Day 0 piggyback) | +60 |
| `docs/.../sprint-57-1/{progress,retrospective}.md` | NEW | ~600 |
| `memory/project_phase57_1_cost_sla_dashboards.md` | NEW | ~60 |

**Total**: ~750 source LOC + ~450 test LOC + ~660 docs LOC

---

## Dependencies & Risks

### Dependencies (must exist before code starts)

- ⚠️ Phase 56.3 backend `GET /admin/tenants/{id}/cost-summary` endpoint — Day 0 grep verify (closed by 56.3 US-3+US-4)
- ⚠️ Phase 56.3 backend `GET /admin/tenants/{id}/sla-report` endpoint — Day 0 grep verify (closed by 56.3 US-1+US-2)
- ⚠️ 56.3 Pydantic CostSummaryResponse + SLAReportResponse field 結構 — Day 0 grep verify(若不符 plan 假設 → types.ts adjust;~5% scope shift)
- ⚠️ 53.5 governanceService.ts plain fetch + `_handleResponse<T>` 既有 pattern — Day 0 grep verify(per v1 D6 既已驗證 pattern,confirm 仍 reusable)
- ⚠️ chat_v2 chatStore.ts Zustand pattern reusable — Day 0 verify
- ⚠️ App.tsx wildcard route pattern — Day 0 verify(per v1 D3 既已驗證,confirm)
- ⚠️ Vitest unit test infrastructure — Day 0 verify(若無 → US-5 scope 含 minimal Vitest config setup;~30 min)
- ⚠️ Admin role 前端判斷 hook — Day 0 grep verify governance / chat_v2 既有 pattern reusable
- ⚠️ tenant.plan field 客戶端可訪問 — Day 0 verify(若僅 backend → SLA threshold 顯示 fallback 99.5% 通用值)

### Risk Classes (per sprint-workflow.md §Common Risk Classes)

**Risk Class A (paths-filter vs required_status_checks)**: 已 closed by 55.6 Option Z (paths-filter retired 永久);此 sprint 不適用。

**Risk Class B (cross-platform mypy unused-ignore)**: N/A — frontend-only sprint;TypeScript 不需要 mypy ignore patterns。

**Risk Class C (module-level singleton across event loops)**: N/A — frontend-only sprint;Zustand stores 是 component-tree-scoped。

### Day 0 探勘 D-findings v2 (catalogued during Day 0 兩-prong 探勘)

> v1 D-findings 已 carry-forward: D1 per-feature folder + D2 pages/{feature}/index.tsx + D3 wildcard route + D4 no React Query / use plain fetch + D5 no form library + D6 plain fetch + _handleResponse helper + D7 (v1-only;onboarding API model);此 sprint v2 Day 0 探勘 catalogue 新 D-findings (D8+) below。

**D8** — 56.3 cost-summary + sla-report endpoints auth = `require_admin_platform_role`(super-admin only),非 plan 假設的 `admin_tenant_role`。Implication:dashboards 是 super-admin tools,不是 tenant-admin self-service。前端 admin gate 邏輯(若加)應檢查 ADMIN_PLATFORM。

**D9** — `CostSummaryResponse.by_type` 是 `dict[str, dict[str, AggregatedSliceResponse]]` 巢狀 2 層 dict(type→sub_type→{quantity / total_cost_usd / entry_count}),非 plan 假設的 flat breakdown。Implication:types.ts 鏡射 nested 結構;CostBreakdownTable 渲染需 2 層 iteration。

**D10** — 前端完全沒有 auth/role 機制(useIsAdmin / useCurrentUser / ADMIN_PLATFORM 全 0 results)。Implication per Option C:跳過前端 auth gate;dashboards 直接 render;依賴 backend 56.3 endpoints 401/403 返回時前端顯示 error UX(retry button / 「Permission required」 message)。Saved ~30 min from US-1 admin gate task。

**D11** — 前端沒有 Vitest(package.json 0 vitest dep / script;只有 Playwright)。Implication per Option C:Day 0 piggyback 加 Vitest config + setup(~1 hr);後續 frontend sprint 受益(Tenant Settings / Onboarding console 等候選 sprint 預備測試基礎建設)。3 unit tests(2 cost + 1 sla)+ 4 e2e = 7 total tests。

**D12** — App.tsx Home 是 49.1 placeholder(plain `<Link>` list 無 auth context;comment 說 「Phase 50.2 extended」 each phase 自然延伸);Implication:加 2 個 dashboard `<Link>` 到 Home 自然 fit existing pattern,不需新組件;US-4 nav 任務 simplification。

**D13** — Frontend Vite config proxy `/api/v1/health` to `localhost:8001`(non-blocking note;CLAUDE.md backend default 8000)。Implication:catalogue note;此 sprint 不修改 vite.config(可能歷史遺留 OR backend 多 port 配置);若 dashboard fetch 觸到 8001 vs 8000 mismatch → US-2/3 service.ts 需 explicit port note 在 Day 1 smoke test 確認。

**Cumulative scope shift** ≈ +1 hr (Vitest setup) + 15 min (D9 nested types) - 30 min (D10 auth gate dropped) + 5 min (D8 role rename) = **+50 min ≈ +5%**;< 20% threshold per AD-Plan-1 → continue Day 1 with risks noted(no plan re-version required)。

### Sprint-specific Risks

| Risk | Mitigation |
|------|-----------|
| 56.3 cost-summary / sla-report endpoint Pydantic Response 與 plan-time 假設不符 | Day 0 grep verify;adjust types.ts;若 schema 大改 → US-2 / US-3 scope +30 min |
| `features/shared/` 不存在 | Day 0 verdict — fallback 將 MonthPicker 放 cost-dashboard 共用 import path;不引入新目錄 violating YAGNI |
| Vitest unit test infra 不存在 | Day 0 verify;若無 → US-5 scope 含 minimal Vitest config;若 existing 既有 Vitest test → mirror pattern |
| tenant.plan 前端不可訪問 | SLA Dashboard threshold fallback 顯示 99.5% 通用值;不阻塞 |
| Playwright e2e admin auth setup 複雜 | Mirror 53.6 + 53.7 既有 e2e auth fixture pattern;若 fixtures/admin_auth.ts 不存在 → US-5 scope +30 min add fixture |
| `medium-frontend` 0.65 mult 1st app ratio outside band | 若 ratio > 1.20 → AD-Sprint-Plan-8 raise(0.65 → 0.75);若 < 0.85 → AD-Sprint-Plan-8 reduce(0.65 → 0.55);each case logged in retro Q2 |
| AD-Plan-4-Schema-Grep fold-in 寫成過詳細 reflection | 嚴格 1-page section limit per existing §Step 2.5 length;5-row drift class table 加 1 列 Schema Drift;不重寫 §Step 2.5 結構 |
| v1 abort lesson capture 過於聚焦 onboarding 模型差距而忘了 broader process insight | retro Q1 sub-section 寫:跨域 plan-time grep 應更密 + memory 對 frontend 細節零基礎 + AD-Plan-3 兩-prong Day 0 探勘 ROI 顯著 |

---

## Workload

> **Bottom-up est ~16 hr → calibrated commit ~10 hr (multiplier 0.65 per AD-Sprint-Plan-4 scope-class matrix `medium-frontend` 1st application baseline mid-band)**
> **11-sprint window 7/11 in-band(`medium-frontend` 0-data-point;此 sprint = 1st)** — `medium-frontend` 從 AD-Sprint-Plan-4 matrix 取 0.60-0.70 band, 取 0.65 mid (per 1st application convention)

| US | Bottom-up (hr) |
|----|---------------|
| US-1 Shared infra(skeleton folders + MonthPicker + admin gate + types + 1 test) | 2 |
| US-2 Cost Dashboard(service + store + 2 components + page + 2 tests) | 5 |
| US-3 SLA Dashboard(service + store + 2 components + page + threshold logic + 2 tests) | 5 |
| US-4 Routing + Home nav(App.tsx 修改 + 1 test + manual smoke) | 1 |
| US-5 Playwright e2e(2 specs × 2 paths)+ closeout(retro + ceremony + AD-Plan-4 fold-in + memory + closeout PR + v1 abort lesson capture) | 3 |
| **Total bottom-up** | **16** |
| **× 0.65 calibrated** | **10.4 ≈ 10** |

Day 4 retrospective Q2 must verify: `actual_total_hr / 10 → ratio` compared to [0.85, 1.20] band;document delta + log calibration verdict for `medium-frontend` class 1st data point;若 ratio in band → 1-data-point window opens;若 outside → AD-Sprint-Plan-8 logged for next-app multiplier adjustment。

---

## Out of Scope

- ❌ Onboarding wizard(self-serve 模型)— Phase 57+ pending backend self-serve API design (Stage 2 scope candidate)
- ❌ Admin tenant console (list / manage / advance step UI for 56.1 admin-driven onboarding)— Phase 57+ separate sprint
- ❌ Tenant Settings page(beyond admin dashboards)— Phase 57+
- ❌ Cost / SLA charts / time-series graphs — 此 sprint table-only;Phase 57++ visualization
- ❌ Cost / SLA export to CSV — Phase 57++
- ❌ Cost / SLA alerting UI / threshold breach notification — Phase 57++(backend stub already exists in 56.3)
- ❌ i18n / localization — 此 sprint English-only
- ❌ WCAG accessibility full audit — basic keyboard nav + label association 即可
- ❌ Mobile responsive — desktop-first
- ❌ Stripe checkout / 月結 invoice UI — Phase 57++ Stage 2
- ❌ Customer-facing Status Page — Phase 57++ Stage 2
- ❌ DR / WAL streaming UI — backend infra Phase 57+ separate sprint
- ❌ Compliance partial GDPR right-to-erasure UI — Phase 57+ separate sprint (legal-driven)
- ❌ Citus PoC frontend — N/A
- ❌ Multi-tenant tenant switcher in admin nav — Phase 57++(此 sprint admin acts on single tenant context per JWT)
- ❌ Cost / SLA dashboard cross-tenant aggregation view (platform admin global view)— Phase 57++

---

## AD Carryover Sub-Scope

### AD-Sprint-Plan-4 `medium-frontend` 1st application

**Source**: Sprint 55.3 retrospective Q2 (calibration matrix proposed) → 56.1+56.2+56.3 large multi-domain + mixed + medium-backend classes 各 ≥ 1-data-point baseline;`medium-frontend` 之前無 frontend sprint → 0-data-point;此 sprint 為 1st application(v1 onboarding wizard plan aborted Day 0;v2 dual dashboard bundle 同 medium-frontend class)

**Closure plan**:
1. Sprint 57.1 v2 plan §Workload uses **0.65** for `medium-frontend` class (1st application;mid-band 0.60-0.70 per starting convention)
2. Day 4 retrospective Q2 computes `actual / 10`
3. If ratio ∈ [0.85, 1.20] → record `medium-frontend` 1-data-point baseline;1-data-point window opens
4. If ratio < 0.85 → log AD-Sprint-Plan-8 (lower 0.65 → 0.55 for next medium-frontend sprint)
5. If ratio > 1.20 → log AD-Sprint-Plan-8 (raise 0.65 → 0.75)
6. medium-frontend window 從 0 → 1 data point;3 data points 之前不調整 mid-band

### AD-Plan-4-Schema-Grep fold-in to sprint-workflow.md §Step 2.5 Prong 3

**Source**: Sprint 55.6 promoted AD-Plan-4-Schema-Grep candidate to validated rule via fold-in commitment(promoted but not yet folded);Sprint 56.3 D6 = 3rd data point evidence(sessions.total_cost_usd Day-0 catch saved ~1 hr;ROI 8×);now ready to fold into sprint-workflow.md formal section

**Closure plan**(piggyback Day 0 Step 0.3;~30-45 min):
1. Edit `.claude/rules/sprint-workflow.md`:
   - In §Step 2.5 (existing Prong 1 Path Verify + Prong 2 Content Verify):add **Prong 3 Schema Verify** subsection
   - Prong 3 description:column-level grep on new DB tables / migrations / ORM models for column drift between plan-time assumed schema vs reality
   - Add 5-row drift class table extending existing pattern in Prong 2(adapt to column-level)
   - Cross-references:56.1 D26+D27 + 56.3 D6 evidence
   - ROI evidence sub-section:3 sprints catch column drift Day-0 saved ~3-4 hr cumulatively
2. Bump file MHist 1-line entry per .claude/rules/file-header-convention.md char-count budget
3. Commit as separate piggyback commit(distinguishable from sprint US commits)
4. Sprint 57.1 retro Q3:confirm fold-in committed + sprint-workflow.md L count delta + future sprints onwards Day 0 探勘 includes Prong 3 by default

### v1 Abort Lesson Capture (process-level)

**Source**: Sprint 57.1 v1 plan(onboarding wizard)abort 2026-05-06 Day 0 due to D7 backend API model mismatch(plan assumed self-serve `POST /onboarding/start + /complete` but reality is admin-driven `POST /admin/tenants/{id}/onboarding/{step}` multi-step advance);scope shift > 50% per AD-Plan-1 → abort + redraft + re-confirm with user

**Closure plan**:
1. Sprint 57.1 v2 plan §Background § "為什麼 57.1 v2 是 Cost + SLA dual dashboard bundle" sub-section already captures abort context
2. retrospective Q1 sub-section (process insight, not just sprint-internal):
   - 跨域(frontend vs backend)plan-time grep 應更密
   - Memory 對 frontend 細節幾乎為零;不可信賴
   - 標準 SaaS lens 假設(self-serve onboarding)在 enterprise admin-driven 場景不適用
   - AD-Plan-3 兩-prong 探勘運作正常(Day 0 catch ~ 1 hr cost vs Day 2 catch 8-10 hr cost;ROI 顯著)
   - 跨域第一次踏入新領域時,plan-time grep should be MORE thorough,not less
3. retrospective Q4 actionable improvement:future cross-domain sprint(下次 frontend sprint OR 之後 first-of-domain sprint):plan §Background 加 mandatory check 「plan-time grep 同新領域 ≥ 5 keywords / dependencies / patterns」

### Phase 57+ Frontend SaaS rolling planning

**Source**: 56.3 retro Q5 listed Phase 57+ candidate scope;57.1 v1 aborted;v2 confirmed as user-approved Option D;**不**預寫 57.2 / 57.3 / ... plan(rolling 紀律)

**Closure plan**:
1. Sprint 57.1 v2 closure → Phase 57+ Frontend SaaS 1/N(N depends on rolling user approval)
2. retrospective.md Q5 lists Phase 57.x updated candidate scope based on 57.1 learnings:
   - Tenant Settings page(medium-frontend ~10-13 hr)— mirror dashboards patterns
   - Onboarding self-serve wizard — defer pending backend self-serve API design (Stage 2 scope)
   - Admin tenant console (list / manage existing 56.1 admin-driven onboarding flow)— medium-frontend ~10-13 hr
   - DR + WAL streaming(backend large multi-domain)— invisible-to-customer
   - GDPR partial(backend medium-backend)— EU pipeline driven
   - SaaS Stage 2(Stripe / 月結 / Status Page)— 多 sprint
3. User approval required per rolling planning 紀律;此 retro 不寫 57.2 plan task detail
4. Memory snapshot `memory/project_phase57_1_cost_sla_dashboards.md` + Phase 57 Frontend SaaS summary entry to MEMORY.md index

---

## Definition of Done

- [ ] All 5 USs acceptance criteria met
- [ ] Frontend `npm run lint && npm run build` clean
- [ ] Frontend `npm run test` (Vitest unit) ≥ 6 new tests pass
- [ ] Playwright e2e 4 tests pass(2 happy + 2 error paths)
- [ ] Backend pytest baseline 1557 不變
- [ ] Backend mypy --strict 0 errors 不變
- [ ] 8 V2 lints green(backend baseline 不變)
- [ ] LLM SDK leak: 0 不變
- [ ] Anti-pattern checklist 11 項對齐
- [ ] AD-Sprint-Plan-4 `medium-frontend` 1st application captured + verdict logged
- [ ] AD-Plan-4-Schema-Grep fold-in to sprint-workflow.md §Step 2.5 Prong 3 done
- [ ] v1 abort lesson captured in retro Q1 sub-section
- [ ] PR opened, CI green (5 active checks 含 Frontend E2E chromium headless), solo-dev merged to main
- [ ] Closeout PR merged
- [ ] SITUATION-V2 + memory + CLAUDE.md updated to **Phase 57+ Frontend SaaS 1/N (Sprint 57.1 closed — Cost + SLA dual dashboard bundle)**
- [ ] Phase 57.x next-sprint candidates documented in retrospective Q5 (user approval required per rolling planning)

---

## References

- 16-frontend-design.md §Cost dashboard + §SLA dashboard(authoritative spec for 2 dashboards)
- 15-saas-readiness.md §SaaS Stage 1 frontend visibility
- 17-cross-category-interfaces.md(此 sprint 不新增 cross-category interface;消費既有)
- 10-server-side-philosophy.md §原則 1 Server-Side First(tenant_id 由 backend 注入)
- 14-security-deep-dive.md §RBAC + §multi-tenant tenant_id propagation
- .claude/rules/sprint-workflow.md §Step 2.5 Day-0 兩-prong 探勘 + §Common Risk Classes(此 sprint Day 0 piggyback edit)
- .claude/rules/file-header-convention.md(MHist 1-line max per AD-Lint-3 + char-count guidance per AD-Lint-MHist-Verbosity)
- .claude/rules/frontend-react.md(React component conventions + Zustand patterns)
- .claude/rules/testing.md
- Sprint 56.3 plan + checklist (format template per AD-Sprint-Plan-1 + AD-Lint-2)
- Sprint 56.3 retrospective Q5 (Phase 57+ candidate scope user approval 2026-05-06)
- Sprint 57.1 v1 plan + checklist (aborted 2026-05-06 Day 0 due to D7 backend model mismatch — git history deleted but audit trail in this plan §Background + retrospective Q1)
- Sprint 53.5 plan (governance frontend pattern reference for service + types + components)
- Sprint 53.6 plan (chat_v2 frontend pattern + Playwright e2e pattern reference)
- Sprint 53.7 (Frontend E2E chromium headless required CI check)

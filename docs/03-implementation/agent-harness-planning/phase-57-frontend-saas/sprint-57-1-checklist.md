# Sprint 57.1 — Phase 57+ SaaS Frontend 1st: Cost + SLA Dual Dashboard Bundle — Checklist

**Plan**: [sprint-57-1-plan.md](sprint-57-1-plan.md)
**Branch**: `feature/sprint-57-1-cost-sla-dashboards`
**Day count**: 5 (Day 0-4) | **Bottom-up est**: ~16 hr | **Calibrated commit**: ~10 hr (multiplier **0.65** per AD-Sprint-Plan-4 scope-class matrix `medium-frontend` 1st application baseline mid-band 0.60-0.70 — first data point)

> **格式遵守**: 每 Day 同 56.3 結構(progress.md update + sanity + commit + verify CI)。每 task 3-6 sub-bullets(case / DoD / Verify command)。Per AD-Lint-2 (53.7) — 不寫 per-day calibrated hour targets;只寫 sprint-aggregate calibration verify in retro。Per AD-Plan-3 promoted (55.6) — Day 0 兩-prong 探勘(Path Verify + Content Verify)是 mandatory;Schema-Grep N/A 此 sprint(無 DB schema 變更)但 fold-in to sprint-workflow.md §Step 2.5 Prong 3 是 piggyback Day 0 task。Day count 5(scope-difference via content not structure)— 對比 56.3 24 hr/5 days,此 sprint 16 hr/5 days(輕量 frontend bundle sprint)。
> **v1 abort 上下文**: Sprint 57.1 v1(onboarding wizard)plan aborted 2026-05-06 Day 0 due to D7 backend API model mismatch;user redirected to Option D dual dashboard bundle;v1 D1-D7 findings carry-forward audit trail in plan §Background。

---

## Day 0 — Setup + Day-0 兩-prong 探勘 v2 + AD-Plan-4 fold-in + Pre-flight Verify

### 0.1 Branch + plan + checklist commit
- [ ] **Verify on feature branch + clean** — `git status --short` empty(except docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/);`git branch --show-current` returns `feature/sprint-57-1-cost-sla-dashboards`
- [ ] **Confirm main HEAD baseline** — `git log main --oneline -1` returns `55d2c157`(post-PR #102 56.3 closeout)
- [ ] **Stage + commit plan + checklist + push branch** — commit msg `chore(docs, sprint-57-1): plan + checklist for Phase 57+ Cost + SLA Dual Dashboard Bundle (v2 after v1 onboarding abort)`;push -u origin

### 0.2 Day-0 兩-prong 探勘 v2 — verify plan §Technical Spec assertions against actual repo state

Per AD-Plan-3 promoted (55.6) — Prong 1 Path Verify + Prong 2 Content Verify;catalogue D-findings v2(D8+;v1 D1-D7 carry-forward).

**Prong 1: Path Verify (existence checks)**
- [ ] **Verify `frontend/src/features/cost-dashboard/` not exists** — Glob check (expect: not exist)
- [ ] **Verify `frontend/src/features/sla-dashboard/` not exists** — Glob check (expect: not exist)
- [ ] **Verify `frontend/src/features/shared/` exists?** — Glob check;catalogue verdict(若不存在 → MonthPicker 放 cost-dashboard/components/ 由 sla-dashboard import)
- [ ] **Verify `frontend/src/pages/cost-dashboard/` + `sla-dashboard/` not exist** — Glob check (expect: not exist)
- [ ] **Verify `frontend/tests/e2e/cost_dashboard.spec.ts` + `sla_dashboard.spec.ts` not exist** — Glob check
- [ ] **Verify Vitest config + test path** — `cat frontend/vite.config.ts` + `cat frontend/package.json | grep -A 1 vitest` confirm Vitest setup;若無 → US-5 scope 含 minimal Vitest config setup
- [ ] **Verify Playwright e2e fixtures structure** — `ls frontend/tests/e2e/fixtures/` confirm available auth fixtures(per 53.6 + 53.7 baseline)

**Prong 2: Content Verify (semantic checks)**
- [ ] **Verify 56.3 `GET /admin/tenants/{tenant_id}/cost-summary` endpoint exists** — `grep -B 2 -A 30 "cost-summary\|cost_summary" backend/src/api/v1/admin/cost_summary.py` confirm endpoint signature + Pydantic Response model fields
- [ ] **Verify 56.3 `GET /admin/tenants/{tenant_id}/sla-report` endpoint exists** — `grep -B 2 -A 30 "sla-report\|sla_reports" backend/src/api/v1/admin/sla_reports.py` confirm endpoint signature + SLAReportResponse fields
- [ ] **Verify CostSummaryResponse + SLAReportResponse Pydantic schemas** — extract field names + types;types.ts 將 mirror;若 plan 假設不符 → catalogue D-finding + types.ts adjust scope
- [ ] **Verify 53.5 governanceService.ts plain fetch + `_handleResponse<T>` helper exists + reusable** — `head -60 frontend/src/features/governance/services/governanceService.ts` confirm pattern reusable
- [ ] **Verify chat_v2 chatStore.ts Zustand pattern reusable** — `head -50 frontend/src/features/chat_v2/store/chatStore.ts` confirm `create()` + state + actions pattern
- [ ] **Verify App.tsx wildcard route pattern** — `grep -B 2 -A 5 "Routes\|Route path" frontend/src/App.tsx` confirm `/foo/*` element pattern
- [ ] **Verify Home page nav `<Link>` pattern in App.tsx** — `grep -B 2 -A 3 "<Link" frontend/src/App.tsx` confirm 既有 nav structure
- [ ] **Verify admin role 前端判斷 hook** — `grep -rn "useIsAdmin\|useCurrentUser\|roles\|admin_role" frontend/src/features/governance/ frontend/src/features/chat_v2/` 找既有 pattern;若無 → US-1 含 inline check
- [ ] **Verify tenant.plan field 客戶端可訪問** — `grep -rn "plan\|TenantPlan\|enterprise" frontend/src/features/governance/ frontend/src/api/` 找 client 是否能 retrieve;若不可 → US-3 SLA threshold fallback 99.5% 通用值

**Catalogue findings**
- [ ] **Catalogue all D-findings v2 (D8+) in progress.md** — format `D{N}` ID + Finding + Implication;link to plan §Risks update if scope shift > 20%
- [ ] **Cross-reference v1 D1-D7** — progress.md Day 0 entry section 「v1 D-findings carry-forward」 list D1-D7 + status verified
- [ ] **Decide go/no-go** — findings shift scope ≤ 20% → continue Day 1;20-50% → revise plan §Acceptance + §Workload + re-confirm with user;> 50% → abort sprint redraft(per AD-Plan-1)

### 0.3 AD-Plan-4-Schema-Grep fold-in to sprint-workflow.md §Step 2.5 Prong 3 (piggyback)
- [ ] **Read existing `.claude/rules/sprint-workflow.md` §Step 2.5** — confirm Prong 1 + Prong 2 current content;capture line range for new Prong 3 insertion
- [ ] **Edit sprint-workflow.md §Step 2.5** — add Prong 3 Schema Verify subsection per plan §AD Carryover Sub-Scope:
  - Prong 3 description (column-level grep on new DB tables / migrations / ORM models)
  - 5-row drift class table extending Prong 2 pattern (adapt to column-level)
  - Cross-references 56.1 D26+D27 + 56.3 D6 evidence
  - ROI evidence sub-section (3 sprints catch column drift Day-0 saved ~3-4 hr cumulatively)
- [ ] **Bump file MHist 1-line** — per AD-Lint-3 char-count budget;e.g. `2026-MM-DD: Sprint 57.1 Day 0 — fold-in AD-Plan-4-Schema-Grep §Step 2.5 Prong 3 (closes promotion)`
- [ ] **Stage + commit as separate piggyback** — commit msg `docs(rules, sprint-57-1): fold-in AD-Plan-4-Schema-Grep §Step 2.5 Prong 3 (closes 55.6 promotion + 56.3 3rd evidence)`
- DoD: sprint-workflow.md L count delta documented in Day 0 progress.md
- Verify: `wc -l .claude/rules/sprint-workflow.md` 對比 pre-edit baseline

### 0.4 Calibration multiplier pre-read
- [ ] **Read 56.3 retrospective Q2** — confirm 11-sprint window 7/11 in-band (53.7=1.01 / 55.2=1.10 / 55.5=1.14 / 55.6=0.92 / 56.1=1.00 / 56.2=1.17 / 56.3=1.04);large multi-domain 2-data-point mean 1.02
- [ ] **Confirm AD-Sprint-Plan-4 scope-class matrix** — `medium-frontend` band 0.60-0.70(starting convention);0-data-point baseline;此 sprint 為 1st application 取 0.65 mid-band
- [ ] **Compute 57.1 v2 bottom-up** — 16 hr × 0.65 = 10.4 ≈ 10 hr commit
- [ ] **Document predicted vs banked** — `medium-frontend` 1st application;若此 sprint ratio ∈ band → 1-data-point window opens;若 outside → AD-Sprint-Plan-8 logged

### 0.5 Pre-flight verify (main green baseline)
- [ ] **pytest collect baseline** — expect `1557 collected` (per 56.3 closeout main HEAD)
- [ ] **8 V2 lints via run_all.py** — `python scripts/lint/run_all.py` → 8/8 green
- [ ] **Backend full pytest baseline** — `python -m pytest` → 1557 passed / 4 skipped / 0 fail
- [ ] **mypy --strict baseline** — `python -m mypy backend/src --strict` → 0 errors / 293 source files
- [ ] **LLM SDK leak baseline** — `grep -rn "^(from |import )(openai|anthropic|agent_framework)" backend/src/agent_harness backend/src/business_domain backend/src/platform_layer backend/src/core` → 0
- [ ] **Frontend `npm run build` baseline** — `cd frontend && npm run build` → success;catalogue baseline build time
- [ ] **Frontend `npm run lint` baseline** — `cd frontend && npm run lint` → 0 errors
- [ ] **Playwright baseline** — `cd frontend && npx playwright test --list 2>&1 | head -10` confirm existing spec file count(53.6 + 53.7 baseline)

### 0.6 Day 0 progress.md
- [ ] **Create `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-1/progress.md`** — Day 0 entry with探勘 findings v2 + v1 D1-D7 carry-forward + AD-Plan-4 fold-in confirmation + baseline + Day 1 plan + scope shifts (if any)
- [ ] **Commit + push Day 0** — commit msg `docs(sprint-57-1): Day 0 progress + 兩-prong 探勘 v2 baseline + AD-Plan-4 fold-in + v1 abort cross-reference`

---

## Day 1 — US-1 Shared Infra + US-2 Cost Dashboard

### 1.1 Cost-dashboard + sla-dashboard skeleton folders
- [ ] **Create `frontend/src/features/cost-dashboard/{components,services,store}/`** + `types.ts`
- [ ] **Create `frontend/src/features/sla-dashboard/{components,services,store}/`** + `types.ts`
- [ ] **Each types.ts has File header docstring** — Purpose / Category Frontend / Created / MHist
- DoD: dirs exist;types.ts placeholders compile
- Verify: `ls frontend/src/features/cost-dashboard/ frontend/src/features/sla-dashboard/`

### 1.2 MonthPicker shared component
- [ ] **Create `MonthPicker.tsx`** at appropriate location per Day 0 verdict(features/shared/components/ OR cost-dashboard/components/)
- [ ] **Props** — `value: string` (YYYY-MM) + `onChange: (month: string) => void`
- [ ] **UI** — month-year picker via native `<input type="month">` OR custom dropdown
- [ ] **File header docstring**
- DoD: renders;onChange triggers

### 1.3 Cost types.ts
- [ ] **Define `CostSummaryResponse`** — mirror 56.3 Pydantic verified Day 0(fields likely: month / tenant_id / total_cost_usd / by_cost_type: { llm_input / llm_output / tool } / by_provider: { ... })
- [ ] **Define helper types** — CostBreakdownEntry / CostType enum
- DoD: TypeScript strict;0 errors

### 1.4 costService.ts
- [ ] **Create `frontend/src/features/cost-dashboard/services/costService.ts`** — plain fetch + _handleResponse helper
- [ ] **`fetchCostSummary(tenantId, month)`** — GET `/api/v1/admin/tenants/${tenantId}/cost-summary?month=${month}` with credentials: include
- [ ] **File header docstring**
- DoD: import works;0 type errors
- Verify: TypeScript build pass

### 1.5 costStore.ts (Zustand)
- [ ] **Create `frontend/src/features/cost-dashboard/store/costStore.ts`** — Zustand store mirror chatStore pattern
- [ ] **State** — currentMonth / data / loading / error
- [ ] **Actions** — setMonth / loadData(tenantId) / reset
- [ ] **File header docstring**
- DoD: store usable;type-safe

### 1.6 CostOverview + CostBreakdownTable components
- [ ] **Create `CostOverview.tsx`** — wrap MonthPicker + total cost + CostBreakdownTable
- [ ] **Use costStore via hook** — useCostStore;auto-load on month change via useEffect
- [ ] **Loading skeleton** — display while loading === true
- [ ] **Error retry button** — display when error !== null
- [ ] **Create `CostBreakdownTable.tsx`** — props: data: CostSummaryResponse;render rows by cost_type + sub_type
- [ ] **File headers**
- DoD: components render with mock data;UX states work

### 1.7 cost-dashboard page wrapper
- [ ] **Create `frontend/src/pages/cost-dashboard/index.tsx`** — Routes wrapper with `<Route index element={<CostOverview />} />`
- [ ] **File header docstring**
- DoD: page imports work

### 1.8 3 Vitest unit tests (1 US-1 + 2 US-2)
- [ ] **test_month_picker_renders_and_triggers_onChange** — render + simulate input change
- [ ] **test_cost_store_load_data_action_calls_service** — mock fetchCostSummary;assert state transitions(loading true → data set → loading false)
- [ ] **test_cost_service_fetch_cost_summary_handles_500** — mock fetch 500;assert throw with detail message
- DoD: 3 tests pass < 3s

### 1.9 Day 1 sanity checks
- [ ] **Frontend lint** — `cd frontend && npm run lint` → 0 errors
- [ ] **Frontend build** — `cd frontend && npm run build` → success
- [ ] **Frontend Vitest** — `cd frontend && npm run test` → 3 new tests pass
- [ ] **Backend baseline unchanged** — pytest 1557 / 8 V2 lints 8/8 / mypy 0/293 / LLM SDK leak 0

### 1.10 Day 1 commit + push + progress.md
- [ ] **Stage + commit Day 1** — commit msg `feat(frontend-cost-dashboard, sprint-57-1): skeleton + service + store + components + page (US-1 partial + US-2 close)`
- [ ] **Update progress.md** with Day 1 actuals + drift findings if any
- [ ] **Push to origin**

---

## Day 2 — US-3 SLA Dashboard

### 2.1 SLA types.ts
- [ ] **Define `SLAReportResponse`** — mirror 56.3 Pydantic verified Day 0(fields likely: month / tenant_id / availability_pct / api_p99_ms / loop_simple_p99_ms / loop_medium_p99_ms / loop_complex_p99_ms / hitl_queue_notif_p99_ms / violations_count / generated_at)
- [ ] **Define helper types** — SLAMetric / SLAThreshold

### 2.2 slaService.ts
- [ ] **Create `frontend/src/features/sla-dashboard/services/slaService.ts`** — mirror costService pattern
- [ ] **`fetchSLAReport(tenantId, month)`** — GET `/api/v1/admin/tenants/${tenantId}/sla-report?month=${month}`
- [ ] **Reuse `_handleResponse<T>` helper** — 若 Day 0 verdict 確定可 extract 為 shared util → import from shared;else inline duplicate(YAGNI principle for 1 repeat)
- [ ] **File header docstring**
- DoD: import works

### 2.3 slaStore.ts (Zustand)
- [ ] **Create `frontend/src/features/sla-dashboard/store/slaStore.ts`** — mirror costStore
- [ ] **State + actions** — same shape as costStore but for SLAReportResponse
- [ ] **File header docstring**

### 2.4 SLAOverview + SLAMetricsCard components
- [ ] **Create `SLAOverview.tsx`** — wrap MonthPicker + 4 SLAMetricsCard + violations badge
- [ ] **Use slaStore via hook**
- [ ] **Auto-load on month change**
- [ ] **Loading + error states**
- [ ] **Create `SLAMetricsCard.tsx`** — props: metric_name / value / threshold / unit;render with pass-fail color(green if value ≤ threshold;red if > threshold OR > violations 0)
- [ ] **File headers**
- DoD: components render

### 2.5 Tier-aware threshold logic
- [ ] **Determine tenant.plan accessibility** — per Day 0 verdict
- [ ] **If accessible** — Standard 99.5% / Enterprise 99.9% mapping
- [ ] **If not accessible** — fallback 通用 99.5% threshold + note 「Threshold may vary by plan」
- [ ] **Implement in SLAMetricsCard** — receive threshold prop from SLAOverview

### 2.6 Violations count badge
- [ ] **Display in SLAOverview** — red badge if data.violations_count > 0;green badge if 0;hidden if data === null

### 2.7 sla-dashboard page wrapper
- [ ] **Create `frontend/src/pages/sla-dashboard/index.tsx`** — Routes wrapper
- [ ] **File header**

### 2.8 2 Vitest unit tests US-3
- [ ] **test_sla_store_load_data_action_calls_service** — mock fetchSLAReport;assert state transitions
- [ ] **test_sla_metrics_card_threshold_pass_fail_color** — render with value < threshold → green;render with value > threshold → red
- DoD: 2 tests pass < 2s

### 2.9 Day 2 sanity checks
- [ ] **Frontend lint** — 0 errors
- [ ] **Frontend build** — success
- [ ] **Frontend Vitest** — 3 + 2 = 5 tests pass
- [ ] **Backend baseline unchanged**

### 2.10 Day 2 commit + push + progress.md
- [ ] **Stage + commit Day 2** — commit msg `feat(frontend-sla-dashboard, sprint-57-1): service + store + components + page + tier threshold (US-3 close)`
- [ ] **Update progress.md** with Day 2 actuals
- [ ] **Push to origin**

---

## Day 3 — US-4 Routing + App Integration + Buffer

### 3.1 App.tsx wildcard routes
- [ ] **Modify `frontend/src/App.tsx`** — add 2 imports + 2 `<Route>` elements:
  - `<Route path="/cost-dashboard/*" element={<CostDashboardPage />} />`
  - `<Route path="/sla-dashboard/*" element={<SLADashboardPage />} />`
- [ ] **Update App.tsx file header MHist** — `Sprint 57.1 — add /cost-dashboard + /sla-dashboard routes (US-4)`

### 3.2 Home page nav links
- [ ] **Modify Home component (App.tsx 內)** — add 2 `<Link>` entries(role-gated display)
- [ ] **Role gate** — wrap with conditional `{isAdmin && <Link>...}`;reuse existing role hook OR inline JWT decode if no hook(per Day 0 verdict)

### 3.3 Admin role 前端 display gate helper
- [ ] **If existing useIsAdmin / useCurrentUser hook found Day 0** — import + use
- [ ] **If not found** — create `frontend/src/features/shared/hooks/useIsAdmin.ts`(若 features/shared 存在)OR inline JWT decode in App.tsx(simplest)
- [ ] **Helper returns boolean** — `true` if user has ADMIN_TENANT or ADMIN_PLATFORM role

### 3.4 1 Vitest unit test US-4
- [ ] **test_home_renders_nav_links_when_admin** — mock useIsAdmin to return true;render Home;assert 2 dashboard links visible
- [ ] **test_home_hides_nav_links_when_not_admin** — mock useIsAdmin false;assert links absent
- DoD: 2 tests pass < 1s

### 3.5 Manual smoke test
- [ ] **Start dev server** — `cd frontend && npm run dev` + ensure backend at port 8000
- [ ] **Browse `/cost-dashboard`** — admin auth → select month → verify network call to `/api/v1/admin/tenants/{id}/cost-summary?month=YYYY-MM`
- [ ] **Browse `/sla-dashboard`** — same flow with sla-report endpoint
- [ ] **Document smoke test result in progress.md**

### 3.6 Buffer for Day 1 / Day 2 follow-ups
- [ ] **Review Day 1 + Day 2 progress.md drift findings** — fix any deferred items
- [ ] **Pre-stage Day 4 e2e helper setup** — if e2e auth fixture needs setup for admin user(per Day 0 verdict)→ create `tests/e2e/fixtures/admin_auth.ts` here

### 3.7 Day 3 sanity checks
- [ ] **Frontend lint** — 0 errors
- [ ] **Frontend build** — success
- [ ] **Frontend Vitest** — 5 + 2 = 7 tests pass
- [ ] **Backend baseline unchanged**

### 3.8 Day 3 commit + push + progress.md
- [ ] **Stage + commit Day 3** — commit msg `feat(frontend, sprint-57-1): App.tsx routes + Home nav + admin gate (US-4 close)`
- [ ] **Update progress.md** with Day 3 actuals + buffer items resolved
- [ ] **Push to origin**

---

## Day 4 — US-5 Playwright E2E + Closeout Ceremony

### 4.1 Playwright e2e cost_dashboard.spec.ts
- [ ] **Create `frontend/tests/e2e/cost_dashboard.spec.ts`** — 2 specs:
  - **happy_path_admin_loads_cost_dashboard** — admin auth fixture → goto `/cost-dashboard?month=2026-04` → assert MonthPicker renders + total cost visible + at least 1 breakdown row
  - **error_path_500_with_retry** — mock backend 500 via `page.route()` → goto dashboard → assert error message + retry button → mock 200 → click retry → assert success
- [ ] **No `sleep`** — use `waitFor` selectors / explicit timeout 5s per .claude/rules/testing.md
- DoD: 2 tests pass headless < 30s

### 4.2 Playwright e2e sla_dashboard.spec.ts
- [ ] **Create `frontend/tests/e2e/sla_dashboard.spec.ts`** — 2 specs:
  - **happy_path_admin_loads_sla_dashboard** — admin auth → goto `/sla-dashboard?month=2026-04` → assert 4 SLAMetricsCard components rendered + violations badge
  - **error_path_500_with_retry** — same pattern as cost dashboard
- DoD: 2 tests pass headless < 30s

### 4.3 Final pytest + lint + leak verify
- [ ] **Backend full pytest** — 1557 unchanged
- [ ] **Frontend Vitest** — 7 unit tests pass
- [ ] **Frontend Playwright** — 4 e2e tests pass
- [ ] **Frontend lint + build** — clean
- [ ] **Backend mypy --strict** — 0 errors
- [ ] **8 V2 lints** — 8/8 green
- [ ] **LLM SDK leak** — 0
- [ ] **Anti-pattern checklist 11 項對齐** — review per .claude/rules/anti-patterns-checklist.md

### 4.4 Retrospective
- [ ] **Create `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-1/retrospective.md`** — 6 必答 + sub-sections:
  - **Q1 What Went Well + v1 abort lesson capture sub-section**:
    - 跨域(frontend vs backend)plan-time grep 應更密
    - Memory 對 frontend 細節幾乎為零;不可信賴
    - 標準 SaaS lens 假設(self-serve onboarding)在 enterprise admin-driven 場景不適用
    - AD-Plan-3 兩-prong 探勘運作正常(Day 0 catch ~ 1 hr cost vs Day 2 catch 8-10 hr cost;ROI 顯著)
  - **Q2 Calibration verify** — `actual_total_hr / 10 = ratio`;若 ∈ [0.85, 1.20] → log medium-frontend 1-data-point baseline;若 outside → log AD-Sprint-Plan-8;document delta
  - **Q3 AD-Plan-4-Schema-Grep fold-in confirmation** — sprint-workflow.md §Step 2.5 Prong 3 lines added;promotion commitment from 55.6 closed;sprint-workflow.md L count delta
  - **Q4 What To Improve** — 含 actionable: future cross-domain sprint plan §Background 加 mandatory check 「plan-time grep 同新領域 ≥ 5 keywords / dependencies / patterns」
  - **Q5 Phase 57+ next-sprint candidates** — list options updated post-57.1 v2 learning(Tenant Settings / Onboarding self-serve(needs backend re-design)/ Admin tenant console / DR / GDPR / Stripe);user approval required per rolling planning;**不寫** Sprint 57.2 plan task detail
  - **Q6 Sprint 57.1 Final Stats** — frontend test count delta(7 unit + 4 e2e)/ 5 USs status / 2 process ADs closed (AD-Plan-4-Schema-Grep fold-in + medium-frontend 1st app calibration verify)/ v1 abort lesson captured
- DoD: retrospective.md committed

### 4.5 Memory snapshot
- [ ] **Create `memory/project_phase57_1_cost_sla_dashboards.md`** — Sprint summary + ADs closed + stats + Phase 57+ next candidates(per memory 規則)
- [ ] **Update MEMORY.md index** — single-line entry for project_phase57_1
- [ ] **Update SITUATION-V2 §9** — Phase 57+ Frontend SaaS 0/N → 1/N
- [ ] **Update root CLAUDE.md** — Phase 57+ Frontend SaaS status entry(per 56.3 closeout pattern)

### 4.6 Open PR + CI green + solo-dev merge
- [ ] **Open PR** — base main;title `Sprint 57.1 — Phase 57+ SaaS Frontend 1st: Cost + SLA Dual Dashboard Bundle`;body含 5 USs + 2 process ADs closed (AD-Plan-4-Schema-Grep fold-in + medium-frontend 1st app calibration verify)+ v1 abort context note + Phase 57+ Frontend SaaS 1/N start note
- [ ] **Wait CI green** — 5 active checks(含 Frontend E2E chromium headless per 53.7 baseline)
- [ ] **Solo-dev squash merge to main** — per solo-dev policy(2026-05-03 review_count=0)
- [ ] **Capture main HEAD post-merge** — for SITUATION-V2 + memory + closeout PR

### 4.7 Closeout PR
- [ ] **Create closeout commit** — SITUATION-V2 §9 + CLAUDE.md + memory + MEMORY.md updates
- [ ] **Open closeout PR** — base main;title `chore(closeout, sprint-57-1): SITUATION + CLAUDE.md + memory sync to Phase 57+ Frontend SaaS 1/N`
- [ ] **Solo-dev squash merge** — per solo-dev policy
- [ ] **Capture main HEAD post-closeout** — final reference

### 4.8 Final push + Phase 57+ Frontend SaaS ceremony note
- [ ] **Add ceremony note in progress.md final entry** — Phase 57+ Frontend SaaS 1/N opens(57.1 Cost + SLA Dual Dashboard Bundle ✅;next candidates Tenant Settings / Onboarding self-serve(pending backend re-design)/ Admin tenant console / DR / GDPR / Stripe pending user approval)
- [ ] **List Phase 57+ next-sprint candidates** — updated post-57.1 v2 learning
- [ ] **Final commit + push** — push final state

---

## Sprint 57.1 v2 Definition of Done(覆核)

- [ ] All 5 USs acceptance criteria met
- [ ] Frontend `npm run lint && npm run build` clean
- [ ] Frontend `npm run test` (Vitest unit) ≥ 7 new tests pass(3 Day 1 + 2 Day 2 + 2 Day 3)
- [ ] Playwright e2e 4 tests pass(2 happy + 2 error paths)
- [ ] Backend pytest baseline 1557 不變
- [ ] Backend mypy --strict 0 errors 不變
- [ ] 8 V2 lints green
- [ ] LLM SDK leak: 0 不變
- [ ] Anti-pattern checklist 11 項對齐
- [ ] AD-Sprint-Plan-4 `medium-frontend` 1st application captured + verdict logged
- [ ] AD-Plan-4-Schema-Grep fold-in to sprint-workflow.md §Step 2.5 Prong 3 done
- [ ] v1 abort lesson captured in retro Q1 sub-section
- [ ] PR opened, CI green (5 active checks 含 Frontend E2E chromium headless), solo-dev merged to main
- [ ] Closeout PR merged
- [ ] SITUATION-V2 + memory + CLAUDE.md updated to **Phase 57+ Frontend SaaS 1/N (Sprint 57.1 closed — Cost + SLA Dual Dashboard Bundle)**
- [ ] Phase 57.x next-sprint candidates documented in retrospective Q5 (user approval required per rolling planning)

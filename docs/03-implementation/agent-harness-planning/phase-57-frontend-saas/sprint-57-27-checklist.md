# Sprint 57.27 — Checklist (AD-Mockup-Fidelity-Rebuild-Overview)

[Link to plan](./sprint-57-27-plan.md)

**Class**: `frontend-mockup-strict-rebuild` 0.60 (4th application; baseline KEEP per 3-sprint window rule)
**Workload**: Bottom-up ~6.5 hr → calibrated commit ~3.9 hr (multiplier 0.60)
**Day count**: 4 (Day 0 setup + 三-prong + Prong 5 / Day 1 page-head + KPI + Active Loops + HITL Queue / Day 2 Cost Burn + Providers + Incidents + Error Trend + Quick Actions / Day 3 i18n + integration + closeout)
**4th-data-point watch**: Day 3 retro Q2 records actual/committed ratio as the 4th `frontend-mockup-strict-rebuild` data point + the rich-dashboard sub-classification DECISION (per next-phase-candidates #41); KEEP 0.60 regardless

---

## Day 0 — Plan + Checklist + 三-prong + Prong 5 + DRIFT-REPORT skeleton (2026-05-21)

### 0.1 Plan + Checklist + Branch
- [x] **Plan drafted** at `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-27-plan.md`
  - DoD: 13-section structure mirror Sprint 57.25 (frontmatter + Sprint Goal / Background / User Stories / Technical Specs / File Change List / Acceptance Criteria / Deliverables / Dependencies & Risks / Workload / Sequencing)
  - Verify: file exists; sections present
- [x] **Checklist drafted** at `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-27-checklist.md`
  - DoD: Day 0-3 structure; per-task DoD + Verify command; sub-bullets 3-6 per task; final Day 6-step closeout (3.1-3.6)
  - Verify: this file exists
- [x] **Branch creation** from main `fb27df73`
  - DoD: `git checkout -b feature/sprint-57-27-overview-rebuild`
  - Verify: `git branch --show-current` → `feature/sprint-57-27-overview-rebuild`
- [x] **DRIFT-REPORT skeleton** at `claudedocs/4-changes/sprint-57-27-overview-rebuild/DRIFT-REPORT.md`
  - DoD: D1-D16 drift list table + 9-widget mockup-vs-production matrix skeleton + mockup ref resolution (`page-overview.jsx:74-379`)
  - Verify: file exists
- [x] **progress.md Day 0** at `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-27/progress.md` → 8 D-PRE findings catalogued
  - DoD: Day 0 entry with 三-prong findings + Prong 5 cross-ref + D-PRE findings
  - Verify: file exists

### 0.2 Day 0 三-prong (Prong 1 path + Prong 2 content + Prong 4 test selector)
- [x] **Prong 1 Path verify**: shared primitives + overview files exist as plan assumes → 7 primitives present; `features/overview/` dir ABSENT (D-PRE-1)
  - DoD: `components/ui/{CardShell,PageHead,BackendGapBanner}.tsx` + `components/charts/{Spark,StatCard,AreaChart,BarTrack}.tsx` all present (7 reuse targets)
  - DoD: `pages/overview/OverviewPage.tsx` present (728 lines, REWRITE target); `features/overview/` dir exists or needs creation (7 NEW component files)
  - Verify: `Glob` each path
- [x] **Prong 2 Content verify**: shared-primitive APIs serve overview needs → D-PRE-4 (PageHead no meta slot) / D-PRE-5 (CardShell title 14px) / D-PRE-6 (Loop type no agent/model)
  - DoD: read `PageHead` props — confirm title/subtitle/routePath/actions slots; check for a mono-meta slot (R1 — if absent, US-B1 decision = feature-scoped sibling line)
  - DoD: read `StatCard` props — confirm `spark` prop exists (Sprint 57.25 used it; R2)
  - DoD: read `CardShell` props — confirm `flush`/`dense` body variants
  - DoD: read `AreaChart` API — assess if it can express CostBurnChart budget-diagonal (R3 — default: keep CostBurnChart bespoke SVG)
  - DoD: read `useActiveLoops` return shape — confirm fields ActiveLoopsCard needs (agent/session/tenant/model/turns)
  - Verify: `Read` each primitive + hook; catalogue findings as D-PRE in progress.md
- [x] **Prong 4 Test selector verify**: existing overview specs + visual-regression baseline → D-PRE-2 / D-PRE-7
  - DoD: locate existing OverviewPage Vitest spec; note selectors that will break on extracted-component rewrite
  - DoD: D-PRE-2 — `/overview` is NOT in `visual-regression.spec.ts` (6-route list excludes it); rebuild will NOT trigger a 57.26-style CI failure; US-D3 may optionally add it
  - Verify: `Grep` overview spec + visual-regression.spec.ts

### 0.3 Day 0 Prong 5 audit cross-ref
- [x] **Prong 5**: Sprint 57.22 AUDIT-REPORT overview row → Unit 7 COSMETIC 60% 3-4hr; "Remove h1" action WRONG (D-PRE-8)
  - DoD: grep `claudedocs/4-changes/sprint-57-22-*/AUDIT-REPORT-COMPREHENSIVE.md` for the overview unit — confirm priority classification + estimate vs this sprint's scope
  - Verify: `Grep` AUDIT-REPORT; catalogue in progress.md Day 0

### 0.4 Day 0 commit
- [x] **Fold Sprint 57.26 checklist §3.4** [x] marks (Merge / Post-merge cleanup) per user decision 2026-05-21
  - DoD: `sprint-57-26-checklist.md` §3.4 last 2 items already `[x]` (done this session); confirm staged
- [ ] **Day 0 commit** — plan + checklist + 三-prong + DRIFT skeleton + progress + 57.26 §3.4 fold
  - DoD: `git add` plan + checklist + DRIFT skeleton + progress.md + sprint-57-26-checklist.md
  - Commit message: `chore(sprint-57-27, Day 0): plan + checklist + 三-prong + DRIFT skeleton + 57.26 §3.4 fold`
  - Verify: `git log --oneline -1`

---

## Day 1 — Group B (page-head + KPI row + Active Loops + HITL Queue) (2026-05-22)

### 1.1 US-B1 — page-head + KPI row 4-stat WITH sparklines
- [ ] **Page-head** rebuilt per mockup `page-overview.jsx:74-87`
  - In-page title + subtitle + `/overview` route-pill + page-actions (Export outline + New Chat primary)
  - Mono `{tenant} · {role} · {clock}` meta line (D2; R1 decision — feature-scoped sibling unless PageHead has meta slot)
  - D1 closed: in-page title rendered; AppShellV2 topbar title decision (R7 — suppress duplicate or keep one)
  - DoD: page-head matches mockup at 1440×900
- [ ] **KPI row** 4× `<StatCard>` per mockup `:90-95`
  - Active Sessions (`14 loops`, +3↑) / HITL Pending (`3 approvals`, 1 critical↓) / Cost MTD (`$2,847` + sparkline) / SLA p95 (`1.84s` + sparkline)
  - D3 + D5 closed: Cost MTD + SLA p95 use `<StatCard spark>` + `<Spark>`; D10 stat delta arrow = SVG icon
  - `kpiSparklines.ts` fixture (2 spark arrays)
  - DoD: 4 stats render; 2 sparklines visible
- [ ] **Verify**: `npm run build` clean; page-head + KPI render at 1440×900

### 1.2 US-B2 — ActiveLoopsCard + HITLQueueCard
- [ ] **ActiveLoopsCard** (NEW; `features/overview/components/ActiveLoopsCard.tsx`)
  - 5-col loopRow per mockup `:99-141`; D4 closed: agent name + session + tenant + model content layout
  - Preserves `useActiveLoops(10)` real data + loading/error/empty states
  - Uses `<CardShell>` (flush body)
  - DoD: real loop rows render; loading/error/empty states intact
- [ ] **HITLQueueCard** (NEW; `features/overview/components/HITLQueueCard.tsx`)
  - 3 risk-tinted cards per mockup `:143-167`; D13 closed: critical tint matches mockup `oklch(.../0.08)`
  - `hitlQueue.ts` fixture + `<BackendGapBanner>`
  - DoD: 3 cards render; critical card danger-tinted; banner visible
- [ ] **Verify**: ActiveLoops + HITL render in `grid2` 1.4fr/1fr layout

### 1.3 Vitest — Day 1 components
- [ ] **ActiveLoopsCard.test.tsx** (~4 cases: loading / error / empty / happy 5-col row)
- [ ] **HITLQueueCard.test.tsx** (~3 cases: 3 cards / critical tint / BackendGapBanner)
  - DoD: Vitest 430+7 passing; no regression
  - Verify: `npm run test`

### 1.4 Day 1 Playwright MCP pair-verify + commit
- [ ] **Playwright MCP** pair-verify Day 1 widgets (mockup 8080 + production 3007 at 1440×900)
  - DoD: page-head + KPI + ActiveLoops + HITL screenshot compared; drift noted in DRIFT-REPORT
- [ ] **Day 1 commit**
  - Commit message: `feat(frontend, sprint-57-27, Day 1, Group B): page-head + KPI sparklines + ActiveLoopsCard + HITLQueueCard`

---

## Day 2 — Group C (Cost Burn + Providers + Incidents + Error Trend + Quick Actions) (2026-05-23)

### 2.1 US-C1 — CostBurnChart + ErrorTrendChart
- [ ] **CostBurnChart** (NEW; `features/overview/components/CostBurnChart.tsx`)
  - SVG cumulative 30-day burn line + gradient area + budget diagonal + gridlines per mockup `:273-329`
  - D16 closed: x-axis labels (`day 1 / today / day 30`) + budget-line text label
  - `costBurn.ts` fixture; bespoke SVG (R3 — not force-fit AreaChart)
  - DoD: chart renders with axis labels + budget line
- [ ] **ErrorTrendChart** (NEW; `features/overview/components/ErrorTrendChart.tsx`)
  - 24-bar histogram + tone-by-value per mockup `:331-379`
  - D16 closed: x-axis labels (`-24h / -12h / now`)
  - `errorTrend.ts` fixture
  - DoD: 24 bars render with axis labels
- [ ] **Verify**: both charts render in `grid2eq` layout

### 2.2 US-C2 — ProvidersCard + IncidentsCard
- [ ] **ProvidersCard** (NEW; `features/overview/components/ProvidersCard.tsx`)
  - 4-row trafficDot (green/amber/red glow) + mono name + p95 + calls per mockup `:180-199`
  - `providers.ts` fixture + `<BackendGapBanner>`
  - DoD: 4 rows render with trafficDot tones
- [ ] **IncidentsCard** (NEW; `features/overview/components/IncidentsCard.tsx`)
  - 4-row RiskBadge + mono id + title + status Badge + since per mockup `:204-225`
  - D11 closed: Badge 4px radius (not pill); D12 closed: RiskBadge `risk-*` token tone map
  - `incidents.ts` fixture + `<BackendGapBanner>`
  - DoD: 4 rows render; badges 4px square; RiskBadge tones correct
- [ ] **Verify**: Providers + Incidents render

### 2.3 US-C3 — QuickActionsStrip
- [ ] **QuickActionsStrip** (NEW; `features/overview/components/QuickActionsStrip.tsx`)
  - 4 quickBtn (New Chat / Review governance / Tenants / Verification; icon + label + sub) per mockup `:236-266`
  - Full-width flex row; each button navigates on click
  - DoD: 4 buttons render; navigate works
- [ ] **Verify**: strip renders full-width below grids

### 2.4 Vitest + Playwright + Day 2 commit
- [ ] **Vitest specs** — CostBurnChart (~3) + ErrorTrendChart (~2) + ProvidersCard (~2) + IncidentsCard (~3) + QuickActionsStrip (~2)
  - DoD: Vitest 430+7+12 passing; no regression
- [ ] **Playwright MCP** pair-verify Day 2 widgets
- [ ] **Day 2 commit**
  - Commit message: `feat(frontend, sprint-57-27, Day 2, Group C): CostBurnChart + ErrorTrendChart + ProvidersCard + IncidentsCard + QuickActionsStrip`

---

## Day 3 — Group D + closeout (2026-05-24)

### 3.1 US-D1 — i18n EN + zh-TW
- [ ] **i18n keys** added to `frontend/src/i18n/locales/{en,zh-TW}/common.json`
  - NEW keys: overview page-head copy + mono meta + KPI labels + 4-5 BackendGapBanner reasons + quick-action labels/subs + chart axis labels
  - DoD: EN + zh-TW parity; no missing-translation warnings on `npm run build`
  - Verify: `npm run build`

### 3.2 US-D2 — OverviewPage final assembly
- [ ] **OverviewPage.tsx rewritten** — 728-line all-in-one → ~150-line assembly
  - Imports 7 extracted widgets + shared primitives; mockup-faithful grid layout (kpiRow / grid2 / grid2eq × 2 / quick strip)
  - Token drifts closed: D6 (radius token) / D7 (card-head padding) / D8 (card-title 12.5px) / D9 (stat padding) / D14 (page-wrapper mb)
  - AP-3 reversal: 0 inline `Card`/`Badge`/`Stat`/`RiskBadge` definitions remain
  - DoD: page assembles; all 9 widgets render
- [ ] **Existing OverviewPage spec adapted** — selectors updated for extracted-component layout
  - DoD: spec passes
- [ ] **Verify**: `npm run lint && npm run build` clean

### 3.3 US-D3 — Vitest + Playwright + visual-regression
- [ ] **Vitest 430+N** (N≥14) passing — no regression
  - Verify: `npm run test`
- [ ] **Playwright MCP pair-verify** full page (mockup 8080 + production 3007 at 1440×900)
  - DoD: full-page screenshot compared; drift severity logged
- [ ] **visual-regression baseline regenerate** for `/overview` via `playwright-e2e.yml` workflow_dispatch + fetch + ff-merge (per AD #42 — page-visual change moves the snapshot; do BEFORE final CI to avoid surprise)
  - DoD: overview baseline regenerated; CI `Frontend E2E` will pass

### 3.4 DRIFT-REPORT verdict
- [ ] **DRIFT-REPORT** §verdict for `/overview` = PARITY
  - DoD: D1-D14 + D16 marked closed; D15 noted as carryover; per-widget verdict recorded
- [ ] **Cosmetic regressions iterated** to parity; structural → carryover AD

### 3.5 Retrospective + memory + closeout
- [ ] **retrospective.md** Q1-Q7 + Q2 calibration ratio analysis + Q4 rich-dashboard sub-class DECISION (4th data point)
- [ ] **memory snapshot** `memory/project_phase57_27_overview_rebuild.md` + MEMORY.md +1 quality pointer
- [ ] **`.claude/rules/sprint-workflow.md`** calibration matrix +1 row (4th app of `frontend-mockup-strict-rebuild`) + MHist
- [ ] **`next-phase-candidates.md`** — add AD-Overview-Backend-Extensions-Phase58 + resolve #41 rich-dashboard sub-class decision
- [ ] **CLAUDE.md** Current Sprint row + Last Updated footer (minimal touch per REFACTOR-001 §Sprint Closeout)

### 3.6 PR open + CI + merge
- [ ] **PR open** with body (Sprint 57.27 scope + 16-drift closure + 9 widget groups + AP-3 reversal + 4th-app calibration + visual-baseline regen note)
- [ ] **CI green**: all 6 required checks (visual-regression baseline pre-regenerated per 3.3)
- [ ] **Merge** (after CI green + user approval; squash per Sprint 57.23-57.26 pattern)
- [ ] **Post-merge cleanup**: local + remote feature branch delete + any throwaway visual-baseline branch delete

---

## Key Decisions Required During Sprint

| ID | Decision | When | Default |
|----|----------|------|---------|
| R1 | PageHead mono-meta slot — extend shared primitive vs feature-scoped sibling line | Day 1 (US-B1) | Feature-scoped sibling (Karpathy §2 — 1 consumer) |
| R3 | CostBurnChart — reuse `<AreaChart>` vs bespoke SVG | Day 0 Prong 2 / Day 2 | Bespoke feature-scoped SVG (mockup-direct port) |
| R7 | In-page title vs AppShellV2 topbar title | Day 1 (US-B1) | Render in-page per mockup; suppress topbar duplicate |
| — | Playwright e2e for `/overview` — add bootstrap spec vs defer | Day 3 | Defer unless quick (out-of-scope; consider Ops Dashboards sprint) |

# Sprint 57.24 — Checklist

**Plan**: `sprint-57-24-plan.md`
**Calibration**: `mockup-fidelity-retrofit` 0.55 (NEW class 1st application; HYBRID per `claudedocs/1-planning/next-phase-candidates.md §3`) — bottom-up ~10 hr → calibrated commit ~5.5 hr (3-sprint window rule: KEEP 0.55 regardless of ratio outcome; if recurs 2-3× → propose 0.55 → 0.40-0.45 or 0.65-0.70 per evidence)
**Day count**: 4 (Day 0 三-prong + Day 1 cost+sla / Day 2 verification+admin / Day 3 closeout)
**Branch**: `feature/sprint-57-24-mockup-fidelity-retrofit-tier-1`

---

## Day 0 — Setup + 三-prong + Playwright MCP reference captures

### 0.1 Plan + checklist landed
- [x] Plan drafted at `sprint-57-24-plan.md` (6-page retrofit Tier 1; Q1+Q2 decisions encoded)
- [x] Checklist drafted at `sprint-57-24-checklist.md` (this file)
- [x] User Q1 (6 pages) + Q2 (/memory defer) alignment (2026-05-19)

### 0.2 Branch + initial doc files
- [x] Verify main HEAD: `13663c8c` (PR #156 squash merge for Sprint 57.23)
- [x] Switch from `main` (working tree clean post Sprint 57.23 closeout)
- [x] Create feature branch `feature/sprint-57-24-mockup-fidelity-retrofit-tier-1` from main `13663c8c`
- [x] Create `progress.md` at `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-24/progress.md` (Day 0 entry + 4 D-PRE findings)
- [x] Create `claudedocs/4-changes/sprint-57-24-mockup-fidelity-retrofit-tier-1/DRIFT-REPORT-RETROFIT-TIER-1.md` skeleton (screenshots dir auto-created Day 0 captures)
- [x] Add NEW AD-Memory-Structural-Rebuild-Phase58 as #31 to `claudedocs/1-planning/next-phase-candidates.md` (Q2 carryover; new §🔵 Sprint 57.24 Decision Carryovers section)

### 0.3 Day 0 三-prong scope verify (per sprint-workflow.md §Step 2.5)
- [x] **Prong 1 (Path verify)** — confirmed each plan §File Change List entry:
  - `frontend/src/pages/cost-dashboard/index.tsx` exists ✅
  - `frontend/src/pages/sla-dashboard/index.tsx` exists ✅
  - `frontend/src/pages/verification/index.tsx` exists ✅
  - `frontend/src/pages/verification/recent.tsx` **DOES NOT EXIST** ❌ → D-PRE-1 collapse to 5-page scope
  - `frontend/src/pages/admin-tenants/index.tsx` exists ✅
  - `frontend/src/pages/tenant-settings/index.tsx` exists ✅
  - Mockup source files identified ✅ (D-PRE-2: all 5 retrofit targets sourced from `page-admin.jsx` + `page-extras.jsx`; see progress.md D-PRE-2 for exact line ranges)
- [x] **Prong 2 (Content verify)** — deferred to Day 1 per-page inventory (cosmetic retrofit's Tailwind class state IS the Day 1 retrofit work itself; not pre-Day-1 verify). Per-page catalog as drift findings during retrofit.
  - (Per-page Tailwind class drift catalog deferred to Day 1-2 retrofit task itself per Prong 2 deferral above)
  - **R1 mitigation flag**: D-PRE-3 confirmed Sprint 57.22 Unit 31 6-tab finding manifests as `/feature-flags (lifted out of /tenant-settings)` per mockup `page-extras.jsx:928`; Day 1 R1 escalation check required before US-D2 retrofit
- [ ] **Prong 3 (Schema verify)**: N/A this sprint (pure frontend retrofit; 0 DB schema work)
- [x] **Prong 4 (Test selector verify)** — completed; findings:
  - ✅ a11y-scan uses `getByTestId("app-shell")` anchor (L127) for all 5 gated retrofit pages — **no drift risk**
  - ⚠️ visual-regression has 2 baselines (`cost-dashboard.png` L107-116 + `admin-tenants.png` L133-137) — expected drift; Day 3 handles via workflow_dispatch + cherry-pick (per Sprint 57.23 PR #156 recovery pattern)
  - ℹ️ Unit Vitest tests are component-level (`SLAMetricsCard.test.tsx` / `CorrectionTraceView.test.tsx` / `adminTenantsStore.test.ts` / `tenantSettingsStore.test.ts`) — **no h1 anchor dependencies**
- [x] Catalog Day 0 drift findings: 4 entries (D-PRE-1 through D-PRE-4) in `progress.md`

### 0.4 Playwright MCP baseline captures (Day 0; R3 mitigation first)
- [ ] 🚧 Deferred to Day 1+ (prior Sprint 57.23 session browser-stuck state still lingering; attempt reset Day 1 first action)
- [ ] If reset fails → defer Playwright MCP to AD-Sprint-57-24-Playwright-Visual-Verify-Followup; document in DRIFT-REPORT; continue closure via code-level audit + Sprint 57.22 baseline
- [ ] If reset succeeds → capture all baselines:
  - `screenshots/mockup/cost-dashboard.png` at 1440×900 (from `reference/design-mockups/` via `python -m http.server 8080`)
  - `screenshots/mockup/sla-dashboard.png` at 1440×900
  - `screenshots/mockup/verification.png` at 1440×900
  - `screenshots/mockup/verification-recent.png` at 1440×900
  - `screenshots/mockup/admin-tenants-list.png` at 1440×900
  - `screenshots/mockup/admin-tenants-settings.png` at 1440×900
  - `screenshots/pre-retrofit/cost-dashboard.png` at 1440×900 (production at port 3007)
  - `screenshots/pre-retrofit/sla-dashboard.png` at 1440×900
  - `screenshots/pre-retrofit/verification.png` at 1440×900
  - `screenshots/pre-retrofit/verification-recent.png` at 1440×900
  - `screenshots/pre-retrofit/admin-tenants-list.png` at 1440×900
  - `screenshots/pre-retrofit/admin-tenants-settings.png` at 1440×900
- [ ] Side-by-side compare per page → Day 0 drift severity catalog entries

### 0.5 Day 0 closeout
- [ ] Day 0 commit: `chore(sprint-57-24, Day 0): plan + checklist + progress + Day 0 三-prong (4 D-PRE findings) + DRIFT skeleton + Memory rebuild AD carryover`

---

## Day 1 — cost-dashboard + sla-dashboard retrofit (US-B1 + US-B2)

### 1.1 US-B1 /cost-dashboard retrofit
- [ ] Per Sprint 57.22 Unit 8 + Day 0 D-PRE drift findings:
  - Page chrome: title 18px + sub 12.5px + path pill 11px + spacing per mockup
  - 4 KPI cards: layout + token shade + radius + shadow per mockup
  - admin-only provider breakdown widget: existing shadow handling preserved; token vocabulary swap
  - Inline-style escape hatches: removed if Tailwind expresses; preserved with STYLE.md §3 reason if not
- [ ] Per-page MHist update (1-line): `Sprint 57.24 — mockup-fidelity cosmetic retrofit (closes audit Unit 8)`
- [ ] Day 1.1 commit: `feat(frontend, sprint-57-24, Day 1): /cost-dashboard cosmetic retrofit per mockup (US-B1)`

### 1.2 US-B2 /sla-dashboard retrofit
- [ ] Per Sprint 57.22 Unit 9 + Day 0 D-PRE drift findings:
  - SLA monitor page chrome alignment
  - KPI / chart styling per mockup
  - Token vocabulary swap
- [ ] Per-page MHist update (1-line): `Sprint 57.24 — mockup-fidelity cosmetic retrofit (closes audit Unit 9)`
- [ ] Day 1.2 commit: `feat(frontend, sprint-57-24, Day 1): /sla-dashboard cosmetic retrofit per mockup (US-B2)`

### 1.3 Day 1 closeout
- [ ] `npx tsc --noEmit` 0 errors
- [ ] `npx vitest run` 369/369 PASS preserved (or adapt selector if rewrite breaks anchor)
- [ ] `npm run lint` silent
- [ ] `npx vite build` succeeds; main bundle within +5 KB of post-Sprint-57-23 baseline (~329 KB)
- [ ] Progress.md Day 1 entry recorded

---

## Day 2 — verification + admin/tenants list + admin/tenants/settings retrofit (US-C1 + US-D1 + US-D2)

### 2.1 US-C1 /verification + /verification/recent retrofit
- [ ] Per Sprint 57.22 Unit 11 + Day 0 D-PRE drift findings:
  - Recent verifications list page chrome migrate (Sprint 57.11 pre-mockup)
  - Card / row token vocabulary swap
- [ ] Per-page MHist update both files
- [ ] Day 2.1 commit: `feat(frontend, sprint-57-24, Day 2): /verification + /verification/recent visual-chrome retrofit per mockup (US-C1)`

### 2.2 US-D1 /admin/tenants list retrofit
- [ ] Per Sprint 57.22 admin/tenants list audit + Day 0 D-PRE drift findings:
  - Filter pill / table / pagination / actions token vocabulary swap
- [ ] Per-page MHist update
- [ ] Day 2.2 commit: `feat(frontend, sprint-57-24, Day 2): /admin/tenants list cosmetic retrofit per mockup (US-D1)`

### 2.3 US-D2 /admin/tenants/settings retrofit
- [ ] **R1 escalation check first** — confirm Day 0 三-prong content-verify on 6-tab structure:
  - If retrofit-only suffices (cosmetic-level drift only) → continue retrofit
  - If escalates to STRUCTURAL (mockup intent shows materially different tab count / grouping) → downgrade US-D2 to AD-Tenant-Settings-Structural-Rebuild-Phase58 carryover; Sprint 57.24 scope shrinks to 5 pages
- [ ] Per-page MHist update
- [ ] Day 2.3 commit: `feat(frontend, sprint-57-24, Day 2): /admin/tenants/settings cosmetic retrofit per mockup (US-D2)`

### 2.4 Day 2 closeout
- [ ] tsc 0 errors / Vitest preserved / lint silent / build within budget
- [ ] Progress.md Day 2 entry

---

## Day 3 — Playwright post-captures + DRIFT-REPORT + Vitest + closeout (US-E1 + US-E2 + US-E3)

### 3.1 US-E1 Vitest final preserve
- [ ] Full Vitest run: `npx vitest run` → expect 369/369 PASS preserved
- [ ] Full e2e Vitest if changed → expect baseline preserved

### 3.2 US-E2 Playwright MCP post-retrofit captures + DRIFT-REPORT
- [ ] If Playwright MCP available (per Day 0 R3 status):
  - `screenshots/post-retrofit/cost-dashboard.png` at 1440×900
  - `screenshots/post-retrofit/sla-dashboard.png` at 1440×900
  - `screenshots/post-retrofit/verification.png` at 1440×900
  - `screenshots/post-retrofit/verification-recent.png` at 1440×900
  - `screenshots/post-retrofit/admin-tenants-list.png` at 1440×900
  - `screenshots/post-retrofit/admin-tenants-settings.png` at 1440×900
- [ ] Side-by-side compare mockup vs post-retrofit per page → DRIFT-REPORT verdicts (PARITY / COSMETIC / STRUCTURAL / FUNCTIONAL)
- [ ] If Playwright MCP unavailable → code-level audit closure (per Sprint 57.23 Day 4 workaround)
- [ ] If any STRUCTURAL/FUNCTIONAL drift identified → fix-then-commit in Day 3 OR escalate to defer AD

### 3.3 US-E2.5 Visual-regression baseline regeneration (per Sprint 57.23 Day 4 pattern)
- [ ] Trigger `gh workflow run playwright-e2e.yml --ref feature/sprint-57-24-...` (visual-baseline workflow_dispatch)
- [ ] Wait for completion
- [ ] If AD-CI-7-GHA-PR-Permission still blocks auto-PR-create → manual cherry-pick from `chore/visual-baselines-XXXX` branch (parallel to Sprint 57.23 PR #156 recovery)
- [ ] Verify visual-regression CI passes on next push

### 3.4 US-E3 doc syncs (closeout — per REFACTOR-001 §Sprint Closeout policy minimal touch)
- [ ] `retrospective.md` Q1-Q7 + Q8 NEW class calibration narrative (`mockup-fidelity-retrofit` 0.55 1st app data point)
- [ ] `memory/project_phase57_24_mockup_fidelity_retrofit_tier_1.md` (auto-memory subfile; ~250-300 char quality pointer)
- [ ] `memory/MEMORY.md` +1 quality-pointer line (subfile path + topic + keywords)
- [ ] `.claude/rules/sprint-workflow.md` calibration matrix +1 row for `mockup-fidelity-retrofit` 0.55 1st app baseline + MHist
- [ ] `CLAUDE.md` minimal-touch update:
  - Current Sprint row: `Sprint 57.24 closed YYYY-MM-DD (PR pending) — mockup-fidelity retrofit Tier 1 (6 pages); see memory/project_phase57_24_*.md for detail. Next: Sprint 57.25 candidate`
  - Last Updated footer: `**Last Updated**: YYYY-MM-DD (Sprint 57.24 — mockup-fidelity retrofit Tier 1); see memory/ for sprint history`
  - NO additional `Latest Sprint` / `Prev Sprint` rows packed with retro detail (per REFACTOR-001 forbidden item)
- [ ] `claudedocs/1-planning/next-phase-candidates.md` carryover ADs (e.g. AD-Memory-Structural-Rebuild-Phase58 + any newly-identified STRUCTURAL drift + AD-Sprint-57-24-Playwright-Visual-Verify-Followup if applicable)

### 3.5 Day 3 commits + PR
- [ ] Day 3 commit: `feat(frontend, sprint-57-24, Day 3): Playwright post-retrofit + DRIFT-REPORT + retrospective + memory + visual baseline cherry-pick`
- [ ] Day 3 closeout commit: `chore(closeout-57-24): CLAUDE.md + MEMORY.md + sprint-workflow.md calibration matrix + carryover ADs`
- [ ] `git push -u origin feature/sprint-57-24-mockup-fidelity-retrofit-tier-1`
- [ ] `gh pr create --draft --title "..." --body "..."`
- [ ] CI green: pytest baseline preserved + frontend-ci all checks

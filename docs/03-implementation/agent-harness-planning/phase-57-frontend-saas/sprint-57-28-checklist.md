# Sprint 57.28 — Checklist (AD-Mockup-Fidelity-Foundation-Switch)

[Link to plan](./sprint-57-28-plan.md)

**Class**: `frontend-verbatim-css-foundation` 0.55 (NEW class; 1st application; HYBRID weighted blend)
**Workload**: Bottom-up ~11.0 hr → calibrated commit ~6.2 hr (multiplier 0.55)
**Day count**: 5 (Day 0 setup + guidance-PR merge + 三-prong + before-baseline / Day 1 Layer 2+3 / Day 2 Layer 4 + theme / Day 3 CI guards + 22-route sweep / Day 4 Vitest + closeout)
**1st-data-point watch**: Day 4 retro Q2 records actual/committed ratio as the NEW class's 1st data point; KEEP 0.55 regardless (1 data point insufficient to adjust per 3-sprint window rule)
**Scope decision**: Option B (user-approved 2026-05-22) — foundation-only; per-page re-point = Phase 2 epic

---

## Day 0 — Plan + Checklist + guidance-PR merge + 三-prong + before-baseline (2026-05-22)

### 0.1 Plan + Checklist
- [x] **Plan drafted** at `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-28-plan.md` — 11-section structure mirror Sprint 57.26; user-approved 2026-05-22 (incl. Option B scope decision)
- [x] **Checklist drafted** at `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-28-checklist.md` — Day 0-4 structure

### 0.2 guidance-PR merge + branch
- [x] **`chore/frontend-mockup-fidelity-guidance` PR opened** — PR #161 (`19f31443`, 22 docs/rules files; 0 source code)
- [x] **guidance PR CI green + merged to main** — branch was BEHIND (PR #160 Sprint 57.27 merged in interim) → merged `origin/main` in (0 conflict) → 8/8 CI checks green → squash-merged to main `d4461141`; remote branch deleted
- [x] **Feature branch cut from updated main** — `feature/sprint-57-28-mockup-fidelity-foundation` from main `d4461141`

### 0.3 Day 0 三-prong (Prong 1 path + Prong 2 content/collision + Prong 4 test selector)
- [x] **Prong 1 Path verify** — 0 path drift; `index.css`/`main.tsx`/`tailwind.config.ts`/`ThemeProvider.tsx` present (edits); `styles-mockup.css` absent (create); `scripts/route-sweep.mjs` present (reuse); frontend CI = `.github/workflows/frontend-ci.yml`
- [x] **Prong 2 Content verify** — token-collision set enumerated (~28: 2 tricky + ~26 shared-intent — FOUNDATION-SWITCH-REPORT §2); mockup `styles.css` 0 `rem` → `html{font-size:13px}` KEEP (D-PRE-3); D-PRE-1 (mockup HAS light theme) + D-PRE-2 (bg/fg theme-scoped) catalogued
- [x] **Prong 4 Test selector verify** — 4 Vitest files reference theme/token literals: `AuthShell.test.tsx`, `AppShellV2.test.tsx`, `UserMenu.test.tsx`, `adminTenantsRoleGate.test.tsx` (D-PRE-6; Day 4 adapt)
- [x] **Read PoC reference implementation** — `investigation/mockup-fidelity-poc` `main.tsx` imports `./styles-mockup.css` (L46) after `./index.css` (L40); confirms Layer 2 wiring

### 0.4 Day 0 sweep before-baseline + report skeleton
- [x] **Before-baseline sweep** — 22 routes at 1440×900 via `route-sweep.mjs before` → `screenshots/before/` (22 PNGs; all ✓). `route-sweep.mjs` OUT_DIR re-pointed 57.26→57.28 + header MHist
- [x] **FOUNDATION-SWITCH-REPORT skeleton** at `claudedocs/4-changes/sprint-57-28-mockup-fidelity-foundation/FOUNDATION-SWITCH-REPORT.md` — 4-layer summary + filled token-collision table + 22-route matrix skeleton + D-PRE catalogue
- [x] **progress.md Day 0** at `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-28/progress.md` — Day 0 entry + 6 D-PRE findings + decisions

### 0.5 Day 0 commit
- [x] **Day 0 commit** — plan + checklist + Day 0 progress + FOUNDATION-SWITCH-REPORT skeleton + route-sweep.mjs re-point (screenshots/ kept local, not committed — per Sprint 57.26 pattern); hash recorded in progress.md
  - Commit message: `chore(sprint-57-28, Day 0): plan + checklist + 三-prong + before-baseline`

---

## Day 1 — Group B (Layer 2 + Layer 3)

### 1.1 US-B1 Layer 2 — verbatim copy
- [ ] **`frontend/src/styles-mockup.css`** = byte-identical copy of `reference/design-mockups/styles.css`
  - DoD: `cp` with LF preserved; 1-line never-hand-edit notice via `main.tsx` import comment (not in the css file — pure byte-identical)
  - Verify: `diff reference/design-mockups/styles.css frontend/src/styles-mockup.css` empty (line-ending tolerant)
- [ ] **`main.tsx` import** `./styles-mockup.css` after `./index.css`
  - DoD: import order = `index.css` then `styles-mockup.css` (cascade order — mockup classes win at equal specificity)
  - Verify: `Grep("styles-mockup", frontend/src/main.tsx)` shows the import below `index.css`

### 1.2 US-B2 Layer 3 — index.css slim-down
- [ ] **Retire mockup-system HSL approximation tokens** from `index.css`
  - DoD: the `--bg`/`--bg-1`/`--bg-2`/`--fg`/... + 7 semantic + 4 risk HSL approximations (Sprint 57.18/57.20) removed — now sourced verbatim from `styles-mockup.css`
  - DoD: shadcn-system token set KEPT (the 13 not-yet-re-pointed pages still consume it)
  - Verify: `Grep("--bg:|--bg-1:", index.css)` → 0 results; `npm run build` green
- [ ] **`html{font-size:13px}` decision applied** per Day-0 grep
  - DoD: if mockup px-only → KEEP the hack (transition-safe), mark for Phase-2 retirement; if mockup uses rem → retire now, transition drift catalogued
  - DoD: decision + grep evidence recorded in progress.md Day 1
  - Verify: progress.md Day 1 §font-size decision present
- [ ] **`index.css` body block** verified
  - DoD: `font-family`/`line-height` — confirm `styles-mockup.css`'s own `body` rule (loads later) covers it; align only if a gap remains
  - Verify: body block reviewed; no duplicate competing rule

### 1.3 Day 1 spot-check + commit
- [ ] **Spot-check** `/overview` + `/auth/login` post-Layer-2/3
  - DoD: both routes still render + usable; mockup classes resolving (`.card`/`.badge` computed style sampled)
  - Verify: dev server `:3007` manual or Playwright single-route check
- [ ] **Day 1 commit** with Group B work
  - Commit message: `feat(frontend, sprint-57-28, Day 1, Group B): Layer 2 verbatim styles-mockup.css + Layer 3 index.css slim-down`
  - DoD: `git status` clean post-commit

---

## Day 2 — Group C (Layer 4 + theme toggle)

### 2.1 US-C1 Layer 4 — tailwind.config.ts bridge rework
- [ ] **Mockup-token bridge** `hsl(var(--X))` → `var(--X)`
  - DoD: every mockup-consumed token's `tailwind.config.ts` colour entry drops the `hsl()` wrapper (var holds full `oklch()`)
  - Verify: `Grep("hsl\\(var", tailwind.config.ts)` shows only de-collided shadcn entries remain
- [ ] **Token collision resolution** per Day-0 Prong 2 enumeration
  - DoD: each shadcn-only name collision de-collided — rename the shadcn var in `index.css` (e.g. `--primary` → `--sc-primary`) + update only that token's config bridge entry
  - DoD: shared-intent collisions → verbatim value wins (index.css approximation already retired Day 1)
  - DoD: 0 `bg-*`/`text-*` utility renders invalid CSS (e.g. `hsl(oklch(...))`)
  - Verify: `npm run build` green; spot-check `bg-primary`/`bg-bg` computed style on a sample route

### 2.2 US-C2 theme toggle alignment
- [ ] **`ThemeProvider` dark-only alignment**
  - DoD: light branch retired; `ThemeProvider` simplified (NOT deleted — kept as mount point for future `[data-variant]`/`[data-density]`)
  - DoD: `<html>` carries the mockup-expected dark default; `index.html` updated only if needed
  - Verify: `/overview` + `/auth/login` render dark consistently; no dead light path
- [ ] **Day 2 spot-check + commit**
  - DoD: `/overview` + `/cost-dashboard` + `/auth/login` render correctly post-Layer-4/theme
  - Commit message: `feat(frontend, sprint-57-28, Day 2, Group C): Layer 4 tailwind bridge rework + token collision resolution + dark-only theme`
  - Verify: `git status` clean post-commit

---

## Day 3 — Group D (CI guards + 22-route regression sweep)

### 3.1 US-D1 CI guards
- [ ] **`frontend/scripts/check-mockup-fidelity.mjs`** authored
  - DoD: diff guard (`styles-mockup.css` vs `styles.css`, line-ending normalised) + grep guard (no new hardcoded hex/oklch in `features/`+`pages/`)
  - DoD: grep guard records the current pre-existing-offender baseline count (Phase-2 backlog); hard-fails only on NEW offenders
  - Verify: `node scripts/check-mockup-fidelity.mjs` exits 0
- [ ] **`package.json` script + CI step**
  - DoD: `+1` `package.json` script `check:mockup-fidelity`; `+1` step in the frontend CI workflow (file from Day 0 Prong 1) after lint
  - Verify: `Grep("check:mockup-fidelity", frontend/package.json)` + the workflow file

### 3.2 US-D2 after-switch 22-route sweep
- [ ] **After-switch sweep** — all ~22 routes via `route-sweep.mjs after` (fresh contexts, no cache)
  - DoD: `screenshots/after/` has ~22 PNGs
  - Verify: directory count ≈ 22
- [ ] **Before/after + vs-mockup matrix** in FOUNDATION-SWITCH-REPORT
  - DoD: 22-route matrix — before/after diff + after vs `:8080` mockup-equivalent per route
  - Verify: report matrix populated for all ~22 routes

### 3.3 US-D3 regression triage
- [ ] **Catastrophic breakage fixed in-sprint**
  - DoD: any page that crashes / is blank / unusable fixed; if none → record "0 catastrophic"
- [ ] **Transition drift catalogued** as Phase-2 epic backlog
  - DoD: the 13 pages' expected shifts listed per-route as Phase-2 re-point backlog (NOT fixed this sprint)
- [ ] **Structural regressions → carryover AD**
  - DoD: any previously-correct route now structurally broken → `AD-Foundation-Switch-Regression-<route>` (NOT silently shipped)
- [ ] **Day 3 commit**
  - Commit message: `feat(frontend, sprint-57-28, Day 3, Group D): CI mockup-fidelity guards + 22-route regression sweep + triage`
  - DoD: `git status` clean post-commit

---

## Day 4 — Group E + closeout

### 4.1 US-E1 Vitest + lint + build
- [ ] **Token/theme Vitest specs adapted** (per Day-0 Prong 4)
  - DoD: specs asserting a retired token / light-theme path adapted (NOT deleted)
- [ ] **Vitest 430/430 passing** (Sprint 57.26+ baseline preserved; 0 regression)
  - Verify: `npm run test` exit 0
- [ ] **`npm run lint` exit 0 + `npm run build` green + bundle KB delta recorded**
  - DoD: lint silent; build green; bundle delta recorded (Layer 2 ≈ +40 KB CSS expected)
  - Verify: build output captured in progress.md

### 4.2 US-E2 FOUNDATION-SWITCH-REPORT final + closeout
- [ ] **FOUNDATION-SWITCH-REPORT final verdict** + Phase-2 epic backlog
  - DoD: per-route verdict (foundation switched / transition-drift noted) + accurate Phase-2 re-point backlog list
- [ ] **retrospective.md Q1-Q7** at `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-28/retrospective.md`
  - DoD: Q2 records actual/committed ratio = 1st data point for NEW `frontend-verbatim-css-foundation` class
- [ ] **memory snapshot** `memory/project_phase57_28_mockup_fidelity_foundation.md` + **MEMORY.md +1 quality pointer**
  - DoD: distinguishing features + verdicts + keywords per quality-pointer principle (~300 char)
- [ ] **`.claude/rules/sprint-workflow.md` calibration matrix +1 NEW class row**
  - DoD: `frontend-verbatim-css-foundation` 0.55 row with 1st data point `57.28=<ratio>` + MHist entry
- [ ] **`claudedocs/1-planning/next-phase-candidates.md` update**
  - DoD: Foundation switch (Phase 1) closed; Phase-2 per-page re-point epic backlog referenced; any structural-regression carryover AD added
- [ ] **CLAUDE.md Current Sprint row + Last Updated footer** (REFACTOR-001 §Sprint Closeout minimal touch — NO history additions)
- [ ] **Day 4 commit** closeout
  - Commit message: `feat(frontend, sprint-57-28, Day 4): closeout — FOUNDATION-SWITCH-REPORT final + retrospective + calibration matrix NEW class + minimal CLAUDE.md touch`
  - DoD: `git status` clean post-commit

### 4.3 PR open + CI + merge
- [ ] **PR open** with body (Sprint 57.28 scope + 4-layer switch + token-collision resolution + dark-only theme + 22-route sweep result + NEW calibration class + browser-cache hard-refresh verification note)
- [ ] **CI green**: all required checks pass (backend-ci fires — PR touches `.github/workflows/**`)
- [ ] **Merge** (after CI green + user approval; squash per Sprint 57.23-57.26 pattern)
- [ ] **Post-merge cleanup**: local + remote feature branch delete

---

## Key Decisions Required During Sprint

| Decision Point | When | Default |
|----------------|------|---------|
| `html{font-size:13px}` hack: keep through Phase 1 vs retire now | Day 0 Prong 2 grep → Day 1.2 | KEEP if mockup `styles.css` is px-only (transition-safe); retire only if mockup uses `rem` |
| Token name collision: de-collide (rename shadcn var) vs let verbatim win | Day 2.1 per Day-0 enumeration | shadcn-only collision → rename shadcn var; shared-intent collision → verbatim wins |
| Theme: dark-only vs retain light mode | **Plan approval** + Day 2.2 | Dark-only (mockup has no light design; production dark-default since 57.21). If user wants light retained = explicit "build beyond mockup" scope addition — raise at plan approval |
| `styles-mockup.css` header comment vs pure byte-identical | Day 1.1 | Pure byte-identical (diff guard); never-edit notice lives in `main.tsx` import comment |
| Sweep regression: in-sprint fix vs catalogue vs carryover AD | Day 3.3 | Catastrophic → fix in-sprint; transition drift → catalogue (Phase-2 backlog); structural → carryover AD |
| guidance PR backend-ci paths-filter skip | Day 0.2 | Touch `.github/workflows/backend-ci.yml` header per documented workaround, or PR-body note |

---

**Plan + checklist drafted**: 2026-05-22 Day 0
**Class**: `frontend-verbatim-css-foundation` 0.55 (NEW class; 1st application)
**Target close**: 5 working days from Day 0 commit to PR merged

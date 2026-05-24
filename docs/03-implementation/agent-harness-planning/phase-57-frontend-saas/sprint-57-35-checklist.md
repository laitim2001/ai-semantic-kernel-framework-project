# Sprint 57.35 — Checklist

**Plan**: [`sprint-57-35-plan.md`](./sprint-57-35-plan.md)
**Sprint Goal**: 6th Phase-2 per-page verbatim-CSS re-point — AuthShell + 7 `/auth/*` routes. **2nd non-rich-dashboard shape** in epic; **3rd validation data point** for `frontend-verbatim-css-repoint` 0.50 lifted baseline + **2nd bimodal-by-shape data point**. Closes Sprint 57.23 vintage HSL-translation epic gap.

---

## Day 0 — Plan + Checklist + 三-prong + Before-baseline

### 0.1 Plan + Checklist drafted

- [x] **`sprint-57-35-plan.md` exists** — mirrors Sprint 57.34 format
- [x] **`sprint-57-35-checklist.md` exists** — this file

### 0.2 三-prong verify

- [x] **Prong 1 path-verify** — 8 production + 2 mockup files confirmed
- [x] **Prong 2 content-verify** — per-route mockup line ranges confirmed + `/auth/login` 0 mockup classes across 18 className occurrences (Sprint 57.23 vintage HSL translation drift confirmed)
- [x] **Prong 3 schema-verify** — N/A
- [x] **Drift findings catalog** — D1 logged in progress.md Day 0

### 0.3 Before-baseline 22-route sweep

- [x] **Run `route-sweep.mjs before`** — 22 PNGs captured to `claudedocs/4-changes/sprint-57-35-auth-repoint/screenshots/before/`
- [x] **Sample auth routes before** — user-reported drift (SSO unstyled / Continue no fill / dev-login orange missing) confirmed in screenshot baseline

### 0.4 Day 0 commit

- [ ] **Commit Day 0** — `docs(sprint-57-35): Day 0 — plan + checklist + 三-prong + before-baseline 22-route sweep`

---

## Day 1 — AuthShell + Login + Dev (Group B)

### 1.1 US-B1 — AuthShell re-point

- [ ] **Edit `AuthShell.tsx`** — verbatim per `page-extras.jsx:5-15` (`.auth-shell`/`.auth-card`/`.auth-foot` mockup CSS)
  - DoD: shared shell verbatim; preserve children + footer prop API

### 1.2 US-B2 — Login re-point

- [ ] **Edit `/auth/login/index.tsx`** — verbatim per `page-extras.jsx:28-56`
  - 3 SSO Buttons with proper `.btn-outline` styling (SAML / Microsoft / Google)
  - `.or-divider`
  - `.input` Work email
  - `.btn-primary` Continue (with arrow icon)
  - `.mono` `dev-login` orange link verbatim per mockup `style={{ color: var(--warning) }}`
  - `.kbar`-style footer (`SAML 2.0 / OIDC · MFA required by tenant policy`)
  - DoD: visual diff ≤ 2 px; all 3 SSO buttons styled correctly; dev-login orange visible

### 1.3 US-B3 — Dev re-point

- [ ] **Edit `/auth/dev/index.tsx`** — verbatim per `page-extras.jsx:110-151`
  - DEV_LOGIN warning hint
  - Form fields verbatim
  - DoD: visual diff ≤ 2 px

### 1.4 Day 1 5-gate quick-check + commit

- [ ] **tsc + ESLint + Vitest pass** — `cd frontend; npm run lint; npm run test -- --run auth`
- [ ] **Commit Day 1** — `feat(frontend, sprint-57-35): AuthShell + /auth/login + /auth/dev verbatim re-point (US-B1+B2+B3)`

---

## Day 2 — Callback + Register (Group C)

### 2.1 US-C1 — Callback re-point

- [ ] **Edit `/auth/callback/index.tsx`** — verbatim per `page-extras.jsx:73-105`
  - Spinner Card + "Completing sign-in…" + provider context
  - DoD: visual diff ≤ 2 px

### 2.2 US-C2 — Register re-point

- [ ] **Edit `/auth/register/index.tsx`** — verbatim per `page-auth-extras.jsx:42-186`
  - Signup form with tenant/role fields
  - "Already have account" link with `.mono` accent
  - DoD: visual diff ≤ 2 px; all Field labels verbatim

### 2.3 Day 2 5-gate quick-check + commit

- [ ] **tsc + ESLint + Vitest pass**
- [ ] **Commit Day 2** — `feat(frontend, sprint-57-35): /auth/callback + /auth/register verbatim re-point (US-C1+C2)`

---

## Day 3 — Invite + MFA + Expired (Group D)

### 3.1 US-D1 — Invite re-point

- [ ] **Edit `/auth/invite/index.tsx`** — verbatim per `page-auth-extras.jsx:192+`
  - DoD: visual diff ≤ 2 px

### 3.2 US-D2 — MFA re-point

- [ ] **Edit `/auth/mfa/index.tsx`** — verbatim per mockup MFA section
  - 6-digit TOTP input grid (preserve existing roll-own UI per Sprint 57.23 Q3 decision)
  - WebAuthn fallback UI
  - DoD: visual diff ≤ 2 px

### 3.3 US-D3 — Expired re-point

- [ ] **Edit `/auth/expired/index.tsx`** — verbatim per mockup Expired section
  - DoD: visual diff ≤ 2 px

### 3.4 Day 3 5-gate quick-check + commit

- [ ] **Full Vitest run** — 456/456 baseline maintained
- [ ] **Commit Day 3** — `feat(frontend, sprint-57-35): /auth/invite + /auth/mfa + /auth/expired verbatim re-point (US-D1+D2+D3)`

---

## Day 4 — Regression sweep + closeout (Group E)

### 4.1 US-E1 — 22-route sweep after

- [ ] **Run `route-sweep.mjs after`** — `claudedocs/4-changes/sprint-57-35-auth-repoint/screenshots/after/`
- [ ] **Sweep delta analysis** — 7 auth routes flip Sprint 57.23 Tailwind → ✅ PARITY; no other route regresses
- [ ] **Sample 7 auth screenshots from `after/`** for visual confirmation

### 4.2 US-E3 — Final 5-gate verification

- [ ] **tsc + Vite build** — `npm run build`
- [ ] **ESLint** — `npm run lint`
- [ ] **Vitest** — 456 baseline preserved
- [ ] **check:mockup-fidelity** — diff empty + grep clean (CSS untouched)

### 4.3 US-E4 — Docs sync

- [ ] **REPOINT-REPORT.md** — `claudedocs/4-changes/sprint-57-35-auth-repoint/REPOINT-REPORT.md` (8 file delta + per-route shape variety + 6th-data-point + 3rd-validation + 2nd-bimodal outcome)
- [ ] **progress.md Day 0-4** — daily entries
- [ ] **retrospective.md Q1-Q7** — Q2 calibration ratio + bimodal evaluation (CONFIRM or REJECT shape hypothesis)
- [ ] **`sprint-workflow.md §Matrix`** — `frontend-verbatim-css-repoint` 6th data point cell update + MHist
- [ ] **memory subfile** — `memory/project_phase57_35_auth_repoint.md`
- [ ] **`MEMORY.md` pointer**
- [ ] **`CLAUDE.md` Current Sprint row + footer** — minimal touch
- [ ] **`next-phase-candidates.md`** — Sprint 57.35 Carryover + bimodal-watch AD update + close Sprint 57.23 epic-gap narrative

### 4.4 US-E5 — Commit + PR + merge

- [ ] **Day 4 commit** on `feature/sprint-57-35-auth-repoint`
- [ ] **PR open** — `gh pr create`
- [ ] **CI green → squash-merge**

### 4.5 Sprint closeout self-check

- [ ] Sacred Rule check — 0 unchecked items deleted
- [ ] Acceptance Criteria — all 6 pass
- [ ] Working tree clean post-merge — on main
- [ ] Branch deleted — `feature/sprint-57-35-auth-repoint` deleted local + remote

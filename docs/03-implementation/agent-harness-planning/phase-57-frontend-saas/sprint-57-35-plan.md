# Sprint 57.35 — AD-Auth-Shell-And-Pages-Verbatim-Repoint

**File**: `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-35-plan.md`
**Purpose**: Plan for Sprint 57.35 — **6th Phase-2 per-page verbatim-CSS re-point** on AuthShell + 7 `/auth/*` routes (login / callback / dev / register / invite / mfa / expired). 2nd non-rich-dashboard shape in epic; **3rd validation data point** for `AD-Sprint-Plan-frontend-verbatim-css-repoint-baseline-lift` AND **2nd data point for bimodal-by-shape hypothesis** (`AD-Sprint-Plan-frontend-verbatim-css-repoint-shape-bimodal-watch`, Sprint 57.34 NEW).
**Category**: Sprint planning / Phase 57+ Frontend SaaS — Phase-2 per-page re-point epic
**Scope**: Phase 57+ Frontend SaaS — Phase-2 epic, 6th application; 2nd non-rich-dashboard shape (auth-flow)
**Created**: 2026-05-24
**Last Modified**: 2026-05-24
**Status**: Draft → awaiting user approval

> **Modification History**
> - 2026-05-24: Initial draft (Sprint 57.35 Day 0) — AuthShell + 7 auth routes Phase-2 verbatim re-point per user request after observing `/auth/login` drift; closes Sprint 57.23 vintage HSL-translation epic gap on auth routes

---

## Sprint Goal

Land the **6th Phase-2 per-page verbatim-CSS re-point** — this time on the shared **AuthShell** component + **7 `/auth/*` routes** (login / callback / dev / register / invite / mfa / expired). These 7 routes were previously "strict-rebuilt" in Sprint 57.23 (`AD-Auth-Page-Full-Rebuild-Round-2`, `frontend-mockup-strict-rebuild` 0.60 class) using the OLD "translate mockup CSS into Tailwind utility classes" method — which Sprint 57.28+ epic identified as drift root cause (per CLAUDE.md §Frontend Mockup-Fidelity Hard Constraint). User identified the drift on `/auth/login` 2026-05-24 (SSO buttons render unstyled / Continue button no fill / `dev-login` orange highlight missing).

This sprint applies the **proper verbatim-CSS protocol** (Sprint 57.28 4-layer + Sprint 57.29-34 per-page) to close the epic gap on auth routes.

This is the **2nd non-rich-dashboard shape** in the Phase-2 epic (1st = Sprint 57.34 `/orchestrator` config/tabbed-forms) and provides the **3rd validation data point** for the lifted 0.50 baseline AND **2nd data point for the bimodal-by-shape hypothesis**:
- rich-dashboard 3-pt mean (57.30-57.32) ≈ 0.40 below band
- non-rich-dashboard 2-pt (57.34 config + 57.35 auth) → 3rd validation needed to confirm or reject bimodal

---

## Background

### Why Sprint 57.35 (this sprint)

User observed `/auth/login` rendering drift 2026-05-24: SSO buttons unstyled (no border / no background) / Continue button no solid blue fill / "Trouble signing in?" `dev-login` orange highlight missing. Investigation confirmed:

1. `frontend/src/pages/auth/login/index.tsx` uses **0 mockup verbatim CSS classes** (18 className occurrences all Tailwind utility translations).
2. Sprint 57.23 (2026-05-18) `AD-Auth-Page-Full-Rebuild-Round-2` shipped 6 P0 auth routes + 1 supporting + AuthShell using the OLD "HSL-translation + Tailwind utility re-composition" method.
3. Sprint 57.28 (2026-05-22) introduced the proper 4-layer verbatim-CSS protocol; auth routes still on pre-57.28 method.
4. CLAUDE.md §Frontend Mockup-Fidelity Hard Constraint explicitly warns: "57.18-57.27 epic 已重建約 10 頁宣稱 parity（auth / cost / sla / overview），但多為「眼湊 HSL 翻譯」版，仍需依新方法 re-point".

This sprint closes the gap on the auth 7 routes (and the shared AuthShell). Other Sprint 57.23-vintage routes already re-pointed:
- ✅ `/overview` (Sprint 57.29) / `/chat-v2` (57.30) / `/cost-dashboard` (57.31) / `/sla-dashboard` (57.32) / `/orchestrator` (57.34)

### Mockup source mapping (Day 0 Prong 2 confirmed)

`reference/design-mockups/page-extras.jsx` + `reference/design-mockups/page-auth-extras.jsx`:

| Mockup component | Mockup file:line | Production target |
|------------------|------------------|-------------------|
| `AuthShell` (shared shell) | `page-extras.jsx:5-15` | `frontend/src/components/AuthShell.tsx` |
| Login (SSO + Email Continue + dev-login hint) | `page-extras.jsx:28-56` | `frontend/src/pages/auth/login/index.tsx` |
| Callback (Completing sign-in…) | `page-extras.jsx:73-105` | `frontend/src/pages/auth/callback/index.tsx` |
| Dev-login (form + warning) | `page-extras.jsx:110-151` | `frontend/src/pages/auth/dev/index.tsx` |
| Register (signup form) | `page-auth-extras.jsx:42-186` | `frontend/src/pages/auth/register/index.tsx` |
| Invite (accept invitation) | `page-auth-extras.jsx:192-...` | `frontend/src/pages/auth/invite/index.tsx` |
| MFA (TOTP / WebAuthn) | `page-auth-extras.jsx:...` (find in Day 0 Prong 2) | `frontend/src/pages/auth/mfa/index.tsx` |
| Expired (session expired) | `page-auth-extras.jsx:...` (find in Day 0 Prong 2) | `frontend/src/pages/auth/expired/index.tsx` |

### Scope boundaries

**IN scope**:
- `frontend/src/components/AuthShell.tsx` (shared shell — re-point once benefits all 7 routes).
- 7 `/auth/*` route pages (login / callback / dev / register / invite / mfa / expired).
- Any mockup-ui primitive additions needed (Button variants already exist; possibly need Field for auth forms — verify Day 0).
- 22-route regression sweep before/after + per-route visual fidelity verify.

**OUT of scope**:
- The 9 remaining 🟡 AppShellV2 routes (loop-debug / memory / state-inspector / governance / admin-tenants / tenant-settings / compaction / +3 unblocked-by-57.33).
- `AD-IAM-Block-B-RBAC` Phase 58+ work (real OIDC backend wiring).
- `AD-WebAuthn-Roll-Own-UI` Phase 58+ (mfa page is fixture-driven this sprint).
- AuthShell role expansion (e.g. adding new auth flows like password-reset — out of scope unless mockup has them).

### Class baseline — `frontend-verbatim-css-repoint` 0.50 (6th application; 3rd validation of lifted baseline; 2nd bimodal data point)

HYBRID weighted blend for Sprint 57.35:

| Component | Class | Multiplier | Weight |
|-----------|-------|------------|--------|
| Day-0 三-prong + before-baseline + mockup mapping per-route | `audit-cycle` | 0.85 | ~12% |
| AuthShell re-point (Day 1) | `frontend-verbatim-css-repoint` | 0.50 | ~15% |
| Login + dev re-point (Day 1) | `frontend-verbatim-css-repoint` | 0.50 | ~15% |
| Callback + register re-point (Day 2) | `frontend-verbatim-css-repoint` | 0.50 | ~20% |
| Invite + mfa + expired re-point (Day 3) | `frontend-verbatim-css-repoint` | 0.50 | ~20% |
| 22-route sweep + fidelity verify | `frontend-verbatim-css-repoint` | 0.50 | ~5% |
| Closeout + retro + docs | `closeout` | 0.80 | ~13% |
| **HYBRID blended baseline** | | **≈ 0.55** | |

Bottom-up estimate:
- Day 0: ~1.5 hr (more than 57.34 due to 8 files + mockup mapping)
- Day 1 (AuthShell + login + dev): ~2 hr
- Day 2 (callback + register): ~2 hr
- Day 3 (invite + mfa + expired): ~2 hr
- Day 4 (sweep + closeout): ~1 hr
- **Total: ~8.5 hr**

Calibrated commit: ~4.25 hr (multiplier 0.50 anchored to class baseline; HYBRID ≈ 0.55 if weighted exactly).

Day 1-3 will likely be agent-delegated per Sprint 57.34 model (code-implementer agent — same calibration caveat).

### Class baseline 6th-data-point + 3rd-validation + 2nd-bimodal evaluation criteria

| Sprint 57.35 ratio range | Interpretation | Action |
|--------------------------|----------------|--------|
| ≈ 0.85-1.20 (in band) | ✅ Bimodal-by-shape CONFIRMED — 2 non-rich-dashboard apps in band; 3 rich apps below band | Propose class split `-rich-dashboard` (0.40) vs `-config-form` (0.50) in Sprint 57.36 retrospective |
| ≈ 0.40-0.55 (lower band edge / below) | Class-wide variance confirmed — non-rich also drifts low | Reject bimodal hypothesis; propose 0.50 → 0.40 class-wide lift in Sprint 57.36 retro |
| ≈ 0.60-0.85 (lower-band) | Ambiguous | KEEP 0.50; 4th-validation data point next sprint |
| > 1.20 | Over-corrected | Revert toward 0.55-0.60 |

### What is preserved (NOT changed)

- All auth logic (TanStack hooks / `useAuthStore` / route navigation / form validation).
- All `data-testid` attributes (used by Playwright auth flow e2e tests).
- Sprint 57.23 functional decisions (e.g. WebAuthn UI roll-own + 6-digit MFA input — keep visual; underlying flow Phase 58+).
- `routes.config.ts` auth route entries.
- `styles-mockup.css` (verbatim foundation; Sprint 57.28 protocol).
- Backend auth endpoints, IAM provider integration (Phase 58+ scope).

### What gets changed (this sprint scope)

**Day 1 — AuthShell + Login + Dev** (3 files):
- `AuthShell.tsx` — drop Tailwind translations + use mockup `.auth-shell`/`.auth-card`/`.auth-foot` CSS verbatim per mockup `page-extras.jsx:5-15`.
- `/auth/login/index.tsx` — drop Tailwind translations + use mockup `.btn`/`.btn-primary`/`.btn-outline`/`.input`/`.or-divider`/`.sso-row` per mockup L28-56 + `dev-login` orange link verbatim.
- `/auth/dev/index.tsx` — same per mockup L110-151.

**Day 2 — Callback + Register** (2 files):
- `/auth/callback/index.tsx` — Completing sign-in… spinner Card per mockup `page-extras.jsx:73-105`.
- `/auth/register/index.tsx` — signup form per mockup `page-auth-extras.jsx:42-186`.

**Day 3 — Invite + MFA + Expired** (3 files):
- `/auth/invite/index.tsx` — invitation accept per mockup `page-auth-extras.jsx:192-...`.
- `/auth/mfa/index.tsx` — 6-digit TOTP grid + WebAuthn UI per mockup.
- `/auth/expired/index.tsx` — session-expired card per mockup.

**Day 4 — Regression sweep + fidelity verify + closeout**.

---

## User Stories

### Group A — Day 0 plan + 三-prong + before-baseline (PRE-WORK)

- **US-A1** (Plan + Checklist): As the AI, I draft Sprint 57.35 plan + checklist mirroring Sprint 57.34 format. Acceptance: this file + `sprint-57-35-checklist.md` exist.
- **US-A2** (Day-0 三-prong): Run path-verify (8 production files exist) + content-verify (per-route mockup line ranges confirmed in `page-extras.jsx` + `page-auth-extras.jsx`; production className verification — confirm 0 mockup classes across all 8 files) + Prong 3 N/A.
- **US-A3** (Before-baseline screenshots): Playwright capture 22 AppShellV2 + auth routes via `route-sweep.mjs before`. Confirm 7 auth routes show Sprint 57.23 vintage drift state (unstyled SSO buttons / no fill Continue / no orange `dev-login`).

### Group B — AuthShell + Login + Dev (Day 1)

- **US-B1** (AuthShell re-point): Shared AuthShell component matches mockup `page-extras.jsx:5-15` byte-for-byte (`.auth-shell`/`.auth-card`/`.auth-foot` mockup CSS verbatim; brand-mark + brand-text + children container + footer). Acceptance: all 7 auth pages inherit fixed shell.
- **US-B2** (Login re-point): `/auth/login` matches mockup L28-56 (3 SSO buttons with proper `.btn-outline` styling + `.or-divider` + `.input` work email + `.btn-primary` Continue + `.mono` `dev-login` orange link). Acceptance: visual diff vs mockup ≤ 2 px; all 3 SSO buttons styled correctly.
- **US-B3** (Dev re-point): `/auth/dev` matches mockup L110-151 (form + DEV_LOGIN warning hint). Acceptance: visual diff ≤ 2 px.

### Group C — Callback + Register (Day 2)

- **US-C1** (Callback re-point): `/auth/callback` matches mockup `page-extras.jsx:73-105` (spinner Card + "Completing sign-in…" + provider context). Acceptance: visual diff ≤ 2 px.
- **US-C2** (Register re-point): `/auth/register` matches mockup `page-auth-extras.jsx:42-186` (signup form + tenant/role fields + Already have account link). Acceptance: visual diff ≤ 2 px; all Field labels verbatim.

### Group D — Invite + MFA + Expired (Day 3)

- **US-D1** (Invite re-point): `/auth/invite` per mockup. Acceptance: visual diff ≤ 2 px.
- **US-D2** (MFA re-point): `/auth/mfa` per mockup — 6-digit TOTP grid + WebAuthn fallback UI. Acceptance: visual diff ≤ 2 px; existing WebAuthn UI roll-own preserved.
- **US-D3** (Expired re-point): `/auth/expired` per mockup. Acceptance: visual diff ≤ 2 px.

### Group E — Regression sweep + fidelity verify + closeout (Day 4)

- **US-E1** (22-route sweep after): Confirm 7 auth routes flip from Sprint 57.23-vintage Tailwind → ✅ PARITY; no other route regresses. Document delta in REPOINT-REPORT.md.
- **US-E2** (Per-route sample): Capture 7 auth screenshots from `after/` for visual confirmation.
- **US-E3** (5-gate verification): tsc + ESLint + Vitest + Vite build + check:mockup-fidelity all green. Vitest count = 456 baseline preserved.
- **US-E4** (Closeout): progress.md / retrospective.md / sprint-workflow.md §Matrix (6th data point + 3rd-validation + 2nd-bimodal evaluation) / memory subfile / MEMORY.md / CLAUDE.md / next-phase-candidates.md (Sprint 57.35 Carryover; bimodal-watch AD update; close Sprint 57.23 epic-gap narrative).
- **US-E5** (Commit + PR + merge): PR open; CI green; squash-merge.

---

## Technical Specifications

### Verbatim re-point method (unchanged from Sprint 57.29-34)

Per `docs/rules-on-demand/frontend-mockup-fidelity.md`. Same as Sprint 57.34.

### Hybrid Tailwind+inline color bridge

Per Sprint 57.31 precedent. Apply preemptively for any tone-coded color element (esp. dev-login warning orange, register error states).

### mockup-ui primitive promotion decisions

| Primitive | Current location | Decision |
|-----------|------------------|----------|
| Button | mockup-ui (existing) | Import — drop local duplicates |
| Tabs / Field / Switch | mockup-ui (added Sprint 57.34) | Import as needed |
| AuthShell | Page-local (NOT in mockup-ui) | Keep page-local (single consumer; shared via direct import). Do NOT promote to mockup-ui unless future re-use trajectory clear |

---

## File Change List

### NEW files (0)

### MODIFIED files (~8-9)

| # | Path | Change |
|---|------|--------|
| 1 | `frontend/src/components/AuthShell.tsx` | Re-point per `page-extras.jsx:5-15` verbatim; +MHist |
| 2 | `frontend/src/pages/auth/login/index.tsx` | Re-point per `page-extras.jsx:28-56`; drop Tailwind translations; +MHist |
| 3 | `frontend/src/pages/auth/dev/index.tsx` | Re-point per `page-extras.jsx:110-151`; +MHist |
| 4 | `frontend/src/pages/auth/callback/index.tsx` | Re-point per `page-extras.jsx:73-105`; +MHist |
| 5 | `frontend/src/pages/auth/register/index.tsx` | Re-point per `page-auth-extras.jsx:42-186`; +MHist |
| 6 | `frontend/src/pages/auth/invite/index.tsx` | Re-point per `page-auth-extras.jsx:192-...`; +MHist |
| 7 | `frontend/src/pages/auth/mfa/index.tsx` | Re-point per `page-auth-extras.jsx` MFA section; +MHist |
| 8 | `frontend/src/pages/auth/expired/index.tsx` | Re-point per `page-auth-extras.jsx` Expired section; +MHist |
| 9 | `frontend/scripts/route-sweep.mjs` | OUT_DIR re-point to sprint-57-35-auth-repoint; +MHist |

### DELETED files (0)

### PRESERVED (not touched)

- `frontend/src/features/auth/components/RequireAuth.tsx` (auth gating; not visual)
- `frontend/src/components/mockup-ui.tsx` (no new primitives this sprint)
- `frontend/src/components/ui/tabs.tsx` (not used by auth)
- `styles-mockup.css` (Sprint 57.28 verbatim foundation)
- Backend, auth provider integrations, etc.

---

## Acceptance Criteria

1. **All 8 production files re-pointed** — AuthShell + 7 auth routes match mockup verbatim CSS classes.
2. **Visual parity ≤ 2 px** on representative elements per route (SSO buttons / Continue button / dev-login orange / Card styling).
3. **22-route sweep `after` baseline shows 7 auth routes ✅ PARITY**, 0 new regressions on other 15 routes.
4. **5 gates green** — tsc + ESLint + Vitest + Vite build + check:mockup-fidelity.
5. **Vitest count maintains** — 456 baseline preserved.
6. **Docs synced** — REPOINT-REPORT.md + retrospective.md + sprint-workflow.md §Matrix 6th data point + 3rd-validation + 2nd-bimodal evaluation + memory subfile + MEMORY.md pointer + CLAUDE.md Current Sprint + next-phase-candidates.md (Sprint 57.35 Carryover; close Sprint 57.23 epic-gap narrative; bimodal-watch AD update).

---

## Deliverables

- [ ] Day 0: this plan + checklist + 三-prong findings + before-baseline screenshots
- [ ] Day 1: AuthShell + login + dev re-point commit
- [ ] Day 2: callback + register re-point commit
- [ ] Day 3: invite + mfa + expired re-point commit
- [ ] Day 4: 22-route sweep after + REPOINT-REPORT + retro + docs sync + PR + CI green + merge

---

## Dependencies & Risks

### Dependencies

- Sprint 57.28 verbatim-CSS foundation in place.
- Sprint 57.34 mockup-ui primitives (Button/Badge/Card/etc.) available.

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Auth flow Playwright e2e tests break due to DOM structure changes | Medium | Medium — would block merge | Preserve all `data-testid`; review per-Day commit with Playwright auth spec presence check |
| Mockup AuthShell signature `<AuthShell children footer>` doesn't map cleanly to current production AuthShell.tsx | Low | Medium — would force AuthShell API refactor cascading to all 7 routes | Day 0 Prong 2 grep production AuthShell.tsx API; document gaps |
| Sprint 57.23 vintage Vitest assertions on local primitive JSX shapes (`btn-outline` Tailwind class) | Medium | Low — Vitest catches; update spec contracts | Run targeted `npm run test -- --run auth` after each Day's edit |
| WebAuthn UI / 6-digit MFA input grid requires complex mockup translation | Medium | Low — visual only; preserve fixture/state | Day 3 review existing implementation vs mockup; if structural retrofit needed, scope-down to visual class swap only |

### Common Risk Classes (per sprint-workflow.md §Common Risk Classes)

- **Class A (paths-filter)**: this PR touches only `frontend/src/**`, no `.github/workflows/**` — backend-ci paths-filter skip; no visual-regression baseline regen needed (Sprint 57.28+ pattern).

---

## Workload

Bottom-up est ~8.5 hr → calibrated commit ~4.25 hr (multiplier 0.50; 6th application; 3rd validation of lifted baseline; 2nd bimodal data point).

| Day | Bottom-up | Calibrated |
|-----|-----------|------------|
| Day 0 | 1.5 hr | 0.75 hr |
| Day 1 (AuthShell + login + dev) | 2 hr | 1 hr |
| Day 2 (callback + register) | 2 hr | 1 hr |
| Day 3 (invite + mfa + expired) | 2 hr | 1 hr |
| Day 4 (sweep + closeout) | 1 hr | 0.5 hr |
| **Total** | **~8.5 hr** | **~4.25 hr** |

Day 1-3 agent-delegated likely (same model as Sprint 57.34 — calibration caveat per Sprint 57.13/57.27/57.28/57.29 convention).

---

## Sequencing / Day plan

### Day 0 — Plan + Checklist + 三-prong + before-baseline

1. Write plan (this file) + checklist
2. 三-prong:
   - **Prong 1** path-verify: 8 production files + 2 mockup files + mockup-ui.tsx
   - **Prong 2** content-verify: per-route mockup line ranges + AuthShell API mapping + production className grep (confirm 0 mockup classes across 8 files)
   - **Prong 3** schema-verify: N/A (frontend-only)
3. Catalog drift findings in progress.md
4. Run `route-sweep.mjs before` (OUT_DIR = sprint-57-35-auth-repoint)

### Day 1 — AuthShell + Login + Dev

1. Edit AuthShell.tsx — verbatim per mockup
2. Edit /auth/login/index.tsx — verbatim per mockup
3. Edit /auth/dev/index.tsx — verbatim per mockup
4. Verify 5 gates pass (esp. auth Playwright e2e tests still pass)
5. Commit Day 1

### Day 2 — Callback + Register

1. Edit /auth/callback/index.tsx + /auth/register/index.tsx
2. Verify
3. Commit Day 2

### Day 3 — Invite + MFA + Expired

1. Edit /auth/invite/index.tsx + /auth/mfa/index.tsx + /auth/expired/index.tsx
2. Verify (full Vitest run)
3. Commit Day 3

### Day 4 — Sweep + closeout

1. `route-sweep.mjs after` + visual confirm 7 auth routes ✅ PARITY
2. REPOINT-REPORT.md
3. 5 gates final
4. Update retrospective.md (Q1-Q7 incl. 6th-data-point + bimodal evaluation)
5. Update sprint-workflow.md §Matrix + memory + MEMORY.md + CLAUDE.md + next-phase-candidates.md
6. Commit Day 4
7. Push + open PR + CI green + squash-merge

---

## Related

- Sprint 57.23 retrospective — `AD-Auth-Page-Full-Rebuild-Round-2` (old strict-rebuild method; this sprint closes the epic gap)
- Sprint 57.34 retrospective — 1st non-rich-dashboard data point + `AD-Sprint-Plan-frontend-verbatim-css-repoint-shape-bimodal-watch` NEW
- Sprint 57.28 — verbatim-CSS 4-layer foundation protocol
- Sprint 57.29-32 + 57.34 — 5 prior Phase-2 per-page re-point apps
- CLAUDE.md §Frontend Mockup-Fidelity Hard Constraint — verbatim-CSS rule + 57.18-57.27 drift warning
- `claudedocs/1-planning/next-phase-candidates.md` Phase-2 backlog
- `docs/rules-on-demand/frontend-mockup-fidelity.md` (verbatim-CSS method; unchanged)
- `reference/design-mockups/page-extras.jsx:5-151` + `page-auth-extras.jsx:42+` (canonical mockup sources)

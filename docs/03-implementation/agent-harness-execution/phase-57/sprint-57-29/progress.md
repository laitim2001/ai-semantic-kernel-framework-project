# Sprint 57.29 Progress — AD-Overview-Verbatim-Repoint

**Sprint**: 57.29 — `/overview` + App Shell (incl. topbar overlays) Phase-2 Per-Page Re-Point
**Class**: `frontend-verbatim-css-repoint` 0.60 (NEW class; 1st application)
**Plan**: `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-29-plan.md`
**Checklist**: `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-29-checklist.md`

---

## Day 0 — 2026-05-22 (plan + checklist + 三-prong + before-baseline)

### Today's Accomplishments

- **Branch** `feature/sprint-57-29-overview-verbatim-repoint` cut from `main` (`05d7f48f` — Sprint 57.28 merged).
- **Discovery** — 2 codebase-researcher passes: (1) `/overview` content + PoC content-layer template; (2) shell (`AppShellV2`/`Sidebar`/`Topbar`) + overlays + mockup `shell.jsx`/`app.jsx`/`topbar-overlays.jsx`.
- **Plan + checklist drafted** — mirror Sprint 57.28 structure; user-approved 2026-05-22. Scope = Option B + overlays (AskUserQuestion ×2): `/overview` content + full shell + 3 topbar overlays. Day count 6 (Day 0-5).
- **Day-0 三-prong** complete — Prong 1 path verify (0 drift), Prong 2 content/testid enumeration, Prong 4 test-selector verify. See Drift findings below.
- **Before-baseline sweep** — `route-sweep.mjs` `OUT_DIR` re-pointed 57.28→57.29 + MHist; `node scripts/route-sweep.mjs before` → 22/22 routes captured at 1440×900 (`screenshots/before/`, kept local — not committed per Sprint 57.26/57.28 pattern).
- **REPOINT-REPORT skeleton** at `claudedocs/4-changes/sprint-57-29-overview-shell-repoint/REPOINT-REPORT.md`.

### Drift findings (Day-0 三-prong)

- **Prong 1 — 0 path drift**: all 16 target files present as edits; `mockup-ui.tsx` correctly absent (create); 5 mockup sources present.
- **D-PRE-1** (🟡): full `data-testid` contract = **10 testids** — `app-shell` / `sidebar-toggle` / `sidebar-tenant-switcher` / `topbar` / `topbar-cmdk` / `topbar-locale` / `topbar-theme` / `notifications-bell` / `notifications-panel` / `traffic-dot-${state}` (dynamic). 3 more fixed + 1 dynamic than the plan's illustrative list. Re-point preserves all 10. **0 scope shift** — plan R3 mandates preserving "every testid"; this is the planned Prong-2 enumeration deliverable.
- **D-PRE-2** (🟢): 13 in-scope unit specs + ~9 e2e specs traverse the shell. Day 5 US-E1 adapts class-selector specs; testid-based specs unaffected.
- **D-PRE-3** (🟢): no dedicated `Topbar.test.tsx` — Topbar covered via `AppShellV2.test.tsx` + e2e.
- **Overlay class existence** (🟢): guaranteed present in `styles-mockup.css` by the verbatim-copy invariant (== `styles.css`, the mockup overlays' own source).

### Decisions

- **Dev server**: Frontend `:3007` (PID 51124) + Backend `:8000` (PID 41528) already running — no start/restart needed; before-baseline captures the current pre-re-point state, which is the intended baseline.
- **Go/No-Go**: 🟢 GO — scope shift 0%, no blocking finding. Day 1 code may start.
- **Calibration**: NEW class `frontend-verbatim-css-repoint` 0.60 (HYBRID weighted blend); Day 5 retro Q2 records the 1st data point.

### Remaining for Next Day

- **Day 1 (Group B)**: `mockup-ui.tsx` verbatim primitive port + `AppShellV2` re-point + `Sidebar` re-point + Day 1 spot-check + commit.

### Notes

- PoC `investigation/mockup-fidelity-poc` `pages/overview-poc/{index.tsx,components.tsx}` is the proven content-layer template; the shell re-point has NO PoC precedent (R1 — first verbatim shell re-point).

---

## Day 1 — 2026-05-22 (Group B — primitives + AppShellV2 + Sidebar)

### Today's Accomplishments

- **US-B1** — NEW `frontend/src/components/mockup-ui.tsx`: typed-TSX verbatim port of mockup `ui.jsx` primitives (`Icon` 56-icon set / `Button` / `Badge` / `Card` / `Stat` / `SevDot` / `RiskBadge`); emits mockup class strings verbatim; 0 Tailwind / 0 shadcn.
- **US-B2** — `AppShellV2.tsx` re-pointed: root `.app` grid (+ `data-collapsed`) / `.main` / `.content` (+ `.fullbleed`); `data-testid="app-shell"` + `fullBleed` prop preserved.
- **US-B3** — `Sidebar.tsx` re-pointed: verbatim `.sidebar` / `.sidebar-head` / `.brand-*` / `.tenant-switcher` / `.nav` / `.nav-section` / `.nav-item`(`data-active`) / `.nav-icon` / `.nav-label` / `.nav-badge` / `.sidebar-foot` / `.user-card`; nav-badge tints + foot-avatar gradient copied verbatim as inline-style objects; `react-router` `<Link>`/`useLocation`, `routes.config.ts`, `useUIStore` collapse, i18n preserved.
- Implementation delegated to a `code-implementer` agent; orchestrator hard-verified (build / lint / tsc / Vitest / check:mockup-fidelity / testid grep / file review).

### Findings

- **D-DAY1-1** (🟡 caught + fixed): the Sidebar re-point dropped the `<aside>` `aria-label={t("shell.primaryNavigation")}` → `AppShellV2.test.tsx:45` failed (`getByRole("complementary", { name: "Primary navigation" })`). The agent had not run Vitest; the orchestrator's verification Vitest pass caught it. **Fixed** — restored `aria-label` on the re-pointed `<aside>`. Lesson: a11y attributes (`aria-label` / `role`) are part of the preserve-contract alongside `data-testid` — Day 2+ re-point briefs call this out explicitly.
- **D-DAY1-2** (🟢 noted → carryover): `no-restricted-syntax` (inline-`style=` ban, Sprint 57.15/57.16) conflicts with the verbatim-re-point method, which REQUIRES copying mockup inline-style literals (gradients / tints). Resolved per-file with a `/* eslint-disable no-restricted-syntax */` carrying the verbatim rationale (STYLE.md §1 escape hatch). Works, but every Phase-2 re-pointed file (~16 by sprint end) will need this → carryover **AD-Inline-Style-Rule-vs-Verbatim-Method** (next-phase-candidates at Day 5 closeout): scope the ESLint rule to exclude re-pointed dirs, or retire it.

### Quality gates (Day 1)

- `npx tsc -b` 0 errors · `npm run lint` exit 0 · `npm run build` green (main JS 337.06 kB — unchanged from Sprint 57.28 baseline) · Vitest **457/457** · `npm run check:mockup-fidelity` pass (18/18 hex baseline) · 3 shell testids (`app-shell` / `sidebar-toggle` / `sidebar-tenant-switcher`) preserved · 0 Tailwind residue in `Sidebar.tsx`.

### Notes

- Day 1 changed the shared shell (wraps all 19 routes); `AppShellV2.test.tsx` mounts + asserts the shell renders. Full 22-route visual sweep is Day 5 US-D1; the re-pointed shell is live on `:3007` via Vite HMR.
- `mockup-ui.tsx` is created but not yet consumed — Day 2/3 overlays + Day 3/4 `/overview` widgets consume it.

### Remaining for Next Day

- **Day 2 (Group B)**: `Topbar.tsx` re-point + `CommandPalette.tsx` + `NotificationsPanel.tsx` overlay re-point.

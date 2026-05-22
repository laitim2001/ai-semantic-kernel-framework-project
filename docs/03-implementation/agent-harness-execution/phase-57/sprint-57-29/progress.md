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

---

## Day 2 — 2026-05-22 (Group B — Topbar + CommandPalette + NotificationsPanel)

### Today's Accomplishments

- **US-B4** — `Topbar.tsx` re-pointed: verbatim `.topbar` / `.crumb` / `.here` (kept as `<h1>` per page-title-is-h1 a11y contract) / `.route-pill` / `.tenant-pill` + `.dot` / `.topbar-spacer` / `.cmdk` / `.kbd`; theme + bell buttons use `.btn ghost` + `data-size="sm"` (mockup Button ghost sm); locale button + divider + bell unread badge + cmdk cursor ported as named `CSSProperties` consts copied byte-for-byte from `shell.jsx`. Lucide icon imports dropped → mockup `Icon` from `mockup-ui.tsx` (the mockup topbar itself renders `<Icon name=…>`). `useLocation` / `useTheme` / `useAuthStore` / i18n `toggleLocale` / all props preserved.
- **US-B5** — `CommandPalette.tsx` re-pointed: mockup `topbar-overlays.jsx` `CommandPalette` classes + inline-style literals consumed; Radix `<Dialog>` / `<DialogContent>` / `<DialogTitle className="sr-only">` + `cmdk` `<Command>` interaction layer untouched; `jsx-a11y/no-autofocus` disable preserved.
- **US-B5** — `NotificationsPanel.tsx` re-pointed: mockup `NotificationsPanel` classes + inline-style literals consumed; `role="dialog"` / `role="tablist"` / `role="tab"` + `aria-selected` + row `role="button"` + `tabIndex` + `onKeyDown` Enter/Space preserved; fixtures + mark-all/mark-one handlers + open/close intact.
- Implementation delegated to a `code-implementer` agent (brief explicitly listed the 6 testids + a11y attrs as preserve-contract — D-DAY1-1 lesson); orchestrator hard-verified all 5 gates independently + greps + code review of the Topbar verbatim port against `shell.jsx`.

### Findings

- **D-DAY2-1** (🟢 verified, not a defect): the `.cmdk` element re-pointed as `<div role="button" tabIndex={0} onKeyDown={Enter}>` — initially flagged as a possible a11y downgrade from the pre-re-point native `<button>`. Verified against `reference/design-mockups/shell.jsx:178`: the mockup itself authors `<div className="cmdk" role="button" tabIndex={0} onKeyDown={…Enter…} style={{cursor:"pointer"}}>`. The re-point is a byte-for-byte verbatim copy → correct per the verbatim-fidelity method (the pre-re-point `<button>` was a translation-era deviation). No fix.
- **D-DAY1-2** (🟢 carryover continues): the `no-restricted-syntax` inline-`style=` ban needed a file-level `eslint-disable` (verbatim rationale comment) in all 3 Day-2 files — same as Day 1's Sidebar. Still tracked as **AD-Inline-Style-Rule-vs-Verbatim-Method** (next-phase-candidates at Day 5 closeout).
- **Agent decisions verified sound**: dropped the mockup `CommandPalette` backdrop/card div (superseded by Radix `<DialogContent>` modal shell — interaction layer must stay); dropped `AVATAR_STYLE` in Topbar (`<UserMenu />` owns its avatar — its re-point is Day 3.1, not now). `.btn ghost` + `data-size="sm"` used instead of non-existent `btn-ghost-sm`; `badge warning pill` instead of non-existent `badge-warning` — both match real `styles-mockup.css` modifier patterns + Day-1 Sidebar precedent.

### Quality gates (Day 2 — orchestrator-verified independently)

- `npx tsc -b` 0 errors · `npm run lint` exit 0 (`--report-unused-disable-directives --max-warnings 0`) · `npm run test` **457/457** (94 files; the `Error: kaboom` in stderr is `AuthShell.test.tsx`'s intentional error-boundary throw) · `npm run build` green (main JS 336.99 kB — −0.07 kB vs Day 1 337.06, Lucide imports dropped) · `npm run check:mockup-fidelity` pass (diff guard byte-identical, hex baseline 18) · 6 shell/overlay testids preserved (`topbar` / `topbar-cmdk` / `topbar-locale` / `topbar-theme` / `notifications-bell` / `notifications-panel`) · 0 Tailwind utility residue in all 3 files.

### Notes

- Day 2 spot-check = code-level review of the Topbar verbatim port against `shell.jsx:171-179` + all 5 gates green + Vitest jsdom render assertions for the topbar/overlay specs all pass. Full Playwright visual + computed-style verification is Day 5 US-D2.
- `<UserMenu />` left untouched (Day 3.1 US-B5 scope).

### Remaining for Next Day

- **Day 3 (Group B finish + Group C start)**: `UserMenu.tsx` overlay re-point + shell spot-check on all 19 routes + `OverviewPage.tsx` re-point.

# FOUNDATION-SWITCH-REPORT — Sprint 57.28 (AD-Mockup-Fidelity-Foundation-Switch)

**Purpose**: Track the verbatim-CSS 4-layer foundation switch — token-collision resolution + 22-route before/after regression evidence.
**Sprint**: 57.28 (Phase 1 of `claudedocs/5-status/v2-investigation-20260522/03-mockup-consistency-rootcause.md` §5)
**Status**: Day 0 — skeleton + token-collision enumeration complete; before-baseline captured
**Created**: 2026-05-22

---

## 1. The 4-layer sync protocol (what this sprint lands)

| Layer | File | Day 0 state | Target |
|-------|------|-------------|--------|
| **1** | `reference/design-mockups/styles.css` | canonical (1123 lines, oklch, on main) | unchanged — verbatim source |
| **2** | `frontend/src/styles-mockup.css` | absent | byte-identical copy of Layer 1; imported in `main.tsx` after `index.css` |
| **3** | `frontend/src/index.css` | carries shadcn tokens + 57.18/57.20 mockup HSL approximations + `html{font-size:13px}` | slimmed — mockup-system HSL approximations retired |
| **4** | `frontend/tailwind.config.ts` | all colours `hsl(var(--X))` | mockup tokens → `var(--X)`; shadcn name-collisions de-collided |

---

## 2. Token-collision set (Day 0 三-prong Prong 2 — enumerated)

`{names in mockup styles.css}` ∩ `{names in production index.css :root/.dark}`. Mockup tokens span `:root` (theme-invariant) + `[data-theme][data-variant]` (theme-scoped bg/fg) + `[data-density]`.

### 2a. Tricky collisions — different system, same name → DE-COLLIDE (rename shadcn var)

| Token | Production (shadcn) | Mockup | Resolution |
|-------|---------------------|--------|------------|
| `--primary` | HSL `234 89% 60%` (bridged `hsl(var(--primary))`) | `oklch(0.62 0.16 250)` | rename shadcn → `--sc-primary`; update `index.css` def + `tailwind.config.ts` `primary` bridge; mockup `--primary` (oklch) owns the name |
| `--border` | HSL `214 31% 91%` (bridged `hsl(var(--border))`; also `* { border-color }` index.css:154) | `oklch(...)` theme-scoped | rename shadcn → `--sc-border`; update `index.css` def + `* { border-color }` rule + `tailwind.config.ts` `border` bridge |

> Without de-collision, mockup oklch wins the cascade → `hsl(oklch(...))` = invalid CSS → every `bg-primary` / border breaks.

### 2b. Shared-intent collisions — production token was a 57.18/57.20 approximation OF the mockup token → RETIRE production HSL; mockup verbatim oklch owns the name; bridge → `var(--X)`

| Tokens | Added by | Mockup form |
|--------|----------|-------------|
| `--primary-soft` | Sprint 57.20 | `oklch(... / 0.14)` |
| `--success` `--warning` `--danger` `--thinking` `--tool` `--memory` `--info` | Sprint 57.18 | oklch |
| `--risk-low` `--risk-medium` `--risk-high` `--risk-critical` | Sprint 57.18 | oklch / var |
| `--bg` `--bg-1` `--bg-2` `--bg-3` `--bg-hover` `--fg` `--fg-muted` `--fg-subtle` `--border-strong` `--shadow` | Sprint 57.20 | oklch — **theme-scoped (`[data-theme][data-variant]`)**, see D-PRE-2 |

### 2c. Identical-value collisions — retire production's; mockup owns (no value change)

| Tokens | Note |
|--------|------|
| `--radius` (`8px`) | mockup `:root` `8px` == production (57.26 made it px); mockup also adds `--radius-sm` `--radius-lg` |
| `--row-h` (`36px`) `--pad` (`14px`) `--gap` (`10px`) | mockup `:root` + `[data-density]` overrides identical to production 57.20 values |

### 2d. shadcn-only — NO collision, KEPT

`--background` `--foreground` `--accent`(+fg) `--secondary`(+fg) `--destructive`(+fg) `--muted`(+fg) `--input` `--ring` + all semantic `*-foreground`. Mockup has no same-named token → stays as shadcn HSL with `hsl(var(--X))` bridge; retired page-by-page in Phase 2.

---

## 3. 22-route before/after regression matrix

Captured 1440×900 via `frontend/scripts/route-sweep.mjs`. Before = Day 0 (this branch, pre-switch). After = Day 3 (post Layer 2/3/4 + theme).

| # | Route | Shell | Before (Day 0) | After (Day 3) | vs Mockup | Verdict |
|---|-------|-------|----------------|---------------|-----------|---------|
| 1 | `/` | Home | ✅ captured | — | — | TBD |
| 2 | `/auth/login` | AuthShell | ✅ captured | — | — | TBD |
| 3 | `/auth/callback` | AuthShell | ✅ captured | — | — | TBD |
| 4 | `/auth/register` | AuthShell | ✅ captured | — | — | TBD |
| 5 | `/auth/invite/:token` | AuthShell | ✅ captured | — | — | TBD |
| 6 | `/auth/mfa` | AuthShell | ✅ captured | — | — | TBD |
| 7 | `/auth/expired` | AuthShell | ✅ captured | — | — | TBD |
| 8 | `/auth/dev` | AuthShell | ✅ captured | — | — | TBD |
| 9 | `/overview` | AppShellV2 | ✅ captured | — | — | TBD |
| 10 | `/chat-v2` | AppShellV2 | ✅ captured | — | — | TBD |
| 11 | `/orchestrator` | AppShellV2 | ✅ captured | — | — | TBD |
| 12 | `/subagents` | AppShellV2 | ✅ captured | — | — | TBD |
| 13 | `/loop-debug` | AppShellV2 | ✅ captured | — | — | TBD |
| 14 | `/memory` | AppShellV2 | ✅ captured | — | — | TBD |
| 15 | `/state-inspector` | AppShellV2 | ✅ captured | — | — | TBD |
| 16 | `/governance` | AppShellV2 | ✅ captured | — | — | TBD |
| 17 | `/verification` | AppShellV2 | ✅ captured | — | — | TBD |
| 18 | `/cost-dashboard` | AppShellV2 | ✅ captured | — | — | TBD |
| 19 | `/sla-dashboard` | AppShellV2 | ✅ captured | — | — | TBD |
| 20 | `/admin-tenants` | AppShellV2 | ✅ captured | — | — | TBD |
| 21 | `/tenant-settings` | AppShellV2 | ✅ captured | — | — | TBD |
| 22 | `/compaction` (PROP stub representative) | AppShellV2 | ✅ captured | — | — | TBD |

Triage legend (Day 3): 🟢 intended-improvement · 🟡 transition-drift (Phase-2 backlog) · 🔴 catastrophic (in-sprint fix) · 🟠 structural-regression (carryover AD).

---

## 4. Day 0 三-prong D-PRE findings

| ID | Sev | Finding | Implication |
|----|-----|---------|-------------|
| D-PRE-1 | 🟠 | Mockup `styles.css` HAS a full **light theme** — `[data-theme="light"]` + 3 light variants (strict/refined/shadcn), L114-164. Reports 02/03 imprecisely said "no light theme" / "dark-only". | Plan US-C2 "dark-only" premise corrected. Revised approach: keep light support; `ThemeProvider` toggles the mockup `[data-theme]` attribute. **Surfaced to user — confirm before Day 2.** |
| D-PRE-2 | 🟠 | Mockup `--bg`/`--bg-1..3`/`--bg-hover`/`--border`/`--border-strong`/`--fg`/`--fg-muted`/`--fg-subtle`/`--shadow` + `--radius*` are defined in `[data-theme][data-variant]` selectors, **NOT `:root`**. `:root` carries only theme-invariant tokens. | Production `<html>` MUST carry `data-theme="dark" data-variant="linear"` for the verbatim CSS to resolve bg/fg at all. Day 1 sets the static attributes on `index.html`; Day 2 wires the `ThemeProvider` toggle. |
| D-PRE-3 | 🟢 | Mockup `styles.css` uses **0 `rem`** — fully px-based. | `html{font-size:13px}` hack is safe to KEEP through Phase 1 (px mockup classes unaffected; hack only keeps the 13 not-re-pointed Tailwind-rem pages compact). Plan R2 default KEEP confirmed. |
| D-PRE-4 | 🟢 | Token-collision set fully enumerated — see §2. ~28 collisions: 2 tricky (de-collide) + ~26 shared-intent/identical (retire prod approximation). | Day 2 Layer 4 has the exact per-token resolution table. |
| D-PRE-5 | 🟢 | `--radius` / `--row-h` / `--pad` / `--gap` mockup values == production values (57.20/57.26). | Retiring production's = zero value change for these (safe). |
| D-PRE-6 | 🟢 | 4 Vitest files reference theme/token literals: `AuthShell.test.tsx`, `AppShellV2.test.tsx`, `UserMenu.test.tsx`, `adminTenantsRoleGate.test.tsx`. | Day 4 US-E1 examines each; adapt if asserting a retired token / theme path (NOT delete). |

**Prong 1 path verify**: 0 path drift — `index.css` / `main.tsx` / `tailwind.config.ts` / `ThemeProvider.tsx` present (edits); `styles-mockup.css` absent (create); `route-sweep.mjs` present (reused); frontend CI = `.github/workflows/frontend-ci.yml`.
**PoC reference confirmed**: `investigation/mockup-fidelity-poc` `main.tsx` imports `./styles-mockup.css` (L46) after `./index.css` (L40); PoC `styles-mockup.css` present.

---

## 5. Final verdict (Day 4)

_TBD — per-route verdict + Phase-2 re-point epic backlog._

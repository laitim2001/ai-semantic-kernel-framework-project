# Sprint 57.24 — AD-Mockup-Existing-Pages-Retrofit Tier 1 (6-Page Cosmetic Retrofit)

**Status**: Plan drafted 2026-05-19 (Day 0 pending)
**Branch**: `feature/sprint-57-24-mockup-fidelity-retrofit-tier-1`
**Class**: NEW `mockup-fidelity-retrofit` 0.55 (1st application; HYBRID per `claudedocs/1-planning/next-phase-candidates.md §3`)
**Bottom-up**: ~10 hr → **Calibrated commit**: ~5.5 hr (multiplier 0.55)
**Day count**: 4 (Day 0-3; shorter than 5-day sprints due to small scope)
**Mockup reference**: `reference/design-mockups/` (canonical visual source of truth per CLAUDE.md §Frontend Mockup-Fidelity Hard Constraint)
**Predecessors**: Sprint 57.22 audit (Units 8 / 9 / 11 + admin/tenants units) / Sprint 57.20 + 57.21 partial coverage (/overview + /chat-v2 already migrated) / Sprint 57.23 Auth Tier 1 closed (6 P0 Auth routes rebuilt)

---

## Sprint Goal

Retrofit **6 previously-shipped frontend pages** (cost-dashboard / sla-dashboard / verification + verification/recent / admin/tenants list / admin/tenants/settings) for mockup fidelity alignment per Sprint 57.22 AUDIT-REPORT Tier 1 priorities. Frontend-only cosmetic retrofit; no backend changes; no structural rebuild (any STRUCTURAL severity drift defers to a dedicated rebuild sprint).

---

## Background

### Why Sprint 57.24 (this sprint)

Sprint 57.22 comprehensive audit identified 41 routes; 32 P0 + 5 P1 + 5 P2 + 2 P3. Of those:
- **6 Auth P0 routes** closed by Sprint 57.23 (full rebuild)
- **5 Operations routes** partially closed by Sprint 57.19 (Round 1) + 57.20 (token-sweep) + 57.21 (chat-v2 Phase-1)
- **Remaining Tier 1 retrofit** = pre-mockup pages from Sprint 57.1-57.12 that pre-date the mockup integration (Sprint 57.18 wired tokens), have NOT received any mockup-fidelity treatment yet, and have only **cosmetic-level drift** (no STRUCTURAL/FUNCTIONAL gap requiring rebuild)

This sprint addresses the remaining cosmetic-level Tier 1 retrofit backlog.

### User Q1 + Q2 decisions (2026-05-19 user alignment)

**Q1 — pages**: 6 confirmed (/cost-dashboard / /sla-dashboard / /verification + /verification/recent / /admin/tenants list / /admin/tenants/settings). chat-v2 + governance excluded (covered by 57.20+57.21 + 57.9 closeout respectively).

**Q2 — /memory STRUCTURAL retrofit**: DEFER to NEW AD-Memory-Structural-Rebuild-Phase58. Sprint 57.22 Unit 10 identified 5-scope × 3-time-scale matrix + time-travel scrubber + memory-ops timeline as missing — exceeds cosmetic retrofit scope. Added to `next-phase-candidates.md` as new candidate.

### What is preserved (NOT retrofitted this sprint)

- **Backend APIs**: 0 backend changes; all retrofit is frontend-only
- **Page-level data fetching logic**: existing hooks / queries / stores preserved as-is
- **Page-level routing / navigation**: route paths + AppShellV2 chrome untouched
- **Vitest behavioral test coverage**: each page's existing Vitest cases preserved; only adapt selectors if rewrite breaks anchor (per Sprint 57.23 lesson)
- **Backend stub states**: any "Phase 58+" stubs (e.g. admin/tenants empty state) preserved as-is

### What gets retrofitted (this sprint scope)

For each of the 6 pages:
1. **Tailwind class drift** between current state and mockup-token semantics → Tailwind utility iteration to parity (mockup token vocabulary already wired Sprint 57.18; arbitrary `text-[#hex]` / `p-[12px]` escape hatches only when mockup doesn't map to existing tokens)
2. **Spacing / sizing / radius / shadow alignment** per mockup line range
3. **Color shade alignment** per mockup `--primary` / `--warning` / `--success` / `--destructive` / `--bg-1` token references
4. **Component primitive swaps** where appropriate (e.g. mockup uses Card variant X but production has variant Y)
5. **Icon size / position alignment** per mockup
6. **Inline-style escape hatches** removed where Tailwind can express (e.g. flex / gap / padding); preserved with `STYLE.md §3` reason comment only when token vocabulary insufficient

### V2 紀律對齐 (per Sprint 57.21 + 57.23 pattern)

- ✅ Frontend-only spike (per Q2 echo of 57.23 frontend-only decision)
- ✅ Backend changes: 0 (per Sprint 57.23 carryover queue; Phase 58+ scope)
- ✅ LLM Provider Neutrality: N/A (frontend; no SDK)
- ✅ 17.md Single-source: no new contracts added
- ✅ Mockup-Fidelity Hard Constraint enforced (mockup = canonical visual source)

---

## User Stories

### Group A — Day 0 setup + 三-prong + Playwright MCP mockup baselines

**US-A1**: As Sprint 57.24 owner, I want to capture pre-retrofit production screenshots + mockup target screenshots at 1440×900 for all 6 pages so that DRIFT-REPORT verdicts can be derived from side-by-side compare per Mockup-Fidelity DoD.

### Group B — cost-dashboard + sla-dashboard retrofit (Day 1)

**US-B1**: As an admin viewing `/cost-dashboard`, I want the Cost Ledger page chrome (page title / sub / path pill / 4 KPI cards / admin-only provider breakdown widget) to match mockup `page-cost.jsx` (or equivalent) token-by-token + spacing-by-spacing for visual consistency with the rest of Sprint 57.18-57.23 ship-pages.

**US-B2**: As an admin viewing `/sla-dashboard`, I want the SLA monitor page chrome to match mockup `page-sla.jsx` (or equivalent) for visual consistency.

### Group C — verification + verification/recent retrofit (Day 2 AM)

**US-C1**: As a user viewing `/verification` (redirects to `/verification/recent`), I want the recent-verifications list page chrome to match mockup `page-verification.jsx` (or equivalent) — Sprint 57.11 pre-mockup; needs visual chrome migrate to mockup token vocabulary.

### Group D — admin/tenants list + admin/tenants/settings retrofit (Day 2 PM)

**US-D1**: As an admin viewing `/admin/tenants` list, I want the tenant list page chrome (filter pill / table / pagination / actions) to match mockup token vocabulary.

**US-D2**: As an admin viewing `/admin/tenants/settings`, I want the tenant settings 6-tab navigator + per-tab body chrome to match mockup token vocabulary. **Sprint 57.22 audit Unit 31 flagged this for architectural finding** — confirm during Day 0 三-prong whether retrofit-only suffices or escalates to STRUCTURAL deferred AD.

### Group E — closeout (Day 3)

**US-E1**: As Sprint 57.24 owner, I want Vitest baselines preserved (current 369/369 PASS) post-retrofit (adapt selectors only if rewrite breaks anchor; per Sprint 57.23 lesson learned).

**US-E2**: As Sprint 57.24 owner, I want Playwright MCP pair-verify capture for all 6 retrofitted pages at 1440×900 → DRIFT-REPORT-RETROFIT-TIER-1.md verdicts (PARITY / COSMETIC / STRUCTURAL / FUNCTIONAL) per Mockup-Fidelity DoD.

**US-E3**: As Sprint 57.24 owner, I want retrospective.md + memory subfile + MEMORY.md pointer + sprint-workflow.md calibration matrix row added for NEW class `mockup-fidelity-retrofit` 0.55 1st app baseline.

---

## Technical Specifications

### Retrofit pattern (uniform across 6 pages)

For each page in 6-page scope:

1. **Day 0 mockup baseline capture**: Playwright MCP screenshot mockup target at 1440×900 → `claudedocs/4-changes/sprint-57-24-*/screenshots/mockup/<page-slug>.png`
2. **Day 0 production pre-retrofit capture**: Playwright MCP screenshot production at 1440×900 → `screenshots/pre-retrofit/<page-slug>.png`
3. **Day 0 side-by-side diff**: identify drift severity (cosmetic / structural / functional)
4. **Day 1-2 retrofit**: Tailwind class iteration; preserve existing logic / state / data fetching; adapt only visual chrome
5. **Day 3 post-retrofit capture**: Playwright MCP screenshot production at 1440×900 → `screenshots/post-retrofit/<page-slug>.png`
6. **Day 3 verdict**: PARITY / COSMETIC documented per page in DRIFT-REPORT-RETROFIT-TIER-1.md

### Token usage (per Sprint 57.18 wired tokens)

All retrofit work uses mockup tokens already wired in `tailwind.config.ts` + `index.css` since Sprint 57.18:
- `--primary` (oklch indigo HSL approximation)
- `--bg` / `--bg-1` / `--bg-2` / `--bg-3` / `--background` / `--foreground`
- `--fg` / `--fg-muted` / `--fg-subtle`
- `--border` / `--ring`
- `--warning` / `--success` / `--destructive` / `--info`
- `--memory` / `--tool` / `--verification` (domain tokens)
- `--radius-sm` / `--radius` / `--radius-lg`

Arbitrary `text-[#hex]` / `p-[Npx]` escape hatches per STYLE.md §3 ONLY when mockup design cannot map to existing token (rare for retrofit since mockup IS the wired token source).

### Common-case retrofit shapes

**Shape 1 (typical)**: Tailwind class swap
```diff
- className="rounded-md border border-gray-200 bg-white p-4"
+ className="rounded-[var(--radius)] border border-border bg-bg-1 p-4"
```

**Shape 2**: shadcn primitive variant swap
```diff
- <Card variant="default">
+ <Card>  {/* default mockup-style */}
```

**Shape 3**: inline-style removed where Tailwind can express
```diff
- <div style={{ display: "flex", gap: 8 }}>
+ <div className="flex gap-2">
```

**Shape 4**: spacing precision match
```diff
- className="p-4"  {/* current 16px */}
+ className="p-3"  {/* mockup 12px */}
```

### Backend impact

0 backend changes. Each retrofit is purely a Tailwind class + JSX restructure on existing pages.

---

## File Change List

### Modified files (6 page directories — exact LOC delta per page TBD Day 0)

- `frontend/src/pages/cost-dashboard/index.tsx` — Tailwind retrofit ~10-30 lines diff
- `frontend/src/pages/sla-dashboard/index.tsx` — Tailwind retrofit ~10-25 lines diff
- `frontend/src/pages/verification/index.tsx` — Tailwind retrofit ~10-25 lines diff
- `frontend/src/pages/verification/recent.tsx` (or `[slug].tsx`) — Tailwind retrofit ~10-20 lines diff
- `frontend/src/pages/admin-tenants/index.tsx` (or `list.tsx`) — Tailwind retrofit ~15-30 lines diff
- `frontend/src/pages/tenant-settings/index.tsx` (or per-tab body files) — Tailwind retrofit ~20-40 lines diff (largest; 6-tab navigator + per-tab bodies)

**Per-page MHist update** required per `.claude/rules/file-header-convention.md` — single line entry: `Sprint 57.24 — mockup-fidelity retrofit (closes audit Unit N)`

### New files

- `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-24-plan.md` (this file)
- `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-24-checklist.md`
- `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-24/progress.md`
- `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-24/retrospective.md` (Day 3 closeout)
- `claudedocs/4-changes/sprint-57-24-mockup-fidelity-retrofit-tier-1/DRIFT-REPORT-RETROFIT-TIER-1.md`
- `claudedocs/4-changes/sprint-57-24-mockup-fidelity-retrofit-tier-1/screenshots/{mockup,pre-retrofit,post-retrofit}/` (12 PNGs total per Day 3)
- `memory/project_phase57_24_mockup_fidelity_retrofit_tier_1.md` (Day 3 closeout)

### Backend changes

0 backend files modified. No new tests, no migrations, no API changes.

---

## Acceptance Criteria

1. ✅ All 6 pages retrofitted; per-page MHist updated; commits 1 page per (or 2 pages grouped) per V2 surgical-change discipline
2. ✅ Vitest 369/369 PASS preserved (selector adapt only if needed; per Sprint 57.23 a11y-scan + visual-regression lesson)
3. ✅ tsc 0 errors / ESLint silent / Build within +5 KB of post-Sprint-57-23 main bundle baseline (~329 KB)
4. ✅ Playwright MCP pair-verify completed for all 6 pages → DRIFT-REPORT verdicts all PARITY or COSMETIC (0 STRUCTURAL / 0 FUNCTIONAL — otherwise escalate to defer AD)
5. ✅ i18n key changes (if any) symmetric between en + zh-TW; jq paths diff = 0
6. ✅ retrospective.md Q1-Q7 + Q8 NEW class calibration narrative recorded
7. ✅ `.claude/rules/sprint-workflow.md` calibration matrix +1 row for `mockup-fidelity-retrofit` 0.55 1st app
8. ✅ memory subfile + MEMORY.md +1 pointer (per REFACTOR-001 §Sprint Closeout policy)
9. ✅ CLAUDE.md minimal touch (Current Sprint row + Last Updated footer only)
10. ✅ All 6 pages' carryover ADs (e.g. AD-Memory-Structural-Rebuild-Phase58 / any newly-identified STRUCTURAL drift) documented in `next-phase-candidates.md`

---

## Workload

**Bottom-up estimate ~10 hr → calibrated commit ~5.5 hr (multiplier 0.55)**

| Day | Goal | Bottom-up estimate |
|-----|------|--------------------|
| Day 0 | Setup + 三-prong (Path/Content/Schema) + Playwright MCP mockup baselines + production pre-retrofit captures + progress.md + DRIFT-REPORT skeleton | ~2 hr |
| Day 1 | cost-dashboard retrofit + sla-dashboard retrofit | ~3-4 hr |
| Day 2 | verification 2 pages retrofit + admin/tenants list retrofit + admin/tenants/settings retrofit | ~3-4 hr |
| Day 3 | Playwright MCP post-retrofit captures + DRIFT-REPORT verdicts + Vitest + closeout (retrospective + memory + sprint-workflow + CLAUDE.md + commits + push + PR) | ~1-2 hr |

**Calibration class baseline**: `mockup-fidelity-retrofit` 0.55 (HYBRID per candidate §3 = cosmetic mechanical 0.45 ~50% weight + structural design 0.65 ~30% weight + closeout 0.80 ~20% weight = ~0.55 mid-band)

**Calibration first-app rule**: KEEP 0.55 regardless of ratio outcome per `When to adjust` 3-sprint window rule; if recurs 2-3× → propose 0.55 → 0.40-0.45 or 0.65-0.70 per evidence.

---

## Risks & Mitigations

### R1 — Sprint 57.22 audit Unit 31 (tenant-settings 6-tab) escalates to STRUCTURAL

**Probability**: Medium. Sprint 57.22 audit flagged tenant-settings 6-tab as "architectural finding"; if mockup intent shows materially different tab structure (e.g. 6 tabs → 5 / 7 / different grouping), retrofit insufficient.
**Mitigation**: Day 0 三-prong content-verify on `tenant-settings/index.tsx` + mockup reference. If STRUCTURAL → escalate US-D2 to AD-Tenant-Settings-Structural-Rebuild-Phase58 carryover + downgrade Sprint 57.24 scope to 5 pages.

### R2 — Mockup tokens (Sprint 57.18) drift from current page Tailwind classes by more than cosmetic

**Probability**: Medium-low. Sprint 57.18 wired tokens 1:1 from mockup; existing pages used shadcn defaults pre-Sprint-57-18, so drift is mostly classname-level.
**Mitigation**: Side-by-side mockup vs production diff at Day 0 captures drift severity; STRUCTURAL escalates to defer.

### R3 — Playwright MCP browser-stuck (per Sprint 57.23 Day 4 lesson)

**Probability**: Medium. Prior session stuck Playwright browser; reset may not work mid-session.
**Mitigation**: First action Day 0 is Playwright MCP `browser_close` to attempt fresh session. If still stuck → defer Playwright MCP captures to AD-Sprint-57-24-Playwright-Visual-Verify-Followup; closure via code-level audit + Sprint 57.22 baseline (parallel to Sprint 57.23 Day 4 workaround).

### R4 — Visual-regression CI baseline drift on all 6 pages

**Probability**: High (this IS the expected behavior). Sprint 57.18+ visual-regression CI captures `/cost-dashboard` / `/sla-dashboard` / `/admin/tenants` / `/admin/tenants/settings` / `/verification` snapshots; retrofit moves them.
**Mitigation**: Trigger visual-baseline workflow_dispatch Day 3 → cherry-pick regenerated baselines (per Sprint 57.23 Day 4 PR #156 recovery pattern). AD-CI-7-GHA-PR-Permission still blocks auto-PR-create — same workaround applies (manual cherry-pick from `chore/visual-baselines-XXXX` branch).

### R5 — Selector drift breaks Vitest/Playwright tests (per Sprint 57.23 lesson)

**Probability**: Low for retrofit (cosmetic class swaps don't usually break selectors). Higher if shadcn primitive swap.
**Mitigation**: Day 0 三-prong includes grep of Vitest + Playwright tests for each page's anchor selectors; if anchor at risk → adapt selector preemptively (NOT post-fact, per 57.23 lesson).

### Common Risk Classes referenced (sprint-workflow.md)

- Risk Class A (paths-filter vs required_status_checks CI infra): N/A this sprint (no `.github/workflows/**` changes)
- Risk Class B (cross-platform mypy `unused-ignore`): N/A this sprint (frontend-only; no Python)
- Risk Class C (module-level singleton across test event loops): N/A this sprint (pure cosmetic frontend; no backend singletons)

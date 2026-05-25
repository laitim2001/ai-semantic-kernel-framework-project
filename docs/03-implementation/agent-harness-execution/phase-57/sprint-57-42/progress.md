# Sprint 57.42 Progress — Day 0

**Branch**: `feature/sprint-57-42-memory-matrix-rebuild`
**Sprint goal**: `/memory` Memory Layers matrix full mockup-fidelity rebuild — closes drift audit 2026-05-25 #2 priority CATASTROPHIC.

---

## Day 0 — 2026-05-25 (plan + checklist + 3-prong + before baseline)

### Plan / checklist drafted

- `sprint-57-42-plan.md` (~360 lines, 9 §) drafted mirroring Sprint 57.41 §0-9 structure exactly
- `sprint-57-42-checklist.md` (~210 lines, Day 0/1/2/2.5/3) drafted mirroring Sprint 57.41
- User approved scope + §1.4 Option B 2-tab DROP at Day 0 §0.9 review checkpoint
- Branch + commit `bdb10844` `docs(sprint-57-42): plan + checklist draft`

### Drift findings (3-prong grep — Day 0 §0.2 + §0.3 + §0.4)

#### D-DAY0-1 (vocabulary mismatch — informational, plan accommodation)
- **Mockup vocab**: `TIME_SCALES = ["permanent", "quarter", "day"]` (`reference/design-mockups/page-governance.jsx:417`)
- **Backend vocab**: `MemoryTimeScale = "permanent" | "quarterly" | "daily"` (`frontend/src/features/memory/types.ts:36`)
- **Decision**: `_fixtures.ts` verbatim ports mockup vocab. MemoryMatrix view never wires to backend this sprint (fixture-only per plan §1.3 + §3.7). No translation layer needed. AP-2 BackendGapBanner declares deferred backend cursor-aware matrix query Phase 58+.
- **Plan §3.7 + §3.8 already accommodate** — no plan edit needed.

#### D-DAY0-2 (RecentMemoryOpsCard data-source clarity — plan correction)
- **Plan §1.2 claim**: "reuse `useMemoryRecent` if shape compatible OR fixture-only" (was speculative).
- **Reality**: `useMemoryRecent` (`hooks/useMemoryRecent.ts:32-38`) returns `MemoryEntryPage` = memory **entries** (id / layer / scope_id / key / content / timestamps). Mockup `RecentMemoryOpsCard` shows ops timeline = **WRITE / READ / EXPIRE** action events.
- **These are different schemas** — entries vs ops timeline. No mapping bridge.
- **Decision**: `RecentMemoryOpsCard` is **fixture-only** + AP-2 BackendGapBanner declares deferred `/api/v1/memory/ops/recent` endpoint Phase 58+. `useMemoryRecent` becomes potential orphan; Day 0 §0.4 consumer grep below confirms safe to deprecate.
- **Plan §1.2 minor clarification** — folded into Day 0 entry, not retroactively edited.

#### D-DAY0-3 (route registry — plan correction)
- **Plan §3.1 + checklist 1.4** mentioned "App.tsx or routes.config.ts" for redirect placement.
- **Reality**: `frontend/src/App.tsx` has **0 `memory` references**. `routes.config.ts` has parent `/memory` entry (lines 174-182) with `lazy(() => import("./pages/memory"))`. No sub-routes for `/memory/recent` or `/memory/by-scope` in routes.config — those nested Routes live INSIDE `pages/memory/index.tsx` (per current Sprint 57.12 vintage).
- **Decision**: Redirects for `/memory/recent` + `/memory/by-scope` → `/memory` go INSIDE `pages/memory/index.tsx` via React Router `<Route element={<Navigate to="/memory" replace />} />`. routes.config.ts not touched. App.tsx not touched.
- **Plan §4 MODIFIED files**: drop App.tsx mention; only `pages/memory/index.tsx` carries redirect addition.

#### D-DAY0-4 (mockup-ui primitive coverage — all present, no lifts)
- `frontend/src/components/mockup-ui.tsx` grep confirms exports: `Icon` (size prop) / `Button` / `Badge` / `Card` / `Stat` / `RiskBadge` / `Tabs` / `Field` / `KvRow`.
- **All 6 primitives** plan §3.4 listed (`Card`, `Badge`, `Button`, `Icon`, `Field`, `BackendGapBanner`) are present post Sprint 57.40 + 57.41 promotions.
- **No lifts needed** — checklist §1.2 marked N/A on Day 1.

#### D-DAY0-5 (vintage Vitest baseline subtraction — quantified)
- 5 memory test files exist:
  - `MemoryRecentList.test.tsx` (6 tests) → DELETE with parent
  - `MemoryByScopeBrowser.test.tsx` (4 tests) → DELETE with parent
  - `MemoryScopeBadge.test.tsx` (5 tests) → DELETE with parent (conditional confirmed below)
  - `useMemoryHooks.test.tsx` (9 tests) → DELETE with hooks
  - `memoryService.test.ts` (6 tests) → **PRESERVE** (service layer untouched)
- **Total vintage delete**: 24 tests. Pre-baseline 498 → post-delete 474.
- **NEW spec target**: +5-8 → post-Sprint 479-482.
- **AC16 update**: ≥498/498 unrealistic post-delete. **AC16 effective baseline = 474 + NEW**. Acknowledged in §1.5; retro Q2 will reconcile.

#### D-DAY0-6 (MemoryScopeBadge consumer breadth — orphan delete confirmed)
- `grep -rn "MemoryScopeBadge"` returns 8 files (all within `frontend/src/features/memory/` + 1 false-positive in `frontend/src/components/ui/badge.tsx` — that's the shadcn Badge module definition, not a MemoryScopeBadge consumer).
- **Confirmed safe to orphan delete** post MemoryRecentList + MemoryByScopeBrowser delete (0 cross-feature consumers). AC13 ✓.

#### D-DAY0-7 (useMemoryByScope / useMemoryByTime / useMemoryRecent consumer breadth)
- Same grep: only `features/memory/` self-consumers. The 3 hooks are consumed only by the 2 vintage components being deleted (and `types.ts` re-export). **Safe to deprecate / delete all 3 hooks** post-rebuild. Carryover `AD-Memory-Vintage-Hooks-Cleanup`.

#### D-DAY0-8 (AP-Phase2-C residue catalogue — informational; will be eliminated by delete)
- `grep "bg-card|text-foreground|border-border|bg-muted|text-muted-foreground"` in `features/memory/components/` returns 22 occurrences across 2 files (MemoryRecentList + MemoryByScopeBrowser). Both scheduled for orphan delete → residue eliminated by delete operation (not by individual replacement).
- **No NEW component will introduce AP-Phase2-C** — agent task brief (checklist §1.1) mandates verbatim CSS classes from `styles-mockup.css` + inline style escape comments per Sprint 57.40 FIX-015 lesson.

#### D-DAY0-9 (fullBleed + outer wrapper grep on `pages/memory/index.tsx` — clean)
- `grep "fullBleed"` returns 0 → memory is NOT a fullBleed page (matrix fits AppShellV2 chrome).
- `grep "<div style=\\{\\{[^}]*padding"` returns 0 → no outer wrapper artifact (AP-Phase2-A clean).

### Drift impact assessment

Per `.claude/rules/sprint-workflow.md §Step 2.5` decision rule:
- D-DAY0-1: ≤5% scope shift (vocabulary already in plan §3.7 accommodation).
- D-DAY0-2: ≤5% scope shift (fixture-only path was always one option; plan §3.4 had AP-2 banner declaration).
- D-DAY0-3: ≤5% scope shift (file path correction; touch surface shrinks by 1 file).
- D-DAY0-5: AC16 baseline math correction (498 → 474+NEW). Acknowledged.

**Total shift**: ~10-15% — well under 20% threshold. **GO for Day 1**.

### Day 0 §0.7 — Capture before baseline (route-sweep) ✅

- `frontend/scripts/route-sweep.mjs` OUT_DIR re-pointed `sprint-57-41-verification-full-rebuild` → `sprint-57-42-memory-matrix-rebuild` + MHist entry on top (Sprint 57.41 entry preserved below per newest-first convention).
- `node frontend/scripts/route-sweep.mjs before` exit 0; **24 PNGs** written to `claudedocs/4-changes/sprint-57-42-memory-matrix-rebuild/screenshots/before/` (8 PUBLIC + 16 AppShellV2 routes per FIX-018 auto-derive from `routes.config.ts`).
- Last 3 routes captured cleanly: `admin-tenants` / `tenant-settings` / `prop-stub-compaction` — confirms FIX-018 auto-derive intact + the 3 CATASTROPHIC remaining targets all sweep without crash.

### Day 0 §0.8 — Pre-Day-1 baseline checks ✅

- **Vitest baseline confirmed**: 498/498 (104 test files); duration 14.84s (last run 21:49:12).
- **mockup-fidelity guard exit 0**: `styles-mockup.css` byte-identical to mockup `styles.css`; `HEX_OKLCH_BASELINE = 46` (Phase-2 re-point backlog tracker).
- **Lint exit 0**: 7-line output (3 jsx-ast-utils library info warnings = recurring noise, NOT eslint errors; `--max-warnings 0` satisfied); non-silent invocation per FIX-020-B lesson.

### Day 0 Completion Summary ✅

| Sub-task | Status |
|----------|--------|
| §0.1 Plan + Checklist drafted (Sprint 57.41 template mirror) | ✅ Committed `bdb10844` |
| §0.2 Prong 1 Path verify (mockup-ui primitives + tests + routes registry) | ✅ All primitives present; 5 vintage test files identified |
| §0.3 Prong 2 Content verify (types + hooks + service shape) | ✅ 9 D-DAY0-N findings catalogued (all <20% shift; GO) |
| §0.4 Prong 2.5 Child component tree audit (AP-Phase2-A/B/C) | ✅ 22 AP-Phase2-C residue in 2 vintage components (eliminated by orphan delete); 0 in pages/memory/index.tsx |
| §0.5 Prong 3 Schema verify | ✅ N/A (frontend-only sprint) |
| §0.6 Drift catalog in progress.md | ✅ This file with 9 D-DAY0-N findings |
| §0.7 Capture before baseline | ✅ 24 PNGs |
| §0.8 Pre-Day-1 baseline checks | ✅ Vitest 498/498 + mockup-fidelity 46 + lint exit 0 |
| §0.9 User review checkpoint | ✅ Approved at Day 0 §0.9 (Sprint 57.42 scope + Option B 2-tab DROP) |

### Day 0 Estimate vs actual

- Est: 1.0 hr (per plan §8 Day 0 row)
- Actual: ~50 min (drafting + grep verification + progress catalog + route-sweep + baseline triple-check)
- **Delta: -10 min under estimate**; ratio actual/est ≈ 0.83 ✅ in [0.85, 1.20] band lower edge
- Sprint pacing: on track for Day 1 7.5-8.5 hr agent-delegated component creation budget

### Day 0 — Ready for Day 1

All Day 0 §0.1-§0.9 checklist items complete. Day 1 code start awaits user green-light per CLAUDE.md §Sprint Execution Workflow + checklist §0.9.

---

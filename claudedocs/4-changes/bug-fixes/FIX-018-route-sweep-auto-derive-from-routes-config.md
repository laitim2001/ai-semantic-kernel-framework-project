# FIX-018: route-sweep.mjs auto-derive APPSHELL_ROUTES from routes.config.ts

**Date**: 2026-05-25
**Sprint**: post-Sprint-57.39 micro-fix series (6th in sequence — FIX-012 → FIX-013 → FIX-014 → FIX-015 → FIX-016 → FIX-017 → **FIX-018**)
**Scope**: Frontend / scripts (prevention infrastructure)
**Closes**: `AD-RouteSweep-Auto-Derive` (logged Sprint 57.39 retro Q4 #3 as FIX-016 carryover)

## Problem

`frontend/scripts/route-sweep.mjs` carried a hand-maintained `APPSHELL_ROUTES`
array. Every PROP→real promotion required a manual patch to keep the sweep
in sync with `frontend/src/routes.config.ts` (the single source of truth that
`App.tsx` + `Sidebar.tsx` consume).

The last manual sync was FIX-016 (PR #184) — after Sprint 57.39 shipped
`/redaction` and `/error-policy` as real pages, the sweep silently kept
recording 13 real routes for the 1st deliberate-test of the `-with-extras`
0.65 baseline. The two new real pages produced no PNG evidence in the
Sprint 57.39 baseline OUT_DIR until FIX-016 patched the array.

**Class of bug**: silent regression on registry-promotion. Every future
PROP→real promotion would re-introduce the same gap until route-sweep was
sourced from the registry itself.

## Root Cause

Two independent sources for the "active AppShellV2 routes" set:

| Source | Updated by |
|--------|------------|
| `routes.config.ts` `ROUTES[]` | Every page-shipping sprint (App.tsx + Sidebar consume it via .filter()) |
| `route-sweep.mjs` `APPSHELL_ROUTES` | Only updated when someone remembers — no enforcement, no CI guard |

The two sources drifted whenever a sprint shipped a new active route without
also editing the sweep script. Discovery only at the next baseline capture
(if ever).

## Solution

Replace hardcoded `APPSHELL_ROUTES` with `deriveAppshellRoutes()` — a regex
parser that:

1. Reads `frontend/src/routes.config.ts`
2. Locates the `export const ROUTES: RouteEntry[] = [...]` block via anchored regex
3. Splits the body on `},` boundaries (safe: RouteEntry blocks have no
   nested braces — `lazy(() => import(...))` uses parens only)
4. For each block, extracts `path:` + `active:` + optional `proposed:`
5. Classifies:
   - `active=true && !proposed` → **real page** (slug = `path.slice(1).replace(/\//g, '-')`)
   - `active=true && proposed=true` → **PROP stub** (slug = `prop-stub-${slug}`)
   - `active=false` → excluded (no `<Route>` generated, no screenshot needed)
6. Returns `{routes: [...real, propStubs[0] if any], realCount, propTotal}`
   — only the FIRST PROP stub is included as a representative because all
   PROP stubs render the same `ComingSoonPlaceholder` shell

**Fail-fast safeguards** (per PR #186 `AD-Pre-Push-Lint-Silent-Suppression-Anti-Pattern` lesson):

- If `export const ROUTES: RouteEntry[] = [...]` regex doesn't match → `throw`
  (schema changed; update parser)
- If derived `real.length === 0` → `throw` (parser silently produced empty
  result; CHECK schema before continuing)

**Dry-run mode** (`--list-only`):

```bash
node scripts/route-sweep.mjs before --list-only
```

Prints the derived list + counts and exits 0 without launching browser /
creating OUT_DIR. Used during this fix to validate the auto-derive output
byte-identical to the prior FIX-016-patched hardcoded list.

**Greppable evidence on real runs**:

```
=== route-sweep [before] → /path/to/OUT_DIR ===
    auto-derived: 15 real AppShellV2 routes + 1 of 12 PROP rep (FIX-018)
```

Future PROP→real promotions are picked up automatically the next sprint —
no `AD-RouteSweep-Coverage-Extend-PROP-Promoted-Pages` carryover needed.

## Verification

```bash
cd frontend && node scripts/route-sweep.mjs before --list-only
```

Output:
- `PUBLIC_ROUTES (8)`: 8 home + AuthShell routes (unchanged — these are
  hardcoded because they bypass AppShellV2)
- `APPSHELL_ROUTES (16 = 15 real + 1 of 12 PROP rep)`:
  - 15 real: `/overview` `/chat-v2` `/orchestrator` `/subagents`
    `/loop-debug` `/memory` `/state-inspector` `/governance` `/verification`
    `/redaction` `/error-policy` `/cost-dashboard` `/sla-dashboard`
    `/admin-tenants` `/tenant-settings`
  - 1 PROP rep: `/compaction` (first `proposed:true` entry in declaration
    order — operations category)

**Byte-identical match to the FIX-016 hardcoded list** (16 entries; same
order; same slugs; same PROP representative).

Lint (per PR #186 non-silent rule):
- `npm run lint` — clean
- `npm run check:mockup-fidelity` — unchanged (HEX_OKLCH_BASELINE 45)
- `npx tsc --noEmit` — N/A (route-sweep.mjs is plain ESM, not TS)

## Impact

| Dimension | Before | After |
|-----------|--------|-------|
| Manual patches required per PROP→real promotion | 1 (FIX-016 class) | 0 |
| Drift detection | Only at next baseline capture (often weeks late) | Auto on every run |
| Silent regression risk | High | Zero (fail-fast `throw` on parse failure) |
| New route added without sweep update | Silent miss | Picked up next run |
| Backward compat | n/a | Same APPSHELL_ROUTES output shape; PNG file names unchanged |

**Future-proofing**:
- New `proposed:true` route added → registered automatically (12 → 13);
  the representative remains `/compaction` (first entry) unless someone
  re-orders the operations category
- New real route added → registered automatically (15 → 16+1=17); appears
  in next sweep baseline without manual sweep edit
- Schema change to `RouteEntry` (e.g. rename `active` field) → `throw` at
  parse time; clear error message points to parser

**Carryover ADs**:
- `AD-RouteSweep-Coverage-Extend-PROP-Promoted-Pages` (Sprint 57.39 Q4 #3) →
  **CLOSED** (root cause eliminated; future PROP→real promotions auto-sync)
- `AD-RouteSweep-Auto-Derive` (Sprint 57.39 Q4 #3 carryover) → **CLOSED** by this fix

**Related**:
- Sister fixes in FIX-014 (`__dirname` ESM derivation, PR #182) +
  FIX-016 (manual `+/redaction +/error-policy`, PR #184)
- Related rule: `.claude/rules/sprint-workflow.md` §Before Commit
  (non-silent lint requirement codified PR #186)

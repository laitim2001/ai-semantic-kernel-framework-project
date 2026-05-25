# Sprint 57.42 — AD-Memory-Layers-Matrix-Rebuild

**Phase**: 57 (Frontend SaaS)
**Sprint id**: 57.42
**Drafted**: 2026-05-25 (Day 0)
**Branch**: `feature/sprint-57-42-memory-matrix-rebuild`
**Class**: `frontend-mockup-strict-rebuild` (8th data point; 7-pt mean 0.76 at lower band edge — last 3 ratios 57.37A≈1.18 + 57.40≈0.36 + 57.41≈0.18 → 2 of 3 < 0.7 → lower-trigger NOT yet met (need 3 consecutive) → KEEP 0.60 per `.claude/rules/sprint-workflow.md` §When to adjust rule). **8th data point — if Sprint 57.42 also < 0.7, becomes 3rd consecutive below-band in 4-sprint window → lower-trigger MET → propose 0.60 → 0.40-0.45 lift in Sprint 57.43 retro.**
**Mirror template**: Sprint 57.41 plan (§ structure 0-9, 9 main sections; 4-day Day-numbering Day 0/1/2/2.5/3).

---

## 0. Sprint Goal

Single-domain sprint to **fully rebuild `/memory` from mockup `page-governance.jsx:462-598 MemoryPage` + `:600-656 TimeTravelScrubber`** (Memory Layers `.page-head` with time-travel actions + interactive 24h TimeTravelScrubber Card + 5×3 `memory-matrix` grid + bottom 2-col grid: Recent memory ops table left + GDPR right-to-erasure form right). Resolves the 2026-05-25 22-page drift audit's **#2 priority CATASTROPHIC** verdict on `/memory` (post Sprint 57.41 it became the highest-ROI remaining CATASTROPHIC, ~10-15 hr est per `AD-Memory-Layers-Matrix-Rebuild`). The outer 2-tab (`recent` / `by-scope`) Sprint 57.12 vintage is **dropped** per §1.4 because — unlike Sprint 57.40 `/governance` `audit-log` tab and Sprint 57.41 `/verification` `timeline` tab (distinct production-only concepts the mockup omits) — both `/memory` sub-tabs are **subsumed by the unified mockup matrix view** (Recent ops = bottom card; By-Scope = main matrix grid). No production-only operational concept survives the rebuild.

### Drift audit context

Per `claudedocs/5-status/drift-audit-2026-05-25/audit-report.md` row 13:

- **Mockup design** (`reference/design-mockups/page-governance.jsx:462-598`, ~137 lines incl. `<TimeTravelScrubber>` 600-656 ~57 lines = ~194 lines): `.page-head` (Memory Layers title + sub "Dual-axis · 5 scope × 3 time scale" + `/memory` route-pill + mono entry count + optional time-travel Badge + 3 actions Time travel/Return to now / Export / New entry) + `<TimeTravelScrubber>` Card (Replay 24h/Pause + Now + 24h slider with op markers + 6 time marks + cursor display) + `.memory-matrix` 5×3 grid with header row (4 cols × 6 rows) + bottom `.grid-main` 2-col (Recent memory ops Card 6-col table + GDPR right-to-erasure Card form).
- **Production reality** (`frontend/src/pages/memory/index.tsx` 73 lines + 3 components): only outer 2-tab `recent` / `by-scope` + `<MemoryRecentList />` (layer dropdown + paginated table) + `<MemoryByScopeBrowser />` (5-layer cards + drill-in detail). Sprint 57.12 vintage shadcn-utility. No matrix grid. No time-travel scrubber. No GDPR erasure form. No ops timeline strip.
- **Outer shell drop decision** (per §1.4): unlike Sprint 57.40-41, the production 2-tab structure here is fully redundant with the mockup unified view → drop the 2-tab + nested Routes; `/memory` becomes single `<MemoryView />`. Old `/memory/recent` + `/memory/by-scope` URLs redirected to `/memory` for backward compat.

---

## 1. Background

### 1.1 Why a strict-rebuild not a verbatim-css-repoint

The current `/memory` page is Sprint 57.12 vintage shadcn-utility — Sprint 57.33 only added defensive `?? []` guards (FIX-pre-existing-route-crashes) and Sprint 57.39+ never Phase-2 re-pointed `/memory`. The remaining drift is **fundamentally structural**:

- No 5×3 matrix grid (mockup `.memory-matrix` with `mm-cell` / `mm-header` / `mm-scope` / `mm-entry` / `count` classes)
- No 24h time-travel scrubber with op markers + cursor-aware entry visibility filtering
- No `.page-head` proper (production only renders `AppShellV2 pageTitle="Memory"` chrome)
- No bottom 2-col grid (Recent ops + GDPR erasure)
- No `<Badge tone="memory">` op-type indicators (WRITE/READ/EXPIRE)
- No "time-travel · Xm ago" / "Return to now" warning state

These cannot be added via a CSS swap — they require new React components with local state (cursor playback, hovered cell, playing flag). Hence `frontend-mockup-strict-rebuild` 0.60 class (8th application — same class as Sprint 57.23/57.24v2/57.25/57.27/57.37A/57.40/57.41).

### 1.2 What stays unchanged (preserved wiring)

| Layer | Preserved | Source |
|-------|-----------|--------|
| Auth gate | `<RequireAuth>` wrap | `frontend/src/pages/memory/index.tsx:53` (current) → new `MemoryPage` keeps wrap |
| Shell wrap | `<AppShellV2 pageTitle={t("nav.memory")}>` | same:54 → preserved with same page title |
| `useMemoryRecent` hook | Day 0 Prong 2 confirm (if exists from Sprint 57.12) — reused for `RecentMemoryOpsCard` real-data optional path | `frontend/src/features/memory/hooks/useMemoryRecent.ts` |
| `useMemoryByScope` hook | Day 0 Prong 2 confirm; reused if shape compatible OR deprecated if matrix entirely fixture | `frontend/src/features/memory/hooks/useMemoryByScope.ts` |
| `useMemoryByTime` hook | Day 0 Prong 2 confirm; mostly retired (matrix is by-scope×time but cursor-aware via local state) | `frontend/src/features/memory/hooks/useMemoryByTime.ts` |
| `memoryService` | Day 0 Prong 2 confirm; reused for `RecentMemoryOpsCard` if real-data path exists | `frontend/src/features/memory/services/memoryService.ts` |
| `types.ts` `MemoryEntry` / scope enum | Reused if shape compatible | `frontend/src/features/memory/types.ts` |

### 1.3 What changes (rebuild scope)

| Layer | Old | New (per mockup) |
|-------|-----|------------------|
| `/memory` route | outer 2-tab `recent` / `by-scope` + nested Routes | Single `<MemoryView />` (no nested routes) |
| `/memory/recent` URL | active Route → `<MemoryRecentList />` | **Redirected** to `/memory` (backward compat; backend bookmarks still resolve) |
| `/memory/by-scope` URL | active Route → `<MemoryByScopeBrowser />` | **Redirected** to `/memory` |
| Page intro | tab nav only (no header above tab) | `.page-head` (Memory Layers title + sub + route-pill + entries count + time-travel Badge cond + 3 actions: Time travel/Return / Export / New entry) |
| Time-travel control | none | `<TimeTravelScrubber>` Card (Replay 24h/Pause + Now + 24h slider with `MEMORY_OPS_TIMELINE` op markers + 6 `TIME_TRAVEL_MARKS` + cursor display "T-Xm" / relative time) |
| Matrix grid | none (separate Recent + By-Scope tabs) | `.memory-matrix` 5×3 grid (4 cols × 6 rows incl. header row): scope-label col + 3 time-scale cols (permanent TTL∞ / quarter TTL90d / day TTL24h); cells show up to 4 entries (k=v) + "+N more" overflow + entry count + cursor-aware visibility filter |
| Recent ops | embedded in `MemoryRecentList` paginated table | `<RecentMemoryOpsCard>` 6-col table (Op Badge / Scope mono / Key mono / Value subtle mono / By mono / When subtle); fixture 5 rows + AP-2 banner (deferred backend ops timeline endpoint) |
| GDPR erasure | none | `<GdprErasureCard>` form (Subject id input + Reason select [gdpr/ccpa/legal] + Issue tombstone danger button); fixture (AP-2 banner — deferred backend `/api/v1/memory/erasure` POST endpoint) |
| Pagination | Prev / Next footer in MemoryRecentList | **Retired** per Karpathy §3 — mockup shows "Live · last 100" subtitle (no pagination); admin-level pagination deferred to Phase 58+ |
| Layer dropdown | MemoryRecentList layer filter | **Retired** per Karpathy §3 — mockup matrix displays all 5 scopes simultaneously |

### 1.4 Outer 2-tab disposition decision (Day 0 final)

**Mockup** (`page-governance.jsx:462-598 MemoryPage`) shows ONE single view with no `recent` / `by-scope` sub-tabs. Production has outer 2-tab per Sprint 57.12 vintage. Two options:

- **Option A** (Sprint 57.40/57.41 precedent — outer 2-tab preservation): preserve outer 2-tab as-is; rebuild only `recent` slot. **Rejected** because — unlike `/governance/audit-log` (Sprint 57.40, distinct WORM Merkle chain page) or `/verification/timeline` (Sprint 57.41, distinct CorrectionTraceView session-scoped concept) — both `/memory/recent` and `/memory/by-scope` are SUBSETS of the mockup unified view (`recent` = bottom RecentMemoryOpsCard; `by-scope` = main MemoryMatrix grid). Preserving the 2-tab would introduce production-only chrome with no operational distinction.
- **Option B** (selected): drop outer 2-tab; `/memory` becomes single mockup-faithful view; old URLs `/memory/recent` + `/memory/by-scope` redirected to `/memory` for backward compat (bookmark / chat session links).

→ **Selected: B** (outer 2-tab dropped; URLs redirect). Reasoning: mockup unified view subsumes both tabs; no production-only operational concept survives; preserving tabs would be Potemkin Feature (AP-4 reference in `.claude/rules/anti-patterns-checklist.md`).

**Risk mitigation**: Day 2.5 sweep + Day 3 retro must verify `/memory/recent` + `/memory/by-scope` redirect cleanly (no 404 / blank). Sidebar nav link `/memory` (no sub-entries) confirmed in routes.config.ts.

### 1.5 Class baseline + calibration evaluation criteria

`frontend-mockup-strict-rebuild` 0.60 (8th application):

| Sprint | Page | Ratio | Notes |
|--------|------|-------|-------|
| 57.23 | auth flow rebuild (7 routes) | 0.59 | 1st app below band 0.26 |
| 57.24 v2 | cost-dashboard rebuild | 1.19 | 2nd app top of band |
| 57.25 | sla-dashboard rebuild | 0.88 | 3rd app in band |
| 57.27 | overview rebuild | ≈0.95 | 4th app in band |
| 57.37A | loop-debug rebuild | ≈1.18 | 5th app top of band |
| 57.40 | governance rebuild | ≈0.36 | 6th app deeply below band (agent-delegation 7th consecutive ~3-5× speedup) |
| 57.41 | verification rebuild | ≈0.18 | 7th app deepest below band (agent-delegation 8th+9th consecutive) |
| **57.42 (this)** | **memory matrix rebuild** | **TBD** | 8th app — single-domain, large-scope (6 NEW components + interactive TimeTravelScrubber + 5×3 matrix grid most complex of class history); 0 NEW Sprint 57.41 rename pattern-reuse (mockup-ui primitives reused but no header/strip rename — header structure differs significantly: time-travel cond Badge + 3 actions vs verification's 2 actions) |

**3-sprint window** (last 3: 57.37A ≈1.18 + 57.40 ≈0.36 + 57.41 ≈0.18): only 2 of 3 < 0.7 → **lower-trigger NOT yet met** (need 3 consecutive) → KEEP 0.60 baseline this iteration per `.claude/rules/sprint-workflow.md §When to adjust`.

**Cross-class agent-delegation signal**: `AD-Sprint-Plan-Agent-Delegation-Factor-Modifier` now has **4 data points across 2 classes** (57.39 -with-extras 0.41 + FIX-015 outlier + 57.40 mockup-strict-rebuild 0.36 + 57.41 mockup-strict-rebuild 0.18); **activation criteria technically MET** per `.claude/rules/sprint-workflow.md §Proposed Agent Delegation Factor Modifier` (3+ cross-class data points). Sprint 57.42 will be agent-delegated Day 1 (10th consecutive code-implementer) — Q4 + Q5 will document the 5th data point + propose **Sprint 57.43 retro structural evaluation** (Option A multiplicative `agent_factor` 0.55 coefficient OR Option B per-class sub-class split per `.claude/rules/sprint-workflow.md §Proposed Agent Delegation Factor Modifier`).

Evaluation thresholds for Sprint 57.42:

- **PASS**: ratio in [0.85, 1.20] → KEEP 0.60; class regresses toward 7-pt mean 0.76 lower edge
- **ABOVE band** (>1.20): 1 above-band among 8 pts; KEEP
- **BELOW band** (<0.85): if < 0.7, becomes **3rd consecutive below-band** (57.40 + 57.41 + 57.42) in 4-sprint window → `When to adjust` lower-trigger MET → Sprint 57.43 plan proposes 0.60 → 0.40-0.45 lift; ALSO 5th cross-class agent-delegation data point reinforces modifier proposal

### 1.6 Phase-2 epic progress impact

Pre-sprint:
- **Honest** Phase-2 status (post Sprint 57.41): 18 PARITY + 1 NEAR-PARITY + 3 🔴 CATASTROPHIC remaining (`/memory` + `/admin-tenants` + `/tenant-settings`).

Post-sprint (if Sprint 57.42 ships):
- **Phase-2: 19 PARITY + 1 NEAR-PARITY / 2 🔴 CATASTROPHIC remaining** (`/admin-tenants` + `/tenant-settings`).
- Drift audit 2026-05-25 #2 priority `/memory` CLOSED (was newly-elevated to #2 post Sprint 57.41).

---

## 2. User Stories

### Domain — `/memory` Memory Layers matrix view full rebuild

#### US-1 — `.page-head` mockup-aligned
As the operator, I want `/memory` to show a proper page header (`Memory Layers` title + sub-text `Dual-axis · 5 scope × 3 time scale` + `/memory` route-pill + mono `· 6,514 entries` count + optional `Badge tone="info" dot` "time-travel · Xm ago" cond when cursor < 0 + 3 outline buttons: `Time travel` (icon clock; variant outline when cursor=0, variant warning when cursor<0 with label "Return to now") + `Export` (icon download) + `New entry` (icon plus, variant primary)) matching mockup, so the page identity + time-travel state is clear.

#### US-2 — `<TimeTravelScrubber>` interactive 24h playback
As the operator, I want an interactive 24h time-travel scrubber Card showing:
- `Replay 24h` / `Pause` toggle button (variant outline → warning when playing; icon play/pause)
- `Now` ghost button (resets cursor to 0)
- 24h slider (range 0-100; maps to cursor -1440..0 min) with **op markers** behind: `MEMORY_OPS_TIMELINE` 12 ops (WRITE / READ / EXPIRE) shown as 2×8px colored vertical bars at relative time positions
- 6 `TIME_TRAVEL_MARKS` labels below slider (now / 5m ago / 30m ago / 2h ago / 6h ago / 1d ago)
- Right-side cursor display: mono "now" / "T-Xm" (warning color when cursor<0) + relative time mono subtle ("10:42:28" / "~10:37" / "~10h ago" / "yesterday")
- Auto-playback: every 200ms decrement cursor by 30 min; stop at -1440 (1d ago)

State: local `useState` cursor (number, default 0) + playing (bool); `useEffect` for setInterval auto-decrement; pass `cursor` + `onCursor` to MemoryMatrix for visibility filtering.

#### US-3 — `<MemoryMatrix>` 5×3 grid (most complex component)
As the operator, I want the central matrix grid (CSS `.memory-matrix`, 4 cols × 6 rows including header row) showing:
- **Header row**: empty corner cell + 3 `.mm-cell .mm-header` cells (one per time scale `permanent` / `quarter` / `day`) with: 6×6 colored dot (var(--memory) permanent / var(--info) quarter / var(--tool) day) + scale name + TTL subtitle ("TTL ∞" / "TTL 90d" / "TTL 24h")
- **5 scope rows** (one per `SCOPES` array entry: system / tenant / role / user / session):
  - `.mm-cell .mm-scope` label cell: scope name (large) + sub (small italic) + bottom row: memory icon 12px var(--memory) color + mono entry count (e.g. "84" / "1,280" / "312" / "4,820" / "18")
  - 3 entry-display cells: hover bg toggle + cursor-aware visibility filter (per cell key `${scope.id}|${t}`):
    - if `cursor < 0 && t === "day" && scope.id === "session"`: limit to `cursor > -10 ? entries.slice(0,1) : []` (session.day entries decay fast)
    - elif `cursor < -120 && t === "day"`: show empty (day entries vanish 2h+ ago)
    - else: show all
  - Display first 4 entries as `<div class="mm-entry">k = v</div>` lines + "+N more" overflow + `.count` footer "N entries" + cond "M hidden" warning when cursor<0 hides entries

Data source: fixture `MEMORY_ENTRIES` map (15 entries across 5×3 cells per mockup; per `page-governance.jsx:419-435`); **AP-2 banner** (deferred backend cursor-aware matrix query `/api/v1/memory/matrix?scope=*&time_scale=*&cursor=*` endpoint).

#### US-4 — `<RecentMemoryOpsCard>` 6-col ops table
As the operator, I want a Card "Recent memory ops" with subtitle "Live · last 100" + ghost button "View all" header action + 6-col table (Op Badge memory-tone WRITE/READ/EXPIRE / Scope mono / Key mono / Value subtle mono ellipsis 240px / By mono fg-muted / When subtle) showing 5 fixture rows per mockup (4 WRITE + 4 READ + 1 EXPIRE mix). Backed by **AP-2 fixture** (`BackendGapBanner` declares deferred backend ops timeline endpoint `/api/v1/memory/ops/recent?limit=100`); reuse `useMemoryRecent` hook **only if** Day 0 Prong 2 confirms its response shape maps to ops timeline schema (likely needs adapt or fixture-only this sprint).

#### US-5 — `<GdprErasureCard>` right-to-erasure form
As the operator, I want a Card "GDPR right-to-erasure" with form:
- Subtle subtitle: "Tombstone subject across all memory scopes. WORM audit retains hash chain."
- `<Field label="Subject id">` with mono input placeholder "u_..."
- `<Field label="Reason (audited)">` with select (defaultValue "gdpr"; options: GDPR Art. 17 erasure / CCPA opt-out / Legal hold release)
- `<Button variant="danger" size="sm" icon="warn">` "Issue tombstone"

Backed by **AP-2 fixture** (`BackendGapBanner` declares deferred backend `/api/v1/memory/erasure` POST endpoint; button non-functional in this sprint — toast or no-op). Carryover `AD-Memory-GDPR-Erasure-Backend-Endpoint`.

#### US-6 — 3 vintage components orphan delete (Karpathy §3)
As the developer, since mockup unified view subsumes both Recent + By-Scope tab content, orphan-delete the 3 Sprint 57.12 vintage components per Karpathy §3:
- `MemoryRecentList.tsx` (paginated table + layer dropdown — superseded by main MemoryMatrix + bottom RecentMemoryOpsCard)
- `MemoryByScopeBrowser.tsx` (5-layer cards + drill-in detail — superseded by main MemoryMatrix grid)
- `MemoryScopeBadge.tsx` (if Day 0 Prong 2.5 grep confirms 0 other consumers — likely orphan after Recent+ByScope delete)

Hooks disposition: Day 0 Prong 2 evaluation —
- `useMemoryRecent` — preserve if `RecentMemoryOpsCard` real-data path; deprecate if fixture-only
- `useMemoryByScope` — deprecate (matrix uses fixture or new `useMemoryMatrix` if backend ships)
- `useMemoryByTime` — deprecate (cursor-aware filter is local state)

Carryover ADs: `AD-Memory-Vintage-Hooks-Cleanup` (Phase 58+ remove dead hooks if matrix backend ships and supersedes them).

#### US-7 — Pattern reuse from Sprint 57.40-57.41 primitives
As the developer, transfer pattern from Sprint 57.40-57.41 PageHeader/StatsStrip via mockup-ui primitive reuse — but **no direct rename** this sprint because:
- Memory header structure differs (3 actions including conditional Time-travel/Return-to-now button + entries count mono span + conditional time-travel Badge) vs verification header (2 simple actions)
- Memory has NO 4-KPI strip (mockup matrix replaces KPI summary; bottom ops table is granular replacement)

`<Card>` / `<Badge>` / `<Button>` / `<Icon>` / `<Field>` / `<BackendGapBanner>` mockup-ui primitives all reused (post Sprint 57.40 promotion). NO NEW primitives needed (Day 0 Prong 2 confirm `<Field>` Select wrap export — may need lift if missing).

#### US-8 — Vitest baseline preserved (≥498/498)
After all sprint changes, Vitest must remain green at or above 498 baseline (Sprint 57.41 close). NEW specs allowed for new components (target +5-8 NEW specs covering MemoryMatrix cell rendering + cursor visibility filter + TimeTravelScrubber slider+playback + RecentMemoryOpsCard ops dispatch + GdprErasureCard form fields + MemoryPageHeader cond time-travel badge). Existing `memoryService.test.ts` preserved unchanged (service layer not touched).

#### US-9 — 22-route sweep clean + route-sweep mock fix
22-route Playwright sweep `before` vs `after`: only `/memory` expected CHANGED (rebuild). Other 21 routes IDENTICAL. **D-DAY0-1 fix candidate**: confirm `/memory/recent` + `/memory/by-scope` route-sweep entries are dropped (per Option B 2-tab drop) OR redirect cleanly to `/memory` (preserving sweep coverage of old URLs). Also confirm `/api/v1/memory/*` endpoint mocks in route-sweep.mjs return envelope-shape `{items: [], total: 0, has_more: false}` (3rd application of `AD-RouteSweep-Envelope-Mock-Convention` post Sprint 57.40 governance + Sprint 57.41 verification).

#### US-10 — mockup-fidelity guard + HEX_OKLCH_BASELINE bump
`node frontend/scripts/check-mockup-fidelity.mjs` exit 0; baseline may bump +3-8 from 46:
- Matrix dot palette (`var(--memory)` / `var(--info)` / `var(--tool)`) for time-scale headers
- Op markers palette (`var(--memory)` / `var(--info)` / `var(--warning)`) — 12 ops
- mm-entry / mm-cell / mm-scope hover bg `var(--bg-2)`
- cursor warning color (`var(--warning)` cond)
- GDPR danger button + select (existing tones — no new bumps expected)
- KvRow / RiskBadge unused this sprint

Target ≤54 (set `check-mockup-fidelity.mjs` `HEX_OKLCH_BASELINE` to 54 max).

#### US-11 — Audit report verdict update
After sprint, update `claudedocs/5-status/drift-audit-2026-05-25/audit-report.md` to mark `/memory` verdict ✅ **PARITY** post-rebuild; carryover list shrinks 3 → 2 🔴 CATASTROPHIC.

---

## 3. Technical Specifications

### 3.1 Component refactor map

```
frontend/src/pages/memory/index.tsx (73 lines → ~30 lines NEW): RequireAuth + AppShellV2 + DROP 2-tab nav + DROP nested Routes
  └─ <MemoryView /> (single route mount; no nested Routes)
       ↓
       frontend/src/features/memory/components/MemoryView.tsx (NEW ~75 lines)
        ├─ const [cursor, setCursor] = useState(0)
        ├─ const [playing, setPlaying] = useState(false)
        ├─ const [hovered, setHovered] = useState<string | null>(null)
        ├─ <MemoryPageHeader cursor={cursor} onResetCursor={() => setCursor(0)} entriesTotal={...} />
        ├─ <TimeTravelScrubber cursor={cursor} onCursor={setCursor} playing={playing} onPlay={() => setPlaying(p => !p)} />
        ├─ <MemoryMatrix cursor={cursor} hovered={hovered} onHover={setHovered} />
        ├─ <div className="grid-main"> — 2-col grid
        │    ├─ <RecentMemoryOpsCard />
        │    └─ <GdprErasureCard />
        └─ {/* no detail pane / no modal — mockup has none */}

PLUS backward-compat redirects in App.tsx or pages/memory/index.tsx:
  /memory/recent → <Navigate to="/memory" replace />
  /memory/by-scope → <Navigate to="/memory" replace />
```

### 3.2 NEW components inventory

| Component | File | Lines (est) | Purpose |
|-----------|------|-------------|---------|
| `MemoryPageHeader` | `features/memory/components/MemoryPageHeader.tsx` | ~55 | mockup `.page-head` + conditional time-travel Badge + 3 actions (Time travel/Return + Export + New entry) |
| `TimeTravelScrubber` | `features/memory/components/TimeTravelScrubber.tsx` | ~95 | Card wrap + Replay/Pause + Now + 24h slider with op markers + 6 time marks + cursor display; interactive `useState` + `useEffect` setInterval auto-playback |
| `MemoryMatrix` | `features/memory/components/MemoryMatrix.tsx` | ~120 | `.memory-matrix` 4×6 grid (1 header row + 5 scope rows × 4 cols); cell rendering + cursor-aware visibility filter + hover bg + entry overflow "+N more" |
| `RecentMemoryOpsCard` | `features/memory/components/RecentMemoryOpsCard.tsx` | ~70 | Card "Recent memory ops" + "Live · last 100" subtitle + 6-col table fixture rows + AP-2 banner |
| `GdprErasureCard` | `features/memory/components/GdprErasureCard.tsx` | ~55 | Card "GDPR right-to-erasure" + form (Subject id + Reason select + Issue tombstone danger button) + AP-2 banner |
| `MemoryView` | `features/memory/components/MemoryView.tsx` | ~75 | container assembling the 5 above; owns cursor + playing + hovered local state |

### 3.3 DELETED / RETIRED components

| Component | File | Disposition |
|-----------|------|-------------|
| `MemoryRecentList` | `features/memory/components/MemoryRecentList.tsx` | **ORPHAN DELETE per Karpathy §3** — paginated table + layer dropdown superseded by mockup unified view (matrix grid + bottom RecentMemoryOpsCard) |
| `MemoryByScopeBrowser` | `features/memory/components/MemoryByScopeBrowser.tsx` | **ORPHAN DELETE per Karpathy §3** — 5-layer cards + drill-in detail superseded by mockup MemoryMatrix grid (5 scopes in one view) |
| `MemoryScopeBadge` | `features/memory/components/MemoryScopeBadge.tsx` | Day 0 Prong 2.5 grep `grep -rn "MemoryScopeBadge" frontend/src` → if 0 consumers outside the 2 deleted parents = **ORPHAN DELETE**; if other consumers, keep + document |
| `useMemoryByScope` | `features/memory/hooks/useMemoryByScope.ts` | **DEPRECATED** — matrix uses fixture this sprint; backend cursor-aware query carryover Phase 58+; delete now (no consumers post Rebuild) OR keep as graveyard with TODO until Phase 58+ ships supersession |
| `useMemoryByTime` | `features/memory/hooks/useMemoryByTime.ts` | Same as above; cursor is local state — backend time-axis query carryover |
| `useMemoryRecent` | `features/memory/hooks/useMemoryRecent.ts` | **CONDITIONAL** — preserve if `RecentMemoryOpsCard` wires real-data via memoryService (Day 0 Prong 2 verify hook + service shape compatibility); deprecate if fixture-only |

### 3.4 mockup-ui primitives used

Per `frontend/src/components/mockup-ui.tsx` (post Sprint 57.40 + 57.41 promotions):

- `<Card>` — reused (3 cards: TimeTravelScrubber Card + RecentMemoryOpsCard + GdprErasureCard)
- `<Badge>` — reused (`tone="info" dot` for time-travel state / `tone="memory"` for op-type WRITE/READ/EXPIRE)
- `<Button>` — reused (variant outline/warning/primary/danger/ghost; multiple use)
- `<Icon>` — reused (clock / download / plus / play / pause / memory / warn) — confirm Day 0 Prong 2 `Icon` size prop usage + memory/warn name presence
- `<Field>` — confirm Day 0 Prong 2 `Field` export exists in mockup-ui.tsx (was promoted Sprint 57.34 per `frontend-mockup-fidelity-audit` epic); **lift candidate** if missing (verbatim port from `page-governance.jsx` Field usage)
- `<BackendGapBanner>` — reused (AP-2 declarations on MemoryMatrix data + RecentMemoryOpsCard ops timeline + GdprErasureCard erasure endpoint = 3 AP-2 banners minimum)

NO NEW primitives expected (mockup-ui.tsx already has Field per Sprint 57.34; Day 0 Prong 2 final confirm).

### 3.5 D-DAY0-1: route-sweep mock candidate

`frontend/scripts/route-sweep.mjs` candidate adds (Day 0 Prong 1 confirm + Day 2 §2.3 task):

```js
// Drop /memory/recent + /memory/by-scope from route list (2-tab dropped per §1.4 Option B)
// OR keep with redirect-aware sweep capture

// Add /memory backend gap mocks (3rd application of AD-RouteSweep-Envelope-Mock-Convention)
if (/\/memory\/ops\/recent/.test(url)) {
  return json({ items: [], total: 0, has_more: false });
}
if (/\/memory\/matrix/.test(url)) {
  return json({ entries: {}, scopes_total: 0 });
}
```

Document MHist entry + carryover `AD-RouteSweep-Envelope-Mock-Convention` deepens (3rd occurrence after Sprint 57.40 governance + Sprint 57.41 verification).

### 3.6 HEX_OKLCH_BASELINE envelope

Current baseline 46 (post Sprint 57.41 ship; Sprint 57.41 plan projected ≤50 but actual remained 46 — likely under-estimate occurred or oklch already covered most). Sprint 57.42 bump estimate:

- Time-scale dot palette (`var(--memory)` / `var(--info)` / `var(--tool)`): +0 (already var-based; var refs)
- Op markers behind slider (12 ops × 3 colors): +0 (var-based)
- mm-cell hover bg `var(--bg-2)` cond: +0
- cursor warning color `var(--warning)` cond: +0
- New literal oklch matrix grid 1px borders / inset shadows IF mockup CSS uses literal hex: +0-2 (most go through var)
- Inline `style=` literal hex in mockup-direct port (e.g. `width: 6, height: 6, borderRadius: "50%"`): +0 (no color literal)
- Op marker color decision inline (e.g. `op.op === "WRITE" ? "var(--memory)" : ...`): +0 (var refs)

Total expected: **+0-4** → target ≤50 (set `check-mockup-fidelity.mjs` `HEX_OKLCH_BASELINE` to 50 max; likely 46-48 actual). Day 2.5 measure + set; if >54 unexpected, document as drift D-DAY2-X for color consolidation.

### 3.7 MemoryMatrix cursor-aware visibility filter logic

Per mockup `page-governance.jsx:528-532`:

```ts
const visible = cursor < 0 && t === "day" && scope.id === "session"
  ? (cursor > -10 ? entries.slice(0, 1) : [])  // session.day decays within 10 min
  : cursor < -120 && t === "day"
    ? []                                       // day entries vanish 2h+ ago
    : entries;                                 // permanent + quarter unchanged by cursor
```

This is fixture-side time-travel simulation (no backend cursor query yet). Document as `AD-Memory-Cursor-Filter-Backend-Migration` — Phase 58+ backend ships cursor-aware matrix query and this client-side filter is replaced by query param.

### 3.8 Fixture data verbatim port

Per mockup `page-governance.jsx:410-460`, port verbatim into `MemoryMatrix.tsx` (or shared `_fixtures.ts` if multiple components consume):

- `SCOPES` const (5 entries with id/name/sub/count)
- `TIME_SCALES` const (3 strings)
- `MEMORY_ENTRIES` map (15 cells × ≤4 entries each = ~30 total {k, v} pairs)
- `TIME_TRAVEL_MARKS` const (6 entries)
- `MEMORY_OPS_TIMELINE` const (12 ops)

Plus `RECENT_MEMORY_OPS` const for `RecentMemoryOpsCard` (5 rows hand-ported from mockup `page-governance.jsx:561-566`).

Verbatim port maintains AP-Phase2-A/B/C anti-pattern compliance (no STYLE.md §3 inline-style violations; rely on mockup CSS `.mm-cell` / `.mm-entry` / `.count` classes from `styles-mockup.css`).

---

## 4. File Change List

### NEW files (6 components + 5-8 specs)

- `frontend/src/features/memory/components/MemoryPageHeader.tsx` — ~55 lines
- `frontend/src/features/memory/components/TimeTravelScrubber.tsx` — ~95 lines
- `frontend/src/features/memory/components/MemoryMatrix.tsx` — ~120 lines
- `frontend/src/features/memory/components/RecentMemoryOpsCard.tsx` — ~70 lines
- `frontend/src/features/memory/components/GdprErasureCard.tsx` — ~55 lines
- `frontend/src/features/memory/components/MemoryView.tsx` — ~75 lines
- `frontend/src/features/memory/_fixtures.ts` — ~80 lines (verbatim SCOPES / TIME_SCALES / MEMORY_ENTRIES / TIME_TRAVEL_MARKS / MEMORY_OPS_TIMELINE / RECENT_MEMORY_OPS const)
- `frontend/tests/unit/memory/MemoryPageHeader.test.tsx` — +1-2 specs (cond time-travel Badge)
- `frontend/tests/unit/memory/TimeTravelScrubber.test.tsx` — +2 specs (slider value mapping + play/pause toggle state)
- `frontend/tests/unit/memory/MemoryMatrix.test.tsx` — +2-3 specs (5×3 grid render + cursor-aware visibility filter cases + entry overflow "+N more")
- `frontend/tests/unit/memory/RecentMemoryOpsCard.test.tsx` — +1 spec (op Badge tone dispatch + AP-2 banner)
- `frontend/tests/unit/memory/GdprErasureCard.test.tsx` — +1 spec (form fields render + AP-2 banner)

### MODIFIED files

- `frontend/src/pages/memory/index.tsx` — drop 2-tab nav + nested Routes; replace with single `<MemoryView />` mount; preserve RequireAuth + AppShellV2; ~73 → ~30 lines
- `frontend/src/App.tsx` (or routes.config.ts) — add backward-compat redirects `/memory/recent` → `/memory` + `/memory/by-scope` → `/memory` (Day 0 Prong 1 confirm exact file path)
- `frontend/scripts/route-sweep.mjs` — D-DAY0-1: drop `/memory/recent` + `/memory/by-scope` route entries OR replace with redirect-aware capture; add `/api/v1/memory/{ops/recent,matrix}` envelope mocks (3rd application AD-RouteSweep-Envelope-Mock-Convention); re-point `OUT_DIR` to `sprint-57-42-memory-matrix-rebuild`
- `frontend/scripts/check-mockup-fidelity.mjs` — `HEX_OKLCH_BASELINE` 46 → ≤50 (set actual on Day 2 close)
- `claudedocs/5-status/drift-audit-2026-05-25/audit-report.md` — Day 3 closeout: mark `/memory` verdict ✅ PARITY post-rebuild; carryover list 3 → 2

### DELETED files

- `frontend/src/features/memory/components/MemoryRecentList.tsx` — orphan delete per Karpathy §3 (paginated table + layer dropdown superseded by MemoryMatrix + RecentMemoryOpsCard)
- `frontend/src/features/memory/components/MemoryByScopeBrowser.tsx` — orphan delete per Karpathy §3 (5-layer cards + drill-in detail superseded by MemoryMatrix grid)
- `frontend/src/features/memory/components/MemoryScopeBadge.tsx` — **conditional** orphan delete (Day 0 Prong 2.5 grep confirm 0 other consumers post the 2 parent deletes)
- `frontend/src/features/memory/hooks/useMemoryByScope.ts` — **conditional** deprecate / delete (Day 0 Prong 2 verify no other consumers; if 0, delete)
- `frontend/src/features/memory/hooks/useMemoryByTime.ts` — **conditional** deprecate / delete (Day 0 Prong 2 verify)
- `frontend/tests/e2e/memory/memory-page.spec.ts` — adapt or delete (tab-flow tests obsolete; replace with mockup-shape view assertions if time permits — best-effort Day 2)

### Cross-domain

- `memory/project_phase57_42_memory_matrix_rebuild.md` — sprint subfile
- `memory/MEMORY.md` — quality pointer (~300 char)
- Sprint plan + checklist + progress.md + retrospective.md (this file + checklist + execution files)
- `.claude/rules/sprint-workflow.md` — §Scope-class multiplier matrix `frontend-mockup-strict-rebuild` row: append Sprint 57.42 as 8th data point + agent-delegation modifier 5th cross-class point note + (if ratio < 0.7) flag Sprint 57.43 retro structural evaluation
- `claudedocs/1-planning/next-phase-candidates.md` — mark Sprint 57.42 rebuild complete; carryover list 3 → 2 🔴 CATASTROPHIC; add ~4-6 NEW carryover ADs

---

## 5. Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| AC1 | `/memory` visual matches mockup `page-governance.jsx:462-598` + `:600-656` (TimeTravelScrubber) | Day 2.5 fidelity verdict ✅ PARITY (worst-case 🟡 NEAR-PARITY with minor cosmetic notes) |
| AC2 | `.page-head` shows "Memory Layers" title + sub "Dual-axis · 5 scope × 3 time scale" + route-pill + entries count + 3 actions | Day 2.5 PNG visual |
| AC3 | TimeTravelScrubber Card with Replay 24h/Pause + Now + 24h slider with op markers + 6 marks + cursor display | Same |
| AC4 | TimeTravelScrubber interactive: cursor decrements 30 min / 200 ms when playing; stops at -1440 | Vitest spec |
| AC5 | `.memory-matrix` 5×3 grid (4 cols × 6 rows with header row); 5 SCOPE rows × 3 TIME_SCALES + scope-label col | Same |
| AC6 | MemoryMatrix cursor-aware visibility filter: session.day decays within 10 min; day entries vanish 2h+ ago | Vitest spec |
| AC7 | mm-cell hover bg toggle var(--bg-2) | Vitest spec |
| AC8 | Bottom 2-col `.grid-main`: RecentMemoryOpsCard left + GdprErasureCard right | PNG |
| AC9 | RecentMemoryOpsCard 6-col table (Op Badge memory-tone / Scope mono / Key mono / Value subtle / By mono / When subtle) | Vitest spec + PNG |
| AC10 | GdprErasureCard form (Subject id input + Reason select + Issue tombstone danger button) | Vitest spec + PNG |
| AC11 | 3 AP-2 BackendGapBanner declarations (MemoryMatrix matrix query + RecentMemoryOpsCard ops timeline + GdprErasureCard erasure endpoint) | Vitest spec |
| AC12 | MemoryRecentList + MemoryByScopeBrowser orphan-deleted; no import sites remaining | grep returns 0 |
| AC13 | MemoryScopeBadge orphan delete confirmed (or kept + documented if other consumers exist) | Day 0 Prong 2.5 + Day 2 final check |
| AC14 | route-sweep `/memory/recent` + `/memory/by-scope` redirect cleanly (no 404 / blank) | Day 2.5 sweep + diff |
| AC15 | Outer 2-tab dropped in `pages/memory/index.tsx`; single `<MemoryView />` mount | grep diff |
| AC16 | Vitest ≥498/498 (+5-8 NEW specs allowed) | `npm test -- --reporter=dot` last line |
| AC17 | 22-route sweep: only `/memory` CHANGED; 21 IDENTICAL | progress.md Day 2.5 entry |
| AC18 | mockup-fidelity guard exit 0 (HEX_OKLCH_BASELINE ≤50) | `node frontend/scripts/check-mockup-fidelity.mjs` exit 0 |
| AC19 | Per-domain calibration ratio recorded in retrospective.md §Q2 | 8th data point + matrix update note |
| AC20 | Drift audit report `/memory` ✅ PARITY post-rebuild | `claudedocs/5-status/drift-audit-2026-05-25/audit-report.md` edited |
| AC21 | Agent-delegation factor modifier 5th cross-class data point logged | retrospective.md Q4 + Q5 propose Sprint 57.43 retro structural evaluation |

---

## 6. Deliverables

- [ ] `MemoryPageHeader` + `TimeTravelScrubber` + `MemoryMatrix` + `RecentMemoryOpsCard` + `GdprErasureCard` + `MemoryView` components shipped
- [ ] `_fixtures.ts` verbatim port (SCOPES / TIME_SCALES / MEMORY_ENTRIES / TIME_TRAVEL_MARKS / MEMORY_OPS_TIMELINE / RECENT_MEMORY_OPS)
- [ ] `pages/memory/index.tsx` 2-tab drop + single `<MemoryView />` mount
- [ ] App.tsx (or routes.config.ts) backward-compat redirects `/memory/recent` + `/memory/by-scope` → `/memory`
- [ ] `MemoryRecentList.tsx` + `MemoryByScopeBrowser.tsx` orphan-deleted per Karpathy §3
- [ ] `MemoryScopeBadge.tsx` orphan delete confirmed (or kept + documented)
- [ ] Vintage hooks (`useMemoryByScope` / `useMemoryByTime`) deprecated / deleted per Day 0 Prong 2 verdict
- [ ] route-sweep.mjs D-DAY0-1 fix applied + OUT_DIR re-pointed
- [ ] 22-route sweep before/after diff reviewed; verdict logged
- [ ] retrospective.md Q1-Q7 with calibration ratio computed (8th data point + 5th cross-class agent-delegation data point)
- [ ] `.claude/rules/sprint-workflow.md` §matrix `frontend-mockup-strict-rebuild` row updated
- [ ] Memory subfile + MEMORY.md pointer entry per Sprint Closeout Update Policy
- [ ] PR opened against main; CI green; squash-merge ready
- [ ] Drift audit report `/memory` verdict updated ✅ PARITY

---

## 7. Risks & Mitigations

| Risk | Class | Mitigation |
|------|-------|-----------|
| `useMemoryRecent` response shape doesn't map to RecentMemoryOpsCard ops timeline schema | Data model gap | Day 0 Prong 2 grep `types.ts` + service shape; if mismatch, RecentMemoryOpsCard uses fixture-only this sprint + AP-2 banner declares hook-shape evolution Phase 58+; carryover AD-Memory-Ops-Timeline-Backend-Endpoint |
| TimeTravelScrubber 200ms setInterval auto-playback memory leak on unmount | Component lifecycle | `useEffect` return cleanup `clearInterval(id)`; Vitest spec covers cleanup on unmount |
| MemoryMatrix cursor-aware visibility filter complexity → Vitest brittleness | Spec fragility | Vitest cases: cursor=0 shows all / cursor=-5 day.session shows 1 entry / cursor=-15 day.session shows 0 / cursor=-130 day.* all shows 0; assert visible-count not class names |
| Outer 2-tab drop breaks bookmarks / chat session links to `/memory/recent` / `/memory/by-scope` | Routing regression | Day 0 Prong 1 confirm redirect paths in App.tsx (or routes.config.ts); manual click test `/memory/recent` → `/memory` in Day 2.5; carryover AD-Memory-Old-URL-Redirect-Phase58-Retire (if Phase 58+ wants to deprecate redirects) |
| MemoryScopeBadge has consumers outside the 2 parents → unsafe orphan delete | Cross-feature coupling | Day 0 Prong 2.5 grep `grep -rn "MemoryScopeBadge" frontend/src` → if non-zero in unrelated files, keep + document; if 0, delete |
| Vintage hooks (`useMemoryByScope` / `useMemoryByTime`) have consumers elsewhere | Hook coupling | Day 0 Prong 2 grep `grep -rn "useMemoryByScope\|useMemoryByTime" frontend/src` → 0 outside the 2 parents = delete; non-zero = deprecate with TODO carryover |
| `MEMORY_ENTRIES` cell rendering exceeds 4 lines → mockup "+N more" overflow logic mis-handled | Component logic | Vitest spec: cell with 6 entries renders 4 + "+2 more" + total count "6 entries"; cursor<0 hides M shows N variant |
| HEX_OKLCH_BASELINE bump exceeds +8 envelope | Mockup-fidelity guard | Update guard threshold to actual count; bump >8 = signal for color consolidation (carryover AD candidate) |
| Day 0 Prong 1/2 path drift → plan §Technical Spec inaccurate | Plan-vs-repo drift (Sprint 53.7 D4-D12 class) | Drift catalogue + plan §1.x amend in progress.md; scope confirm with user before Day 1 |
| Risk Class A: paths-filter vs `required_status_checks` | CI infra (recurring) | Touch `.github/workflows/backend-ci.yml` header comment if backend-ci skips on frontend-only PR |
| Single-domain agent-delegation budget overruns (10th consecutive code-implementer) | Agent-delegation scope | Day 1 = 6 components + fixtures + page restructure (1 agent invocation OR 2 invocations split: components first then page/redirects); Day 2 = specs + route-sweep + orphan delete |
| Per AD-Plan-5 Prong 2.5: child-component-tree depth audit | Child tree drift | Day 0 enumerate `features/memory/components/*` + grep shadcn-utility residue (AP-Phase2-C `bg-card` / `text-foreground` etc.) on `MemoryRecentList` + `MemoryByScopeBrowser` + `MemoryScopeBadge` — these are scheduled for delete, but if any rev re-pointing during rebuild reveals residue patterns, document. Children of NEW components must be 0 AP-Phase2-A/B/C from inception. |
| Agent-delegation 5th cross-class data point < 0.7 (3rd consecutive in 4-sprint window 57.40+57.41+57.42) → modifier activation trigger MET + class-level baseline lower-trigger MET | Calibration drift | Document ratio honestly in retrospective.md Q2; if < 0.7, propose Sprint 57.43 retro evaluation of BOTH `AD-Sprint-Plan-Agent-Delegation-Factor-Modifier` (Option A coefficient = 0.55 OR Option B per-class split) AND `frontend-mockup-strict-rebuild` baseline 0.60 → 0.40-0.45 lift |

---

## 8. Workload

**Bottom-up est** ~13 hr → **calibrated commit ~8 hr** (multiplier 0.60 per `frontend-mockup-strict-rebuild` 8th app baseline; 3-sprint window lower-trigger NOT yet met — 2 of last 3 < 0.7)

Bottom-up breakdown:

| Day | Tasks | Est (hr) |
|-----|-------|----------|
| Day 0 | 3-prong grep + drift catalog + plan amend | 1.0 |
| Day 1 | 6 NEW components (PageHeader 0.5 + TimeTravelScrubber 1.5 interactive + MemoryMatrix 2.5 most complex + RecentMemoryOpsCard 1.0 + GdprErasureCard 1.0 + MemoryView 1.0) + `_fixtures.ts` 0.5 + page restructure + redirects 0.5 | 8.5 |
| Day 2 | Vitest specs (5-8 NEW) + route-sweep mock + orphan delete x3-5 (components + hooks per Day 0 verdict) + e2e adapt | 3.0 |
| Day 2.5 | Fidelity PNG + 22-route sweep + redirect spot-check + HEX_OKLCH baseline assert | 1.0 |
| Day 3 | Retro + memory + audit-report + CLAUDE.md + next-phase-candidates + PR | 1.5 |

Sprint-aggregate: **~15 hr bottom-up** → 0.60 × = **~9 hr committed**. Within AD-Memory-Layers-Matrix-Rebuild estimate ~10-15 hr.

**Note**: If agent-delegation Day 1 + Day 2 achieves typical ~3-5× speedup vs human-rewrite estimates (per Sprint 57.39+57.40+57.41 evidence), actual may land ~5-7 hr (ratio ~0.55-0.78) → if so, this becomes a key 5th cross-class data point for `AD-Sprint-Plan-Agent-Delegation-Factor-Modifier` proposal.

---

## 9. Carryover candidates (Phase 58+)

Logged in retrospective.md §Q5 + `claudedocs/1-planning/next-phase-candidates.md`:

- `AD-Memory-Matrix-Backend-Cursor-Aware-Endpoint` — Backend `/api/v1/memory/matrix?scope=*&time_scale=*&cursor=*` endpoint required for real cursor-aware time-travel data. Sprint 57.42 uses fixture + client-side filter simulation. Phase 58+ ships backend.
- `AD-Memory-Ops-Timeline-Backend-Endpoint` — Backend `/api/v1/memory/ops/recent?limit=100` endpoint for RecentMemoryOpsCard. Sprint 57.42 fixture-only. Phase 58+ wires real.
- `AD-Memory-GDPR-Erasure-Backend-Endpoint` — Backend `/api/v1/memory/erasure` POST endpoint for GdprErasureCard form submission (audit chain WORM record). Sprint 57.42 form is non-functional (UI-only).
- `AD-Memory-Vintage-Hooks-Cleanup` — Phase 58+ remove deprecated `useMemoryByScope` / `useMemoryByTime` (and `useMemoryRecent` if RecentMemoryOpsCard backed by fixture-only) once supersession backend ships per above 3 ADs.
- `AD-Memory-Old-URL-Redirect-Phase58-Retire` — Sprint 57.42 keeps `/memory/recent` + `/memory/by-scope` → `/memory` redirects for backward compat. Phase 58+ analytics-based retire once bookmark traffic decays.
- `AD-Memory-New-Entry-Modal-Phase58` — Mockup `.page-head` "New entry" button is Sprint 57.42 AP-2 stub. Phase 58+ wires write modal (scope-aware key/value/ttl form + backend POST /api/v1/memory/{scope}/entries).
- `AD-Sprint-Plan-Agent-Delegation-Factor-Modifier` (carryover from Sprint 57.39 + 57.40 + 57.41) — Sprint 57.42 contributes 5th cross-class data point; **activation criteria fully MET**. If Sprint 57.42 ratio also < 0.7, propose Sprint 57.43 retro **structural decision** per `.claude/rules/sprint-workflow.md §Proposed Agent Delegation Factor Modifier` (Option A multiplicative `agent_factor` 0.55 OR Option B per-class sub-class split).
- `AD-Sprint-Plan-frontend-mockup-strict-rebuild-baseline-lift-trigger` (NEW conditional carryover) — IF Sprint 57.42 ratio also < 0.7 → 3rd consecutive below-band in 4-sprint window (57.40 + 57.41 + 57.42) → `When to adjust` lower-trigger MET → propose Sprint 57.43 plan lifts baseline 0.60 → 0.40-0.45.

---

**Last Updated**: 2026-05-25 (Day 0)

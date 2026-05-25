# Sprint 57.41 — AD-Verification-Catastrophic-Rebuild

**Phase**: 57 (Frontend SaaS)
**Sprint id**: 57.41
**Drafted**: 2026-05-25 (Day 0)
**Branch**: `feature/sprint-57-41-verification-full-rebuild`
**Class**: `frontend-mockup-strict-rebuild` (7th data point; 6-pt mean 0.86 at lower band edge — last 3 ratios 57.27≈0.95 + 57.37A≈1.18 + 57.40≈0.36 → only 1 < 0.7 in 3-sprint window → lower-trigger NOT met → KEEP 0.60 per `.claude/rules/sprint-workflow.md` §When to adjust rule).
**Mirror template**: Sprint 57.40 plan (§ structure 0-9, 9 main sections; 4-day Day-numbering Day 0/1/2/2.5/3).

---

## 0. Sprint Goal

Single-domain sprint to **fully rebuild `/verification` (the `recent` tab content) from mockup `page-extras.jsx:817-926 VerificationPage`** (Verification header + 4-KPI strip + 2-col grid with Recent verification runs table left + Failure kinds & Flaky checks sidebar right). Resolves the 2026-05-25 22-page drift audit's **#2 priority CATASTROPHIC** verdict on `/verification`. Existing `useVerificationRecent` TanStack Query wiring + service layer preserved; `VerificationList.tsx` filter form retired per Karpathy §3 (mockup has no filter form — only an "All kinds" outline header button as AP-2 stub).

### Drift audit context

Per `claudedocs/5-status/drift-audit-2026-05-25/audit-report.md` row 16:

- **Mockup design** (`reference/design-mockups/page-extras.jsx:817-926`, ~110 lines): `.page-head` (Verification title + sub + route-pill + All kinds / Export actions) + `.grid-stats` 4 KPI (Pass rate · 1h / Claims · 1h / Failed · 1h / Median latency) + 2-col `.grid-main` (Recent verification runs 6-col table left + Failure kinds card + Flaky checks card stacked right).
- **Production reality** (`frontend/src/features/verification/components/VerificationList.tsx` 299 lines): only filter form (3 fields Session ID / Verifier Type / Passed + Apply/Reset buttons) + paginated 6-col table + "No entries match" empty state + Prev/Next pagination footer.
- **Outer shell unchanged** (`frontend/src/pages/verification/index.tsx`): `RequireAuth` + `AppShellV2 pageTitle="Verification"` + outer 2-tab (`recent` / `timeline`) — per §1.4 outer-shell preservation decision (mirrors Sprint 57.40 outer 2-tab preservation precedent).

---

## 1. Background

### 1.1 Why a strict-rebuild not a verbatim-css-repoint

Sprint 57.39 Domain B already did the verbatim CSS swap on `/verification/recent` (tab-shell tokens / shadcn residue removed via FIX-015). The token surface is already mockup-aligned. The remaining drift is **structural** — the production `VerificationList` does not have:

- 4-KPI strip
- 2-col `.grid-main` layout (currently single column under tab shell)
- Recent verification runs table mockup shape (6-col with claim+evidence dual-line cells + agent mono + Kind badge + colored score + when subtle)
- Failure kinds sidebar card (5-row with bar-track + dot indicators)
- Flaky checks sidebar card (3-row with rate badge)

These cannot be added via a CSS swap — they require new React components. Hence `frontend-mockup-strict-rebuild` 0.60 class.

### 1.2 What stays unchanged (preserved wiring)

| Layer | Preserved | Source |
|-------|-----------|--------|
| Auth gate | `<RequireAuth>` wrap | `frontend/src/pages/verification/index.tsx:60` |
| Shell wrap | `<AppShellV2 pageTitle={t("nav.verification")}>` | same:61 |
| Outer 2-tab routing | `<Tabs items=[recent, timeline]>` + `<Routes>` nested | same:62-76 |
| `/verification/timeline` mount | `<CorrectionTraceView />` unchanged | same:74 |
| `useVerificationRecent` TanStack Query | `queryKey + 30s refetchInterval` (if applicable) | `features/verification/hooks/useVerificationRecent.ts` |
| `verificationService.listRecent` | `fetchWithAuth` JWT injection | `features/verification/services/verificationService.ts` (if exists) |
| `VerifierTypeBadge` | reused in NEW table row | `features/verification/components/VerifierTypeBadge.tsx` |
| `CorrectionTraceView` | unchanged (separate tab `/verification/timeline`) | same |
| `VerificationPanel` | inline chat-v2 panel — out of scope | `features/verification/components/VerificationPanel.tsx` |
| Backend `/verifications/recent` endpoint | no change | `backend/src/api/v1/verification/router.py` (presumed; confirm Day 0) |
| `types.ts` `VerificationLogFilter` / `VerifierType` | reused for query filter shape | `features/verification/types.ts` |

### 1.3 What changes (rebuild scope)

| Layer | Old | New (per mockup) |
|-------|-----|------------------|
| `/verification/recent` content | `<VerificationList />` (filter form + paginated table) | `<VerificationView />` (4-KPI + 2-col Recent runs table + Failure kinds & Flaky checks sidebar) |
| Filter form | 3 fields + Apply / Reset / Prev / Next pagination | **Retired** per Karpathy §3 — mockup has no filter form. "All kinds" mockup header button = AP-2 stub (kind-filter dropdown deferred to Phase 58+ per carryover `AD-Verification-All-Kinds-Filter-Dropdown`) |
| Page intro | tab-only (no header above tab) | `.page-head` proper (Verification title + sub + route-pill + All kinds / Export actions) |
| KPI | none | `.grid-stats` 4 cards: Pass rate · 1h (computed from `items.filter(ok).length / total`) / Claims · 1h (fixture + AP-2 banner) / Failed · 1h (fixture + AP-2) / Median latency (fixture + AP-2) |
| Layout | single column table | 2-col grid `(1fr 320px)` per mockup `.grid-main` |
| Table rows | 6-col with `passed badge` + reason snippet | 6-col mockup-shape: `Status circle / Claim+evidence dual-line / Agent mono / Kind Badge / Score colored / When subtle` |
| Sidebar | none | Failure kinds card (5-row bar-track AP-2 fixture) + Flaky checks card (3-row rate badge AP-2 fixture) |
| Pagination | Prev / Next footer | **Retired** per Karpathy §3 — mockup table is "Most recent first · failures pinned"; deferred admin pagination to Phase 58+ |

### 1.4 Outer shell + `/timeline` tab disposition decision (Day 0 final)

**Mockup** (`page-extras.jsx:817-926 VerificationPage`) shows ONE single view with no `recent` / `timeline` sub-tabs. Production has outer 2-tab (`recent` / `timeline`) per Sprint 57.11 + 57.13 vintage. Two options:

- **Option A** (lower-risk; mirrors Sprint 57.40 outer-2-tab preservation for `/governance` + `/governance/audit-log`): preserve outer 2-tab as-is; rebuild only the `recent` slot. `/verification/timeline` continues to host `CorrectionTraceView` (unchanged). Outer 2-tab is production-only structural element — acceptable per Sprint 57.40 precedent because timeline is a distinct concept (correction trace per session) NOT covered by mockup `VerificationPage`.
- **Option B**: drop outer 2-tab; `/verification` becomes single mockup-faithful view; `/verification/timeline` moves to its own sidebar entry. Higher-risk routing restructure; sidebar entry mismatch.

→ **Selected: A** (outer 2-tab preserved; only `recent` slot rebuilt). Same reasoning as Sprint 57.40 §1.4: lower-risk + matches mockup `VerificationPage` exactly within its scope; the `timeline` tab is a distinct production-only operational concept that mockup omits.

### 1.5 Class baseline + calibration evaluation criteria

`frontend-mockup-strict-rebuild` 0.60 (7th application):

| Sprint | Page | Ratio | Notes |
|--------|------|-------|-------|
| 57.23 | auth flow rebuild (7 routes) | 0.59 | 1st app below band 0.26 |
| 57.24 v2 | cost-dashboard rebuild | 1.19 | 2nd app top of band |
| 57.25 | sla-dashboard rebuild | 0.88 | 3rd app in band |
| 57.27 | overview rebuild | ≈0.95 | 4th app in band |
| 57.37A | loop-debug rebuild | ≈1.18 | 5th app top of band |
| 57.40 | governance rebuild | ≈0.36 | 6th app deeply below band (agent-delegation 7th consecutive ~3-5× speedup) |
| **57.41 (this)** | **verification rebuild** | **TBD** | 7th app — single-domain, mid-scope (4-KPI + 2-col + sidebar); 5 NEW components, 2 NEW Sprint 57.40 pattern-reuse renames |

**3-sprint window** (last 3: 57.27 ≈0.95 + 57.37A ≈1.18 + 57.40 ≈0.36): only 1 of 3 < 0.7 → **lower-trigger NOT met** → KEEP 0.60 baseline this iteration per `.claude/rules/sprint-workflow.md §When to adjust`.

**Cross-class agent-delegation signal**: `AD-Sprint-Plan-Agent-Delegation-Factor-Modifier` has 3 data points across 2 classes (57.39 -with-extras 0.41 + FIX-015 outlier + 57.40 mockup-strict-rebuild 0.36); activation rule technically met but spans classes. **Defer 1 more sprint for 4th data point before structurally changing matrix**. Sprint 57.41 will be agent-delegated Day 1 (8th consecutive code-implementer) — if ratio < 0.7, this becomes the 4th cross-class data point and triggers proposal evaluation in Sprint 57.42 retro.

Evaluation thresholds for Sprint 57.41:

- **PASS**: ratio in [0.85, 1.20] → KEEP 0.60; class returns toward 6-pt mean 0.86 lower edge
- **ABOVE band** (>1.20): 1 above-band among 7 pts; KEEP
- **BELOW band** (<0.85): if < 0.7, becomes 2nd consecutive below-band in 4-sprint window (57.40 + 57.41) → activation of agent-delegation factor modifier nears trigger; KEEP this iteration but flag for 57.42

### 1.6 Phase-2 epic progress impact

Pre-sprint:
- **Honest** Phase-2 status (post Sprint 57.40): 17 PARITY + 1 NEAR-PARITY + 4 🔴 CATASTROPHIC remaining (`/memory` + `/verification` + `/admin-tenants` + `/tenant-settings`).

Post-sprint (if Sprint 57.41 ships):
- **Phase-2: 18 PARITY + 1 NEAR-PARITY / 3 🔴 CATASTROPHIC remaining** (`/memory` + `/admin-tenants` + `/tenant-settings`).
- Drift audit 2026-05-25 #2 priority CLOSED.

---

## 2. User Stories

### Domain — `/verification` recent view full rebuild

#### US-1 — `.page-head` mockup-aligned
As the operator, I want `/verification/recent` to show a proper page header (`Verification` title + sub-text `Range 7 · Claim verification with evidence · failed claims block downstream actions` + `/verification` route-pill + `All kinds` + `Export` outline buttons) matching mockup, so the page identity is clear.

#### US-2 — 4 KPI strip
As the operator, I want 4 KPI cards at the top of the Verification view (Pass rate · 1h / Claims · 1h / Failed · 1h / Median latency) for at-a-glance health. **Pass rate** derived from `useVerificationRecent.data.items` (compute `passed.length / total * 100`). Other 3 KPIs use fixture data with `<BackendGapBanner>` (AP-2) until Cat 12 verification stats endpoint ships.

#### US-3 — Recent verification runs table mockup-shape (6-col)
As the operator, I want the main list to show 6 cols matching mockup `page-extras.jsx:856-877`:
- Status circle (✓ green / ✗ red with `oklch(from var(--success|danger) l c h / 0.2)` background)
- Claim + evidence dual-line cell (`fontSize: 12.5` claim / `fontSize: 11 mono subtle` evidence)
- Agent mono (`fontSize: 11.5; color: var(--fg-muted)`)
- Kind `<Badge tone="success">`
- Score mono tnum right-aligned, colored: `>0.85 var(--success)` / `>0.6 var(--warning)` / else `var(--danger)`
- When subtle (`fontSize: 11.5`)

Rows from real `useVerificationRecent` query; map `VerificationLogEntry` shape to mockup `VERIFY_CLAIMS` shape (claim / evidence / agent / kind / score / at).

#### US-4 — Failure kinds sidebar card (5-row bar-track)
As the operator, I want a sidebar card "Failure kinds — What's breaking" showing 5 entries (source_allowlist / schema_completeness / metric_threshold / evidence_chain / doc_match) each with: dot indicator + mono name + count + bar-track scaled `(n/max)*100%`. Backed by **AP-2 fixture** (`BackendGapBanner` declares deferred backend kinds aggregation endpoint). Mockup data uses palette `var(--danger)` / `var(--warning)` / `var(--memory)` / `var(--info)`.

#### US-5 — Flaky checks sidebar card (3-row rate badge)
As the operator, I want a sidebar card "Flaky checks — Failing > 5%, last 24h" showing 3 entries (claim_pii_redacted / source_in_allowlist / schema.action_items_have_owner) each with: mono check name + agent subtle mono + `<Badge tone="warning">{rate}</Badge>`. Backed by **AP-2 fixture** (`BackendGapBanner` declares deferred backend flaky aggregation endpoint).

#### US-6 — VerificationList filter form retirement
As the developer, since mockup has no filter form (only "All kinds" outline header button as AP-2 stub for future kind-filter dropdown), retire `VerificationList.tsx` filter form via Karpathy §3 orphan delete. Backend `GET /verifications/recent?session_id=&verifier_type=&passed=` filter capability is preserved (backend not touched) but UI surface deferred to Phase 58+ via carryover `AD-Verification-Filter-Form-Phase58-Migrate`.

#### US-7 — Pattern reuse from Sprint 57.40 primitives
As the developer, transfer 2 of Sprint 57.40's 5 NEW components via mild rename:
- `ApprovalsPageHeader` → `VerificationPageHeader` (~30 lines; rename + relabel)
- `ApprovalsStatsStrip` → `VerificationStatsStrip` (~50 lines; rename + relabel + change derived count from `approvals.length` to `Pass rate` computed)
The other 3 Sprint 57.40 components (`ApprovalsFilterTabs` / `ApprovalDetailPane` / `ApprovalsEmptyTab`) don't transfer (mockup verification layout has no tabs / no detail pane / no empty-tab placeholder).

#### US-8 — Vitest baseline preserved (≥493/493)
After all sprint changes, Vitest must remain green at or above the 493 baseline (Sprint 57.40 close). NEW specs allowed for new components (target +5-8 NEW specs covering StatsStrip / RunsTable / FailureKindsCard / FlakyChecksCard / PageHeader).

#### US-9 — 22-route sweep clean + route-sweep mock fix
22-route Playwright sweep `before` vs `after`: only `/verification` + `/verification/recent` expected CHANGED (rebuild). Other 20 routes IDENTICAL. **D-DAY0-1 fix candidate**: add `/verifications/recent` specific mock in `route-sweep.mjs` returning `{items: [], total: 0, has_more: false}` shape to eliminate any potential "data is undefined" red banner (parallel to Sprint 57.40 D-DAY0-1 governance mock fix).

#### US-10 — mockup-fidelity guard + HEX_OKLCH_BASELINE bump
`node frontend/scripts/check-mockup-fidelity.mjs` exit 0; baseline may bump +2-5 (status circle `oklch(from var(--success|danger) l c h / 0.2)` × 2 + score colored thresholds 3 colors + bar-track palette 5 colors).

#### US-11 — Audit report verdict update
After sprint, update `claudedocs/5-status/drift-audit-2026-05-25/audit-report.md` to mark `/verification` verdict ✅ **PARITY** post-rebuild; carryover list shrinks 4 → 3 🔴 CATASTROPHIC.

---

## 3. Technical Specifications

### 3.1 Component refactor map

```
frontend/src/pages/verification/index.tsx (81 lines, UNCHANGED structure: RequireAuth + AppShellV2 + outer 2-tab Tabs + Routes)
  └─ <Route path="recent" element={<VerificationView />} />  ← was VerificationList
       ↓
       frontend/src/features/verification/components/VerificationView.tsx (NEW ~80 lines)
        ├─ <VerificationPageHeader /> — NEW (rename Sprint 57.40 ApprovalsPageHeader)
        ├─ <VerificationStatsStrip /> — NEW (rename Sprint 57.40 ApprovalsStatsStrip + Pass rate compute)
        ├─ <div className="grid-main"> — 2-col grid
        │    ├─ <VerificationRunsTable /> — NEW (Recent verification runs Card wrap + 6-col table)
        │    └─ <div className="col" style={{ gap: 14 }}>
        │         ├─ <FailureKindsCard /> — NEW (5-row bar-track AP-2)
        │         └─ <FlakyChecksCard /> — NEW (3-row rate badge AP-2)
        └─ {/* no detail pane / no modal — mockup has none */}
```

### 3.2 NEW components inventory

| Component | File | Lines (est) | Purpose |
|-----------|------|-------------|---------|
| `VerificationPageHeader` | `features/verification/components/VerificationPageHeader.tsx` | ~30 | mockup `.page-head` + All kinds / Export buttons |
| `VerificationStatsStrip` | `features/verification/components/VerificationStatsStrip.tsx` | ~55 | 4 Stat cards; Pass rate derived from `items.filter(ok).length / total`; other 3 KPIs fixture + AP-2 banner |
| `VerificationRunsTable` | `features/verification/components/VerificationRunsTable.tsx` | ~110 | Card wrap with title "Recent verification runs" + 6-col table; status circle / claim+evidence dual-line / agent mono / Kind badge / colored score / when |
| `FailureKindsCard` | `features/verification/components/FailureKindsCard.tsx` | ~55 | sidebar Card "Failure kinds — What's breaking"; 5-row bar-track AP-2 fixture |
| `FlakyChecksCard` | `features/verification/components/FlakyChecksCard.tsx` | ~45 | sidebar Card "Flaky checks — Failing > 5%, last 24h"; 3-row rate badge AP-2 fixture |
| `VerificationView` | `features/verification/components/VerificationView.tsx` | ~80 | container assembling the 5 above; consumes `useVerificationRecent` query |

### 3.3 DELETED / RETIRED components

| Component | File | Disposition |
|-----------|------|-------------|
| `VerificationList` | `features/verification/components/VerificationList.tsx` (299 lines) | **ORPHAN DELETE per Karpathy §3** — filter form + paginated table replaced entirely by `VerificationView`. Sprint 57.33 defensive `?? []` guards preserved at logic level (consumed via `useVerificationRecent` hook in new `VerificationRunsTable`). Carryover AD: `AD-Verification-Filter-Form-Phase58-Migrate` for future `/verification/admin` route with filter form. |

### 3.4 mockup-ui primitives used

Per `frontend/src/components/mockup-ui.tsx` (post Sprint 57.40 promotion):

- `<Stat>` — reused (4 KPI cards; same as Sprint 57.40 StatsStrip)
- `<Card>` — reused (3 cards: Recent verification runs + Failure kinds + Flaky checks)
- `<Badge>` — reused (Kind badges + rate badges; multiple tones)
- `<BackendGapBanner>` — reused (AP-2 declarations on 3 KPI + 2 sidebar cards)
- `<Icon>` — reused for status circles (check / x) — confirm Day 0 Prong 2 (`mockup-ui` Icon export presence + size prop)

NO NEW primitives needed (mockup-ui.tsx already has all required parts from Sprint 57.40).

### 3.5 D-DAY0-1: route-sweep mock candidate

`frontend/scripts/route-sweep.mjs` line ~177-185 default branch: candidate add (Day 0 Prong 1 confirm path + Day 2 §2.3 task):

```js
if (/\/verifications\/recent/.test(url)) {
  return json({ items: [], total: 0, has_more: false });
}
```

Eliminates potential "data is undefined" mock artifact (parallel to Sprint 57.40 governance fix). Document MHist entry + carryover `AD-RouteSweep-Envelope-Mock-Convention` deepens (3rd occurrence after Sprint 57.40 governance).

### 3.6 HEX_OKLCH_BASELINE envelope

Current baseline 46 (post Sprint 57.40). Sprint 57.41 bump estimate:

- Status circle backgrounds `oklch(from var(--success|danger) l c h / 0.2)`: +2
- Score color tier var refs (`var(--success)` / `var(--warning)` / `var(--danger)`): +0 (already var-based)
- Failure kinds dot palette (`var(--danger)` / `var(--warning)` / `var(--memory)` / `var(--info)`): +0 (already var)
- Bar-track inline `background: f.c` — uses var refs not hex: +0

Total expected: **+2-4** → target ≤50 (set `check-mockup-fidelity.mjs` `HEX_OKLCH_BASELINE` to 50 max).

### 3.7 useVerificationRecent → VERIFY_CLAIMS shape mapping

Production `VerificationLogEntry` shape (from `features/verification/types.ts`):
```ts
{ id, created_at_ms, session_id, verifier_name, verifier_type, passed, reason, score? }
```

Mockup `VERIFY_CLAIMS` shape:
```ts
{ id, agent, session, claim, evidence, ok, score, ms, kind, at }
```

Mapping (in `VerificationRunsTable`):
- `id` ← `entry.id`
- `agent` ← `entry.verifier_name` (or session-scoped agent if present in payload)
- `session` ← `entry.session_id` (sliced 8 chars)
- `claim` ← computed: if `passed` use `verifier_name + " check passed"`; if `!passed` use `reason || "verification failed"` (best-effort — backend doesn't yet expose "claim" / "evidence" structured fields)
- `evidence` ← `entry.reason` snippet 80 chars
- `ok` ← `entry.passed`
- `score` ← `entry.score ?? (passed ? 0.95 : 0.5)` (fallback when null)
- `kind` ← `entry.verifier_type` (rules_based / llm_judge / external) — surface as Kind badge
- `at` ← relative time from `entry.created_at_ms` (e.g. "now" / "5m ago" / "12m ago")

Document mapping as `AD-Verification-Backend-Claim-Evidence-Extension` carryover (Phase 58+ backend extends `VerificationLogEntry` with structured `claim` + `evidence` + `kind` fields beyond `reason` text).

---

## 4. File Change List

### NEW files (6 components + 5-8 specs)

- `frontend/src/features/verification/components/VerificationPageHeader.tsx` — ~30 lines
- `frontend/src/features/verification/components/VerificationStatsStrip.tsx` — ~55 lines
- `frontend/src/features/verification/components/VerificationRunsTable.tsx` — ~110 lines
- `frontend/src/features/verification/components/FailureKindsCard.tsx` — ~55 lines
- `frontend/src/features/verification/components/FlakyChecksCard.tsx` — ~45 lines
- `frontend/src/features/verification/components/VerificationView.tsx` — ~80 lines
- `frontend/tests/unit/verification/VerificationPageHeader.test.tsx` — +1 spec
- `frontend/tests/unit/verification/VerificationStatsStrip.test.tsx` — +2 specs
- `frontend/tests/unit/verification/VerificationRunsTable.test.tsx` — +2-3 specs (mapping + status circle + score color)
- `frontend/tests/unit/verification/FailureKindsCard.test.tsx` — +1 spec
- `frontend/tests/unit/verification/FlakyChecksCard.test.tsx` — +1 spec

### MODIFIED files

- `frontend/src/pages/verification/index.tsx` — swap `<VerificationList />` → `<VerificationView />` on `recent` route; preserve outer 2-tab + auth gate + AppShellV2
- `frontend/scripts/route-sweep.mjs` — D-DAY0-1 candidate fix: specific `/verifications/recent` mock returning `{items: [], total: 0, has_more: false}` + re-point `OUT_DIR` to `sprint-57-41-verification-full-rebuild`
- `frontend/scripts/check-mockup-fidelity.mjs` — `HEX_OKLCH_BASELINE` 46 → ≤50 (set actual on Day 2 close)
- `claudedocs/5-status/drift-audit-2026-05-25/audit-report.md` — Day 3 closeout: mark `/verification` verdict ✅ PARITY post-rebuild; carryover list 4 → 3

### DELETED files

- `frontend/src/features/verification/components/VerificationList.tsx` — orphan delete per Karpathy §3 (filter form + paginated table superseded by mockup-shape `VerificationView`)
- `frontend/tests/unit/verification/VerificationList.test.tsx` (if exists) — delete with parent; or refactor remaining defensive `?? []` assertions to migrate into `VerificationRunsTable.test.tsx` if applicable
- `frontend/tests/e2e/verification/verification-list.spec.ts` (if exists) — adapt or delete; new e2e for mockup view if time permits (best-effort Day 2)

### Cross-domain

- `memory/project_phase57_41_verification_full_rebuild.md` — sprint subfile
- `memory/MEMORY.md` — quality pointer (~300 char)
- Sprint plan + checklist + progress.md + retrospective.md (this file + checklist + execution files)
- `.claude/rules/sprint-workflow.md` — §Scope-class multiplier matrix `frontend-mockup-strict-rebuild` row: append Sprint 57.41 as 7th data point + agent-delegation modifier 4th cross-class point note
- `claudedocs/1-planning/next-phase-candidates.md` — mark Sprint 57.41 rebuild complete; carryover list 4 → 3 🔴 CATASTROPHIC; add `AD-Verification-Filter-Form-Phase58-Migrate` + `AD-Verification-Backend-Claim-Evidence-Extension`

---

## 5. Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| AC1 | `/verification/recent` visual matches mockup `page-extras.jsx:817-926` | Day 2.5 fidelity verdict ✅ PARITY (worst-case 🟡 NEAR-PARITY with minor cosmetic notes) |
| AC2 | `.page-head` shows "Verification" title + sub + route-pill + All kinds + Export | Day 2.5 PNG visual |
| AC3 | 4 KPI cards visible: Pass rate · 1h / Claims · 1h / Failed · 1h / Median latency | Same |
| AC4 | Pass rate computed from real `useVerificationRecent.data.items` | Vitest spec |
| AC5 | 2-col `.grid-main` layout: Recent runs table left + sidebar (Failure kinds + Flaky checks) right | Same |
| AC6 | Recent runs table 6-col mockup shape (status circle / claim+evidence / agent / Kind badge / score / when) | Vitest spec + PNG |
| AC7 | Score color tier: `>0.85 success` / `>0.6 warning` / else `danger` | Vitest spec |
| AC8 | Failure kinds 5-row bar-track with palette | Vitest spec + PNG |
| AC9 | Flaky checks 3-row rate badge | Vitest spec + PNG |
| AC10 | 3 of 4 KPI + Failure kinds + Flaky checks render `<BackendGapBanner>` (AP-2) | Vitest spec |
| AC11 | VerificationList orphan-deleted; no import sites remaining | grep returns 0 |
| AC12 | route-sweep `/verifications/recent` mock returns proper envelope (D-DAY0-1 fix) | Re-run sweep → no red banner |
| AC13 | Vitest ≥493/493 (+5-8 NEW specs allowed) | `npm test -- --reporter=dot` last line |
| AC14 | 22-route sweep: only `/verification` + `/verification/recent` CHANGED; 20 IDENTICAL | progress.md Day 2.5 entry |
| AC15 | mockup-fidelity guard exit 0 (HEX_OKLCH_BASELINE ≤50) | `node frontend/scripts/check-mockup-fidelity.mjs` exit 0 |
| AC16 | Outer 2-tab (recent / timeline) PRESERVED in `pages/verification/index.tsx` | unchanged outer shell |
| AC17 | `/verification/timeline` (CorrectionTraceView) UNCHANGED | grep diff: 0 lines |
| AC18 | `useVerificationRecent` / `verificationService` UNCHANGED | grep diff: 0 lines |
| AC19 | Per-domain calibration ratio recorded in retrospective.md §Q2 | 7th data point + matrix update note |
| AC20 | Drift audit report `/verification` ✅ PARITY post-rebuild | `claudedocs/5-status/drift-audit-2026-05-25/audit-report.md` edited |

---

## 6. Deliverables

- [ ] `VerificationPageHeader` + `VerificationStatsStrip` + `VerificationRunsTable` + `FailureKindsCard` + `FlakyChecksCard` + `VerificationView` components shipped
- [ ] `pages/verification/index.tsx` route swap to `VerificationView`
- [ ] `VerificationList.tsx` orphan-deleted per Karpathy §3
- [ ] route-sweep.mjs D-DAY0-1 fix applied + OUT_DIR re-pointed
- [ ] 22-route sweep before/after diff reviewed; verdict logged
- [ ] retrospective.md Q1-Q7 with calibration ratio computed (7th data point)
- [ ] `.claude/rules/sprint-workflow.md` §matrix `frontend-mockup-strict-rebuild` row updated
- [ ] Memory subfile + MEMORY.md pointer entry per Sprint Closeout Update Policy
- [ ] PR opened against main; CI green; squash-merge ready
- [ ] Drift audit report `/verification` verdict updated ✅ PARITY

---

## 7. Risks & Mitigations

| Risk | Class | Mitigation |
|------|-------|-----------|
| `VerificationLogEntry` shape lacks `kind` / `claim` / `evidence` structured fields → mapping degraded | Data model gap | Day 0 Prong 2 grep `types.ts` + backend router; if lacks, accept fixture-shaped derived fields with AP-2 banner declaring structured-field backend extension deferred; carryover AD-Verification-Backend-Claim-Evidence-Extension |
| `useVerificationRecent` returns paginated 50-row shape; mockup shows all rows unpaginated | Pagination semantics drift | Sprint 57.41 keeps backend pagination at hook level but UI renders only first page (50 rows) — matches mockup's "Most recent first · failures pinned" semantic; pagination footer dropped per §1.3 |
| Vitest specs assert old VerificationList class names → break on orphan delete | Spec fragility | Day 2 §2.1 spec migration: delete VerificationList.test.tsx; new specs cover new components only |
| Outer 2-tab `timeline` route accidentally broken by `recent` slot swap | Route regression | Day 0 Prong 2.5 confirm `index.tsx` 2-tab + nested Routes structure preserved; manual click test `/verification/timeline` Day 2.5 |
| Failure kinds + Flaky checks AP-2 fixture data + banner overcrowds sidebar | Visual density | Day 2.5 PNG review; tweak fixture row counts if needed (mockup has 5 + 3) |
| HEX_OKLCH_BASELINE bump exceeds +4 envelope | Mockup-fidelity guard | Update guard threshold to actual count; bump >4 = signal for color consolidation (carryover AD candidate) |
| Day 0 Prong 1/2 path drift → plan §Technical Spec inaccurate | Plan-vs-repo drift (Sprint 53.7 D4-D12 class) | Drift catalogue + plan §1.x amend in progress.md; scope confirm with user before Day 1 |
| Risk Class A: paths-filter vs `required_status_checks` | CI infra (recurring) | Touch `.github/workflows/backend-ci.yml` header comment if backend-ci skips on frontend-only PR |
| Single-domain agent-delegation budget overruns | Agent-delegation scope | Day 1 = 6 components (1 agent invocation); Day 2 = specs + route-sweep + restructure (2nd agent invocation OR human-direct) |
| Per AD-Plan-5 Prong 2.5: child-component-tree depth audit | Child tree drift | Day 0 enumerate `features/verification/components/*` + grep shadcn-utility residue (post FIX-015 should be 0 in VerificationPanel + VerifierTypeBadge; expect 0 in CorrectionTraceView since out-of-scope `timeline` tab); confirm no AP-Phase2-A/B/C anti-patterns |
| Agent-delegation 4th cross-class data point < 0.7 → modifier activation trigger | Calibration drift | Document ratio honestly in retrospective.md Q2; if < 0.7, propose Sprint 57.42 retro evaluation of `AD-Sprint-Plan-Agent-Delegation-Factor-Modifier` (Option A coefficient = 0.55) |

---

## 8. Workload

**Bottom-up est** ~14 hr → **calibrated commit ~8.5 hr** (multiplier 0.60 per `frontend-mockup-strict-rebuild` 7th app baseline; 3-sprint window lower-trigger NOT met)

Bottom-up breakdown:

| Day | Tasks | Est (hr) |
|-----|-------|----------|
| Day 0 | 3-prong grep + drift catalog + plan amend | 1.0 |
| Day 1 | 6 NEW components (PageHeader 0.5 + StatsStrip 0.75 + RunsTable 2.5 + FailureKindsCard 1.5 + FlakyChecksCard 1.0 + VerificationView 1.5) | 7.75 |
| Day 2 | Vitest specs (5-8 NEW) + route-sweep mock + restructure + VerificationList orphan delete | 3.0 |
| Day 2.5 | Fidelity PNG + 22-route sweep + HEX_OKLCH baseline assert | 1.0 |
| Day 3 | Retro + memory + audit-report + CLAUDE.md + next-phase-candidates + PR | 1.5 |

Sprint-aggregate: 14.25 hr → 0.60 × = **~8.5 hr committed**. Matches `AD-Verification-Catastrophic-Rebuild` estimate ~8-10 hr.

---

## 9. Carryover candidates (Phase 58+)

Logged in retrospective.md §Q5 + `claudedocs/1-planning/next-phase-candidates.md`:

- `AD-Verification-Filter-Form-Phase58-Migrate` — Sprint 57.41 retired filter form per Karpathy §3 (mockup has none). If admin filter UI is needed, surface on `/verification/admin` separate route OR re-introduce as collapsible `<details>` panel above the runs table (NOT inline form per mockup).
- `AD-Verification-Backend-Claim-Evidence-Extension` — Backend `VerificationLogEntry` currently has only `reason` text; mockup expects structured `claim` + `evidence` + `kind` fields. Sprint 57.41 maps best-effort via fallback. Phase 58+ backend can extend schema for cleaner mapping.
- `AD-Verification-All-Kinds-Filter-Dropdown` — Mockup header "All kinds" outline button is Sprint 57.41 AP-2 stub; deferred kind-filter dropdown wiring to Phase 58+.
- `AD-Verification-Failure-Kinds-Aggregation-Endpoint` — Sprint 57.41 sidebar Failure kinds is AP-2 fixture. Phase 58+ backend `GET /verifications/stats/failure-kinds` endpoint required for real data.
- `AD-Verification-Flaky-Checks-Aggregation-Endpoint` — Same as above for Flaky checks sidebar.
- `AD-Sprint-Plan-Agent-Delegation-Factor-Modifier` (carryover from Sprint 57.39 + 57.40) — Sprint 57.41 contributes 4th cross-class data point; if ratio < 0.7, propose Sprint 57.42 retro evaluation per `.claude/rules/sprint-workflow.md §Proposed Agent Delegation Factor Modifier`.

---

**Last Updated**: 2026-05-25 (Day 0)

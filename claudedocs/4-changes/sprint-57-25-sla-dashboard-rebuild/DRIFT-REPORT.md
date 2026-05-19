# Sprint 57.25 — DRIFT-REPORT (SLA Dashboard Rebuild)

**Sprint**: 57.25 (AD-Mockup-Fidelity-Rebuild-Sla-Dashboard)
**Class**: `frontend-mockup-strict-rebuild` 0.60 (3rd application)
**Mockup ref**: `reference/design-mockups/page-admin.jsx:31-199` (SlaPage + LatencyChart helper)
**Production ref**: `frontend/src/features/sla-dashboard/components/SLAOverview.tsx` (Sprint 57.1 + 57.9 + 57.13 + 57.16 evolved baseline)
**Audit lineage**: Sprint 57.22 AUDIT-REPORT-COMPREHENSIVE.md Unit 9 (P0 full rebuild; same FUNCTIONAL pattern as Unit 8 cost-dashboard)

---

## Initial Drift Inventory (Day 0)

### 6-Widget-Group Coverage Matrix

| # | Mockup widget group | Mockup ref line | Production state | Drift severity | Sprint 57.25 work | Final verdict (Day 3 close) |
|---|---------------------|-----------------|------------------|----------------|-------------------|------------------------------|
| 1 | page-head (title + sub + route-pill + 4-button time-range tabs + Refresh + Export) | `:33-52` | ❌ Missing (only AppShellV2 chrome title + plaintext paragraph) | STRUCTURAL | US-B1 PageHead + TimeRangeTabs + Refresh + Export stubs | TBD |
| 2 | 4-stat sparkline grid (p50 / p95 / p99 latency + Error budget) | `:54-59` | ❌ Missing (production = 6-card MetricsCard layout with different field semantic) | STRUCTURAL | US-B2 4 × `<StatCard>` + `<Spark>` reuse | TBD |
| 3 | 24h LatencyChart 3-series SVG (p50 / p95 / p99 over 48 time points) | `:61-70 + :157-198` | ❌ Missing (no chart at all) | STRUCTURAL | US-B3 NEW `<LatencyChart>` feature-scoped (Karpathy §2 inline) | TBD |
| 4 | 5-row SLO status card (Loop p95 / Tool success / HITL response / Subagent depth / Cost per run) | `:72-99` | ❌ Missing (production has flat 6-card MetricsCard) | STRUCTURAL | US-C1 NEW `<SLOStatusCard>` + `<BarTrack>` reuse | TBD |
| 5 | Top slow operations table (6-row × Operation + Kind Badge + p50/p95/p99/Calls) | `:104-129` | ❌ Missing | STRUCTURAL + backend gap | US-C2 NEW `<TopSlowOpsTable>` + fixture + AP-2 banner | TBD |
| 6 | Error rate by service card (6-row × service + rate + `<BarTrack>`) | `:131-152` | ❌ Missing | STRUCTURAL + backend gap | US-C3 NEW `<ErrorRateByServiceCard>` + fixture + AP-2 banner | TBD |
| — | violations Badge + MonthPicker (production-only) | (not in mockup) | ✅ existing | reverse-drift | Preserve MonthPicker as auxiliary + sibling note (Q1 user alignment); drop violations Badge OR move to subtle location | TBD |
| — | 6 × SLAMetricsCard flat layout (production-only) | (not in mockup) | ✅ existing | reverse-drift | Karpathy §3 orphan delete (Q3 user alignment) | TBD |

---

## Field Semantic Mismatch (D-PRE-2)

`useSLAReport` backend response shape vs mockup field expectations:

| Mockup field expectation | Backend `useSLAReport` response | Mapping |
|--------------------------|----------------------------------|---------|
| `p50 latency` | ❌ NOT in response | Fixture in `__fixtures__/statSparklines.ts` + AP-2 banner |
| `p95 latency` | ❌ NOT in response | Fixture |
| `p99 latency` | ✅ `api_p99_ms` | Real backend → stat card #3 |
| `Error budget` | ❌ NOT in response | Fixture + AP-2 banner |
| `LatencyChart 24h time-series (p50 / p95 / p99 × 48 points)` | ❌ NOT in response (only month-level aggregate) | Fixture in `__fixtures__/latencyChart24h.ts` + AP-2 banner |
| `SLO Loop p95 < 2s` | ✅ `loop_simple_p95_ms` (if Sprint 57.13+ has p95 split) OR fixture | TBD Day 2.1 verify |
| `SLO Tool success` / `SLO HITL response` / `SLO Subagent depth` / `SLO Cost per run` | ❌ NOT in response | Fixture (4 of 5 SLO rows fixture) |
| `Top slow ops × p50/p95/p99/Calls` | ❌ NOT in response | Fixture + AP-2 banner |
| `Error rate by service × rate` | ❌ NOT in response | Fixture + AP-2 banner |

**3 expected BackendGapBanner instances** (LatencyChart 24h history / cross-operation p99 / per-service error rate); Plan §Risks R2 mitigation.

---

## Mockup Reference Resolution

| Mockup section | Lines | Function/component | Sprint 57.25 mapping |
|----------------|-------|--------------------|-----------------------|
| `AreaChart` helper | `:4-29` | Single-series AreaChart (NOT used this sprint; Sprint 57.24 v2 `<AreaChart>` is for SVG single-series stack — mockup's LatencyChart is multi-series) | N/A (LatencyChart inline) |
| `SlaPage` body | `:32-156` | Full SLA dashboard layout | SLAOverview.tsx rewrite |
| `LatencyChart` helper | `:157-198` | 3-series multi-line SVG | NEW `LatencyChart.tsx` feature-scoped |

---

## Tools/References Used Day 0

- Sprint 57.22 AUDIT-REPORT-COMPREHENSIVE.md Unit 9 (Prong 5 audit cross-ref)
- next-phase-candidates.md #32 (rebuild quartet 57.25-57.28 anchor)
- Sprint 57.24 v2 plan + checklist + retrospective (template + class baseline data point reference)
- Sprint 57.20 plan (Option W frontend-leads + backend-follows philosophy carryover)
- CLAUDE.md §Frontend Mockup-Fidelity Hard Constraint (Mockup ≠ retrofit; rebuild only)
- `.claude/rules/sprint-workflow.md §Step 2.5` (Day-0 verify discipline; Prong 5 audit cross-ref)
- `.claude/rules/sprint-workflow.md §Scope-class multiplier matrix` (frontend-mockup-strict-rebuild 0.60 class history)

---

## Day 1 — 2026-05-19 (US-B1 + US-B2 + US-B3 SHIPPED)

### Coverage matrix update (3 of 6 widget groups shipped)

| # | Mockup widget group | Production state | Verdict (Day 1) |
|---|---------------------|------------------|-----------------|
| 1 | page-head + TimeRangeTabs + Refresh + Export | ✅ shipped (PageHead reuse + TimeRangeTabs NEW + Refresh wired + Export stub) | **PARITY (code-level)** |
| 2 | 4-stat sparkline grid | ✅ shipped (StatCard + Spark reused × 4) | **PARITY (code-level; 3 of 4 fixture per D-PRE-2)** |
| 3 | 24h LatencyChart 3-series | ✅ shipped (NEW feature-scoped + CardShell + BackendGapBanner) | **PARITY (code-level; fixture per D-PRE-2; banner present)** |
| 4 | 5-row SLO status card | ⏳ pending Day 2 | n/a |
| 5 | Top slow operations table | ⏳ pending Day 2 | n/a |
| 6 | Error rate by service | ⏳ pending Day 2 | n/a |

### Cross-references

- `progress.md` Day 1 §Mockup-fidelity audit (line-by-line code vs mockup `page-admin.jsx:33-198`)
- `LatencyChart.test.tsx` (5 cases verify SVG path count + tick count + stroke hierarchy + opacity)
- `TimeRangeTabs.test.tsx` (4 cases verify 4 tabs render + 24h active default + click change + role tablist)

### Day 1 deliverables (per Plan §Acceptance §1-§5)

| AC | Status |
|----|--------|
| §1 6 widget groups at 1440×900 | 3 of 6 shipped Day 1; remaining 3 Day 2 |
| §2 Reuse 7 Sprint 57.24 v2 primitives | ✅ PageHead + StatCard + Spark + CardShell + BackendGapBanner used Day 1; AreaChart not used (mockup multi-line ≠ single-area); BarTrack pending Day 2 |
| §3 Real backend data where applicable | ✅ `useSLAReport.api_p99_ms` → p99 stat; remaining fields fixture per D-PRE-2 |
| §4 BackendGapBanner instances | 1 of 3 expected shipped (LatencyChart 24h); 2 pending Day 2 (cross-operation p99 + per-service error rate) |
| §5 TimeRangeTabs visual-only + MonthPicker auxiliary | ✅ both wired per Q1+Q2 user alignment |

## Day 2 — 2026-05-19 (US-C1 + US-C2 + US-C3 SHIPPED; rebuild COMPLETE)

### Coverage matrix update (6 of 6 widget groups SHIPPED)

| # | Mockup widget group | Production state | Verdict (Day 2) |
|---|---------------------|------------------|-----------------|
| 1 | page-head + TimeRangeTabs + Refresh + Export | ✅ shipped Day 1 | PARITY |
| 2 | 4-stat sparkline grid | ✅ shipped Day 1 | PARITY (3/4 fixture) |
| 3 | 24h LatencyChart 3-series | ✅ shipped Day 1 | PARITY (banner #1) |
| 4 | 5-row SLO status card | ✅ shipped Day 2 (SLOStatusCard NEW; BarTrack + CardShell reused) | **PARITY** |
| 5 | Top slow operations table | ✅ shipped Day 2 (TopSlowOpsTable NEW; Kind Badge tone palette; p99 warning > 3000ms) | **PARITY (banner #2)** |
| 6 | Error rate by service | ✅ shipped Day 2 (ErrorRateByServiceCard NEW; warning tone > 0.5%; BarTrack reused) | **PARITY (banner #3)** |
| — | legacy 6×SLAMetricsCard + violations Badge | ⚠️ DELETED Day 2 (Karpathy §3 orphan delete per Q3 user alignment) | reverse-drift resolved |

### Cross-references

- `progress.md` Day 2 §Mockup-fidelity audit (per-widget code vs mockup `page-admin.jsx:72-152`)
- `SLOStatusCard.test.tsx` (5 cases: 5 SLO rows / dot color ok/failing / failing danger text / ok muted text / Loop p95 proxy from data)
- `TopSlowOpsTable.test.tsx` (5 cases: 6 rows / Kind tone per kind / p99 warning > 3000 / p99 muted <= 3000 / cross-operation banner)
- `ErrorRateByServiceCard.test.tsx` (4 cases: 6 rows / warning rate > 0.5 / muted rate <= 0.5 / per-service banner)

### Day 2 deliverables (per Plan §Acceptance §1-§12)

| AC | Status |
|----|--------|
| §1 6 widget groups at 1440×900 | ✅ **6 of 6 SHIPPED** |
| §2 Reuse 7 Sprint 57.24 v2 primitives | ✅ PageHead + StatCard + Spark + CardShell + BackendGapBanner + BarTrack used; AreaChart not used (multi-line LatencyChart ≠ single-area shape) |
| §3 Real backend data where applicable | ✅ `useSLAReport.api_p99_ms` → p99 stat; `loop_simple_p99_ms` → Loop p95 SLO proxy; remaining fields fixture per D-PRE-2 |
| §4 BackendGapBanner instances | ✅ **3 of 3 expected** (LatencyChart 24h + cross-operation p99 + per-service error rate) |
| §5 TimeRangeTabs visual-only + MonthPicker auxiliary | ✅ both wired per Q1+Q2 |
| §12 Karpathy §3 orphan delete | ✅ `SLAMetricsCard.tsx` + spec deleted; 0 production importer |

### Final verdict (Day 2 end)

**`/sla-dashboard` rebuild: PARITY (code-level)** per CLAUDE.md §Frontend Mockup-Fidelity Hard Constraint + Sprint 57.22 Unit 9 P0 audit. Playwright MCP visual pair-verify deferred to Day 3 per Q4 (4th-consecutive blocker watch).

## Day 3 — final verdict (target: PARITY code-level audit per Q4 user alignment on Playwright MCP 4th-consecutive blocker fallback)

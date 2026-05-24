# Sprint 57.34 — Retrospective

**Sprint**: 57.34 — AD-Orchestrator-Verbatim-Repoint
**Closed**: 2026-05-24
**Class**: `frontend-verbatim-css-repoint` 0.50 (5th application; **2nd validation** of lifted baseline)
**PR**: (pending push)
**Outcome**: 🎉 `/orchestrator` flipped from Sprint 57.19 Tailwind-translation → mockup verbatim PARITY. 22-route sweep 0 regressions. **1st non-rich-dashboard shape** in epic; bimodal-by-shape hypothesis logged.

---

## Q1 — What went well?

1. **Atomic primitive promotion** — agent identified Day 1 build-dep: page subcomponents (ConfigTab/PromptTab/ToolsTab/etc.) all consume Field+Switch primitives; promoting only Tabs (planned for Day 1) would leave half-translated code. Agent landed all 3 primitives + visual re-point on Day 1; Day 2/3 became data-testid + MHist increments. Smart engineering decision, transparently reported.
2. **Net code reduction** — OrchestratorPage.tsx 644 → 605 lines (-39 net) despite full re-point: local primitive duplication eliminated. mockup-ui.tsx +101 lines reusable across future admin pages (governance / tenant-settings).
3. **Tabs visual delta** — Before-baseline showed tabs squished together (no spacing); after-baseline shows proper mockup `.tabs` styling with active tab underline + count badges. Most visible UX win.
4. **22-route sweep clean** — 0 regressions; 3 routes from Sprint 57.33 fix (`/subagents`, `/memory`, `/verification`) maintained ✅ post-merge.
5. **5 gates green** — tsc / ESLint / Vitest 456/456 baseline / check:mockup-fidelity / Vite build.
6. **a11y bridges added preemptively** — agent added `tabIndex` + `onKeyDown` for Enter/Space on Tabs + Switch to satisfy `jsx-a11y/click-events-have-key-events`. Not in mockup but caught existing lint rules.

---

## Q2 — Calibration

| Metric | Value |
|--------|-------|
| Bottom-up estimate | ~7.5 hr (450 min) |
| Calibrated commit (×0.50) | ~3.75 hr (225 min) |
| Actual (effective human-equivalent) | **~3-4 hr** (agent-assisted; Day 1-3 compressed wall-clock ~9 min) |
| `actual / committed` ratio | **≈ 0.95-1.05** — **in band middle** [0.85, 1.20] |
| `actual / bottom-up` ratio | **≈ 0.55-0.65** — bottom-up ~1.5-1.8× generous; 0.50 multiplier validated |

**Class baseline 5th data point + 2nd validation outcome**:

| Sprint | Shape | Ratio (actual/committed) | Band? |
|--------|-------|--------------------------|-------|
| 57.29 | rich-dashboard (/overview) | ≈1.0 | ✅ in band |
| 57.30 | rich-dashboard (/chat-v2) | ≈0.40 | ❌ below |
| 57.31 | rich-dashboard (/cost-dashboard) | ≈0.35 | ❌ below |
| 57.32 | rich-dashboard (/sla-dashboard) | ≈0.40-0.55 | lower edge |
| **57.34** | **non-rich-dashboard (/orchestrator)** | **≈0.95-1.05** | **✅ in band middle** |

**Bimodal-by-shape signal emerging**:
- Rich-dashboard 3-pt mean (57.30-57.32) ≈ 0.40 below band
- Non-rich-dashboard 1-pt (57.34) ≈ 0.95-1.05 in band middle
- 2-data-point span (57.32 rich + 57.34 non-rich) is suggestive but insufficient per `When to adjust` 3-sprint window rule.

**Decision per rule**:
- **KEEP 0.50 baseline** this iteration.
- **NEW AD: `AD-Sprint-Plan-frontend-verbatim-css-repoint-shape-bimodal-watch`** — if Sprint 57.35 (another non-rich-dashboard shape; e.g. `/loop-debug` or `/state-inspector`) lands in band → propose class split `-rich-dashboard` (0.40) vs `-config-form` (0.50). If lands below band → class-wide variance after all → 0.50 → 0.40 lift.

**Calibration caveat** (same as Sprint 57.13/57.27/57.28/57.29): Day 1-3 was agent-assisted (code-implementer agent), not rigorously per-day human time tracking. Ratio estimated from human-equivalent effort.

---

## Q3 — What didn't go as planned?

1. **Day 1 atomic re-point**: Plan §What gets changed listed Tabs promotion Day 1 / Field promotion Day 2 / Switch promotion Day 3. Agent correctly identified the build-dep — page subcomponents all consume Field+Switch, so promoting Tabs alone would leave duplicate page-local Field+Switch. Atomic Day 1 promotion of all 3 was the right call; plan Day 2/3 became commit-cycle housekeeping (data-testid + MHist). Plan structure looks "wrong" in retrospect, but the result was clean.
2. **Calibration ratio estimation imprecise**: with agent-assisted code work, actual human-equivalent effort is hard to pin down precisely. Estimate range ≈0.95-1.05 is approximate; future agent-assisted sprints should consider tracking the agent's planning+execution as proxy for human-equivalent.

---

## Q4 — What would I do differently next time?

1. **Plan acknowledgement of cross-day primitive co-dependencies**: when 3 primitives share consumer components, Day 1 should promote all 3 (or none) — not stagger across Days. Future sprints with similar primitive promotion + consumer-rewrite pattern should plan atomic Day 1 promotion.
2. **Agent calibration tracking template**: develop a clearer convention for agent-assisted sprint hour estimation. Maybe track 3 metrics: (a) plan-to-PR wall-clock human time, (b) agent execution wall-clock, (c) effective human-equivalent estimate. Then choose 1 for calibration.

---

## Q5 — Next sprint pickup candidates

Per Phase-2 epic backlog and Sprint 57.34 bimodal-watch AD:

1. **`/loop-debug` Phase-2 verbatim CSS re-point** — operator-facing debug UI; another non-rich-dashboard shape; if ratio in band confirms shape-driven bimodal; if below band rejects shape hypothesis.
2. **`/state-inspector` Phase-2 verbatim CSS re-point** — operations admin shape; same bimodal test.
3. **`/admin-tenants` Phase-2 verbatim CSS re-point** — admin shape; could pair with bimodal test (and Sprint 57.32 retro Q5 alternate candidate).
4. **`/governance` Phase-2 verbatim CSS re-point** — governance config shape.
5. **`/tenant-settings` Phase-2 verbatim CSS re-point** — tenant admin shape.

User to pick direction. Rolling planning §6 — next sprint plan **NOT pre-written**.

---

## Q6 — Open items / Carryover

- **NEW**: `AD-Sprint-Plan-frontend-verbatim-css-repoint-shape-bimodal-watch` — 2-data-point bimodal signal needs 3rd validation; KEEP 0.50 baseline.
- **NEW (low priority)**: `AD-Tabs-Migration-To-MockupUi` — `frontend/src/components/ui/tabs.tsx` Sprint 57.19 vintage primitive still imported by other consumers; future sprint may migrate then delete.
- **Updated**: `AD-Sprint-Plan-frontend-verbatim-css-repoint-baseline-lift` (Sprint 57.31 NEW) — 2nd validation data point logged. 0.50 baseline still appropriate but bimodal-by-shape signal emerging.
- **Unchanged**: `AD-Orchestrator-Backend-Wire` (Phase 58+ scope).

Full updates posted to `claudedocs/1-planning/next-phase-candidates.md` Sprint 57.34 Carryover section.

---

## Q7 — Design note extract (spike sprint only)

**N/A** — Sprint 57.34 is a Phase-2 epic continuation (5th application of `frontend-verbatim-css-repoint` class), not a spike. No design note required per `.claude/rules/sprint-workflow.md` Step 5.5.

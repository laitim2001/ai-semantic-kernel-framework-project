# Sprint 57.45 — `/chat-v2` Inspector Tab Vocabulary Rename (NEAR-PARITY Quick Win)

> **Sprint type**: `frontend-refactor-mechanical` (3rd application — class baseline **0.80** per Sprint 57.16 AD-Sprint-Plan-13 lift; 0.50 was the iteration rule for 57.15+57.16 only, lifted to 0.80 for 3rd+ application)
> **Status**: Draft (pending user approval per `.claude/rules/sprint-workflow.md §6 Rolling Planning`)
> **Closes**: `AD-ChatV2-Inspector-Tab-Rename` — last 🟡 NEAR-PARITY route per drift audit 2026-05-25; **🎉 Phase-2 epic + NEAR-PARITY clean dual milestone** upon merge (22/22 PARITY)
> **Critical role**: **1st validation under newly tightened `agent_factor = 0.45`** per Sprint 57.44 retro Q4 structural decision (was 0.55 activated Sprint 57.42; tightened 2026-05-26 after 2 consecutive < 0.7 — Sprint 57.43=0.41 + Sprint 57.44≈0.20). Small-scope sprint chosen specifically for low class-baseline-drift risk.

---

## 0. Sprint Goal

Resolve `/chat-v2` Inspector tab vocabulary divergence per drift audit 2026-05-25 row 9 — bring production Inspector 4-tab labels into PARITY with the **canonical mockup source of truth**. Day 0 Prong 2 will resolve the **audit-report vs mockup-file divergence** (audit says mockup expects "Run / Tools / Memory / Verify"; current mockup file `page-chat.jsx:378-381` shows "Turn / Trace / Memory / Tree" which production already matches). Either outcome closes the NEAR-PARITY verdict: (a) rename production tabs to match the canonical audit-claimed mockup, OR (b) override audit row 9 as obsolete if mockup file is authoritative — both result in 22/22 PARITY.

Secondary goal: provide **1st validation data point under `agent_factor = 0.45`** to verify the Sprint 57.44 retro Q4 rollback rule decision.

---

## 1. Background

### 1.1 Phase-2 epic context (post Sprint 57.44)

- **21 PARITY + 1 NEAR-PARITY + 0 CATASTROPHIC** post Sprint 57.44 (Phase-2 epic FULL CLEAN milestone achieved).
- This sprint closes the last NEAR-PARITY → **22/22 PARITY + 0 NEAR-PARITY + 0 CATASTROPHIC** (full drift-audit clean).
- Per audit-report row 9: "tab name vocab divergence (1 component)"; row 117 recommends "30 min, `frontend-refactor-mechanical` 0.50" — this sprint applies class 0.80 per AD-Sprint-Plan-13 lift rule (3rd+ application).

### 1.2 The audit-vs-mockup-file divergence (Day 0 Prong 2 critical investigation)

**audit-report.md L37 + L93** (Sprint 57.22 comprehensive audit baseline):
> Mockup expects: `Run / Tools / Memory / Verify`
> Production has: `Turn / Trace / Memory / Tree`
> "Same components, different vocab. ~30 min rename."

**Current mockup file `reference/design-mockups/page-chat.jsx:378-381`**:
```
{ id: "turn", label: "Turn" },
{ id: "trace", label: "Trace" },
{ id: "memory", label: "Memory" },
{ id: "subagent", label: "Tree" },
```

**Production `frontend/src/features/chat_v2/components/inspector/ChatInspector.tsx:60-65`**:
```
{ id: "turn", label: "Turn" },
{ id: "trace", label: "Trace" },
{ id: "memory", label: "Memory" },
{ id: "tree", label: "Tree" },
```

Production matches the **mockup file labels exactly** (only the id of the 4th tab differs: "subagent" mockup vs "tree" production — both render same label "Tree"). Audit row 9's claim of "Run / Tools / Memory / Verify" mockup labels does NOT match the current mockup file.

**Day 0 Prong 2 resolution paths**:
- **Path A**: audit-report's claim is authoritative (mockup may have been updated post-audit OR audit author looked at canonical UX spec elsewhere) → rename production tabs to `Run / Tools / Memory / Verify`
- **Path B**: mockup file is authoritative (source of truth per `frontend-mockup-fidelity.md`) → production is already PARITY; close NEAR-PARITY by overruling audit row 9 with documentation correction

Path selection at Day 0; plan §3.x covers both branches.

### 1.3 `agent_factor = 0.45` 1st validation context

Per `.claude/rules/sprint-workflow.md §Active Agent Delegation Factor Modifier`:

- **Tightened** 2026-05-26 (Sprint 57.44 retro Q4) from 0.55 → 0.45 after 2 consecutive sprints < 0.7 (Sprint 57.43=0.41 + Sprint 57.44≈0.20)
- **Formula**: `committed = bottom_up × scope_class_multiplier × agent_factor` where `agent_factor = 0.45`
- **1st validation = this sprint MANDATORY**: per rollback rule, "If activated factor produces 2 sprints with ratio < 0.7 → tighten to 0.45"; this is the 1st post-tightening sprint
- **Predicted ratio**: Sprint 57.44 actual 0.20 at 0.55 → equivalent at 0.45 ≈ 0.24; still likely BELOW band — but small-scope sprint chosen specifically because class-baseline-drift risk is minimal (mechanical-refactor class is low-variance per Sprint 57.16 lesson)

### 1.4 Karpathy §2 simplicity guidance

This is a 1-component change. Per Karpathy §2:
> "200 lines能變50 lines 就重寫" / "不寫沒被問的功能"

If Path A (rename) → only `ChatInspector.tsx` L60-65 + corresponding Vitest spec (if exists; Day 0 Prong 2.5 grep). No tab content components rename (Inspector**Turn**.tsx etc. stay since they're internal symbol names per existing convention).

If Path B (mockup overrule) → **0 code change**; only audit-report.md row 9 edit + progress.md documentation.

---

## 2. User Stories

- **US-1** (Audit row 9 resolution)
  - As an operator viewing `/chat-v2`, I want the Inspector tabs to either (a) match the canonical mockup vocabulary "Run / Tools / Memory / Verify" if the audit is correct, OR (b) remain "Turn / Trace / Memory / Tree" if the mockup file is the source of truth and audit is obsolete — both paths close the drift-audit row 9 NEAR-PARITY verdict.
- **US-2** (`agent_factor = 0.45` 1st validation)
  - As the calibration matrix maintainer, I want Sprint 57.45 retro Q4 to record the 1st validation data point under tightened `agent_factor = 0.45` to verify the Sprint 57.44 retro Q4 rollback rule structural decision.
- **US-3** (Phase-2 epic + NEAR-PARITY clean dual milestone)
  - As the V2 ship maintainer, I want the audit-report.md row 9 closed (either via rename OR audit-overrule documentation) so the Phase-2 mockup-fidelity epic + NEAR-PARITY shelf both reach 0 outstanding routes = **22/22 PARITY**.

---

## 3. Technical Specifications

### 3.1 Day 0 Prong 2 — audit-vs-mockup-file resolution

Three grep-based content checks:

1. **Re-read** `reference/design-mockups/page-chat.jsx:370-390` (ChatInspector mockup section) — confirm current labels
2. **Grep** repo-wide for "Run.*Tools.*Memory.*Verify" — find if any other mockup file / archive / docs reference contains this vocab (the audit's source)
3. **Grep** styles-mockup.css / mockup CSS for inspector tab counters / counts that might bias the vocab choice

Decision at Day 0 closeout: Path A or Path B (or pause-and-ask-user if unresolvable from grep evidence).

### 3.2 Path A (Rename production tabs)

If Path A: 1-file rename in `ChatInspector.tsx:60-65` + `id` enum at L53.

```typescript
// L53 — type
type InspectorTabId = "run" | "tools" | "memory" | "verify";

// L60-65 — labels
const TAB_ITEMS: TabItem[] = [
  { id: "run", label: "Run" },
  { id: "tools", label: "Tools" },
  { id: "memory", label: "Memory" },
  { id: "verify", label: "Verify" },
];
```

Plus dispatch updates at L93-117 — `tab === "run"` etc. + ComingSoonInspectorTab `name` props ("Run" / "Tools" / "Verify" replacing "Trace" / "Tree"). `InspectorTurn` import stays (component file name unchanged — pure internal symbol).

**Day 0 Prong 2.5** scope: grep `chat-v2.*Inspector|"turn".*"trace".*"memory".*"tree"|inspector.*tab` in test files to identify Vitest specs that test current tab labels (likely `ChatInspector.test.tsx` if exists).

### 3.3 Path B (Audit overrule)

If Path B: **0 code change**. Edits limited to:
- `audit-report.md` row 9 update: NEAR-PARITY → ✅ PARITY (audit overruled — mockup file is canonical source of truth; production already matches)
- Possibly add Path B rationale paragraph to audit-report Key findings section
- Progress.md Day 1 entry documents the audit-vs-mockup-file divergence + Path B selection reasoning

### 3.4 Verbatim-CSS protocol

HEX_OKLCH_BASELINE estimated **+0 bump** (no new oklch literals in either path; production already mockup-aligned in styling). 0 new mockup-ui primitive lifts.

### 3.5 Vitest spec impact

- Path A: existing Vitest specs that assert tab labels need update (Day 0 Prong 2.5 grep identifies exact count; estimated 1-2 spec files based on past spec coverage patterns)
- Path B: 0 Vitest changes

### 3.6 Audit report update

Row 9 verdict update in either path:
- Path A: 🟡 NEAR-PARITY → ✅ PARITY (rename completed Sprint 57.45)
- Path B: 🟡 NEAR-PARITY → ✅ PARITY (audit overruled; mockup-file canonical)

Plus summary update: 21→22 PARITY + 1→0 NEAR-PARITY + 0 CATASTROPHIC (Phase-2 epic + NEAR-PARITY clean DUAL milestone).

### 3.7 route-sweep before/after

`frontend/scripts/route-sweep.mjs` re-point OUT_DIR to `sprint-57-45-chatv2-inspector-tab-rename` slug. Day 0 + Day 2.5 sweep:
- Path A: expect 1 INTENDED CHANGED `/chat-v2` (tab label text differs in screenshot)
- Path B: expect 0 unintended CHANGED (no code change)

---

## 4. File Change List

### Path A (Rename) — MODIFIED files

- `frontend/src/features/chat_v2/components/inspector/ChatInspector.tsx` (1-line type + 5-line TAB_ITEMS + 4-line dispatch + ComingSoonInspectorTab `name` props ~12 lines total edited)
- `frontend/tests/unit/chat_v2/inspector/ChatInspector.test.tsx` (if exists — TBD Day 0 Prong 2.5 grep; likely 2-4 test assertions update)
- `claudedocs/5-status/drift-audit-2026-05-25/audit-report.md` (~5 edits: row 9 verdict + summary 21→22 + Key findings paragraph + Effort estimate strike + Recommendations renumber)
- `frontend/scripts/route-sweep.mjs` (OUT_DIR slug re-point + 1-line MHist entry)
- `.claude/rules/sprint-workflow.md` (matrix MHist + `agent_factor` 1st post-tightening validation entry)

### Path B (Audit overrule) — MODIFIED files

- `claudedocs/5-status/drift-audit-2026-05-25/audit-report.md` (~5 edits same as Path A but with Path B rationale)
- `frontend/scripts/route-sweep.mjs` (OUT_DIR slug re-point + 1-line MHist entry)
- `.claude/rules/sprint-workflow.md` (matrix MHist + `agent_factor` validation entry)

### NEW files

None (no new components either path).

### DELETED files

None.

**Net Day 1 delta estimate**:
- Path A: ~+15 / ~-15 ≈ NET ~0 lines (pure rename in 1-2 files)
- Path B: ~+5 / ~-2 ≈ NET +3 lines (audit-report.md update only)

---

## 5. Acceptance Criteria

- **AC1**: Day 0 Prong 2 audit-vs-mockup-file resolution documented in progress.md with Path A/B decision + rationale.
- **AC2**: `/chat-v2` drift audit verdict 🟡 NEAR-PARITY → ✅ PARITY (audit-report.md row 9 update); summary 21→22 PARITY / 1→0 NEAR-PARITY / 0 CATASTROPHIC. **🎉 Phase-2 epic + NEAR-PARITY clean DUAL milestone**.
- **AC3**: If Path A — Vitest delta updated (specs that asserted prior tab labels now assert new labels); all GREEN. If Path B — Vitest 561 unchanged.
- **AC4**: 24-route sweep — Path A: expect 1 INTENDED CHANGED `/chat-v2` + ≤ 3 sub-300-byte noise + 0 unintended regressions. Path B: expect 0 unintended CHANGED (≤ 3 noise tolerated).
- **AC5**: HEX_OKLCH_BASELINE unchanged (47 from Sprint 57.44 closeout); no new oklch literals.
- **AC6**: Sprint plan §Workload retro records `agent-delegated: yes` + `actual/committed-with-agent-factor` ratio as **1st validation data point** under newly tightened `agent_factor = 0.45` per `.claude/rules/sprint-workflow.md §Active Agent Delegation Factor Modifier`. Single-data-point caution applies; if ratio < 0.7 OR > 1.20 → Sprint 57.46 retro flags for 2nd-validation evaluation.

---

## 6. Deliverables

- [ ] **US-1** Audit row 9 resolution — Path A rename OR Path B overrule documented + executed
- [ ] **US-2** `agent_factor = 0.45` 1st validation data point recorded in retro Q4
- [ ] **US-3** Phase-2 epic + NEAR-PARITY clean DUAL milestone — 22/22 PARITY achieved

---

## 7. Dependencies & Risks

### Dependencies

- Sprint 57.44 closeout (Phase-2 epic FULL CLEAN baseline)
- `frontend-mockup-fidelity.md` canonical source-of-truth rule (mockup file is authoritative per recent rule version)

### Risks

| Risk class | Symptom | Workaround | Long-term fix |
|------------|---------|------------|---------------|
| **Audit vs mockup-file ambiguity** | Day 0 Prong 2 can't resolve cleanly (e.g. multiple mockup versions / archived sources) | Pause Day 0; ask user for guidance on which source is canonical | Document canonical source rule in `frontend-mockup-fidelity.md` |
| **`agent_factor = 0.45` 1st validation < 0.7 again** | Continued mockup-direct-port speedup undercounted | Sprint 57.46 retro evaluates; if < 0.7 → propose 0.45 → 0.35 OR Option B per-class split | Open `AD-Sprint-Plan-Agent-Delegation-Factor-3rd-Recalibration` Sprint 57.46 |
| **Path A Vitest spec breakage cascade** | Renaming tab IDs ("turn" → "run" etc.) breaks spec selectors | Day 0 Prong 2.5 catches affected specs; Day 1 same-commit update | n/a |

### Carryover from Sprint 57.44 (still open)

- 🔴 `AD-AdminTenants-Backend-Schema-Extension` BLOCKING Phase 58+ (independent track)
- `AD-TenantSettings-Backend-Schema-Extension` Phase 58+ (independent track)
- `AD-MockupCapture-04-MOCKUP-tenant-settings` (Option C byte-proxy deferred — same blocker as AD-MockupCapture-03)
- `AD-Sprint-Plan-Agent-Delegation-Factor-2nd-Recalibration` — executed in this sprint Q4 retro (1st validation under 0.45)
- `AD-TenantSettings-E2E-Refresh` Phase 58+

---

## 8. Workload Calibration (four-segment form per `agent_factor = 0.45` tightened)

> **Bottom-up est ~30-45 min → class-calibrated commit ~24-36 min (mult 0.80 per AD-Sprint-Plan-13 lift) → agent-adjusted commit ~11-16 min (agent_factor 0.45)**

### Bottom-up estimate (~30-45 min, human-rewrite cadence)

- Day 0 verify (3-prong + audit-vs-mockup grep + before-sweep + decision): ~10 min
- Day 1 Path A (rename `ChatInspector.tsx` + 1-2 Vitest spec updates + lint): ~10-15 min
  - OR Day 1 Path B (audit-report update only): ~5 min
- Day 2.5 sweep + 3-way evidence: ~5-10 min
- Day 3 retro + matrix MHist + closeout: ~10-15 min
- Total bottom-up ~30-45 min

### Class calibration (`frontend-refactor-mechanical` 0.80 per AD-Sprint-Plan-13)

30-45 × 0.80 = **24-36 min class-calibrated commit**.

3rd application of class (post Sprint 57.15 / 57.16 both at 0.50 baseline). Per AD-Sprint-Plan-13:
> "The next (3rd+) `frontend-refactor-mechanical` sprint uses 0.80 (near the top of the band like `medium-backend` 0.80 — a mechanical class belongs near the top, not the cautious mid-band)"

### Agent-delegation calibration (`agent_factor = 0.45` tightened)

24-36 × 0.45 = **~11-16 min agent-adjusted commit**.

Possibly executed **without code-implementer agent delegation** (sprint is small enough that I can do it manually; "agent-delegated: no" tag would apply, reverting to `agent_factor = 1.0` = ~24-36 min committed). Day 0 decision.

### 1st validation data point recording (MANDATORY at Day 3 retro Q4)

Per `.claude/rules/sprint-workflow.md §Active Agent Delegation Factor Modifier`:

- Sprint 57.45 ratio actual/committed-with-agent-factor will be recorded
- This is the 1st post-tightening sprint under 0.45
- Single-data-point caution rollback rule applies; if ratio < 0.7 OR > 1.20 → Sprint 57.46 retro evaluates 2nd validation
- Documented in `§Active block` Activation history Sprint 57.45 entry

---

## 9. Carryover Audit Debt (anticipated; finalized at Day 3 retro)

### Anticipated NEW carryovers from this sprint

- Likely `AD-Sprint-Plan-Agent-Delegation-Factor-3rd-Recalibration` if Sprint 57.45 ratio also < 0.7 (Sprint 57.46 evaluates 0.45 → 0.35 OR Option B per-class split)
- Possibly `AD-MockupFidelity-CanonicalSource-Rule` if Day 0 Prong 2 reveals audit-vs-mockup-file divergence requires `frontend-mockup-fidelity.md` rule clarification

### Carried from Sprint 57.44 (still open; not addressed this sprint)

- 🔴 `AD-AdminTenants-Backend-Schema-Extension` BLOCKING Phase 58+
- `AD-TenantSettings-Backend-Schema-Extension` Phase 58+
- `AD-MockupCapture-03-MOCKUP-admin-tenants` + `AD-MockupCapture-04-MOCKUP-tenant-settings`
- `AD-TenantSettings-E2E-Refresh` Phase 58+

### Closing milestone

🎉 **Phase-2 epic + NEAR-PARITY clean DUAL milestone** upon merge — **22/22 PARITY + 0 NEAR-PARITY + 0 CATASTROPHIC**. Full drift-audit-2026-05-25 cleared.

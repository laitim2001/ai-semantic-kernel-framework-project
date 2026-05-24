# Sprint 57.36 — AD-Loop-Debug-Verbatim-Repoint

**File**: `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-36-plan.md`
**Purpose**: Plan for Sprint 57.36 — **7th Phase-2 per-page verbatim-CSS re-point** on `/loop-debug` route (`LoopVisualizer.tsx` single-file scope). **3rd non-rich-dashboard shape** in epic; **3rd validation data point** for the shape-bimodal hypothesis (`AD-Sprint-Plan-frontend-verbatim-css-repoint-shape-bimodal-watch` Sprint 57.34 NEW; weakened Sprint 57.35); **first 1-file non-rich sprint after the 8-file scale outlier** — provides decisive signal discriminating shape vs scale variance drivers.
**Category**: Sprint planning / Phase 57+ Frontend SaaS — Phase-2 per-page re-point epic
**Scope**: Phase 57+ Frontend SaaS — Phase-2 epic, 7th application; 3rd non-rich-dashboard shape (operator debug viewer)
**Created**: 2026-05-24
**Last Modified**: 2026-05-24
**Status**: Draft → awaiting user approval

> **Modification History**
> - 2026-05-24: Initial draft (Sprint 57.36 Day 0) — `/loop-debug` Phase-2 verbatim re-point per Sprint 57.35 retro Q5 #1 candidate; 3rd shape-validation data point

---

## 0. Sprint Goal

Land the **7th Phase-2 per-page verbatim-CSS re-point** on the `/loop-debug` route. Single-file scope = `frontend/src/features/orchestrator-loop/components/LoopVisualizer.tsx` (209 lines; the page wrapper `pages/loop-debug/index.tsx` is a 50-line 3-line-body shell and stays untouched). Re-point the visual layer to **verbatim mockup classes** from `reference/design-mockups/page-governance.jsx:33-263` (mockup component is `LoopDebug` + `LoopDebugHeader` + `EventRow` + `LoopInspector`).

The mockup `LoopDebug` widget bundles features the production component does not yet have (full playback / scrubber / speed control / per-category filter pills / 2-column inspector pane with HITL policy + raw payload). Per user-selected **Option A** at sprint kickoff: this sprint does **NOT** rebuild those features — they require backend SSE-event persistence which is explicitly Phase 58+ scope per Sprint 57.12 AP-6 deferral (`useChatStore.rawEvents` is in-memory live session only). Instead this sprint:

1. Verbatim-ports the **visual layer** of what we already render — per-turn buckets + event rows + turn header — to mockup classes (`.loop-canvas` / `.loop-track` / `.loop-turn` / `.loop-turn-head` / `.loop-turn-body` / `.event-row` / `.ev-dot` / `.ev-type` / `.ev-detail` / `.ev-timing` / `.turn-no`).
2. Adds an **AP-2 `BackendGapBanner`** above the visualizer in standalone mode honestly disclosing the playback / scrubber / inspector pane / filter pills are Phase 58+ pending SSE event persistence.
3. Preserves the **dual-mount behavior** (`mode="inline"` for chat-v2 panel + `mode="standalone"` for `/loop-debug` page) — the chat-v2 inline mount must NOT regress (was Sprint 57.30 Phase-2 ship).

This is the **3rd non-rich-dashboard shape** in the Phase-2 epic (1st = Sprint 57.34 `/orchestrator` config/tabbed-forms 1-file ratio ≈1.0 in band; 2nd = Sprint 57.35 AuthShell + 7 auth routes 8-file batched ratio ~1.7 ABOVE band) — **decisive 3rd data point discriminating bimodal-by-shape vs scale-overhead hypotheses** (Sprint 57.35 Day 4 carryover ADs). Single-file scope (like 57.34) — if ratio lands in [0.85, 1.20] band, bimodal hypothesis stays WEAKENED and scale-overhead becomes plausible primary variance driver.

---

## 1. Background

### 1.1 Why Sprint 57.36 (this sprint)

Per Sprint 57.35 retrospective Q5 candidate list, `/loop-debug` is the **#1 priority Phase-2 re-point pickup** because:

1. **3rd shape-validation data point** — bimodal-by-shape hypothesis (Sprint 57.34 NEW) was weakened (not rejected) by Sprint 57.35 8-file scale outlier. A clean single-file non-rich data point is needed.
2. **Operator-facing**: `/loop-debug` is debug visibility for the TAO/ReAct loop state machine; high-leverage for operations observability.
3. **Single-file scope**: cleanest possible data point — only `LoopVisualizer.tsx` (209 lines). Dual-mount means chat-v2 inline benefits too (cascade win).
4. **Mockup canonical source clear**: `page-governance.jsx:33-263` — uses well-documented `.loop-canvas` / `.loop-track` / `.loop-turn` classes that already exist in `styles-mockup.css` (per Sprint 57.28 verbatim copy).

### 1.2 Mockup source mapping (Day 0 Prong 2 confirmed)

`reference/design-mockups/page-governance.jsx`:

| Mockup component | Mockup file:line | Production target | Disposition |
|------------------|------------------|-------------------|-------------|
| `LoopEvents` fixture | L5-31 | n/a | mockup-only demo fixture; production uses `useChatStore.rawEvents` |
| `LoopDebug` (main shell) | L33-116 | `LoopVisualizer.tsx` (standalone mode) | re-point: wrap in `.loop-canvas` 2-col + `.loop-track` left |
| `LoopDebugHeader` (controls) | L118-185 | n/a (production header is summary only) | AP-2 banner: playback / scrubber / filters Phase 58+ |
| `EventRow` (per-event) | L187-212 | event row in `LoopVisualizer.tsx` | re-point: `.event-row` + `.ev-dot` + `.ev-type` + `.ev-detail` + `.ev-timing` |
| `LoopInspector` (right pane) | L214-263 | n/a (production has no inspector) | AP-2 banner: inspector pane Phase 58+; standalone shows empty placeholder pane |
| `KvRow` helper | L265-270 | n/a | inspector-pane-only helper; not needed this sprint |

Mockup classes (defined in `reference/design-mockups/styles.css` → byte-identical-copied to `frontend/src/styles-mockup.css` per Sprint 57.28 verbatim foundation):

- Layout: `.loop-canvas`, `.loop-track`, `.loop-inspector`
- Per-turn: `.loop-turn`, `.loop-turn-head`, `.loop-turn-body`, `.turn-no`
- Per-event: `.event-row`, `.ev-dot`, `.ev-type`, `.ev-detail`, `.ev-timing`
- Existing shared: `.row`, `.col`, `.grow`, `.mono`, `.subtle`, `.muted`, `.page-title`, `.page-sub`, `.route-pill`

Mockup tokens (already in `styles-mockup.css`):
- Foreground: `--fg-muted`, `--fg-subtle`
- Background: `--bg-1`, `--bg-2`
- Border: `--border`
- Per-category: `--primary`, `--thinking`, `--tool`, `--memory`, `--success`, `--warning`, `--info`, `--primary-soft`, `--primary-soft-2`
- Mono: `--font-mono`

### 1.3 Scope boundaries

**IN scope**:
- `frontend/src/features/orchestrator-loop/components/LoopVisualizer.tsx` — verbatim CSS re-point of standalone + inline modes.
- AP-2 `BackendGapBanner` integration in standalone mode disclosing Phase 58+ deferred features.
- `frontend/src/pages/loop-debug/index.tsx` — only touch if AP-2 banner needs to live in page wrapper rather than visualizer (decided Day 0 Prong 1).
- Vitest spec updates if mockup-class adoption changes DOM queries.
- 22-route regression sweep (before / after) including `/chat-v2` (dual-mount cascade verify) + `/loop-debug`.

**OUT of scope** (Phase 58+ per AP-6 / Sprint 57.12 deferral):
- Real playback / scrubber / speed control — requires backend SSE event persistence (`loop_event` table).
- Cursor-based event selection — requires playback foundation.
- Per-category filter pills with toggleable visibility — feasible w/o backend but is a feature, not a re-point.
- `LoopInspector` right pane with HITL Policy + Raw payload + KvRow detail — requires event-detail backend endpoint.
- `LoopDebugHeader` title block (`Loop Visualizer · Session sess_xxx · /loop-debug · streaming/replay Badge`) — partial impl possible if session id is in `useChatStore`; verify Day 0.

**OUT of scope (other Phase-2 epic routes)**:
- `/state-inspector`, `/memory`, `/governance`, `/admin-tenants`, `/tenant-settings`, `/compaction` — separate sprints.

### 1.4 Class baseline — `frontend-verbatim-css-repoint` 0.50 (7th application; 3rd shape-validation data point)

Per Sprint 57.35 retro Q2 evidence + Sprint 57.34 calibration matrix row in `.claude/rules/sprint-workflow.md`. Baseline lifted from 0.60 → 0.50 in Sprint 57.31 Day 4 per `AD-Sprint-Plan-frontend-verbatim-css-repoint-baseline-lift`. KEEP 0.50 per `When to adjust` 3-sprint window rule.

HYBRID weighted blend for Sprint 57.36 (single-file scope; closer to 57.34 than 57.35):

| Component | Class | Multiplier | Weight |
|-----------|-------|------------|--------|
| Day-0 三-prong + before-baseline + mockup mapping | `audit-cycle` | 0.85 | ~15% |
| Day 1 — LoopVisualizer.tsx verbatim port (standalone + inline) | `frontend-verbatim-css-repoint` | 0.50 | ~35% |
| Day 2 — AP-2 BackendGapBanner integration + Vitest spec update | `frontend-verbatim-css-repoint` | 0.50 | ~20% |
| Day 3 — 22-route sweep + fidelity verify + drift handle | `frontend-verbatim-css-repoint` | 0.50 | ~15% |
| Day 4 — Closeout + retro + memory + push + PR | `closeout` | 0.80 | ~15% |
| **HYBRID blended baseline** | | **≈ 0.55** | |

Bottom-up estimate:
- Day 0: ~0.75 hr (single mockup file mapping; fewer files than Sprint 57.35 = 8 files; closer to 57.34 = 1 file)
- Day 1 (verbatim port): ~1.5 hr
- Day 2 (AP-2 banner + Vitest): ~1 hr
- Day 3 (sweep + drift): ~0.5 hr
- Day 4 (closeout): ~1 hr
- **Total: ~4.75 hr**

Calibrated commit: **~2.4 hr** (multiplier 0.50). Day 1-2 will be agent-delegated per Sprint 57.34/57.35 model.

### 1.5 Shape-vs-scale 3rd-data-point evaluation criteria

| Sprint 57.36 ratio range | Interpretation | Action for AD-Sprint-Plan-frontend-verbatim-css-repoint-shape-bimodal-watch + scale-overhead-watch |
|--------------------------|----------------|--------------------------------------------------------------------------|
| **0.85 — 1.20 (in band)** | Shape (non-rich, single-file) is NOT the variance driver; **scale-overhead hypothesis** strengthens — file-count + Vitest-spec-update overhead is the dominant secondary signal | KEEP 0.50 baseline; close `shape-bimodal-watch` (REJECTED 2-data confirms in-band); promote `scale-overhead-watch` to primary watch (need 1 more multi-file data point to validate file-count surcharge proposal) |
| **0.50 — 0.84 (below band)** | Shape MAY still be variance driver (3-pt non-rich would be 1.0 + 1.7 + below = mean ≈ 0.9, inconclusive) | KEEP 0.50; require Sprint 57.37+ 4th non-rich data point to discriminate |
| **1.21 — 1.50 (above band)** | Single-file non-rich also above band → variance is class-wide; **0.50 → 0.40 lift candidate** | propose `AD-Sprint-Plan-frontend-verbatim-css-repoint-baseline-lift-round-2` |
| **> 1.50 (significantly above)** | Multi-data-point class-wide drift | trigger class split or major lift |

---

## 2. User Stories

### US-1 — Verbatim mockup CSS classes on standalone mode layout

**As an operator** browsing `/loop-debug`,
**I want** the page to look pixel-faithful to `reference/design-mockups/page-governance.jsx` LoopDebug,
**so that** I can rely on a single canonical visual contract (and the production styling matches design QA).

**Acceptance**:
- `LoopVisualizer mode="standalone"` body root uses `.loop-canvas` class wrapping `.loop-track` (left rail) + placeholder `.loop-inspector` (right pane).
- Each turn bucket renders with `.loop-turn` + `.loop-turn-head` + `.loop-turn-body` classes; turn number badge uses `.turn-no` class.
- Each event row uses `.event-row` + `.ev-dot` + `.ev-type` + `.ev-detail` + `.ev-timing` classes.
- All colors come from CSS vars (`--primary`, `--thinking`, `--tool`, `--memory`, `--success`, `--warning`, `--info`) — zero hardcoded hex/oklch (passes `check-mockup-fidelity.mjs` Guard 2 baseline).

### US-2 — AP-2 BackendGapBanner discloses Phase 58+ deferred features

**As an operator** observing `/loop-debug`,
**I want** an honest visible banner explaining playback / scrubber / inspector pane / filter pills are deferred,
**so that** I don't expect non-existent features (matches Sprint 57.24 + 57.27 AP-2 transparency precedent).

**Acceptance**:
- AP-2 `BackendGapBanner` renders above the visualizer in standalone mode only (inline mode = chat-v2 already has its own header context; no banner needed).
- Banner copy specifically names the deferred features + the Phase 58+ deferral reason (SSE event persistence).
- Banner does NOT render in `mode="inline"` (would clutter chat-v2 panel).

### US-3 — Inline mode (chat-v2 cascade) preserves Sprint 57.30 ship state

**As a chat-v2 user** with the inline LoopVisualizer panel open,
**I want** the panel layout to remain compact (no inspector right pane, no banner clutter),
**so that** the Sprint 57.30 `/chat-v2` Phase-2 ship state is not regressed.

**Acceptance**:
- `mode="inline"` does NOT wrap in `.loop-canvas` 2-col layout; uses single-column compact layout.
- `mode="inline"` reuses `.loop-turn` + `.event-row` mockup classes for visual consistency with standalone, but layout shell stays compact.
- 22-route sweep `/chat-v2` after-screenshot is byte-equivalent to before (or visual delta ≤ ε within mockup-faithful range).

### US-4 — Vitest specs preserve behavioral intent across class re-naming

**As a dev** running `npm run test`,
**I want** all LoopVisualizer-related Vitest specs to pass against the new mockup classes,
**so that** the test contract is preserved.

**Acceptance**:
- Any spec that selects by class name updated to mockup class equivalents.
- Behavioral test intent preserved (turn count / event count / error state rendering / dual-mount mode prop respect).
- `npm run test` baseline preserved (456 / 456 from Sprint 57.35, or +N if new specs added for AP-2 banner).

### US-5 — Drift findings catalogued + agent-handover preserved

**As a maintainer**,
**I want** all Day 0-3 drift findings (D-DAY0-N, D-DAY1-N, etc.) catalogued in progress.md,
**so that** future audits can trace what the plan said vs what reality forced.

**Acceptance**:
- Each drift gets ID + Finding + Implication entry in progress.md.
- Plan §Risks updated (not §Spec) per anti-pattern AP-2 audit trail rule.
- Agent-delegation Day 1-2 hands back agent narrative for Day 4 retro reuse.

---

## 3. Technical Specifications

### 3.1 Dual-mount strategy

`LoopVisualizer` is mounted in two contexts (per Sprint 57.12 Day 2 / US-4 ship):

| Mode | Mount point | Layout target |
|------|-------------|---------------|
| `mode="standalone"` | `pages/loop-debug/index.tsx` (Sprint 57.12) | Full screen 2-col `.loop-canvas` per mockup; AP-2 banner above; placeholder inspector right pane (mockup `LoopInspector` deferred) |
| `mode="inline"` | `features/chat_v2/components/...` (Sprint 57.30 ship) | Compact 1-col panel inside chat-v2 right rail; no banner; no inspector pane |

**Implementation pattern**: branch the JSX wrapper conditional on `mode`, share inner turn/event rendering primitives.

```tsx
// Pseudocode (final implementation by code-implementer agent)
if (mode === "standalone") {
  return (
    <>
      <BackendGapBanner ... />
      <div className="loop-canvas">
        <div className="loop-track">{turnsRender}</div>
        <aside className="loop-inspector">
          {/* AP-2: inspector pane deferred Phase 58+ */}
          <EmptyInspectorPlaceholder />
        </aside>
      </div>
    </>
  );
}
return <div className="loop-track" data-mode="inline">{turnsRender}</div>;
```

### 3.2 Mockup class adoption inventory

From mockup L33-212:

| Mockup class | Used in | Production adoption |
|--------------|---------|---------------------|
| `.loop-canvas` | shell wrapper (2-col) | standalone mode only |
| `.loop-track` | left scroll rail | both modes |
| `.loop-inspector` | right pane | standalone (placeholder) |
| `.loop-turn` | per-turn container | both modes; reuse `data-status` attr from mockup L76 |
| `.loop-turn-head` | turn header row | both modes |
| `.loop-turn-body` | event list | both modes |
| `.turn-no` | turn number pill | both modes |
| `.event-row` | per-event row | both modes |
| `.ev-dot` | per-event tone dot | both modes |
| `.ev-type` | event type label | both modes |
| `.ev-detail` | event description | both modes |
| `.ev-timing` | event timing | both modes |
| `.mono`, `.subtle`, `.muted` | typography | both modes |

### 3.3 AP-2 BackendGapBanner integration

Reuse the existing `BackendGapBanner` component (Sprint 57.24+ established):

```tsx
<BackendGapBanner
  title="Playback / inspector deferred Phase 58+"
  body="The mockup LoopDebug includes playback controls (scrubber / play / pause / speed), per-category filter pills, and a 2-column inspector pane with HITL policy + raw event payload. These require backend SSE event persistence (loop_event table) which is Phase 58+ scope per Sprint 57.12 AP-6 deferral. This view shows the in-memory live session only."
  href="#"  // or link to Phase 58 roadmap entry if available
/>
```

If `BackendGapBanner` API expects different prop shape, adapt; agent will confirm via Day 0 Prong 1.

### 3.4 Token color mapping (event tone → CSS var)

Mockup L189-191 `toneMap`:

```js
{ fg: "--fg-muted", primary: "--primary", thinking: "--thinking", tool: "--tool",
  memory: "--memory", success: "--success", warning: "--warning" }
```

Production LoopVisualizer L23-26 currently uses red/amber/gray left-border encoding. Replace with mockup `toneMap` per-event-type → `var(--X)`-driven `.ev-dot` + `.ev-type` color (matches mockup verbatim).

### 3.5 Standalone inspector placeholder

For US-1 acceptance criterion of 2-col layout, the right `.loop-inspector` pane needs SOME content. Choose minimal placeholder:

```tsx
<aside className="loop-inspector">
  <div style={{ padding: 16, color: "var(--fg-subtle)", textAlign: "center" }}>
    Inspector pane deferred — see banner above.
  </div>
</aside>
```

Or render mockup-faithful `.thin-rule` separator + "no event selected" empty state for closer fidelity. Final choice: code-implementer agent picks per visual review.

---

## 4. File Change List

**Modified** (1 file):
- `frontend/src/features/orchestrator-loop/components/LoopVisualizer.tsx` — verbatim CSS re-point + dual-mount branching + AP-2 banner integration in standalone mode

**Modified, only if needed** (1 file, Day 0 Prong 1 confirms):
- `frontend/src/pages/loop-debug/index.tsx` — only if AP-2 banner needs to live in page wrapper rather than visualizer (likely NO change; visualizer is the natural home)

**Updated** (≤2 spec files):
- `frontend/src/features/orchestrator-loop/components/LoopVisualizer.test.tsx` (if exists; otherwise no spec touch) — update class-name selectors to mockup classes
- Any chat-v2 spec touching LoopVisualizer inline rendering — update class selectors

**Updated** (1 CI guard config):
- `frontend/scripts/check-mockup-fidelity.mjs` — `HEX_OKLCH_BASELINE` re-evaluate (if Day 0 Prong 2 finds production LoopVisualizer has hardcoded hex/oklch, baseline may drop; if mockup verbatim adds new `oklch(from var(--X) l c h / X)` patterns, baseline may rise — confirm Day 3 actual offender count)

**Re-pointed** (1 OUT_DIR config):
- `frontend/scripts/route-sweep.mjs` — `OUT_DIR` re-pointed to `sprint-57-36-loop-debug-repoint` per Sprint 57.31-35 pattern

**New** (0 files):
- No new components; no new specs added (US-4 spec preservation, not new spec authoring)

---

## 5. Acceptance Criteria

| # | Criterion | Verify |
|---|-----------|--------|
| AC-1 | Standalone mode wraps `.loop-canvas` 2-col layout per mockup L56 | Visual diff vs mockup; DOM contains `<div class="loop-canvas">` |
| AC-2 | All turn buckets use `.loop-turn` + `.loop-turn-head` + `.loop-turn-body` | DOM query; Vitest spec selector update |
| AC-3 | All event rows use `.event-row` + `.ev-dot` + `.ev-type` + `.ev-detail` + `.ev-timing` | DOM query; Vitest spec selector update |
| AC-4 | Tone colors come from CSS vars (`--primary` / `--thinking` / `--tool` / `--memory` / `--success` / `--warning`) | `check-mockup-fidelity.mjs` Guard 2 baseline preserved or lifted with reason |
| AC-5 | AP-2 BackendGapBanner renders above visualizer in standalone mode only | DOM presence in `/loop-debug` route; absent in `/chat-v2` inline mount |
| AC-6 | `/chat-v2` inline LoopVisualizer mount NOT regressed | 22-route sweep diff: `/chat-v2` before/after ≤ ε visual delta |
| AC-7 | Vitest 456+ passing (baseline preserved or +N with new AP-2 banner spec) | `npm run test` exit 0 |
| AC-8 | `check-mockup-fidelity.mjs` exit 0 | CI guard pass |
| AC-9 | 22-route sweep: 0 catastrophic regression; 0 structural regression | Before/after manual diff (Sprint 57.34/57.35 process) |

---

## 6. Deliverables

- [ ] sprint-57-36-plan.md (this file)
- [ ] sprint-57-36-checklist.md
- [ ] frontend/src/features/orchestrator-loop/components/LoopVisualizer.tsx (verbatim re-pointed)
- [ ] frontend/scripts/route-sweep.mjs (OUT_DIR re-pointed)
- [ ] frontend/scripts/check-mockup-fidelity.mjs (HEX_OKLCH_BASELINE re-evaluated)
- [ ] Vitest specs updated for mockup class selectors (if applicable)
- [ ] 22-route before sweep + after sweep + diff report
- [ ] docs/03-implementation/agent-harness-execution/phase-57/sprint-57-36/progress.md
- [ ] docs/03-implementation/agent-harness-execution/phase-57/sprint-57-36/retrospective.md
- [ ] memory/project_phase57_36_loop_debug_repoint.md + 1-line MEMORY.md pointer
- [ ] Calibration matrix updated (`.claude/rules/sprint-workflow.md` §Scope-class multiplier matrix — 7th data point for `frontend-verbatim-css-repoint`)
- [ ] PR opened against main

---

## 7. Risks & Mitigations

| # | Risk | Likelihood | Mitigation |
|---|------|------------|------------|
| R-1 | Dual-mount cascade — chat-v2 inline panel regresses when shared class re-named | Medium | Day 1 agent task: explicit `mode="inline"` branch test; Day 3 22-route sweep with `/chat-v2` diff |
| R-2 | mockup `.loop-canvas` / `.loop-track` / `.loop-inspector` classes not in `styles-mockup.css` (Day 0 Prong 1 catches) | Low | Sprint 57.28 byte-identical copy + mockup source verified Day 0; if missing → must add to verbatim copy (would block — escalate before Day 1) |
| R-3 | `BackendGapBanner` component API may have changed since Sprint 57.27 (last AP-2 banner reuse) | Low | Day 0 Prong 2: grep BackendGapBanner current shape + recent caller |
| R-4 | Vitest spec already broken from prior sprint (not class-name driven) | Low | Day 0 Step 3: run `npm run test` to confirm 456/456 baseline before Day 1 |
| R-5 | Event-tone mapping changes user-perceived semantics (e.g. red border for is_error removed) | Medium | Preserve current behavioral cues via mockup `--warning` / `--danger` color tokens; AP-2 banner can also note any UX shift |
| R-6 | `useChatStore.rawEvents` empty state — visualizer shows empty + AP-2 banner may look redundant | Low | Empty state copy adjusts: "no live session events yet" + AP-2 banner stays for backend-gap honesty |
| R-7 | Agent-delegation Day 1-2 ratio variance (proven 2× but small sample) | Low | Day 4 retro Q2 calibration update; if ratio > 1.20 propose AD addition to existing watch |
| R-8 | Recurring Risk Class A — paths-filter vs `required_status_checks` (CI infra; Sprint 53.7+ §Common Risk Classes) | Low | Touch `.github/workflows/backend-ci.yml` header comment if needed to trigger backend-ci context required by branch protection |

---

## 8. Workload

**Bottom-up est** ~4.75 hr → **calibrated commit** ~2.4 hr (multiplier 0.50; HYBRID ≈ 0.55 if exact)

### Day-by-day allocation

| Day | Theme | Bottom-up | Calibrated | Notes |
|-----|-------|-----------|------------|-------|
| Day 0 | Plan + Checklist + 三-prong + before baseline + mockup mapping | ~0.75 hr | ~0.6 hr (audit 0.85) | Single file → faster than 57.35 (8 files) |
| Day 1 | LoopVisualizer.tsx verbatim port (standalone + inline) | ~1.5 hr | ~0.75 hr | Agent-delegated |
| Day 2 | AP-2 BackendGapBanner + Vitest spec | ~1 hr | ~0.5 hr | Agent-delegated |
| Day 3 | 22-route sweep + drift handle + fidelity verify | ~0.5 hr | ~0.25 hr | Manual sweep |
| Day 4 | Closeout: retro + memory + push + PR | ~1 hr | ~0.8 hr (closeout 0.80) | Self |
| **Total** | | **~4.75 hr** | **~2.4 hr** | |

---

## 9. Dependencies

**Hard dependencies (must be true before Day 1)**:
- ✅ Sprint 57.28 verbatim-CSS foundation (Layer 2 `styles-mockup.css` byte-identical copy) — confirmed
- ✅ Sprint 57.30 `/chat-v2` Phase-2 re-point (inline LoopVisualizer mount baseline) — confirmed
- ✅ `BackendGapBanner` component existence — Sprint 57.24 ship; verify Day 0 Prong 2

**Soft dependencies (nice but not blocking)**:
- Sprint 57.27 `/overview` rebuild AP-2 banner pattern as reference
- Sprint 57.33 `/subagents` + `/memory` defensive guard pattern (for `rawEvents ?? []`)

**Unblocks (downstream)**:
- Phase 58+ SSE event persistence backend sprint can iterate on AP-2 banner removal
- `/state-inspector` Sprint 57.37+ (same single-file non-rich shape; 4th shape-validation data point candidate)

---

**End of plan**

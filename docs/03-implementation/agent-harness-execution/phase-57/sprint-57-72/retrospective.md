# Sprint 57.72 Retrospective — A-5c Inspector UI: Subagent Tree tab (Tree tab only)

**Closed**: 2026-06-03
**Plan**: `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-72-plan.md`
**Branch**: `feature/sprint-57-72-inspector-tree` (from `0f76e592`)

---

## Q1 — What was delivered?

The chat-v2 Inspector **Tree** tab, wired from the existing `subagents` slice. New `InspectorTree.tsx` (verbatim mockup re-point of `page-chat.jsx:489-531`, mirroring `InspectorTurn.tsx`) builds a tree from the flat `SubagentNode[]` (`parentId` nesting, cycle-guarded) and renders the `.subagent-tree` + Mode/Depth/Concurrency/Tokens summary + an empty state; `ChatInspector.tsx` swaps the Tree `ComingSoonInspectorTab` for it. **Tree tab only** (user-confirmed) — Trace (needs SpanStarted/SpanEnded over SSE) + Memory (needs `memory_accessed`) stay `ComingSoon`. Pure frontend.

## Q2 — Estimate accuracy / calibration

- Scope class **`frontend-mockup-direct-port` (0.55)**; `agent_factor` **`mechanical-greenfield-design-decisions` 0.65**; **Agent-delegated: yes** (single `code-implementer` for the component + test + mockup-fidelity verify; parent re-verify read the full component + ran all gates incl. `check:mockup-fidelity`).
- Plan: bottom-up ~7 hr → class-calibrated ~3.9 hr (0.55) → agent-adjusted ~2.5 hr (0.65).
- **No clean wall-clock** (agent-delegated) → **10th consecutive** agent-delegated no-clean-measure (57.63→57.72) → reinforces `AD-Calibration-AgentDelegated-WallClock-Measure`. CAVEATED; this is a small structural port (not a token-sweep), so the `frontend-mockup-direct-port` upper mode (~0.85 historical, bimodal) is expected. KEEP, no generalization.

## Q3 — What went well?

- **Day-0 surfaced the real scope before any code** — the user asked for "A-5c Inspector UI", but the Day-0 researcher pass found that only 1 of the 3 unfilled tabs (Tree) has a live producer; Trace + Memory both need deferred backend emission. Surfacing this + asking the user (Tree-only) avoided either building 2 Potemkin tabs or silently shipping less than asked.
- **The data model already existed** — `s.subagents` (Sprint 57.12) is already populated by `subagent_spawned`/`subagent_completed`; the Tree tab was a pure UI-consumer gap. No backend / event / store work needed.
- **The mirror pattern made it clean** — `InspectorTurn.tsx` provided the exact template (selector + verbatim classes + empty state + eslint-disable shape + lucide-icon mapping); `InspectorTree` follows it 1:1. Parent-run gates all green first time (CSS diff empty, build 0, Vitest 9/9, check:mockup-fidelity 50 unchanged).

## Q4 — What to improve / lessons

- **"Fill the Inspector" was 1 fillable tab, not 3** — for an Inspector/dashboard ask, Day-0 must map each widget to a live producer before scoping; here 2 of 3 had none. The honest delivery is 1 tab + 2 documented `ComingSoon` deferrals, not a fabricated-data Inspector.
- **The mockup's demo rows are fixture, not structure** — the "fork · t1 · 3 children" intermediate row + per-child turns + concurrency "/max" are mockup demo data with no `SubagentNode` field. Dropping them (D5) + conveying the fork via `.indent` + `GitFork` icon preserves structural fidelity without fabrication (AP-4). Mockup-fidelity = verbatim CSS/structure, NOT verbatim fixture content.
- **The Tree tab is empty until a run spawns subagents** — value is realized only on the subagent path (A-3a is wired); the empty state is the common case. Worth confirming the demo path actually exercises subagents in a future end-to-end check.

## Q5 — Carryover / open items (plan §9)

- **Inspector Trace tab** — `SpanStarted`/`SpanEnded` over SSE (deferred A-4/A-5 sliver) + backpressure. `AD-ChatV2-Inspector-Trace-Phase2`.
- **Inspector Memory tab** — `memory_accessed` (never yielded; A-1 sliver). `AD-ChatV2-Inspector-Memory-Phase2`.
- **Diagnostic-event surfacing** (`prompt_built`/`context_compacted`/`state_checkpointed`/`tripwire_triggered`/`guardrail_triggered`) — on the SSE wire (rawEvents-only), no mockup-faithful Inspector home; needs Trace tab or a new alert component.
- **Per-child turns + concurrency max** — needs richer subagent telemetry (backend producer change).
- **Other Area-A**: A-6 (frontend real-data wiring), FE `/subagents` page wiring (57.70 carryover). Two high-priority capstone key chains remain untouched: **C-11 (real-LLM enablement)** + the **billing-correctness bundle (B-7/B-8/C-15)**.

## Q6 — Anti-pattern audit (04-anti-patterns.md)

- AP-4 (Potemkin): the Tree tab renders REAL `s.subagents` data (Vitest seeds a root + 2 children and asserts the tree + summary); the unfillable tabs (Trace/Memory) were deferred, NOT shipped with fake data; the mockup's demo fixture rows were dropped, not fabricated. ✅
- AP-2 (no orphan): `InspectorTree` is wired into `ChatInspector` (the only consumer); no dead component. ✅
- Mockup-fidelity: verbatim mockup classes + `var(--*)` colors; CSS diff empty; `check:mockup-fidelity` baseline 50 unchanged; grep guard 0 hardcoded colors. ✅
- AP-3 (cross-dir scatter): change cohered in `chat_v2/components/inspector` + its test; no scatter. ✅

## Q7 — Final verification

CSS diff EMPTY; `npm run build` tsc 0; `npx vitest run …/inspector` 9/9; `npm run check:mockup-fidelity` byte-identical + baseline 50 unchanged; `npm run lint` (no `--silent`) EXIT 0; grep guard 0 hardcoded hex/oklch. No backend change (pytest/mypy/V2-lints untouched). No design note (frontend feature-continuation — verbatim re-point mirroring `InspectorTurn`).

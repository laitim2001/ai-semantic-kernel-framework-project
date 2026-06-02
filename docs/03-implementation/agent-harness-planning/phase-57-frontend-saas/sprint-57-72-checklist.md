# Sprint 57.72 — Checklist (A-5c Inspector UI: Subagent Tree tab — chat-v2 Inspector, Tree tab only)

**Plan**: [`sprint-57-72-plan.md`](./sprint-57-72-plan.md)
**Created**: 2026-06-03
**Status**: Draft (commit/push/PR user-gated)

> Rule: only `[ ]` → `[x]`; never delete unchecked items; defer with `🚧 + reason`.
> Frontend feature-continuation (verbatim mockup re-point of one tab, mirroring shipped `InspectorTurn.tsx`) → **no design note**. Mockup-Fidelity Hard Constraint applies (`docs/rules-on-demand/frontend-mockup-fidelity.md`). Scope = Tree tab only (user-confirmed); Trace/Memory stay ComingSoon (deferred to their producers).

---

## Day 0 — Plan-vs-Repo Verify + Branch + Decisions

### 0.1 Day-0 verify (researcher ground-truth pass, main `0f76e592`)
- [x] **Prong 1 (path)**: `frontend/src/features/chat_v2/components/inspector/{ChatInspector,InspectorTurn,ComingSoonInspectorTab}.tsx`; `store/chatStore.ts:514/571` (subagent_spawned/completed → `s.subagents`); `types.ts` (`SubagentNode` / `SubagentEntry` / `SubagentForkBlock`); mockup `reference/design-mockups/page-chat.jsx:489-531` (Tree tab); `styles-mockup.css` (.subagent-tree classes); `frontend/scripts/check-mockup-fidelity.mjs`
- [x] **Prong 2 (content)**: D1 only Tree fillable today (Trace needs SpanStarted/SpanEnded SSE; Memory needs `memory_accessed` — both deferred); D2 `s.subagents` slice already populated by subagent_spawned/completed (Sprint 57.12); D3 mockup Tree = root→fork→children + Mode/Depth/Concurrency/Tokens spread; D4 `InspectorTurn` mirror pattern (selector + verbatim classes + empty state + eslint-disable + lucide icons); D5 data gaps (no per-child turns, no concurrency max → "—"/omit per InspectorTurn convention)
- [x] **Prong 3 (schema)**: N/A — no DB / migration / ORM (frontend-only)
- [x] **Mockup-fidelity**: D6 `styles-mockup.css` byte-identical (diff empty); `.subagent-tree`/`.subagent-row`/`.indent` classes exist → no CSS change; `check:mockup-fidelity` `HEX_OKLCH_BASELINE = 50` (must stay; 57.69 D-DAY2-1 lesson — frontend sprint MUST run the gate)
- [x] **Doc-location**: CHANGE-040; mockup canonical = `page-chat.jsx:489-531`; no 17.md/02.md/01.md change (pure frontend consumer)
- [x] Catalogued drift D1-D6 in plan §0; **go/no-go = GO** (scope = Tree tab only, user-confirmed; data model + mockup classes + mirror pattern all present; <20% drift)

### 0.2 Branch + decisions
- [x] Branch `feature/sprint-57-72-inspector-tree` from `0f76e592`
- [x] plan+checklist commit; Day-0 progress commit (`fd4312ee`)
- [x] Decisions: scope = **Tree tab only** (Trace/Memory deferred to SpanStarted/SpanEnded-SSE + memory_accessed producers); render available fields, "—"/omit per-child turns + concurrency max (D5, no fabrication); verbatim mockup classes + `var(--*)` colors (no new CSS, no baseline bump); mirror `InspectorTurn`; **Agent-delegated: yes** (single code-implementer component + test + mockup-fidelity verify; parent re-verify)

---

## Day 1 — InspectorTree component + wire-in

### 1.1 InspectorTree component (US-1/US-2/US-3)
- [x] `InspectorTree.tsx` (NEW) — file header w/ mockup line-refs + Related; `eslint-disable no-restricted-syntax` block + mockup-line-ref comment (no literal `oklch(`); lucide MessageSquare(root leaf)/GitFork(root w/ children)/ChevronRight(child)
- [x] `buildTree(s.subagents)` — flat → nested by `parentId` (roots = parentId ∉ subagent ids; `visited` cycle guard + MAX_DEPTH=5; mirrors SubagentTree.buildForest); `.subagent-tree` root `.subagent-row` + recursive `.indent`
- [x] Per-node row: icon + name (`subagentId`, `var(--primary)` root / `var(--info)` child) + StatusBadge (running→`badge warning`, completed→`badge success dot`) + mode(running)/summary(completed) as `.subtle .grow`
- [x] `.thin-rule` + `.col` summary `.spread`: Mode (badge, dominant) / Depth (mono, max nesting) / Concurrency (mono, running-count — NO fabricated "/max") / Tokens-subtree (mono, Σ tokensUsed, "—" if all null)
- [x] Empty state `data-testid="inspector-tree-empty"` — "no subagents spawned this session"

### 1.2 Wire-in (US-3)
- [x] `ChatInspector.tsx` — Tree tab `<ComingSoonInspectorTab>` → `<InspectorTree/>` (L94); docstring/MHist/Related updated; Trace/Memory ComingSoon untouched

### 1.3 Tests (US-4)
- [x] Vitest (extended `ChatInspector.test.tsx`): empty state (`inspector-tree-empty` + ComingSoon-gone) + populated root+2children (names/nesting, running+2×completed, Depth=2/Concurrency=1/Tokens=2,000 summary, ComingSoon-gone); 8→9 tests

---

## Day 2 — Mockup-fidelity + full sweep

- [x] **CSS diff**: `diff styles.css styles-mockup.css` → empty (no CSS change; parent-verified)
- [x] **grep guard**: no hardcoded hex/oklch in `InspectorTree.tsx` (0 matches; all `var(--*)`)
- [x] **`check:mockup-fidelity`**: baseline unchanged (50=50, byte-identical) — parent-run ✅
- [x] **computed-style**: verbatim `.subagent-row`/`.spread`/`.badge` classes (no new CSS → inherits mockup computed style); deviation = dropped mockup demo synthetic "fork · t1 · 3 children" row (D5 anti-fabrication), `.indent` nesting conveys fork structure
- [x] `npm run lint` (no `--silent`) EXIT=0 + `npm run build` tsc 0 + Vitest 9/9 — parent-run
- [x] Parent re-verify: verbatim-class fidelity + buildTree cycle-guard + empty state + baseline 50; no backend change

---

## Day 3 — (buffer / edge)

- [x] Edge: empty `[]` → empty state; root + 2 children covered by Vitest; deep nesting / null tokens / running-count handled by buildTree+maxDepth+token-filter logic (parent-verified by read; MAX_DEPTH cap)
- [x] No drift beyond Day-0 D1-D6

---

## Day 4 — Closeout

### 4.1 Closeout docs
- [x] CHANGE-040 created; no 17.md/02.md/01.md change (pure frontend consumer)
- [x] progress.md (Day 0-4) + retrospective.md (Q1-Q7) — NO design note (feature-continuation)
- [x] Calibration: `frontend-mockup-direct-port` 0.55 + `agent_factor` 0.65 (CAVEATED — 10th consecutive no-clean-wall-clock 57.63→72); recorded `calibration-log.md §3`
- [x] MEMORY.md pointer + `project_phase57_72_inspector_tree.md` subfile + CLAUDE.md lean (Current Sprint row + footer)

### 4.2 Final verify + ship
- [x] Final verify (parent-run): CSS diff empty + `npm run build` tsc 0 + Vitest 9/9 + `check:mockup-fidelity` 50 unchanged + `npm run lint` (no `--silent`) EXIT 0 + grep 0 hardcoded color
- [ ] commit (Day 1-4) + push + PR — **user-authorized** (Day-0 `fd4312ee` + impl `0bdcbf91` committed; push/PR pending user approval)
- [x] Carryover recorded (plan §9 + retrospective §Q5 + memory subfile): Trace tab (SpanStarted/SpanEnded SSE) + Memory tab (memory_accessed) + diagnostic-event surfacing + per-child turns/concurrency-max telemetry + A-6 + FE /subagents wiring + capstone key chains (C-11 / billing bundle)

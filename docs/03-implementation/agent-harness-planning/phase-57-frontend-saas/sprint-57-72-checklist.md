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
- [ ] Branch `feature/sprint-57-72-inspector-tree` from `0f76e592`
- [ ] plan+checklist commit; Day-0 progress commit
- [ ] Decisions: scope = **Tree tab only** (Trace/Memory deferred to SpanStarted/SpanEnded-SSE + memory_accessed producers); render available fields, "—"/omit per-child turns + concurrency max (D5, no fabrication); verbatim mockup classes + `var(--*)` colors (no new CSS, no baseline bump); mirror `InspectorTurn`; **Agent-delegated: yes** (single code-implementer component + test + mockup-fidelity verify; parent re-verify)

---

## Day 1 — InspectorTree component + wire-in

### 1.1 InspectorTree component (US-1/US-2/US-3)
- [ ] `InspectorTree.tsx` (NEW) — file header w/ mockup line-refs + Related; `eslint-disable no-restricted-syntax` block + mockup-line-ref comment (no literal `oklch(` in the comment — 57.69 false-count lesson); lucide icons for mockup `Icon name="chat"/"fork"/"chevron_right"` (MessageSquare/GitFork/ChevronRight)
- [ ] `buildTree(s.subagents)` — flat → nested by `parentId` (roots = parentId ∉ subagent ids; guard self-ancestor cycle); render `.subagent-tree` root `.subagent-row` + `.indent` children
- [ ] Per-node row: icon + name (`subagentId`, `var(--primary)`/`var(--info)`) + status Badge (running → warning/info, completed → success dot) + mode/summary as `.subtle .grow` task text
- [ ] `.thin-rule` + `.col` summary `.spread` rows: Mode (Badge) / Depth (mono, max nesting) / Concurrency (mono, running-count — NO fabricated "/max") / Tokens-subtree (mono, Σ tokensUsed, "—" if all null)
- [ ] Empty state `data-testid="inspector-tree-empty"` — "no subagents spawned this session" (mirror InspectorTurn)

### 1.2 Wire-in (US-3)
- [ ] `ChatInspector.tsx` — Tree tab `<ComingSoonInspectorTab>` → `<InspectorTree/>`; update Tree AD note to "shipped Sprint 57.72"; Trace/Memory placeholders untouched

### 1.3 Tests (US-4)
- [ ] Vitest (`InspectorTree.test.tsx` NEW or extend `ChatInspector.test.tsx`): seed `s.subagents` (root + 2 children) → assert names + status + Mode/Depth/Concurrency/Tokens summary render; assert empty state when `[]`; assert Tree tab no longer renders ComingSoon

---

## Day 2 — Mockup-fidelity + full sweep

- [ ] **CSS diff**: `diff reference/design-mockups/styles.css frontend/src/styles-mockup.css` → empty (no CSS change)
- [ ] **grep guard**: no hardcoded hex/oklch in `InspectorTree.tsx` (`grep -nE '#[0-9a-fA-F]{6}|oklch\(' InspectorTree.tsx` → only legal `var(--*)`)
- [ ] **`check:mockup-fidelity`**: `npm run check:mockup-fidelity` → baseline unchanged (50) — MUST run (57.69 lesson)
- [ ] **computed-style spot-check**: `.subagent-row` / `.spread` / `.badge` vs mockup (Tree tab visible after seeding a subagent); drift verdict in progress.md
- [ ] `npm run lint` (NO `--silent`, 57.40 lesson) + `npm run build` + tsc 0 + Vitest green
- [ ] Parent re-verify: verbatim-class fidelity + tree-build logic + empty state + baseline 50; no backend change (pytest/mypy untouched)

---

## Day 3 — (buffer / edge)

- [ ] Edge: single root no children / deep nesting (depth 3) / all-completed vs mixed running / null tokensUsed → "—"; running-count correct
- [ ] No drift beyond Day-0 D1-D6

---

## Day 4 — Closeout

### 4.1 Closeout docs
- [ ] CHANGE-040 created; no 17.md/02.md/01.md change (pure frontend consumer)
- [ ] progress.md (Day 0-4) + retrospective.md (Q1-Q7) — NO design note (feature-continuation)
- [ ] Calibration: `frontend-mockup-direct-port` 0.55 + `agent_factor` 0.65 (CAVEATED — 10th consecutive no-clean-wall-clock 57.63→72); record `calibration-log.md §3`
- [ ] MEMORY.md pointer + `project_phase57_72_inspector_tree.md` subfile + CLAUDE.md lean (Current Sprint row + footer)

### 4.2 Final verify + ship
- [ ] Final verify: `npm run lint` + build + tsc 0 + Vitest + `check:mockup-fidelity` 50; CSS diff empty
- [ ] commit (Day 1-4) + push + PR — **user-authorized** (push/PR pending user approval)
- [ ] Carryover recorded (plan §9 + retrospective §Q5 + memory subfile): Trace tab (SpanStarted/SpanEnded SSE) + Memory tab (memory_accessed) + diagnostic-event surfacing + per-child turns/concurrency-max telemetry + A-6 + FE /subagents wiring + capstone key chains (C-11 / billing bundle)

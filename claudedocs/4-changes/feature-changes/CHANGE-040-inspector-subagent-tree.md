# CHANGE-040: A-5c Inspector UI — Subagent Tree tab (chat-v2 Inspector, Tree tab only)

**Date**: 2026-06-03
**Sprint**: 57.72
**Scope**: Frontend (chat-v2 Inspector — mockup `page-chat.jsx` Tree tab) consuming Cat 11 subagent events

## Change Summary

Filled the chat-v2 Inspector **Tree** tab — the one of the three unfilled Inspector tabs that can be honestly populated from events already on the SSE wire today. `subagent_spawned` / `subagent_completed` already update the chatStore `subagents` slice (`SubagentNode`, Sprint 57.12), but the Tree tab was still a `ComingSoonInspectorTab` placeholder. New `InspectorTree.tsx` (a verbatim mockup re-point of `page-chat.jsx:489-531`, mirroring the shipped `InspectorTurn.tsx` sibling) builds a tree from the flat slice (`parentId` nesting) and renders the `.subagent-tree` + Mode/Depth/Concurrency/Tokens summary; `ChatInspector.tsx` swaps the placeholder for it.

**Scope = Tree tab ONLY** (user-confirmed). The other two unfilled tabs need deferred backend producers and stay `ComingSoon`: **Trace** needs `SpanStarted`/`SpanEnded` over SSE (A-4 shipped the loop span tree to OTel only; the SSE form is the deferred A-4/A-5 sliver), **Memory** needs `memory_accessed` (never yielded in `loop.py`; the A-1 sliver). Filling either now = AP-4 Potemkin.

## Change Reason

A-5c (diagnostic Inspector UI, Area-A item 5c) is the frontend-consumer half of the event-visibility pipeline (A-5a serialized, A-5b added codegen+CI; both shipped 57.66/57.67). The Tree tab's producer (subagent events) is already live and wired into the store — it just lacked a UI consumer. Trace/Memory producers are not yet live, so only Tree could be honestly built this sprint.

## Detailed Changes

- `frontend/src/features/chat_v2/components/inspector/InspectorTree.tsx` (NEW) — verbatim re-point of mockup L489-531. `buildTree()` folds `SubagentNode[]` → forest by `parentId` (roots = parentId ∉ subagent ids; `visited` cycle guard + `MAX_DEPTH=5`); `NodeRow` renders `.subagent-row` + recursive `.indent`; lucide `MessageSquare`/`GitFork`/`ChevronRight` for the mockup `chat`/`fork`/`chevron_right` icons; `StatusBadge` (running→`badge warning`, completed→`badge success dot`); `.thin-rule` + `.col` summary (Mode dominant-mode badge / Depth max-nesting / Concurrency running-count / Tokens-subtree Σ tokensUsed); empty state (`inspector-tree-empty`). Colors via `var(--*)` only.
- `frontend/src/features/chat_v2/components/inspector/ChatInspector.tsx` (EDIT) — Tree tab `ComingSoonInspectorTab` → `<InspectorTree/>` (L94); docstring/MHist/Related updated. Trace/Memory placeholders untouched.
- `frontend/tests/unit/chat_v2/components/inspector/ChatInspector.test.tsx` (EXTEND) — 8→9 tests: empty-state + populated-tree (root + 2 children, status, Depth/Concurrency/Tokens summary, ComingSoon-gone).

## D5 deviation (render-vs-fabricate)

`SubagentNode` carries no per-child `turns` and no concurrency **max**, and the mockup's "fork · t1 · 3 children" intermediate row is demo fixture data. These were **dropped, not fabricated** (AP-4): Concurrency shows the running-count only (no "/max"); the per-child turn suffix is omitted; the fork structure is conveyed by `.indent` nesting + a `GitFork` icon on a parent-with-children. Structural CSS fidelity preserved; literal demo content not reproduced.

## Verification

- CSS diff `styles.css` vs `styles-mockup.css` EMPTY (no CSS change); `npm run build` tsc 0; `npx vitest run …/inspector` 9/9; `npm run check:mockup-fidelity` byte-identical + baseline **50 unchanged**; `npm run lint` (no `--silent`) EXIT 0; grep guard 0 hardcoded hex/oklch in InspectorTree.tsx.
- No backend change (pytest/mypy/V2-lints untouched).

## Impact

Frontend-only (chat-v2 Inspector). No backend, no new SSE event/wire-type/codegen, no CSS/`styles-mockup.css` change, no new dependency. Trace + Memory tabs stay `ComingSoon` (deferred to their producers). PR pending.

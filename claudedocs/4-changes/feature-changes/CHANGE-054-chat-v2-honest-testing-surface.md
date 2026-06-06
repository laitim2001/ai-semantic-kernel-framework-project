# CHANGE-054: chat-v2 honest testing surface (frontend UX correctness)

**Change Date**: 2026-06-06
**Change Type**: Feature Improvement (frontend UX correctness)
**Status**: ✅ Completed (browser-verified)
**Scope**: Frontend / chat_v2 (no backend change)
**Branch**: `feature/chat-v2-honest-testing-surface`

## Change Summary

After the unmocked e2e + real-LLM smoke (PR #253) the user opened `/chat-v2` and reported it was not a usable testing surface:
1. Left session history is 6 rows of fixture demo data; the "New session" button did nothing.
2. Sending a message showed no normal LLM output; could not tell what was demo vs real.

Investigation confirmed both — plus a deeper root cause behind #2: the agent's **final text answer was never rendered**. This change makes `/chat-v2` an honest, non-misleading surface that defaults to the live agent and shows its answer.

## Change Reason

The page conflated "the agent loop works (when driven in real_llm)" with "the page is ready". Several elements were fixture/dead/misleading independent of the loop:
- `New session` button had no `onClick` (visual-only).
- Default mode was `echo_demo` (echoes input — never a real answer); a casual tester saw an echo, not the agent.
- Header model badge was hardcoded `claude-haiku-4-5`; per-turn label hardcoded `incident-responder` — both shown even on a real gpt-5.2 run.
- The Block union (thinking / tool / verification / subagent_fork) had **no assistant-answer block**, so a plain Q&A answer (no tool call) rendered an empty turn — the literal "can't see the LLM output".

## Detailed Changes (5 fixes)

1. **New session wired** — `SessionList` "New session" button now calls `store.reset()`; `reset()` also zeroes the module-global `_turnCounter` so a fresh session restarts at turn 1.
2. **Default mode → `real_llm`** + clarity — `chatStore` default mode flipped `echo_demo`→`real_llm`; `InputBar` mode buttons gained tooltips (echo = offline mock / real = live Azure) and an inline note when `echo_demo` is active ("echoes your input — switch to real_llm for a live answer").
3. **Honest labels** — added `currentModel` to the store (captured from `llm_request.model`); `ChatHeader` model badge now shows the real model (e.g. `gpt-5.2`), falling back to the mode before the first call; header agent default `incident-responder`→`agent`; `AgentTurn` per-turn role `incident-responder`→`agent`.
4. **Session list DEMO badge** — added a `DEMO` badge on the SESSIONS section (the fixture list is unmistakably demo; existing AP-2 banner preserved). Real persisted list remains deferred (`AD-ChatV2-SessionList-Backend`, item 5 — NOT in this change).
5. **Render the agent's final answer** (root of #2) — new `AnswerBlock` type + component; `chatStore.llm_response` pushes an answer block from `ev.data.content` when non-empty; `Block` dispatcher + `InspectorTurn` block-sequence handle the new type.

## Modified Files

- `frontend/src/features/chat_v2/store/chatStore.ts` — default mode, `currentModel`, `reset()` counter, `llm_response` answer block
- `frontend/src/features/chat_v2/types.ts` — `AnswerBlock` type + Block union
- `frontend/src/features/chat_v2/components/SessionList.tsx` — wire New session + DEMO badge
- `frontend/src/features/chat_v2/components/ChatHeader.tsx` — real model badge + honest agent label
- `frontend/src/features/chat_v2/components/InputBar.tsx` — mode tooltips + echo note (+ i18n)
- `frontend/src/features/chat_v2/components/TurnList.tsx` — mode-aware empty-state copy
- `frontend/src/features/chat_v2/components/turns/AgentTurn.tsx` — role label `agent`
- `frontend/src/features/chat_v2/components/blocks/AnswerBlock.tsx` — NEW
- `frontend/src/features/chat_v2/components/blocks/Block.tsx` — answer case
- `frontend/src/features/chat_v2/components/inspector/InspectorTurn.tsx` — answer tone + describe
- `frontend/src/i18n/locales/{en,zh-TW}/common.json` — `chat.session.demoTag` + `chat.composer.*`
- Tests: `ChatHeader.test.tsx`, `TurnList.test.tsx`, `SessionList.test.tsx` (assertions updated for the deliberate label/copy changes + New-session reset test), `chat-v2-real-backend.spec.ts` (stale comment)

## Verification

- Gates: `tsc -b && vite build` ✓ · `vitest` 762 ✓ · `check:mockup-fidelity` ✓ (styles-mockup.css byte-identical; hardcoded-color baseline 53 unchanged — all additions use `var(--*)`) · `eslint src` no errors.
- **Browser-verified (real Azure gpt-5.2, `/chat-v2`)**:
  - Default mode `real_llm` active; echo tooltips + echo note appear on `echo_demo`.
  - Header badge shows `gpt-5.2` after a run (mode label before); agent label `agent`; SESSIONS shows `DEMO` badge.
  - "What is 2 plus 2?" → **answer block renders `4`** (was previously invisible); model badge `gpt-5.2`; verification 0.55.
  - "New session" clears the conversation (2 turns → 0, empty state, `○ idle`).
- Screenshot: `frontend/.playwright-mcp/chat-v2-honest-surface-after-fixes-20260606.png`.

## Impact

Frontend-only. No backend / API / SSE wire change. The real persisted session list (load history on click) remains the one deferred item (`AD-ChatV2-SessionList-Backend`), tracked separately.

# CHANGE-133: Chat 主流量 production default persona (stop the demo-persona leak)

**Date**: 2026-07-15
**Sprint**: 57.166 candidate (drive-through-driven immediate fix — `AD-Chat-Default-Persona-Demo-Leak`)
**Scope**: 範疇 3 (Memory) usage-guidance + `api/v1/chat` (persona resolution) — cross-cutting, backend-only

## Problem

A drive-through of the real chat-v2 主流量 (真 UI + 真後端 + 真 LLM, 2026-07-15) exposed that every
ordinary user without a tenant `agent_role` was being served `DEMO_SYSTEM_PROMPT` — the "Sprint 50.2
demonstration agent". Observed agent misbehaviour, all on the primary flow:

1. **Confidential over-tagging** — the demo persona mandates the word "confidential" on any
   share/state request, so the agent tagged the user's own name / role / project facts `(confidential)`.
2. **Denied having memory** — the demo persona never taught the agent to USE its injected memory
   (57.148 profile identity + 57.151 cross-session recall), so it answered "I don't have access to
   chat history" despite the facts sitting in its context.
3. **Time confusion** — a prior-session incident (INC-99999) was narrated as happening "in this
   session"; the injected session summaries carried no marker distinguishing a prior session.
4. **Demo identity leak** — the agent introduced itself as a "Sprint 50.2 demonstration agent".

This is an AP-4 Potemkin-adjacent defect: the demo scaffold (built for the 57.91/92/93 demo
drive-throughs) sat on the 主流量 and shipped its test triggers to production conversations. Every gate
was green — only a drive-through surfaced it.

## Root Cause

`resolve_session_persona` (backend/src/api/v1/chat/handler.py) fell back to `DEMO_SYSTEM_PROMPT` on all
5 non-role paths (no db / no session / no agent_role / unknown role / null persona). The demo prompt was
doubling as both the demo-test scaffold AND the production default — they were never separated.

## Solution

**Method A** (user-selected — cleanest, preserves the demo drive-through paths):

1. **`core/config/__init__.py`** — add `chat_demo_mode: bool = False` (env `CHAT_DEMO_MODE`).
2. **`api/v1/chat/handler.py`**:
   - Add `DEFAULT_SYSTEM_PROMPT` — a clean production persona that (a) KEEPS the two genuinely-production
     behaviours the demo carried (`write_todos` multi-step planning + `knowledge_search` grounding),
     (b) ADDS explicit MEMORY-usage guidance ("ANSWER from injected memory — do NOT claim you have no
     memory"; "distinguish a PRIOR session from the current one by its date"; "do not label it
     'confidential' unless genuinely sensitive"), (c) DROPS the demo identity / confidential mandate /
     echo-note triggers.
   - Add `_default_persona()` — returns `DEMO_SYSTEM_PROMPT if get_settings().chat_demo_mode else
     DEFAULT_SYSTEM_PROMPT`, read at call time so the flag can flip per-request / per-test.
   - Repoint the 5 `resolve_session_persona` fallbacks from `DEMO_SYSTEM_PROMPT` → `_default_persona()`.
   - `build_echo_demo_handler` + `build_real_llm_handler` / `build_handler` default args stay
     `= DEMO_SYSTEM_PROMPT` (unchanged) — the 主流量 router passes an explicit `system_prompt` from
     `resolve_session_persona`, so only the demo-test entry points still default to demo.
3. **`agent_harness/memory/retrieval.py`** — `recent_sessions()` prefixes each session hint with a dated
   marker `[Prior session, {updated_at:%Y-%m-%d}] …` so the agent can place a summary in time (fixes #3).

The demo persona (with echo/note/confidential triggers) survives behind `CHAT_DEMO_MODE=1` so the
57.91/92/93 demo drive-throughs keep working — nothing is deleted.

## Verification

**Gate layer**:
- mypy `src`: 400 files, no issues
- V2 architecture lints (`scripts/lint/run_all.py`): 12/12 green (incl. LLM-SDK-leak + PromptBuilder AP-8)
- black / isort / flake8: clean (5 changed files)
- pytest (affected scope): persona unit 11 pass (4 updated + 3 new: demo-mode gate, clean-prompt
  assertions) · retrieval recent_sessions 5 pass · e2e (chat_e2e + pause_resume + category_activation) 28 pass

**Drive-through layer** ⭐ (真 UI + 真後端 + 真 LLM, 2026-07-15, user `jamie`, chat-v2, backend PID 72120
clean-restart with the new persona loaded):

Prompt: "do you know what we have discuss before? please show all the work or conversation we have
discuss or work together before"

| Target | Before (demo) | Actual (production persona) | Verdict |
|--------|---------------|-----------------------------|---------|
| No confidential over-tag | every fact `(confidential)` | zero `(confidential)` in output | ✅ |
| Does not deny memory | "I don't have access to chat history" | "Yes—based on the saved session summaries I have" | ✅ |
| Time-correct prior sessions | INC-99999 read as "in this session" | `2026-07-15 (prior session)` / `2026-07-10` / `2026-07-09`, INC-99999 correctly on the 07-09/07-10 prior session | ✅ |
| No demo identity | "Sprint 50.2 demonstration agent" | professional enterprise-assistant tone | ✅ |

Bonus positive signals: the agent reasoned about memory staleness ("role: compliance lead — this may be
outdated given the later name update") and honestly distinguished "summaries ≠ verbatim transcript"
(correct behaviour, not a defect). **Drive-through PASS (4/4).**

## Impact

- Backend-only. No migration, no wire change, no frontend change.
- Behaviour change on the 主流量 for every non-role session (i.e. ordinary chat): production persona
  instead of demo. Demo behaviour is now opt-in via `CHAT_DEMO_MODE`.
- The 57.91/92/93 demo drive-through paths are preserved behind the flag (their unit coverage stays green).

## Related

- `AD-Chat-Default-Persona-Demo-Leak` — `claudedocs/1-planning/next-phase-candidates.md` §Open Carryover ADs
- CLAUDE.md §Drive-Through Acceptance Hard Constraint (this fix is itself a drive-through find)
- `memory/feedback_drive_through_over_paper_metrics.md` — gate-green ≠ usable; only the drive-through caught it
- Sprint 57.148 (profile identity) + 57.151 (cross-session recall) — the memory this persona now teaches the agent to use

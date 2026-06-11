# Sprint 57.102 Retrospective — TEAMMATE real multi-turn child loop + send_to_parent + B1 inbox wiring (B2a)

**Closed**: 2026-06-11
**Plan**: [`../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-102-plan.md`](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-102-plan.md)
**Branch**: `feature/sprint-57-102-teammate-multiturn`

## Q1 — What shipped?

The first half of harness-deepening Workflow B slice B2: TEAMMATE (Cat 11 mode 2) goes from a single-shot `chat()` to a real multi-turn collaborating child loop (mirror 57.94 FORK), with a `send_to_parent` tool (child→parent report folded into the summary) + the B1 `MessageInbox` wired (reuse 57.101; live UI producer = B2b). Backend-only, 15 files, `loop.py` UNCHANGED, no new wire event (reuses `SubagentChildEvent`), no DB, no frontend. CHANGE-069 + 17.md + design note 20 edit.

## Q2 — Estimate accuracy / calibration

- Scope class **`subagent-teammate-multiturn-spike` (NEW, 0.55, 1st data point)**. Bottom-up ~14.5 hr → class-calibrated commit ~8 hr (mult 0.55). **Agent-delegated: no** (parent-direct; `agent_factor = 1.0`).
- Actual ≈ ~7.5-8 hr (Day-0 recon + plan/checklist + impl + 5 test files + full gate + drive-through + docs). Ratio `actual/committed` ≈ **~0.95-1.0 — IN BAND**. The 0.55 multiplier fit well: this was composition-heavy (reused 3 proven assets — FORK pattern + 57.96 relay + B1 inbox), so the per-file work was mechanical mirroring + wiring, not new-domain design. KEEP `subagent-teammate-multiturn-spike` 0.55 pending 2-3 sprint validation.

## Q3 — What went well?

- **Day-0 三-prong paid off twice**: (1) caught the proposal's `teammate.py`-under-`modes/` path drift + the await-completion constraint (→ B2a/B2b split, decided WITH the user before any code); (2) the deeper read of `make_default_executor`/`ToolRegistry` surfaced the cleaner `teammate_mailbox` opt-in registration (D-DAY0-4) vs the plan's post-construction sketch — applied at Day-1 with no rework.
- **Reuse discipline**: mirroring FORK's `_drive` + fail-closed envelope made the `TeammateExecutor` rewrite low-risk; the 57.96 `SubagentChildEvent` relay gave the teammate's multi-turn + `send_to_parent` Tree rendering for FREE → B2a needed zero frontend.
- **Drive-through nailed it first try** — the real Azure gpt-5.2 spawned a teammate (mode=teammate), the teammate ran a real 3-turn loop (tool → send_to_parent → answer), the report folded + the parent integrated it + verification 0.99. No prompt iteration needed (vs the 57.101 forceful-prompt budget).
- **send_to_parent is not a Potemkin**: the reader (mailbox.drain → fold into summary) was built in the SAME sprint, drive-through-proven (the parent's answer quoted the teammate's report).

## Q4 — What to improve / lessons?

- **Layer-neutral seam took the most thought**: agent_harness must not import the api-layer `InjectionRegistry`, so the executor receives an `inbox_factory` callable typed against the `MessageInbox` ABC; the concrete `QueueMessageInbox` is built in the handler. Worth codifying as a reusable pattern (cross-layer DI via an ABC + a factory callable) — it recurs (B1 did the same for the chat inbox).
- **PowerShell here-string in the Bash tool** mangled the impl commit message (a literal `@` leaked into the subject) — amended via `git commit --amend -F -` heredoc. Lesson: `@'...'@` is PowerShell-only; for multi-line commit messages in the **Bash** tool use a `<<'EOF'` heredoc with `-F -`.
- **Pre-existing FE carryover surfaced**: the inline `SubagentForkBlock` mislabels a teammate spawn as "Fork · concurrent" + shows "0t" (the 57.95/96 carryover) — the Tree is correct, but B2b should make the inline block mode-aware.

## Q5 — Carryover (→ B2b / next-phase-candidates.md)

- **B2b** — the live UI producer for the teammate inbox: `POST /chat/{id}/subagents/{subagent_id}/inject` (extend B1's inject with a subagent target) + the `InjectionRegistry` spawn-time registration + the FE inject-to-teammate control + render + that inbox's drive-through.
- **B2b (FE polish)** — make the inline `SubagentForkBlock` mode-aware ("Teammate" vs "Fork") + fix the "0t" token display (pre-existing 57.95/96 carryover).
- **Deferred** — detached / non-blocking teammate (live parent→child mid-run injection; proposal §2.5); depth>1; per-tenant teammate policy (C3); durable teammate transcript (`AD-Subagent-Transcript-Isolation`).

## Q6 — Gate evidence

mypy `src` 0/355 · flake8 `src tests` clean · `run_all` 10/10 (event count unchanged) · full pytest **2333 passed + 4 skipped** (+13, 0 deletions) · **drive-through PASS** (real UI + real Azure gpt-5.2; `artifacts/dt57102-teammate-tree.png`). Frontend: no change (diff = 0). `loop.py`/`modes/fork.py`/`router.py`/`injection_registry.py`/`events.py`/DB diff = 0.

## Q7 — Design-note self-check

NO new design note (composition continuation of design note 20 + B1) — per `sprint-workflow.md §Step 5.5`. Record = CHANGE-069 + 17.md (`send_to_parent` + `TeammateChildLoopFactory` + the MessageInbox B2a backing) + design note 20 §5 light edit (TEAMMATE shipped).

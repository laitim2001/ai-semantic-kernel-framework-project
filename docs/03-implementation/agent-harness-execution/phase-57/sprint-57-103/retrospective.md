# Sprint 57.103 Retrospective — chat-user inject-to-teammate (B2b)

**Closed**: 2026-06-11
**Plan**: [`../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-103-plan.md`](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-103-plan.md)
**Branch**: `feature/sprint-57-103-inject-to-teammate`

## Q1 — What shipped?

The second half of harness-deepening Workflow B slice B2: the chat-user inject-to-teammate primitive. **Shipped + proven**: US-1 the `POST /chat/{id}/subagents/{sid}/inject` endpoint (a B1 sibling), US-2 the `inbox_scope` lifecycle (the teammate's `InjectionRegistry` queue registered only while it runs, via `make_teammate_inbox_scope`), US-3 the `MessageInjected`-in-relay (the injected child turn surfaces as a `SubagentChildEvent`), and US-5 (57.102 carryover) the inline `SubagentForkBlock` mode-awareness ("Teammate · peer" + real tokens vs "Fork · concurrent" + "0t").

**Deferred (drive-through finding)**: US-4 the inject UI control + US-6 the live inject — the FE never observes a teammate as "running" under the buffered SSE relay + await-completion, so the control can never render. Removed per Option A (no dead control); the live inject UI awaits the detached/streaming teammate (proposal §2.5). The backend primitive (US-1/2/3) is fully reusable when §2.5 lands.

## Q2 — Estimate accuracy / calibration

- Scope class **`subagent-inject-to-teammate` (NEW, 0.55, 1st data point)**. Bottom-up ~13 hr → class-calibrated commit ~7 hr (mult 0.55). **Agent-delegated: no** (parent-direct; `agent_factor = 1.0`).
- Actual ≈ ~8-9 hr (Day-0 recon + plan/checklist + backend + 9 tests + FE + 9 Vitest + full gate + a real Playwright drive-through that found the blocker + the Option-A reversion + docs). Ratio `actual/committed` ≈ **~1.15-1.25 — slightly over**. The over-run is the drive-through investigation + the reversion (building the FE control + tests, then removing them after the finding). KEEP `subagent-inject-to-teammate` 0.55 pending 2-3 sprint validation, but note that a sprint whose user-facing half is architecture-blocked carries a hidden "build-then-revert" tax the bottom-up didn't price.

## Q3 — What went well?

- **Day-0 三-prong resolved two load-bearing contradictions BEFORE code**: (1) `InjectionRegistry.put()` does NOT auto-create a queue (two recon agents disagreed; reading the code settled it → US-2 needs spawn-time register/unregister), (2) `MessageInjected` was absent from `_TAO_CHILD_EVENT_TYPES` (US-3 must add it). Both were the spine of the sprint.
- **The `inbox_scope` extraction (`make_teammate_inbox_scope`) was a clean win** — co-locating the register/unregister lifecycle with `QueueMessageInbox` made the load-bearing B2b invariant (queue live only while the teammate runs) directly unit-testable against the real code, not a test-local copy. mypy + the 6 inbox tests passed first try.
- **The drive-through did its job** — it caught that the headline feature can't be driven, exactly the failure mode the Drive-Through Acceptance rule exists for. US-5 + the backend flow were proven driven (real Azure: parent integrated "Teammate subagent finding (checkout patrol)" + verification passed); the inject control was proven un-drivable.
- **Honest close** — surfaced the finding to the user, took the Option-A decision (remove the dead control, keep the proven primitive), no Potemkin shipped.

## Q4 — What to improve / lessons?

- **The planning miss (the load-bearing lesson)**: the B2b Day-0 noted the await-completion constraint (the dispatcher blocks on the child) but did NOT connect that the **buffered SSE relay** (Sprint 57.95: the router buffers subagent events + drains them only when the parent loop yields its next event, i.e. AFTER the awaited teammate completes) means the FE **never sees a teammate as "running"**. So a control gated on `status === "running"` can never render. **Generalizable rule**: when a feature's gating depends on a live in-progress state of a subagent/child, verify at Day-0 that the FE actually *receives that state live* — trace the event from emit → SSE flush → store, not just "the event exists". A buffered/turn-boundary relay collapses in-progress states. (→ candidate AD for sprint-workflow Prong-2.)
- **Build-then-revert tax**: US-4 (control + service + 6 Vitest) was built, then removed. A Day-0 check on the relay's live-ness would have caught this before building. The backend primitive was the right thing to build regardless (reusable for §2.5), so the loss was only the FE control + its tests (~1-1.5 hr).
- **`@'...'@` PowerShell here-string is NOT for the Bash tool** (carried lesson from 57.102) — used `<<'EOF'` heredocs for all commit messages this sprint; clean.

## Q5 — Carryover (→ next-phase-candidates.md)

- **The inject-to-teammate UI (US-4/6)** — blocked on the detached/streaming teammate (proposal §2.5). When §2.5 lands (the parent reasons while the child runs, OR the SSE relay streams subagent events live), the FE will observe a running teammate → rebuild the inject control (the `injectToSubagent` service + the `InspectorTree` gated control + the `message_injected` child row, which is already wired) on top of the proven backend primitive.
- **`message_injected` child-row render** — kept in `InspectorTree.childTurnLabel` (the relay render is correct + reachable once §2.5 lands; backend relay primitive wired now).
- **Deferred (unchanged)** — depth>1 child-of-child inject routing; per-tenant teammate inject policy (C3); durable teammate transcript.

## Q6 — Gate evidence

mypy `src` 0/355 · flake8 `src tests` clean · `run_all` 10/10 (event count unchanged) · full pytest **2342 passed + 4 skipped** (+9, 0 deletions) · `loop.py` + DB + generated wire schema diff = 0 · FE build ✓ / lint exit 0 / Vitest 143 / `check:mockup-fidelity` 53 unchanged · **drive-through**: US-5 + backend flow PROVEN driven (real Azure gpt-5.2); inject control PROVEN un-drivable (removed). Artifacts: `artifacts/dt57103-*.png`.

## Q7 — Design-note self-check

NO new design note (feature continuation of design note 20 + B1, per `sprint-workflow.md §Step 5.5`). Record = CHANGE-070 + 17.md (`TeammateInboxScope` + the inject-to-subagent endpoint + MessageInjected-in-relay) + design note 20 §5 edit (the B2b backend primitive shipped + the await-completion finding documented as the blocker for the live inject UI).

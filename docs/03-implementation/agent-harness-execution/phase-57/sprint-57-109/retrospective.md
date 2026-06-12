# Sprint 57.109 Retrospective — C2: compaction cheap tier + `_compaction` ledger attribution + compaction knobs

**Date**: 2026-06-12 (single-day sprint, Day 0-4)
**Outcome**: SHIPPED — all 5 plan deliverables; drive-through PASS; closes harness-deepening proposal §3.4 C2 (the LAST C-family slice — C 3/3 done).

## Q1 — What was delivered vs planned?

All US-1..US-4 + CHANGE-076. One design correction (D-DAY1-1: `ContextCompacted` carrier instead of the planned LoopCompleted mirror — strictly better: 1 yield-site loop.py diff + every termination path bills) and one in-family scope add (D-DAY3-2: `CHAT_COMPACTION_KEEP_RECENT_TURNS` knob — required to make the dt DoD reachable AND a real deployability fix). Tests +23, 0 deletions (2462 → 2485 incl. e2e). Wire/codegen/FE/DB all untouched as planned.

## Q2 — Estimate accuracy (calibration)

- Plan §Workload: bottom-up ~8 hr → class-calibrated commit ~4.5 hr (`multi-model-profile-spike` 0.55, 3-segment). **Agent-delegated: no** (parent-direct; 2 Explore agents Day-0 recon only) → `agent_factor 1.0`.
- Actual ≈ 5-5.5 hr (Day 0 ~1 + Day 1-2 ~2 + Day 3 ~2.5 incl. two failed dt attempts + the keep-knob pivot + closeout ~0.75).
- **Ratio ≈ 1.1-1.2 — IN band (upper edge)**. The over-run is entirely the Day-3 dt discovery loop (D-DAY3-1 structural unreachability → two recipe iterations → knob #2). The build itself ran ~0.85.
- **`multi-model-profile-spike` 0.55 — 2nd data point** (57.97 ~0.93 + 57.109 ~1.1-1.2; mean ~1.0) → KEEP 0.55.

## Q3 — What went well?

- **Day-0 三-prong ROI again**: D1 pinned the `_verification` mirror EXACTLY (incl. `verification_model` existing — the plan's biggest unknown); D3 caught the `_summarise` return-shape need; D13 caught the factory-not-threading-budget gap that would have made the knob a silent no-op. ~45 min Day-0 prevented ≥2 hr mid-build rework.
- **D-DAY1-1 carrier pivot**: grepping `yield LoopCompleted(` (30+ sites) BEFORE coding the planned accumulator shape avoided a sprawling diff and produced a strictly-better design (event-carrier bills MAX_TURNS paths the verification precedent drops).
- **Drive-through did its job par excellence**: it falsified a 5-sprint-old assumption — semantic compaction had been a latent main-flow NO-OP since 52.1 (all gates green the whole time). Paper metrics could never have caught this; the dt rule did.
- B1 injection (57.101) became the dt lever for a sibling category — cross-slice payoff.

## Q4 — What to improve / lessons?

- **D-DAY3-1 → carryover `AD-Semantic-Compaction-User-Turn-Anchor`**: the user-turn-anchored cutoff assumes CC-style in-run multi-turn history; V2 chat continuity lives in Cat 3 memory. A message-count (or token-mass) anchor would make semantic compaction organically reachable. Own Cat 4 slice; NOT folded in (Karpathy §3).
- **D-DAY1-2 → test-file basename rule**: pytest's unique-basename constraint made the new `tests/unit/api/v1/chat/test_category_factories.py` collide with the EXISTING `tests/unit/api/test_category_factories.py` — standalone run green, full run collection-ERROR. Lesson: **Glob the basename across the whole test tree before creating any new test file** (candidate Prong-1 row on 2nd occurrence).
- **dt-recipe timing**: composer-driven B1 injection has a ~10 s/message floor through Playwright snapshots; runs finish faster. Single-injection recipes (enabled by the keep knob) are the repeatable shape.
- `AD-Resume-Billing-Observers` (🟢 pre-existing): the resume path bills nothing (loop + verification + now compaction alike).

## Q5 — Anti-pattern audit

AP-1..AP-11: 0 violations. Notably AP-4: the dt itself EXPOSED a latent near-Potemkin (semantic stage never engaging on 主流量) and the sprint made it deployable + observable (ledger rows); AP-6: both knobs have live use (ops tuning + the dt lever), defaults unchanged; AP-2: attribution chain is main-flow (router observer), integration-tested end-to-end.

## Q6 — Drive-through verdict

PASS (real UI + real backend PID 36280 + real Azure; zero dev-login). Evidence: `context_compacted` 9824→2679/8 msgs/3535 ms live frame · billing_outbox `_compaction` @ `gpt-5.4-mini-2026-03-17` 260/149 done · cost_ledger 2 priced rows ($0.000195/$0.0006705) · post-compaction answer carries the injected fact + llm_judge 0.99 · whole-day `_compaction` outbox count = 1 (zero-usage guard live). Honest carve-out: memory-extraction tier is gate-level only (no runtime ledger surface for extraction calls).

## Q7 — Carryover / next

- NEW: `AD-Semantic-Compaction-User-Turn-Anchor` (Cat 4 cutoff anchor redesign) · `AD-Resume-Billing-Observers` (🟢) · test-basename Prong-1 watch (1st pt).
- C-family 3/3 done (C1 57.104 / C3 57.106 / C2 57.109). **Next slice per interleave: B4** — rolling discipline, plan only on user kickoff.

## Design Note Extract（spike sprint only）

NOT required — feature continuation of design note 24 (§5.5 NOT-apply); note 24 §4 invariant marked RESOLVED + MHist instead.

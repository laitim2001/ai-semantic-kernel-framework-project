# Sprint 57.161 Retrospective — structural compactor real token re-count

**Closed** 2026-07-07 · branch `feature/sprint-57-161-compaction-structural-realcount` from `main` `204c4499` · engine-debt compaction range · closes `AD-Compaction-Structural-RealTokenCount`.

## Q1 — What shipped?

`StructuralCompactor.tokens_after` upgraded from a message-count ratio (blind to in-place tombstoning) to a REAL `TokenCounter` re-count when a counter is injected (mirroring `PreClearCompactor` `preclear.py:178-181`); the chat factory injects `TiktokenCounter` default-on. So tool-anchored observation masking (57.160) now surfaces its reduction on the 57.159 chat-v2 marker AND relieves the loop budget WITHOUT the preclear lever. Fixed the stale `structural.py:192` "Loop.run() will re-count" comment (the loop trusts `tokens_after`, `loop.py:2282`). Backend-only, ZERO wire/codegen/frontend/migration. CHANGE-128 + design note 63.

## Q2 — Calibration (estimate accuracy)

- Class: NEW `compaction-structural-realcount-spike` **0.60** (1st data point) — anchored to the sibling `compaction-tool-anchored-masking-spike` 0.60 (57.160): same Cat-4 compaction correctness-fix + MANDATORY-drive-through shape; LIGHTER code (a real-count branch mirroring an existing preclear pattern; no new masking mode / A-B harness / corpus) offset by the same fixed drive-through ceremony floor.
- **Agent-delegated: no** (parent-direct; agent_factor 1.0 → 3-segment).
- Bottom-up ~5-5.5 hr → class-calibrated commit ~3-3.3 hr (mult 0.60) → **actual ~3.5 hr** → ratio **~1.0 IN band**.
- Why on-budget: the code mirrored an existing pattern (preclear real-count) 1:1 → fast + low-risk; the drive-through ran smoothly first try (no re-drive, no orphan hunt — clean slate at start). The wall-clock was split evenly code/tests (~1.5 hr) · docs (~1 hr) · drive-through (~1 hr). Unlike the 57.120/160-style tiny-code-full-ceremony re-points, the real-count branch + parity test + factory + docstring fixes were enough real code that the 0.60 held (57.137 lesson — a >~3 hr real core holds the spike multiplier).
- **KEEP 0.60**; if a 2nd `compaction-structural-realcount-spike` lands > 1.20 re-point 0.75, if < 0.7 re-point 0.50.

## Q3 — What went well?

- **Day-0 三-prong 0 drift** — every root-cause file:line (`structural.py:192-193` / `preclear.py:178-181` / `loop.py:2282` / factory 65/244/295 / 6 counter-absent tests) matched real code exactly; the plan's root-cause table was verified before Day 1, so the code was mechanical.
- **The fix delta is a clean deterministic proof** — `test_no_counter_is_message_count_ratio_blind_to_tombstone` (N→N) vs `test_realcount_on_tombstone_reflects_reduction` (real reduction) on the SAME transcript IS the 57.160-Leg-1/2-vs-fixed contrast at unit level; plus preclear-parity.
- **Drive-through reproduced 57.160's own recorded config** — reusing the exact 57.160 Leg-3 staging but with preclear OFF made the before/after crisp (`22,925 → 10,584` where 57.160 showed `N→N`). No ambiguity about whether the fix worked.
- **KEY runtime finding upgraded understanding** — confirming `loop.py:2282` trusts `tokens_after` (no re-count) revealed the blindness was a real budget-tracking bug (the 4k→35k pathology), not just a display issue → stronger justification for default-on.

## Q4 — What to improve next sprint?

- The `messages_compacted = 0` on pure tombstone makes the marker read `· 0 msgs` alongside a big token drop (honest but slightly odd) — deferred to `AD-Compaction-Structural-TombstoneCount-Marker`; could have bundled it, but scope discipline (tokens_after only) kept the sprint tight and the AD focused.
- The drive-through hit `max_turns=8` before a single final summary answer — expected (bounded-burst ceiling) but a future compaction drive-through could raise `max_turns` via env to see the full completion + BOREALIS-9 echo in one burst.

## Q5 — Anti-pattern self-check

- AP-2 (side-track): no — the change is on the chat main-flow compactor, drive-through-verified. ✅
- AP-3 (scattering): no — Cat 4 stays in `context_mgmt/compactor/`. ✅
- AP-4 (Potemkin): no — the marker renders REAL reductions from real wire data (drive-through). ✅
- AP-6 (未來預留抽象): no — `token_counter` has an immediate real use (the factory injects it default-on); the `None` fallback is for existing callers, not speculation. ✅
- AP-8 (PromptBuilder): N/A (no prompt assembly). AP-11 (version suffix): none. ✅
- v2 lints 11/11 green.

## Q6 — Carryover ADs

- **`AD-Compaction-Structural-TombstoneCount-Marker`** (NEW) — mirror preclear's tombstoned count into `StructuralCompactor.messages_compacted` so the marker shows `· N msgs` on pure tombstone.
- `AD-Compaction-Preclear-PerTenant-Phase58` (per-tenant compaction policy; now also covers per-tenant real-count toggle).
- `AD-Compaction-Marker-Inspector-Trace-Correlate` (57.159 FE carryover, unrelated surface).
- 57.160 carryovers still open: flip `CHAT_COMPACTION_TOOL_ANCHORED_MASKING` default ON (data-gated) · behavioural-retention-under-real-traffic study.
- `AD-Compaction-ToolAnchored-Preclear-Phase58` (57.139) — **mechanism half now fully closed** (structural surfaces WITHOUT preclear); the default-on-preclear decision remains a separate, now-lower-priority item.

## Q7 — Gates (final sweep)

pytest **3206 passed + 6 skipped** (baseline 3202 +4) · mypy `src` **400** · run_all **11/11** green · black/isort/flake8 clean · LLM-SDK-leak clean · FE untouched (Vitest 927 / mockup 51). Drive-through STRONG PASS (real reductions −54%/−37% WITHOUT preclear).

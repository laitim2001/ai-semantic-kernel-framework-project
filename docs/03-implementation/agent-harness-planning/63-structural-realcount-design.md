---
title: 63-structural-realcount design note
purpose: Spike-extract design note from Sprint 57.161; documents the loop-consumes-tokens_after runtime invariant + the structural real token re-count fix (Cat 4)
category: V2 extension docs (post-22-sprint era)
created: 2026-07-07 (Sprint 57.161 Day 4 closeout)
sprint_source: 57.161
verified_ratio: ≥ 95% (per 8-Point Quality Gate)
status: Active
---

# 63-structural-realcount Design Note (Sprint 57.161 extract)

## 0. Spike Summary

- **Sprint scope** (US-1..US-5): make `StructuralCompactor.tokens_after` a REAL post-mask token re-count (mirroring `PreClearCompactor`) so tool-anchored observation masking surfaces its reduction on the chat-v2 marker AND relieves the loop budget WITHOUT the preclear lever; roll out default-on; drive-through the real reduction on chat-v2.
- **AD closed**: `AD-Compaction-Structural-RealTokenCount` (57.160 carryover). Closes the mechanism half of `AD-Compaction-ToolAnchored-Preclear-Phase58` (57.139 deferred).
- **Verified period**: 2026-07-07.
- **Calibration**: bottom-up ~5-5.5 hr → committed ~3-3.3 hr (class `compaction-structural-realcount-spike` 0.60, parent-direct agent_factor 1.0) → actual ~3.5 hr → ratio ~1.0 IN band (the drive-through was smooth first try — no re-drive; the code mirrored an existing pattern).
- **Verification**: pytest +4 (3 structural + 1 factory) · drive-through STRONG PASS (real reductions −54%/−37% WITHOUT preclear).

## 1. Decision Matrix (rollout posture — user AskUserQuestion pick)

| Option | Default behaviour | Blast radius | Decision |
|--------|-------------------|--------------|----------|
| **A: default-on correctness fix** ✅ | factory always injects `TiktokenCounter` → structural real-counts for all compaction | marker numbers + loop budget become accurate for ALL compaction | **CHOSEN** (user pick) — the message-count ratio is a genuine bug (pins the loop budget on tombstoning), not a behaviour choice; the `token_counter=None` fallback already gives byte-identical safety |
| B: env-gated (mirror 57.160) | new lever default OFF → byte-identical | opt-in only | rejected — an env lever would only preserve a WRONG default; the AD's stated purpose ("surface WITHOUT preclear") is defeated when default stays blind |

Why A ≠ 57.160's B: 57.160's tool-anchored masking was a behaviour CHOICE (which tool results to keep) with a retention tradeoff → warranted a measured retention floor first. Here the fix is a pure accuracy correction to a number that is currently wrong → no tradeoff to measure, and the `None` fallback preserves every existing test.

## 2. Verified Invariants

### 2.1 The loop consumes `tokens_after` as its ongoing budget — it does NOT re-count (US-3)
- **Implementation anchor**: `backend/src/agent_harness/orchestrator_loop/loop.py:2282` — `tokens_used = compaction_result.tokens_after` (then fed into the next turn's `TransientState.token_usage_so_far`, `loop.py:2343`). The marker is emitted from the same value (`loop.py:2288-2293` `ContextCompacted(tokens_after=...)`).
- **Behaviour**: `CompactionResult.tokens_after` is authoritative for BOTH the 57.159 chat-v2 marker AND the loop's ongoing token budget. The pre-57.161 `structural.py:192` comment "real Loop.run() will re-count via TokenCounter" was STALE (the loop trusts the value) — a Karpathy §3 stale-docstring, fixed this sprint.
- **Consequence**: `StructuralCompactor`'s message-count ratio, on in-place tombstoning, reported `tokens_after == tokens_before` → the loop budget stayed pinned → `should_compact` kept firing every turn without relief → the 57.159 `4k → 35k, 8 no-op compactions` pathology. The fix relieves the budget, not just the display.
- **Verification**: code read `loop.py:2280-2293`; drive-through — context bounded ~10-22k (budget relieved) vs 57.159's unbounded 4k→35k.

### 2.2 Structural real re-count mirrors PreClearCompactor when a counter is injected (US-1)
- **Implementation**: `backend/src/agent_harness/context_mgmt/compactor/structural.py` Step 5 — `token_counter is not None` → `tokens_after = int(tokens_before * count(kept)/count(orig))` (the `preclear.py:178-181` ratio-on-loop-scale formula; `TokenCounter.count(*, messages, tools)` keyword-only, `token_counter/_abc.py:43-49`); `None` → the verbatim legacy message-count ratio.
- **Behaviour**: injected → in-place tombstoning surfaces its real reduction; `None` → byte-identical pre-57.161 (existing 6 structural tests UNCHANGED). `messages_compacted` unchanged (drops-only) this sprint.
- **Verification**: `pytest tests/unit/agent_harness/context_mgmt/test_compactor_structural.py -q` (9 passed: 6 original + `test_realcount_on_tombstone_reflects_reduction` + `test_no_counter_is_message_count_ratio_blind_to_tombstone` + `test_realcount_matches_preclear_reduction`).
- **Test fixture**: `_LenCounter` (token count = str-content length) + `_tool_transcript(n_users)` (distinct args → no drop → only tombstoning → `len(kept)==original`) — mirrors the preclear test helpers.

### 2.3 Default-on factory injection (US-2)
- **Implementation**: `backend/src/api/v1/chat/_category_factories.py:make_chat_compactor` passes `token_counter=TiktokenCounter(model="gpt-4o")` to `StructuralCompactor(...)` — applies to both the bare-hybrid default AND the preclear-chained path. No new env lever.
- **Behaviour**: chat main flow always real-counts structural compaction. `TiktokenCounter` is a pure tokenizer (no provider SDK) → LLM-neutral (約束 3).
- **Verification**: `test_factory_injects_token_counter_into_structural` (asserts `compactor.structural.token_counter` is a `TiktokenCounter`, `accuracy()=="exact"`).

### 2.4 Drive-through: real reduction rendered WITHOUT preclear (US-4)
- **Behaviour**: real chat-v2 + Azure gpt-5.2 + 6× knowledge_search in ONE user turn (`CHAT_COMPACTION_TOOL_ANCHORED_MASKING=1` + budget 2500, **preclear OFF**) → the 57.159 marker renders `22,925 → 10,584 (−54%)` and `21,754 → 13,650 (−37%)`, where 57.160 Leg-1/2 (same config) rendered `N→N`. Context bounded ~10-22k; BOREALIS-9 retained through 7 compactions; run terminated at `max_turns=8` (bounded-burst ceiling, not a failure).
- **Verification**: manual drive-through (Playwright-driven); screenshot `sprint-57-161/artifacts/sprint-57-161-structural-realcount-marker.png` + observed-vs-intended in `sprint-57-161/progress.md` Day 3.

## 3. Cross-Category Contracts

No new contract / ABC. `Compactor` ABC (`compactor/_abc.py`) + `TokenCounter` ABC (`token_counter/_abc.py`) unchanged — `token_counter` is an instance-config ctor param of the concrete `StructuralCompactor` (impl detail), mirroring how `PreClearCompactor` already accepts one. `CompactionResult.tokens_after` semantics are unchanged (still "the post-compaction token count"); only its ACCURACY for tombstoning improved. `17-cross-category-interfaces.md §2.1` (Compactor / TokenCounter rows) needs no edit.

## 4. Open Invariants (deferred)

- [ ] **`messages_compacted` = tombstoned count in the marker** — `PreClearCompactor` reports `tombstoned` as `messages_compacted`; structural still reports drops-only (`· 0 msgs` on pure tombstone). Cosmetic → `AD-Compaction-Structural-TombstoneCount-Marker`.
- [ ] **Per-tenant real-count toggle** — folds into the C3 per-tenant compaction policy seam.
- [ ] **Flip `CHAT_COMPACTION_TOOL_ANCHORED_MASKING` default ON** (57.160 carryover, data-gated) — now that structural surfaces the reduction, the masking default-on decision is cleaner but still separate.
- [ ] **`SemanticCompactor` token accounting** — already real via the LLM summarize path; not in scope.

## 5. Rollback / Fallback

- **Sentinel**: any caller that constructs `StructuralCompactor()` without a counter (all existing unit tests, any non-chat consumer) is byte-identical to pre-57.161 — the `token_counter=None` branch IS the old code.
- **If default-on proves wrong**: revert the one-line factory injection in `_category_factories.py:make_chat_compactor` → the chat path reverts to the message-count ratio; the `structural.py` ctor param + branch can stay (dormant when no counter is passed). Estimated ~0.2 hr. The tests are additive (no revert needed).
- **Blast radius**: the ctor param defaults to None, so only the chat factory opts in; a factory revert affects only the chat main flow.

## 6. References

- Sprint plan: `phase-57-frontend-saas/sprint-57-161-plan.md`
- Sprint retrospective: `agent-harness-execution/phase-57/sprint-57-161/retrospective.md`
- CHANGE record: `claudedocs/4-changes/feature-changes/CHANGE-128-structural-compactor-real-token-count.md`
- Related: `preclear.py:178-181` (the real-count pattern mirrored) · `structural.py:192-193` (the fixed message-count ratio) · `loop.py:2282` (the loop-consumes-tokens_after invariant) · `62-tool-anchored-masking-design.md` §2.5 (the 57.160 finding this closes) · `.claude/rules/sprint-workflow.md §Scope-class matrix` (`compaction-structural-realcount-spike` 0.60)
- 04-anti-patterns.md AP-7 (Context Rot Ignored — the root motivation for compaction)

## Modification History

- 2026-07-07: Initial extract from Sprint 57.161 closeout (Day 4)

# CHANGE-128: StructuralCompactor real token re-count (surface masking without preclear)

**Date**: 2026-07-07
**Sprint**: 57.161
**Scope**: 範疇 4 (Context Management) — backend-only
**AD**: closes `AD-Compaction-Structural-RealTokenCount` (57.160 carryover) · engine-debt compaction range
**PR**: (pending) · **Branch**: `feature/sprint-57-161-compaction-structural-realcount` from `main` `204c4499`

## Problem

`StructuralCompactor.tokens_after` was a **message-count ratio** (`structural.py:192-193`: `int(tokens_before * len(kept)/original)`). The observation masker tombstones old tool bodies **in place** (list length preserved), so `len(kept) == original` → ratio `1.0` → `tokens_after == tokens_before` even when real token content shrank. Consequence: in Sprint 57.160, tool-anchored masking only surfaced a reduction on the chat-v2 marker when the preclear lever was ALSO enabled (Legs 1-2 without preclear = all `N→N`); worse, the loop's ongoing budget stayed pinned at the pre-mask value.

## Root Cause

`loop.py:2282` sets `tokens_used = compaction_result.tokens_after` — the loop **trusts** `tokens_after` as its ongoing budget and does **not** re-count (the `structural.py:192` "real Loop.run() will re-count via TokenCounter" comment was **stale/false**). So the message-count-ratio blindness was not cosmetic: on in-place tombstoning it reported no reduction, so `should_compact` kept firing every turn while the tracked budget never dropped → the 57.159-observed `4k → 35k, 8 no-op compactions` pathology. Only `PreClearCompactor` (`preclear.py:178-181`) did a real `TokenCounter` re-count.

## Solution

Mirror `PreClearCompactor`'s real re-count into `StructuralCompactor`:

- `StructuralCompactor.__init__(*, ..., token_counter: TokenCounter | None = None)`. When injected, Step 5 computes `tokens_after = int(tokens_before * count(kept)/count(orig))` (the exact `preclear.py:178-181` ratio-on-loop-scale formula); when `None`, it falls back to the legacy message-count ratio → existing tests + un-wired callers stay **byte-identical**.
- **Rollout A (default-on, user AskUserQuestion pick)**: `make_chat_compactor` always injects `TiktokenCounter(model="gpt-4o")` (already imported/used in the factory) into the structural stage — no new env lever. `TiktokenCounter` is a pure tokenizer (no provider SDK) → LLM-neutral.
- Fixed the stale `structural.py:192` comment (Karpathy §3) + class docstring point 6.

Backend-only; ZERO wire/codegen/frontend/migration. Code: `structural.py` + `_category_factories.py` (2 EDIT) + 4 new tests.

## Verification

- **Unit (the fix delta, deterministic)**: `test_realcount_on_tombstone_reflects_reduction` (counter → `tokens_after < tokens_before` on a tombstoned single-user-turn transcript) vs `test_no_counter_is_message_count_ratio_blind_to_tombstone` (no counter → `N→N` on the SAME input) + `test_realcount_matches_preclear_reduction` (parity with `PreClearCompactor`) + factory injection test. pytest **3206 + 6 skipped** (baseline 3202 +4) · mypy `src` 400 · run_all 11/11 · black/isort/flake8 clean · LLM-SDK-leak clean · FE untouched.
- **Drive-through STRONG PASS** (real chat-v2 + Azure gpt-5.2, 6× knowledge_search in ONE user turn, `CHAT_COMPACTION_TOOL_ANCHORED_MASKING=1` + budget 2500, **preclear OFF**): the 57.159 marker renders **REAL reductions WITHOUT preclear** — `22,925 → 10,584 (−54%)` + `21,754 → 13,650 (−37%)` — vs 57.160 Leg-1/2's `N→N`. Context bounded ~10-22k vs 57.159's 4k→35k; BOREALIS-9 retained through 7 compactions; run terminated cleanly at `max_turns=8`. Screenshot `sprint-57-161/artifacts/sprint-57-161-structural-realcount-marker.png`.

## Impact

Backend-only, Cat 4. The default-on real-count changes the marker numbers + loop budget for ALL compaction (strictly more accurate; non-tombstoning drops agree with the old ratio within int rounding). Byte-identical for any caller that constructs `StructuralCompactor()` without a counter. Follow-ons: `AD-Compaction-Structural-TombstoneCount-Marker` (mirror preclear's tombstoned count into `messages_compacted` so the marker shows `· N msgs` on pure tombstone instead of `· 0 msgs`); per-tenant real-count toggle (C3 seam). Closes the mechanism the 57.160 note deferred as `AD-Compaction-ToolAnchored-Preclear-Phase58`.

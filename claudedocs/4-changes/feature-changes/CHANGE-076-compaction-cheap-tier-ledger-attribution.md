# CHANGE-076: C2 — compaction cheap tier + `_compaction` cost-ledger attribution + compaction knobs

**Date**: 2026-06-12
**Sprint**: 57.109
**Scope**: Cat 4 (Context Mgmt) × Cat 1 (one yield site) × api/v1/chat × platform billing (observer only)

## Problem

Harness-deepening proposal §3.4 C2 (design note 24 first carryover): the semantic compactor's summarize call ran on the ACTION (strong) tier (`handler.py` passed `chat_client = profile.action` to `make_chat_compactor`), and its LLM usage was captured NOWHERE — the call bypasses loop events, so compaction cost was invisible to the cost ledger (verification got its `_verification` attribution in 57.82; compaction never did).

## Root Cause

Construction-time DI predated the ModelProfile split (57.97) — the compactor simply inherited the loop client. The cost gap was structural: `SemanticCompactor._summarise` returned only the summary text; no consumer of the summarize `ChatResponse.usage` existed.

## Solution

1. **Retier (one line)**: `make_chat_compactor(profile.cheap)` (handler.py:466 region) — cheap-unset env keeps `cheap is action` (byte-identical, the 57.97 invariant); the C1 per-tenant model policy now governs compaction tier too.
2. **Attribution (57.82 mirror, better carrier)**: `CompactionResult` +`input_tokens`/`output_tokens`/`model` (semantic captures the successful attempt's usage; hybrid forwards on the merged result). **D-DAY1-1**: usage rides `ContextCompacted` server-side dataclass fields (NOT the planned LoopCompleted mirror — 30+ ctor sites and early terminations would drop cost); wire/codegen untouched (count 24). The chat router accumulates off the events, enqueues `sub_type_suffix="_compaction"` at LoopCompleted (model = the cheap tier's live `response.model`, fallback loop model), and folds compaction tokens into the quota actual (D12).
3. **Knobs**: `CHAT_COMPACTION_TOKEN_BUDGET` (default 100k) + `CHAT_COMPACTION_KEEP_RECENT_TURNS` (default 5, min 1 — `[-0]` would silently full-keep), both threaded to ALL THREE compactors (D13 — the factory previously passed budget only to the hybrid while the sub-strategies used their own defaults).

**NOT done (documented)**: memory extraction stays action (benchmark-gated; design note 24 invariant stays open); resume path has no billing observers (pre-existing for loop+verification too — candidate `AD-Resume-Billing-Observers`); failed-retry-attempt usage (attempts raise before usage exists); `context_compacted` FE rendering.

## Verification

Unit/integration: +23 tests, 0 deletions (tier pins ×2 · semantic capture ×2 · hybrid forward · knobs ×11 · cost-ledger integration ×4 incl. multi-compaction single-row accumulation + quota fold). Full pytest 2485 ≡ 2462+23; mypy 0/359; run_all 10/10 (no codegen diff).

Drive-through (real UI + real Azure, zero dev-login): keep=1 + budget=2000 + one B1 mid-run injection → `context_compacted` **9824→2679 (8 messages, 3.5s real summarize)** → billing_outbox `_compaction` at **`gpt-5.4-mini-2026-03-17`** (action is gpt-5.2) → cost_ledger `..._compaction_input/_output` $0.000195/$0.0006705 → final answer still carries the injected fact (BLUEFIN) + llm_judge 0.99. Evidence: sprint-57-109 progress.md Day 3 + artifacts.

**Load-bearing dt finding (D-DAY3-1)**: semantic compaction was a latent main-flow NO-OP since 52.1 — chat continuity lives in Cat 3 memory (one user message per run), so the user-turn-anchored cutoff (`len(user_indices) > 5`) never engaged. The keep knob makes it deployable; carryover `AD-Semantic-Compaction-User-Turn-Anchor` proposes a message-count anchor in a future Cat 4 slice.

## Impact

Backend-only. No DB/migration, no wire/codegen change, no FE change, `loop.py` diff = one yield site. Closes proposal §3.4 C2 — C-family 3/3 done.

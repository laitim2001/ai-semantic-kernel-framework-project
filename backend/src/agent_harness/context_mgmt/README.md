# Category 4 — Context Management

**ABCs**: `Compactor`, `TokenCounter`, `PromptCacheManager` (in `_abc.py`)
**Spec**: `01-eleven-categories-spec.md` §範疇 4
**Implementation Phase**: 52.1
**V1 Alignment**: 5% → V2 target 75%+

## Responsibility

- **Compactor**: Detects context rot (>75% token budget); summarizes oldest observations; observation masking
- **TokenCounter**: Per-provider tokenizer abstraction; called from PromptBuilder + Loop
- **PromptCacheManager**: Plans cache breakpoint placement (Anthropic-style cache_control)

## Critical anti-pattern to prevent

**AP-7 (Context Rot Ignored)**: V1 ignored token bloat — 10+ turn
conversations degraded badly. V2 calls `Compactor.compact_if_needed()`
EVERY loop turn. Mandatory.

## Cross-category interaction (per 17.md §7.1)

Compactor → Subagent: NO direct ABC call. Compactor emits prompt hint
"consider delegation"; LLM decides via task_spawn tool.

## Sprint roadmap

| Sprint | Adds |
|--------|------|
| 49.1   | ABC stub (this) |
| 52.1   | Compactor + masking strategies + provider tokenizer adapters + cache planner |

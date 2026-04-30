# adapters/_base — ChatClient ABC

**Module owner**: 10-server-side-philosophy.md §原則 2 (LLM Provider Neutrality)
**Single-source**: 17.md §2.1
**Implementation Phase**: 49.3 (Azure adapter); ABC stable from 49.1

## Purpose

Single LLM interface used by all `agent_harness/` categories.
Concrete adapters in sibling dirs (`azure_openai/`, `anthropic/`,
`openai/`, `maf/`) translate to/from provider-native formats.

## Why this matters

If `agent_harness/` could import openai/anthropic directly, switching
providers would require changing dozens of files. With this ABC,
switching = config change only (target SLO: < 2 weeks for full migration
+ 1 month for quality re-alignment per philosophy doc).

## Strict rule

**`agent_harness/**` MUST NEVER `import openai` / `import anthropic`.**

CI lint (Sprint 49.4 onwards) fails any PR that violates this.
Tests under `agent_harness/` use `MockChatClient` from `_testing/`.

## ABC surface (7 methods)

- `chat()` — core call
- `stream()` — SSE-compatible streaming
- `count_tokens()` — for Cat 4 token budget enforcement
- `get_pricing()` — per-tenant cost tracking
- `supports_feature()` — multi-provider routing capability check
- `model_info()` — model metadata for routing / cache keys / metrics

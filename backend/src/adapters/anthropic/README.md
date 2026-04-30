# adapters/anthropic — Anthropic Claude Adapter (RESERVED)

**Status**: Reserved placeholder at Sprint 49.1.
**Implementation**: Phase 50+ if/when company approves Claude usage.

## Purpose

Adapter to call Anthropic Claude (claude-3.7-sonnet, claude-haiku, etc.)
via Anthropic SDK. Honors `ChatClient` ABC.

## Why reserved now

Even though we don't use Claude in production yet, V2 architecture is
**provider-neutral** by design. Reserving this directory:

1. Documents the intent for future readers
2. Lets developers test multi-provider routing in dev
3. Lets contract tests validate the ABC isn't accidentally Azure-specific

## Implementation when activated

Same SOP as `azure_openai/` (see `.claude/rules/adapters-layer.md` §新
Provider 上架 SOP — 5 steps + contract tests).

Provider-specific notes:
- Anthropic supports prompt caching (`cache_control` ephemeral)
- Anthropic supports `thinking` block (extended reasoning)
- Tokenizer: claude-tokenizer (NOT tiktoken)
- Stop reasons: `end_turn` / `tool_use` / `max_tokens` / `stop_sequence`

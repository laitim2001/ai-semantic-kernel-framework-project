# Category 5 — Prompt Construction

**ABC**: `PromptBuilder` (in `_abc.py`)
**Spec**: `01-eleven-categories-spec.md` §範疇 5
**Implementation Phase**: 52.2
**V1 Alignment**: 20% → V2 target 75%+

## Responsibility

Single entry point for LLM message assembly. Layers:

1. **System** — global instructions
2. **Tenant memory** — tenant-scoped policies/context
3. **Role memory** — role-scoped guidelines
4. **User memory** — user preferences + session refs
5. **Session history** — current conversation
6. **User input** — current turn

Plus: inject cache breakpoints (Anthropic-style cache_control) per
`PromptCacheManager` (Cat 4) recommendations.

## Critical anti-pattern to prevent

**AP-8 (No Centralized PromptBuilder)**: V1 had prompt assembly
scattered across LLM call sites. V2 enforces:

- ❌ NO `messages = [{"role": ...}, ...]` ad-hoc construction
- ✅ ALL LLM calls go through `PromptBuilder.build()`
- Lint enforced in Sprint 49.4

## Sprint roadmap

| Sprint | Adds |
|--------|------|
| 49.1   | ABC stub (this) |
| 52.2   | Layered builder + memory injection + cache plan integration + tone profiles |

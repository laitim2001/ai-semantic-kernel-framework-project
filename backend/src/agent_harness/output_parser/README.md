# Category 6 — Output Parsing

**ABC**: `OutputParser` (in `_abc.py`)
**Spec**: `01-eleven-categories-spec.md` §範疇 6
**Implementation Phase**: 50.1
**V1 Alignment**: 75% → V2 target 90%+

## Responsibility

Convert provider-neutral `ChatResponse` into uniform `ParsedOutput`
(text + tool_calls + stop_reason). Emits `ToolCallRequested` events
for downstream Tool Executor (Cat 2).

## Critical: native tool_calls only

V2 uses native tool calling (function calling / Anthropic tools) via
the LLM-neutral `ChatResponse` contract. **No regex / JSON parsing of
free-text** — adapters convert provider-native tool calls to
`ToolCall` objects before reaching OutputParser.

## Sprint roadmap

| Sprint | Adds |
|--------|------|
| 49.1   | ABC stub (this) |
| 50.1   | Parser implementation (parses ChatResponse into ParsedOutput; emits events) |

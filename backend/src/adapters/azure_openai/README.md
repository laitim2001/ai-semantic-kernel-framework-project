# adapters/azure_openai — Azure OpenAI Adapter (V2 Primary)

**Status**: Skeleton only at Sprint 49.1; implementation in **Sprint 49.3**.

## Why this is V2 primary

Per project context: Azure OpenAI is the only currently approved LLM
provider for the company. V2 is built around it but designed
provider-neutrally so future Claude / OpenAI direct enablement is
config-only.

## Sprint 49.3 deliverables

- `adapter.py` — `AzureOpenAIAdapter(ChatClient)` implementing 7 methods
- `config.py` — endpoint / api_version / deployment_name handling
- `error_mapper.py` — Azure native errors → `ProviderError` enum
- `tool_converter.py` — `ToolSpec` → Azure function calling format
- `tests/` — contract tests (every adapter must pass these)

See `.claude/rules/adapters-layer.md` §Azure OpenAI 特定細節 for
endpoint format, deployment name handling, retry/timeout settings.

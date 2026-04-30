# features/tools

UI components for **Category 2 (Tool Layer)** — tool calls + results.

**Backend pair**: `backend/src/agent_harness/tools/`
**First impl**: Phase 51.1 (alongside backend Tool Layer impl)

## Components (planned)

- `<ToolCallCard>` — single tool call viewer (input / output / duration / status)
- `<ToolRegistryBrowser>` — list of registered ToolSpecs (admin view)
- `<ConcurrencyBadge>` — visual hint for ConcurrencyPolicy (sequential / read_only / all_parallel)

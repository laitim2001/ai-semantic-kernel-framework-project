# Query Engine — Claude Code CLI

> Source: `src/query.ts`, `src/QueryEngine.ts`, `src/query/`, `src/services/api/`

## Overview

The query engine is the central execution loop that transforms user messages into API calls, manages tool execution, and handles conversation state. Implemented in `src/query.ts` (single-turn) and `src/QueryEngine.ts` (multi-turn wrapper).

## QueryParams Contract (`src/query.ts`)

```typescript
type QueryParams = {
  messages: Message[]
  systemPrompt: SystemPrompt
  userContext: { [k: string]: string }
  systemContext: { [k: string]: string }
  canUseTool: CanUseToolFn
  toolUseContext: ToolUseContext
  fallbackModel?: string
  querySource: QuerySource
  maxOutputTokensOverride?: number
  maxTurns?: number
  taskBudget?: { total: number }
  deps?: QueryDeps
}
```

## Query Lifecycle

### Step 1: Initialization
The loop initializes mutable `State` and a `budgetTracker`. `buildQueryConfig()` (`src/query/config.ts`) snapshots all feature flags once at entry — preventing mid-loop changes.

### Step 2: Message Preparation
Before each API call:
1. `autoCompactIfNeeded()` — check context window threshold
2. `getAttachmentMessages()` — prepend CLAUDE.md, memory files, MCP instructions
3. `normalizeMessagesForAPI()` — strip internal metadata, ensure user/assistant alternation
4. `prependUserContext()` / `appendSystemContext()` — inject environment context

### Step 3: API Call (`src/services/api/claude.ts`)
`streamQuery()` calls `getAnthropicClient()` (creates provider-appropriate client: direct API / Bedrock / Vertex / Foundry), then `client.beta.messages.stream()` with streaming.

### Step 4: Stream Processing
The generator yields events: `content_block_start/delta` (text), `tool_use` blocks (queued for execution), `message_delta` with `stop_reason`.

### Step 5: Tool Execution
When `stop_reason === 'tool_use'`:
1. `StreamingToolExecutor` processes tool calls
2. Each tool's `canUseTool` permission check applied
3. Tool results injected as `tool_result` content blocks
4. Loop continues with results appended

### Step 6: Termination
Loop terminates when: `end_turn` with no tools, `max_tokens`, context window exceeded, user abort, or `maxTurns` exceeded.

## Retry Logic (`src/services/api/withRetry.ts`)

| Error Type | Behavior |
|------------|----------|
| HTTP 401 | Refresh OAuth token, retry |
| HTTP 429 (rate limit) | Retry with backoff unless ClaudeAI subscriber |
| HTTP 529 (overload) | Retry up to 3x for foreground sources; fallback model for Opus |
| ECONNRESET/EPIPE | Disable keep-alive, retry |
| Context overflow (400) | Reduce `maxTokensOverride`, retry |
| Fast mode rejected | Permanently disable fast mode, retry |

**Backoff formula**: `baseDelay = min(500ms * 2^(attempt-1), 32000ms)` + jitter.

**Opus fallback**: After 3 consecutive 529s, `FallbackTriggeredError` triggers switch to fallback model (transparent to user).

**Fast mode cooldown**: Short retry-after (< 20s) → wait with fast mode active. Long → cooldown 10+ minutes, switch to standard speed.

## QuerySource Tagging

Every call site tags with `QuerySource` string. Controls:
- Which calls retry on 529 (only foreground)
- Analytics attribution
- Compaction guards (compact/session_memory sources skip autocompact)

Key sources: `repl_main_thread`, `sdk`, `agent:custom`, `compact`, `extract_memories`, `session_memory`, `hook_agent`.

## Message Types

| Type | Purpose |
|------|---------|
| `UserMessage` | Human input or tool results |
| `AssistantMessage` | Model response (wraps BetaMessage) |
| `AttachmentMessage` | Injected context (CLAUDE.md) — not sent to API |
| `SystemCompactBoundaryMessage` | Marks compaction points |
| `TombstoneMessage` | Marks deleted content |

## Architecture Flow

```
REPL/SDK caller
    │
    ▼
query() → queryLoop()
    ├── buildQueryConfig() — snapshot feature flags
    ├── autoCompactIfNeeded()
    ├── getAttachmentMessages()
    ├── normalizeMessagesForAPI()
    │
    ▼
streamQuery() → withRetry() → client.beta.messages.stream()
    │
    ▼
Streaming event loop
    ├── Text deltas → yield StreamEvent
    ├── tool_use → StreamingToolExecutor → tool.call()
    └── end_turn → return Terminal
```

## Key Design Decisions

1. **Generator-based streaming**: `query()` is an `AsyncGenerator`, enabling incremental UI updates
2. **Immutable config snapshot**: `buildQueryConfig()` prevents mid-loop feature flag drift
3. **QuerySource tagging**: Fine-grained retry control prevents retry amplification
4. **Fallback model pattern**: Opus → Sonnet automatic fallback after 529s
5. **Thinking block enforcement**: Query loop enforces API-required thinking block lifecycle rules

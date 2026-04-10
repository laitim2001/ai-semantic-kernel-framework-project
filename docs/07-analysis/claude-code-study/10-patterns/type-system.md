# Type System Patterns

> Claude Code leverages TypeScript's type system extensively, using discriminated unions, branded types, generated protobuf types, Zod schemas, and compile-time assertions to achieve type safety across a complex multi-layered architecture.

## Overview

The type system in Claude Code serves multiple roles: it enforces exhaustive handling of state machines, validates external data at runtime via Zod schemas, provides compile-time safety for permission systems, and bridges the gap between the TypeScript codebase and protobuf-defined analytics events. The codebase uses modern TypeScript 5 patterns including `satisfies`, `const` assertions, template literal types, and conditional types.

---

## Key Type Files

| File | Purpose |
|------|---------|
| `src/Tool.ts` | Tool interface (47 members), `ToolUseContext` (55 fields), permission types |
| `src/Task.ts` | Task types, status lifecycle, ID generation |
| `src/types/permissions.ts` | Permission modes, rules, behaviors |
| `src/types/hooks.ts` | Hook event types, Zod schemas, compile-time assertions |
| `src/types/message.ts` | Message union types |
| `src/types/ids.ts` | Branded ID types (SessionId, AgentId) |
| `src/types/command.ts` | Command type definitions |
| `src/types/textInputTypes.ts` | `BaseTextInputProps` (31 fields), `QueuedCommand` (13 fields) |
| `src/types/logs.ts` | `Entry` union (20 variants), `LogOption`, `SerializedMessage` |
| `src/types/plugin.ts` | Plugin system types |
| `src/types/generated/` | Protobuf-generated event types |
| `src/schemas/hooks.ts` | Hook configuration schemas |

---

## 1. Core Types

### 1.1 Discriminated Union Patterns

#### Vim State Machine (`src/vim/types.ts`)

The most comprehensive example of discriminated unions — an 11-variant command state:

```typescript
export type VimState =
  | { mode: 'INSERT'; insertedText: string }
  | { mode: 'NORMAL'; command: CommandState }

export type CommandState =
  | { type: 'idle' }
  | { type: 'count'; digits: string }
  | { type: 'operator'; op: Operator; count: number }
  | { type: 'operatorCount'; op: Operator; count: number; digits: string }
  | { type: 'operatorFind'; op: Operator; count: number; find: FindType }
  | { type: 'operatorTextObj'; op: Operator; count: number; scope: TextObjScope }
  | { type: 'find'; find: FindType; count: number }
  | { type: 'g'; count: number }
  | { type: 'operatorG'; op: Operator; count: number }
  | { type: 'replace'; count: number }
  | { type: 'indent'; dir: '>' | '<'; count: number }
```

Each variant carries exactly the data needed for that state — no optional fields. TypeScript's exhaustive `switch` ensures every state is handled in transition functions.

#### Recorded Changes

```typescript
export type RecordedChange =
  | { type: 'insert'; text: string }
  | { type: 'operator'; op: Operator; motion: string; count: number }
  | { type: 'operatorTextObj'; op: Operator; objType: string; scope: TextObjScope; count: number }
  | { type: 'operatorFind'; op: Operator; find: FindType; char: string; count: number }
  | { type: 'replace'; char: string; count: number }
  | { type: 'x'; count: number }
  | { type: 'toggleCase'; count: number }
  | { type: 'indent'; dir: '>' | '<'; count: number }
  | { type: 'openLine'; direction: 'above' | 'below' }
  | { type: 'join'; count: number }
```

#### Task Types (`src/Task.ts`)

```typescript
export type TaskType = 'local_bash' | 'local_agent' | 'remote_agent' | 'in_process_teammate' | 'local_workflow' | 'monitor_mcp' | 'dream'
export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'killed'

export function isTerminalTaskStatus(status: TaskStatus): boolean {
  return status === 'completed' || status === 'failed' || status === 'killed'
}
```

#### Lock Result Types (`src/utils/computerUse/computerUseLock.ts`)

```typescript
export type AcquireResult =
  | { readonly kind: 'acquired'; readonly fresh: boolean }
  | { readonly kind: 'blocked'; readonly by: string }

export type CheckResult =
  | { readonly kind: 'free' }
  | { readonly kind: 'held_by_self' }
  | { readonly kind: 'blocked'; readonly by: string }
```

#### Hook Results (`src/types/hooks.ts`)

```typescript
export type PermissionRequestResult =
  | { behavior: 'allow'; updatedInput?: Record<string, unknown>; updatedPermissions?: PermissionUpdate[] }
  | { behavior: 'deny'; message?: string; interrupt?: boolean }
```

### 1.2 Type-Safe ID System

#### Task IDs (`src/Task.ts`)

```typescript
const TASK_ID_PREFIXES: Record<string, string> = {
  local_bash: 'b', local_agent: 'a', remote_agent: 'r',
  in_process_teammate: 't', local_workflow: 'w', monitor_mcp: 'm', dream: 'd',
}

// Case-insensitive-safe: 36^8 ~ 2.8 trillion combinations
const TASK_ID_ALPHABET = '0123456789abcdefghijklmnopqrstuvwxyz'
```

#### Branded ID Types (`src/types/ids.ts`)

Two branded types using TypeScript's intersection-with-`__brand` pattern to prevent accidental mixing of session and agent IDs at compile time:

```typescript
type SessionId = string & { readonly __brand: 'SessionId' }
type AgentId = string & { readonly __brand: 'AgentId' }
```

**Casting Functions (unsafe)**:

```typescript
function asSessionId(id: string): SessionId   // Raw cast, no validation
function asAgentId(id: string): AgentId       // Raw cast, no validation
```

**Validation Function — `toAgentId()` (safe)**:

```typescript
const AGENT_ID_PATTERN = /^a(?:.+-)?[0-9a-f]{16}$/

function toAgentId(s: string): AgentId | null {
  return AGENT_ID_PATTERN.test(s) ? (s as AgentId) : null
}
```

Format: `a` + optional `<label>-` + 16 hex characters. Examples: `a0123456789abcdef` (unlabeled), `aworker-0123456789abcdef` (labeled). Returns `null` if the string doesn't match. This is the only validated branding function.

**Usage in Computer Use Lock**:

```typescript
const lock: ComputerUseLock = {
  sessionId: getSessionId(),
  pid: process.pid,
  acquiredAt: Date.now(),
}
```

---

## 2. Tool System Types

### 2.1 ToolUseContext — Complete 55-Field Inventory (`src/Tool.ts`)

The largest interface in the codebase, defining the execution context for every tool call. 19 required fields, 36 optional fields.

#### Group 1: Options (nested `options` object) — 15 fields

| # | Field | Type | Req? | Purpose |
|---|-------|------|------|---------|
| 1 | `options.commands` | `Command[]` | Yes | Available slash commands registered in the session |
| 2 | `options.debug` | `boolean` | Yes | Enables debug-level logging and diagnostics |
| 3 | `options.mainLoopModel` | `string` | Yes | Model identifier used for the main conversation loop |
| 4 | `options.tools` | `Tools` | Yes | Complete set of tools available to the agent |
| 5 | `options.verbose` | `boolean` | Yes | Controls verbose output rendering in UI |
| 6 | `options.thinkingConfig` | `ThinkingConfig` | Yes | Extended thinking budget and token configuration |
| 7 | `options.mcpClients` | `MCPServerConnection[]` | Yes | Active MCP server connections for tool dispatch |
| 8 | `options.mcpResources` | `Record<string, ServerResource[]>` | Yes | MCP server resources indexed by server name |
| 9 | `options.isNonInteractiveSession` | `boolean` | Yes | True for SDK/print mode (no REPL); gates interactive features |
| 10 | `options.agentDefinitions` | `AgentDefinitionsResult` | Yes | Loaded agent definitions from the agents directory |
| 11 | `options.maxBudgetUsd` | `number` | No | Maximum API spend cap in USD for the session |
| 12 | `options.customSystemPrompt` | `string` | No | Custom system prompt that replaces the default |
| 13 | `options.appendSystemPrompt` | `string` | No | Additional system prompt appended after the main one |
| 14 | `options.querySource` | `QuerySource` | No | Override querySource for analytics tracking |
| 15 | `options.refreshTools` | `() => Tools` | No | Callback to get latest tools after MCP servers connect mid-query |

#### Group 2: Core Runtime — 4 fields

| # | Field | Type | Req? | Purpose |
|---|-------|------|------|---------|
| 16 | `abortController` | `AbortController` | Yes | Cancellation signal for the current query/turn |
| 17 | `readFileState` | `FileStateCache` | Yes | LRU cache of file contents to avoid redundant disk reads |
| 18 | `messages` | `Message[]` | Yes | Full conversation message history for the current thread |
| 19 | `toolUseId` | `string` | No | ID of the current tool_use block being executed |

#### Group 3: App State Management — 3 fields

| # | Field | Type | Req? | Purpose |
|---|-------|------|------|---------|
| 20 | `getAppState()` | `() => AppState` | Yes | Returns the current immutable application state snapshot |
| 21 | `setAppState` | `(f: (prev: AppState) => AppState) => void` | Yes | Updates application state via a reducer function |
| 22 | `setAppStateForTasks` | `(f: (prev: AppState) => AppState) => void` | No | Always-shared setAppState for session-scoped infrastructure; always reaches root store even for async subagents |

#### Group 4: UI / Interactive Features — 8 fields

| # | Field | Type | Req? | Purpose |
|---|-------|------|------|---------|
| 23 | `setToolJSX` | `SetToolJSXFn` | No | Sets custom JSX to render in the tool output area (REPL only) |
| 24 | `addNotification` | `(notif: Notification) => void` | No | Pushes a notification to the REPL notification queue |
| 25 | `appendSystemMessage` | `(msg: ...) => void` | No | Appends a UI-only system message to the REPL message list (stripped at API boundary) |
| 26 | `sendOSNotification` | `(opts: { message: string; notificationType: string }) => void` | No | Sends an OS-level notification (iTerm2, Kitty, Ghostty, bell) |
| 27 | `handleElicitation` | `(serverName, params, signal) => Promise<ElicitResult>` | No | Handler for URL elicitations triggered by MCP tool call errors (-32042) |
| 28 | `openMessageSelector` | `() => void` | No | Opens the interactive message selector UI in REPL mode |
| 29 | `requestPrompt` | `(sourceName, toolInputSummary?) => (request) => Promise<PromptResponse>` | No | Callback factory for requesting interactive prompts from the user (REPL only) |
| 30 | `setStreamMode` | `(mode: SpinnerMode) => void` | No | Controls the spinner/stream mode displayed during tool execution |

#### Group 5: Memory / Skills — 4 fields

| # | Field | Type | Req? | Purpose |
|---|-------|------|------|---------|
| 31 | `nestedMemoryAttachmentTriggers` | `Set<string>` | No | Trigger patterns that cause CLAUDE.md files to be injected as nested memory |
| 32 | `loadedNestedMemoryPaths` | `Set<string>` | No | CLAUDE.md paths already injected this session; dedup guard |
| 33 | `dynamicSkillDirTriggers` | `Set<string>` | No | Trigger patterns for dynamically loading skill directories |
| 34 | `discoveredSkillNames` | `Set<string>` | No | Skill names surfaced via skill_discovery (telemetry only) |

#### Group 6: Agent Identity — 4 fields

| # | Field | Type | Req? | Purpose |
|---|-------|------|------|---------|
| 35 | `agentId` | `AgentId` | No | Unique ID for subagents; hooks use this to distinguish subagent calls |
| 36 | `agentType` | `string` | No | Subagent type name; main thread falls back to `getMainThreadAgentType()` |
| 37 | `userModified` | `boolean` | No | Whether the user has modified input/context since last turn |
| 38 | `requireCanUseTool` | `boolean` | No | When true, `canUseTool` must always be called even when hooks auto-approve |

#### Group 7: State Setters (Callbacks) — 8 fields

| # | Field | Type | Req? | Purpose |
|---|-------|------|------|---------|
| 39 | `setInProgressToolUseIDs` | `(f: (prev: Set<string>) => Set<string>) => void` | Yes | Tracks which tool_use IDs are currently executing |
| 40 | `setResponseLength` | `(f: (prev: number) => number) => void` | Yes | Updates the running count of response tokens for budget tracking |
| 41 | `setHasInterruptibleToolInProgress` | `(v: boolean) => void` | No | Signals whether a cancellable tool is running (REPL only) |
| 42 | `pushApiMetricsEntry` | `(ttftMs: number) => void` | No | Ant-only: pushes API metrics entry for OTPS tracking |
| 43 | `setSDKStatus` | `(status: SDKStatus) => void` | No | Updates SDK lifecycle status for the Agent SDK entrypoint |
| 44 | `setConversationId` | `(id: UUID) => void` | No | Sets the conversation ID (UUID) for session tracking |
| 45 | `updateFileHistoryState` | `(updater: (prev: FileHistoryState) => FileHistoryState) => void` | Yes | Updates file edit history state for undo/attribution tracking |
| 46 | `updateAttributionState` | `(updater: (prev: AttributionState) => AttributionState) => void` | Yes | Updates commit attribution state for Co-Authored-By tracking |

#### Group 8: Limits / Decisions — 4 fields

| # | Field | Type | Req? | Purpose |
|---|-------|------|------|---------|
| 47 | `fileReadingLimits` | `{ maxTokens?: number; maxSizeBytes?: number }` | No | Configurable caps on file reading |
| 48 | `globLimits` | `{ maxResults?: number }` | No | Configurable cap on glob search result count |
| 49 | `toolDecisions` | `Map<string, { source; decision; timestamp }>` | No | Cached permission decisions for tool uses |
| 50 | `onCompactProgress` | `(event: CompactProgressEvent) => void` | No | Callback for context compaction lifecycle events |

#### Group 9: Query / Prompt — 3 fields

| # | Field | Type | Req? | Purpose |
|---|-------|------|------|---------|
| 51 | `queryTracking` | `QueryChainTracking` | No | Tracks query chain depth for nested/recursive tool invocations |
| 52 | `criticalSystemReminder_EXPERIMENTAL` | `string` | No | Experimental field for injecting critical system reminders |
| 53 | `preserveToolUseResults` | `boolean` | No | Preserve `toolUseResult` on messages for in-process teammates |

#### Group 10: Subagent / Advanced — 3 fields

| # | Field | Type | Req? | Purpose |
|---|-------|------|------|---------|
| 54 | `localDenialTracking` | `DenialTrackingState` | No | Local denial tracking for async subagents (mutable, in-place) |
| 55 | `contentReplacementState` | `ContentReplacementState` | No | Per-thread content replacement state for tool result budget |
| 56 | `renderedSystemPrompt` | `SystemPrompt` | No | Parent's rendered system prompt frozen at turn start for fork subagents |

#### ToolUseContext Architecture Notes

1. **REPL vs SDK split**: 8 fields are REPL-only (`setToolJSX`, `addNotification`, `appendSystemMessage`, `sendOSNotification`, `openMessageSelector`, `requestPrompt`, `setHasInterruptibleToolInProgress`, `setStreamMode`). SDK/print mode leaves these undefined.
2. **Subagent context**: `createSubagentContext` in `forkSubagent.ts` creates a derived context where `setAppState` becomes a no-op for async agents, `setAppStateForTasks` always reaches the root store, and `contentReplacementState` is cloned from parent.
3. **Memory dedup**: `loadedNestedMemoryPaths` exists because `readFileState` is an LRU that evicts entries. Without this Set, the same CLAUDE.md could be injected dozens of times.
4. **Prompt cache preservation**: `renderedSystemPrompt` is frozen at turn start so fork subagents share the parent's prompt cache.
5. **Denial accumulation**: `localDenialTracking` is mutable (in-place) because async subagents' `setAppState` is a no-op.

#### ToolUseContext Imported Types

| Type | Source Module |
|------|--------------|
| `FileStateCache` | `utils/fileStateCache.js` |
| `AppState` | `state/AppState.js` |
| `SetToolJSXFn` | `Tool.ts` (line 103) |
| `Notification` | `context/notifications.js` |
| `SpinnerMode` | `components/Spinner.js` |
| `SDKStatus` | `entrypoints/agentSdkTypes.js` |
| `QuerySource` | `constants/querySource.js` |
| `AgentId` | `types/ids.js` |
| `ThinkingConfig` | `utils/thinking.js` |
| `MCPServerConnection` | `services/mcp/types.js` |
| `ServerResource` | `services/mcp/types.js` |
| `AgentDefinitionsResult` | `tools/AgentTool/loadAgentsDir.js` |
| `Command` | `commands.js` |
| `Message` | `types/message.js` |
| `DenialTrackingState` | `utils/permissions/denialTracking.js` |
| `ContentReplacementState` | `utils/toolResultStorage.js` |
| `SystemPrompt` | `utils/systemPromptType.js` |
| `FileHistoryState` | `utils/fileHistory.js` |
| `AttributionState` | `utils/commitAttribution.js` |
| `QueryChainTracking` | `Tool.ts` (line 90) |
| `CompactProgressEvent` | `Tool.ts` (line 150) |
| `PromptRequest` / `PromptResponse` | `types/hooks.js` |
| `ElicitRequestURLParams` / `ElicitResult` | `@modelcontextprotocol/sdk/types.js` |

### 2.2 Tool Interface — Complete 47-Member Inventory (`src/Tool.ts`)

The `Tool<Input, Output, P>` type is the central interface for all tools. Generic over three type parameters:

| Parameter | Constraint | Default | Purpose |
|-----------|-----------|---------|---------|
| `Input` | `extends AnyObject` | `AnyObject` | Zod schema for tool input |
| `Output` | (none) | `unknown` | Type of tool result data |
| `P` | `extends ToolProgressData` | `ToolProgressData` | Progress event payload type |

Where `AnyObject = z.ZodType<{ [key: string]: unknown }>`.

#### Core Identity (4 members)

| # | Member | Type | Default | Purpose |
|---|--------|------|---------|---------|
| 1 | `name` | `readonly string` | (required) | Primary tool name for lookup and API registration |
| 2 | `aliases` | `string[]` | `undefined` | Alternative names for backwards compatibility |
| 3 | `searchHint` | `string` | `undefined` | One-line capability phrase for ToolSearch keyword matching |
| 4 | `inputSchema` | `readonly Input` | (required) | Zod schema that validates the tool's input parameters |

#### Schema & Validation (4 members)

| # | Member | Type | Default | Purpose |
|---|--------|------|---------|---------|
| 5 | `inputJSONSchema` | `readonly ToolInputJSONSchema` | `undefined` | Raw JSON Schema for MCP tools |
| 6 | `outputSchema` | `z.ZodType<unknown>` | `undefined` | Zod schema for output validation |
| 7 | `inputsEquivalent` | `(a, b) => boolean` | `undefined` | Custom equality check for duplicate tool call detection |
| 8 | `validateInput` | `(input, context) => Promise<ValidationResult>` | `undefined` | Pre-execution validation that can reject with error message and code |

#### Execution (2 members)

| # | Member | Type | Default | Purpose |
|---|--------|------|---------|---------|
| 9 | `call` | `(args, context, canUseTool, parentMessage, onProgress?) => Promise<ToolResult<Output>>` | (required) | Main execution function |
| 10 | `description` | `(input, options) => Promise<string>` | (required) | Generates tool description, varying by input and permission context |

#### Permission & Security (4 members)

| # | Member | Type | Default | Purpose |
|---|--------|------|---------|---------|
| 11 | `checkPermissions` | `(input, context) => Promise<PermissionResult>` | `{ behavior: 'allow', updatedInput: input }` | Tool-specific permission logic |
| 12 | `toAutoClassifierInput` | `(input) => unknown` | `''` (empty string, skip) | Compact representation for auto-mode security classifier |
| 13 | `preparePermissionMatcher` | `(input) => Promise<(pattern) => boolean>` | `undefined` | Factory for hook `if`-condition matchers |
| 14 | `getPath` | `(input) => string` | `undefined` | Extracts file path for permission and tracking systems |

#### Behavioral Flags (8 members)

| # | Member | Type | Default | Purpose |
|---|--------|------|---------|---------|
| 15 | `isEnabled` | `() => boolean` | `() => true` | Whether the tool is currently available |
| 16 | `isConcurrencySafe` | `(input) => boolean` | `() => false` | Whether concurrent execution is safe (fail-closed) |
| 17 | `isReadOnly` | `(input) => boolean` | `() => false` | Whether tool only reads (fail-closed: assume writes) |
| 18 | `isDestructive` | `(input) => boolean` | `() => false` | Whether tool performs irreversible operations |
| 19 | `isOpenWorld` | `(input) => boolean` | `undefined` | Whether tool can access external resources |
| 20 | `requiresUserInteraction` | `() => boolean` | `undefined` | Whether tool requires interactive user input |
| 21 | `interruptBehavior` | `() => 'cancel' \| 'block'` | `undefined` (defaults to `'block'`) | Behavior when user submits new message while running |
| 22 | `isSearchOrReadCommand` | `(input) => { isSearch; isRead; isList? }` | `undefined` | Classifies operation type for UI collapse |

#### MCP & Protocol (5 members)

| # | Member | Type | Default | Purpose |
|---|--------|------|---------|---------|
| 23 | `isMcp` | `boolean` | `undefined` | Marks tool as originating from an MCP server |
| 24 | `isLsp` | `boolean` | `undefined` | Marks tool as originating from an LSP server |
| 25 | `shouldDefer` | `readonly boolean` | `undefined` | Tool is deferred and requires ToolSearch before use |
| 26 | `alwaysLoad` | `readonly boolean` | `undefined` | Tool is never deferred (full schema in initial prompt) |
| 27 | `mcpInfo` | `{ serverName; toolName }` | `undefined` | Original unnormalized MCP server and tool names |

#### Result Handling (3 members)

| # | Member | Type | Default | Purpose |
|---|--------|------|---------|---------|
| 28 | `maxResultSizeChars` | `number` | (required) | Max chars before result is persisted to disk; `Infinity` for Read |
| 29 | `strict` | `readonly boolean` | `undefined` | Strict mode for API adherence (feature-gated) |
| 30 | `mapToolResultToToolResultBlockParam` | `(content, toolUseID) => ToolResultBlockParam` | (required) | Converts typed output into Anthropic API format |

#### Prompt & Description (2 members)

| # | Member | Type | Default | Purpose |
|---|--------|------|---------|---------|
| 31 | `prompt` | `(options) => Promise<string>` | (required) | Generates tool's system prompt text |
| 32 | `backfillObservableInput` | `(input) => void` | `undefined` | Mutates copies of input before observers see it (idempotent) |

#### Rendering — Names & Labels (5 members)

| # | Member | Type | Default | Purpose |
|---|--------|------|---------|---------|
| 33 | `userFacingName` | `(input) => string` | `() => name` | Human-readable tool name shown in UI |
| 34 | `userFacingNameBackgroundColor` | `(input) => keyof Theme \| undefined` | `undefined` | Theme key for tool name badge background color |
| 35 | `isTransparentWrapper` | `() => boolean` | `undefined` | Tool delegates all rendering to its progress handler |
| 36 | `getToolUseSummary` | `(input) => string \| null` | `undefined` | Short string summary for compact views |
| 37 | `getActivityDescription` | `(input) => string \| null` | `undefined` | Present-tense activity for spinner (e.g., "Reading src/foo.ts") |

#### Rendering — Messages (8 members)

| # | Member | Type | Default | Purpose |
|---|--------|------|---------|---------|
| 38 | `renderToolUseMessage` | `(input, options) => React.ReactNode` | (required) | Renders "calling tool X with Y" UI |
| 39 | `renderToolResultMessage` | `(content, progressMessages, options) => React.ReactNode` | `undefined` | Renders tool result |
| 40 | `renderToolUseProgressMessage` | `(progressMessages, options) => React.ReactNode` | `undefined` | Progress UI while tool runs |
| 41 | `renderToolUseQueuedMessage` | `() => React.ReactNode` | `undefined` | Message when tool use is queued |
| 42 | `renderToolUseRejectedMessage` | `(input, options) => React.ReactNode` | `undefined` | Custom rejection UI |
| 43 | `renderToolUseErrorMessage` | `(result, options) => React.ReactNode` | `undefined` | Custom error UI |
| 44 | `renderToolUseTag` | `(input) => React.ReactNode` | `undefined` | Optional tag after tool use message |
| 45 | `renderGroupedToolUse` | `(toolUses, options) => React.ReactNode \| null` | `undefined` | Renders multiple parallel instances as group |

#### Search & Transcript (2 members)

| # | Member | Type | Default | Purpose |
|---|--------|------|---------|---------|
| 46 | `extractSearchText` | `(out) => string` | `undefined` | Flattened text for transcript search indexing |
| 47 | `isResultTruncated` | `(output) => boolean` | `undefined` | Gates click-to-expand affordance in fullscreen |

#### Required vs Optional Summary

| Category | Count | Required | Defaulted | Optional |
|----------|-------|----------|-----------|----------|
| Core Identity | 4 | 2 | 0 | 2 |
| Schema & Validation | 4 | 1 | 0 | 3 |
| Execution | 2 | 2 | 0 | 0 |
| Permission & Security | 4 | 0 | 2 | 2 |
| Behavioral Flags | 8 | 0 | 3 | 5 |
| MCP & Protocol | 5 | 0 | 0 | 5 |
| Result Handling | 3 | 2 | 0 | 1 |
| Prompt & Description | 2 | 1 | 0 | 1 |
| Rendering — Names | 5 | 0 | 1 | 4 |
| Rendering — Messages | 8 | 1 | 0 | 7 |
| Search & Transcript | 2 | 0 | 0 | 2 |
| **Total** | **47** | **9** | **7** | **31** |

#### `buildTool()` and Supporting Types

```typescript
// ToolDef — the "input" type; makes 7 defaultable methods optional
type ToolDef<Input, Output, P> =
  Omit<Tool<Input, Output, P>, DefaultableToolKeys> &
  Partial<Pick<Tool<Input, Output, P>, DefaultableToolKeys>>

// buildTool — single factory through which all 60+ tools pass
export function buildTool<D extends AnyToolDef>(def: D): BuiltTool<D> {
  return { ...TOOL_DEFAULTS, userFacingName: () => def.name, ...def } as BuiltTool<D>
}
```

**7 Defaultable Members** (`DefaultableToolKeys`):

| Member | Default Value | Rationale |
|--------|--------------|-----------|
| `isEnabled` | `() => true` | Tools enabled by default |
| `isConcurrencySafe` | `() => false` | Fail-closed: assume NOT safe |
| `isReadOnly` | `() => false` | Fail-closed: assume writes |
| `isDestructive` | `() => false` | Not destructive by default |
| `checkPermissions` | `(input) => { behavior: 'allow', updatedInput: input }` | Defer to general permissions |
| `toAutoClassifierInput` | `() => ''` | Skip classifier by default |
| `userFacingName` | `() => def.name` | Falls back to tool name |

**Supporting Result Types**:

```typescript
type ValidationResult =
  | { result: true }
  | { result: false; message: string; errorCode: number }

type ToolResult<T> = {
  data: T
  newMessages?: (UserMessage | AssistantMessage | AttachmentMessage | SystemMessage)[]
  contextModifier?: (context: ToolUseContext) => ToolUseContext
  mcpMeta?: { _meta?: Record<string, unknown>; structuredContent?: Record<string, unknown> }
}

type Tools = readonly Tool[]  // Read-only collection
```

---

## 3. Permission Types (`src/types/permissions.ts`)

### Mode Types with Feature Gating

```typescript
export const EXTERNAL_PERMISSION_MODES = ['acceptEdits','bypassPermissions','default','dontAsk','plan'] as const
export type ExternalPermissionMode = (typeof EXTERNAL_PERMISSION_MODES)[number]

export type InternalPermissionMode = ExternalPermissionMode | 'auto' | 'bubble'
export type PermissionMode = InternalPermissionMode

export const INTERNAL_PERMISSION_MODES = [
  ...EXTERNAL_PERMISSION_MODES,
  ...(feature('TRANSCRIPT_CLASSIFIER') ? (['auto'] as const) : ([] as const)),
] as const satisfies readonly PermissionMode[]
```

The `satisfies` operator ensures the array contents are valid `PermissionMode` values at compile time while preserving the narrow literal types.

### Permission Context with `DeepImmutable`

```typescript
export type ToolPermissionContext = DeepImmutable<{
  mode: PermissionMode
  additionalWorkingDirectories: Map<string, AdditionalWorkingDirectory>
  alwaysAllowRules: ToolPermissionRulesBySource
  alwaysDenyRules: ToolPermissionRulesBySource
  alwaysAskRules: ToolPermissionRulesBySource
  isBypassPermissionsModeAvailable: boolean
  isAutoModeAvailable?: boolean
  strippedDangerousRules?: ToolPermissionRulesBySource
  shouldAvoidPermissionPrompts?: boolean
  awaitAutomatedChecksBeforeDialog?: boolean
  prePlanMode?: PermissionMode
}>
```

`DeepImmutable` (from `src/types/utils.ts`) recursively makes all properties readonly, preventing accidental mutation.

### Rule Hierarchy

```typescript
export type PermissionBehavior = 'allow' | 'deny' | 'ask'

export type PermissionRuleSource =
  | 'userSettings' | 'projectSettings' | 'localSettings'
  | 'flagSettings' | 'policySettings' | 'cliArg' | 'command' | 'session'

export type PermissionRule = {
  source: PermissionRuleSource
  ruleBehavior: PermissionBehavior
  ruleValue: PermissionRuleValue
}
```

---

## 4. Input Types

### 4.1 BaseTextInputProps — Complete 31-Field Inventory (`src/types/textInputTypes.ts`)

Core prop contract for all text input components in the Ink-based TUI. Every keystroke, paste, cursor movement, and input lifecycle event flows through this interface.

| # | Field | Type | Req? | Description |
|---|-------|------|------|-------------|
| 1 | `value` | `string` | Yes | Current text input value |
| 2 | `onChange` | `(value: string) => void` | Yes | Callback when value updates |
| 3 | `columns` | `number` | Yes | Number of columns for text wrapping |
| 4 | `cursorOffset` | `number` | Yes | Offset of cursor within text |
| 5 | `onChangeCursorOffset` | `(offset: number) => void` | Yes | Callback to set cursor offset |
| 6 | `onSubmit` | `(value: string) => void` | No | Callback on Enter press |
| 7 | `onExit` | `() => void` | No | Callback on Ctrl+C to exit |
| 8 | `onExitMessage` | `(show: boolean, key?: string) => void` | No | Show exit message overlay |
| 9 | `onHistoryUp` | `() => void` | No | History navigation on up arrow |
| 10 | `onHistoryDown` | `() => void` | No | History navigation on down arrow |
| 11 | `onHistoryReset` | `() => void` | No | Reset history navigation position |
| 12 | `onClearInput` | `() => void` | No | Callback when input is cleared (double-escape) |
| 13 | `onImagePaste` | `(base64Image, mediaType?, filename?, dimensions?, sourcePath?) => void` | No | Callback when image is pasted |
| 14 | `onPaste` | `(text: string) => void` | No | Callback when large text (>800 chars) is pasted |
| 15 | `onIsPastingChange` | `(isPasting: boolean) => void` | No | Callback when pasting state changes |
| 16 | `onUndo` | `() => void` | No | Undo functionality callback |
| 17 | `placeholder` | `string` | No | Text to display when `value` is empty |
| 18 | `placeholderElement` | `React.ReactNode` | No | Custom React element as placeholder |
| 19 | `multiline` | `boolean` | No | Allow multi-line input (default: `true`) |
| 20 | `focus` | `boolean` | No | Route keyboard input to this component |
| 21 | `mask` | `string` | No | Replace all chars with mask character (passwords) |
| 22 | `showCursor` | `boolean` | No | Show cursor and allow arrow key navigation |
| 23 | `highlightPastedText` | `boolean` | No | Visually highlight pasted text |
| 24 | `dimColor` | `boolean` | No | Render text with dim color |
| 25 | `maxVisibleLines` | `number` | No | Maximum visible lines for viewport (enables windowing) |
| 26 | `disableCursorMovementForUpDownKeys` | `boolean` | No | Disable cursor movement for up/down keys |
| 27 | `disableEscapeDoublePress` | `boolean` | No | Skip text-level double-press escape handler |
| 28 | `argumentHint` | `string` | No | Hint text after command input |
| 29 | `highlights` | `TextHighlight[]` | No | Text highlights for search results |
| 30 | `inlineGhostText` | `InlineGhostText` | No | Inline ghost text for mid-input command autocomplete |
| 31 | `inputFilter` | `(input: string, key: Key) => string` | No | Filter applied to raw input before key routing |

**Supporting Types**:

```typescript
type InlineGhostText = {
  readonly text: string           // Ghost text to display (e.g., "mit" for /commit)
  readonly fullCommand: string    // Full command name (e.g., "commit")
  readonly insertPosition: number // Position where ghost text should appear
}
```

**Derived Types**:
- `VimTextInputProps` = `BaseTextInputProps & { initialMode?: VimMode; onModeChange?: (mode: VimMode) => void }`
- `BaseInputState` — Hook return type with `onInput`, `renderedValue`, `offset`, cursor/viewport data, and paste state

**Key Consumers**: `BaseTextInput`, `TextInput`, `PromptInput`

### 4.2 QueuedCommand — 13 Fields (`src/types/textInputTypes.ts`)

Core unit of work in the command queue system. Every user prompt, slash command, bridge message, and system-generated meta-prompt passes through this type before reaching the query engine.

| # | Field | Type | Req? | Description |
|---|-------|------|------|-------------|
| 1 | `value` | `string \| Array<ContentBlockParam>` | Yes | Command content — plain text or structured blocks |
| 2 | `mode` | `PromptInputMode` | Yes | `'bash' \| 'prompt' \| 'orphaned-permission' \| 'task-notification'` |
| 3 | `priority` | `QueuePriority` | No | `'now'` (interrupt), `'next'` (mid-turn), `'later'` (end-of-turn) |
| 4 | `uuid` | `UUID` | No | Unique identifier for the command |
| 5 | `orphanedPermission` | `OrphanedPermission` | No | Permission result for orphaned permission handling |
| 6 | `pastedContents` | `Record<number, PastedContent>` | No | Raw pasted contents including images |
| 7 | `preExpansionValue` | `string` | No | Input before placeholder expansion (for ultraplan detection) |
| 8 | `skipSlashCommands` | `boolean` | No | Treat as plain text even if starts with `/` |
| 9 | `bridgeOrigin` | `boolean` | No | Commands filtered through `isBridgeSafeCommand()` |
| 10 | `isMeta` | `boolean` | No | Hidden in transcript UI but visible to model |
| 11 | `origin` | `MessageOrigin` | No | Provenance stamp (undefined = human keyboard) |
| 12 | `workload` | `string` | No | Workload tag for billing-header attribution |
| 13 | `agentId` | `AgentId` | No | Target agent for notification (enables subagent queue isolation) |

**Queue Priority Semantics**:
- `'now'` — Interrupt immediately, abort in-flight tool call
- `'next'` — Mid-turn drain: let current tool finish, send between tool result and next API call
- `'later'` — End-of-turn drain: wait for turn to finish, process as new query

Both `'next'` and `'later'` wake an in-progress `SleepTool` call (proactive mode only).

**Key Consumers** (18 files): Queue management (`useCommandQueue`, `useQueueProcessor`), input processing (`handlePromptSubmit`, `processUserInput`), execution engine (`query.ts`, `REPL.tsx`), UI components (`PromptInput`, `PromptInputQueuedCommands`).

---

## 5. State Types

### Const Assertion Patterns

#### `as const` with `satisfies`

```typescript
export const OPERATORS = {
  d: 'delete', c: 'change', y: 'yank',
} as const satisfies Record<string, Operator>

export const TEXT_OBJ_SCOPES = {
  i: 'inner', a: 'around',
} as const satisfies Record<string, TextObjScope>
```

`as const` preserves literal types; `satisfies` validates structure without widening.

#### Rarity Weights (`buddy/types.ts`)

```typescript
export const RARITY_WEIGHTS = {
  common: 60, uncommon: 25, rare: 10, epic: 4, legendary: 1,
} as const satisfies Record<Rarity, number>

export const RARITY_STARS = {
  common: '★', uncommon: '★★', rare: '★★★', epic: '★★★★', legendary: '★★★★★',
} as const satisfies Record<Rarity, string>

export const RARITY_COLORS = {
  common: 'inactive', uncommon: 'success', rare: 'permission', epic: 'autoAccept', legendary: 'warning',
} as const satisfies Record<Rarity, keyof import('../utils/theme.js').Theme>
```

#### String-from-CharCode Encoding

```typescript
const c = String.fromCharCode
export const duck = c(0x64,0x75,0x63,0x6b) as 'duck'
export const goose = c(0x67,0x6f,0x6f,0x73,0x65) as 'goose'
```

Runtime construction preserves the literal type via `as` cast (erased pre-bundle).

### Readonly and Immutability Patterns

```typescript
export const RARITIES = ['common','uncommon','rare','epic','legendary'] as const
export type Rarity = (typeof RARITIES)[number]

const TERMINAL_BUNDLE_ID_FALLBACK: Readonly<Record<string, string>> = { ... }
```

---

## 6. Log Types — Entry Union (20 Variants, `src/types/logs.ts`)

Discriminated union representing every possible entry type written to a session transcript log file. The session transcript is an append-only log of `Entry` values that captures the full session state for resume, analytics, and recovery.

### Discriminant

The `type` field is present on all variants except `TranscriptMessage` (which uses the `Message` union's own `role` discriminant).

### Complete Variant List

| # | Variant | Discriminant (`type`) | Key Fields | Purpose |
|---|---------|----------------------|------------|---------|
| 1 | `TranscriptMessage` | (inherits `Message.role`) | `parentUuid`, `isSidechain`, `agentId`, `promptId` | Core conversation messages with sidechain + agent metadata |
| 2 | `SummaryMessage` | `'summary'` | `leafUuid`, `summary` | Conversation summary for session resume |
| 3 | `CustomTitleMessage` | `'custom-title'` | `sessionId`, `customTitle` | User-set custom title (always wins over AI title) |
| 4 | `AiTitleMessage` | `'ai-title'` | `sessionId`, `aiTitle` | AI-generated session title (ephemeral) |
| 5 | `LastPromptMessage` | `'last-prompt'` | `sessionId`, `lastPrompt` | Records last user prompt |
| 6 | `TaskSummaryMessage` | `'task-summary'` | `sessionId`, `summary`, `timestamp` | Fork-generated summary of current agent activity |
| 7 | `TagMessage` | `'tag'` | `sessionId`, `tag` | Searchable tag for session (used in `/resume`) |
| 8 | `AgentNameMessage` | `'agent-name'` | `sessionId`, `agentName` | Agent's custom name |
| 9 | `AgentColorMessage` | `'agent-color'` | `sessionId`, `agentColor` | Agent's display color |
| 10 | `AgentSettingMessage` | `'agent-setting'` | `sessionId`, `agentSetting` | Agent definition used |
| 11 | `PRLinkMessage` | `'pr-link'` | `prNumber`, `prUrl`, `prRepository`, `timestamp` | Links session to a GitHub pull request |
| 12 | `FileHistorySnapshotMessage` | `'file-history-snapshot'` | `messageId`, `snapshot`, `isSnapshotUpdate` | File history snapshot for undo/tracking |
| 13 | `AttributionSnapshotMessage` | `'attribution-snapshot'` | `messageId`, `surface`, `fileStates` | Character-level contribution tracking |
| 14 | `QueueOperationMessage` | (from `messageQueueTypes.ts`) | -- | Queue operation records |
| 15 | `SpeculationAcceptMessage` | `'speculation-accept'` | `timestamp`, `timeSavedMs` | Accepted speculative execution and time saved |
| 16 | `ModeEntry` | `'mode'` | `sessionId`, `mode` | Session mode: `'coordinator' \| 'normal'` |
| 17 | `WorktreeStateEntry` | `'worktree-state'` | `sessionId`, `worktreeSession` | Worktree enter/exit state |
| 18 | `ContentReplacementEntry` | `'content-replacement'` | `sessionId`, `agentId?`, `replacements` | Content blocks replaced with smaller stubs |
| 19 | `ContextCollapseCommitEntry` | `'marble-origami-commit'` | `collapseId`, `summaryUuid`, `summaryContent`, boundary UUIDs | Persisted context-collapse commit (obfuscated discriminant) |
| 20 | `ContextCollapseSnapshotEntry` | `'marble-origami-snapshot'` | `staged[]`, `armed`, `lastSpawnTokens` | Last-wins snapshot of staged collapse queue |

### Design Patterns

1. **Obfuscated Discriminants**: `'marble-origami-commit'` and `'marble-origami-snapshot'` deliberately obfuscate the context-collapse feature name to prevent leaking through transcript plumbing.
2. **Last-Wins vs Append-Only**: Most entries are append-only (replay all). `ContextCollapseSnapshotEntry` and `WorktreeStateEntry` are **last-wins** (only the most recent applies on restore).
3. **Title Precedence**: `CustomTitleMessage` always wins over `AiTitleMessage`. AI titles are ephemeral and not re-appended on resume.
4. **Agent Isolation**: `ContentReplacementEntry.agentId` and `TranscriptMessage.agentId` partition the transcript by agent, enabling subagent sidechain resume.

### Supporting Types

```typescript
type SerializedMessage = Message & {
  cwd: string; userType: string; entrypoint?: string;
  sessionId: string; timestamp: string; version: string;
  gitBranch?: string; slug?: string;
}

type LogOption = {  // 33 fields — fully-hydrated session metadata for /resume and LogSelector
  date: string; messages: SerializedMessage[];
  fullPath?: string; value: number;
  created: Date; modified: Date;
  firstPrompt: string; messageCount: number;
  fileSize?: number; isSidechain: boolean;
  isLite?: boolean; sessionId?: string;
  teamName?: string; agentName?: string; agentColor?: string;
  agentSetting?: string; isTeammate?: boolean;
  leafUuid?: UUID; summary?: string; customTitle?: string;
  tag?: string; fileHistorySnapshots?: FileHistorySnapshot[];
  attributionSnapshots?: AttributionSnapshotMessage[];
  contextCollapseCommits?: ContextCollapseCommitEntry[];
  contextCollapseSnapshot?: ContextCollapseSnapshotEntry;
  gitBranch?: string; projectPath?: string;
  prNumber?: number; prUrl?: string; prRepository?: string;
  mode?: 'coordinator' | 'normal';
  worktreeSession?: PersistedWorktreeSession | null;
  contentReplacements?: ContentReplacementRecord[];
}
```

### Input-to-Persistence Pipeline

```
User keystroke
    |
BaseTextInputProps.onChange()          -- Input System
    |
handlePromptSubmit() -> QueuedCommand -- Command Queue
    |
useQueueProcessor -> query.ts         -- Dequeue + execute
    |
query result -> TranscriptMessage     -- Session Persistence
    |
sessionStorage.appendEntry(Entry)     -- Append to log file
    |
/resume -> loadTranscriptFile()       -- Replay Entry stream
```

### Key Consumers (25+ files)

| Category | Files | Usage |
|----------|-------|-------|
| Session Storage | `utils/sessionStorage.ts` | Primary read/write of Entry |
| Session Resume | `commands/resume/resume.tsx`, `screens/ResumeConversation.tsx` | Replay Entry stream |
| Session Recovery | `utils/conversationRecovery.ts` | Recover from corrupted transcripts |
| Analytics | `services/analytics/firstPartyEventLogger.ts` | Extract metrics from Entry stream |
| Attribution | `utils/attribution.ts`, `utils/commitAttribution.ts` | Track contributions |
| UI | `components/LogSelector.tsx`, `components/SessionPreview.tsx` | Display session list |

---

## 7. Zod Schema Validation (`src/types/hooks.ts`)

### Runtime Validation with Type Inference

Hook responses are validated at runtime using Zod schemas:

```typescript
export const syncHookResponseSchema = lazySchema(() =>
  z.object({
    continue: z.boolean().optional(),
    suppressOutput: z.boolean().optional(),
    stopReason: z.string().optional(),
    decision: z.enum(['approve', 'block']).optional(),
    reason: z.string().optional(),
    hookSpecificOutput: z.union([
      z.object({ hookEventName: z.literal('PreToolUse'), permissionDecision: permissionBehaviorSchema().optional(), ... }),
      z.object({ hookEventName: z.literal('UserPromptSubmit'), ... }),
      z.object({ hookEventName: z.literal('SessionStart'), watchPaths: z.array(z.string()).optional(), ... }),
      // ... 13 hook event types
    ]).optional(),
  })
)
```

### Lazy Schema Pattern

Schemas are wrapped in `lazySchema()` to defer construction and avoid import-time cycles:

```typescript
import { lazySchema } from '../utils/lazySchema.js'

export const promptRequestSchema = lazySchema(() =>
  z.object({
    prompt: z.string(),
    message: z.string(),
    options: z.array(z.object({ key: z.string(), label: z.string(), description: z.string().optional() })),
  })
)
```

### Compile-Time Type Assertion

The codebase verifies that Zod-inferred types match hand-written SDK types at compile time:

```typescript
import type { IsEqual } from 'type-fest'
type Assert<T extends true> = T

// If SchemaHookJSONOutput !== HookJSONOutput, this is a compile error
type _assertSDKTypesMatch = Assert<IsEqual<SchemaHookJSONOutput, HookJSONOutput>>
```

---

## 8. Generated Types (Protobuf)

### Analytics Events (`src/types/generated/events_mono/`)

Generated by `protoc-gen-ts_proto` from protobuf definitions:

```typescript
// claude_code_internal_event.ts — generated, DO NOT EDIT
export interface EnvironmentMetadata {
  platform?: string | undefined
  node_version?: string | undefined
  terminal?: string | undefined
  is_ci?: boolean | undefined
  is_github_action?: boolean | undefined
  arch?: string | undefined
  // ... 25+ optional fields
}
```

**Generated type characteristics:**
- All fields are optional with `| undefined` (protobuf optional semantics)
- No runtime code — pure type definitions
- Separate files per proto package: `common/v1/auth.ts`, `google/protobuf/timestamp.ts`

### Timestamp Types

```typescript
// google/protobuf/timestamp.ts — generated
export interface Timestamp {
  seconds?: number | undefined
  nanos?: number | undefined
}
```

---

## 9. Type Guards

### Feature-Gated Type Guards

```typescript
export function isOperatorKey(key: string): key is keyof typeof OPERATORS {
  return key in OPERATORS
}

export function isTextObjScopeKey(key: string): key is keyof typeof TEXT_OBJ_SCOPES {
  return key in TEXT_OBJ_SCOPES
}
```

### Hook Type Guards

```typescript
export function isSyncHookJSONOutput(json: HookJSONOutput): json is SyncHookJSONOutput {
  return !('async' in json && json.async === true)
}

export function isAsyncHookJSONOutput(json: HookJSONOutput): json is AsyncHookJSONOutput {
  return 'async' in json && json.async === true
}

export function isHookEvent(value: string): value is HookEvent {
  return HOOK_EVENTS.includes(value as HookEvent)
}
```

### Computer Use Lock Type Guard

```typescript
function isComputerUseLock(value: unknown): value is ComputerUseLock {
  if (typeof value !== 'object' || value === null) return false
  return 'sessionId' in value && typeof value.sessionId === 'string' &&
         'pid' in value && typeof value.pid === 'number'
}
```

---

## 10. Import Cycle Prevention

The `src/types/permissions.ts` file header explains the pattern:

```typescript
/**
 * Pure permission type definitions extracted to break import cycles.
 * This file contains only type definitions and constants with no runtime dependencies.
 * Implementation files remain in src/utils/permissions/ but can now import from here.
 */
```

Similarly, `Tool.ts` re-exports types from centralized locations:

```typescript
import type { PermissionMode, PermissionResult } from './types/permissions.js'
import type { ToolProgressData, BashProgress, MCPProgress } from './types/tools.js'
export type { ToolPermissionRulesBySource }
```

---

## Pattern Summary

| Pattern | Examples | Purpose |
|---------|----------|---------|
| Discriminated Unions | VimState, CommandState, AcquireResult, Entry (20 variants) | Exhaustive type-safe branching |
| `as const satisfies` | OPERATORS, RARITY_WEIGHTS | Narrow literals + structural validation |
| Zod + Type Assertion | hookJSONOutputSchema, `_assertSDKTypesMatch` | Runtime validation + compile-time drift detection |
| DeepImmutable | ToolPermissionContext | Prevent accidental mutation |
| Generated Types | Protobuf events, Timestamp | Cross-language type safety |
| Type Guards | isOperatorKey, isComputerUseLock | Safe runtime narrowing |
| Branded IDs | SessionId, AgentId (`__brand`), `toAgentId()` | Prevent ID type confusion at compile time |
| Lazy Schema | lazySchema(() => z.object(...)) | Deferred construction for import cycles |
| Feature-Gated Types | INTERNAL_PERMISSION_MODES | Compile-time feature flag support |
| buildTool Factory | 7 defaults, 60+ tools, fail-closed security | Single source of truth for tool construction |
| Input Pipeline | BaseTextInputProps -> QueuedCommand -> Entry | Keystroke-to-persistence type chain |

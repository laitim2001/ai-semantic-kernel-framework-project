# Wave 31 — ToolUseContext Complete Field Inventory

> Definitive reference for `ToolUseContext` (Tool.ts lines 158-300).
> Source: `CC-Source/src/Tool.ts` | Verified: 2026-04-01
> Resolves M-17 gap: 18/55 fields documented -> 55/55 fields documented.

---

## Field Count Summary

| Group | Required | Optional | Total |
|-------|----------|----------|-------|
| Options (nested object) | 10 | 4 | 14 |
| Core Runtime | 4 | 0 | 4 |
| App State Management | 2 | 1 | 3 |
| UI / Interactive | 0 | 8 | 8 |
| Memory / Skills | 0 | 4 | 4 |
| Agent Identity | 1 | 3 | 4 |
| State Setters | 2 | 6 | 8 |
| Limits / Decisions | 0 | 4 | 4 |
| Query / Prompt | 0 | 3 | 3 |
| Subagent / Advanced | 0 | 3 | 3 |
| **Total** | **19** | **36** | **55** |

---

## Group 1: Options (nested `options` object)

| # | Field | Type | Opt? | Purpose |
|---|-------|------|------|---------|
| 1 | `options.commands` | `Command[]` | No | Available slash commands registered in the session |
| 2 | `options.debug` | `boolean` | No | Enables debug-level logging and diagnostics |
| 3 | `options.mainLoopModel` | `string` | No | Model identifier used for the main conversation loop |
| 4 | `options.tools` | `Tools` | No | Complete set of tools available to the agent |
| 5 | `options.verbose` | `boolean` | No | Controls verbose output rendering in UI |
| 6 | `options.thinkingConfig` | `ThinkingConfig` | No | Extended thinking budget and token configuration |
| 7 | `options.mcpClients` | `MCPServerConnection[]` | No | Active MCP server connections for tool dispatch |
| 8 | `options.mcpResources` | `Record<string, ServerResource[]>` | No | MCP server resources indexed by server name |
| 9 | `options.isNonInteractiveSession` | `boolean` | No | True for SDK/print mode (no REPL); gates interactive features |
| 10 | `options.agentDefinitions` | `AgentDefinitionsResult` | No | Loaded agent definitions from the agents directory |
| 11 | `options.maxBudgetUsd` | `number` | Yes | Maximum API spend cap in USD for the session |
| 12 | `options.customSystemPrompt` | `string` | Yes | Custom system prompt that replaces the default system prompt |
| 13 | `options.appendSystemPrompt` | `string` | Yes | Additional system prompt appended after the main system prompt |
| 14 | `options.querySource` | `QuerySource` | Yes | Override querySource for analytics tracking |
| 15 | `options.refreshTools` | `() => Tools` | Yes | Callback to get latest tools after MCP servers connect mid-query |

---

## Group 2: Core Runtime

| # | Field | Type | Opt? | Purpose |
|---|-------|------|------|---------|
| 16 | `abortController` | `AbortController` | No | Cancellation signal for the current query/turn |
| 17 | `readFileState` | `FileStateCache` | No | LRU cache of file contents to avoid redundant disk reads |
| 18 | `messages` | `Message[]` | No | Full conversation message history for the current thread |
| 19 | `toolUseId` | `string` | Yes | ID of the current tool_use block being executed |

---

## Group 3: App State Management

| # | Field | Type | Opt? | Purpose |
|---|-------|------|------|---------|
| 20 | `getAppState()` | `() => AppState` | No | Returns the current immutable application state snapshot |
| 21 | `setAppState` | `(f: (prev: AppState) => AppState) => void` | No | Updates application state via a reducer function |
| 22 | `setAppStateForTasks` | `(f: (prev: AppState) => AppState) => void` | Yes | Always-shared setAppState for session-scoped infrastructure (background tasks, session hooks); unlike setAppState, always reaches the root store even for async subagents |

---

## Group 4: UI / Interactive Features

| # | Field | Type | Opt? | Purpose |
|---|-------|------|------|---------|
| 23 | `setToolJSX` | `SetToolJSXFn` | Yes | Sets custom JSX to render in the tool output area (REPL only) |
| 24 | `addNotification` | `(notif: Notification) => void` | Yes | Pushes a notification to the REPL notification queue |
| 25 | `appendSystemMessage` | `(msg: Exclude<SystemMessage, SystemLocalCommandMessage>) => void` | Yes | Appends a UI-only system message to the REPL message list (stripped at API boundary) |
| 26 | `sendOSNotification` | `(opts: { message: string; notificationType: string }) => void` | Yes | Sends an OS-level notification (iTerm2, Kitty, Ghostty, bell, etc.) |
| 27 | `handleElicitation` | `(serverName: string, params: ElicitRequestURLParams, signal: AbortSignal) => Promise<ElicitResult>` | Yes | Handler for URL elicitations triggered by MCP tool call errors (-32042); used in print/SDK mode |
| 28 | `openMessageSelector` | `() => void` | Yes | Opens the interactive message selector UI in REPL mode |
| 29 | `requestPrompt` | `(sourceName: string, toolInputSummary?: string \| null) => (request: PromptRequest) => Promise<PromptResponse>` | Yes | Callback factory for requesting interactive prompts from the user; returns a bound prompt callback (REPL only) |
| 30 | `setStreamMode` | `(mode: SpinnerMode) => void` | Yes | Controls the spinner/stream mode displayed during tool execution |

---

## Group 5: Memory / Skills

| # | Field | Type | Opt? | Purpose |
|---|-------|------|------|---------|
| 31 | `nestedMemoryAttachmentTriggers` | `Set<string>` | Yes | Trigger patterns that cause CLAUDE.md files to be injected as nested memory attachments |
| 32 | `loadedNestedMemoryPaths` | `Set<string>` | Yes | CLAUDE.md paths already injected this session; dedup guard since readFileState LRU can evict entries |
| 33 | `dynamicSkillDirTriggers` | `Set<string>` | Yes | Trigger patterns for dynamically loading skill directories |
| 34 | `discoveredSkillNames` | `Set<string>` | Yes | Skill names surfaced via skill_discovery this session; telemetry only (feeds `was_discovered`) |

---

## Group 6: Agent Identity

| # | Field | Type | Opt? | Purpose |
|---|-------|------|------|---------|
| 35 | `agentId` | `AgentId` | Yes | Unique ID for subagents; hooks use this to distinguish subagent calls from main thread |
| 36 | `agentType` | `string` | Yes | Subagent type name; for main thread's --agent type, hooks fall back to `getMainThreadAgentType()` |
| 37 | `userModified` | `boolean` | Yes | Indicates whether the user has modified input/context since last turn |
| 38 | `requireCanUseTool` | `boolean` | Yes | When true, `canUseTool` must always be called even when hooks auto-approve; used by speculation for overlay file path rewriting |

---

## Group 7: State Setters (Callbacks)

| # | Field | Type | Opt? | Purpose |
|---|-------|------|------|---------|
| 39 | `setInProgressToolUseIDs` | `(f: (prev: Set<string>) => Set<string>) => void` | No | Tracks which tool_use IDs are currently executing |
| 40 | `setResponseLength` | `(f: (prev: number) => number) => void` | No | Updates the running count of response tokens for budget tracking |
| 41 | `setHasInterruptibleToolInProgress` | `(v: boolean) => void` | Yes | Signals whether a cancellable tool is running; only wired in REPL contexts |
| 42 | `pushApiMetricsEntry` | `(ttftMs: number) => void` | Yes | Ant-only: pushes a new API metrics entry for OTPS (output tokens per second) tracking |
| 43 | `setSDKStatus` | `(status: SDKStatus) => void` | Yes | Updates SDK lifecycle status for the Agent SDK entrypoint |
| 44 | `setConversationId` | `(id: UUID) => void` | Yes | Sets the conversation ID (UUID) for session tracking |
| 45 | `updateFileHistoryState` | `(updater: (prev: FileHistoryState) => FileHistoryState) => void` | No | Updates the file edit history state for undo/attribution tracking |
| 46 | `updateAttributionState` | `(updater: (prev: AttributionState) => AttributionState) => void` | No | Updates commit attribution state for Co-Authored-By tracking |

> Note: `setInProgressToolUseIDs`, `setResponseLength`, `updateFileHistoryState`, and `updateAttributionState` are required (no `?`). The other four setters are optional (REPL/SDK-specific).

---

## Group 8: Limits / Decisions

| # | Field | Type | Opt? | Purpose |
|---|-------|------|------|---------|
| 47 | `fileReadingLimits` | `{ maxTokens?: number; maxSizeBytes?: number }` | Yes | Configurable caps on file reading (token count and byte size) |
| 48 | `globLimits` | `{ maxResults?: number }` | Yes | Configurable cap on glob search result count |
| 49 | `toolDecisions` | `Map<string, { source: string; decision: 'accept' \| 'reject'; timestamp: number }>` | Yes | Cached permission decisions for tool uses, keyed by tool_use ID |
| 50 | `onCompactProgress` | `(event: CompactProgressEvent) => void` | Yes | Callback for context compaction lifecycle events (hooks_start, compact_start, compact_end) |

---

## Group 9: Query / Prompt

| # | Field | Type | Opt? | Purpose |
|---|-------|------|------|---------|
| 51 | `queryTracking` | `QueryChainTracking` (`{ chainId: string; depth: number }`) | Yes | Tracks query chain depth for nested/recursive tool invocations |
| 52 | `criticalSystemReminder_EXPERIMENTAL` | `string` | Yes | Experimental field for injecting critical system reminders into the context |
| 53 | `preserveToolUseResults` | `boolean` | Yes | When true, preserve `toolUseResult` on messages even for subagents; used by in-process teammates whose transcripts are viewable by the user |

---

## Group 10: Subagent / Advanced

| # | Field | Type | Opt? | Purpose |
|---|-------|------|------|---------|
| 54 | `localDenialTracking` | `DenialTrackingState` | Yes | Local denial tracking for async subagents whose `setAppState` is a no-op; mutable, updated in-place by permissions code to accumulate denial counts |
| 55 | `contentReplacementState` | `ContentReplacementState` | Yes | Per-conversation-thread content replacement state for the tool result budget; main thread provisions once, subagents clone from parent |
| 56 | `renderedSystemPrompt` | `SystemPrompt` | Yes | Parent's rendered system prompt bytes frozen at turn start; used by fork subagents to share the parent's prompt cache and avoid GrowthBook divergence |

---

## Cross-Reference: Required vs Optional

### 19 Required Fields (no `?`)
`options` (entire object), `abortController`, `readFileState`, `messages`, `getAppState`, `setAppState`, `setInProgressToolUseIDs`, `setResponseLength`, `updateFileHistoryState`, `updateAttributionState`

Within `options`: `commands`, `debug`, `mainLoopModel`, `tools`, `verbose`, `thinkingConfig`, `mcpClients`, `mcpResources`, `isNonInteractiveSession`, `agentDefinitions`

### 36 Optional Fields (marked with `?`)
All others. Optional fields fall into two categories:
- **REPL-only** (not wired in SDK/print mode): `setToolJSX`, `addNotification`, `appendSystemMessage`, `sendOSNotification`, `openMessageSelector`, `requestPrompt`, `setHasInterruptibleToolInProgress`, `setStreamMode`
- **Context-dependent** (set only when relevant): `agentId`, `agentType`, `localDenialTracking`, `contentReplacementState`, `renderedSystemPrompt`, `setAppStateForTasks`, etc.

---

## Key Imported Types

| Type | Source Module | Used In |
|------|--------------|---------|
| `FileStateCache` | `utils/fileStateCache.js` | `readFileState` |
| `AppState` | `state/AppState.js` | `getAppState`, `setAppState` |
| `SetToolJSXFn` | Tool.ts (line 103) | `setToolJSX` |
| `Notification` | `context/notifications.js` | `addNotification` |
| `SpinnerMode` | `components/Spinner.js` | `setStreamMode` |
| `SDKStatus` | `entrypoints/agentSdkTypes.js` | `setSDKStatus` |
| `QuerySource` | `constants/querySource.js` | `options.querySource` |
| `AgentId` | `types/ids.js` | `agentId` |
| `ThinkingConfig` | `utils/thinking.js` | `options.thinkingConfig` |
| `MCPServerConnection` | `services/mcp/types.js` | `options.mcpClients` |
| `ServerResource` | `services/mcp/types.js` | `options.mcpResources` |
| `AgentDefinitionsResult` | `tools/AgentTool/loadAgentsDir.js` | `options.agentDefinitions` |
| `Command` | `commands.js` | `options.commands` |
| `Message` | `types/message.js` | `messages` |
| `DenialTrackingState` | `utils/permissions/denialTracking.js` | `localDenialTracking` |
| `ContentReplacementState` | `utils/toolResultStorage.js` | `contentReplacementState` |
| `SystemPrompt` | `utils/systemPromptType.js` | `renderedSystemPrompt` |
| `FileHistoryState` | `utils/fileHistory.js` | `updateFileHistoryState` |
| `AttributionState` | `utils/commitAttribution.js` | `updateAttributionState` |
| `QueryChainTracking` | Tool.ts (line 90) | `queryTracking` |
| `CompactProgressEvent` | Tool.ts (line 150) | `onCompactProgress` |
| `PromptRequest` / `PromptResponse` | `types/hooks.js` | `requestPrompt` |
| `ElicitRequestURLParams` / `ElicitResult` | `@modelcontextprotocol/sdk/types.js` | `handleElicitation` |

---

## Architecture Notes

1. **REPL vs SDK split**: 8 fields are REPL-only (`setToolJSX`, `addNotification`, `appendSystemMessage`, `sendOSNotification`, `openMessageSelector`, `requestPrompt`, `setHasInterruptibleToolInProgress`, `setStreamMode`). SDK/print mode leaves these undefined.

2. **Subagent context**: `createSubagentContext` in `forkSubagent.ts` creates a derived ToolUseContext where `setAppState` becomes a no-op for async agents, `setAppStateForTasks` always reaches the root store, and `contentReplacementState` is cloned from parent.

3. **Memory dedup**: `loadedNestedMemoryPaths` exists because `readFileState` is an LRU that evicts entries in busy sessions. Without this dedicated Set, the same CLAUDE.md could be injected dozens of times.

4. **Prompt cache preservation**: `renderedSystemPrompt` is frozen at turn start so fork subagents share the parent's prompt cache. Re-calling `getSystemPrompt()` at fork-spawn time can diverge due to GrowthBook warm/cold state differences.

5. **Denial accumulation**: `localDenialTracking` is mutable (updated in-place) because async subagents' `setAppState` is a no-op, so the normal AppState-based denial counter never accumulates.

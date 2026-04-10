# Claude Code CLI — Data Flow Analysis (Wave 16 Corrected)

> **Wave 16 Corrected** — Rewritten using Wave 4 source-verified ground truth (Paths 1-5).
> Original analysis contained 12+ factual errors. All sections below are verified against CC source code.
> Correction Date: 2026-04-01 | Verifier: Claude Opus 4.6 (1M context)

---

## 1. Primary Data Flow: User Input -> Response

Two distinct paths exist: the **interactive REPL** path and the **SDK/headless** path. The original analysis conflated them via the non-existent "QueryEngine in REPL" claim.

### 1.1 Interactive REPL Path (Primary)

```
REPL.tsx onSubmit(input, helpers, speculationAccept?, options?)
  │  setUserInputOnProcessing(input)     ← show placeholder immediately
  │  awaitPendingHooks()                 ← ensure SessionStart hook context ready
  │
  ▼
handlePromptSubmit.ts (orchestration layer)
  │  Handle exit commands (exit/quit/:q/:wq) -> redirect to /exit
  │  Expand [Pasted text #N] references via expandPastedTextRefs()
  │  Handle immediate local-jsx commands while loading
  │  If already loading -> enqueue via enqueue({value, mode, ...})
  │  If idle -> construct QueuedCommand -> executeUserInput()
  │
  ▼
executeUserInput(params)
  │  Create fresh AbortController
  │  Reserve queryGuard (prevents concurrent execution)
  │  Wrap in runWithWorkload() AsyncLocalStorage context
  │  Iterate queuedCommands -> processUserInput() for each
  │
  ▼
processUserInput({input, mode, ...})
  │  Route by mode + input prefix:
  │    mode === 'bash'              -> processBashCommand()
  │    inputString.startsWith('/')  -> processSlashCommand()
  │    Ultraplan keyword detected   -> rewritten to /ultraplan
  │    Otherwise                    -> processTextPrompt()
  │  After routing: executeUserPromptSubmitHooks() for hook blocking/context
  │
  ▼
onQuery callback (defined in REPL.tsx)
  │  Acquire queryGuard.tryStart() -> returns generation number or null
  │  Append newMessages to messages via setMessages()
  │  Reset streaming state (responseLengthRef, apiMetricsRef, streamingToolUses)
  │  Call onQueryImpl()
  │
  ▼
onQueryImpl (REPL.tsx)
  │  Build system prompt via buildEffectiveSystemPrompt()
  │  Load context (CLAUDE.md, user context, system context)
  │  Generate session title from first user message
  │
  ▼
query() loop (query.ts) — the agentic while(true) loop
  │  Destructure mutable state each iteration
  │  Yield { type: 'stream_request_start' }
  │  Prepare messagesForQuery from post-compact-boundary messages
  │  Run microcompact + autocompact if needed (see Section 5)
  │
  ▼
deps.callModel({messages, systemPrompt, ...})
  │  deps.callModel = queryModelWithStreaming (from query/deps.ts)
  │  Dependency injection pattern enables testing
  │
  ▼
queryModelWithStreaming (claude.ts)
  │  Wraps queryModel() with VCR recording via withStreamingVCR()
  │
  ▼
queryModel (claude.ts)
  │  Off-switch check
  │  Resolve model, build beta headers, tool schemas
  │  Build params (system prompt blocks, message params, tools, thinking config)
  │  Message normalization: buildMessagesForAPI / userMessageToMessageParam /
  │    assistantMessageToMessageParam (NOT in query.ts)
  │
  ▼
anthropic.beta.messages.create({...params, stream: true}).withResponse()
  │  Uses @anthropic-ai/sdk with raw streaming
  │  Returns Stream<BetaRawMessageStreamEvent> (NOT BetaMessageStream)
  │  Raw streaming avoids O(n^2) partial JSON parsing
```

### 1.2 SDK/Headless Path (Alternative)

```
QueryEngine.submitMessage()
  -> processUserInput()
  -> fetchSystemPromptParts() (called inside QueryEngine, NOT query.ts)
  -> query()
  -> same API call chain as above
```

`QueryEngine.ts` is NOT used in the interactive REPL path. It exists for the programmatic SDK API.

### 1.3 Stream-to-Render Pipeline

```
query() yields StreamEvent/Message
  │
  ▼
onQueryEvent (REPL.tsx callback)
  │
  ▼
handleMessageFromStream (messages.ts) — Stream event router
  │
  ├─ Non-stream events (assistant/user/system messages):
  │    onMessage(message) -> setMessages() -> React re-render
  │
  ├─ stream_request_start:
  │    Set spinner to 'requesting'
  │
  ├─ message_start:
  │    Record TTFT metrics
  │
  ├─ content_block_start:
  │    thinking  -> onSetStreamMode('thinking')
  │    text      -> onSetStreamMode('responding')
  │    tool_use  -> onSetStreamMode('tool-input') + add to streamingToolUses
  │
  ├─ content_block_delta:
  │    Update streaming text via onStreamingText and onUpdateLength
  │
  └─ message_stop:
       Set mode to 'tool-use', clear streaming tool uses
```

SpinnerMode state machine: `requesting -> thinking -> responding -> tool-input -> tool-use`

### 1.4 Data Transformations

| Stage | Input | Output |
|-------|-------|--------|
| User input | Raw string + optional image/file attachments | `UserMessage` object |
| Orchestration | UserMessage + mode + pasted refs | QueuedCommand (exit/enqueue/execute routing) |
| Context assembly | Messages + CLAUDE.md + git/files context | Built system prompt (in onQueryImpl, NOT query.ts) |
| API normalization | Internal `Message[]` | `@anthropic-ai/sdk` `MessageParam[]` (in claude.ts) |
| Stream processing | SSE chunks (BetaRawMessageStreamEvent) | `AssistantMessage` with text + `ToolUseBlock[]` |
| Tool execution | `ToolUseBlock.input` (JSON) | `ToolResultBlockParam` (text/image/error) |
| Stream routing | StreamEvent | SpinnerMode transitions + React state updates |

---

## 2. Tool Invocation Flow

### 2.1 Detection and Routing

```
API SSE stream (tool_use block)
  │
  ├─ Streaming mode: StreamingToolExecutor.addTool()
  │     └─ findToolByName() + queue
  │     └─ executeTool() via processQueue()
  │           └─ calls runToolUse() from toolExecution.ts
  │
  └─ Legacy mode: batched after stream ends
        └─ also calls runToolUse()
```

### 2.2 Three-Stage Validation Pipeline

Before any permission check or execution, every tool call passes through:

```
Stage 1: Zod schema validation
  inputSchema.safeParse(input) -> typed ParsedInput
  (toolExecution.ts L615-680)

Stage 2: Tool-specific validateInput()
  tool.validateInput(parsedInput, context) -> ValidationResult
  (toolExecution.ts L683-733)

Stage 3: PreToolUse hooks
  runPreToolUseHooks() -> possible input modification, stop execution, or permission decision
  (toolExecution.ts L800-862)
```

### 2.3 Permission Resolution

After validation, permission is resolved via `resolveHookPermissionDecision()`:

```
resolveHookPermissionDecision() -> canUseTool
  │
  ├─ ALLOW -> tool.call(callInput, context, canUseTool, assistantMessage, onProgress)
  │           -> tool.mapToolResultToToolResultBlockParam(data, toolUseID)
  │           -> processToolResultBlock() (size-limited, possibly persisted to disk)
  │           -> createUserMessage({content: [toolResultBlock]})
  │           -> runPostToolUseHooks() (can modify MCP tool output)
  │
  ├─ DENY  -> synthetic tool_result with denial message + runPostToolUseHooks()
  │
  └─ ASK   -> render interactive prompt -> await user (see Section 3)
```

### 2.4 StreamingToolExecutor — Parallel Execution

`StreamingToolExecutor` (StreamingToolExecutor.ts) enables concurrent tool execution:

```typescript
// Concurrency rules:
canExecuteTool(isConcurrencySafe: boolean): boolean {
  const executingTools = this.tools.filter(t => t.status === 'executing')
  return (
    executingTools.length === 0 ||
    (isConcurrencySafe && executingTools.every(t => t.isConcurrencySafe))
  )
}
```

- Concurrent-safe tools (e.g., Read, Grep, Glob) run in parallel with each other
- Non-concurrent tools get exclusive access (no other tools running)
- Results are yielded in arrival order
- On sibling error or streaming fallback: synthetic error `tool_result` messages created

### 2.5 Tool Interface

| Method | Purpose |
|--------|---------|
| `call(args, context, canUseTool, parentMessage, onProgress?)` | Execute the tool |
| `validateInput(input, context)` | Tool-specific input validation |
| `checkPermissions(input, context)` | Tool-specific permission logic |
| `mapToolResultToToolResultBlockParam(content, toolUseID)` | Convert output to API format |
| `inputSchema` (Zod) | Schema for input validation |
| `isConcurrencySafe(input)` | Whether tool can run in parallel |
| `backfillObservableInput(input)` | Add derived fields for hooks/SDK without mutating API input |

Default `checkPermissions`: returns `{ behavior: 'allow', updatedInput: input }`.
Default `isConcurrencySafe`: returns `false` (fail-closed).

### 2.6 Complete Data Transformation Chain

```
API tool_use block { type, id, name, input }
  -> findToolByName() -> Tool instance (checks name + aliases)
  -> inputSchema.safeParse(input) -> typed ParsedInput (Zod)
  -> tool.validateInput(parsedInput) -> ValidationResult
  -> runPreToolUseHooks() -> possible input modification
  -> resolveHookPermissionDecision() -> PermissionDecision { behavior, updatedInput }
  -> tool.call(callInput, context) -> ToolResult<Output> { data, newMessages?, contextModifier? }
  -> tool.mapToolResultToToolResultBlockParam(data, toolUseID) -> ToolResultBlockParam
  -> processToolResultBlock() -> size-limited, possibly persisted to disk
  -> createUserMessage({ content: [toolResultBlock] }) -> UserMessage
  -> Yielded back to query.ts -> appended to message history -> sent in next API call
```

---

## 3. Permission Checking Flow

The permission system uses a **3-step cascade** inside `hasPermissionsToUseToolInner()`, NOT a mode-first approach.

### 3.1 Core Cascade: `hasPermissionsToUseToolInner()`

```
Step 1: Deny and Ask Checks (BEFORE any mode check)
  │
  ├─ 1a: getDenyRuleForTool() — blanket deny on entire tool
  ├─ 1b: getAskRuleForTool() — blanket ask on entire tool
  │       (sandbox auto-allow exception for Bash)
  ├─ 1c: tool.checkPermissions(input, context) — tool-specific logic
  │       (NOT "userPermissionResult()" — that function does not exist)
  ├─ 1d: If tool returned deny -> return immediately
  ├─ 1e: If tool requiresUserInteraction() + returned ask -> return
  ├─ 1f: Content-specific ask rules (e.g., Bash(npm publish:*))
  │       -> return even in bypass mode (bypass-immune)
  └─ 1g: Safety checks (.git/, .claude/, shell configs)
          -> bypass-immune (safetyCheck reason type)

Step 2: Mode and Allow-Rule Checks
  │
  ├─ 2a: bypassPermissions mode OR (plan mode + bypass available) -> allow
  └─ 2b: toolAlwaysAllowedRule() — entire tool in allow list -> allow

Step 3: Passthrough Conversion
  │
  └─ If tool returned passthrough (no opinion) -> convert to ask
```

**Critical correction**: Mode checks happen at Step 2, AFTER deny rules and tool-specific checks. Bypass is NOT absolute -- steps 1d-1g all execute before bypass and can override it.

### 3.2 Post-Processing (Outer Function)

After the inner cascade returns:

```
allow  -> reset consecutive denial counter (auto mode), return
ask + dontAsk mode  -> convert to deny with DONT_ASK_REJECT_MESSAGE
ask + auto mode  -> multi-stage pipeline:
  ├─ Non-classifierApprovable safetyChecks -> immune to auto-approve
  ├─ requiresUserInteraction tools -> stay as ask
  ├─ PowerShell without POWERSHELL_AUTO_MODE -> stay as ask
  ├─ acceptEdits fast-path -> check if mode would allow
  ├─ Denial tracking fallback -> if too many consecutive denials, prompt user
  └─ YOLO classifier -> classifyYoloAction() with full transcript context
```

### 3.3 Interactive Handler: 5-Way Concurrent Permission Resolver

When permission is `ask` and no automated check resolves it:

```
                    +-- User interaction (onAllow/onReject/onAbort)
                    +-- Permission hooks (executePermissionRequestHooks)
Permission Ask -----+-- Bash classifier (executeAsyncClassifierCheck)
                    +-- Bridge response (CCR / claude.ai web UI)
                    +-- Channel response (Telegram, iMessage via MCP)

                    First to claim() wins via atomic ResolveOnce guard
```

`ResolveOnce` is an atomic check-and-mark preventing double-resolution across all async callbacks.

### 3.4 Permission Modes

| Mode | Scope | Behavior |
|------|-------|----------|
| `default` | External | Prompt for write/destructive operations |
| `acceptEdits` | External | Auto-allow file edits; prompt for shell |
| `plan` | External | Read-only mode; writes blocked |
| `bypassPermissions` | External | Full bypass (but NOT absolute -- safety checks still apply) |
| `dontAsk` | External | Convert all ask to deny silently |
| `auto` | Internal (ant-only) | AI classifier decides; gated by TRANSCRIPT_CLASSIFIER |
| `bubble` | Internal | Bubble up to parent (for subagents) |

### 3.5 Permission Rule Sources

Rules from ALL sources are flattened into arrays; first-match wins within each step. The cascade order (deny checked before allow) is the actual priority mechanism, not source ordering.

```
Sources: userSettings, projectSettings, localSettings,
         flagSettings, policySettings, cliArg, command, session
```

Rule format: `"ToolName"` or `"ToolName(content)"` with escaped parentheses.
Legacy tool name aliases resolved via `LEGACY_TOOL_NAME_ALIASES` (e.g., `Task` -> `Agent`).

---

## 4. State Management Flow

```
Global Singleton State (bootstrap/state.ts)
  │  Session-level: sessionId, originalCwd, totalCostUSD
  │  Model: mainLoopModelOverride, modelUsage
  │  Flags: isInteractive, kairosActive
  │
  └─ Updated by: query.ts (cost), bootstrap (session ID)
     Read by: all layers via exported getters

Per-Session App State (state/AppStateStore.ts + state/store.ts)
  │  messages: Message[]           -> conversation history
  │  tools: Tool[]                 -> active tool set
  │  settings: SettingsJson        -> current settings snapshot
  │  permissionMode: PermissionMode
  │  mcpConnections: MCPServerConnection[]
  │  speculationState: SpeculationState
  │  agentDefinitions: AgentDefinitionsResult
  │  taskState: TaskState[]
  │  agentNameRegistry: Map<string, string>  -> SendMessage routing
  │
  └─ Changed by: REPL hooks (settings/tools), onQuery (messages)
     Subscribed by: React components via useStore() hook

React Context (context/)
  │  notifications: Notification[]
  │  modalState, overlayState
  │  queuedMessages
  │
  └─ Changed by: hooks (useRateLimitWarning, useMcpConnectivity, etc.)
     Consumed by: REPL screen components
```

### Message State Transitions

```
User types message
  -> handlePromptSubmit orchestration (exit/queue/immediate routing)
  -> processTextPrompt() -> { messages: [UserMessage], shouldQuery: true }
  -> Append to AppState.messages via setMessages()

API streaming
  -> handleMessageFromStream() routes each SSE event type
  -> AssistantMessage accumulates text_delta chunks
  -> ToolUseBlock collected from tool_use events
  -> SpinnerMode transitions drive UI indicators

Tool execution
  -> Tool result appended as UserMessage with tool_result content
  -> Progress messages shown during execution (ephemeral, replaced not appended)

Session end / compact
  -> getMessagesAfterCompactBoundary() filters history
  -> recordTranscript() persists to ~/.claude/projects/<hash>/
```

---

## 5. Context Window Management Flow

Three-tier compaction hierarchy: microcompact (pre-pass) -> session memory (fast, no API) -> full LLM compact (expensive).

### 5.1 Threshold Formula (Absolute Token Counts, NOT Percentages)

```
effectiveContextWindow = min(contextWindowForModel, CLAUDE_CODE_AUTO_COMPACT_WINDOW)
                       - min(maxOutputTokensForModel, 20_000)

autoCompactThreshold   = effectiveContextWindow - 13,000

warningThreshold       = autoCompactThreshold - 20,000   (if auto-compact enabled)
                       = effectiveContextWindow - 20,000  (if disabled)

blockingLimit          = effectiveContextWindow - 3,000
```

Key constants (from autoCompact.ts):
- `MAX_OUTPUT_TOKENS_FOR_SUMMARY`: 20,000 (based on p99.99 = 17,387)
- `AUTOCOMPACT_BUFFER_TOKENS`: 13,000
- `WARNING_THRESHOLD_BUFFER_TOKENS`: 20,000
- `MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES`: 3 (circuit breaker)

Optional: `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` env var can set threshold as % of effective window.

### 5.2 Query Loop Integration (Per-Iteration)

```
1. microcompactMessages()          <- lightweight pre-pass
2. contextCollapse (if enabled)    <- alternative context management
3. autoCompactIfNeeded()           <- main compaction decision
4. Post-compact: replace messages, reset tracking, yield boundary + summary
```

### 5.3 Microcompact (Pre-Pass, Before Autocompact)

Two paths:

| Path | Trigger | Action | Mutates Messages? |
|------|---------|--------|-------------------|
| **Time-based** | Gap since last assistant message exceeds threshold | Content-clears old tool results with `[Old tool result content cleared]` | Yes (cache is cold) |
| **Cached** (cache_edits API) | Count-based threshold | Queues `cache_edits` blocks for server-side deletion | No (preserves cached prefix) |

Compactable tools: FileReadTool, FileEditTool, FileWriteTool, shell tools, GrepTool, GlobTool, WebSearchTool, WebFetchTool.

### 5.4 Session Memory Compaction (Fast Path, No API Call)

`trySessionMemoryCompaction()` — avoids the expensive LLM summarization call.

Prerequisites: `tengu_session_memory` AND `tengu_sm_compact` feature flags, session memory file exists.

Algorithm:
1. Find `lastSummarizedMessageId` in messages
2. Calculate tokens + text-block message count from that point
3. Keep at least 10,000 tokens OR 5 text messages, up to 40,000 tokens max
4. `adjustIndexToPreserveAPIInvariants()`: don't split tool_use/tool_result pairs, include thinking blocks
5. Post-threshold guard: if result would still exceed autoCompactThreshold, return null (fall through to full compact)

### 5.5 Full Compaction (Expensive LLM Summarization)

```
compactConversation()
  │
  ├─ Pre-compact hooks: executePreCompactHooks({ trigger: 'auto'|'manual' })
  │
  ├─ Summary generation via forked agent:
  │   runForkedAgent({
  │     promptMessages: [summaryRequest],
  │     cacheSafeParams,              <- shares parent's prompt cache prefix
  │     querySource: 'compact',
  │     maxTurns: 1,
  │     canUseTool: createCompactCanUseTool()  <- rejects all tools
  │   })
  │   Fallback: queryModelWithStreaming() if forked agent fails
  │   PTL retry loop (up to 3 retries): truncateHeadForPTLRetry()
  │
  ├─ Post-compact cleanup:
  │   Clear file state cache (readFileState, loadedNestedMemoryPaths)
  │   Generate file attachments (up to 5 files, 5K tokens each, 50K budget)
  │   Re-announce deltas (deferred tools, agent listing, MCP instructions)
  │   Run session start hooks (restore CLAUDE.md etc.)
  │
  └─ Create boundary: SystemCompactBoundaryMessage (type: 'system')
     Create summary: UserMessage with isCompactSummary: true
     Post-compact message order: boundary -> summary -> messagesToKeep -> attachments -> hookResults
```

### 5.6 Circuit Breaker

After 3 consecutive autocompact failures, compaction is disabled for the session. Added after BQ 2026-03-10 finding: 1,279 sessions had 50+ failures wasting ~250K API calls/day.

### 5.7 Context Collapse Mutual Exclusion

When context collapse is enabled, autocompact is suppressed. Collapse operates at 90% commit / 95% blocking; autocompact at ~93% would race it and destroy granular context.

---

## 6. MCP Tool Invocation Flow

```
MCP server configured in settings
  -> services/mcp/client.ts establishes connection
  -> getMcpToolsCommandsAndResources() discovers available tools
  -> assembleToolPool() merges MCP + built-in tools
     (built-ins win on name collision, sorted for prompt-cache stability)

When Claude invokes an MCP tool:
  MCPTool.call(input, context)
    -> Find MCPServerConnection by server name
    -> connection.client.callTool(toolName, input)
    -> MCP SDK sends JSON-RPC request to server process
    -> Server executes and returns result
    -> MCPTool formats result as ToolResultBlockParam
    -> PostToolUse hooks can modify MCP tool output
```

MCP tools (`mcp__*`) pass through all agent tool filters.

---

## 7. Agent Spawning Flow (6-Way Routing)

`AgentTool.call()` implements a 6-way routing decision:

```
call() entry
│
├─ [1] team_name + name -> spawnTeammate()
│   └─ Returns: teammate_spawned (flat roster, no nesting)
│
├─ [2] Resolve effectiveType:
│   ├─ subagent_type set -> use it
│   ├─ subagent_type omitted + FORK_SUBAGENT on -> fork path
│   └─ subagent_type omitted + FORK_SUBAGENT off -> 'general-purpose'
│
├─ [3] isForkPath (effectiveType === undefined)
│   ├─ Recursive fork guard: reject if already in fork child
│   └─ selectedAgent = FORK_AGENT (tools: ['*'], mode: 'bubble', maxTurns: 200)
│   └─ Cache sharing: parent's renderedSystemPrompt (byte-exact copy)
│       + buildForkedMessages() for cache-identical API prefixes
│
├─ [4] effectiveIsolation === 'remote' (ant-only)
│   └─ teleportToRemote() -> CCR session -> Returns: remote_launched
│
├─ [5] shouldRunAsync === true
│   └─ registerAsyncAgent() -> runAsyncAgentLifecycle() (fire-and-forget)
│   └─ Returns: async_launched
│
└─ [6] Synchronous (default)
    └─ registerAgentForeground() with auto-background timer (120s default)
    └─ Race: agentIterator.next() vs backgroundSignal
    └─ If backgrounded mid-execution: .return() iterator, restart as async
    └─ Returns: completed (or async_launched if backgrounded)
```

### 7.1 Core Execution: `runAgent()` (Async Generator)

```
runAgent() setup:
  1. Resolve model via getAgentModel()
  2. Build context messages (fork messages filtered for incomplete tool calls)
  3. Clone file state (fork: clone parent; normal: fresh cache)
  4. Configure permission mode (agent def can override; async agents auto-deny)
  5. Resolve tools: fork -> parent's exact tools; normal -> assembleToolPool() independently
  6. Build system prompt: fork -> parent's rendered bytes; normal -> computed
  7. Execute SubagentStart hooks
  8. Initialize agent MCP servers (additive to parent's)

  -> query() loop (same agentic while-loop as main path)
  -> Messages yielded to caller for progress tracking
  -> Sidechain transcript recording (O(1) per message)
```

### 7.2 Agent Cleanup (10 Operations)

`runAgent()` finally block: MCP server cleanup, clear session hooks, cleanup prompt cache tracking, release file state cache, release fork context messages, unregister Perfetto agent, clear transcript subdir, remove TodoWrite entries, kill background bash tasks, kill MCP monitor tasks.

### 7.3 Inter-Agent Communication: SendMessageTool

| Target | Mechanism |
|--------|-----------|
| Named teammate | `writeToMailbox()` -> filesystem mailbox (JSON envelope) |
| `"*"` (broadcast) | Iterate team file members, write to each mailbox |
| `"uds:<path>"` | Unix domain socket (feature-gated) |
| `"bridge:<id>"` | REPL bridge (remote control peer) |

Background agents receive messages via `queuePendingMessage()` drained at tool-round boundaries.

### 7.4 Built-in Agent Types

| Agent | Model | Tools | Key Properties |
|-------|-------|-------|----------------|
| **General Purpose** | inherited | `['*']` | Default; full tool access |
| **Explore** | haiku (ext) / inherit (ant) | All minus write tools | Read-only; omitClaudeMd |
| **Plan** | haiku (ext) / inherit (ant) | All minus write tools | Read-only architect |
| **Verification** | inherit | All minus write tools | background: true; strict PASS/FAIL/PARTIAL |
| **Fork** | inherit | parent's exact tools | bubble mode; cache-sharing |

---

## Appendix: Key Corrections from Original

| # | Original Claim | Corrected |
|---|---------------|-----------|
| 1 | REPL path uses `useTextInput -> submitMessage() -> QueryEngine.ts` | `onSubmit -> handlePromptSubmit -> executeUserInput -> processUserInput -> onQuery -> query()` |
| 2 | API call is `api.messages.stream()` | `anthropic.beta.messages.create({...params, stream: true}).withResponse()` |
| 3 | Permission checks mode first, then rules | Cascade: deny rules -> ask rules -> tool.checkPermissions() -> mode check -> allow rules |
| 4 | Function name: `userPermissionResult()` | `checkPermissions()` (tool-level), `hasPermissionsToUseTool()` (entry hook) |
| 5 | Sequential tool execution implied | `StreamingToolExecutor` enables parallel execution of concurrency-safe tools |
| 6 | No validation pipeline mentioned | 3-stage: Zod safeParse -> validateInput() -> PreToolUse hooks |
| 7 | Simple permission dialog, await user | 5-way concurrent race: user + hooks + classifier + bridge + channel |
| 8 | Compact thresholds as percentages (70%, 85%) | Absolute token counts: `effectiveContextWindow - 13,000` (not fixed %) |
| 9 | Type: `SDKCompactBoundaryMessage` | `SystemCompactBoundaryMessage` (type: 'system') |
| 10 | query.ts does `fetchSystemPromptParts()` | System prompt built in `onQueryImpl` (REPL) or `QueryEngine` (SDK), NOT query.ts |
| 11 | Missing `handlePromptSubmit` orchestration layer | Added: exit handling, queue management, reference expansion, queryGuard |
| 12 | No agent spawning flow | Added: 6-way routing, fork cache sharing, foreground-to-background race, SendMessage |

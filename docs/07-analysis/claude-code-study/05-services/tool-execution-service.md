# Tool Execution Service

> Core tool execution engine — streaming-aware concurrency, permission checks, hook lifecycle, error handling, and telemetry.

**Source**: `src/services/tools/` (4 files) + `src/services/MagicDocs/` (2 files) + `src/services/settingsSync/` (2 files) + `src/services/policyLimits/` (2 files)

---

## 1. services/tools/ — Tool Execution Engine

### Purpose

The core runtime for executing tool calls streamed from the Claude API. Manages concurrency control, permission checks, hook lifecycle (pre/post), error handling, progress reporting, and telemetry. This is the "inner loop" that turns model tool_use blocks into actual file edits, bash commands, MCP calls, etc.

### File Inventory (4 files)

| File | LOC (approx) | Purpose |
|------|--------------|---------|
| `StreamingToolExecutor.ts` | ~530 | Streaming-aware concurrency executor; processes tools as they arrive from the API stream |
| `toolExecution.ts` | ~700+ | Core `runToolUse()` entry point; permission checking, tool call, telemetry, error classification |
| `toolHooks.ts` | ~650 | Pre/post tool-use hook runners; permission resolution logic shared with REPL inner calls |
| `toolOrchestration.ts` | ~189 | Legacy batch orchestrator; partitions tools into concurrent-safe vs serial batches |

### Key Functions & Classes

#### StreamingToolExecutor (class)

The primary executor used during streaming API responses. Manages a queue of `TrackedTool` objects with states: `queued` -> `executing` -> `completed` -> `yielded`.

- **`addTool(block, assistantMessage)`**: Enqueues a tool from a streaming content block. Immediately checks `isConcurrencySafe` via the tool definition and starts execution if concurrency conditions allow.
- **`canExecuteTool(isConcurrencySafe)`**: Concurrency gate — concurrent-safe tools can run in parallel with other concurrent-safe tools; non-concurrent tools require exclusive access (no other tools executing).
- **`executeTool(tool)`**: Creates a per-tool abort controller (child of `siblingAbortController`), runs `runToolUse()`, collects results. On Bash errors, fires `siblingAbortController.abort('sibling_error')` to cancel sibling tools — only Bash errors cascade (Read/WebFetch failures are independent).
- **`getCompletedResults()` / `getRemainingResults()`**: Yield results in order, with progress messages yielded immediately regardless of completion order. Uses a `progressAvailableResolve` signal to wake up waiting consumers.
- **`discard()`**: Called on streaming fallback to abandon all pending/in-progress tools with synthetic error messages.
- **`createSyntheticErrorMessage()`**: Generates appropriate error messages for `sibling_error`, `user_interrupted`, and `streaming_fallback` abort reasons.

**Key design decisions**:
- Abort hierarchy: `toolUseContext.abortController` (parent, query-level) -> `siblingAbortController` (fires on Bash error) -> per-tool `toolAbortController`
- Permission-dialog rejection bubbles up to query controller (fix for #21056 regression)
- Context modifiers only supported for non-concurrent tools (noted as a TODO)

#### toolExecution.ts

- **`runToolUse(toolUse, assistantMessage, canUseTool, context)`**: Main entry point. Resolves tool by name (with deprecated alias fallback), checks abort state, delegates to `streamedCheckPermissionsAndCallTool()`.
- **`streamedCheckPermissionsAndCallTool()`**: Wraps `checkPermissionsAndCallTool()` using a `Stream` adapter to merge progress events and final results into a single `AsyncIterable`.
- **`checkPermissionsAndCallTool()`**: Full lifecycle:
  1. Zod schema validation (`inputSchema.safeParse`)
  2. Tool-specific validation (`tool.validateInput`)
  3. Pre-tool hooks (`runPreToolUseHooks`)
  4. Permission resolution (`resolveHookPermissionDecision`)
  5. Tool execution (`tool.call()`)
  6. Post-tool hooks (`runPostToolUseHooks`)
  7. Result formatting and telemetry
- **`classifyToolError(error)`**: Telemetry-safe error classifier that handles minified builds — extracts `TelemetrySafeError.telemetryMessage`, Node.js errno codes, or stable `.name` properties.
- **`buildSchemaNotSentHint(tool, messages, tools)`**: Detects when a deferred tool's schema wasn't included (ToolSearch not called first) and appends a corrective hint to the Zod error.

#### toolHooks.ts

- **`runPreToolUseHooks()`**: AsyncGenerator that executes pre-tool hooks and yields typed results: `message`, `hookPermissionResult`, `hookUpdatedInput`, `preventContinuation`, `stopReason`, `additionalContext`, or `stop`.
- **`runPostToolUseHooks()`**: AsyncGenerator for post-tool hooks. Supports `updatedMCPToolOutput` (hooks can modify MCP tool output), `preventContinuation`, `additionalContexts`, `blockingError`. Deduplicates `hook_blocking_error` attachments (fix for #31301).
- **`runPostToolUseFailureHooks()`**: Runs hooks specifically for tool execution failures (distinct from success hooks).
- **`resolveHookPermissionDecision()`**: Critical shared function that resolves a hook's permission result into a final `PermissionDecision`. Key invariant: **hook 'allow' does NOT bypass settings.json deny/ask rules** — `checkRuleBasedPermissions` still applies. Handles `requiresUserInteraction` and `requireCanUseTool` guards. Shared between `toolExecution.ts` and `REPLTool/toolWrappers.ts`.

#### toolOrchestration.ts

- **`runTools(toolUseMessages, assistantMessages, canUseTool, context)`**: Legacy batch mode — partitions tool calls via `partitionToolCalls()` into consecutive batches of concurrent-safe or non-concurrent tools.
- **`partitionToolCalls()`**: Groups tools into `Batch[]` where each batch is either a single non-concurrent tool or multiple consecutive concurrent-safe tools.
- **`runToolsSerially()` / `runToolsConcurrently()`**: Serial runs tools one-by-one with context modifier propagation; concurrent uses `all()` utility with `CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` (default 10).

### Integration Points

- **Upstream**: `query.ts` (main query loop) creates `StreamingToolExecutor` for streaming mode, or calls `runTools()` for batch mode
- **Downstream**: Every tool definition (`BashTool`, `FileEditTool`, `FileReadTool`, MCP tools, etc.) via `tool.call()`
- **Hook system**: `src/utils/hooks.ts` -> `executePreToolHooks`, `executePostToolHooks`
- **Permission system**: `src/utils/permissions/permissions.ts` -> `checkRuleBasedPermissions`
- **Analytics**: Extensive telemetry via `logEvent('tengu_tool_use_*')` and OTel tracing via `sessionTracing.ts`
- **MCP**: `src/services/mcp/` for MCP tool resolution, server connection lookup

---

## 2. services/MagicDocs/ — Auto-Updating Documentation

### Purpose

Automatically maintains markdown documentation files marked with `# MAGIC DOC: [title]` headers. When such a file is read, it gets tracked and periodically updated in the background by a forked subagent that incorporates new learnings from the conversation.

### File Inventory (2 files)

| File | LOC (approx) | Purpose |
|------|--------------|---------|
| `magicDocs.ts` | ~254 | Core logic: detection, tracking, update orchestration via subagent |
| `prompts.ts` | ~128 | Prompt template with variable substitution; supports custom prompts at `~/.claude/magic-docs/prompt.md` |

### Key Functions

- **`initMagicDocs()`**: Registers a `FileReadTool` listener and a post-sampling hook. **Gated to `USER_TYPE === 'ant'` only** (internal Anthropic users).
- **`detectMagicDocHeader(content)`**: Regex-based detection of `# MAGIC DOC: [title]` pattern at file start.
- **`updateMagicDoc(docInfo, context)`**: Core update logic — re-reads file, rebuilds prompt, runs `runAgent()` with `magic-docs` agent definition (model: `sonnet`, tools: `[Edit]` only).
- **`getMagicDocsAgent()`**: Returns a `BuiltInAgentDefinition` with `agentType: 'magic-docs'`, model `sonnet`, only `FILE_EDIT_TOOL_NAME` allowed.

### Key Design Decisions

- **Ant-only gate**: The entire feature is gated behind `USER_TYPE === 'ant'` — not available to external users.
- **Non-intrusive**: Uses `sequential()` wrapper, only runs when idle, uses forked subagent with `isAsync: true`.
- **File-scoped permissions**: The subagent can ONLY call Edit on the exact magic doc path.
- **Customizable**: Both the prompt template and the doc-specific instructions (via italics after the header) are user-configurable.

---

## 3. services/settingsSync/ — Cross-Environment Settings Sync

### Purpose

Synchronizes user settings (settings.json) and memory files (CLAUDE.md) across Claude Code environments — interactive CLI uploads to remote, CCR (Cloud Code Runner) downloads from remote.

### File Inventory (2 files)

| File | LOC (approx) | Purpose |
|------|--------------|---------|
| `index.ts` | ~582 | Full sync logic: upload (CLI), download (CCR), file operations, retry, OAuth auth |
| `types.ts` | ~68 | Zod schemas (`UserSyncDataSchema`, `UserSyncContentSchema`) and TypeScript types |

### Key Functions

- **`uploadUserSettingsInBackground()`**: CLI upload path. Incremental sync — only uploads changed entries.
- **`downloadUserSettings()`**: CCR download path. Cached `downloadPromise` pattern — first call starts fetch, subsequent calls join it.
- **`buildEntriesFromLocalFiles(projectId)`**: Collects sync entries from 4 sources: global user settings, global user memory, project settings, project memory.
- **`applyRemoteEntriesToLocal(entries, projectId)`**: Writes remote entries to local files. Uses `markInternalWrite()` to prevent spurious change detection.

### Sync Key Patterns

- `USER_SETTINGS`: `~/.claude/settings.json`
- `USER_MEMORY`: `~/.claude/CLAUDE.md`
- `projectSettings(id)`: `projects/{id}/.claude/settings.local.json`
- `projectMemory(id)`: `projects/{id}/CLAUDE.local.md`

### Key Design Decisions

- **Incremental upload**: Only changed entries are sent (diff against remote state).
- **Fail-open**: All errors caught and logged — never blocks startup.
- **Size limits**: 500 KB per file, defense-in-depth matching backend.
- **Cache invalidation**: Properly invalidates settings and memory caches after applying remote entries.

---

## 4. services/policyLimits/ — Organization Policy Restrictions

### Purpose

Fetches organization-level policy restrictions from the Anthropic API and uses them to disable CLI features for Team/Enterprise users. Follows fail-open pattern, with ETag caching, background polling, and retry logic.

### File Inventory (2 files)

| File | LOC (approx) | Purpose |
|------|--------------|---------|
| `index.ts` | ~664 | Full lifecycle: eligibility check, fetch with retry, file caching, background polling, policy checking |
| `types.ts` | ~28 | Zod schema for API response; fetch result type |

### Key Functions

- **`isPolicyLimitsEligible()`**: Must be `firstParty` API provider. Console users always eligible; OAuth needs `enterprise` or `team` subscription.
- **`loadPolicyLimits()`**: Called during CLI init. Fetches from API, starts background polling.
- **`isPolicyAllowed(policy)`**: **Synchronous** check at feature boundaries. Returns `true` if policy unknown (fail-open). Exception: `ESSENTIAL_TRAFFIC_DENY_ON_MISS` policies fail closed in HIPAA mode.
- **`fetchWithRetry(cachedChecksum?)`**: Up to 5 retries with exponential backoff. ETag via `If-None-Match`.

### Sync Intervals

| Phase | Interval | Mechanism |
|-------|----------|-----------|
| Initial load | Once at startup | `loadPolicyLimits()` |
| Background poll | Every 60 minutes | `setInterval` with `.unref()` |
| Auth change | On login/logout | `refreshPolicyLimits()` |

### Key Design Decisions

- **Fail-open**: Service availability prioritized over restriction enforcement.
- **Essential-traffic deny-on-miss**: Exception for `allow_product_feedback` in HIPAA mode — fails closed without cache.
- **Background polling**: 1-hour interval ensures policy changes take effect within an hour.
- **ETag caching**: Content-based SHA-256 checksums for efficient 304 responses.
- **No circular deps**: `isPolicyLimitsEligible()` explicitly avoids calling `getSettings()`.

---

## 5. Cross-Module Patterns

### Shared Patterns Across All Modules

1. **Forked subagent model**: Both MagicDocs and SessionMemory use forked subagents with restricted `canUseTool` (Edit-only on specific paths).

2. **Post-sampling hooks**: MagicDocs and SessionMemory both register via `registerPostSamplingHook()` and wrap in `sequential()` to prevent concurrent execution.

3. **Fail-open resilience**: settingsSync and policyLimits both follow fail-open — service unavailability never blocks CLI startup.

4. **Feature gating**: All modules use some form of gating:
   - MagicDocs: `USER_TYPE === 'ant'` (hardcoded)
   - settingsSync: `bun:bundle` features + GrowthBook flags
   - policyLimits: Eligibility check (auth type + subscription)
   - tools: Always enabled (core functionality)

5. **Custom prompt support**: MagicDocs (`~/.claude/magic-docs/prompt.md`) supports user-provided prompt overrides with `{{variable}}` substitution.

### Dependency Graph

```
query.ts
  |-- StreamingToolExecutor (streaming mode)
  |   |-- runToolUse() [toolExecution.ts]
  |       |-- runPreToolUseHooks() [toolHooks.ts]
  |       |-- resolveHookPermissionDecision() [toolHooks.ts]
  |       |-- tool.call() [actual tool execution]
  |       |-- runPostToolUseHooks() [toolHooks.ts]
  |-- runTools() [toolOrchestration.ts] (batch mode, legacy)

Post-sampling hooks (after each API response):
  |-- MagicDocs.updateMagicDocs()
  |   |-- runAgent() -> Edit tool only

Startup:
  |-- settingsSync.uploadUserSettingsInBackground() [CLI]
  |-- settingsSync.downloadUserSettings() [CCR]
  |-- policyLimits.initializePolicyLimitsLoadingPromise()
  |-- policyLimits.loadPolicyLimits()

Runtime checks:
  |-- policyLimits.isPolicyAllowed(policy) [synchronous, at feature boundaries]
```

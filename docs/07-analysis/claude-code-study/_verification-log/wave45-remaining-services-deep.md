# Wave 45: Deep Analysis — Remaining Service Modules

> **Scope**: `services/tools/` (4 files), `services/MagicDocs/` (2 files), `services/settingsSync/` (2 files), `services/SessionMemory/` (3 files), `services/policyLimits/` (2 files)
> **Date**: 2026-04-01
> **Quality Target**: Source-verified, function-level analysis

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

The primary executor used during streaming API responses. Manages a queue of `TrackedTool` objects with states: `queued` → `executing` → `completed` → `yielded`.

- **`addTool(block, assistantMessage)`**: Enqueues a tool from a streaming content block. Immediately checks `isConcurrencySafe` via the tool definition and starts execution if concurrency conditions allow.
- **`canExecuteTool(isConcurrencySafe)`**: Concurrency gate — concurrent-safe tools can run in parallel with other concurrent-safe tools; non-concurrent tools require exclusive access (no other tools executing).
- **`executeTool(tool)`**: Creates a per-tool abort controller (child of `siblingAbortController`), runs `runToolUse()`, collects results. On Bash errors, fires `siblingAbortController.abort('sibling_error')` to cancel sibling tools — only Bash errors cascade (Read/WebFetch failures are independent).
- **`getCompletedResults()` / `getRemainingResults()`**: Yield results in order, with progress messages yielded immediately regardless of completion order. Uses a `progressAvailableResolve` signal to wake up waiting consumers.
- **`discard()`**: Called on streaming fallback to abandon all pending/in-progress tools with synthetic error messages.
- **`createSyntheticErrorMessage()`**: Generates appropriate error messages for `sibling_error`, `user_interrupted`, and `streaming_fallback` abort reasons.

**Key design decisions**:
- Abort hierarchy: `toolUseContext.abortController` (parent, query-level) → `siblingAbortController` (fires on Bash error) → per-tool `toolAbortController`
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
- **`McpServerType`**: Union type for MCP transport types: `'stdio' | 'sse' | 'http' | 'ws' | 'sdk' | 'sse-ide' | 'ws-ide' | 'claudeai-proxy'`

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
- **Hook system**: `src/utils/hooks.ts` → `executePreToolHooks`, `executePostToolHooks`
- **Permission system**: `src/utils/permissions/permissions.ts` → `checkRuleBasedPermissions`
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

#### magicDocs.ts

- **`initMagicDocs()`**: Registers a `FileReadTool` listener and a post-sampling hook. **Gated to `USER_TYPE === 'ant'` only** (internal Anthropic users).
- **`detectMagicDocHeader(content)`**: Regex-based detection of `# MAGIC DOC: [title]` pattern at file start. Also detects optional italicized instructions on the next line (e.g., `_Focus on architecture decisions_`).
- **`registerMagicDoc(filePath)`**: Adds a file to `trackedMagicDocs` Map (idempotent — only registers once per path).
- **`updateMagicDoc(docInfo, context)`**: Core update logic:
  1. Clones `FileStateCache` to isolate reads (deletes doc entry to bypass dedup)
  2. Re-reads the file via `FileReadTool.call()` — if file deleted/unreadable, removes from tracking
  3. Re-detects header from latest content (removes from tracking if header gone)
  4. Builds update prompt via `buildMagicDocsUpdatePrompt()`
  5. Runs `runAgent()` with a `magic-docs` agent definition (model: `sonnet`, tools: `[Edit]` only)
  6. Custom `canUseTool` restricts to Edit for the exact magic doc file path only
- **`updateMagicDocs` (post-sampling hook)**: Wrapped in `sequential()` to prevent concurrent runs. Only fires on `repl_main_thread`, only when conversation is idle (no tool calls in last assistant turn).
- **`getMagicDocsAgent()`**: Returns a `BuiltInAgentDefinition` with `agentType: 'magic-docs'`, model `sonnet`, only `FILE_EDIT_TOOL_NAME` allowed.

#### prompts.ts

- **`buildMagicDocsUpdatePrompt(docContents, docPath, docTitle, instructions?)`**: Loads prompt template (custom or default), substitutes `{{docContents}}`, `{{docPath}}`, `{{docTitle}}`, `{{customInstructions}}` variables.
- **`loadMagicDocsPrompt()`**: Reads custom prompt from `~/.claude/magic-docs/prompt.md`, falls back to built-in template.
- **`substituteVariables(template, variables)`**: Single-pass `{{variable}}` replacement that avoids `$` backreference corruption and double-substitution bugs.

### Key Design Decisions

- **Ant-only gate**: The entire feature is gated behind `USER_TYPE === 'ant'` — not available to external users.
- **Non-intrusive**: Uses `sequential()` wrapper, only runs when idle, uses forked subagent with `isAsync: true`.
- **File-scoped permissions**: The subagent can ONLY call Edit on the exact magic doc path — all other tool uses are denied.
- **Customizable**: Both the prompt template and the doc-specific instructions (via italics after the header) are user-configurable.

### Integration Points

- **FileReadTool**: `registerFileReadListener` triggers magic doc detection on any file read
- **Post-sampling hooks**: `registerPostSamplingHook` for periodic updates
- **AgentTool/runAgent**: Forked subagent execution
- **FileEditTool**: Only allowed tool for the subagent

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

#### index.ts

- **`uploadUserSettingsInBackground()`**: CLI upload path. Called from `main.tsx preAction`. Guarded by: `feature('UPLOAD_USER_SETTINGS')`, GrowthBook feature flag `tengu_enable_settings_sync_push`, `getIsInteractive()`, and `isUsingOAuth()`. Performs incremental sync — only uploads changed entries (compares local vs remote via `lodash-es/pickBy`).
- **`downloadUserSettings()`**: CCR download path. Uses a cached `downloadPromise` pattern — first call starts fetch, subsequent calls join it. Called fire-and-forget at `runHeadless()` startup, then awaited before plugin install.
- **`redownloadUserSettings()`**: Mid-session refresh for `/reload-plugins` command. No retries (single attempt), caller must notify `settingsChangeDetector`.
- **`buildEntriesFromLocalFiles(projectId)`**: Collects sync entries from 4 sources: global user settings, global user memory, project settings, project memory. Project files keyed by `getRepoRemoteHash()`.
- **`applyRemoteEntriesToLocal(entries, projectId)`**: Writes remote entries to local files. Uses `markInternalWrite()` to prevent spurious change detection. Invalidates `resetSettingsCache()` and `clearMemoryFileCaches()` after writing.
- **`fetchUserSettings(maxRetries)`**: Retry wrapper with exponential backoff via `getRetryDelay()`. Max 3 retries by default.
- **`isUsingOAuth()`**: Checks first-party OAuth with `user:inference` scope (intentionally not requiring `user:profile` since CCR tokens only have inference).
- **`tryReadFileForSync(filePath)`**: Size-limited file reader (500 KB max per file, matches backend limit).

#### types.ts

- **`SYNC_KEYS`**: Defines sync key patterns:
  - `USER_SETTINGS`: `~/.claude/settings.json`
  - `USER_MEMORY`: `~/.claude/CLAUDE.md`
  - `projectSettings(id)`: `projects/{id}/.claude/settings.local.json`
  - `projectMemory(id)`: `projects/{id}/CLAUDE.local.md`
- **`UserSyncDataSchema`**: `{ userId, version, lastModified (ISO 8601), checksum (MD5), content: { entries } }`

### Key Design Decisions

- **Incremental upload**: Only changed entries are sent (diff against remote state).
- **Fail-open**: All errors caught and logged — never blocks startup.
- **Dual auth path**: Supports both API key (Console users) and OAuth (Claude.ai users).
- **Size limits**: 500 KB per file, defense-in-depth matching backend.
- **Cache invalidation**: Properly invalidates settings and memory caches after applying remote entries.

### Integration Points

- **OAuth**: `src/utils/auth.ts` for token management
- **Settings system**: `src/utils/settings/` for file paths and cache management
- **CLAUDE.md system**: `src/utils/claudemd.ts` for memory file caches
- **Git**: `getRepoRemoteHash()` for project identification
- **API**: Backend endpoint `/api/claude_code/user_settings` (anthropic/anthropic#218817)
- **GrowthBook**: Feature flags `tengu_enable_settings_sync_push`, `tengu_strap_foyer`

---

## 4. services/SessionMemory/ — Automatic Session Notes

### Purpose

Automatically maintains a structured markdown file (`session-memory.md`) with notes about the current conversation. Runs periodically in the background using a forked subagent to extract key information (task specification, files, errors, workflow, learnings) without interrupting the main conversation.

### File Inventory (3 files)

| File | LOC (approx) | Purpose |
|------|--------------|---------|
| `sessionMemory.ts` | ~496 | Core logic: initialization, extraction trigger logic, forked agent execution, manual extraction |
| `prompts.ts` | ~325 | Template (9 sections), update prompt, section size analysis, truncation for compaction |
| `sessionMemoryUtils.ts` | ~208 | Utility functions: config, state tracking, threshold checking, extraction coordination |

### Key Functions

#### sessionMemory.ts

- **`initSessionMemory()`**: Registers post-sampling hook if auto-compact is enabled and not in remote mode. Gate check (`tengu_session_memory` feature flag) happens lazily when hook runs.
- **`shouldExtractMemory(messages)`**: Dual-threshold logic:
  - **Token threshold** (`minimumTokensBetweenUpdate`, default 5000): Measures context window growth since last extraction. **Always required**.
  - **Tool calls threshold** (`toolCallsBetweenUpdates`, default 3): Counts tool calls since last extraction.
  - Extraction triggers when: (both thresholds met) OR (token threshold met AND no tool calls in last turn — natural conversation break).
  - **Initialization threshold** (`minimumMessageTokensToInit`, default 10000): Must be met before first extraction.
- **`extractSessionMemory` (post-sampling hook)**: Wrapped in `sequential()`. Only fires on `repl_main_thread`. Uses `runForkedAgent()` with isolated context (`createSubagentContext`). Only allows `FILE_EDIT_TOOL_NAME` on the exact memory path.
- **`manuallyExtractSessionMemory(messages, toolUseContext)`**: For `/summary` command — bypasses threshold checks, otherwise identical flow.
- **`setupSessionMemoryFile(toolUseContext)`**: Creates session memory directory and file with template content. Clones FileStateCache to isolate reads.
- **`createMemoryFileCanUseTool(memoryPath)`**: Exported permission function — only allows Edit on exact memory path.

#### prompts.ts

- **`DEFAULT_SESSION_MEMORY_TEMPLATE`**: 9 structured sections:
  1. Session Title (5-10 word descriptive)
  2. Current State (active work, pending tasks)
  3. Task specification (what user asked)
  4. Files and Functions (important files)
  5. Workflow (bash commands, order)
  6. Errors & Corrections (fixes, failed approaches)
  7. Codebase and System Documentation (system components)
  8. Learnings (what worked/didn't)
  9. Key results (exact output)
  10. Worklog (step-by-step terse summary)
- **`loadSessionMemoryTemplate()`**: Custom template from `~/.claude/session-memory/config/template.md`.
- **`loadSessionMemoryPrompt()`**: Custom prompt from `~/.claude/session-memory/config/prompt.md`.
- **`buildSessionMemoryUpdatePrompt(currentNotes, notesPath)`**: Substitutes variables and appends section size reminders.
- **`analyzeSectionSizes(content)`**: Counts tokens per section using `roughTokenCountEstimation()`.
- **`generateSectionReminders(sectionSizes, totalTokens)`**: Warns when sections exceed `MAX_SECTION_LENGTH` (2000 tokens) or total exceeds `MAX_TOTAL_SESSION_MEMORY_TOKENS` (12000 tokens).
- **`truncateSessionMemoryForCompact(content)`**: Truncates oversized sections at line boundaries for compaction insertion.
- **`isSessionMemoryEmpty(content)`**: Detects if content matches the template (no actual extraction done yet).

#### sessionMemoryUtils.ts

- **Config**: `SessionMemoryConfig` type with defaults: `{ minimumMessageTokensToInit: 10000, minimumTokensBetweenUpdate: 5000, toolCallsBetweenUpdates: 3 }`.
- **State tracking**: `tokensAtLastExtraction`, `sessionMemoryInitialized`, `lastSummarizedMessageId`, `extractionStartedAt`.
- **`waitForSessionMemoryExtraction()`**: Polls with 1s interval, 15s timeout, 60s stale threshold — used by compaction to wait for in-progress extraction.
- **`getSessionMemoryContent()`**: Reads from `getSessionMemoryPath()` — the file path within the session directory.

### Key Design Decisions

- **Token-gated, not time-gated**: Extraction frequency tied to context window growth, not wall clock.
- **Compaction integration**: Session memory feeds into auto-compact. If auto-compact disabled, session memory is also disabled.
- **Remote-configurable**: Thresholds configurable via GrowthBook `tengu_sm_config` dynamic config.
- **Structure preservation**: Prompt explicitly instructs subagent to never modify section headers or italic descriptions — only content below them.
- **Customizable**: Template, prompt, and config all loadable from `~/.claude/session-memory/config/`.

### Integration Points

- **Auto-compact**: `isAutoCompactEnabled()` gates initialization; session memory content injected during compaction
- **Post-sampling hooks**: `registerPostSamplingHook` for periodic extraction
- **Forked agent**: `runForkedAgent()` with prompt caching support
- **GrowthBook**: `tengu_session_memory` gate, `tengu_sm_config` dynamic config
- **FileReadTool/FileEditTool**: For reading/updating the session memory file
- **Token estimation**: `tokenCountWithEstimation()` for threshold comparison

---

## 5. services/policyLimits/ — Organization Policy Restrictions

### Purpose

Fetches organization-level policy restrictions from the Anthropic API and uses them to disable CLI features for Team/Enterprise users. Follows fail-open pattern, with ETag caching, background polling, and retry logic.

### File Inventory (2 files)

| File | LOC (approx) | Purpose |
|------|--------------|---------|
| `index.ts` | ~664 | Full lifecycle: eligibility check, fetch with retry, file caching, background polling, policy checking |
| `types.ts` | ~28 | Zod schema for API response; fetch result type |

### Key Functions

#### index.ts

- **`isPolicyLimitsEligible()`**: Eligibility check (must NOT call `getSettings()` to avoid circular deps):
  - Must be `firstParty` API provider with first-party base URL
  - Console users (API key): always eligible
  - OAuth users: must have `user:inference` scope AND `subscriptionType` of `'enterprise'` or `'team'`
- **`loadPolicyLimits()`**: Called during CLI init. Fetches from API, starts background polling. Resolves `loadingCompletePromise` when done.
- **`initializePolicyLimitsLoadingPromise()`**: Called early (e.g., `init.ts`) to create a promise that other systems can await, even before `loadPolicyLimits()` runs. Includes 30s timeout to prevent deadlocks.
- **`isPolicyAllowed(policy)`**: **Synchronous** check at feature boundaries. Returns `true` if policy unknown/unavailable (fail-open). Exception: `ESSENTIAL_TRAFFIC_DENY_ON_MISS` policies (currently `allow_product_feedback`) fail closed when essential-traffic-only mode is active and cache unavailable.
- **`fetchWithRetry(cachedChecksum?)`**: Up to 5 retries with exponential backoff via `getRetryDelay()`.
- **`fetchPolicyLimits(cachedChecksum?)`**: Single attempt — supports HTTP 304 (ETag via `If-None-Match`), 404 (no restrictions), 200 (new restrictions). Validates response with `PolicyLimitsResponseSchema`.
- **`fetchAndLoadPolicyLimits()`**: Full fetch-cache-apply lifecycle:
  1. Load cached restrictions from `~/.claude/policy-limits.json`
  2. Compute SHA-256 checksum for ETag
  3. Fetch with retry (passing checksum for 304 support)
  4. On success: update session cache + persist to disk
  5. On 404: delete cache file (no restrictions)
  6. On failure: fall back to stale cache
- **`startBackgroundPolling()`**: Polls every 1 hour (`POLLING_INTERVAL_MS`). Uses `setInterval` with `.unref()`. Registers cleanup handler.
- **`refreshPolicyLimits()`**: For auth state changes (login). Clears all caches and re-fetches.
- **`clearPolicyLimitsCache()`**: Stops polling, clears session cache, deletes cache file.
- **`computeChecksum(restrictions)`**: Deep-sorts keys for consistent hashing, then SHA-256 → `sha256:` prefix.

#### types.ts

- **`PolicyLimitsResponseSchema`**: `{ restrictions: Record<string, { allowed: boolean }> }`
- **`PolicyLimitsFetchResult`**: `{ success, restrictions?, etag?, error?, skipRetry? }` — `restrictions: null` means 304 Not Modified.

### Key Design Decisions

- **Fail-open**: Service availability prioritized over restriction enforcement. If API unreachable and no cache, all policies allowed.
- **Essential-traffic deny-on-miss**: Exception for `allow_product_feedback` in essential-traffic-only (HIPAA) mode — this one fails closed without cache.
- **Background polling**: 1-hour interval ensures policy changes take effect within an hour without restart.
- **ETag caching**: Content-based checksums (SHA-256) for efficient 304 responses.
- **No circular deps**: `isPolicyLimitsEligible()` explicitly avoids calling `getSettings()`.
- **Dual auth**: Supports both API key and OAuth authentication for policy fetch.

### Integration Points

- **OAuth**: `src/utils/auth.ts` for token management and refresh
- **API providers**: `src/utils/model/providers.ts` for eligibility checks
- **Privacy**: `isEssentialTrafficOnly()` for HIPAA mode
- **Cleanup registry**: `registerCleanup()` for graceful shutdown
- **API**: Backend endpoint `/api/claude_code/policy_limits`
- **Init system**: `initializePolicyLimitsLoadingPromise()` called from `init.ts`

---

## 6. Discrepancy Analysis vs Existing Documentation

### vs cost-tracking.md (policyLimits section)

The existing doc at `03-ai-engine/cost-tracking.md` has a brief but accurate summary. Findings:

| Claim | Verified? | Notes |
|-------|-----------|-------|
| "Console users and Team/Enterprise OAuth" eligible | **Correct** | Source confirms `isPolicyLimitsEligible()` logic |
| "loadPolicyLimits() with retry, cached in ~/.claude/policy-limits.json" | **Correct** | Up to 5 retries, SHA-256 ETag caching |
| "Polling every 1 hour" | **Correct** | `POLLING_INTERVAL_MS = 60 * 60 * 1000` |
| "Fail-open" | **Mostly correct** | One exception: `allow_product_feedback` fails closed in essential-traffic-only mode |
| "isPolicyAllowed(policy) — synchronous" | **Correct** | Uses session cache or file cache synchronously |

**Missing from existing doc**: `ESSENTIAL_TRAFFIC_DENY_ON_MISS` exception, `initializePolicyLimitsLoadingPromise()` early init pattern, `refreshPolicyLimits()` for auth changes, `redownloadUserSettings()` mid-session refresh.

### vs memory-system.md (SessionMemory section)

The existing doc at `05-services/memory-system.md` covers session memory briefly under "Session Memory" and "Session-Scoped State" but conflates two different concepts:

| Claim | Verified? | Notes |
|-------|-----------|-------|
| "Session-scoped state: message history, file state cache, tool decisions" | **Partially correct** | This describes `ToolUseContext` state, not the `SessionMemory` service |
| "Sessions can be resumed" | **Correct** but unrelated to `services/SessionMemory/` |

**Major gap**: The existing doc does NOT describe the `services/SessionMemory/` module at all. It describes session state management (which is in `ToolUseContext` and the compact system), not the automatic session notes extraction service. The SessionMemory service:
- Maintains a structured markdown file with 9 sections
- Uses a forked subagent with sonnet model
- Has token-based + tool-call-based dual thresholds
- Is gated by GrowthBook feature flag `tengu_session_memory`
- Integrates with auto-compact (disabled if auto-compact disabled)
- Supports custom templates and prompts at `~/.claude/session-memory/config/`

**Recommendation**: The memory-system.md needs a new section specifically for the `services/SessionMemory/` auto-extraction service, distinct from the existing session state discussion.

---

## 7. Cross-Module Patterns

### Shared Patterns Across All 5 Modules

1. **Forked subagent model**: Both MagicDocs and SessionMemory use forked subagents with restricted `canUseTool` (Edit-only on specific paths). This is the standard pattern for background work that touches files.

2. **Post-sampling hooks**: MagicDocs and SessionMemory both register via `registerPostSamplingHook()` and wrap in `sequential()` to prevent concurrent execution. Both only fire on `repl_main_thread`.

3. **Fail-open resilience**: settingsSync and policyLimits both follow fail-open — service unavailability never blocks CLI startup.

4. **Feature gating**: All modules use some form of gating:
   - MagicDocs: `USER_TYPE === 'ant'` (hardcoded)
   - SessionMemory: GrowthBook `tengu_session_memory` + auto-compact enabled
   - settingsSync: `bun:bundle` features + GrowthBook flags
   - policyLimits: Eligibility check (auth type + subscription)
   - tools: Always enabled (core functionality)

5. **Custom prompt support**: Both MagicDocs (`~/.claude/magic-docs/prompt.md`) and SessionMemory (`~/.claude/session-memory/config/prompt.md`) support user-provided prompt overrides with `{{variable}}` substitution.

6. **FileStateCache isolation**: Both MagicDocs and SessionMemory clone `readFileState` and delete specific entries before reading to bypass FileReadTool's dedup (which would return `file_unchanged` stubs).

### Dependency Graph

```
query.ts
  └─ StreamingToolExecutor (streaming mode)
     └─ runToolUse() [toolExecution.ts]
        ├─ runPreToolUseHooks() [toolHooks.ts]
        ├─ resolveHookPermissionDecision() [toolHooks.ts]
        ├─ tool.call() [actual tool execution]
        └─ runPostToolUseHooks() [toolHooks.ts]
  └─ runTools() [toolOrchestration.ts] (batch mode, legacy)

Post-sampling hooks (after each API response):
  ├─ MagicDocs.updateMagicDocs()
  │   └─ runAgent() → Edit tool only
  └─ SessionMemory.extractSessionMemory()
      └─ runForkedAgent() → Edit tool only

Startup:
  ├─ settingsSync.uploadUserSettingsInBackground() [CLI]
  ├─ settingsSync.downloadUserSettings() [CCR]
  ├─ policyLimits.initializePolicyLimitsLoadingPromise()
  └─ policyLimits.loadPolicyLimits()

Runtime checks:
  └─ policyLimits.isPolicyAllowed(policy) [synchronous, at feature boundaries]
```

# LSP Service

> Language Server Protocol integration — server lifecycle, tool operations, diagnostic registry, and passive feedback.

**Source**: `src/services/lsp/` (7 files, ~2,467 LOC) + `src/tools/LSPTool/` (6 files, ~2,133 LOC)
**Quality**: 8.5+/10

---

## 1. Architecture Overview

The LSP subsystem provides Language Server Protocol integration for Claude Code, enabling code intelligence features (go-to-definition, find-references, hover, etc.) by managing external language server processes. The architecture follows a **four-layer design**:

```
┌─────────────────────────────────────────────────────────┐
│  LSPTool (Tool Layer)                                   │
│  src/tools/LSPTool/LSPTool.ts                           │
│  - 9 operations exposed to Claude                       │
│  - Input validation, permission checks                  │
│  - Result formatting, gitignore filtering               │
├─────────────────────────────────────────────────────────┤
│  manager.ts (Singleton Layer)                           │
│  src/services/lsp/manager.ts                            │
│  - Global singleton lifecycle                           │
│  - Async initialization (non-blocking startup)          │
│  - Generation counter for stale-promise protection      │
├─────────────────────────────────────────────────────────┤
│  LSPServerManager.ts (Routing Layer)                    │
│  src/services/lsp/LSPServerManager.ts                   │
│  - Extension-to-server mapping                          │
│  - File synchronization (didOpen/didChange/didSave)     │
│  - Request routing by file type                         │
├─────────────────────────────────────────────────────────┤
│  LSPServerInstance.ts (Instance Layer)                  │
│  src/services/lsp/LSPServerInstance.ts                  │
│  - State machine (stopped→starting→running→stopping)    │
│  - Health monitoring, restart logic                     │
│  - Transient error retry with exponential backoff       │
├─────────────────────────────────────────────────────────┤
│  LSPClient.ts (Transport Layer)                         │
│  src/services/lsp/LSPClient.ts                          │
│  - JSON-RPC over stdio via vscode-jsonrpc               │
│  - Process spawn + lifecycle management                 │
│  - Pending handler queues (lazy initialization)         │
└─────────────────────────────────────────────────────────┘

  Side channels:
  ┌───────────────────────┐  ┌──────────────────────────┐
  │ LSPDiagnosticRegistry │  │ passiveFeedback.ts       │
  │ - Pending diagnostics │  │ - publishDiagnostics     │
  │ - LRU dedup (500 max) │  │   notification handler   │
  │ - Volume limiting     │  │ - Severity mapping       │
  │   10/file, 30 total   │  │ - Attachment formatting  │
  └───────────────────────┘  └──────────────────────────┘

  Config:
  ┌──────────────────────────────────────────────────────┐
  │ config.ts - Plugin-based LSP server discovery        │
  │ - Loads from enabled plugins (parallel Promise.all)  │
  │ - No user/project settings support (plugins only)    │
  └──────────────────────────────────────────────────────┘
```

---

## 2. LSP Client Lifecycle

### 2.1 Process Spawning (`LSPClient.ts`)

The `createLSPClient(serverName, onCrash?)` factory creates a closure-based client:

1. **Spawn**: `child_process.spawn()` with `stdio: ['pipe', 'pipe', 'pipe']`, `windowsHide: true`
2. **Spawn Verification**: Awaits the `spawn` event before using streams (prevents ENOENT unhandled rejections)
3. **JSON-RPC Connection**: `vscode-jsonrpc` `StreamMessageReader`/`StreamMessageWriter` over stdin/stdout
4. **Error Handlers**: Registered before `connection.listen()` to catch all errors
5. **Trace**: Verbose protocol tracing enabled (catches $/setTrace failures gracefully)
6. **Pending Handler Drain**: Queued notification/request handlers applied after connection ready

Key design decisions:
- **Closure-based, not class-based**: All state (`process`, `connection`, `capabilities`, `isInitialized`) in closure variables
- **`isStopping` flag**: Prevents spurious error logging during intentional shutdown
- **Notifications are fire-and-forget**: `sendNotification` catches errors, logs, but does not re-throw
- **`onCrash` callback**: Allows `LSPServerInstance` to detect crash and transition to `error` state

### 2.2 Graceful Shutdown

The `stop()` method follows a defensive sequence:
1. Set `isStopping = true` (suppress spurious logs)
2. Send `shutdown` request + `exit` notification
3. `connection.dispose()` in finally block
4. `process.kill()` with listener cleanup
5. Reset state (but preserve `startFailed`/`startError` for diagnostics)
6. Re-throw shutdown errors after cleanup

---

## 3. Server Management

### 3.1 LSPServerInstance State Machine

```
  stopped ──→ starting ──→ running
    ↑              │          │
    │              ↓          ↓
    └── stopping ←─┤       error
                   │          │
                   └──────────┘
                  (retry via start())
```

States: `stopped`, `starting`, `running`, `stopping`, `error` (type `LspServerState` from `types.ts`)

**Crash Recovery**:
- `onCrash` callback transitions state to `error`, increments `crashRecoveryCount`
- `start()` checks `crashRecoveryCount > maxRestarts` (default: 3) before retry
- Successful start resets `crashRecoveryCount` to 0

**Transient Error Retry** (in `sendRequest`):
- LSP error code `-32801` (ContentModified) triggers automatic retry
- Up to 3 retries with exponential backoff: 500ms, 1000ms, 2000ms
- Common with rust-analyzer during project indexing

**Unimplemented Config Fields**:
- `restartOnCrash` and `shutdownTimeout` throw errors if set (future work)

### 3.2 LSPServerManager (Routing)

`createLSPServerManager()` manages multiple server instances:

**Data Structures**:
- `servers: Map<string, LSPServerInstance>` -- all server instances
- `extensionMap: Map<string, string[]>` -- file extension to server name(s)
- `openedFiles: Map<string, string>` -- file URI to server name (tracks didOpen state)

**Extension-Based Routing**:
- `config.extensionToLanguage` dict maps extensions to language IDs
- `getServerForFile()` looks up extension, returns first matching server
- Multiple servers per extension supported (first-registered wins)

**File Synchronization Protocol**:
| Method | LSP Notification | Behavior |
|--------|-----------------|----------|
| `openFile(path, content)` | `textDocument/didOpen` | Sends languageId from config, tracks in openedFiles |
| `changeFile(path, content)` | `textDocument/didChange` | Falls back to openFile if not yet opened |
| `saveFile(path)` | `textDocument/didSave` | Triggers diagnostics from server |
| `closeFile(path)` | `textDocument/didClose` | Removes from openedFiles tracking |

**Note**: `closeFile` has a TODO for integration with compact flow (not yet integrated).

**workspace/configuration Handler**: Registered for each server to return `null` for all config items (some servers like TypeScript send these even when capability is not advertised).

### 3.3 Singleton Manager (`manager.ts`)

Global lifecycle management with these key features:

**Initialization States**: `not-started`, `pending`, `success`, `failed`

**Generation Counter**: `initializationGeneration` prevents stale promises from updating state after re-initialization.

**Bare Mode Skip**: `isBareMode()` check -- LSP is disabled for scripted `-p` calls.

**Re-initialization** (`reinitializeLspServerManager`):
- Fixes issue #15521: memoized `loadAllPlugins()` could cache empty plugin list before marketplace reconciliation
- Shuts down old instance (fire-and-forget), resets state, calls `initializeLspServerManager()`
- Safe to call when no LSP plugins changed (servers are lazy-started)

**`isLspConnected()`**: Returns true if at least one server is not in `error` state. Backs `LSPTool.isEnabled()`.

---

## 4. LSP Configuration (`config.ts`)

LSP servers are **plugin-only** -- no user/project settings support.

`getAllLspServers()`:
1. Loads all enabled plugins via `loadAllPluginsCacheOnly()`
2. Calls `getPluginLspServers(plugin, errors)` in parallel (`Promise.all`)
3. Merges results with `Object.assign` (later plugins win on collision)
4. Defensive: individual plugin failures don't prevent loading others

The `ScopedLspServerConfig` type includes:
- `command: string` -- server executable
- `args?: string[]` -- command arguments
- `env?: Record<string, string>` -- environment variables
- `workspaceFolder?: string` -- working directory
- `extensionToLanguage: Record<string, string>` -- file extension to language ID mapping
- `initializationOptions?: object` -- passed to LSP initialize (needed by vue-language-server)
- `startupTimeout?: number` -- initialization timeout in ms
- `maxRestarts?: number` -- default 3
- `restartOnCrash?: undefined` -- not yet implemented (throws if set)
- `shutdownTimeout?: undefined` -- not yet implemented (throws if set)

---

## 5. Diagnostic Registry (`LSPDiagnosticRegistry.ts`)

Stores diagnostics received asynchronously from LSP servers via `textDocument/publishDiagnostics`.

### 5.1 Architecture Pattern

Follows the same pattern as `AsyncHookRegistry`:
1. LSP server sends `publishDiagnostics` notification
2. `registerPendingLSPDiagnostic()` stores in `pendingDiagnostics` Map (UUID-keyed)
3. `checkForLSPDiagnostics()` retrieves, deduplicates, and marks as sent
4. Delivered via attachment system to conversation

### 5.2 Deduplication

**Within-batch dedup**: JSON key from `{message, severity, range, source, code}` per file URI.

**Cross-turn dedup**: `deliveredDiagnostics` LRU cache (max 500 files) tracks previously delivered diagnostics. Prevents re-sending the same diagnostic across turns.

**File edit reset**: `clearDeliveredDiagnosticsForFile(fileUri)` clears cross-turn tracking when a file is edited, so new diagnostics for that file are shown.

### 5.3 Volume Limiting

Applied after deduplication, sorted by severity (Error first):
- **Per-file cap**: `MAX_DIAGNOSTICS_PER_FILE = 10`
- **Total cap**: `MAX_TOTAL_DIAGNOSTICS = 30`

### 5.4 Cleanup Functions

| Function | Clears Pending | Clears Delivered | Use Case |
|----------|---------------|-----------------|----------|
| `clearAllLSPDiagnostics()` | Yes | No | Shutdown/cleanup |
| `resetAllLSPDiagnosticState()` | Yes | Yes | Session reset, testing |
| `clearDeliveredDiagnosticsForFile(uri)` | No | Per-file | After file edit |

---

## 6. Passive Feedback (`passiveFeedback.ts`)

### 6.1 Notification Handler Registration

`registerLSPNotificationHandlers(manager)`:
- Iterates all servers from `manager.getAllServers()`
- Registers `textDocument/publishDiagnostics` handler on each
- Returns `HandlerRegistrationResult` with success/failure tracking

### 6.2 Diagnostic Processing Pipeline

1. **Validate params**: Check for `uri` and `diagnostics` fields
2. **Format**: `formatDiagnosticsForAttachment()` converts LSP format to Claude's `DiagnosticFile[]`
3. **Severity mapping**: LSP numeric (1-4) to string (`Error`, `Warning`, `Info`, `Hint`)
4. **URI handling**: Supports both `file://` URIs and plain paths with fallback
5. **Register**: Calls `registerPendingLSPDiagnostic()` for async delivery
6. **Failure tracking**: Consecutive failures per server, warns after 3+

### 6.3 Error Isolation

Each server's handler is isolated -- errors in one server's handler don't break others. Registration failures are tracked and reported but don't fail the overall registration.

---

## 7. Supported Operations (9 Total)

The LSPTool exposes 9 operations mapped to LSP protocol methods:

| # | Operation | LSP Method | Input | Output |
|---|-----------|-----------|-------|--------|
| 1 | `goToDefinition` | `textDocument/definition` | file + position | Location/LocationLink |
| 2 | `findReferences` | `textDocument/references` | file + position | Location[] |
| 3 | `hover` | `textDocument/hover` | file + position | Hover (markdown/plaintext) |
| 4 | `documentSymbol` | `textDocument/documentSymbol` | file + position | DocumentSymbol[]/SymbolInformation[] |
| 5 | `workspaceSymbol` | `workspace/symbol` | file + position | SymbolInformation[] |
| 6 | `goToImplementation` | `textDocument/implementation` | file + position | Location/LocationLink |
| 7 | `prepareCallHierarchy` | `textDocument/prepareCallHierarchy` | file + position | CallHierarchyItem[] |
| 8 | `incomingCalls` | Two-step: prepare + `callHierarchy/incomingCalls` | file + position | CallHierarchyIncomingCall[] |
| 9 | `outgoingCalls` | Two-step: prepare + `callHierarchy/outgoingCalls` | file + position | CallHierarchyOutgoingCall[] |

### 7.1 Input Schema

All operations share the same input shape:
- `operation`: discriminated union enum
- `filePath`: absolute or relative path
- `line`: 1-based (converted to 0-based for LSP protocol)
- `character`: 1-based (converted to 0-based for LSP protocol)

Validated against a Zod discriminated union (`lspToolInputSchema`) for precise error messages.

### 7.2 Two-Step Call Hierarchy

For `incomingCalls` and `outgoingCalls`:
1. First send `textDocument/prepareCallHierarchy` to get `CallHierarchyItem[]`
2. Use the first item to request `callHierarchy/incomingCalls` or `callHierarchy/outgoingCalls`

### 7.3 Gitignore Filtering

Location-based results (`findReferences`, `goToDefinition`, `goToImplementation`, `workspaceSymbol`) are filtered through `git check-ignore`:
- Extracts unique file paths from result URIs
- Batched `git check-ignore` calls (50 paths per batch, 5s timeout)
- Removes results from gitignored files

### 7.4 File Size Guard

Files larger than 10MB (`MAX_LSP_FILE_SIZE_BYTES = 10_000_000`) are rejected before sending to LSP server.

---

## 8. Tool System Integration

### 8.1 LSPTool Properties

| Property | Value | Purpose |
|----------|-------|---------|
| `name` | `'LSP'` | Tool identifier |
| `isLsp` | `true` | Marks as LSP tool |
| `shouldDefer` | `true` | Deferred loading (schema fetched on demand) |
| `isEnabled()` | `isLspConnected()` | Only visible when LSP server(s) healthy |
| `isConcurrencySafe()` | `true` | Can run in parallel |
| `isReadOnly()` | `true` | No filesystem mutations |
| `maxResultSizeChars` | `100,000` | Output truncation limit |

### 8.2 Permission Model

Uses `checkReadPermissionForTool()` -- read-only filesystem permission check.

**Security**: UNC paths (`\\...` or `//...`) are skipped to prevent NTLM credential leaks on Windows.

### 8.3 File Synchronization on Tool Call

Before sending any LSP request, the tool ensures the file is open:
1. Check `manager.isFileOpen(absolutePath)`
2. If not open: read file content, call `manager.openFile()`
3. This triggers `textDocument/didOpen` notification to the server

### 8.4 Initialization Wait

If `getInitializationStatus()` returns `pending`, the tool awaits `waitForInitialization()` before proceeding. This prevents returning "no server available" during startup.

---

## 9. Language Detection

Language detection is **configuration-driven**, not heuristic-based:

- Each LSP server plugin defines `extensionToLanguage: Record<string, string>` mapping file extensions to LSP language IDs
- Examples: `{".ts": "typescript", ".py": "python", ".rs": "rust"}`
- The `LSPServerManager` builds an `extensionMap` during initialization
- `getServerForFile()` uses `path.extname()` to look up the appropriate server
- If no server handles an extension, operations return "No LSP server available"

### LSP Capabilities Advertised

During initialization (`InitializeParams.capabilities`):
- `textDocument.synchronization`: didSave supported, willSave not supported
- `textDocument.publishDiagnostics`: relatedInformation, tagSupport (Unnecessary/Deprecated), codeDescriptionSupport
- `textDocument.hover`: markdown and plaintext content formats
- `textDocument.definition`: linkSupport enabled
- `textDocument.references`: basic support
- `textDocument.documentSymbol`: hierarchical support
- `textDocument.callHierarchy`: basic support
- `workspace.configuration`: **false** (avoids servers requesting config we can't provide)
- `workspace.workspaceFolders`: **false** (no didChangeWorkspaceFolders support)
- `general.positionEncodings`: UTF-16

Both modern (`workspaceFolders`) and deprecated (`rootPath`, `rootUri`) workspace fields are sent for compatibility.

---

## 10. Error Handling Strategy

### 10.1 Layered Error Handling

| Layer | Strategy | Details |
|-------|----------|---------|
| LSPClient | Catch + log + re-throw (requests), catch + log + swallow (notifications) | `isStopping` suppresses spurious errors |
| LSPServerInstance | State transition to `error`, crash recovery with max retry | Exponential backoff for ContentModified |
| LSPServerManager | Per-server isolation, continue with other servers | Config validation before instance creation |
| manager.ts | Generation counter prevents stale updates | Fire-and-forget shutdown on reinit |
| LSPDiagnosticRegistry | Dedup errors include diagnostic anyway | LRU cache prevents memory growth |
| passiveFeedback.ts | Per-server error isolation, consecutive failure tracking | Warns after 3+ consecutive failures |
| LSPTool | Catches all errors, returns structured error output | Never throws to conversation |

### 10.2 Key Error Patterns

- **Spawn Failure**: Awaits `spawn` event before using streams (prevents ENOENT crashes)
- **stdin Error**: Suppressed during shutdown, logged otherwise
- **Connection Close**: Only treated as error if not intentionally stopping
- **Stale Init**: Generation counter invalidates abandoned initialization promises
- **Zombie State Prevention**: `onCrash` callback transitions state from `running` to `error`

---

## 11. UI Layer (`LSPTool/UI.tsx`)

The UI layer provides React (Ink) components for terminal rendering:

- **`renderToolUseMessage`**: Shows operation + file + symbol context (e.g., "Finding definition of `createLSPClient` in src/services/lsp/LSPClient.ts:51:17")
- **`renderToolResultMessage`**: Collapsed summary (count + files) with Ctrl+O to expand full results
- **`renderToolUseErrorMessage`**: Delegates to `FallbackToolUseErrorMessage`
- **`userFacingName`**: Returns human-readable operation name for UI display

### Symbol Context Extraction (`symbolContext.ts`)

`getSymbolAtPosition(filePath, line, character)`:
- Reads first 64KB of file synchronously (called from React render)
- Extracts word at position using regex pattern matching
- Supports: standard identifiers, Rust lifetimes (`'a`), macros (`name!`), operators
- Truncates symbols to 30 characters
- Returns `null` on any error (graceful fallback to position display)

---

## 12. Formatters (`LSPTool/formatters.ts`)

Eight dedicated formatters produce human-readable output:

| Formatter | Input Type | Output Format |
|-----------|-----------|---------------|
| `formatGoToDefinitionResult` | Location/LocationLink | "Defined in path:line:char" or list |
| `formatFindReferencesResult` | Location[] | Grouped by file with line numbers |
| `formatHoverResult` | Hover | Markdown/plaintext content |
| `formatDocumentSymbolResult` | DocumentSymbol[]/SymbolInformation[] | Hierarchical tree with indentation |
| `formatWorkspaceSymbolResult` | SymbolInformation[] | Grouped by file with kind and container |
| `formatPrepareCallHierarchyResult` | CallHierarchyItem[] | Name (Kind) - path:line |
| `formatIncomingCallsResult` | CallHierarchyIncomingCall[] | Grouped by file with call sites |
| `formatOutgoingCallsResult` | CallHierarchyOutgoingCall[] | Grouped by file with call sites |

Common patterns:
- All formatters handle null/empty gracefully with descriptive messages
- URI formatting: strips `file://`, handles Windows drive letters, percent-decoding, relative path optimization
- Invalid location filtering with debug logging
- SymbolKind enum to string mapping (26 kinds: File through TypeParameter)

---

## 13. File Inventory

### `src/services/lsp/` (7 files)

| File | LOC | Purpose |
|------|-----|---------|
| `config.ts` | 80 | Plugin-based LSP server discovery |
| `LSPClient.ts` | 448 | JSON-RPC client over stdio |
| `LSPDiagnosticRegistry.ts` | 387 | Async diagnostic storage with dedup + volume limiting |
| `LSPServerInstance.ts` | 512 | Single server lifecycle + state machine |
| `LSPServerManager.ts` | 421 | Multi-server routing + file sync |
| `manager.ts` | 290 | Global singleton lifecycle |
| `passiveFeedback.ts` | 329 | publishDiagnostics handler + formatting |
| **Total** | **~2,467** | |

### `src/tools/LSPTool/` (6 files)

| File | LOC | Purpose |
|------|-----|---------|
| `LSPTool.ts` | 861 | Main tool implementation (9 operations) |
| `schemas.ts` | 216 | Zod discriminated union input schema |
| `prompt.ts` | 22 | Tool name + description |
| `formatters.ts` | 593 | 8 result formatters |
| `symbolContext.ts` | 91 | Symbol extraction at position |
| `UI.tsx` | ~350+ | React (Ink) UI components |
| **Total** | **~2,133** | |

**Grand Total**: ~4,600 LOC across 13 files.

---

## 14. Key Findings

### Strengths

1. **Robust error isolation**: Every layer has independent error handling; one server's failure never cascades
2. **Smart deduplication**: Cross-turn LRU-based diagnostic dedup prevents flooding the conversation
3. **Lazy initialization**: `vscode-jsonrpc` (~129KB) only loads when an LSP server is actually instantiated
4. **Windows-aware**: `windowsHide`, UNC path security, drive letter handling throughout
5. **Transient error handling**: ContentModified retry with exponential backoff is production-quality

### Design Observations

1. **Plugin-only config**: No way for users to configure LSP servers directly -- must go through plugin system
2. **Closure-over-class pattern**: All factories (`createLSPClient`, `createLSPServerInstance`, `createLSPServerManager`) use closures instead of classes -- consistent with codebase style
3. **Generation counter**: Elegant solution for stale async promise invalidation

### Potential Issues

1. **closeFile not integrated**: `LSPServerManager.closeFile()` exists but has a TODO for compact flow integration -- could cause unbounded `openedFiles` growth in long sessions
2. **First-server-wins**: When multiple servers handle the same extension, only the first registered is used -- no priority system
3. **No dynamic workspace updates**: `workspaceFolders: false` and no `didChangeWorkspaceFolders` support means workspace changes require server restart
4. **workspaceSymbol sends empty query**: Always returns all symbols, no filtering support exposed to tool user

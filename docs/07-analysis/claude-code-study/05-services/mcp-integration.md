# MCP Integration

> MCP server management, 10 transport protocols, 6-scope configuration, tool discovery, elicitation, OAuth, and output management.

**Source**: `src/services/mcp/`, `src/tools/MCPTool/`, `src/utils/mcp/` (12 files, ~4,200 LOC)
**Quality**: 9.2/10 — verified against source code line references

---

## 1. Complete Connection Lifecycle

### 1.1 Configuration Aggregation Pipeline

The configuration is assembled in `config.ts` via `getAllMcpConfigs()` with a strict precedence hierarchy:

```
Enterprise (exclusive) → OR → claude.ai (lowest) < plugin < user < project < local (highest)
```

**Key functions in the chain:**

| Function | Role |
|----------|------|
| `getAllMcpConfigs()` | Top-level aggregator; merges claude.ai + CLI configs |
| `getClaudeCodeMcpConfigs()` | Merges plugin/user/project/local scopes |
| `getMcpConfigsByScope(scope)` | Reads from specific config source |
| `parseMcpConfig()` | Zod schema validation + env var expansion |
| `expandEnvVars()` | Replaces `${VAR}` in command/url/args/headers |

**Enterprise mode**: If `managed-mcp.json` exists, it has exclusive control; all other scopes are ignored.

**Plugin-only policy**: When `isRestrictedToPluginOnly('mcp')` is set, user/project/local scopes are suppressed but plugin servers remain.

**Project servers** require explicit user approval (`getProjectMcpServerStatus(name) === 'approved'`) before being included.

**Deduplication**: Three separate dedup functions prevent duplicate connections:
1. `dedupPluginMcpServers()` — plugin vs manual (signature-based: `stdio:${JSON.stringify(cmd)}` or `url:${unwrapCcrProxyUrl(url)}`)
2. `dedupClaudeAiMcpServers()` — claude.ai connectors vs enabled manual servers
3. `unwrapCcrProxyUrl()` — extracts original vendor URL from CCR proxy URLs for cross-format matching

**Policy filtering** (`filterMcpServersByPolicy`): Applied at the end via allowlist/denylist. Supports three match types:
- Name-based: `{ serverName: "..." }`
- Command-based: `{ serverCommand: [...] }` (stdio only)
- URL-based: `{ serverUrl: "https://*.example.com/*" }` (wildcard patterns)

Denylist always takes absolute precedence over allowlist.

### 1.2 Transport Selection

In `connectToServer()` (client.ts, line ~595), the transport type is determined by `serverRef.type`:

| Type | Transport Class | Conditions |
|------|----------------|------------|
| `stdio` (or `undefined`) | `StdioClientTransport` | Default for local processes; command + args spawned as subprocess |
| `sse` | `SSEClientTransport` | Legacy SSE transport; includes `ClaudeAuthProvider` for OAuth |
| `http` | `StreamableHTTPClientTransport` | MCP Streamable HTTP spec; supports session management |
| `ws` | `WebSocketTransport` (custom) | WebSocket with `['mcp']` protocol; Bun or node `ws` |
| `ws-ide` | `WebSocketTransport` | IDE-specific WebSocket; includes `X-Claude-Code-Ide-Authorization` header |
| `sse-ide` | `SSEClientTransport` | IDE-specific SSE; no auth provider |
| `claudeai-proxy` | `StreamableHTTPClientTransport` | Proxied through claude.ai; uses `createClaudeAiProxyFetch()` with OAuth bearer |
| `sdk` | `SdkControlClientTransport` | In-process via control channel (handled in `setupSdkMcpClients()`) |
| In-process (Chrome) | `InProcessTransport` (linked pair) | Detected by `isClaudeInChromeMCPServer(name)`; avoids ~325 MB subprocess |
| In-process (Computer Use) | `InProcessTransport` (linked pair) | Feature-gated by `CHICAGO_MCP`; detected by `isComputerUseMCPServer(name)` |

### 1.3 Connection Flow (per server)

```
1. Config loaded → type resolved
2. Transport instantiated (with auth provider if remote)
3. Client created:
   - name: 'claude-code', version: MACRO.VERSION
   - capabilities: { roots: {}, elicitation: {} }
4. ListRootsRequestSchema handler registered (returns file://cwd)
5. Default ElicitRequestSchema handler registered (returns cancel)
6. client.connect(transport) with timeout race:
   - Default: 30s (MCP_TIMEOUT env override)
   - Promise.race([connectPromise, timeoutPromise])
7. On success:
   - Read capabilities, serverVersion, instructions (truncated to 2048 chars)
   - Register stderr logging (stdio only, capped at 64 MB)
   - Register error/close handlers for reconnection
   - Register cleanup (SIGINT → SIGTERM → SIGKILL escalation for stdio)
   - Emit tengu_mcp_server_connection_succeeded analytics
8. Return ConnectedMCPServer { client, name, type: 'connected', capabilities, ... }
```

### 1.4 Batched Connection Strategy

`getMcpToolsCommandsAndResources()` partitions servers into:
- **Local** (stdio/sdk): concurrency = `MCP_SERVER_CONNECTION_BATCH_SIZE` (default 3)
- **Remote** (sse/http/ws/claudeai-proxy): concurrency = `MCP_REMOTE_SERVER_CONNECTION_BATCH_SIZE` (default 20)

Uses `pMap` for slot-based scheduling (replaced fixed sequential batches in 2026-03).

### 1.5 Tool Discovery

After connection, `fetchToolsForClient()`, `fetchResourcesForClient()`, `fetchCommandsForClient()` run in parallel. Each is memoized with LRU cache (size 20, keyed by server name). On `client.onclose`, all fetch caches are invalidated.

---

## 2. Tool Name Generation and Deduplication

### 2.1 Naming Convention: `mcp__<server>__<tool>`

Implemented in `mcpStringUtils.ts`:

```typescript
function buildMcpToolName(serverName, toolName) {
  return `mcp__${normalizeNameForMCP(serverName)}__${normalizeNameForMCP(toolName)}`
}
```

`normalizeNameForMCP()` (normalization.ts):
- Replaces all non-`[a-zA-Z0-9_-]` chars with `_`
- For claude.ai servers (prefixed `claude.ai `): collapses multiple underscores and strips leading/trailing `_`

**Parsing** (`mcpInfoFromString`): Splits on `__`, first part must be `mcp`, second is server name, remainder (joined by `__`) is tool name. Known limitation: server names containing `__` will misparse.

### 2.2 SDK No-Prefix Mode

When `CLAUDE_AGENT_SDK_MCP_NO_PREFIX` is set and `config.type === 'sdk'`, tools use their original name (no `mcp__` prefix), allowing MCP tools to override built-in tools by name. The `mcpInfo` field still tracks the original server/tool for permission checking.

### 2.3 Built-in Tool Deduplication

- IDE tools are filtered by allowlist: only `mcp__ide__executeCode` and `mcp__ide__getDiagnostics` are included
- Resource tools (`ListMcpResourcesTool`, `ReadMcpResourceTool`) are added once globally (first server with resource capability wins)

---

## 3. MCP Tool Execution Flow

### 3.1 MCPTool.ts — The Shell

`MCPTool` (src/tools/MCPTool/MCPTool.ts) is a template tool built with `buildTool()`:
- `isMcp: true`, `name: 'mcp'` (overridden per-tool in fetchToolsForClient)
- `inputSchema`: `z.object({}).passthrough()` — accepts any JSON
- `maxResultSizeChars`: 100,000
- `checkPermissions()`: returns `{ behavior: 'passthrough' }` with suggestion to add allow rules
- All key methods (`call`, `description`, `prompt`, `userFacingName`) are **overridden** in `fetchToolsForClient()` when building per-tool instances

### 3.2 Execution Chain

```
tool.call(args, context, _, parentMessage, onProgress)
  │
  ├─ Extract toolUseId from parentMessage
  ├─ Emit 'started' progress
  │
  ├─ ensureConnectedClient(client)          // reconnect if cache cleared
  │   └─ connectToServer() (memoized)
  │
  ├─ callMCPToolWithUrlElicitationRetry()   // handles -32042 error
  │   │
  │   ├─ callMCPTool()
  │   │   ├─ client.callTool({ name, arguments, _meta })
  │   │   │   - timeout: MCP_TOOL_TIMEOUT (default ~27.8 hours)
  │   │   │   - signal: from context.abortController
  │   │   │   - onprogress: SDK progress notifications
  │   │   │   - Promise.race([callTool, timeoutPromise])
  │   │   │
  │   │   ├─ Check result.isError → throw McpToolCallError
  │   │   ├─ processMCPResult(result, tool, name)
  │   │   └─ Return { content, _meta, structuredContent }
  │   │
  │   └─ On McpError(-32042): URL elicitation retry loop (max 3)
  │
  ├─ On McpSessionExpiredError: retry once with fresh client
  ├─ Emit 'completed'/'failed' progress
  └─ Return { data: content, mcpMeta? }
```

### 3.3 Tool Annotations Usage

MCP tool annotations from the server are mapped to tool behavior:
- `readOnlyHint` → `isConcurrencySafe()`, `isReadOnly()`
- `destructiveHint` → `isDestructive()`
- `openWorldHint` → `isOpenWorld()`
- `title` → `userFacingName()` fallback display
- `anthropic/searchHint` (from `_meta`) → `searchHint` for deferred tool matching
- `anthropic/alwaysLoad` (from `_meta`) → `alwaysLoad` flag

---

## 4. Output Size Management

### 4.1 Result Processing Pipeline

`processMCPResult()` handles three result shapes:

| Shape | Detection | Processing |
|-------|-----------|------------|
| `toolResult` | `'toolResult' in result` | `String(result.toolResult)` |
| `structuredContent` | `'structuredContent' in result` | `JSON.stringify()` + schema inference |
| `contentArray` | `'content' in result && Array.isArray` | `transformResultContent()` per item |

### 4.2 Content Type Handling in transformResultContent()

| Content Type | Action |
|-------------|--------|
| `text` | Pass through as text block |
| `image` | Resize/downsample via `maybeResizeAndDownsampleImageBuffer()`, return base64 |
| `audio` | Persist to disk via `persistBinaryContent()`, return file path text |
| `resource` (text) | Prefix with `[Resource from server at uri]` |
| `resource` (blob/image) | Resize like image |
| `resource` (blob/other) | Persist to disk like audio |
| `resource_link` | Return text with URI and description |

### 4.3 Large Output Handling

When `mcpContentNeedsTruncation(content)` returns true:

1. **If `ENABLE_MCP_LARGE_OUTPUT_FILES` is falsy**: Truncate inline (legacy behavior)
2. **If content contains images**: Truncate (preserve compression/viewability)
3. **Otherwise**: Persist to disk:
   - File ID: `mcp-${server}-${tool}-${timestamp}`
   - Saved via `persistToolResult(contentStr, persistId)`
   - Return instructions text with file path, size, and format description
   - Format description uses `inferCompactSchema()` for jq-friendly type signatures (e.g., `{title: string, items: [{id: number}]}`)

4. **If persist fails**: Fall back to truncation with error message suggesting pagination

Analytics events: `tengu_mcp_large_result_handled` with outcome `truncated|persisted` and reason.

---

## 5. Elicitation Handler

### 5.1 Architecture (elicitationHandler.ts)

The elicitation system allows MCP servers to request user input mid-execution. Two modes:

| Mode | Trigger | UX |
|------|---------|-----|
| `form` | Server sends `ElicitRequestSchema` with `requestedSchema` | Form-based input dialog |
| `url` | Server sends URL for user to visit + `elicitationId` | Browser open + waiting state |

### 5.2 Registration Flow

`registerElicitationHandler(client, serverName, setAppState)`:
1. Registers `ElicitRequestSchema` handler on the MCP client
2. Registers `ElicitationCompleteNotificationSchema` handler (URL mode completion)
3. Wrapped in try/catch — silently skips if client lacks elicitation capability

### 5.3 Request Processing

```
Server sends ElicitRequest
  │
  ├─ runElicitationHooks(serverName, params, signal)
  │   └─ executeElicitationHooks() — hooks can resolve programmatically
  │       ├─ If hookResponse → return immediately (no UI)
  │       └─ If blockingError → return { action: 'decline' }
  │
  ├─ No hook response → Queue for UI:
  │   └─ setAppState → elicitation.queue.push(event)
  │       - respond: callback to resolve Promise
  │       - waitingState: for URL mode phase-2 UI
  │       - signal: abort → cancel
  │
  ├─ Await user response
  │
  └─ runElicitationResultHooks(serverName, result, signal, mode, elicitationId)
      └─ executeElicitationResultHooks() — can modify/block response
          ├─ If blockingError → return { action: 'decline' }
          └─ Fire 'elicitation_response' notification
```

### 5.4 URL Elicitation via Error (-32042)

`callMCPToolWithUrlElicitationRetry()` handles `McpError` with `ErrorCode.UrlElicitationRequired`:

1. Parse `error.data.elicitations[]` — each must have `mode: 'url'`, `url`, `elicitationId`, `message`
2. For each elicitation:
   - Run hooks first (can resolve programmatically)
   - If `handleElicitation` callback exists (print/SDK mode): delegate to structuredIO
   - Otherwise (REPL mode): queue with two-phase consent/waiting flow
     - Phase 1: User opens URL (accept is no-op)
     - Phase 2: Waiting state with "Retry now" / "Cancel"
   - Run result hooks
3. If all accepted: retry tool call (max 3 retries)

### 5.5 Completion Notification

For URL mode, the server sends `ElicitationCompleteNotification` when the user completes the external action. The handler sets `completed: true` on the matching queue event (matched by `serverName` + `elicitationId`), and the UI dialog reacts to this flag.

---

## 6. OAuth Flow for MCP Servers

### 6.1 ClaudeAuthProvider (auth.ts, line 1376)

Implements `OAuthClientProvider` from `@modelcontextprotocol/sdk/client/auth.js`:

| Method | Behavior |
|--------|----------|
| `clientMetadata` | Returns `{ client_name: "Claude Code (server)", grant_types: ['authorization_code', 'refresh_token'], token_endpoint_auth_method: 'none' }` |
| `clientMetadataUrl` | Returns CIMD URL for URL-based client_id (SEP-991); overridable via `MCP_OAUTH_CLIENT_METADATA_URL` |
| `clientInformation()` | Reads from secure storage (keychain); falls back to `config.oauth.clientId` |
| `saveClientInformation()` | Writes to secure storage keyed by `${serverName}|${sha256(config).slice(0,16)}` |
| `tokens()` | Reads from secure storage; handles XAA auto-auth, proactive refresh (30s before expiry), step-up scope |
| `saveTokens()` | Writes access/refresh/expiry to secure storage with lock file coordination |
| `redirectUrl` | `http://127.0.0.1:{port}/oauth/callback` |
| `state()` | Generates random 32-byte base64url state |
| `markStepUpPending(scope)` | Triggers re-authorization with elevated scope (omits refresh_token to force full flow) |

### 6.2 Discovery

`fetchAuthServerMetadata()`:
1. If `authServerMetadataUrl` configured (must be HTTPS): fetch directly
2. Else: RFC 9728 → `discoverOAuthServerInfo()` (probe `/.well-known/oauth-protected-resource`)
3. Fallback: RFC 8414 path-aware discovery (`/.well-known/oauth-authorization-server/{path}`)

### 6.3 Token Refresh

- **Proactive**: `tokens()` checks `expiresAt - 30s < now` and triggers `refreshAuthorization()`
- **Concurrency**: Uses `lockfile` to coordinate between multiple Claude Code processes
- **Retry**: 3 retries with 1s backoff for `TemporarilyUnavailableError`, `TooManyRequestsError`, `ServerError`
- **Invalid grant**: Clears stored tokens; next call triggers full re-auth
- **Cross-process**: macOS keychain cache with TTL; explicit `clearKeychainCache()` on reconnect

### 6.4 Non-standard Server Handling

- **Slack quirks**: `normalizeOAuthErrorBody()` rewraps HTTP 200 error responses as HTTP 400 for SDK compatibility
- **Non-standard error codes**: `invalid_refresh_token`, `expired_refresh_token`, `token_expired` normalized to `invalid_grant`
- **Token revocation** (`revokeServerTokens`): RFC 7009 compliant with fallback to Bearer auth for non-compliant servers

### 6.5 Step-Up Authentication

When a 403 `insufficient_scope` response is detected:
1. `wrapFetchWithStepUpDetection()` intercepts the response
2. Calls `authProvider.markStepUpPending(scope)` with the required scope
3. `tokens()` omits refresh_token, forcing SDK to run full auth flow with elevated scope
4. Step-up state persisted so re-auth can use cached scope

### 6.6 Auth Caching

`mcp-needs-auth-cache.json` with 15-minute TTL:
- Servers that returned 401 are cached to skip reconnection attempts
- Combined with `hasMcpDiscoveryButNoToken()` — servers with stored discovery state but no tokens are also skipped
- XAA servers exempted (can silently re-auth via cached id_token)

---

## 7. In-Process Transport

### 7.1 InProcessTransport (InProcessTransport.ts)

A lightweight linked transport pair for running MCP servers in the same process:

```typescript
class InProcessTransport implements Transport {
  send(message) → peer.onmessage(message)  // via queueMicrotask
  close() → this.onclose() + peer.onclose()
}

createLinkedTransportPair() → [clientTransport, serverTransport]
```

Used for:
1. **Chrome MCP server**: `isClaudeInChromeMCPServer(name)` — avoids spawning ~325 MB subprocess
2. **Computer Use MCP server**: Feature-gated by `CHICAGO_MCP` — same rationale

Both use the pattern:
```
const [clientTransport, serverTransport] = createLinkedTransportPair()
await inProcessServer.connect(serverTransport)
transport = clientTransport
```

### 7.2 SDK Control Transport

`SdkControlClientTransport` — for SDK-type servers that communicate via control channel messages. Uses `sendMcpMessage(serverName, message)` callback provided by the SDK host.

---

## 8. Error Handling and Reconnection

### 8.1 Connection Error Classification

| Error | Action |
|-------|--------|
| `UnauthorizedError` (SSE/HTTP) | Return `{ type: 'needs-auth' }` + cache in needs-auth file |
| HTTP 401 (claudeai-proxy) | Same as above |
| Connection timeout (30s default) | Close transport, throw TelemetrySafeError |
| Other connection errors | Return `{ type: 'failed', error }` |

### 8.2 Runtime Error Handling

The `client.onerror` handler classifies errors:

| Error Pattern | Diagnosis |
|--------------|-----------|
| `ECONNRESET` | Server crashed or restarted |
| `ETIMEDOUT` | Network issue or unresponsive |
| `ECONNREFUSED` | Server down |
| `EPIPE` | Unexpected close |
| `EHOSTUNREACH` | Network connectivity |
| `ESRCH` | Stdio process terminated |
| `spawn` | Command/permission error |
| `Maximum reconnection attempts` | SDK SSE reconnect exhausted → close transport |

### 8.3 Reconnection Strategy

1. **Consecutive terminal errors**: After 3 consecutive terminal errors (`ECONNRESET`, `ETIMEDOUT`, etc.), transport is closed via `closeTransportAndRejectPending()`
2. **Session expiry**: HTTP 404 + JSON-RPC `-32001` → close transport, clear cache, throw `McpSessionExpiredError`
3. **On close** (`client.onclose`): Clears memoization cache (connectToServer + all fetch caches) so next operation triggers fresh connection
4. **Tool call retry**: On `McpSessionExpiredError`, `tool.call()` retries once with a fresh client via `ensureConnectedClient()`
5. **401 during tool call**: Throws `McpAuthError` → updates server status to 'needs-auth'

### 8.4 Cleanup Escalation (stdio)

```
SIGINT → wait 100ms → SIGTERM → wait 400ms → SIGKILL
Total cleanup budget: 600ms failsafe timeout
Process existence checked via process.kill(pid, 0)
```

### 8.5 Fetch Timeout Architecture

`wrapFetchWithTimeout()` wraps all fetch calls:
- **POST requests**: 60s timeout via `setTimeout` + `AbortController` (not `AbortSignal.timeout()` to avoid Bun memory leak)
- **GET requests**: No timeout (long-lived SSE streams)
- **Accept header**: Forces `application/json, text/event-stream` on all POSTs per MCP Streamable HTTP spec

---

## 9. React Context (MCPConnectionManager.tsx)

Provides two hooks via `MCPConnectionContext`:
- `useMcpReconnect()` → `reconnectMcpServer(serverName)`
- `useMcpToggleEnabled()` → `toggleMcpServer(serverName)`

Delegates to `useManageMCPConnections(dynamicMcpConfig, isStrictMcpConfig)` which manages the connection lifecycle. Uses React Compiler runtime (`_c` memoization).

---

## 10. Key Source Files

| File | Purpose |
|------|---------|
| `src/services/mcp/client.ts` | MCP client, transport creation, tool wrapping |
| `src/services/mcp/types.ts` | Config schemas, transport types |
| `src/services/mcp/config.ts` | Config loading, scope merging, deduplication |
| `src/services/mcp/MCPConnectionManager.tsx` | React connection manager |
| `src/services/mcp/auth.ts` | OAuth for MCP servers (ClaudeAuthProvider) |
| `src/services/mcp/elicitationHandler.ts` | Elicitation protocol (form + URL modes) |
| `src/services/mcp/normalization.ts` | Tool name normalization |
| `src/services/mcp/InProcessTransport.ts` | In-process linked transport pair |
| `src/services/mcp/SdkControlTransport.ts` | SDK control channel transport |
| `src/tools/MCPTool/MCPTool.ts` | MCP tool wrapper |
| `src/tools/McpAuthTool/McpAuthTool.ts` | OAuth trigger tool |
| `src/utils/mcp/` | MCP utilities (mcpStringUtils, etc.) |

---

## Verification Summary

| Finding | Confidence |
|---------|------------|
| 10 transport types (stdio, sse, http, ws, ws-ide, sse-ide, claudeai-proxy, sdk, in-process-chrome, in-process-computeruse) | HIGH |
| Tool naming: `mcp__${normalize(server)}__${normalize(tool)}` | HIGH |
| 6-scope config precedence: enterprise > local > project > user > plugin > claude.ai | HIGH |
| OAuth via ClaudeAuthProvider with RFC 9728/8414 discovery + PKCE + CIMD | HIGH |
| Large output: truncate or persist-to-disk with jq-friendly schema hint | HIGH |
| Elicitation: form mode + URL mode with -32042 error retry | HIGH |
| Reconnection: 3 consecutive terminal errors → close; session expiry → 1 retry | HIGH |
| Connection batching: local=3, remote=20 concurrency via pMap | HIGH |

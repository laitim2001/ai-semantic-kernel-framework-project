# Bridge / Remote Control Protocol

> Consolidated from deep analysis. Authoritative reference covering standalone bridge, REPL bridge, v1/v2 transports, JWT refresh, reconnection, deduplication, and all backoff constants.
> Source: `src/bridge/` (31 files), `src/cli/transports/`

## Overview

The "bridge" (branded "Remote Control") allows claude.ai web/mobile clients to send prompts to a local Claude Code instance. The local machine registers as an "environment" with the Anthropic backend, polls for work items, and spawns child processes per session. It has two independent execution modes:

| Mode | Entry Point | File | Use Case |
|------|-------------|------|----------|
| **Standalone Bridge** | `claude remote-control` | `bridgeMain.ts` | Persistent server, multi-session, spawns child `claude` processes |
| **REPL Bridge** | `/remote-control` slash command | `replBridge.ts` | In-process, single-session, connects existing REPL to cloud |

Both share the same underlying protocol: register environment -> create session -> poll for work -> connect transport -> forward messages bidirectionally.

```
claude.ai/code (Web UI)
       |
       v
  Anthropic Backend (CCR / Session-Ingress)
       |
       v  [Work Poll / JWT delivery]
  Bridge Environment (registered)
       |
       v  [Transport: WS/SSE + HTTP POST]
  Local Claude Code Process(es)
```

## Protocol Types (`src/bridge/types.ts`)

### WorkResponse / WorkSecret

```typescript
type WorkResponse = {
  id: string, type: 'work', environment_id: string,
  state: string, data: WorkData, secret: string, // base64url JSON
  created_at: string
}
```

### WorkSecret Structure

```typescript
type WorkSecret = {
  version: 1                                    // must be exactly 1
  session_ingress_token: string                 // JWT for session auth
  api_base_url: string                          // backend base URL
  sources: Array<{
    type: string
    git_info?: { type: string; repo: string; ref?: string; token?: string }
  }>
  auth: Array<{ type: string; token: string }>
  claude_code_args?: Record<string, string> | null
  mcp_config?: unknown | null
  environment_variables?: Record<string, string> | null
  use_code_sessions?: boolean                   // server-driven v2 selector
}
```

### Decoding Flow (`decodeWorkSecret`)

1. `Buffer.from(secret, 'base64url').toString('utf-8')` -> JSON string
2. `jsonParse(json)` -> validate `version === 1`
3. Validate `session_ingress_token` is non-empty string
4. Validate `api_base_url` is string
5. Cast to `WorkSecret` and return

### SpawnMode

| Mode | Behavior | Lifecycle | Working Directory |
|------|----------|-----------|-------------------|
| `single-session` | One session, bridge exits when it ends | Coupled to session | `config.dir` (cwd) |
| `worktree` | Persistent server, each new session gets isolated git worktree | Independent | Unique worktree per session; initial session stays in `config.dir` |
| `same-dir` | Persistent server, all sessions share directory | Independent | `config.dir` for all |

### BridgeWorkerType
`'claude_code'` | `'claude_code_assistant'` -- sent at registration so claude.ai can filter session picker.

---

## Core Files

| File | Role |
|------|------|
| `bridgeMain.ts` | Server-mode bridge (multi-session, worktree support) |
| `replBridge.ts` | REPL-mode bridge (single active session, inline) |
| `bridgeApi.ts` | `BridgeApiClient` -- HTTP calls to Environments API |
| `bridgeMessaging.ts` | Message routing, deduplication, control handling |
| `replBridgeTransport.ts` | Transport interface + v1/v2 factories |
| `workSecret.ts` | Work secret decoding, URL construction, worker registration |
| `sessionRunner.ts` | Child process spawner (`SessionSpawner`) |
| `bridgePermissionCallbacks.ts` | Permission dialog -> bridge events |
| `jwtUtils.ts` | JWT token refresh scheduler |
| `trustedDevice.ts` | Trusted device token management |
| `pollConfig.ts` | Dynamic poll interval from server |
| `capacityWake.ts` | Capacity wake signal |
| `flushGate.ts` | Ordered message flush gate |

---

## Bridge Main Loop (`src/bridge/bridgeMain.ts`)

### Initialization

1. **Parse CLI args** (`parseArgs`): `--verbose`, `--sandbox`, `--spawn <mode>`, `--capacity <N>`, `--session-id`, `--continue`, `--permission-mode`, `--name`, `--debug-file`, `--session-timeout`
2. **Enable configs**: bypass `init.ts`, call `enableConfigs()` directly
3. **Init analytics sinks**: `initSinks()` (bridge bypasses standard setup flow)
4. **Auth check**: verify OAuth token via `getAccessToken()`; abort with `BRIDGE_LOGIN_ERROR` if missing
5. **Create API client**: `createBridgeApiClient({ baseUrl, getAccessToken, onAuth401, getTrustedDeviceToken })`
6. **Register environment**: `api.registerBridgeEnvironment(config)` -> `{ environment_id, environment_secret }`
7. **Create logger**: `createBridgeLogger()` for terminal UI (status lines, QR code, session list)
8. **Create session spawner**: `createSessionSpawner()` for child process management
9. **Optionally pre-create session**: via `createBridgeSession()` if `createSessionInDir` is true
10. **Enter poll loop**: `runBridgeLoop(config, envId, envSecret, api, spawner, logger, signal)`

### Poll Loop (`runBridgeLoop`)

```
while (!loopSignal.aborted) {
  1. Fetch poll config (GrowthBook, refreshes every 5 min)
  2. api.pollForWork(environmentId, environmentSecret, signal, reclaim_older_than_ms)
  3. On success: reset backoff counters, log reconnection if was disconnected
  4. On null (no work):
     a. If at capacity -> heartbeat loop OR slow-poll sleep
     b. If not at capacity -> fast-poll sleep
     c. continue
  5. Skip already-completed work IDs (dedup)
  6. Decode work secret (base64url JSON)
  7. Switch on work.data.type:
     - 'healthcheck': ack + continue
     - 'session':
       a. Validate session_id
       b. Check existing session -> update token if found
       c. Check capacity -> break if full
       d. Ack work
       e. Determine v1/v2 transport
       f. Register worker (v2 only, retry once)
       g. Create worktree (worktree mode only)
       h. Spawn child process
       i. Register session metadata
       j. Start status updates + timeout watchdog
       k. Schedule JWT refresh
       l. Wire handle.done -> onSessionDone
  8. At-capacity throttle (heartbeat + sleep)
  9. Error handling: BridgeFatalError -> break; connection/server -> backoff
}
```

### Session Done Handler

When a child process exits (`onSessionDone`):
1. Clean up all maps: `activeSessions`, `sessionStartTimes`, `sessionWorkIds`, `sessionIngressTokens`, `sessionCompatIds`
2. Remove from logger display
3. Cancel token refresh timer
4. Wake capacity signal (so poll loop can accept new work)
5. Classify exit: `completed` / `failed` / `interrupted` (timeout-killed -> `failed`)
6. Notify server: `stopWorkWithRetry` (3 attempts, 1s/2s/4s backoff)
7. Clean up worktree if applicable
8. **Lifecycle decision**:
   - `single-session` mode: abort poll loop, bridge exits
   - `worktree` / `same-dir` mode: archive session, return to idle

### Graceful Shutdown

1. Stop status updates, clear display
2. Log shutdown analytics
3. Collect all session IDs to archive (active + initial)
4. SIGTERM all active sessions
5. Wait up to `shutdownGraceMs` (default 30s) for graceful exit
6. SIGKILL any stuck sessions
7. Clean up worktrees
8. Stop all work items (`api.stopWork(envId, workId, force=true)`)
9. Wait for pending in-flight cleanup promises
10. Archive all sessions (`api.archiveSession`)
11. Deregister environment (`api.deregisterEnvironment`)
12. Clear crash-recovery pointer

**Exception**: if `feature('KAIROS')` + single-session + `initialSessionId` + not fatal exit, skip archive/deregister to allow `--continue` resume.

---

## REPL Bridge (`replBridge.ts`)

### `initBridgeCore(params: BridgeCoreParams)` Steps

1. **Read crash-recovery pointer** (perpetual mode only): `readBridgePointer(dir)` -> reuse if `source === 'repl'`
2. **Create API client**: `createBridgeApiClient` with optional fault injection (ant-only)
3. **Register environment**: `api.registerBridgeEnvironment(bridgeConfig)` with optional `reuseEnvironmentId` from prior pointer
4. **Try reconnect in place** (perpetual + prior exists): `tryReconnectInPlace()` -> calls `api.reconnectSession()`
5. **Create session** (if no prior reused): `createSession({ environmentId, title, gitRepoUrl, branch })`
6. **Write crash-recovery pointer**: `writeBridgePointer(dir, { sessionId, environmentId, source: 'repl' })`
7. **Initialize dedup structures**:
   - `recentPostedUUIDs`: `BoundedUUIDSet(2000)` for echo filtering
   - `recentInboundUUIDs`: `BoundedUUIDSet(2000)` for re-delivery dedup
   - `initialMessageUUIDs`: Set of initial message UUIDs
8. **Start work poll loop**: `startWorkPollLoop(pollOpts)` (background)
9. **Start keep-alive timer**: sends `{ type: 'keep_alive' }` at configured interval (default 120s)
10. **Start pointer refresh timer** (perpetual mode): hourly mtime bump
11. **Register cleanup**: `registerCleanup(() => doTeardownImpl?.())`
12. **Return handle**: `BridgeCoreHandle` with write/teardown methods

### `onWorkReceived` (transport creation)

When poll delivers work:
1. Validate session ID match: `sameSessionId(workSessionId, currentSessionId)`
2. Store `currentWorkId` and `currentIngressToken`
3. Determine v1/v2: `secret.use_code_sessions` or `CLAUDE_BRIDGE_USE_CCR_V2` env var
4. **v1 path**: get OAuth token -> `updateSessionIngressAuthToken(oauth)` -> create `HybridTransport`
5. **v2 path**: `createV2ReplTransport({ sessionUrl, ingressToken, sessionId, initialSequenceNum })` (async)
6. Close old transport (capture SSE seq before close)
7. `wireTransport(newTransport)`:
   - `setOnConnect`: flush initial messages, drain flush gate, emit `onStateChange('connected')`
   - `setOnData`: `handleIngressMessage()` for routing
   - `setOnClose`: `handleTransportPermanentClose()`
   - Start flush gate if initial messages pending
   - `newTransport.connect()`

### Reconnection (`doReconnect`)

Triggered by: poll 404 (env deleted) or transport permanent close (budget exhausted).

**Strategy 1 - Reconnect in place**:
1. Close stale transport, capture SSE seq
2. Release current work item (`api.stopWork`, `force=false`)
3. Re-register environment with `reuseEnvironmentId`
4. If same env ID returned -> `api.reconnectSession()` -> same session, same URL

**Strategy 2 - Fresh session fallback**:
1. Archive old session
2. Create new session on the now-registered environment
3. Reset SSE seq to 0, clear inbound UUID dedup
4. Rewrite crash-recovery pointer

**Guards**: max 3 environment recreations; resets on successful poll. Reentrancy guard via `reconnectPromise`.

### Teardown

**Non-perpetual**:
1. Abort poll loop
2. Capture final SSE seq from live transport
3. Send `result` message (session archival trigger)
4. Stop work + archive session (parallel)
5. Close transport
6. Deregister environment
7. Clear crash-recovery pointer

**Perpetual**:
1. Abort poll loop
2. NULL transport (do NOT close -- let socket die with process)
3. Do NOT send result, stop work, or archive
4. Refresh pointer mtime (survive 4h TTL)
5. Server times out work-item lease (300s TTL), next daemon start reconnects

---

## v1 vs v2 Transport Comparison

| Aspect | v1 (HybridTransport) | v2 (SSE + CCRClient) |
|--------|---------------------|-------------------------------|
| **Read channel** | WebSocket (`wss://...session_ingress/ws/{id}`) | SSE (`https://...worker/events/stream`) |
| **Write channel** | HTTP POST to `/session/{id}/events` | HTTP POST via CCRClient `/worker/events` |
| **Auth (reads)** | OAuth token in WS headers | JWT in SSE request headers |
| **Auth (writes)** | OAuth via `getSessionIngressAuthToken()` | JWT via `getSessionIngressAuthHeaders()` |
| **Token refresh** | Direct OAuth token swap on child | Server re-dispatch (reconnectSession) |
| **Sequence tracking** | None (returns 0) | SSE `id:` field -> `lastSequenceNum` |
| **Resume on reconnect** | Server-side message cursor | `from_sequence_num` / `Last-Event-ID` |
| **Dedup** | UUID-based (BoundedUUIDSet) | Sequence number + `seenSequenceNums` Set |
| **Worker registration** | Not required | `POST /worker/register` -> `worker_epoch` |
| **Heartbeat** | Via poll loop | CCRClient built-in heartbeat (20s default) |
| **Write batching** | `SerialBatchEventUploader` (500 max batch, 100ms stream buffer) | CCRClient -> `SerialBatchEventUploader` (100 max batch) |
| **State reporting** | No-op | `PUT /worker` state + metadata |
| **Delivery tracking** | No-op | `POST /worker/events/{id}/delivery` (received + processed) |
| **Epoch mismatch** | N/A | Close transport, fire `onClose(4090)` |
| **Selection** | Default; `secret.use_code_sessions !== true` | `secret.use_code_sessions === true` OR `CLAUDE_BRIDGE_USE_CCR_V2=true` |

### v1 HybridTransport Write Flow

```
write(stream_event) -> buffer (100ms timer)
write(other)        -> flush buffer + enqueue
                          |
                          v
                    SerialBatchEventUploader
                          |  serial, batched
                          |  retry with exp backoff
                          v
                    postOnce() -> HTTP POST
```

### v2 SSETransport Read Flow

```
HTTP GET (fetch API) with Accept: text/event-stream
       |
       v
  readStream() -> TextDecoder -> parseSSEFrames()
       |
       v
  For each frame:
    - Reset liveness timer
    - Track sequence number (dedup via seenSequenceNums)
    - Route client_event frames -> extract payload -> onData(JSON)
```

### v2 SSETransport Write Flow (POST retry)

```
write(message) -> for loop (1..POST_MAX_RETRIES)
                    |
                    v
              axios.post(postUrl, message)
                    |
                    +-- 200/201 -> return (success)
                    +-- 4xx (not 429) -> return (permanent, drop)
                    +-- 429/5xx -> sleep(exp backoff) -> retry
                    +-- network error -> sleep(exp backoff) -> retry
```

---

## URL Construction

**v1**: `buildSdkUrl(apiBaseUrl, sessionId)`
- localhost -> `ws://host/v2/session_ingress/ws/{sessionId}`
- production -> `wss://host/v1/session_ingress/ws/{sessionId}` (Envoy rewrites v1 -> v2)

**v2**: `buildCCRv2SdkUrl(apiBaseUrl, sessionId)`
- `{base}/v1/code/sessions/{sessionId}` (HTTP, not WS)

### Session ID Compatibility

`sameSessionId(a, b)`: compares by underlying UUID body (after last `_`), not by tagged-ID prefix. Handles `session_*` (compat API surface) vs `cse_*` (infrastructure layer) divergence under `ccr_v2_compat_enabled`.

### Worker Registration (`registerWorker`)

`POST {sessionUrl}/worker/register` with JWT Bearer auth.
- Returns `worker_epoch` (int64, may be JSON string or number)
- Validates epoch is finite safe integer
- Retry: once on transient failure (2s delay)
- Timeout: 10,000ms

---

## Session Spawning Modes

### Multi-Session Feature Gate

`isMultiSessionSpawnEnabled()`: checks GrowthBook gate `tengu_ccr_bridge_multi_session` (blocking check, staged rollout).

### Worktree Creation

```
createAgentWorktree(`bridge-${safeFilenameId(sessionId)}`)
  -> { worktreePath, worktreeBranch, gitRoot, hookBased }
```

Cleanup: `removeAgentWorktree()` on session done or shutdown.

### Capacity Management

- `maxSessions`: configurable via `--capacity` (default: 32 for multi-session, 1 for single)
- `capacityWake`: signal that wakes at-capacity sleep when a session completes
- `activeSessions.size >= config.maxSessions` -> heartbeat-only or slow-poll

---

## Permission Forwarding Mechanism

### Types (`bridgePermissionCallbacks.ts`)

```typescript
type BridgePermissionResponse = {
  behavior: 'allow' | 'deny'
  updatedInput?: Record<string, unknown>
  updatedPermissions?: PermissionUpdate[]
  message?: string
}

type BridgePermissionCallbacks = {
  sendRequest(requestId, toolName, input, toolUseId, description, permissionSuggestions?, blockedPath?): void
  sendResponse(requestId, response: BridgePermissionResponse): void
  cancelRequest(requestId): void
  onResponse(requestId, handler): () => void  // returns unsubscribe
}
```

### Flow: Local Terminal <-> Remote Agent

**Outbound (local -> cloud)**:
1. Local REPL encounters tool permission request
2. `sendRequest()` sends `control_request` with tool details via transport
3. Cloud UI shows permission dialog to user

**Inbound (cloud -> local)**:
1. User approves/denies in cloud UI
2. Server sends `control_response` via transport
3. `handleIngressMessage()` routes to `onPermissionResponse` callback
4. `isBridgePermissionResponse()` validates `behavior: 'allow' | 'deny'`
5. Permission decision applied locally

### Server Control Requests (`handleServerControlRequest`)

The server sends `control_request` messages for lifecycle events. The bridge MUST respond within **10-14 seconds** or the server kills the WS.

| Subtype | Action | Response |
|---------|--------|----------|
| `initialize` | Return minimal capabilities | `{ commands: [], output_style: 'normal', models: [], account: {}, pid }` |
| `set_model` | Call `onSetModel(model)` | success |
| `set_max_thinking_tokens` | Call `onSetMaxThinkingTokens(tokens)` | success |
| `set_permission_mode` | Call `onSetPermissionMode(mode)` -> policy verdict | success or error |
| `interrupt` | Call `onInterrupt()` | success |
| Unknown | N/A | error response |

**Outbound-only mode**: all mutable requests (except `initialize`) return error with `OUTBOUND_ONLY_ERROR` message. Initialize must still succeed or server kills connection.

---

## JWT Token Refresh Scheduling (`jwtUtils.ts`)

### Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `TOKEN_REFRESH_BUFFER_MS` | 5 minutes (300,000ms) | Request new token before expiry |
| `FALLBACK_REFRESH_INTERVAL_MS` | 30 minutes (1,800,000ms) | Follow-up refresh when no new JWT expiry available |
| `MAX_REFRESH_FAILURES` | 3 | Consecutive failures before stopping chain |
| `REFRESH_RETRY_DELAY_MS` | 60 seconds (60,000ms) | Retry delay when OAuth token unavailable |

### `createTokenRefreshScheduler` Behavior

1. **Schedule**: decode JWT's `exp` claim -> set timer for `(exp - now - buffer)` ms
2. **On fire**: call `getAccessToken()` -> if successful, call `onRefresh(sessionId, oauthToken)`
3. **Follow-up**: schedule another refresh at `FALLBACK_REFRESH_INTERVAL_MS` (30min) for long-running sessions
4. **Failure**: retry up to 3 times at 60s intervals; give up after `MAX_REFRESH_FAILURES`
5. **Generation counter**: prevents stale async callbacks from setting orphaned timers after cancel/reschedule

### v1 vs v2 Refresh Path

- **v1**: `onRefresh` delivers OAuth token directly to child via `handle.updateAccessToken(oauthToken)`
- **v2**: `onRefresh` calls `api.reconnectSession(environmentId, sessionId)` to trigger server re-dispatch with fresh JWT (v2 endpoints require JWT, not OAuth)

---

## Message Deduplication

### Echo Filtering (outbound dedup)

`recentPostedUUIDs: BoundedUUIDSet(2000)`
- Every message sent via transport has its UUID added
- Ingress messages matching these UUIDs are ignored (echo of own message)

### Re-delivery Dedup (inbound dedup)

`recentInboundUUIDs: BoundedUUIDSet(2000)`
- Every forwarded inbound `user` message has its UUID added
- Catches re-deliveries when SSE seq-num negotiation fails

### `BoundedUUIDSet` Implementation

FIFO-bounded set backed by a **circular ring buffer**:
- `capacity`: fixed at construction (2000 in practice)
- `ring: (string | undefined)[]`: pre-allocated array
- `set: Set<string>`: O(1) lookup
- `writeIdx`: circular pointer
- **Eviction**: oldest entry removed when capacity reached
- **Memory**: constant O(capacity)

### SSE Sequence Number Dedup (v2 only)

`seenSequenceNums: Set<number>` with pruning:
- Tracks all seen sequence numbers
- Logs duplicate frames (same seq received twice)
- Prunes entries < `lastSequenceNum - 200` when set exceeds 1000 entries
- `lastSequenceNum`: monotonic high-water mark carried across transport swaps

### Message Eligibility

`isEligibleBridgeMessage(m: Message)`:
- Accept: `user`, `assistant`, `system` (subtype `local_command`)
- Reject: virtual messages (`isVirtual`), tool results, progress events

---

## Backoff Configuration (Exact Constants)

### Standalone Bridge (`bridgeMain.ts`)

```typescript
const DEFAULT_BACKOFF: BackoffConfig = {
  connInitialMs:     2_000,      // 2 seconds
  connCapMs:         120_000,    // 2 minutes (max single delay)
  connGiveUpMs:      600_000,    // 10 minutes (total budget)
  generalInitialMs:  500,        // 500ms
  generalCapMs:      30_000,     // 30 seconds
  generalGiveUpMs:   600_000,    // 10 minutes
  // shutdownGraceMs: 30_000     (default, SIGTERM->SIGKILL)
  // stopWorkBaseDelayMs: 1_000  (default, 1s/2s/4s)
}
```

**Jitter**: +/- 25% (`ms + ms * 0.25 * (2 * random() - 1)`)

**Sleep detection threshold**: `connCapMs * 2` = 4 minutes

**stopWorkWithRetry**: 3 attempts, `baseDelay * 2^(attempt-1)` with jitter (1s/2s/4s)

### REPL Bridge (`replBridge.ts`)

```typescript
const POLL_ERROR_INITIAL_DELAY_MS = 2_000     // 2 seconds
const POLL_ERROR_MAX_DELAY_MS     = 60_000    // 1 minute
const POLL_ERROR_GIVE_UP_MS       = 15 * 60 * 1000  // 15 minutes
```

**Sleep detection**: gap > `POLL_ERROR_MAX_DELAY_MS * 2` = 2 minutes

**Environment recreations**: max 3 (resets on successful poll, not on successful recreation)

### SSE Transport Reconnection

```typescript
const RECONNECT_BASE_DELAY_MS = 1_000         // 1 second
const RECONNECT_MAX_DELAY_MS  = 30_000        // 30 seconds
const RECONNECT_GIVE_UP_MS   = 600_000        // 10 minutes
const LIVENESS_TIMEOUT_MS    = 45_000          // 45 seconds (3x server keepalive)
```

**Jitter**: +/- 25% (`baseDelay + baseDelay * 0.25 * (2 * random() - 1)`)

**Permanent HTTP codes** (no retry): `401`, `403`, `404`

### HybridTransport POST Backoff (via SerialBatchEventUploader)

```typescript
baseDelayMs:  500
maxDelayMs:   8_000
jitterMs:     1_000
maxBatchSize: 500
maxQueueSize: 100_000
```

**Write constants**:
- `BATCH_FLUSH_INTERVAL_MS = 100`
- `POST_TIMEOUT_MS = 15,000`
- `CLOSE_GRACE_MS = 3,000`
- `maxConsecutiveFailures = 50` (bridge-only; ~20min)

### SSE Transport POST Retry

```typescript
POST_MAX_RETRIES  = 10
POST_BASE_DELAY_MS = 500
POST_MAX_DELAY_MS  = 8_000
```

Formula: `min(500 * 2^(attempt-1), 8000)` ms between retries.

---

## Protocol Constants Summary

| Constant | Value | Purpose |
|----------|-------|---------|
| `DEFAULT_SESSION_TIMEOUT_MS` | 24 hours (86,400,000ms) | Per-session timeout |
| `BRIDGE_LOGIN_INSTRUCTION` | "Remote Control is only available..." | Auth error guidance |
| `STATUS_UPDATE_INTERVAL_MS` | 1,000ms | Live display refresh rate |
| `SPAWN_SESSIONS_DEFAULT` | 32 | Default max sessions (multi-session) |

---

## Reconnection and Resume Logic

### Transport-Level Reconnection

**v1 (HybridTransport/WebSocketTransport)**:
- `autoReconnect: true` (default)
- Internal exponential backoff with 10-minute budget
- POST writes continue during WS reconnection (independent of WS state)
- Only fires `onClose` on: clean close (1000), permanent rejection (4001/1002/4003), or budget exhaustion

**v2 (SSETransport)**:
- Reconnects automatically with exponential backoff
- Uses `from_sequence_num` query param + `Last-Event-ID` header for resumption
- Liveness timer: **45 seconds** of silence -> treat as dead -> reconnect
- Server sends keepalives every **15 seconds**

### Bridge-Level Reconnection

**REPL Bridge** (`reconnectEnvironmentWithSession`):
- Max 3 environment recreations (resets on successful poll)
- Reentrancy guard via promise
- Two strategies (reconnect in place vs fresh session)

**Standalone Bridge** (poll loop error handling):
- Two independent backoff tracks: connection errors and general errors
- Sleep detection: gap > `connCapMs * 2` -> reset error budget
- Each track: give up after `connGiveUpMs` (10 minutes default)

### Session Resume (`--continue` / `--session-id`)

1. Read `bridge-pointer.json` from cwd (or worktree siblings)
2. Re-register environment with `reuseEnvironmentId`
3. Call `api.reconnectSession(environmentId, sessionId)` to re-queue work
4. Poll loop picks up re-dispatched work with fresh JWT

---

## Keep-Alive and Heartbeat Mechanisms

### Session Keep-Alive (REPL Bridge)

- Interval from GrowthBook: `session_keepalive_interval_v2_ms` (default 120s)
- Sends `{ type: 'keep_alive' }` via transport
- Prevents upstream proxies and session-ingress from GC-ing idle sessions
- Filtered before reaching client UI (`Query.ts` drops it)

### Work Item Heartbeat (Both Bridges)

- Interval from GrowthBook: `non_exclusive_heartbeat_interval_ms`
- Uses `api.heartbeatWork(environmentId, workId, sessionToken)`
- Auth: session ingress JWT (lightweight, no DB hit)
- Extends work-item lease (300s TTL on server)
- Failure handling:
  - 401/403 (JWT expired) -> `reconnectSession` to re-queue
  - 404/410 (work gone) -> fatal, tear down transport

### CCR v2 Client Heartbeat

- Default interval: 20s (configurable via `heartbeatIntervalMs`)
- Optional jitter via `heartbeatJitterFraction`
- Built into `CCRClient`, runs independently of poll-loop heartbeat

### Crash-Recovery Pointer Refresh

- Perpetual mode: hourly `setInterval` refreshes `bridge-pointer.json` mtime
- Non-perpetual: refreshed on each `onWorkReceived` (per user message)
- Prevents 4h staleness check from invalidating long-running sessions

---

## Process Suspension Detection

Both bridges detect system sleep/wake (laptop lid close, VM pause):

### Standalone Bridge
- **Poll loop**: if gap between consecutive poll errors > `connCapMs * 2` (4 min), reset error budget
- Prevents immediate give-up after wake

### REPL Bridge
- **Poll loop**: if gap > `POLL_ERROR_MAX_DELAY_MS * 2` (2 min), reset error budget
- **At-capacity sleep overrun**: if `sleep(atCapMs)` overruns by > 60s, set `suspensionDetected = true`
  - Next iteration skips at-capacity branch for one fast-poll cycle
  - Gives re-dispatched work item a chance to land

### WebSocket/SSE
- WebSocketTransport: ping interval (10s granularity) is primary short-suspension detector
- SSE liveness timer (45s) catches connection death after suspension

---

## Security

- `validateBridgeId()` -- UUID format validation
- `getTrustedDeviceToken()` -- device trust
- `isInProtectedNamespace()` -- prevents bridge in sensitive directories
- Work secrets are short-lived JWTs, not persisted
- Permission decisions sent as `control_response` events via Session API

---

## Key Design Decisions

1. **Hybrid write path**: WS for reads, HTTP POST for writes avoids concurrent Firestore write collisions. SerialBatchEventUploader ensures at most one POST in-flight.

2. **Two-track backoff in standalone bridge**: connection errors and general errors have independent budgets. Switching error types resets the other track.

3. **Session ID compatibility layer**: `sameSessionId()` compares UUID bodies, not prefixes, to handle `session_*` vs `cse_*` divergence during CCR v2 migration.

4. **Perpetual teardown is local-only**: daemon mode does not send result/stopWork/close to server. Server's 300s lease TTL expires naturally; next start reconnects via pointer.

5. **Flush gate for message ordering**: prevents new messages from arriving at the server interleaved with historical messages during initial flush.

6. **Generation counters**: both JWT refresh scheduler and v2 transport handshake use generation counters to detect stale async callbacks after cancel/reschedule/reconnect.

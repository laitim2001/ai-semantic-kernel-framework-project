# Wave 43: Deep Analysis — `services/analytics/` (9 files)

> Telemetry pipeline, PII safety enforcement, sink routing, sampling, feature flags, Datadog dispatch, 1P logger, kill switches.
>
> **Date**: 2026-04-01 | **Verifier**: Claude Opus 4.6 | **Source snapshot**: CC-Source as-read

---

## 1. File Inventory

| # | File | LOC (approx) | Role |
|---|------|-------------|------|
| 1 | `index.ts` | 174 | Public API — `logEvent`, `logEventAsync`, queue-then-drain, PII branded types |
| 2 | `config.ts` | 39 | Global analytics-disabled predicate |
| 3 | `sink.ts` | 115 | Sink implementation — routes to Datadog + 1P, sampling gate |
| 4 | `sinkKillswitch.ts` | 26 | Per-sink remote killswitch via GrowthBook JSON config |
| 5 | `datadog.ts` | 308 | Datadog Logs API v2 integration — batched HTTP POST |
| 6 | `metadata.ts` | 974 | Event metadata enrichment, PII sanitization helpers, `to1PEventFormat` |
| 7 | `growthbook.ts` | 1156 | GrowthBook SDK wrapper — feature flags, remote eval, disk cache, periodic refresh |
| 8 | `firstPartyEventLogger.ts` | 450 | 1P event logger — OTel LoggerProvider, sampling, GrowthBook experiment logging |
| 9 | `firstPartyEventLoggingExporter.ts` | 807 | Custom OTel `LogRecordExporter` — retry, backoff, disk persistence, auth |

**Total**: ~4,049 LOC across 9 files.

---

## 2. Existing Analysis Discrepancies

The prior `analytics.md` contains several inaccuracies vs source:

| # | Claim in analytics.md | Actual Source Truth | Severity |
|---|----------------------|---------------------|----------|
| 1 | `logEvent` accepts `AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS` as parameter type | Actual parameter type is `{ [key: string]: boolean \| number \| undefined }` — no strings at all. The branded type is `never` and used only for cast-assertions in metadata.ts call sites. | HIGH |
| 2 | Branded type described as `{ [key: string]: unknown }` | Actually `type ... = never` — a phantom/branded type that can never hold a value; serves as a cast-target for code review signals | HIGH |
| 3 | "BigQuery" listed as a third sink alongside Datadog and 1P | No BigQuery sink exists. 1P events reach BQ indirectly via the `/api/event_logging/batch` server-side pipeline. The exporter targets `api.anthropic.com`, not BQ directly. | MEDIUM |
| 4 | Claims "Compression" in the exporter | No compression in the exporter. Events are sent as plain JSON via axios POST. | MEDIUM |
| 5 | Mentions `TelemetrySafeError_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS` | This type does not appear in any analytics file. May exist elsewhere but is not part of this module. | LOW |
| 6 | Mentions `AnalyticsMetadata_I_VERIFIED_THIS_IS_PII_TAGGED` only as non-existent | Actually exported from index.ts (line 33) — used for `_PROTO_*` keys routed to privileged BQ columns | MEDIUM |
| 7 | Event categories listed (tool_*, session_*, error_*, auth_*) | No evidence of these prefixes. All Datadog-allowed events use `tengu_*` or `chrome_bridge_*` prefix. | MEDIUM |
| 8 | Metric types: Counter, Histogram, Gauge | Datadog integration sends structured logs, not DD metrics. No histogram/gauge/counter API. | MEDIUM |
| 9 | "Statsig" referenced as current integration | Statsig is deprecated/migrated. GrowthBook is the active system. `checkStatsigFeatureGate_CACHED_MAY_BE_STALE` exists only as a migration shim. | MEDIUM |
| 10 | "Dynamic Config" hook `useDynamicConfig.ts` listed as part of analytics | That file is in `src/hooks/`, not in `src/services/analytics/`. Not part of this module. | LOW |

---

## 3. Complete Event Logging Pipeline

### 3.1 Queue-Then-Drain Pattern (index.ts)

```
Application code
  |
  v
logEvent(name, metadata)  ──── sink === null? ──── YES ──> eventQueue.push({name, metadata, async:false})
  |                                                          (array, unbounded)
  NO
  |
  v
sink.logEvent(name, metadata)
```

**Drain on attach:**
```typescript
export function attachAnalyticsSink(newSink: AnalyticsSink): void {
  if (sink !== null) return                    // idempotent
  sink = newSink
  if (eventQueue.length > 0) {
    const queuedEvents = [...eventQueue]       // snapshot
    eventQueue.length = 0                      // clear
    queueMicrotask(() => {                     // async drain — non-blocking
      for (const event of queuedEvents) {
        event.async ? void sink!.logEventAsync(...) : sink!.logEvent(...)
      }
    })
  }
}
```

Key design: Module has **zero imports** to prevent import cycles. The sink is injected late during startup.

### 3.2 Sink Routing (sink.ts)

```
logEventImpl(eventName, metadata)
  |
  v
shouldSampleEvent(eventName)  ──── returns 0 ──> DROP (sampled out)
  |
  returns null (no config, 100%) or positive rate
  |
  v
metadataWithSampleRate = { ...metadata, sample_rate }   (if rate !== null)
  |
  ├──> shouldTrackDatadog()?
  |      YES -> trackDatadogEvent(eventName, stripProtoFields(metadata))
  |             ^ strips _PROTO_* keys before Datadog (general-access backend)
  |
  └──> logEventTo1P(eventName, metadataWithSampleRate)
         ^ receives FULL payload including _PROTO_* keys
           (exporter hoists them to proto fields, then strips remainder)
```

**Async impl**: `logEventAsyncImpl` simply calls `logEventImpl` synchronously and returns `Promise.resolve()`. Comment: "With Segment removed the two remaining sinks are fire-and-forget."

### 3.3 Initialization Sequence

Called from `main.tsx` during `setupBackend()`:
1. `initializeAnalyticsGates()` — reads Datadog feature gate from GrowthBook cache
2. `initializeAnalyticsSink()` — calls `attachAnalyticsSink({ logEvent: logEventImpl, logEventAsync: logEventAsyncImpl })`

---

## 4. PII Safety Enforcement (Branded Types)

### 4.1 Core Branded Types

```typescript
// index.ts — phantom type, resolves to `never`
export type AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS = never

// index.ts — for PII-tagged proto columns
export type AnalyticsMetadata_I_VERIFIED_THIS_IS_PII_TAGGED = never
```

**Enforcement mechanism**: `logEvent` metadata type is `{ [key: string]: boolean | number | undefined }` — **strings are structurally excluded**. String values can only enter analytics through metadata.ts helper functions that return the branded `never` type via explicit `as` casts, forcing developer acknowledgment at each call site.

### 4.2 _PROTO_* Key Convention

Keys prefixed with `_PROTO_` carry PII-tagged data destined for privileged BQ columns:
- `_PROTO_skill_name` — hoisted to `ClaudeCodeInternalEvent.skill_name`
- `_PROTO_plugin_name` — hoisted to `ClaudeCodeInternalEvent.plugin_name`
- `_PROTO_marketplace_name` — hoisted to `ClaudeCodeInternalEvent.marketplace_name`

**stripProtoFields()** (index.ts): Removes all `_PROTO_*` keys from a record. Used:
1. In sink.ts before Datadog fanout
2. In firstPartyEventLoggingExporter.ts after hoisting known keys — defensive strip of `additional_metadata`

Returns same reference (no clone) when no `_PROTO_` keys present (optimization).

### 4.3 MCP Tool Name Sanitization (metadata.ts)

```typescript
sanitizeToolNameForAnalytics("mcp__slack__read_channel") // => "mcp_tool"
sanitizeToolNameForAnalytics("Read")                      // => "Read" (pass-through)
```

Detailed logging allowed for:
- `CLAUDE_CODE_ENTRYPOINT === 'local-agent'` (Cowork)
- `mcpServerType === 'claudeai-proxy'`
- URL matches official MCP registry
- Built-in MCP servers (e.g., `computer-use`, feature-gated via `CHICAGO_MCP`)

### 4.4 File Extension Extraction

`getFileExtensionForAnalytics(filePath)`: Extracts extension, caps at 10 chars (longer = `'other'`).
`getFileExtensionsFromBashCommand(command)`: Parses bash commands, extracts extensions from allowed commands (`rm`, `mv`, `cp`, `cat`, `grep`, `sed`, etc.), skips flags.

### 4.5 Tool Input Truncation

`extractToolInputForTelemetry(input)`: Gated on `OTEL_LOG_TOOL_DETAILS`. Truncation limits:
- Strings > 512 chars truncated to 128 + length indicator
- Max depth: 2 levels
- Max collection items: 20
- Max JSON output: 4096 chars
- Internal `_`-prefixed keys stripped

---

## 5. Datadog Integration (datadog.ts)

### 5.1 Configuration

| Constant | Value |
|----------|-------|
| Endpoint | `https://http-intake.logs.us5.datadoghq.com/api/v2/logs` |
| Client Token | `pubbbf48e6d78dae54bceaa4acf463299bf` |
| Flush Interval | 15,000ms (override via `CLAUDE_CODE_DATADOG_FLUSH_INTERVAL_MS`) |
| Max Batch Size | 100 |
| Network Timeout | 5,000ms |

### 5.2 Allowed Events (Allowlist, 37 events)

```
chrome_bridge_connection_succeeded, chrome_bridge_connection_failed,
chrome_bridge_disconnected, chrome_bridge_tool_call_completed,
chrome_bridge_tool_call_error, chrome_bridge_tool_call_started,
chrome_bridge_tool_call_timeout,
tengu_api_error, tengu_api_success, tengu_brief_mode_enabled,
tengu_brief_mode_toggled, tengu_brief_send, tengu_cancel,
tengu_compact_failed, tengu_exit, tengu_flicker, tengu_init,
tengu_model_fallback_triggered,
tengu_oauth_error, tengu_oauth_success, tengu_oauth_token_refresh_failure,
tengu_oauth_token_refresh_success, tengu_oauth_token_refresh_lock_acquiring,
tengu_oauth_token_refresh_lock_acquired, tengu_oauth_token_refresh_starting,
tengu_oauth_token_refresh_completed, tengu_oauth_token_refresh_lock_releasing,
tengu_oauth_token_refresh_lock_released,
tengu_query_error, tengu_session_file_read, tengu_started,
tengu_tool_use_error, tengu_tool_use_granted_in_prompt_permanent,
tengu_tool_use_granted_in_prompt_temporary, tengu_tool_use_rejected_in_prompt,
tengu_tool_use_success, tengu_uncaught_exception,
tengu_unhandled_rejection, tengu_voice_recording_started,
tengu_voice_toggled, tengu_team_mem_sync_pull, tengu_team_mem_sync_push,
tengu_team_mem_sync_started, tengu_team_mem_entries_capped
```

### 5.3 Tag Fields (for DD searchable tags)

`arch, clientType, errorType, http_status_range, http_status, kairosActive, model, platform, provider, skillMode, subscriptionType, toolName, userBucket, userType, version, versionBase`

### 5.4 Cardinality Reduction

- MCP tool names normalized to `"mcp"` (external users)
- Model names normalized via `getCanonicalName` to known `MODEL_COSTS` keys or `"other"` (external users only)
- Dev versions truncated: `2.0.53-dev.20251124.t173302.sha526cc6a` -> `2.0.53-dev.20251124`
- `status` field remapped to `http_status` + `http_status_range` (avoids DD reserved field)

### 5.5 User Bucketing

```typescript
const NUM_USER_BUCKETS = 30
// SHA256(userId) % 30 — for alerting on unique-user-count without cardinality explosion
```

### 5.6 Gating

- `NODE_ENV !== 'production'` -> skip
- `getAPIProvider() !== 'firstParty'` -> skip (no 3P provider events)
- `initializeDatadog()` memoized, checks `isAnalyticsDisabled()`
- `DATADOG_ALLOWED_EVENTS` allowlist check
- Kill switch: `isSinkKilled('datadog')`

### 5.7 Batch Flush

- Events accumulate in `logBatch[]`
- Timer-based flush every 15s (`.unref()` — doesn't keep process alive)
- Immediate flush when batch >= 100
- `shutdownDatadog()` clears timer and flushes (called from `gracefulShutdown()`)

---

## 6. First-Party Event Logger (firstPartyEventLogger.ts)

### 6.1 Architecture

Built on OpenTelemetry SDK Logs:
```
logEventTo1P(name, metadata)
  |
  v
logEventTo1PAsync(logger, name, metadata)    [fire-and-forget]
  |
  v
getEventMetadata(...)                         [enrichment]
  |
  v
logger.emit({ body: eventName, attributes })  [OTel LogRecord]
  |
  v
BatchLogRecordProcessor                       [batching]
  |
  v
FirstPartyEventLoggingExporter.export()       [HTTP POST]
```

### 6.2 Sampling (shouldSampleEvent)

```typescript
function shouldSampleEvent(eventName: string): number | null
```

- Config from GrowthBook: `tengu_event_sampling_config` — JSON map of `{ [eventName]: { sample_rate: number } }`
- No config for event -> `null` (log at 100%, no `sample_rate` field added)
- `sample_rate === 1` -> `null` (log all, no metadata added)
- `sample_rate === 0` -> `0` (drop all)
- `0 < rate < 1` -> `Math.random() < rate ? rate : 0`
- Return value `0` = drop; positive number = log and attach as `sample_rate` metadata

### 6.3 Batch Configuration

From GrowthBook `tengu_1p_event_batch_config`:
```typescript
type BatchConfig = {
  scheduledDelayMillis?: number    // default: 10,000ms
  maxExportBatchSize?: number      // default: 200
  maxQueueSize?: number            // default: 8,192
  skipAuth?: boolean
  maxAttempts?: number
  path?: string                    // default: '/api/event_logging/batch'
  baseUrl?: string                 // default: 'https://api.anthropic.com'
}
```

### 6.4 GrowthBook Experiment Logging

```typescript
function logGrowthBookExperimentTo1P(data: GrowthBookExperimentData): void
```

Emits `'growthbook_experiment'` events with:
- `experiment_id`, `variation_id`, `device_id`, `account_uuid`, `organization_uuid`
- `session_id`, `user_attributes` (JSON), `experiment_metadata` (JSON)
- `environment: 'production'`

### 6.5 Hot-Reinit on Config Change

```typescript
async function reinitialize1PEventLoggingIfConfigChanged(): Promise<void>
```

Registered with `onGrowthBookRefresh`. When `tengu_1p_event_batch_config` changes:
1. Null the logger (concurrent calls bail)
2. `forceFlush()` old provider (drain buffer)
3. Create new provider via `initialize1PEventLogging()`
4. Old provider shutdown in background
5. On failure: restore old provider+logger for recovery

### 6.6 Initialization

```typescript
function initialize1PEventLogging(): void
```

- Creates `FirstPartyEventLoggingExporter` with batch config
- Creates `LoggerProvider` with `BatchLogRecordProcessor`
- Logger scope: `'com.anthropic.claude_code.events'`
- Resource: `service.name: 'claude-code'`, `service.version: MACRO.VERSION`
- WSL version attribute added if applicable

---

## 7. First-Party Event Logging Exporter (firstPartyEventLoggingExporter.ts)

### 7.1 Class: `FirstPartyEventLoggingExporter implements LogRecordExporter`

**Constructor defaults:**
| Option | Default |
|--------|---------|
| `timeout` | 10,000ms |
| `maxBatchSize` | 200 |
| `skipAuth` | false |
| `batchDelayMs` | 100ms (between sub-batches) |
| `baseBackoffDelayMs` | 500ms |
| `maxBackoffDelayMs` | 30,000ms |
| `maxAttempts` | 8 |
| `endpoint` | `https://api.anthropic.com/api/event_logging/batch` |

### 7.2 Export Cycle

```
export(logs, resultCallback)
  |
  v
doExport(logs, resultCallback)
  |
  v
Filter: instrumentationScope.name === 'com.anthropic.claude_code.events'
  |
  v
transformLogsToEvents(logs) -> FirstPartyEventLoggingEvent[]
  |
  v
sendEventsInBatches(events)
  |
  ├── SUCCESS -> resetBackoff(), retryFailedEvents() if queued
  └── FAILURE -> queueFailedEvents(), scheduleBackoffRetry()
```

### 7.3 Event Transformation

Two event types:
1. **`ClaudeCodeInternalEvent`** — standard analytics events
   - Enriched with `core_metadata`, `user_metadata`, `event_metadata`
   - `_PROTO_*` keys hoisted to proto fields (`skill_name`, `plugin_name`, `marketplace_name`)
   - Remaining `_PROTO_*` defensively stripped from `additional_metadata`
   - `additional_metadata` base64-encoded JSON
2. **`GrowthbookExperimentEvent`** — A/B test assignments
   - Identified by `attributes.event_type === 'GrowthbookExperimentEvent'`

Both use protobuf `.toJSON()` for serialization.

### 7.4 Retry & Backoff

- **Quadratic backoff**: `baseBackoffDelayMs * attempts^2`, capped at `maxBackoffDelayMs`
  - Attempt 1: 500ms, Attempt 2: 2,000ms, Attempt 3: 4,500ms, ... Attempt 8: 30,000ms (capped)
- **Max attempts**: 8 (then events are dropped)
- **Short-circuit**: On first batch failure, remaining unsent batches are queued (not POSTed)
- **Disk persistence**: Failed events appended to `~/.claude/telemetry/1p_failed_events.<sessionId>.<batchUUID>.json` (JSONL format)
- **Startup retry**: Constructor calls `retryPreviousBatches()` — scans for same-session files from previous process runs

### 7.5 Kill Switch Integration

```typescript
if (this.isKilled()) {
  throw new Error('firstParty sink killswitch active')
  // -> queued to disk, backoff timer continues probing
}
```

The `isKilled` callback is injected at construction to avoid import cycles.

### 7.6 Auth Handling

Priority chain:
1. `skipAuth` option (from batch config) -> no auth
2. Trust not established AND not non-interactive -> no auth
3. OAuth token expired -> skip auth (avoid 401)
4. No profile scope -> skip auth
5. Otherwise: `getAuthHeaders()` for full auth

On 401 with auth: retries without auth (fallback).

Headers: `Content-Type`, `User-Agent` (Claude Code UA), `x-service-name: claude-code`

---

## 8. Analytics Configuration (config.ts)

### 8.1 Exported Functions

```typescript
function isAnalyticsDisabled(): boolean
```
Returns `true` when ANY of:
- `NODE_ENV === 'test'`
- `CLAUDE_CODE_USE_BEDROCK` is truthy
- `CLAUDE_CODE_USE_VERTEX` is truthy
- `CLAUDE_CODE_USE_FOUNDRY` is truthy
- `isTelemetryDisabled()` (privacy level)

```typescript
function isFeedbackSurveyDisabled(): boolean
```
Only checks `NODE_ENV === 'test'` OR `isTelemetryDisabled()` — does NOT block on 3P providers.

---

## 9. Sink Kill Switch (sinkKillswitch.ts)

### 9.1 Mechanism

```typescript
type SinkName = 'datadog' | 'firstParty'

function isSinkKilled(sink: SinkName): boolean
```

- GrowthBook config name: `tengu_frond_boric` (intentionally mangled)
- Config shape: `{ datadog?: boolean, firstParty?: boolean }`
- `true` = killed (stop dispatch)
- Default `{}` = fail-open (both sinks active)
- Missing/malformed config = fail-open

**WARNING in source**: Must NOT be called from `is1PEventLoggingEnabled()` — would cause recursion through `growthbook.ts:isGrowthBookEnabled()`.

---

## 10. GrowthBook / Feature Flags (growthbook.ts)

### 10.1 Architecture

GrowthBook SDK with `remoteEval: true` — server pre-evaluates features for the user. Client caches results in memory (`remoteEvalFeatureValues` Map) and on disk (`~/.claude.json:cachedGrowthBookFeatures`).

### 10.2 Value Resolution Priority

For `getFeatureValue_CACHED_MAY_BE_STALE`:
1. Env var overrides: `CLAUDE_INTERNAL_FC_OVERRIDES` (ant-only, JSON)
2. Config overrides: `~/.claude.json:growthBookOverrides` (ant-only, via `/config` Gates tab)
3. In-memory `remoteEvalFeatureValues` Map (post-init)
4. Disk cache: `~/.claude.json:cachedGrowthBookFeatures`
5. `defaultValue` parameter

### 10.3 Exported Functions — Complete List

| Function | Signature | Description |
|----------|-----------|-------------|
| `initializeGrowthBook` | `() => Promise<GrowthBook \| null>` | Memoized init, blocks until ready |
| `getFeatureValue_DEPRECATED<T>` | `(feature, defaultValue) => Promise<T>` | Blocking, logs exposure |
| `getFeatureValue_CACHED_MAY_BE_STALE<T>` | `(feature, defaultValue) => T` | Non-blocking disk/memory cache |
| `getFeatureValue_CACHED_WITH_REFRESH<T>` | `(feature, defaultValue, refreshIntervalMs) => T` | Deprecated, delegates to CACHED_MAY_BE_STALE |
| `checkStatsigFeatureGate_CACHED_MAY_BE_STALE` | `(gate) => boolean` | Migration shim: GB cache -> Statsig cache fallback |
| `checkSecurityRestrictionGate` | `(gate) => Promise<boolean>` | Waits for reinit if in progress |
| `checkGate_CACHED_OR_BLOCKING` | `(gate) => Promise<boolean>` | Fast path if cached true, else blocks on init |
| `getDynamicConfig_BLOCKS_ON_INIT<T>` | `(configName, defaultValue) => Promise<T>` | Blocks on init |
| `getDynamicConfig_CACHED_MAY_BE_STALE<T>` | `(configName, defaultValue) => T` | Non-blocking |
| `refreshGrowthBookAfterAuthChange` | `() => void` | Destroys + recreates client |
| `refreshGrowthBookFeatures` | `() => Promise<void>` | Light refresh (re-fetch, no recreate) |
| `setupPeriodicGrowthBookRefresh` | `() => void` | Sets up interval (6h external, 20min ant) |
| `stopPeriodicGrowthBookRefresh` | `() => void` | Clears interval |
| `resetGrowthBook` | `() => void` | Full state reset (testing) |
| `onGrowthBookRefresh` | `(listener) => () => void` | Subscribe to refresh events |
| `hasGrowthBookEnvOverride` | `(feature) => boolean` | Check if env override exists |
| `getAllGrowthBookFeatures` | `() => Record<string, unknown>` | All known features |
| `getGrowthBookConfigOverrides` | `() => Record<string, unknown>` | Current config overrides |
| `setGrowthBookConfigOverride` | `(feature, value) => void` | Set/clear single override |
| `clearGrowthBookConfigOverrides` | `() => void` | Clear all overrides |
| `getApiBaseUrlHost` | `() => string \| undefined` | Non-default API host for targeting |

### 10.4 Experiment Exposure Tracking

- `experimentDataByFeature` Map: populated from remote eval payload when `source === 'experiment'`
- `loggedExposures` Set: dedup within session (each feature logged at most once)
- `pendingExposures` Set: features accessed before init, logged after init completes
- Exposure events emitted via `logGrowthBookExperimentTo1P()`

### 10.5 Periodic Refresh

| User Type | Interval |
|-----------|----------|
| External | 6 hours |
| Ant (internal) | 20 minutes |

Timer is `.unref()`'d. Process exit handler registered via `process.once('beforeExit')`.

### 10.6 Workarounds

1. **Malformed API response**: Server returns `{ value: ... }` instead of `{ defaultValue: ... }`. Transformed in `processRemoteEvalPayload`.
2. **SDK re-evaluation bug**: SDK's `evalFeature()` re-evaluates rules locally, ignoring pre-evaluated `value` from `remoteEval`. Values cached in `remoteEvalFeatureValues` Map.
3. **Empty payload guard**: `Object.keys(payload.features).length === 0` check prevents wiping disk cache from truncated responses.

---

## 11. Metadata Enrichment (metadata.ts)

### 11.1 Core Types

**EventMetadata** — shared across all analytics:
- `model`, `sessionId`, `userType`, `betas`, `envContext`, `entrypoint`, `agentSdkVersion`
- `isInteractive`, `clientType`, `processMetrics`, `sweBenchRunId/InstanceId/TaskId`
- Agent identification: `agentId`, `parentSessionId`, `agentType` (teammate|subagent|standalone), `teamName`
- `subscriptionType`, `rh` (repo remote hash), `kairosActive`, `skillMode`, `observerMode`

**EnvContext** — 30+ fields covering platform, CI, remote, GitHub Actions, WSL, Linux distro, VCS.

**ProcessMetrics** — uptime, RSS, heap, external, arrayBuffers, constrainedMemory, cpuUsage, cpuPercent (delta-based).

### 11.2 Exported Functions — Complete List

| Function | Signature | Description |
|----------|-----------|-------------|
| `getEventMetadata` | `(options?) => Promise<EventMetadata>` | Full metadata enrichment |
| `to1PEventFormat` | `(metadata, userMetadata, additionalMetadata?) => FirstPartyEventLoggingMetadata` | Convert to 1P snake_case proto format |
| `sanitizeToolNameForAnalytics` | `(toolName) => branded string` | MCP -> 'mcp_tool', built-in pass-through |
| `isToolDetailsLoggingEnabled` | `() => boolean` | `OTEL_LOG_TOOL_DETAILS` check |
| `isAnalyticsToolDetailsLoggingEnabled` | `(mcpServerType?, mcpServerBaseUrl?) => boolean` | Per-MCP-server gating |
| `mcpToolDetailsForAnalytics` | `(toolName, mcpServerType?, mcpServerBaseUrl?) => { mcpServerName?, mcpToolName? }` | Spreadable helper for logEvent call sites |
| `extractMcpToolDetails` | `(toolName) => { serverName, mcpToolName } \| undefined` | Parse `mcp__<server>__<tool>` |
| `extractSkillName` | `(toolName, input) => string \| undefined` | Extract skill name from Skill tool input |
| `extractToolInputForTelemetry` | `(input) => string \| undefined` | Truncated JSON serialization |
| `getFileExtensionForAnalytics` | `(filePath) => branded string \| undefined` | Safe extension extraction |
| `getFileExtensionsFromBashCommand` | `(command, sedFilePath?) => branded string \| undefined` | Parse bash for file extensions |

### 11.3 Agent Identification (getAgentIdentification)

Priority:
1. AsyncLocalStorage context (`getAgentContext()`) — for subagents in same process
2. Env vars via `teammate.ts` — for swarm agents
3. Bootstrap state (`getParentSessionIdFromState()`) — for plan-mode -> implementation

### 11.4 to1PEventFormat

Converts camelCase `EventMetadata` + `CoreUserData` + additional metadata into `FirstPartyEventLoggingMetadata`:
- `env`: Proto-typed `EnvironmentMetadata` (compile-time check against proto schema)
- `process`: Base64-encoded JSON of `ProcessMetrics`
- `auth`: `{ account_uuid, organization_uuid }` (if present)
- `core`: Snake_case core fields (session_id, model, user_type, etc.)
- `additional`: Catch-all for `rh`, `is_assistant_mode`, `skill_mode`, `observer_mode`, plus event-specific metadata

---

## 12. Architectural Patterns

### 12.1 Zero-Import Public API
`index.ts` imports nothing — prevents import cycle contamination. The sink is injected via `attachAnalyticsSink()`.

### 12.2 Fail-Open / Fail-Safe Design
- Kill switch defaults to `{}` (all sinks active)
- GrowthBook failure -> use disk cache -> use default values
- 1P exporter failure -> persist to disk -> retry with backoff

### 12.3 Ant-Only Debug Logging
Extensive `process.env.USER_TYPE === 'ant'` guards throughout. Internal users get verbose debug output; external users get silent operation.

### 12.4 Idempotent Initialization
Both `attachAnalyticsSink` and `initializeAnalyticsSink` are idempotent (no-op on second call). `initializeGrowthBook` and `initializeDatadog` are memoized.

### 12.5 Proto-Typed Safety
`to1PEventFormat` uses the generated `EnvironmentMetadata` type so that adding a field that the proto doesn't define is a compile error. Prevents silent data loss from `toJSON()` dropping unknown keys.

---

## 13. Quality Assessment

| Dimension | Score | Notes |
|-----------|-------|-------|
| PII Safety | 9/10 | Branded types + structural string exclusion + _PROTO_ convention + tool name sanitization |
| Resilience | 9/10 | Disk persistence, quadratic backoff, kill switches, auth fallback |
| Code Clarity | 8/10 | Excellent comments, clear naming conventions (_CACHED_MAY_BE_STALE, _BLOCKS_ON_INIT) |
| Testability | 7/10 | `_resetForTesting()`, injectable `schedule`, `getQueuedEventCount()` exposed |
| Complexity | 7/10 | GrowthBook has significant workaround complexity; the reinit logic is intricate but well-documented |
| **Overall** | **8.2/10** | Production-grade telemetry with strong privacy guarantees |

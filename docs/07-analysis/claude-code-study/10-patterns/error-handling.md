# Error Handling Patterns

> Claude Code implements a multi-layered error handling system spanning API retry logic, native module failures, permission denials, and user-facing error presentation.

## Overview

Error handling in Claude Code is designed around several principles: fail-fast for unrecoverable errors, exponential-backoff retry for transient failures, graceful degradation when optional features are unavailable, and clear user-facing messages that guide resolution. The most sophisticated error handling lives in the API retry system, which must handle a matrix of error codes, subscription tiers, and authentication providers.

## Error Type Hierarchy

### API Errors (`src/services/api/`)

The primary error types from the Anthropic SDK:

| Type | Source | Retryable |
|------|--------|-----------|
| `APIError` | HTTP status codes from API | Depends on status |
| `APIConnectionError` | Network failures | Yes |
| `APIConnectionTimeoutError` | Request timeout | Yes |
| `APIUserAbortError` | User cancellation (Ctrl+C) | No |

### Custom Error Types

```typescript
// withRetry.ts — wraps non-retryable failures
export class CannotRetryError extends Error {
  constructor(
    public readonly originalError: unknown,
    public readonly retryContext: RetryContext,  // model, thinking config, etc.
  ) {
    super(errorMessage(originalError))
    // Preserve original stack trace
    if (originalError instanceof Error && originalError.stack) {
      this.stack = originalError.stack
    }
  }
}

// withRetry.ts — signals model fallback
export class FallbackTriggeredError extends Error {
  constructor(
    public readonly originalModel: string,
    public readonly fallbackModel: string,
  ) {
    super(`Model fallback triggered: ${originalModel} -> ${fallbackModel}`)
  }
}
```

From `errors.ts`:
```typescript
// Image handling errors
import { ImageResizeError } from '../../utils/imageResizer.js'
import { ImageSizeError } from '../../utils/imageValidation.js'
```

## API Retry System (`src/services/api/withRetry.ts`)

### Architecture

The retry system is an `AsyncGenerator` that yields status messages while retrying, allowing the UI to display progress:

```typescript
export async function* withRetry<T>(
  getClient: () => Promise<Anthropic>,
  operation: (client: Anthropic, attempt: number, context: RetryContext) => Promise<T>,
  options: RetryOptions,
): AsyncGenerator<SystemAPIErrorMessage, T>
```

### Retry Decision Matrix

| Status | Condition | Action |
|--------|-----------|--------|
| 400 | `max_tokens` overflow | Adjust max_tokens, retry |
| 400 | Fast mode not enabled | Disable fast mode, retry |
| 401 | OAuth token expired | Refresh token, retry |
| 403 | OAuth token revoked | Refresh token, retry |
| 403 | Bedrock auth error | Clear AWS cache, retry |
| 408 | Request timeout | Retry with backoff |
| 409 | Lock timeout | Retry with backoff |
| 429 | Rate limit (short) | Sleep retry-after, retry with fast mode |
| 429 | Rate limit (long) | Enter cooldown, switch to standard model |
| 429 | Overage disabled | Permanently disable fast mode |
| 429 | ClaudeAI subscriber | Do not retry (unless Enterprise) |
| 529 | Overloaded (foreground) | Retry up to MAX_529_RETRIES=3 |
| 529 | Overloaded (background) | Immediate fail (no amplification) |
| 529 | Consecutive 3x | Trigger model fallback |
| 5xx | Server error | Retry with backoff |
| ECONNRESET | Stale connection | Disable keep-alive, reconnect |

### Exponential Backoff

```typescript
export function getRetryDelay(
  attempt: number,
  retryAfterHeader?: string | null,
  maxDelayMs = 32000,
): number {
  if (retryAfterHeader) {
    const seconds = parseInt(retryAfterHeader, 10)
    if (!isNaN(seconds)) return seconds * 1000
  }
  const baseDelay = Math.min(BASE_DELAY_MS * Math.pow(2, attempt - 1), maxDelayMs)
  const jitter = Math.random() * 0.25 * baseDelay
  return baseDelay + jitter
}
```

- `BASE_DELAY_MS = 500`
- Exponential: 500ms, 1s, 2s, 4s, 8s, 16s, 32s (cap)
- 25% jitter to prevent thundering herd
- `retry-after` header overrides calculated delay

### Persistent Retry Mode

For unattended sessions (`CLAUDE_CODE_UNATTENDED_RETRY`):

```typescript
const PERSISTENT_MAX_BACKOFF_MS = 5 * 60 * 1000      // 5 minutes
const PERSISTENT_RESET_CAP_MS = 6 * 60 * 60 * 1000   // 6 hours
const HEARTBEAT_INTERVAL_MS = 30_000                   // 30 seconds
```

- Retries 429/529 indefinitely
- Chunked sleep with 30-second heartbeat yields (prevents host idle detection)
- Respects `anthropic-ratelimit-unified-reset` header for window-based limits
- For-loop counter clamped so it never terminates

### Background Query Protection

Non-foreground queries bail immediately on 529 to prevent amplification during capacity cascades:

```typescript
const FOREGROUND_529_RETRY_SOURCES = new Set<QuerySource>([
  'repl_main_thread', 'sdk', 'agent:custom', 'compact', 'auto_mode', ...
])

function shouldRetry529(querySource: QuerySource | undefined): boolean {
  return querySource === undefined || FOREGROUND_529_RETRY_SOURCES.has(querySource)
}
```

### Fast Mode Error Handling

Three fast-mode-specific error paths:

1. **Short retry-after (<20s)**: Wait and retry with same model (preserves prompt cache)
2. **Long retry-after**: Enter cooldown (minimum 10 minutes), switch to standard speed
3. **Overage disabled**: Permanently disable fast mode with specific reason message

```typescript
const SHORT_RETRY_THRESHOLD_MS = 20 * 1000
const MIN_COOLDOWN_MS = 10 * 60 * 1000
const DEFAULT_FAST_MODE_FALLBACK_HOLD_MS = 30 * 60 * 1000
```

### Context Overflow Recovery

```typescript
export function parseMaxTokensContextOverflowError(error: APIError) {
  // Parses: "input length and `max_tokens` exceed context limit: 188059 + 20000 > 200000"
  const regex = /input length and `max_tokens` exceed context limit: (\d+) \+ (\d+) > (\d+)/
  // Adjusts maxTokensOverride for next attempt, floor at FLOOR_OUTPUT_TOKENS=3000
}
```

## Native Module Error Handling

### Graceful Degradation

All native module loaders follow the same pattern — try multiple paths, return null on failure:

```typescript
// vendor/audio-capture-src/index.ts
function loadModule(): AudioCaptureNapi | null {
  if (loadAttempted) return cachedModule
  loadAttempted = true
  if (process.env.AUDIO_CAPTURE_NODE_PATH) {
    try { cachedModule = require(process.env.AUDIO_CAPTURE_NODE_PATH); return cachedModule }
    catch { /* fall through */ }
  }
  for (const p of fallbacks) {
    try { cachedModule = require(p); return cachedModule }
    catch { /* try next */ }
  }
  return null  // graceful degradation
}
```

### Computer Use Native Errors

The computer use executor has no degraded mode — native module load failure is fatal:

```typescript
// hostAdapter.ts
export function getComputerUseHostAdapter(): ComputerUseHostAdapter {
  // ... throws on load failure — there is no degraded mode
}
```

### Timeout Protection

Native calls are wrapped with 30-second timeouts:

```typescript
// drainRunLoop.ts
export async function drainRunLoop<T>(fn: () => Promise<T>): Promise<T> {
  retain()
  try {
    const work = fn()
    work.catch(() => {})  // swallow orphaned rejection on timeout
    const timeout = withResolvers<never>()
    timer = setTimeout(timeoutReject, TIMEOUT_MS, timeout.reject)
    return await Promise.race([work, timeout.promise])
  } finally { release() }
}
```

## Error Recovery Patterns

### Swallow-and-Log

Used for best-effort operations where failure should not propagate:

```typescript
// executor.ts — modifier key release
async function releasePressed(input, pressed): Promise<void> {
  let k: string | undefined
  while ((k = pressed.pop()) !== undefined) {
    try { await input.key(k, 'release') }
    catch { /* Swallow — best-effort release */ }
  }
}
```

```typescript
// cleanup.ts — unhide with timeout
const unhide = unhideComputerUseApps([...hidden]).catch(err =>
  logForDebugging(`auto-unhide failed: ${errorMessage(err)}`)
)
await Promise.race([unhide, timeout.promise])
```

### Try-Recover-Retry

The computer use lock uses a recover-and-retry pattern for stale locks:

```typescript
// Stale lock — recover
await unlink(getLockPath()).catch(() => {})
if (await tryCreateExclusive(lock)) {
  registerLockCleanup()
  return FRESH
}
// Race lost to another session recovering same stale lock
return { kind: 'blocked', by: (await readLock())?.sessionId ?? 'unknown' }
```

### Finally-Based Cleanup

Critical resources always cleaned up via `finally`:

```typescript
// executor.ts — drag always releases mouse button
async drag(from, to): Promise<void> {
  await input.mouseButton('left', 'press')
  try {
    await animatedMove(input, to.x, to.y, getMouseAnimationEnabled())
  } finally {
    await input.mouseButton('left', 'release')  // never leave button stuck
  }
}
```

```typescript
// executor.ts — clipboard always restored after paste
async function typeViaClipboard(input, text): Promise<void> {
  let saved = await readClipboardViaPbpaste()
  try {
    await writeClipboardViaPbcopy(text)
    // ... verify and paste
  } finally {
    if (typeof saved === 'string') {
      try { await writeClipboardViaPbcopy(saved) }
      catch { logForDebugging('clipboard restore failed') }
    }
  }
}
```

## User-Facing Error Messages

### API Error Formatting (`src/services/api/errors.ts`)

Error messages are prefixed for consistent identification:

```typescript
export const API_ERROR_MESSAGE_PREFIX = 'API Error'

export function startsWithApiErrorPrefix(text: string): boolean {
  return text.startsWith(API_ERROR_MESSAGE_PREFIX) ||
    text.startsWith(`Please run /login · ${API_ERROR_MESSAGE_PREFIX}`)
}
```

### Prompt-Too-Long Detection

```typescript
export function parsePromptTooLongTokenCounts(rawMessage: string) {
  const match = rawMessage.match(/prompt is too long[^0-9]*(\d+)\s*tokens?\s*>\s*(\d+)/i)
  return {
    actualTokens: match ? parseInt(match[1]!, 10) : undefined,
    limitTokens: match ? parseInt(match[2]!, 10) : undefined,
  }
}
```

### Deep Link Error Messages

Specific, actionable error messages for each validation failure:

```typescript
throw new Error(`Invalid cwd in deep link: must be an absolute path, got "${cwd}"`)
throw new Error('Deep link cwd contains disallowed control characters')
throw new Error(`Deep link cwd exceeds ${MAX_CWD_LENGTH} characters (got ${cwd.length})`)
throw new Error(`Invalid repo in deep link: expected "owner/repo", got "${repo}"`)
throw new Error('Deep link query contains disallowed control characters')
```

### Voice Mode Error Messages

| Condition | Message |
|-----------|---------|
| No Anthropic OAuth | "Voice mode requires a Claude.ai account. Please run /login to sign in." |
| Kill-switch active | "Voice mode is not available." |
| Mic unavailable | Dynamic reason from availability check |
| Settings write fail | "Failed to update settings. Check your settings file for syntax errors." |

## Error Analytics

Errors are tracked with structured events:

```typescript
logEvent('tengu_api_retry', {
  attempt: reportedAttempt,
  delayMs,
  error: (error as APIError).message,
  status: (error as APIError).status,
  provider: getAPIProviderForStatsig(),
})

logEvent('tengu_api_529_background_dropped', {
  query_source: options.querySource,
})

logEvent('tengu_api_opus_fallback_triggered', {
  original_model: options.model,
  fallback_model: options.fallbackModel,
  provider: getAPIProviderForStatsig(),
})
```

## Authentication Error Recovery

### Multi-Provider Support

```typescript
function isBedrockAuthError(error: unknown): boolean {
  return isEnvTruthy(process.env.CLAUDE_CODE_USE_BEDROCK) &&
    (isAwsCredentialsProviderError(error) || (error instanceof APIError && error.status === 403))
}

function isVertexAuthError(error: unknown): boolean {
  return isEnvTruthy(process.env.CLAUDE_CODE_USE_VERTEX) &&
    (isGoogleAuthLibraryCredentialError(error) || (error instanceof APIError && error.status === 401))
}
```

Each provider has a cache-clear function called on auth error:
- AWS: `clearAwsCredentialsCache()`
- GCP: `clearGcpCredentialsCache()`
- OAuth: `handleOAuth401Error(failedAccessToken)`
- API Key: `clearApiKeyHelperCache()`

### CCR (Claude Code Remote) Special Handling

```typescript
if (isEnvTruthy(process.env.CLAUDE_CODE_REMOTE) && (error.status === 401 || error.status === 403)) {
  return true  // always retry — auth via infrastructure JWTs, not user credentials
}
```

## Protocol Handler Error Handling

### Registration Failure Backoff

```typescript
const FAILURE_BACKOFF_MS = 24 * 60 * 60 * 1000  // 24 hours

// On deterministic errors (EACCES, ENOSPC), write failure marker
if (code === 'EACCES' || code === 'ENOSPC') {
  await fs.writeFile(failureMarkerPath, '').catch(() => {})
}
// Next session skips if marker < 24h old
const stat = await fs.stat(failureMarkerPath)
if (Date.now() - stat.mtimeMs < FAILURE_BACKOFF_MS) return
```

## Summary of Error Handling Strategies

| Strategy | Where Used | When |
|----------|-----------|------|
| Exponential backoff + jitter | API retry | Transient failures |
| Graceful degradation (return null) | Native module loading | Optional features |
| Fail-fast (throw) | Computer use executor | Required native modules |
| Swallow-and-log | Cleanup, key release, unhide | Best-effort side effects |
| Try-recover-retry | Lock acquisition | Race conditions |
| Finally-based cleanup | Mouse button, clipboard, modifiers | Resource safety |
| 24h backoff marker | Protocol registration | Deterministic failures |
| Timeout + race | drainRunLoop, app enumeration | Hung native calls |
| AsyncGenerator yield | withRetry | UI feedback during retry |

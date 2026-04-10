# Design Patterns

> A comprehensive catalog of software design patterns found across the Claude Code codebase, with concrete source references.

## Overview

Claude Code employs a rich set of design patterns suited to its architecture: a TypeScript CLI built on Ink (React for terminals) with extensive native module integration, MCP server management, and an async tool execution pipeline. The patterns range from classic GoF patterns to modern TypeScript-specific idioms.

## 1. Factory Pattern

### Executor Factory (`src/utils/computerUse/executor.ts`)

`createCliExecutor()` constructs a `ComputerExecutor` object with closures over configuration and native modules:

```typescript
export function createCliExecutor(opts: {
  getMouseAnimationEnabled: () => boolean
  getHideBeforeActionEnabled: () => boolean
}): ComputerExecutor {
  if (process.platform !== 'darwin') {
    throw new Error(`createCliExecutor called on ${process.platform}`)
  }
  const cu = requireComputerUseSwift()  // loaded once at factory time
  return {
    capabilities: { ...CLI_CU_CAPABILITIES, hostBundleId: CLI_HOST_BUNDLE_ID },
    async screenshot(opts) { /* uses cu */ },
    async click(x, y, button, count, modifiers) { /* uses cu */ },
    // ... 15+ methods
  }
}
```

**Pattern characteristics:**
- Platform validation at construction time (fail-fast)
- Native modules loaded once, shared across all methods via closure
- Configuration injected as getter functions for late-binding

### MCP Server Factory (`src/utils/computerUse/mcpServer.ts`)

`createComputerUseMcpServerForCli()` is an async factory that builds an MCP server with installed app enumeration:

```typescript
export async function createComputerUseMcpServerForCli() {
  const adapter = getComputerUseHostAdapter()
  const server = createComputerUseMcpServer(adapter, coordinateMode)
  const installedAppNames = await tryGetInstalledAppNames()  // 1s timeout
  const tools = buildComputerUseTools(adapter.executor.capabilities, coordinateMode, installedAppNames)
  server.setRequestHandler(ListToolsRequestSchema, async () =>
    adapter.isDisabled() ? { tools: [] } : { tools })
  return server
}
```

### Task ID Factory (`src/Task.ts`)

```typescript
export function generateTaskId(type: TaskType): string {
  const prefix = getTaskIdPrefix(type)  // 'b', 'a', 'r', 't', 'w', 'm', 'd'
  const bytes = randomBytes(8)
  let id = prefix
  for (let i = 0; i < 8; i++) {
    id += TASK_ID_ALPHABET[bytes[i]! % TASK_ID_ALPHABET.length]
  }
  return id
}
```

Uses a case-insensitive-safe alphabet (36^8 ~ 2.8 trillion combinations) with type-prefixed IDs.

## 2. Singleton Pattern

### Host Adapter Singleton (`src/utils/computerUse/hostAdapter.ts`)

```typescript
let cached: ComputerUseHostAdapter | undefined

export function getComputerUseHostAdapter(): ComputerUseHostAdapter {
  if (cached) return cached
  cached = {
    serverName: COMPUTER_USE_MCP_SERVER_NAME,
    logger: new DebugLogger(),
    executor: createCliExecutor({ /* config */ }),
    ensureOsPermissions: async () => { /* TCC checks */ },
    // ...
  }
  return cached
}
```

**Used extensively for:**
- Native module loaders (`inputLoader.ts`, `swiftLoader.ts`) — load once, cache forever
- Audio capture module (`vendor/audio-capture-src/index.ts`) — `cachedModule` + `loadAttempted` flag
- URL handler module (`vendor/url-handler-src/index.ts`) — same pattern
- Companion roll cache (`buddy/companion.ts`) — keyed on userId for deterministic results

### Lazy Singleton with Platform Guard

```typescript
// inputLoader.ts
let cached: ComputerUseInputAPI | undefined

export function requireComputerUseInput(): ComputerUseInputAPI {
  if (cached) return cached
  const input = require('@ant/computer-use-input') as ComputerUseInput
  if (!input.isSupported) {
    throw new Error('@ant/computer-use-input is not supported')
  }
  return (cached = input)
}
```

## 3. Strategy Pattern

### Gate Strategy (`src/utils/computerUse/gates.ts`)

Feature enablement is computed from multiple strategies composed together:

```typescript
export function getChicagoEnabled(): boolean {
  // Strategy 1: Ant monorepo exclusion
  if (process.env.USER_TYPE === 'ant' && process.env.MONOREPO_ROOT_DIR && !isEnvTruthy(...)) return false
  // Strategy 2: Subscription tier check
  // Strategy 3: GrowthBook dynamic config
  return hasRequiredSubscription() && readConfig().enabled
}
```

### Motion Resolution Strategy (`src/vim/motions.ts`)

```typescript
function applySingleMotion(key: string, cursor: Cursor): Cursor {
  switch (key) {
    case 'h': return cursor.left()
    case 'l': return cursor.right()
    case 'w': return cursor.nextVimWord()
    // ... 14 strategies
  }
}
```

Each motion key selects a different cursor movement strategy, all returning a `Cursor` (uniform interface).

### Retry Strategy (`src/services/api/withRetry.ts`)

Multiple retry strategies composed in a single loop:

| Strategy | Trigger | Behavior |
|----------|---------|----------|
| Fast-mode fallback | 429/529 with short retry-after | Wait and retry with same model |
| Fast-mode cooldown | 429/529 with long retry-after | Switch to standard speed |
| Persistent retry | `CLAUDE_CODE_UNATTENDED_RETRY` | Retry indefinitely with heartbeat |
| Fallback model | Consecutive 529s | Switch to fallback model |
| Auth refresh | 401/403 | Refresh OAuth token and retry |
| Stale connection | ECONNRESET/EPIPE | Disable keep-alive and reconnect |

## 4. State Machine Pattern

### Vim Command State Machine (`src/vim/`)

A textbook finite state machine with TypeScript discriminated unions:

```typescript
// 11-state machine with exhaustive transitions
export type CommandState =
  | { type: 'idle' }
  | { type: 'count'; digits: string }
  | { type: 'operator'; op: Operator; count: number }
  // ... 8 more states

// Transition function: (state, input, context) → (nextState?, sideEffect?)
export function transition(state: CommandState, input: string, ctx: TransitionContext): TransitionResult
```

**Design qualities:**
- TypeScript exhaustive checking via `switch` on discriminated unions
- States encode exactly what data they need (no optional fields)
- Side effects are deferred (returned as `execute?: () => void`)

### Task State Machine (`src/Task.ts`)

```typescript
export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'killed'

export function isTerminalTaskStatus(status: TaskStatus): boolean {
  return status === 'completed' || status === 'failed' || status === 'killed'
}
```

## 5. Observer Pattern

### Settings Change Detection

```typescript
settingsChangeDetector.notifyChange('userSettings')
```

The `settingsChangeDetector` notifies observers when settings change, used by the voice command and other features.

### Companion Notification Hook (`src/buddy/useBuddyNotification.tsx`)

A React hook that observes session events and triggers buddy companion reactions.

### Abort Signal Propagation

Throughout the codebase, `AbortController` / `AbortSignal` implements observer pattern for cancellation:

```typescript
// withRetry.ts
if (options.signal?.aborted) throw new APIUserAbortError()
await sleep(delayMs, options.signal, { abortError })
```

## 6. Adapter Pattern

### Host Adapter (`src/utils/computerUse/hostAdapter.ts`)

Adapts the CLI environment to the `ComputerUseHostAdapter` interface expected by `@ant/computer-use-mcp`:

```typescript
cached = {
  serverName: COMPUTER_USE_MCP_SERVER_NAME,
  executor: createCliExecutor({ /* CLI-specific config */ }),
  ensureOsPermissions: async () => { /* TCC checks */ },
  isDisabled: () => !getChicagoEnabled(),
  cropRawPatch: () => null,  // CLI can't do sync decode; returns null = skipped
}
```

### Debug Logger Adapter

```typescript
class DebugLogger implements Logger {
  silly(message: string, ...args: unknown[]): void {
    logForDebugging(format(message, ...args), { level: 'debug' })
  }
  // ... adapts Logger interface to Claude Code's logForDebugging
}
```

## 7. Registry Pattern

### Browser Registry (`src/utils/claudeInChrome/common.ts`)

A static registry of 7 Chromium browsers with per-platform configuration:

```typescript
export const CHROMIUM_BROWSERS: Record<ChromiumBrowser, BrowserConfig> = {
  chrome: { name: 'Google Chrome', macos: { ... }, linux: { ... }, windows: { ... } },
  brave: { ... },
  // ... 5 more browsers
}

export const BROWSER_DETECTION_ORDER: ChromiumBrowser[] = ['chrome','brave','arc','edge','chromium','vivaldi','opera']
```

### Species Registry (`src/buddy/types.ts`)

```typescript
export const SPECIES = [duck, goose, blob, cat, dragon, octopus, owl, penguin, turtle, snail, ghost, axolotl, capybara, cactus, robot, rabbit, mushroom, chonk] as const
```

### Terminal Bundle ID Registry (`src/utils/computerUse/common.ts`)

```typescript
const TERMINAL_BUNDLE_ID_FALLBACK: Readonly<Record<string, string>> = {
  'iTerm.app': 'com.googlecode.iterm2',
  Apple_Terminal: 'com.apple.Terminal',
  ghostty: 'com.mitchellh.ghostty',
  kitty: 'net.kovidgoyal.kitty',
  WarpTerminal: 'dev.warp.Warp-Stable',
  vscode: 'com.microsoft.VSCode',
}
```

## 8. Middleware / Pipeline Pattern

### Retry Pipeline (`src/services/api/withRetry.ts`)

The `withRetry` function is an `AsyncGenerator` that yields status messages while retrying:

```typescript
export async function* withRetry<T>(
  getClient: () => Promise<Anthropic>,
  operation: (client: Anthropic, attempt: number, context: RetryContext) => Promise<T>,
  options: RetryOptions,
): AsyncGenerator<SystemAPIErrorMessage, T> {
  for (let attempt = 1; attempt <= maxRetries + 1; attempt++) {
    try {
      return await operation(client, attempt, retryContext)
    } catch (error) {
      yield createSystemAPIErrorMessage(error, delayMs, attempt, maxRetries)
      await sleep(delayMs, options.signal, { abortError })
    }
  }
}
```

### Modifier Bracketing (`src/utils/computerUse/executor.ts`)

A middleware-like bracket pattern for keyboard modifiers:

```typescript
async function withModifiers<T>(input, mods, fn: () => Promise<T>): Promise<T> {
  const pressed: string[] = []
  try {
    for (const m of mods) { await input.key(m, 'press'); pressed.push(m) }
    return await fn()
  } finally {
    await releasePressed(input, pressed)  // always release, even on throw
  }
}
```

## 9. Lock / Mutex Pattern

### File-Based Lock (`src/utils/computerUse/computerUseLock.ts`)

```typescript
async function tryCreateExclusive(lock: ComputerUseLock): Promise<boolean> {
  try {
    await writeFile(getLockPath(), jsonStringify(lock), { flag: 'wx' })  // O_EXCL
    return true
  } catch (e) {
    if (getErrnoCode(e) === 'EEXIST') return false
    throw e
  }
}
```

**Features:** Atomic test-and-set via OS, stale detection via `process.kill(pid, 0)`, race-safe recovery with retry.

### Refcounted Resource (`src/utils/computerUse/drainRunLoop.ts`)

```typescript
let pump: ReturnType<typeof setInterval> | undefined
let pending = 0

function retain(): void { pending++; if (!pump) pump = setInterval(drainTick, 1, ...) }
function release(): void { pending--; if (pending <= 0 && pump) { clearInterval(pump); pump = undefined } }
```

## 10. Builder / Configuration Pattern

### MCP Config Builder (`src/utils/computerUse/setup.ts`)

```typescript
export function setupComputerUseMCP(): {
  mcpConfig: Record<string, ScopedMcpServerConfig>
  allowedTools: string[]
} {
  const allowedTools = buildComputerUseTools(CLI_CU_CAPABILITIES, getChicagoCoordinateMode())
    .map(t => buildMcpToolName(COMPUTER_USE_MCP_SERVER_NAME, t.name))
  return {
    mcpConfig: { [COMPUTER_USE_MCP_SERVER_NAME]: { type: 'stdio', command: process.execPath, args, scope: 'dynamic' } },
    allowedTools,
  }
}
```

### GrowthBook Config with Defaults (`src/utils/computerUse/gates.ts`)

```typescript
const DEFAULTS: ChicagoConfig = {
  enabled: false, pixelValidation: false, clipboardPasteMultiline: true,
  mouseAnimation: true, hideBeforeAction: true, autoTargetDisplay: true, clipboardGuard: true,
  coordinateMode: 'pixels',
}

function readConfig(): ChicagoConfig {
  return { ...DEFAULTS, ...getDynamicConfig_CACHED_MAY_BE_STALE<Partial<ChicagoConfig>>('tengu_malort_pedway', DEFAULTS) }
}
```

## 11. Seeded PRNG Pattern (`src/buddy/companion.ts`)

Deterministic generation using Mulberry32 seeded from hashed user ID:

```typescript
const SALT = 'friend-2026-401'

export function roll(userId: string): Roll {
  const key = userId + SALT
  if (rollCache?.key === key) return rollCache.value  // hot-path cache
  const value = rollFrom(mulberry32(hashString(key)))
  rollCache = { key, value }
  return value
}
```

## Pattern Summary

| Pattern | Primary Locations | Frequency |
|---------|-------------------|-----------|
| Factory | executor, mcpServer, taskId | High |
| Singleton | hostAdapter, native loaders, audio | High |
| Strategy | gates, motions, retry | High |
| State Machine | vim, task status | Medium |
| Observer | settings, abort signals, buddy | Medium |
| Adapter | hostAdapter, debugLogger | Medium |
| Registry | browsers, species, terminals | Medium |
| Middleware/Pipeline | withRetry, withModifiers | Medium |
| Lock/Mutex | computerUseLock, pidLock, drainRunLoop | Medium |
| Builder/Config | setup, gates | Low |
| Seeded PRNG | companion | Low |

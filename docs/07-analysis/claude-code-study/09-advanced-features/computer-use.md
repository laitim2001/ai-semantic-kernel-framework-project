# Computer Use Implementation

> Claude Code's computer use feature enables the AI to control the user's desktop through screenshots, mouse, and keyboard — all gated behind a multi-layered safety system.

## Overview

Computer use (internally codenamed "Chicago") is a macOS-only feature that gives the Claude model the ability to take screenshots, move the mouse, click, type, drag, and scroll on the user's display. It is built on two native modules and exposed as an in-process MCP server with tool names matching the `mcp__computer-use__*` convention required by the API backend.

**Key source files:**

| File | Purpose |
|------|---------|
| `src/utils/computerUse/executor.ts` | Core `ComputerExecutor` implementation — mouse, keyboard, screenshots |
| `src/utils/computerUse/common.ts` | Constants, terminal bundle ID detection |
| `src/utils/computerUse/gates.ts` | Feature gating via GrowthBook + subscription tier |
| `src/utils/computerUse/hostAdapter.ts` | Singleton adapter bridging executor to MCP |
| `src/utils/computerUse/setup.ts` | MCP config + allowed tool list construction |
| `src/utils/computerUse/mcpServer.ts` | In-process MCP server factory |
| `src/utils/computerUse/wrapper.tsx` | `.call()` override, session context binding, permission dialog |
| `src/utils/computerUse/toolRendering.tsx` | User-facing rendering of CU tool calls |
| `src/utils/computerUse/computerUseLock.ts` | File-based session lock (O_EXCL atomicity) |
| `src/utils/computerUse/cleanup.ts` | Turn-end cleanup: unhide apps, release lock |
| `src/utils/computerUse/escHotkey.ts` | Global Escape hotkey abort via CGEventTap |
| `src/utils/computerUse/drainRunLoop.ts` | CFRunLoop pump for Swift/Rust native calls |
| `src/utils/computerUse/inputLoader.ts` | Lazy-load `@ant/computer-use-input` (Rust/enigo) |
| `src/utils/computerUse/swiftLoader.ts` | Lazy-load `@ant/computer-use-swift` |
| `src/components/permissions/ComputerUseApproval/` | Permission dialog React component |

## Architecture

### Native Module Stack

```
Claude Model (API)
    ↓ mcp__computer-use__* tool calls
In-Process MCP Server (mcpServer.ts)
    ↓ call override
Session Context Binding (wrapper.tsx)
    ↓ dispatches
CLI Executor (executor.ts)
    ├── @ant/computer-use-swift  →  SCContentFilter screenshots, NSWorkspace apps, TCC checks
    └── @ant/computer-use-input  →  Rust/enigo mouse + keyboard via HID
```

The architecture mirrors the Cowork (desktop app) `ComputerExecutor` contract from `@ant/computer-use-mcp`, with notable CLI-specific adaptations:

1. **No click-through**: Cowork wraps mouse ops in `BrowserWindow.setIgnoreMouseEvents(true)`. The CLI has no window, so this is a no-op.
2. **Terminal as surrogate host**: `getTerminalBundleId()` detects the terminal emulator (iTerm2, Terminal.app, Ghostty, Kitty, Warp, VS Code) via `__CFBundleIdentifier` env var, and exempts it from hiding and screenshots.
3. **Clipboard via pbcopy/pbpaste**: No Electron `clipboard` module; shell commands are used instead.

### CFRunLoop Drain Pump

Swift's `@MainActor` async methods and Rust's `DispatchQueue.main` calls both dispatch to the macOS main run loop. Under Node.js/Bun (libuv), this queue never drains naturally (unlike Electron which continuously pumps CFRunLoop). The solution:

```typescript
// drainRunLoop.ts — shared refcounted setInterval at 1ms
let pump: ReturnType<typeof setInterval> | undefined
let pending = 0

function retain() {
  pending++
  if (pump === undefined) {
    pump = setInterval(drainTick, 1, requireComputerUseSwift())
  }
}
```

`drainRunLoop<T>(fn)` holds the pump for the duration of the native call, with a 30-second timeout. Multiple concurrent calls share a single pump via refcounting.

## Screenshot System

### Capture Pipeline

1. **Display geometry**: `cu.display.getSize(displayId)` returns logical width/height and scale factor
2. **Target dimensions**: `computeTargetDims()` converts logical → physical → API target dims via `targetImageSize()` from `@ant/computer-use-mcp`
3. **Capture**: `cu.screenshot.captureExcluding()` takes a JPEG at 0.75 quality, pre-sized to match the API's expected dimensions so no server-side resize occurs
4. **Terminal exclusion**: `withoutTerminal()` filters the terminal's bundle ID from the allow-list

### Region Zoom

`zoom()` captures a specific region of the screen at higher effective resolution, using `cu.screenshot.captureRegion()` with independent output dimensions.

## Input Control

### Keyboard

- **Key sequences**: xdotool-style strings like `"ctrl+shift+a"` are split on `+` and dispatched via `input.keys(parts)`
- **Key repeat**: 8ms between iterations (125Hz USB polling cadence)
- **Hold key**: Press/release bracketed with independent drain pump, `orphaned` flag guards against timeout races
- **Type text**: Two modes — direct `input.typeText()` for single graphemes, or clipboard-based paste via `typeViaClipboard()` for multiline

### Clipboard-Based Typing (`typeViaClipboard`)

A robust 6-step sequence ported from Cowork:
1. Save user's clipboard via `pbpaste`
2. Write target text via `pbcopy`
3. **Read-back verify** — if mismatch, abort (never Cmd+V junk)
4. Press `Cmd+V` via `input.keys(['command', 'v'])`
5. Sleep 100ms for paste-effect vs restore race
6. Restore original clipboard in `finally` block

### Mouse

- **Move and settle**: Instant `moveMouse()` + 50ms settle for HID round-trip
- **Click**: Move → settle → `mouseButton(button, 'click', count)` with optional modifier bracketing
- **Drag**: Move to `from` → press → `animatedMove()` (ease-out-cubic at 60fps, 2000px/sec, capped 0.5s) → release in `finally`
- **Scroll**: Move → vertical first → horizontal (vertical-first so horizontal failure doesn't lose vertical)

### Animated Mouse Movement

Used only for drag operations. Ease-out-cubic curve at 60fps with distance-proportional duration:

```typescript
const durationSec = Math.min(distance / 2000, 0.5)
for (let frame = 1; frame <= totalFrames; frame++) {
  const t = frame / totalFrames
  const eased = 1 - Math.pow(1 - t, 3)  // ease-out-cubic
  await input.moveMouse(Math.round(start.x + deltaX * eased), ...)
}
```

## Safety System

### Multi-Layered Gating

1. **Platform gate**: `createCliExecutor` throws on non-darwin platforms
2. **Subscription gate**: Max or Pro subscription required (ants bypass via `USER_TYPE`)
3. **GrowthBook gate**: `tengu_malort_pedway` feature flag controls runtime enablement
4. **Monorepo guard**: Ants with monorepo dev config are blocked unless `ALLOW_ANT_COMPUTER_USE_MCP=1`
5. **OS permissions**: TCC checks for Accessibility and Screen Recording via `cu.tcc.checkAccessibility()` / `cu.tcc.checkScreenRecording()`

### Session Lock (`computerUseLock.ts`)

A file-based mutual exclusion ensuring only one Claude session controls the computer at a time:

- **Lock file**: `~/.claude/computer-use.lock` containing `{ sessionId, pid, acquiredAt }`
- **Atomic creation**: `writeFile(path, data, { flag: 'wx' })` (O_EXCL) — OS guarantees at most one process sees success
- **Stale detection**: `process.kill(pid, 0)` signal-0 probe checks liveness; stale locks are unlinked with one retry
- **Re-entrant**: Same session re-acquiring returns `{ kind: 'acquired', fresh: false }`
- **Shutdown cleanup**: `registerCleanup()` ensures release even if turn-end cleanup is skipped

### Escape Hotkey Abort

A global CGEventTap via `@ant/computer-use-swift` that:
- Consumes Escape system-wide during CU sessions (prompt injection defense — prevents injected actions from dismissing dialogs)
- Model-synthesized Escapes punch a hole via `notifyExpectedEscape()` with 100ms decay
- Holds a drain pump retain for the CGEventTap's CFRunLoopSource lifetime
- Registered on fresh lock acquire, unregistered on lock release

### Turn-End Cleanup (`cleanup.ts`)

Three call sites (natural turn end, abort during streaming, abort during tools) trigger:
1. **Auto-unhide**: Restores apps hidden by `prepareForAction`, with 5-second timeout
2. **Escape hotkey unregister**: Idempotent, swallows errors
3. **Lock release**: Sends OS notification "Claude is done using your computer"

### Permission Dialog

The `ComputerUseApproval` React component (rendered in terminal via Ink) handles:
- Per-app permission grants with bundle IDs
- Grant flags: clipboard read/write, system key combos
- Display selection and pinning
- Session-scoped state stored in `appState.computerUseMcpState`

## Tool Rendering

`toolRendering.tsx` provides user-friendly display of computer use operations:

| Tool | Display |
|------|---------|
| `screenshot` / `zoom` | "Captured" |
| `left_click` / `right_click` | Coordinates `(x, y)` |
| `type` | Quoted text (truncated to 40 chars) |
| `key` / `hold_key` | Key sequence string |
| `left_click_drag` | `(x1, y1) → (x2, y2)` |
| `scroll` | Direction, amount, position |
| `request_access` | App display names |
| `computer_batch` | Action count |

## Coordinate System

Two modes controlled by the `coordinateMode` gate (frozen at first read to prevent mid-session drift):
- **pixels**: Physical pixel coordinates
- **normalized**: API-defined normalized coordinates

The coordinate mode is baked into tool descriptions at setup time and used consistently by the executor for scaling.

## Sub-Gates

Fine-grained feature toggles within computer use, read from the `tengu_malort_pedway` GrowthBook config:

| Sub-Gate | Default | Purpose |
|----------|---------|---------|
| `pixelValidation` | false | Pre-click pixel comparison to verify target |
| `clipboardPasteMultiline` | true | Use clipboard for multiline typing |
| `mouseAnimation` | true | Animated drag movements |
| `hideBeforeAction` | true | Hide non-target apps before actions |
| `autoTargetDisplay` | true | Auto-select display based on app locations |
| `clipboardGuard` | true | Save/restore clipboard around paste |

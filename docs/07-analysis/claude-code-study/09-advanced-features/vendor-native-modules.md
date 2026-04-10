# Vendor Native Modules

> Deep analysis of Claude Code's four N-API addon modules: audio capture, image processing, URL handling, and keyboard modifier detection.
> Source: `vendor/audio-capture-src/`, `vendor/image-processor-src/`, `vendor/url-handler-src/`, `vendor/modifiers-napi-src/`

---

## Executive Summary

Claude Code ships four native (N-API) addon modules compiled per platform/arch. Each TypeScript wrapper in `vendor/*-src/index.ts` provides a **lazy-load, cache-once, fail-safe** facade over the `.node` binary. The modules cover audio I/O, image processing, macOS URL protocol handling, and keyboard modifier detection. Only **audio-capture** supports all three desktop platforms; the other three are **macOS-only**.

---

## 1. audio-capture-src/index.ts

### Exported API

| Function | Signature | Description |
|----------|-----------|-------------|
| `isNativeAudioAvailable` | `() => boolean` | Checks if native binary loaded successfully |
| `startNativeRecording` | `(onData: (Buffer) => void, onEnd: () => void) => boolean` | Begin mic capture; streams PCM via callback |
| `stopNativeRecording` | `() => void` | Halt active recording |
| `isNativeRecordingActive` | `() => boolean` | Whether mic is currently recording |
| `startNativePlayback` | `(sampleRate: number, channels: number) => boolean` | Open playback stream |
| `writeNativePlaybackData` | `(data: Buffer) => void` | Push audio data to speaker |
| `stopNativePlayback` | `() => void` | Halt playback |
| `isNativePlaying` | `() => boolean` | Whether playback is active |
| `microphoneAuthorizationStatus` | `() => number` | OS mic permission: 0=notDetermined, 1=restricted, 2=denied, 3=authorized |

### Platform Support

| Platform | Supported | Mic Auth Behavior |
|----------|-----------|-------------------|
| **macOS (darwin)** | Yes | TCC status (0/1/2/3) |
| **Linux** | Yes | Always returns 3 (no system API) |
| **Windows (win32)** | Yes | Registry-based: 3=allowed, 2=denied |

### Loading Strategy

**Three-tier fallback with cache-once pattern:**

1. **Env var path** (`AUDIO_CAPTURE_NODE_PATH`): For bun-compile / native-embed builds. The env var is defined at build time in `build-with-plugins.ts` as static literal `../../audio-capture.node` so bun can rewrite to `/$bunfs/root/audio-capture.node`. Must remain a direct `require(env)` -- bun cannot analyze `require(variable)` from a loop.
2. **npm-install layout**: `./vendor/audio-capture/${arch}-${platform}/audio-capture.node`
3. **dev/source layout**: `../audio-capture/${arch}-${platform}/audio-capture.node`

### Error Handling

- `loadAttempted` boolean prevents repeated dlopen attempts after first failure
- Every exported function guards with `if (!mod) return false/void/0`
- `microphoneAuthorizationStatus` returns 0 (notDetermined) when native module unavailable

---

## 2. image-processor-src/index.ts

### Exported API

| Export | Type | Description |
|--------|------|-------------|
| `ClipboardImageResult` | Type | `{ png: Buffer, originalWidth, originalHeight, width, height }` |
| `NativeModule` | Type | `{ processImage, readClipboardImage?, hasClipboardImage? }` |
| `getNativeModule` | `() => NativeModule \| null` | Raw binding accessor for optional exports |
| `sharp` | `(input: Buffer) => SharpInstance` | **Drop-in sharp replacement** -- chainable image pipeline |

### SharpInstance API (Chainable)

| Method | Signature | Description |
|--------|-----------|-------------|
| `metadata` | `() => Promise<{width, height, format}>` | Image dimensions and format |
| `resize` | `(w, h, opts?) => SharpInstance` | Resize with fit/withoutEnlargement options |
| `jpeg` | `(opts?) => SharpInstance` | Convert to JPEG with quality option |
| `png` | `(opts?) => SharpInstance` | Convert to PNG with compression/palette/colors |
| `webp` | `(opts?) => SharpInstance` | Convert to WebP with quality option |
| `toBuffer` | `() => Promise<Buffer>` | Execute pipeline, return result buffer |

### Platform Support

- **All platforms** for core `processImage` / sharp functionality
- **macOS only** for clipboard image functions (optional exports, guarded by callers)
- Binary links against **CoreGraphics/ImageIO** on darwin

### Architecture: Deferred Operation Pipeline

The `sharp()` function implements a **deferred operations pattern**:

1. Operations (`resize`, `jpeg`, `png`, `webp`) are queued in an `operations[]` array
2. Native `processImage()` is not called until `toBuffer()` or `metadata()`
3. `applyPendingOperations()` tracks applied count to avoid re-application
4. This enables the familiar chainable API: `sharp(buf).resize(800,600).jpeg({quality:80}).toBuffer()`

---

## 3. url-handler-src/index.ts

### Exported API

| Function | Signature | Description |
|----------|-----------|-------------|
| `waitForUrlEvent` | `(timeoutMs: number) => string \| null` | Block-wait for macOS Apple Event `kAEGetURL` |

### Platform Support

| Platform | Supported |
|----------|-----------|
| **macOS (darwin)** | Yes |
| **Linux** | No -- returns null |
| **Windows** | No -- returns null |

### Mechanism

Initializes `NSApplication`, registers for the `kAEGetURL` Apple Event, and pumps the macOS event loop for up to `timeoutMs` milliseconds. Used for **custom URL protocol handling** (e.g., `claude://` deep links for OAuth callbacks).

### Loading Strategy

**Two-tier with env var override:**
1. **Bundled mode** (`URL_HANDLER_NODE_PATH` env var): `require(env_path)`
2. **Dev mode**: `../url-handler/${arch}-darwin/url-handler.node`

---

## 4. modifiers-napi-src/index.ts

### Exported API

| Function | Signature | Description |
|----------|-----------|-------------|
| `getModifiers` | `() => string[]` | List currently pressed modifier keys |
| `isModifierPressed` | `(modifier: string) => boolean` | Check if specific modifier is held |
| `prewarm` | `() => void` | Pre-load native module at startup to avoid first-use delay |

### Platform Support

| Platform | Supported |
|----------|-----------|
| **macOS (darwin)** | Yes |
| **Linux** | No -- returns `[]` / `false` |
| **Windows** | No -- returns `[]` / `false` |

### Use Case

Detects keyboard modifier keys (Shift, Ctrl, Option/Alt, Cmd) in real-time. Used for **modifier-aware keyboard shortcuts** -- e.g., detecting if Option is held when pressing Enter to change submission behavior.

---

## Cross-Module Comparison Matrix

| Aspect | audio-capture | image-processor | url-handler | modifiers-napi |
|--------|--------------|-----------------|-------------|----------------|
| **Platforms** | macOS + Linux + Windows | All (clipboard: macOS only) | macOS only | macOS only |
| **Exports** | 9 functions | 3 exports (sharp, getNativeModule, types) | 1 function | 3 functions |
| **Load Pattern** | 3-tier (env -> npm -> dev) | Single require path | 2-tier (env -> dev) | 2-tier (env -> dev) |
| **Env Var** | `AUDIO_CAPTURE_NODE_PATH` | (none) | `URL_HANDLER_NODE_PATH` | `MODIFIERS_NODE_PATH` |
| **Cache Guard** | `loadAttempted` boolean | `loadAttempted` boolean | null-check only | null-check only |
| **Failure Mode** | Silent (returns false/void/0) | `sharp().toBuffer()` throws | Silent (returns null) | Silent (returns []/false) |
| **Binary Name** | `audio-capture.node` | `image-processor.node` | `url-handler.node` | `modifiers.node` |
| **Binary Dir Pattern** | `${arch}-${platform}/` | (flat, relative) | `${arch}-darwin/` | `${arch}-darwin/` |
| **ESM Support** | CommonJS require only | CommonJS require only | `createRequire` from ESM | `createRequire` from ESM |
| **Prewarm** | No | No (lazy critical for startup) | No | Yes (`prewarm()`) |

---

## Architectural Patterns

### 1. Lazy-Load Cache-Once Pattern

All four modules share a common pattern:
```typescript
let cachedModule: T | null = null
function loadModule(): T | null {
  if (cachedModule) return cachedModule
  // platform guard -> try require -> cache -> return
}
```

Two variants exist:
- **`loadAttempted` boolean** (audio-capture, image-processor): Prevents retry even after failure -- one attempt only
- **null-check only** (url-handler, modifiers): Will retry on every call until first success

### 2. Env-Var-First Binary Resolution

Three of four modules (all except image-processor) support a build-time env var that points to the `.node` binary. This enables:
- **bun compile** embedding (binary rewritten into `/$bunfs/root/`)
- **Custom deployment layouts** where binaries aren't at standard relative paths

### 3. Graceful Degradation

No module throws on load failure from the public API (except `sharp().toBuffer()` which is a deliberate "must have native" assertion). Every other function returns a safe default:
- `boolean` -> `false`
- `string | null` -> `null`
- `string[]` -> `[]`
- `number` -> `0`

### 4. Platform Specificity

| Category | Modules | Reason |
|----------|---------|--------|
| **Cross-platform** | audio-capture | Audio I/O is essential for voice mode everywhere |
| **macOS-only** | url-handler, modifiers-napi | Rely on macOS-specific APIs (NSApplication, IOKit/CGEvent) |
| **Mostly cross-platform** | image-processor | Core processing is portable; clipboard uses CoreGraphics |

---

## Key Findings

1. **audio-capture is the most sophisticated**: 3-tier loading, full cross-platform support, 9 exported functions covering both recording and playback, plus per-platform mic permission semantics.

2. **image-processor replaces sharp**: The `sharp()` export is a drop-in replacement for the npm `sharp` package, using a deferred-operation-pipeline pattern. This eliminates the heavy `sharp` native dependency while providing identical API surface.

3. **url-handler enables OAuth deep links**: The `waitForUrlEvent` function pumps the macOS event loop to catch `claude://` protocol URLs, critical for OAuth callback flows without requiring a local HTTP server.

4. **modifiers-napi enables modifier-aware shortcuts**: The only module with a `prewarm()` function, indicating it is performance-sensitive for real-time keyboard detection during terminal input.

5. **Inconsistent ESM handling**: audio-capture and image-processor use bare `require()`, while url-handler and modifiers-napi use `createRequire(import.meta.url)` -- reflecting different authorship timelines or bundler compatibility needs.

6. **No Windows/Linux support for 3 of 4 modules**: url-handler, modifiers-napi, and image-processor clipboard features are darwin-only. This means Claude Code on Windows/Linux lacks URL protocol handling, modifier key detection, and clipboard image paste.

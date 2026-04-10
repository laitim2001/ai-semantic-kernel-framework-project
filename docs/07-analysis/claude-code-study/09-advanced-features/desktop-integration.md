# Desktop Integration

> Claude Code integrates with the desktop environment through deep links, Chrome extension bridge, mobile companion, native installer, buddy companion, and platform-specific protocol handlers.

## Overview

Desktop integration spans multiple subsystems that extend Claude Code beyond the terminal: a custom URI scheme for web-to-CLI handoff, a Chrome extension bridge for browser control, a mobile companion QR code flow, an animated buddy companion, and a native installer with auto-update. Together these create a cohesive cross-platform experience.

**Key source directories and files:**

| Path | Purpose |
|------|---------|
| `src/utils/deepLink/` | `claude-cli://` protocol handler registration and parsing |
| `src/utils/claudeInChrome/` | Chrome extension MCP bridge |
| `src/commands/desktop/` | `/desktop` command — desktop app handoff |
| `src/commands/chrome/` | `/chrome` command — extension management |
| `src/commands/mobile/` | `/mobile` command — QR code for mobile apps |
| `src/utils/nativeInstaller/` | Native binary installer with symlinks and auto-update |
| `src/buddy/` | Animated companion creature (collectible, seeded PRNG) |
| `vendor/url-handler-src/` | macOS NAPI module for Apple Event URL handling |
| `vendor/image-processor-src/` | Image processing NAPI module |

## Deep Link System (`src/utils/deepLink/`)

### URI Scheme

Claude Code registers the `claude-cli://` custom URI scheme with the OS, enabling web-to-CLI handoff:

```
claude-cli://open?q=fix+tests&repo=owner/repo&cwd=/path/to/project
```

**Parameters (all optional):**
| Param | Purpose | Limits |
|-------|---------|--------|
| `q` | Pre-fill prompt (not auto-submitted) | Max 5000 chars |
| `cwd` | Working directory (absolute path) | Max 4096 chars |
| `repo` | GitHub `owner/name` slug | Must match `/^[\w.-]+\/[\w.-]+$/` |

### Security Measures (`parseDeepLink.ts`)

Deep links are a significant injection surface. The parser applies multiple defenses:

1. **ASCII control character rejection**: Newlines, carriage returns, and other control chars (0x00-0x1F, 0x7F) are blocked — they can act as command separators
2. **Unicode sanitization**: `partiallySanitizeUnicode()` strips hidden Unicode characters (ASCII smuggling / hidden prompt injection)
3. **Repo slug validation**: Regex-constrained to prevent path traversal
4. **Length limits**: Query 5000 chars (Windows cmd.exe 8191-char limit), CWD 4096 chars (PATH_MAX)
5. **Shell escaping**: Single-quote escaping at point of use in `terminalLauncher.ts`
6. **No auto-submit**: Prefilled prompts require explicit user confirmation

### Protocol Handler Registration (`registerProtocol.ts`)

Cross-platform OS integration:

**macOS:**
- Creates a minimal `.app` trampoline at `~/Applications/Claude Code URL Handler.app`
- `Info.plist` with `CFBundleURLTypes` registering the `claude-cli` scheme
- `CFBundleExecutable` is a **symlink** to the installed `claude` binary (avoids signing a separate executable)
- Re-registers with LaunchServices via `lsregister`

**Linux:**
- Creates `.desktop` file at `$XDG_DATA_HOME/applications/claude-code-url-handler.desktop`
- Registers with `xdg-mime default` for `x-scheme-handler/claude-cli`
- Graceful fallback when `xdg-utils` is missing (WSL, Docker, CI)

**Windows:**
- Writes registry keys under `HKEY_CURRENT_USER\Software\Classes\claude-cli`
- Sets `URL Protocol` value and `shell\open\command` default value
- Uses `reg add` with `/f` force flag

### Auto-Registration

`ensureDeepLinkProtocolRegistered()` runs every session from background housekeeping:
- Reads the OS artifact directly (symlink target, .desktop Exec line, registry value) — no cached flag
- Self-heals stale paths (install method change, deleted artifacts)
- 24-hour backoff on deterministic failures (EACCES, ENOSPC)
- Controlled by `tengu_lodestone_enabled` GrowthBook flag

### Protocol Handler Flow (`protocolHandler.ts`)

When the OS invokes `claude --handle-uri <url>`:

1. Parse URI via `parseDeepLink()`
2. Resolve working directory: explicit `cwd` > repo MRU lookup > `$HOME`
3. Compute FETCH_HEAD age for git freshness display
4. Launch a new terminal window via `launchInTerminal()`

**macOS URL Scheme Launch:**
```typescript
export async function handleUrlSchemeLaunch(): Promise<number | null> {
  if (process.env.__CFBundleIdentifier !== MACOS_BUNDLE_ID) return null
  const { waitForUrlEvent } = await import('url-handler-napi')
  const url = waitForUrlEvent(5000)
  if (!url) return null
  return await handleDeepLinkUri(url)
}
```

The `url-handler-napi` module (`vendor/url-handler-src/`) uses Objective-C to initialize NSApplication, register for `kAEGetURL` Apple Events, and pump the event loop for up to 5 seconds.

## Chrome Extension Bridge (`src/utils/claudeInChrome/`)

### Architecture

Claude Code communicates with a Chrome extension via a native messaging host, exposed as an MCP server:

```
Chrome Extension ←→ Native Messaging Host ←→ Unix Socket/Named Pipe ←→ Claude Code MCP Client
```

### Multi-Browser Support (`common.ts`)

The system supports 7 Chromium-based browsers with per-browser configuration:

| Browser | macOS | Linux | Windows |
|---------|-------|-------|---------|
| Chrome | `com.google.iterm2` | `google-chrome` | `Google\Chrome\User Data` |
| Brave | `Brave Browser.app` | `brave-browser` | `BraveSoftware\Brave-Browser` |
| Arc | `Arc.app` | N/A | `Arc\User Data` |
| Edge | `Microsoft Edge.app` | `microsoft-edge` | `Microsoft\Edge\User Data` |
| Chromium | `Chromium.app` | `chromium` | `Chromium\User Data` |
| Vivaldi | `Vivaldi.app` | `vivaldi` | `Vivaldi\User Data` |
| Opera | `com.operasoftware.Opera` | `opera` | `Opera Software\Opera Stable` (Roaming) |

Each browser has configured paths for:
- **Data path**: Extension installation detection
- **Native messaging path**: Host manifest location (macOS/Linux)
- **Registry key**: Native messaging registration (Windows)

### Browser Detection

`detectAvailableBrowser()` checks browsers in priority order (Chrome first), using platform-specific probes:
- macOS: Check `/Applications/${appName}.app` directory exists
- Linux: `which` for binary names
- Windows: Check `AppData\Local` (or `Roaming` for Opera) data path

### Socket Communication

IPC between the native messaging host and Claude Code:

```typescript
// Unix: per-process socket files
export function getSecureSocketPath(): string {
  return join(getSocketDir(), `${process.pid}.sock`)
}

// Windows: named pipes
export function getSecureSocketPath(): string {
  return `\\\\.\\pipe\\claude-mcp-browser-bridge-${getUsername()}`
}
```

Socket discovery scans `*.sock` files in the socket directory plus legacy fallback paths.

### `/chrome` Command

The `/chrome` command (`src/commands/chrome/chrome.tsx`) provides a React (Ink) menu:
- **Install extension**: Opens Chrome extension store URL
- **Reconnect**: Re-detects extension installation
- **Manage permissions**: Opens permissions page
- **Toggle default**: Enable/disable Chrome integration by default

### Tab Tracking

A bounded set tracks active Chrome tab IDs (max 200, clears on overflow):
```typescript
const MAX_TRACKED_TABS = 200
const trackedTabIds = new Set<number>()
```

## Desktop App Handoff (`src/commands/desktop/`)

The `/desktop` command renders a `DesktopHandoff` React component that facilitates transitioning from the CLI to the desktop application (Cowork).

## Mobile Companion (`src/commands/mobile/`)

The `/mobile` command generates QR codes for downloading the Claude mobile app:

```typescript
const PLATFORMS: Record<Platform, { url: string }> = {
  ios: { url: 'https://apps.apple.com/app/claude-by-anthropic/id6473753684' },
  android: { url: 'https://play.google.com/store/apps/details?id=com.anthropic.claude' }
}
```

- Uses `qrcode` library to generate UTF-8 terminal QR codes
- Tab key toggles between iOS and Android
- Both QR codes are generated in parallel at mount time

## Native Installer (`src/utils/nativeInstaller/`)

### Architecture

The native installer manages a directory-based installation with symlinks and version retention:

```
~/.local/share/claude-code/
├── versions/
│   ├── 1.2.3/          # installed version directories
│   └── 1.2.4/
├── current -> versions/1.2.4   # symlink to active version
└── claude-code.lock    # file-based lock

~/.local/bin/
└── claude -> ~/.local/share/claude-code/current/bin/claude   # stable symlink
```

### Key Features

- **Version retention**: Keeps `VERSION_RETENTION_COUNT = 2` versions for rollback
- **Multi-process safety**: PID-based locking with stale detection (7-day timeout for laptop sleep)
- **Platform detection**: `${os}-${arch}` (e.g., `linux-x64`, `darwin-arm64`)
- **Auto-update**: `downloadVersion()` + `getLatestVersion()` from CDN
- **Shell integration**: Updates shell config files (`.bashrc`, `.zshrc`) for PATH
- **Alias cleanup**: `filterClaudeAliases()` removes stale aliases from shell configs

### Lock System (`pidLock.ts`)

File-based locking with PID liveness checks:
- `acquireProcessLifetimeLock()`: Creates lock with PID file
- `isLockActive()`: Validates PID is still running
- `cleanupStaleLocks()`: Removes locks from dead processes
- 7-day mtime-based stale timeout (survives laptop sleep)

## Buddy Companion (`src/buddy/`)

### Overview

An animated ASCII companion creature that lives in the terminal. Each user gets a deterministic companion based on their user ID, with collectible rarity tiers.

### Species and Traits

**18 Species:** duck, goose, blob, cat, dragon, octopus, owl, penguin, turtle, snail, ghost, axolotl, capybara, cactus, robot, rabbit, mushroom, chonk

**6 Eye styles:** `·`, `✦`, `×`, `◉`, `@`, `°`

**8 Hats:** none, crown, tophat, propeller, halo, wizard, beanie, tinyduck (common rarity gets no hat)

### Rarity System

```typescript
export const RARITY_WEIGHTS = {
  common: 60, uncommon: 25, rare: 10, epic: 4, legendary: 1
} as const

export const RARITY_STARS = {
  common: '★', uncommon: '★★', rare: '★★★', epic: '★★★★', legendary: '★★★★★'
}
```

### Deterministic Generation (`companion.ts`)

Companions are seeded from `hash(userId + 'friend-2026-401')` using Mulberry32 PRNG:

```typescript
function mulberry32(seed: number): () => number {
  let a = seed >>> 0
  return function () {
    a |= 0; a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}
```

- **Bones** (deterministic): rarity, species, eye, hat, shiny (1% chance), stats
- **Soul** (model-generated): name, personality — stored in config after first hatch
- **Stats**: DEBUGGING, PATIENCE, CHAOS, WISDOM, SNARK — one peak, one dump, rest scattered, floor based on rarity

### Sprite Animation

ASCII art sprites are 5 lines tall, 12 wide, with 3 frames per species for idle fidget animation. Line 0 is the hat slot. The `CompanionSprite.tsx` React component renders the animated companion with a `useBuddyNotification` hook for event reactions.

### Anti-Cheat

Bones are never persisted — they're regenerated from `hash(userId)` on every read. Users cannot edit config to fake a rarity; the stored config only contains `{ name, personality, hatchedAt }`.

## URL Handler NAPI Module (`vendor/url-handler-src/`)

macOS-only native module for receiving Apple Events:

```typescript
type UrlHandlerNapi = {
  waitForUrlEvent(timeoutMs: number): string | null
}
```

- Initializes `NSApplication` for URL event registration
- Pumps the macOS event loop for up to `timeoutMs`
- Returns the URL string from `kAEGetURL` Apple Event, or null on timeout
- Only loads on `darwin` platform

## Image Processor NAPI Module (`vendor/image-processor-src/`)

A native image processing module (sharp-compatible, async-only) used for:
- Computer use pixel validation (JPEG decode + crop)
- Image resizing for API submission
- The module is async-only, which is why `hostAdapter.ts` returns `null` from `cropRawPatch()` (the package expects synchronous returns)

## Cross-Platform Considerations

| Feature | macOS | Linux | Windows |
|---------|-------|-------|---------|
| Deep links | .app bundle + LaunchServices | .desktop + xdg-mime | Registry keys |
| Chrome bridge | Unix sockets | Unix sockets | Named pipes |
| URL handler | NAPI Apple Events | N/A | N/A |
| Computer use | Full support | N/A | N/A |
| Voice input | CoreAudio | ALSA/PulseAudio | WASAPI |
| Native installer | Full | Full | Full |
| Buddy | Terminal ASCII | Terminal ASCII | Terminal ASCII |

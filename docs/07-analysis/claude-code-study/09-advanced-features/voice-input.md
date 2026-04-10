# Voice Input Implementation

> Claude Code supports voice input through native audio capture and server-side speech-to-text, enabling hands-free interaction with the CLI.

## Overview

Voice mode allows users to dictate prompts instead of typing them. The feature integrates native audio capture (platform-specific NAPI modules for macOS, Linux, and Windows) with Anthropic's `voice_stream` endpoint for real-time speech-to-text transcription. It is toggled via the `/voice` command and gated behind Anthropic OAuth authentication plus a GrowthBook kill-switch.

**Key source files:**

| File | Purpose |
|------|---------|
| `src/voice/voiceModeEnabled.ts` | Feature gating: auth check + GrowthBook kill-switch |
| `src/commands/voice/voice.ts` | `/voice` command: toggle on/off with pre-flight checks |
| `src/commands/voice/index.ts` | Command registration |
| `vendor/audio-capture-src/index.ts` | Native audio NAPI module loader + API |
| `src/hooks/useVoice.js` | React hook for voice state management |
| `src/services/voiceStreamSTT.js` | Voice stream STT service (claude.ai endpoint) |
| `src/services/voice.js` | Recording availability checks |

## Architecture

```
User speaks into microphone
    ↓
Native Audio Capture (NAPI — Rust/C++)
    ↓ raw PCM data buffers
Voice Stream Client (voiceStreamSTT.js)
    ↓ WebSocket / streaming
claude.ai voice_stream endpoint
    ↓ transcribed text
Prompt Input (pre-filled, not auto-submitted)
```

## Feature Gating

Voice mode uses a three-layer gate defined in `src/voice/voiceModeEnabled.ts`:

### 1. GrowthBook Kill-Switch

```typescript
export function isVoiceGrowthBookEnabled(): boolean {
  return feature('VOICE_MODE')
    ? !getFeatureValue_CACHED_MAY_BE_STALE('tengu_amber_quartz_disabled', false)
    : false
}
```

- Flag name: `tengu_amber_quartz_disabled`
- Default `false` means fresh installs get voice working immediately without waiting for GrowthBook init
- The `feature('VOICE_MODE')` compile-time gate ensures the code tree-shakes from non-voice builds

### 2. Authentication Check

```typescript
export function hasVoiceAuth(): boolean {
  if (!isAnthropicAuthEnabled()) return false
  const tokens = getClaudeAIOAuthTokens()
  return Boolean(tokens?.accessToken)
}
```

Voice mode requires:
- Anthropic OAuth authentication (not API keys, Bedrock, Vertex, or Foundry)
- A valid access token (not just the auth provider being configured)
- The memoized `getClaudeAIOAuthTokens()` caches keychain lookups (~20-50ms first call)

### 3. Combined Runtime Check

```typescript
export function isVoiceModeEnabled(): boolean {
  return hasVoiceAuth() && isVoiceGrowthBookEnabled()
}
```

This full check is used at command-time paths (`/voice`, `ConfigTool`, `VoiceModeNotice`). React render paths use a memoized `useVoiceEnabled()` hook instead.

## Native Audio Capture

### NAPI Module (`vendor/audio-capture-src/index.ts`)

The audio capture system is a platform-native NAPI addon (Rust/C++ compiled to `.node` binary) with the following API:

```typescript
type AudioCaptureNapi = {
  startRecording(onData: (data: Buffer) => void, onEnd: () => void): boolean
  stopRecording(): void
  isRecording(): boolean
  startPlayback(sampleRate: number, channels: number): boolean
  writePlaybackData(data: Buffer): void
  stopPlayback(): void
  isPlaying(): boolean
  microphoneAuthorizationStatus?(): number  // macOS TCC status
}
```

### Platform Support

| Platform | Recording | Playback | Mic Permission Check |
|----------|-----------|----------|---------------------|
| macOS | Native (CoreAudio) | Native | TCC: 0=notDetermined, 1=restricted, 2=denied, 3=authorized |
| Linux | Native (ALSA/PulseAudio) | Native | Always returns 3 (no system-level mic API) |
| Windows | Native (WASAPI) | Native | Registry-based: 3=authorized/absent, 2=denied |

### Module Loading Strategy

The loader uses a three-tier fallback:

1. **Bun-bundled path**: `AUDIO_CAPTURE_NODE_PATH` env var (set at build time by `build-with-plugins.ts`, resolves to `/$bunfs/root/audio-capture.node`)
2. **npm-install layout**: `./vendor/audio-capture/${arch}-${platform}/audio-capture.node`
3. **Dev/source layout**: `../audio-capture/${arch}-${platform}/audio-capture.node`

```typescript
function loadModule(): AudioCaptureNapi | null {
  if (loadAttempted) return cachedModule  // singleton cache
  loadAttempted = true
  
  if (process.env.AUDIO_CAPTURE_NODE_PATH) { /* bundled path */ }
  // fallback to runtime discovery
  const platformDir = `${process.arch}-${platform}`
  const fallbacks = [
    `./vendor/audio-capture/${platformDir}/audio-capture.node`,
    `../audio-capture/${platformDir}/audio-capture.node`,
  ]
}
```

### Audio Data Flow

The recording API uses a callback-based streaming pattern:

```typescript
export function startNativeRecording(
  onData: (data: Buffer) => void,  // raw PCM chunks
  onEnd: () => void,               // recording stopped (external event)
): boolean
```

- `onData` receives raw PCM audio buffers as they are captured
- `onEnd` fires when recording stops (e.g., device disconnected)
- Returns `false` if the native module is unavailable or recording fails to start

### Playback Support

The module also supports audio playback (for potential TTS or audio feedback):

```typescript
startNativePlayback(sampleRate: number, channels: number): boolean
writeNativePlaybackData(data: Buffer): void
stopNativePlayback(): void
isNativePlaying(): boolean
```

## `/voice` Command

### Toggle Logic (`src/commands/voice/voice.ts`)

The `/voice` command toggles voice mode on or off:

**Toggle OFF** (simple path):
- Update user settings: `voiceEnabled: false`
- Notify settings change detector
- Log analytics event

**Toggle ON** (with pre-flight checks):
1. Check `isVoiceModeEnabled()` — auth + kill-switch
2. Check recording availability (`checkRecordingAvailability()`) — microphone access
3. Check voice stream API availability (`isVoiceStreamAvailable()`)
4. Update user settings: `voiceEnabled: true`
5. Show language configuration hint (limited to `LANG_HINT_MAX_SHOWS = 2` times)

### Error Messages

| Condition | Message |
|-----------|---------|
| No Anthropic OAuth | "Voice mode requires a Claude.ai account. Please run /login to sign in." |
| Kill-switch active | "Voice mode is not available." |
| Mic unavailable | Dynamic reason from `checkRecordingAvailability()` |
| No API access | "Voice mode requires a Claude.ai account." |
| Settings write fail | "Failed to update settings. Check your settings file for syntax errors." |

## Speech-to-Text Integration

### Voice Stream Service

The `voiceStreamSTT.js` service connects to Anthropic's `voice_stream` endpoint on claude.ai:

- Uses the OAuth access token for authentication
- Streams raw audio data from the native capture module
- Receives transcribed text in real-time
- Language normalization via `normalizeLanguageForSTT()` from `useVoice` hook

### Configuration

Voice settings are stored in the user settings file:

- `voiceEnabled`: boolean toggle
- `voiceLanguage`: optional language code for STT (shown as a configuration hint on first enable)
- Settings are persisted via `updateSettingsForSource('userSettings', ...)` and detected by `settingsChangeDetector`

## React Integration

### `useVoice` Hook

The voice mode integrates with the React (Ink) UI through a custom hook:

- Manages recording state (idle, recording, processing)
- Handles keybinding for voice toggle (display via `getShortcutDisplay()`)
- Normalizes language codes for STT via `normalizeLanguageForSTT()`
- Memoizes auth checks to avoid per-render keychain lookups

### UI Flow

1. User presses voice keybinding or runs `/voice`
2. Recording indicator appears in the prompt area
3. Audio is captured and streamed to the STT endpoint
4. Transcribed text is inserted into the prompt input
5. User reviews and submits (voice never auto-submits)

## Security Considerations

1. **Auth-gated**: Only Anthropic OAuth users can access voice (prevents unauthorized API usage)
2. **Kill-switch**: GrowthBook flag allows emergency disable without code deployment
3. **Permission checks**: Native microphone permission verified before recording starts
4. **No auto-submit**: Transcribed text is pre-filled for review, not auto-executed
5. **Token memoization**: OAuth token lookups are cached to avoid repeated keychain access during render cycles, with cache clearing on token refresh (~once/hour)

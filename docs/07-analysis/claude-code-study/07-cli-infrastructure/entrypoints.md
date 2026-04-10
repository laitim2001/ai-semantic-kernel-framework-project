# CLI Entry Points and Bootstrap

> Source: `src/entrypoints/cli.tsx`, `src/entrypoints/init.ts`, `src/main.tsx`, `src/cli/`

## Overview

Claude Code has a single primary entry point (`src/entrypoints/cli.tsx`) with aggressive fast-path routing to minimize module loading. All imports are dynamic to reduce startup cost.

## Entry Point Files

| File | Purpose |
|------|---------|
| `src/entrypoints/cli.tsx` | Primary CLI entry — bootstrap, fast paths |
| `src/entrypoints/init.ts` | One-time initialization (memoized) |
| `src/entrypoints/mcp.ts` | MCP server mode entry |
| `src/entrypoints/sdk/coreTypes.ts` | SDK public types |
| `src/entrypoints/sdk/coreSchemas.ts` | SDK Zod schemas |
| `src/entrypoints/sdk/controlSchemas.ts` | SDK control message schemas |
| `src/entrypoints/agentSdkTypes.ts` | Agent SDK type definitions |
| `src/entrypoints/sandboxTypes.ts` | Sandbox type definitions |
| `src/bootstrap/state.ts` | Global process state singleton |

## cli.tsx Bootstrap Sequence

### Phase 1: Top-Level Side Effects (before async main)

Synchronous side effects at module load:
1. **Corepack pin suppression**: `COREPACK_ENABLE_AUTO_PIN = '0'`
2. **Remote heap expansion**: `--max-old-space-size=8192` for CCR containers (16GB)
3. **Ablation baseline** (feature-gated): Sets `CLAUDE_CODE_SIMPLE`, `DISABLE_THINKING`, etc. before module-level constants capture them

### Phase 2: Fast Paths (zero/minimal imports)

| Condition | Path | Module Cost |
|-----------|------|-------------|
| `--version` / `-v` | Print `MACRO.VERSION`, exit | Zero imports |
| `--dump-system-prompt` | Print system prompt, exit | Light (ant-only) |
| `--claude-in-chrome-mcp` | Run Chrome MCP server | Separate stack |
| `--chrome-native-host` | Run Chrome native host | Separate stack |
| `--computer-use-mcp` | Run computer use MCP | Feature-gated |
| `--daemon-worker=<kind>` | Run daemon worker | Lean (no analytics) |
| `remote-control` / `rc` / `bridge` | Bridge mode | Full stack + auth |
| `daemon` | Daemon supervisor | Full stack |

### Phase 3: Main CLI Load

After fast paths: `profileCheckpoint('cli_entry')` → `enableConfigs()` → argument parsing → Ink render loop → `initBundledSkills()`.

## init.ts Initialization

`src/entrypoints/init.ts` runs once (memoized):
1. Graceful shutdown handler registration
2. Config file loading
3. SSL/TLS certificate configuration
4. Windows shell detection
5. MDM settings loading
6. Proxy configuration
7. JetBrains IDE detection
8. OAuth account info prefetch
9. Policy limits initialization
10. API pre-connection (DNS warmup)
11. Telemetry initialization (lazy — defers 400KB OpenTelemetry)

## Bootstrap State (`src/bootstrap/state.ts`)

Global singleton — comment: "DO NOT ADD MORE STATE HERE — BE JUDICIOUS WITH GLOBAL STATE"

Key state: `sessionId`, `originalCwd`, `projectRoot`, `totalCostUSD`, `totalAPIDuration`, `totalToolDuration`, model settings, telemetry providers, hook registries.

## Transport Layer (`src/cli/transports/`)

| Transport | Protocol | Use Case |
|-----------|----------|----------|
| `SSETransport.ts` | Server-Sent Events | CCR v2 ingress reads |
| `WebSocketTransport.ts` | WebSocket | Session-Ingress v1 |
| `HybridTransport.ts` | WS reads + HTTP POST writes | Bridge v1 |
| `ccrClient.ts` | CCR v2 API | Bridge v2 writes via `/worker/*` |
| `SerialBatchEventUploader.ts` | Batched HTTP POST | Event upload with retry |

## CLI Handlers (`src/cli/handlers/`)

| Handler | Subcommand |
|---------|-----------|
| `auth.ts` | `/login`, `/logout`, token management |
| `agents.ts` | `claude agents` — agent management |
| `mcp.tsx` | `claude mcp` — MCP server management |
| `plugins.ts` | `claude plugins` — plugin management |
| `print.ts` | Non-interactive stdout writer |
| `structuredIO.ts` | JSON/NDJSON output mode |
| `exit.ts` | Clean exit with analytics flush |

## SDK Entry Points (`src/entrypoints/sdk/`)

- `coreTypes.ts` — `SDKMessage`, `AssistantResponse`, `ToolUse`, `ToolResult`
- `coreSchemas.ts` — Zod runtime validation
- `controlSchemas.ts` — `SDKControlRequest`, `SDKControlResponse`, `StdoutMessage`

## Process Lifecycle

```
1. cli.tsx module load (side effects)
2. main() → fast path check
3. profileCheckpoint('cli_entry')
4. Dynamic imports for selected path
5. enableConfigs() → .env, settings
6. Auth/policy checks (if bridge)
7. Full CLI or subcommand handler
8. Ink render loop (interactive) OR stdout writer (non-interactive)
9. exit.ts → flush analytics, cleanup
```

# Sandbox

> Analysis of Claude Code's sandbox model, network/filesystem restrictions, settings integration, and sandbox toggling.

## Overview

Claude Code's sandbox system restricts the execution environment of shell commands and tool operations. It uses the `@anthropic-ai/sandbox-runtime` package as its foundation, wrapped with Claude CLI-specific integrations for settings, permissions, and tool awareness. The sandbox controls filesystem access (read/write), network connectivity, and process execution.

**Key source files:**
- `src/utils/sandbox/sandbox-adapter.ts` — Adapter wrapping `@anthropic-ai/sandbox-runtime`
- `src/utils/sandbox/sandbox-ui-utils.ts` — UI utilities for sandbox status
- `src/components/sandbox/` — Sandbox UI components
- `src/commands/sandbox-toggle/` — Sandbox enable/disable command
- `src/tools/BashTool/shouldUseSandbox.ts` — Per-command sandbox decision

---

## Architecture

### Layered Design

```
Claude Code Settings (user/project/policy)
         │
         ▼
   sandbox-adapter.ts  ←── Claude CLI-specific path resolution, violation handling
         │
         ▼
   @anthropic-ai/sandbox-runtime  ←── Core sandbox enforcement
         │
         ▼
   OS-level sandboxing (macOS sandbox-exec, Linux seccomp, etc.)
```

### SandboxManager

The `SandboxManager` (extended from `BaseSandboxManager` in the runtime package) is the central coordinator. The adapter in `src/utils/sandbox/sandbox-adapter.ts` wraps it with:

1. **Settings conversion** — Translates Claude Code's permission rules into `SandboxRuntimeConfig`
2. **Path resolution** — Resolves Claude Code-specific path patterns for the sandbox
3. **Violation handling** — Processes and reports sandbox violations
4. **Dependency checking** — Verifies sandbox runtime dependencies are available

---

## Configuration Model

### SandboxRuntimeConfig

The sandbox is configured via `SandboxRuntimeConfig` from the runtime package, which includes:

```typescript
type SandboxRuntimeConfig = {
  fs_read?: FsReadRestrictionConfig     // Filesystem read restrictions
  fs_write?: FsWriteRestrictionConfig   // Filesystem write restrictions
  network?: NetworkRestrictionConfig     // Network access restrictions
  ignore_violations?: IgnoreViolationsConfig  // Violations to suppress
}
```

### Settings Sources

Sandbox configuration cascades from multiple settings sources (in priority order):
1. **policySettings** — Organization-managed policies (highest priority)
2. **flagSettings** — Feature flag overrides
3. **projectSettings** — Per-project `.claude/settings.json`
4. **userSettings** — User-level `~/.claude/settings.json`

### Path Pattern Resolution

`resolvePathPatternForSandbox()` handles Claude Code-specific path conventions:

| Pattern | Meaning | Resolution |
|---------|---------|------------|
| `//path` | Absolute from filesystem root | Becomes `/path` |
| `/path` | Relative to settings file directory | Becomes `$SETTINGS_DIR/path` |
| `~/path` | User home relative | Passed through to sandbox-runtime |
| `./path` or `path` | CWD-relative | Passed through to sandbox-runtime |

This resolution happens per-source, so `/scripts` in a project settings file resolves relative to the project root, while `/scripts` in user settings resolves relative to `~/.claude/`.

---

## Filesystem Restrictions

### Read Restrictions

Control which files/directories the sandbox allows reading:

- **Allowed paths** — Explicitly permitted read locations
- **Internal paths** — Claude config directories auto-allowed
- **Project paths** — CWD and project root auto-allowed
- **Additional directories** — CLAUDE.md hierarchy directories

Auto-allowed paths include:
- Current working directory and its parents (for git root detection)
- Claude config home (`~/.claude/`)
- Project temp directory
- Ripgrep binary location

### Write Restrictions

Control which files/directories can be modified:

- **Allowed paths** — Explicitly permitted write locations
- **Project scope** — Typically restricted to CWD
- **Temp directories** — Claude temp and sandbox temp dirs

### Permission Rule Integration

The sandbox adapter reads Claude Code's permission rules and converts them:

```typescript
// Claude Code permission rule
"Bash(npm install *)"

// Converted to sandbox-runtime rule
{ toolName: 'Bash', ruleContent: 'npm install *' }
```

Tool-specific permissions (e.g., `FileWrite(/path/*)`, `Bash(git push *)`) are parsed and their filesystem implications are extracted for sandbox configuration.

---

## Network Restrictions

### NetworkRestrictionConfig

Controls outbound network access:

```typescript
type NetworkRestrictionConfig = {
  allow_patterns?: NetworkHostPattern[]   // Allowed host patterns
  deny_patterns?: NetworkHostPattern[]    // Blocked host patterns
}
```

### Default Behavior

- By default, the sandbox blocks most outbound network connections
- API endpoints (Anthropic, OAuth providers) are always allowed
- MCP server connections are allowed based on configured server addresses
- Users can add additional allowed hosts via settings

---

## Sandbox Toggle

### Command: `/sandbox-toggle`

`src/commands/sandbox-toggle/` provides a user command to enable/disable sandboxing:

- Interactive toggle in the REPL
- Updates the sandbox state in AppState
- Takes effect for subsequent commands (not retroactive)

### Per-Command Decision

`src/tools/BashTool/shouldUseSandbox.ts` determines whether to sandbox each individual command:

- Checks global sandbox enable/disable state
- May skip sandboxing for certain trusted commands
- Considers the command's permission classification

---

## Violation Handling

### Violation Events

When a sandbox violation occurs, a `SandboxViolationEvent` is generated:

```typescript
type SandboxViolationEvent = {
  type: string          // Violation type (fs_read, fs_write, network, etc.)
  path?: string         // Affected path
  host?: string         // Affected host (network violations)
  tool?: string         // Tool that triggered the violation
  timestamp: number     // When the violation occurred
}
```

### Violation Store

`SandboxViolationStore` (from the runtime package) accumulates violations for:
- **User notification** — Violations surface in the UI
- **Analytics** — Violation patterns are tracked
- **Debugging** — Full violation log available for troubleshooting

### Violation Suppression

`IgnoreViolationsConfig` allows suppressing known-safe violations:
- Certain system paths that trigger spurious violations
- OS-specific paths that are safe but technically out of sandbox scope

---

## Sandbox UI

### Status Display

`src/utils/sandbox/sandbox-ui-utils.ts` provides utilities for displaying sandbox status:
- Current sandbox state (enabled/disabled)
- Active restrictions summary
- Recent violation count

### Components

`src/components/sandbox/` provides React/Ink components for:
- Sandbox status indicator in the footer
- Violation notifications
- Sandbox toggle confirmation dialogs

---

## Dependency Checking

### SandboxDependencyCheck

The adapter performs dependency checks at startup:

```typescript
type SandboxDependencyCheck = {
  available: boolean        // Whether sandbox can run
  reason?: string          // Why it's unavailable
  platform: string         // Current platform
}
```

Platform support:
- **macOS** — Full support via `sandbox-exec`
- **Linux** — Support via seccomp/AppArmor where available
- **Windows** — Limited support

### Ask Callback

`SandboxAskCallback` provides a mechanism for the sandbox to request user confirmation:
- Used when a command would violate the sandbox
- Allows the user to grant a one-time exception
- Integrates with the permission prompt system

---

## Key Design Patterns

1. **External package wrapping** — Core enforcement in `@anthropic-ai/sandbox-runtime`, CLI-specific integration in adapter
2. **Multi-source settings** — Sandbox config cascades from policy through user settings with clear priority
3. **Path convention handling** — Claude Code-specific path patterns resolved before passing to runtime
4. **Per-command decisions** — Each command individually evaluated for sandboxing
5. **Violation accumulation** — Violations tracked for user notification, analytics, and debugging
6. **Settings change detection** — `settingsChangeDetector` triggers sandbox reconfiguration on settings changes
7. **Platform adaptation** — Graceful degradation on platforms with limited sandbox support

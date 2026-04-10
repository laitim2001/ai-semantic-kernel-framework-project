# Migrations, Schemas, OutputStyles & MoreRight

> Deep analysis of startup data migrations, shared hook schemas, output style loading, and the internal/external build stub.
> Source: `src/migrations/` (11 files), `src/schemas/` (1 file), `src/outputStyles/` (1 file), `src/moreright/` (1 file)

---

## 1. migrations/ Module (11 files, ~530 LOC)

### Purpose

The migrations module handles **one-shot data migrations** that run at application startup in `main.tsx`. Each migration transforms legacy config/settings keys into their current equivalents, ensuring backward compatibility as Claude Code evolves. They follow a consistent pattern: check precondition, transform data, clean up old key, log analytics event.

All 11 migrations are imported and called sequentially in `main.tsx` (lines 323-341), with a `@[MODEL LAUNCH]` comment reminding developers to consider new model-string migrations on each release.

### File Inventory

#### 1.1 migrateAutoUpdatesToSettings.ts
- **Purpose**: Moves user-set `autoUpdates: false` preference from GlobalConfig (`~/.claude.json`) to `settings.json` as `env.DISABLE_AUTOUPDATER=1`.
- **Guard**: Skips if `autoUpdates !== false` or if it was set automatically for native protection (`autoUpdatesProtectedForNative`).
- **Side effect**: Sets `process.env.DISABLE_AUTOUPDATER = '1'` for immediate effect.
- **Cleanup**: Removes `autoUpdates` and `autoUpdatesProtectedForNative` from GlobalConfig.

#### 1.2 migrateBypassPermissionsAcceptedToSettings.ts
- **Purpose**: Moves `bypassPermissionsModeAccepted` from GlobalConfig to `settings.json` as `skipDangerousModePermissionPrompt: true`.
- **Guard**: Skips if `bypassPermissionsModeAccepted` is falsy in GlobalConfig.
- **Idempotent**: Checks `hasSkipDangerousModePermissionPrompt()` before writing.

#### 1.3 migrateEnableAllProjectMcpServersToSettings.ts
- **Purpose**: Moves three MCP server approval fields from project config to local settings:
  - `enableAllProjectMcpServers` (boolean)
  - `enabledMcpjsonServers` (string array, merged with dedup via `Set`)
  - `disabledMcpjsonServers` (string array, merged with dedup)
- **Target**: Writes to `localSettings` (not `userSettings`), appropriate for project-scoped data.

#### 1.4 migrateFennecToOpus.ts
- **Purpose**: Migrates removed internal "fennec" model aliases to Opus 4.6 equivalents.
  - `fennec-latest` -> `opus`
  - `fennec-latest[1m]` -> `opus[1m]`
  - `fennec-fast-latest` / `opus-4-5-fast` -> `opus[1m]` + `fastMode: true`
- **Guard**: Only runs for internal users (`USER_TYPE === 'ant'`).

#### 1.5 migrateLegacyOpusToCurrent.ts
- **Purpose**: Migrates pinned Opus 4.0/4.1 model strings to the `opus` alias (which resolves to Opus 4.6 for first-party).
- **Matched strings**: `claude-opus-4-20250514`, `claude-opus-4-1-20250805`, `claude-opus-4-0`, `claude-opus-4-1`.
- **Guard**: Only first-party API provider + `isLegacyModelRemapEnabled()`.

#### 1.6 migrateOpusToOpus1m.ts
- **Purpose**: Migrates users with `opus` pinned in settings to `opus[1m]` for Max/Team Premium subscribers who get the merged 1M experience.
- **Guard**: `isOpus1mMergeEnabled()` must be true; skips Pro subscribers and 3P users.
- **Smart default handling**: If migrated model equals the default, sets `model: undefined` to remove the pin entirely.

#### 1.7 migrateReplBridgeEnabledToRemoteControlAtStartup.ts
- **Purpose**: Renames config key `replBridgeEnabled` to `remoteControlAtStartup`.
- **Rationale**: The old key was an implementation detail that leaked into user-facing config.
- **Simplest migration**: No analytics, no external dependencies.

#### 1.8 migrateSonnet1mToSonnet45.ts
- **Purpose**: Pins users who had `sonnet[1m]` to explicit `sonnet-4-5-20250929[1m]` when the `sonnet` alias was updated to resolve to Sonnet 4.6.
- **Guard**: Completion flag `sonnet1m45MigrationComplete` in GlobalConfig (runs once).
- **In-memory migration**: Also migrates the runtime `MainLoopModelOverride` if already set.

#### 1.9 migrateSonnet45ToSonnet46.ts
- **Purpose**: For Pro/Max/Team Premium first-party users: moves explicit Sonnet 4.5 strings back to the `sonnet` alias (now resolving to 4.6).
- **Matched strings**: `claude-sonnet-4-5-20250929`, `sonnet-4-5-20250929`, and their `[1m]` variants.
- **1M awareness**: Preserves `[1m]` suffix when present.

#### 1.10 resetAutoModeOptInForDefaultOffer.ts
- **Purpose**: One-shot migration that clears `skipAutoPermissionPrompt` for users who accepted the old 2-option AutoModeOptInDialog but don't have auto as their default mode. Re-surfaces the dialog for the new "make it my default mode" option.

#### 1.11 resetProToOpusDefault.ts
- **Purpose**: Auto-migrates Pro subscribers on first-party to the Opus 4.5 default model.
- **Guard**: Completion flag `opusProMigrationComplete` in GlobalConfig.

### Cross-Cutting Patterns

| Pattern | Detail |
|---------|--------|
| **Idempotency** | Every migration is safe to re-run. Strategies: completion flags in GlobalConfig, reading/writing same settings source, checking target existence before write. |
| **Scope isolation** | Migrations only touch `userSettings` (never merged settings) to avoid silently promoting project-scoped pins to global defaults. Exception: MCP migration targets `localSettings`. |
| **Error handling** | Try/catch with `logError()` + analytics event. Failures never break startup. |
| **Analytics** | All migrations log `tengu_migrate_*` or `tengu_reset_*` events for tracking rollout. |
| **Execution order** | Called sequentially in `main.tsx`. Order matters: `migrateSonnet1mToSonnet45` must run before `migrateSonnet45ToSonnet46`. |
| **MODEL LAUNCH marker** | `main.tsx:323` has `@[MODEL LAUNCH]` comment reminding devs to add model migrations. |

### Key Dependencies

- `utils/config.js` -- `getGlobalConfig()`, `saveGlobalConfig()`, `getCurrentProjectConfig()`, `saveCurrentProjectConfig()`
- `utils/settings/settings.js` -- `getSettingsForSource()`, `updateSettingsForSource()`
- `utils/model/model.js` -- `isLegacyModelRemapEnabled()`, `isOpus1mMergeEnabled()`, `parseUserSpecifiedModel()`
- `utils/auth.js` -- `isProSubscriber()`, `isMaxSubscriber()`, `isTeamPremiumSubscriber()`

---

## 2. schemas/ Module (1 file, 223 LOC)

### Purpose

The schemas module contains **shared Zod schema definitions** extracted to break import cycles. Currently holds only `hooks.ts`, which defines the canonical schema for Claude Code's hook system.

### Why It Exists

The file's header comment explains: hook-related schemas were originally in `src/utils/settings/types.ts`. A circular dependency existed between `settings/types.ts` and `plugins/schemas.ts`. By extracting to this shared location, both files import from here instead of each other.

### Schema Definitions

**BashCommandHookSchema** (`type: 'command'`)
- `command: string` -- Shell command to execute
- `if` -- IfConditionSchema filter (permission rule syntax, e.g., `"Bash(git *)"`)
- `shell` -- Enum of `SHELL_TYPES` (bash/powershell); defaults to bash
- `timeout` -- Seconds (positive number)
- `statusMessage` -- Custom spinner text
- `once` -- Run once then remove
- `async` -- Run in background without blocking
- `asyncRewake` -- Background + wake model on exit code 2. Implies async.

**PromptHookSchema** (`type: 'prompt'`)
- `prompt: string` -- LLM prompt with `$ARGUMENTS` placeholder for hook input JSON
- `model` -- Optional model override (e.g., `"claude-sonnet-4-6"`)

**HttpHookSchema** (`type: 'http'`)
- `url: string` -- URL to POST hook input JSON to
- `headers` -- Record of string headers with env var interpolation (`$VAR_NAME` / `${VAR_NAME}`)
- `allowedEnvVars` -- Explicit whitelist for env var interpolation (security measure)

**AgentHookSchema** (`type: 'agent'`)
- `prompt: string` -- What to verify (e.g., "Verify that unit tests ran and passed.")
- `model` -- Optional model override; defaults to Haiku

**HookCommandSchema** (exported)
- Discriminated union of all four hook types via `z.discriminatedUnion('type', [...])`
- Uses `lazySchema()` wrapper for deferred evaluation to avoid circular imports

**HooksSchema** (exported)
- Partial record keyed by `HookEvent` enum values, valued as `HookMatcher[]` arrays

### Consumers

| Consumer | Usage |
|----------|-------|
| `utils/settings/types.ts` | Re-exports schemas and types. Uses `HooksSchema()` in settings validation. |
| `utils/plugins/schemas.ts` | Imports `HooksSchema` to build `PluginHooksSchema` and `PluginManifestHooksSchema`. |
| `skills/loadSkillsDir.ts` | Parses frontmatter hooks via `HooksSchema().safeParse()`. |
| `tools/AgentTool/loadAgentsDir.ts` | Parses agent frontmatter hooks via `HooksSchema().safeParse()`. |

---

## 3. outputStyles/ Module (1 file, 98 LOC)

### Purpose

Loads user-defined and project-defined **output style configurations** from markdown files in `.claude/output-styles/` directories.

### Core Function: `getOutputStyleDirStyles(cwd: string)`

Memoized async function that:

1. **Loads markdown files** from `.claude/output-styles/` directories via `loadMarkdownFilesForSubdir('output-styles', cwd)` -- scans both project-level and user-level (`~/.claude/output-styles/`) directories.

2. **For each markdown file**, extracts:
   - **name**: From frontmatter `name` field, or falls back to filename (minus `.md`)
   - **description**: From frontmatter `description` field, or extracted from markdown content
   - **prompt**: The markdown content body (trimmed), used as the style's system prompt
   - **source**: Origin indicator (project vs user)
   - **keepCodingInstructions**: Boolean from frontmatter `keep-coding-instructions` field

3. **Returns**: Array of `OutputStyleConfig` objects.

### Integration

Called by `constants/outputStyles.ts` to merge custom styles into the output style registry. Priority: built-in < plugin < user < project < managed.

---

## 4. moreright/ Module (1 file, 26 LOC)

### Purpose

An **external-build stub** for an internal-only React hook. The real `useMoreRight` implementation is internal to Anthropic; this stub provides a no-op replacement for open-source/external builds.

### Stub Interface

```typescript
export function useMoreRight(_args: {
  enabled: boolean;
  setMessages: (action: M[] | ((prev: M[]) => M[])) => void;
  inputValue: string;
  setInputValue: (s: string) => void;
  setToolJSX: (args: M) => void;
}): {
  onBeforeQuery: (input: string, all: M[], n: number) => Promise<boolean>;
  onTurnComplete: (all: M[], aborted: boolean) => Promise<void>;
  render: () => null;
}
```

### No-Op Returns
- `onBeforeQuery`: Always returns `true` (allow query to proceed)
- `onTurnComplete`: Empty async function
- `render`: Returns `null` (renders nothing)

### Design Notes
- Self-contained: **No relative imports** -- placed at `scripts/external-stubs/src/moreright/` before overlay
- Uses `type M = any` to avoid importing internal types
- The real hook is overlaid during internal builds, replacing this stub

---

## Summary Table

| Module | Files | LOC | Purpose | Called From |
|--------|-------|-----|---------|-------------|
| `migrations/` | 11 | ~530 | One-shot startup data migrations (config keys, model strings, settings consolidation) | `main.tsx` (sequential at startup) |
| `schemas/` | 1 | 223 | Shared Zod schemas for hook system (breaks import cycles) | `settings/types.ts`, `plugins/schemas.ts`, `loadSkillsDir.ts`, `loadAgentsDir.ts` |
| `outputStyles/` | 1 | 98 | Load custom output styles from `.claude/output-styles/*.md` directories | `constants/outputStyles.ts` |
| `moreright/` | 1 | 26 | External-build stub for internal REPL hook | `screens/REPL.tsx` |

## Key Architectural Insights

1. **Migration ordering matters**: Model migrations have dependencies (Sonnet 4.5 pin must happen before 4.5-to-4.6 migration). The `@[MODEL LAUNCH]` marker serves as a checklist reminder.

2. **Hook schema is a critical shared type**: The 4-type discriminated union (command, prompt, http, agent) with lazy evaluation is the foundation for Claude Code's extensibility -- used by settings, plugins, skills, and agents.

3. **Output styles demonstrate the markdown-as-config pattern**: Frontmatter provides metadata, content body provides the prompt. Same pattern used by skills and agents.

4. **MoreRight reveals the internal/external build split**: Claude Code uses an overlay mechanism where internal-only features are stubbed for external builds. The stub's interface is the contract between builds.

# Wave 51: Migrations, Schemas, OutputStyles, MoreRight

> Deep analysis of four small but critical modules in Claude Code's utility layer.
> Source: `CC-Source/src/migrations/` (11 files), `src/schemas/` (1 file), `src/outputStyles/` (1 file), `src/moreright/` (1 file)

---

## 1. migrations/ Module (11 files)

### Purpose

The migrations module handles **one-shot data migrations** that run at application startup in `main.tsx`. Each migration transforms legacy config/settings keys into their current equivalents, ensuring backward compatibility as Claude Code evolves. They follow a consistent pattern: check precondition, transform data, clean up old key, log analytics event.

All 11 migrations are imported and called sequentially in `main.tsx` (lines 323-341), with a `@[MODEL LAUNCH]` comment reminding developers to consider new model-string migrations on each release.

### File Inventory

#### 1.1 migrateAutoUpdatesToSettings.ts
- **Purpose**: Moves user-set `autoUpdates: false` preference from GlobalConfig (`~/.claude.json`) to `settings.json` as `env.DISABLE_AUTOUPDATER=1`.
- **Guard**: Skips if `autoUpdates !== false` or if it was set automatically for native protection (`autoUpdatesProtectedForNative`).
- **Side effect**: Sets `process.env.DISABLE_AUTOUPDATER = '1'` for immediate effect.
- **Cleanup**: Removes `autoUpdates` and `autoUpdatesProtectedForNative` from GlobalConfig.
- **Analytics**: `tengu_migrate_autoupdates_to_settings`, `tengu_migrate_autoupdates_error`.

#### 1.2 migrateBypassPermissionsAcceptedToSettings.ts
- **Purpose**: Moves `bypassPermissionsModeAccepted` from GlobalConfig to `settings.json` as `skipDangerousModePermissionPrompt: true`.
- **Guard**: Skips if `bypassPermissionsModeAccepted` is falsy in GlobalConfig.
- **Idempotent**: Checks `hasSkipDangerousModePermissionPrompt()` before writing.
- **Cleanup**: Removes `bypassPermissionsModeAccepted` from GlobalConfig.
- **Analytics**: `tengu_migrate_bypass_permissions_accepted`.

#### 1.3 migrateEnableAllProjectMcpServersToSettings.ts
- **Purpose**: Moves three MCP server approval fields from project config to local settings:
  - `enableAllProjectMcpServers` (boolean)
  - `enabledMcpjsonServers` (string array, merged with dedup via `Set`)
  - `disabledMcpjsonServers` (string array, merged with dedup)
- **Guard**: Skips if none of the three fields exist in project config.
- **Target**: Writes to `localSettings` (not `userSettings`), appropriate for project-scoped data.
- **Analytics**: `tengu_migrate_mcp_approval_fields_success`, `tengu_migrate_mcp_approval_fields_error`.

#### 1.4 migrateFennecToOpus.ts
- **Purpose**: Migrates removed internal "fennec" model aliases to Opus 4.6 equivalents.
  - `fennec-latest` -> `opus`
  - `fennec-latest[1m]` -> `opus[1m]`
  - `fennec-fast-latest` / `opus-4-5-fast` -> `opus[1m]` + `fastMode: true`
- **Guard**: Only runs for internal users (`USER_TYPE === 'ant'`).
- **Scope**: Only touches `userSettings` to avoid promoting project-scoped settings globally.
- **Idempotent**: Re-reading same source after write means no-op on next run.

#### 1.5 migrateLegacyOpusToCurrent.ts
- **Purpose**: Migrates pinned Opus 4.0/4.1 model strings to the `opus` alias (which resolves to Opus 4.6 for first-party).
- **Matched strings**: `claude-opus-4-20250514`, `claude-opus-4-1-20250805`, `claude-opus-4-0`, `claude-opus-4-1`.
- **Guard**: Only first-party API provider + `isLegacyModelRemapEnabled()`.
- **Side effect**: Sets `legacyOpusMigrationTimestamp` in GlobalConfig for one-time REPL notification.
- **Analytics**: `tengu_legacy_opus_migration` with `from_model`.

#### 1.6 migrateOpusToOpus1m.ts
- **Purpose**: Migrates users with `opus` pinned in settings to `opus[1m]` for Max/Team Premium subscribers who get the merged 1M experience.
- **Guard**: `isOpus1mMergeEnabled()` must be true; skips Pro subscribers and 3P users.
- **Smart default handling**: If migrated model equals the default, sets `model: undefined` to remove the pin entirely.
- **Analytics**: `tengu_opus_to_opus1m_migration`.

#### 1.7 migrateReplBridgeEnabledToRemoteControlAtStartup.ts
- **Purpose**: Renames config key `replBridgeEnabled` to `remoteControlAtStartup`.
- **Rationale**: The old key was an implementation detail that leaked into user-facing config.
- **Guard**: Only acts when old key exists and new key hasn't been set.
- **Implementation**: Uses untyped cast `(prev as Record<string, unknown>)` since old key is removed from the `GlobalConfig` TypeScript type.
- **Simplest migration**: No analytics, no external dependencies.

#### 1.8 migrateSonnet1mToSonnet45.ts
- **Purpose**: Pins users who had `sonnet[1m]` to explicit `sonnet-4-5-20250929[1m]` when the `sonnet` alias was updated to resolve to Sonnet 4.6.
- **Guard**: Completion flag `sonnet1m45MigrationComplete` in GlobalConfig (runs once).
- **In-memory migration**: Also migrates the runtime `MainLoopModelOverride` if already set.
- **Rationale**: Sonnet 4.6 1M was offered to a different user group than Sonnet 4.5 1M.

#### 1.9 migrateSonnet45ToSonnet46.ts
- **Purpose**: Reverses/updates the previous migration for Pro/Max/Team Premium first-party users: moves explicit Sonnet 4.5 strings back to the `sonnet` alias (now resolving to 4.6).
- **Matched strings**: `claude-sonnet-4-5-20250929`, `sonnet-4-5-20250929`, and their `[1m]` variants.
- **Guard**: First-party + (Pro OR Max OR Team Premium).
- **1M awareness**: Preserves `[1m]` suffix when present.
- **Notification**: Sets `sonnet45To46MigrationTimestamp` only for non-new users (`numStartups > 1`).
- **Analytics**: `tengu_sonnet45_to_46_migration` with `from_model`, `has_1m`.

#### 1.10 resetAutoModeOptInForDefaultOffer.ts
- **Purpose**: One-shot migration that clears `skipAutoPermissionPrompt` for users who accepted the old 2-option AutoModeOptInDialog but don't have auto as their default mode. Re-surfaces the dialog so they see the new "make it my default mode" option.
- **Guard**: Feature flag `TRANSCRIPT_CLASSIFIER` + `hasResetAutoModeOptInForDefaultOffer` in GlobalConfig + `getAutoModeEnabledState() === 'enabled'`.
- **Design note**: Explicitly avoids 'opt-in' users where clearing the prompt would remove auto from the carousel entirely.
- **Analytics**: `tengu_migrate_reset_auto_opt_in_for_default_offer`.

#### 1.11 resetProToOpusDefault.ts
- **Purpose**: Auto-migrates Pro subscribers on first-party to the Opus 4.5 default model.
- **Guard**: Completion flag `opusProMigrationComplete` in GlobalConfig.
- **Notification**: Sets `opusProMigrationTimestamp` only for users on the default model (no custom setting).
- **Non-Pro handling**: Immediately marks migration complete for non-Pro or non-first-party users.
- **Analytics**: `tengu_reset_pro_to_opus_default` with `skipped`, `had_custom_model`.

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
- `utils/model/providers.js` -- `getAPIProvider()`
- `utils/auth.js` -- `isProSubscriber()`, `isMaxSubscriber()`, `isTeamPremiumSubscriber()`
- `services/analytics/index.js` -- `logEvent()`
- `bootstrap/state.js` -- `getMainLoopModelOverride()`, `setMainLoopModelOverride()`

---

## 2. schemas/ Module (1 file)

### Purpose

The schemas module contains **shared Zod schema definitions** extracted to break import cycles. Currently holds only `hooks.ts`, which defines the canonical schema for Claude Code's hook system.

### File: hooks.ts (223 lines)

#### Why It Exists

The file's header comment explains: hook-related schemas were originally in `src/utils/settings/types.ts`. A circular dependency existed between `settings/types.ts` and `plugins/schemas.ts`. By extracting to this shared location, both files import from here instead of each other.

#### Schema Definitions

**IfConditionSchema** (shared filter)
- Optional string using permission rule syntax (e.g., `"Bash(git *)"`)
- Evaluated against `tool_name` and `tool_input` to filter hook execution before spawning
- Avoids spawning hooks for non-matching commands

**BashCommandHookSchema** (`type: 'command'`)
- `command: string` -- Shell command to execute
- `if` -- IfConditionSchema filter
- `shell` -- Enum of `SHELL_TYPES` (bash/powershell); defaults to bash
- `timeout` -- Seconds (positive number)
- `statusMessage` -- Custom spinner text
- `once` -- Run once then remove
- `async` -- Run in background without blocking
- `asyncRewake` -- Background + wake model on exit code 2 (blocking error). Implies async.

**PromptHookSchema** (`type: 'prompt'`)
- `prompt: string` -- LLM prompt with `$ARGUMENTS` placeholder for hook input JSON
- `model` -- Optional model override (e.g., `"claude-sonnet-4-6"`)
- `if`, `timeout`, `statusMessage`, `once` -- Same as command hooks

**HttpHookSchema** (`type: 'http'`)
- `url: string` -- URL to POST hook input JSON to
- `headers` -- Record of string headers with env var interpolation (`$VAR_NAME` / `${VAR_NAME}`)
- `allowedEnvVars` -- Explicit whitelist for env var interpolation (security measure)
- `if`, `timeout`, `statusMessage`, `once` -- Same as above

**AgentHookSchema** (`type: 'agent'`)
- `prompt: string` -- What to verify (e.g., "Verify that unit tests ran and passed.")
- `model` -- Optional model override; defaults to Haiku
- `if`, `timeout` (default 60s), `statusMessage`, `once`
- **Historical note**: A `.transform()` was removed (gh-24920, CC-79) because it broke JSON round-tripping in `updateSettingsForSource`.

**HookCommandSchema** (exported)
- Discriminated union of all four hook types via `z.discriminatedUnion('type', [...])`
- Uses `lazySchema()` wrapper for deferred evaluation to avoid circular imports

**HookMatcherSchema** (exported)
- `matcher: string` -- Pattern to match (e.g., tool names like `"Write"`)
- `hooks: HookCommand[]` -- Array of hooks to execute when matcher matches

**HooksSchema** (exported)
- Partial record keyed by `HookEvent` enum values, valued as `HookMatcher[]` arrays
- Uses `z.partialRecord()` since not all hook events need to be defined

#### Exported Types

| Type | Definition |
|------|-----------|
| `HookCommand` | Inferred union of all 4 hook schemas |
| `BashCommandHook` | `Extract<HookCommand, { type: 'command' }>` |
| `PromptHook` | `Extract<HookCommand, { type: 'prompt' }>` |
| `AgentHook` | `Extract<HookCommand, { type: 'agent' }>` |
| `HttpHook` | `Extract<HookCommand, { type: 'http' }>` |
| `HookMatcher` | Inferred type for matcher config |
| `HooksSettings` | `Partial<Record<HookEvent, HookMatcher[]>>` |

#### Consumers (Integration Points)

| Consumer | Usage |
|----------|-------|
| `utils/settings/types.ts` | Re-exports `HookCommandSchema`, `HooksSchema`, types. Uses `HooksSchema()` in settings validation schema. |
| `utils/plugins/schemas.ts` | Imports `HooksSchema` to build `PluginHooksSchema` and `PluginManifestHooksSchema`. |
| `utils/plugins/pluginLoader.ts` | Uses `PluginHooksSchema` to validate plugin hook configs. |
| `utils/plugins/validatePlugin.ts` | Uses `PluginHooksSchema` for plugin validation. |
| `skills/loadSkillsDir.ts` | Parses frontmatter hooks via `HooksSchema().safeParse()`. |
| `tools/AgentTool/loadAgentsDir.ts` | Parses agent frontmatter hooks via `HooksSchema().safeParse()`. |
| `utils/frontmatterParser.ts` | Comments reference `HooksSchema` validation. |

---

## 3. outputStyles/ Module (1 file)

### Purpose

Loads user-defined and project-defined **output style configurations** from markdown files in `.claude/output-styles/` directories.

### File: loadOutputStylesDir.ts (98 lines)

#### Core Function: `getOutputStyleDirStyles(cwd: string): Promise<OutputStyleConfig[]>`

Memoized async function that:

1. **Loads markdown files** from `.claude/output-styles/` directories via `loadMarkdownFilesForSubdir('output-styles', cwd)` -- scans both project-level and user-level (`~/.claude/output-styles/`) directories.

2. **For each markdown file**, extracts:
   - **name**: From frontmatter `name` field, or falls back to filename (minus `.md`)
   - **description**: From frontmatter `description` field, or extracted from markdown content, or default `"Custom {name} output style"`
   - **prompt**: The markdown content body (trimmed), used as the style's system prompt
   - **source**: Origin indicator (project vs user)
   - **keepCodingInstructions**: Boolean parsed from frontmatter `keep-coding-instructions` field (supports both boolean and string `"true"`/`"false"`)

3. **Validates**: Warns if `force-for-plugin` is set on non-plugin styles (that option only applies to plugin output styles).

4. **Returns**: Array of `OutputStyleConfig` objects.

#### Cache Management: `clearOutputStyleCaches()`

Clears three caches:
- `getOutputStyleDirStyles.cache` (lodash memoize)
- `loadMarkdownFilesForSubdir.cache` (shared markdown loader)
- `clearPluginOutputStyleCache()` (plugin output styles)

#### Integration Points

| Consumer | Usage |
|----------|-------|
| `constants/outputStyles.ts` | Calls `getOutputStyleDirStyles(cwd)` at line 140 to merge custom styles into the output style registry. |

#### Dependencies

- `lodash-es/memoize` -- Memoization
- `constants/outputStyles.js` -- `OutputStyleConfig` type
- `utils/frontmatterParser.js` -- `coerceDescriptionToString()`
- `utils/markdownConfigLoader.js` -- `loadMarkdownFilesForSubdir()`, `extractDescriptionFromMarkdown()`
- `utils/plugins/loadPluginOutputStyles.js` -- `clearPluginOutputStyleCache()`
- `utils/debug.js` -- `logForDebugging()`
- `utils/log.js` -- `logError()`

---

## 4. moreright/ Module (1 file)

### Purpose

An **external-build stub** for an internal-only React hook. The real `useMoreRight` implementation is internal to Anthropic; this stub provides a no-op replacement for open-source/external builds.

### File: useMoreRight.tsx (26 lines)

#### Stub Interface

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

#### No-Op Returns
- `onBeforeQuery`: Always returns `true` (allow query to proceed)
- `onTurnComplete`: Empty async function
- `render`: Returns `null` (renders nothing)

#### Design Notes
- Self-contained: **No relative imports** -- the comment explains this is placed at `scripts/external-stubs/src/moreright/` before overlay, where relative paths would fail.
- Uses `type M = any` to avoid importing internal types.
- Includes inline source map (base64-encoded).
- The real hook is overlaid during internal builds, replacing this stub.

#### Integration Point

| Consumer | Usage |
|----------|-------|
| `screens/REPL.tsx` (line 68) | Imports `useMoreRight` from `../moreright/useMoreRight.js`. Called at line 1665 with REPL state (messages, input, toolJSX). The three returned callbacks integrate into the REPL query lifecycle. |

#### Inferred Real Behavior

From the interface shape, the real (internal) `useMoreRight` likely:
- **onBeforeQuery**: Can intercept/modify/block queries before they reach the model
- **onTurnComplete**: Processes conversation turns after completion (analytics, side effects)
- **render**: Renders additional UI elements in the REPL
- **setMessages/setInputValue/setToolJSX**: Can modify REPL state (inject messages, change input, render tool UI)

The name "moreright" is opaque -- likely an internal codename for an experimental feature or A/B test that hooks into the REPL conversation loop.

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

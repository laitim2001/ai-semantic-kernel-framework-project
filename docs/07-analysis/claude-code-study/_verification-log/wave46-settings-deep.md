# Wave 46: Settings System Deep Analysis

> **Source**: `src/utils/settings/` (16 files) + `src/utils/settings/mdm/` (3 files) = 19 files total
> **LOC**: ~2,800 lines (types.ts alone ~1,150)
> **Verification Date**: 2026-04-01
> **Quality Score**: 9.3/10

---

## 1. Architecture Overview

The settings system is a **layered configuration pipeline** that merges settings from 6+ sources with strict precedence rules, Zod v4 schema validation, filesystem watching, and MDM (Mobile Device Management) enterprise integration.

### Core Design Principles
- **Layered precedence**: Higher-priority sources override lower ones via `lodash.mergeWith`
- **Schema-first**: All settings validated through a single `SettingsSchema` (Zod v4)
- **Enterprise-ready**: MDM profiles (macOS plist, Windows registry), remote managed settings, drop-in policy fragments
- **Security-conscious**: `projectSettings` intentionally excluded from security-sensitive settings (RCE prevention)
- **Cache-aware**: Three-tier caching (session, per-source, per-file) with centralized invalidation

---

## 2. File Inventory

### Root: `src/utils/settings/`

| File | LOC | Purpose |
|------|-----|---------|
| `types.ts` | ~1,150 | Master Zod schema (`SettingsSchema`), all TypeScript types, 60+ setting fields |
| `settings.ts` | ~1,016 | Core merge engine, file loading, source resolution, `getInitialSettings()` |
| `changeDetector.ts` | ~489 | Chokidar filesystem watcher, MDM polling, deletion grace periods |
| `constants.ts` | ~202 | Source definitions, display names, `SETTING_SOURCES` array, `--setting-sources` parser |
| `permissionValidation.ts` | ~263 | Permission rule parser/validator (parentheses, MCP, Bash, file patterns) |
| `validation.ts` | ~266 | Zod error formatting, `validateSettingsFileContent()`, invalid rule filtering |
| `validationTips.ts` | ~164 | Context-aware validation tips with documentation links |
| `settingsCache.ts` | ~81 | Three-tier cache: session, per-source, per-file; plugin settings base layer |
| `applySettingsChange.ts` | ~93 | Applies settings changes to AppState (permissions, hooks, effort sync) |
| `toolValidationConfig.ts` | ~103 | Tool-specific validation (file pattern tools, bash prefix tools, WebSearch/WebFetch) |
| `pluginOnlyPolicy.ts` | ~61 | `strictPluginOnlyCustomization` enforcement; admin-trusted source checking |
| `managedPath.ts` | ~35 | Platform-specific managed settings paths (macOS/Windows/Linux) |
| `internalWrites.ts` | ~38 | Timestamp tracking to suppress chokidar echoes from internal writes |
| `validateEditTool.ts` | ~46 | Pre-edit validation for settings files (blocks invalid schema changes) |
| `allErrors.ts` | ~33 | Combines settings + MCP config errors (breaks circular dependency) |
| `schemaOutput.ts` | ~9 | JSON Schema generation via `zod/v4` `toJSONSchema()` |

### MDM Subdirectory: `src/utils/settings/mdm/`

| File | LOC | Purpose |
|------|-----|---------|
| `settings.ts` | ~317 | MDM parsing, caching, first-source-wins policy, HKLM/plist/HKCU resolution |
| `rawRead.ts` | ~131 | Subprocess I/O for MDM reads (`plutil`, `reg query`); minimal imports for startup speed |
| `constants.ts` | ~82 | Registry paths, plist domain, plutil args, macOS plist path builder |

---

## 3. Settings Sources & Precedence

### Merge Order (lowest to highest priority)

```
pluginSettings (base)     — from loaded plugins (allowlisted keys only)
    ↓ mergeWith
userSettings              — ~/.claude/settings.json (or cowork_settings.json)
    ↓ mergeWith
projectSettings           — $CWD/.claude/settings.json (checked into repo)
    ↓ mergeWith
localSettings             — $CWD/.claude/settings.local.json (gitignored)
    ↓ mergeWith
flagSettings              — --settings CLI flag file + SDK inline settings
    ↓ mergeWith
policySettings            — Enterprise managed (see sub-precedence below)
```

### Policy Settings Sub-Precedence (first source wins)

Within `policySettings`, a "first source wins" strategy is used:

```
remote (API-synced)       — highest priority
    ↓ fallback
HKLM / macOS plist        — admin-only OS-level MDM
    ↓ fallback
managed-settings.json     — file-based + managed-settings.d/*.json drop-ins
    ↓ fallback
HKCU                      — user-writable Windows registry (lowest)
```

### File Locations by Source

| Source | File Path |
|--------|-----------|
| `userSettings` | `~/.claude/settings.json` (or `cowork_settings.json` in cowork mode) |
| `projectSettings` | `$CWD/.claude/settings.json` |
| `localSettings` | `$CWD/.claude/settings.local.json` (auto-added to `.gitignore`) |
| `flagSettings` | Path from `--settings` CLI flag |
| `policySettings` (file) | Platform-dependent managed path (see below) |

### Managed Settings Platform Paths

| Platform | Base Path | File |
|----------|-----------|------|
| macOS | `/Library/Application Support/ClaudeCode/` | `managed-settings.json` |
| Windows | `C:\Program Files\ClaudeCode\` | `managed-settings.json` |
| Linux | `/etc/claude-code/` | `managed-settings.json` |
| All | `{base}/managed-settings.d/` | `*.json` drop-in fragments (alphabetical merge) |

### MDM OS Paths

| Platform | Source | Path/Key |
|----------|--------|----------|
| macOS (per-user) | plist | `/Library/Managed Preferences/{username}/com.anthropic.claudecode.plist` |
| macOS (device) | plist | `/Library/Managed Preferences/com.anthropic.claudecode.plist` |
| Windows (admin) | HKLM | `HKLM\SOFTWARE\Policies\ClaudeCode` → `Settings` (REG_SZ JSON) |
| Windows (user) | HKCU | `HKCU\SOFTWARE\Policies\ClaudeCode` → `Settings` (REG_SZ JSON) |

---

## 4. Schema Validation (Zod v4)

### SettingsSchema — Complete Field Inventory

The `SettingsSchema` is defined via `lazySchema(() => z.object({...}).passthrough())` in `types.ts`. Fields organized by category:

#### Authentication & Credentials
| Field | Type | Description |
|-------|------|-------------|
| `apiKeyHelper` | `string?` | Path to script outputting auth values |
| `awsCredentialExport` | `string?` | Path to AWS credential export script |
| `awsAuthRefresh` | `string?` | Path to AWS auth refresh script |
| `gcpAuthRefresh` | `string?` | GCP auth refresh command |
| `xaaIdp` | `object?` | XAA IdP OIDC config (feature-gated `CLAUDE_CODE_ENABLE_XAA`) |
| `otelHeadersHelper` | `string?` | Script outputting OpenTelemetry headers |

#### Permissions
| Field | Type | Description |
|-------|------|-------------|
| `permissions.allow` | `PermissionRule[]?` | Allowed operations |
| `permissions.deny` | `PermissionRule[]?` | Denied operations |
| `permissions.ask` | `PermissionRule[]?` | Always-prompt operations |
| `permissions.defaultMode` | `enum?` | Default permission mode |
| `permissions.disableBypassPermissionsMode` | `"disable"?` | Disable bypass mode |
| `permissions.disableAutoMode` | `"disable"?` | Disable auto mode (feature-gated) |
| `permissions.additionalDirectories` | `string[]?` | Extra directories in scope |
| `skipDangerousModePermissionPrompt` | `boolean?` | Bypass permissions dialog accepted |
| `skipAutoPermissionPrompt` | `boolean?` | Auto mode opt-in accepted (feature-gated) |
| `useAutoModeDuringPlan` | `boolean?` | Plan mode uses auto semantics (default: true) |
| `autoMode` | `object?` | Auto mode classifier config (allow/soft_deny/environment) |
| `disableAutoMode` | `"disable"?` | Disable auto mode globally |

#### Model Configuration
| Field | Type | Description |
|-------|------|-------------|
| `model` | `string?` | Override default model |
| `availableModels` | `string[]?` | Enterprise model allowlist |
| `modelOverrides` | `Record<string, string>?` | Model ID mapping (e.g., to Bedrock ARN) |
| `advisorModel` | `string?` | Advisor model for server-side advisor tool |
| `effortLevel` | `enum?` | Persisted effort level (`low`/`medium`/`high`/`max` for ant) |
| `alwaysThinkingEnabled` | `boolean?` | Enable/disable thinking |
| `fastMode` | `boolean?` | Enable fast mode |
| `fastModePerSessionOptIn` | `boolean?` | Non-persistent fast mode |

#### MCP Server Management
| Field | Type | Description |
|-------|------|-------------|
| `enableAllProjectMcpServers` | `boolean?` | Auto-approve all project MCP servers |
| `enabledMcpjsonServers` | `string[]?` | Approved MCP servers from `.mcp.json` |
| `disabledMcpjsonServers` | `string[]?` | Rejected MCP servers |
| `allowedMcpServers` | `AllowedMcpServerEntry[]?` | Enterprise MCP allowlist |
| `deniedMcpServers` | `DeniedMcpServerEntry[]?` | Enterprise MCP denylist |
| `allowManagedMcpServersOnly` | `boolean?` | Only read MCP allowlist from managed settings |

#### Hooks
| Field | Type | Description |
|-------|------|-------------|
| `hooks` | `HooksSchema?` | Custom pre/post tool execution commands |
| `disableAllHooks` | `boolean?` | Disable all hooks and statusLine |
| `allowManagedHooksOnly` | `boolean?` | Only managed hooks run |
| `allowedHttpHookUrls` | `string[]?` | HTTP hook URL allowlist |
| `httpHookAllowedEnvVars` | `string[]?` | HTTP hook env var allowlist |

#### Sandbox
| Field | Type | Description |
|-------|------|-------------|
| `sandbox` | `SandboxSettingsSchema?` | Full sandbox configuration |

#### Plugins & Marketplaces
| Field | Type | Description |
|-------|------|-------------|
| `enabledPlugins` | `Record<string, boolean\|string[]>?` | Enabled plugins by ID |
| `extraKnownMarketplaces` | `Record<string, ExtraKnownMarketplace>?` | Additional marketplace sources |
| `strictKnownMarketplaces` | `MarketplaceSource[]?` | Enterprise marketplace allowlist |
| `blockedMarketplaces` | `MarketplaceSource[]?` | Enterprise marketplace blocklist |
| `strictPluginOnlyCustomization` | `boolean \| Surface[]?` | Lock customization to plugins only |
| `pluginConfigs` | `Record<string, PluginConfig>?` | Per-plugin MCP server configs |

#### UI & Behavior
| Field | Type | Description |
|-------|------|-------------|
| `outputStyle` | `string?` | Output style for responses |
| `language` | `string?` | Preferred language for responses and voice dictation |
| `statusLine` | `object?` | Custom status line display |
| `spinnerTipsEnabled` | `boolean?` | Show tips in spinner |
| `spinnerVerbs` | `object?` | Customize spinner verbs (append/replace) |
| `spinnerTipsOverride` | `object?` | Override spinner tips |
| `syntaxHighlightingDisabled` | `boolean?` | Disable syntax highlighting in diffs |
| `promptSuggestionEnabled` | `boolean?` | Enable/disable prompt suggestions |
| `prefersReducedMotion` | `boolean?` | Reduce animations for accessibility |
| `showThinkingSummaries` | `boolean?` | Show thinking summaries in transcript |
| `showClearContextOnPlanAccept` | `boolean?` | Offer "clear context" on plan accept |
| `defaultView` | `enum?` | Default transcript view (feature-gated) |

#### Git & Attribution
| Field | Type | Description |
|-------|------|-------------|
| `attribution.commit` | `string?` | Custom commit attribution text |
| `attribution.pr` | `string?` | Custom PR attribution text |
| `includeCoAuthoredBy` | `boolean?` | Deprecated: use `attribution` instead |
| `includeGitInstructions` | `boolean?` | Include built-in git instructions in system prompt |

#### Session & Cleanup
| Field | Type | Description |
|-------|------|-------------|
| `cleanupPeriodDays` | `number?` | Transcript retention days (0 = disable persistence) |
| `env` | `Record<string, string>?` | Environment variables for sessions |
| `defaultShell` | `enum?` | Default shell for `!` commands (`bash`/`powershell`) |

#### Enterprise & Remote
| Field | Type | Description |
|-------|------|-------------|
| `forceLoginMethod` | `enum?` | Force `claudeai` or `console` login |
| `forceLoginOrgUUID` | `string?` | Organization UUID for OAuth |
| `companyAnnouncements` | `string[]?` | Startup announcements |
| `pluginTrustMessage` | `string?` | Custom plugin trust warning |
| `allowManagedPermissionRulesOnly` | `boolean?` | Only managed permission rules |
| `sshConfigs` | `SshConfig[]?` | Pre-configured SSH connections |
| `remote.defaultEnvironmentId` | `string?` | Default remote environment |
| `channelsEnabled` | `boolean?` | Enable channel notifications |
| `allowedChannelPlugins` | `object[]?` | Channel plugin allowlist |

#### Memory & Files
| Field | Type | Description |
|-------|------|-------------|
| `autoMemoryEnabled` | `boolean?` | Enable auto-memory |
| `autoMemoryDirectory` | `string?` | Custom auto-memory path |
| `autoDreamEnabled` | `boolean?` | Enable background memory consolidation |
| `claudeMdExcludes` | `string[]?` | Glob patterns to exclude CLAUDE.md files |
| `plansDirectory` | `string?` | Custom plans directory |
| `fileSuggestion` | `object?` | Custom file suggestion for `@` mentions |
| `respectGitignore` | `boolean?` | File picker respects `.gitignore` (default: true) |

#### Worktree & Git
| Field | Type | Description |
|-------|------|-------------|
| `worktree.symlinkDirectories` | `string[]?` | Directories to symlink in worktrees |
| `worktree.sparsePaths` | `string[]?` | Sparse-checkout paths for worktrees |

#### Updates & Miscellaneous
| Field | Type | Description |
|-------|------|-------------|
| `autoUpdatesChannel` | `enum?` | Release channel (`latest`/`stable`) |
| `minimumVersion` | `string?` | Prevents downgrades |
| `skipWebFetchPreflight` | `boolean?` | Skip WebFetch blocklist check |
| `feedbackSurveyRate` | `number?` | Survey appearance probability (0-1) |
| `agent` | `string?` | Named agent for main thread |
| `$schema` | `literal?` | JSON Schema reference URL |

### Schema Features
- **`lazySchema()`**: Deferred schema creation to avoid circular import issues
- **`.passthrough()`**: Unknown fields preserved (forward compatibility)
- **`.catch(undefined)`**: Invalid values degrade gracefully instead of breaking entire file
- **Feature gates**: Fields conditionally included based on `feature()` flags (`TRANSCRIPT_CLASSIFIER`, `KAIROS`, `VOICE_MODE`, `LODESTONE`, `PROACTIVE`)
- **`z.preprocess()`**: Used for `strictPluginOnlyCustomization` to silently drop unknown surface names (forward compatibility)
- **Backward compatibility**: `.optional()` on all fields; test suite (`backward-compatibility.test.ts`) guards against breaking changes

---

## 5. Merge Behavior

### Array Merge Strategy
Arrays are **concatenated and deduplicated** (via `settingsMergeCustomizer`):
```typescript
function mergeArrays<T>(targetArray: T[], sourceArray: T[]): T[] {
  return uniq([...targetArray, ...sourceArray])
}
```

### Object Merge Strategy
Objects are **deep merged** via lodash `mergeWith` (recursive property merge).

### Update/Delete Strategy
When updating settings via `updateSettingsForSource()`:
- Arrays are **replaced entirely** (caller computes final state)
- `undefined` values are treated as **deletions** (key removed from object)
- Other values use default lodash merge behavior

### Cowork Mode
When `--cowork` flag or `CLAUDE_CODE_USE_COWORK_PLUGINS` env is set, user settings read from `cowork_settings.json` instead of `settings.json`.

---

## 6. Caching Architecture

### Three-Tier Cache (`settingsCache.ts`)

| Tier | Key | Stores | Invalidation |
|------|-----|--------|--------------|
| Session cache | singleton | Merged `SettingsWithErrors` from all sources | `resetSettingsCache()` |
| Per-source cache | `Map<SettingSource>` | `SettingsJson \| null` per source | `resetSettingsCache()` |
| Per-file cache | `Map<string>` | Parsed file result (settings + errors) | `resetSettingsCache()` |
| Plugin base | singleton | `Record<string, unknown>` from plugin loader | `clearPluginSettingsBase()` |

All three caches are cleared atomically by `resetSettingsCache()`. The centralized invalidation in `changeDetector.fanOut()` prevents N-way thrashing (previously N listeners each clearing cache caused N disk reloads per notification).

---

## 7. Change Detection (`changeDetector.ts`)

### Filesystem Watching
- **Engine**: `chokidar` with `awaitWriteFinish` (1000ms stability, 500ms poll)
- **Events**: `change`, `unlink` (deletion), `add` (creation/re-creation)
- **Internal write suppression**: `internalWrites.ts` tracks timestamps; changes within 5s of `markInternalWrite()` are ignored
- **Deletion grace period**: 1700ms window absorbs delete-and-recreate patterns (auto-updater, session startup)
- **Skip**: `flagSettings` not watched (CLI-provided, may be in `$TMPDIR` with special files)

### MDM Polling
- **Interval**: 30 minutes (`MDM_POLL_INTERVAL_MS`)
- **Mechanism**: Re-runs subprocess reads (`plutil`/`reg query`), compares JSON snapshot
- **Timer**: Uses `.unref()` so it doesn't keep the process alive

### Hook Integration
File changes trigger `executeConfigChangeHooks()` before applying. If hook returns exit code 2 or `decision: 'block'`, the change is rejected.

### Signal Pattern
Uses `createSignal<[source: SettingSource]>()` for pub/sub notification. Subscribers include:
- `useSettingsChange` React hook (interactive mode)
- `applySettingsChange` (headless/SDK mode)

---

## 8. MDM Integration (`mdm/` subsystem)

### Architecture (3-file split for startup performance)

```
constants.ts  — Zero heavy imports (only `os`), shared by both modules
     ↓
rawRead.ts    — Subprocess I/O only, fires at main.tsx module evaluation time
     ↓
settings.ts   — Parsing, caching, first-source-wins logic
```

### Startup Sequence
1. `startMdmRawRead()` fires at `main.tsx` module evaluation (before event loop)
2. Subprocess (`plutil` or `reg query`) runs in parallel with module loading
3. `ensureMdmSettingsLoaded()` awaited before first settings read
4. `consumeRawReadResult()` parses stdout into validated `MdmResult`

### macOS MDM
- Reads plist via `/usr/bin/plutil -convert json -o - -- {path}`
- Priority: per-user managed prefs > device-level managed prefs > user prefs (ant-only)
- `existsSync()` fast-path skips plutil spawn for non-MDM machines (~5ms saving)

### Windows MDM
- HKLM and HKCU read in parallel via `reg query ... /v Settings`
- JSON blob stored as `REG_SZ` or `REG_EXPAND_SZ` value
- Registry paths under `SOFTWARE\Policies` (WOW64 shared, no 32/64-bit redirection)

### Linux MDM
No OS-level MDM equivalent; uses file-based `managed-settings.json` only.

---

## 9. Permission Validation (`permissionValidation.ts`)

### Rule Format
```
ToolName(pattern)    — tool with content pattern
ToolName             — tool without pattern (all invocations)
mcp__server__tool    — MCP server-specific rule
```

### Validation Rules
- Tool names must start with uppercase
- Parentheses must be balanced (escape-aware)
- Empty parentheses rejected with suggestion
- MCP rules cannot have parenthesized patterns
- Bash tools: `:*` must be at end (legacy prefix syntax); wildcards allowed anywhere
- File tools: `:*` syntax rejected (Bash-only); wildcard placement checked
- Custom validators: `WebSearch` (no wildcards), `WebFetch` (must use `domain:` prefix)

### Tool Validation Config
```typescript
filePatternTools: ['Read', 'Write', 'Edit', 'Glob', 'NotebookRead', 'NotebookEdit']
bashPrefixTools: ['Bash']
customValidation: { WebSearch: ..., WebFetch: ... }
```

---

## 10. Security Design

### Project Settings Exclusions (RCE Prevention)
`projectSettings` is intentionally excluded from security-sensitive checks:

| Feature | Excluded From projectSettings | Reason |
|---------|------------------------------|--------|
| `skipDangerousModePermissionPrompt` | Yes | Malicious project could auto-bypass permissions |
| `skipAutoPermissionPrompt` | Yes | Could auto-bypass auto mode dialog |
| `autoMode` classifier rules | Yes | Could inject classifier allow/deny rules |
| `useAutoModeDuringPlan` | Yes | Could control plan mode behavior |
| `autoMemoryDirectory` | Yes | Could redirect memory storage |

### Admin Trust Model
`strictPluginOnlyCustomization` blocks user/project sources for specified surfaces. Admin-trusted sources:
- `plugin` (gated by `strictKnownMarketplaces`)
- `policySettings` (admin-controlled by definition)
- `built-in` / `builtin` / `bundled` (ships with CLI)

### Settings File Edit Validation
`validateEditTool.ts` intercepts Edit tool calls targeting settings files:
- If file was valid before edit, ensures it remains valid after
- If file was already invalid, allows edit (doesn't block fixing)
- Returns full JSON schema on validation failure

---

## 11. Exported API Surface

### Primary Settings Access
| Function | Module | Description |
|----------|--------|-------------|
| `getInitialSettings()` | `settings.ts` | Returns merged settings snapshot (cached) |
| `getSettings_DEPRECATED()` | `settings.ts` | Alias for `getInitialSettings()` |
| `getSettingsWithErrors()` | `settings.ts` | Merged settings + validation errors (cached) |
| `getSettingsWithSources()` | `settings.ts` | Effective settings + per-source breakdown (fresh read) |
| `getSettingsWithAllErrors()` | `allErrors.ts` | Settings + MCP config errors combined |
| `getSettingsForSource(source)` | `settings.ts` | Single source settings (cached) |

### Settings Modification
| Function | Module | Description |
|----------|--------|-------------|
| `updateSettingsForSource(source, settings)` | `settings.ts` | Merge + write to source file |
| `applySettingsChange(source, setAppState)` | `applySettingsChange.ts` | Apply change to AppState |

### Source Information
| Function | Module | Description |
|----------|--------|-------------|
| `getSettingsFilePathForSource(source)` | `settings.ts` | Absolute file path for source |
| `getSettingsRootPathForSource(source)` | `settings.ts` | Root directory for source |
| `getRelativeSettingsFilePathForSource(source)` | `settings.ts` | Relative path (project/local) |
| `getPolicySettingsOrigin()` | `settings.ts` | Which policy source is active |
| `getManagedFileSettingsPresence()` | `settings.ts` | Whether base/drop-in files exist |

### Security Checks
| Function | Module | Description |
|----------|--------|-------------|
| `hasSkipDangerousModePermissionPrompt()` | `settings.ts` | Bypass permissions accepted (trusted sources only) |
| `hasAutoModeOptIn()` | `settings.ts` | Auto mode opted in (trusted sources only) |
| `getUseAutoModeDuringPlan()` | `settings.ts` | Plan mode auto semantics (default: true) |
| `getAutoModeConfig()` | `settings.ts` | Merged auto mode classifier config |
| `isRestrictedToPluginOnly(surface)` | `pluginOnlyPolicy.ts` | Surface locked to plugins only |
| `isSourceAdminTrusted(source)` | `pluginOnlyPolicy.ts` | Source bypasses plugin-only lock |

### Validation
| Function | Module | Description |
|----------|--------|-------------|
| `validateSettingsFileContent(content)` | `validation.ts` | Validate JSON against strict schema |
| `validatePermissionRule(rule)` | `permissionValidation.ts` | Validate single permission rule |
| `validateInputForSettingsFileEdit(...)` | `validateEditTool.ts` | Pre-edit validation guard |
| `generateSettingsJSONSchema()` | `schemaOutput.ts` | Full JSON Schema from Zod |

### Change Detection
| Function | Module | Description |
|----------|--------|-------------|
| `settingsChangeDetector.initialize()` | `changeDetector.ts` | Start filesystem watcher + MDM poll |
| `settingsChangeDetector.dispose()` | `changeDetector.ts` | Stop watcher and timers |
| `settingsChangeDetector.subscribe(cb)` | `changeDetector.ts` | Subscribe to settings changes |
| `settingsChangeDetector.notifyChange(source)` | `changeDetector.ts` | Programmatic change notification |
| `resetSettingsCache()` | `settingsCache.ts` | Invalidate all caches |

### MDM
| Function | Module | Description |
|----------|--------|-------------|
| `startMdmRawRead()` | `mdm/rawRead.ts` | Fire startup subprocess reads |
| `startMdmSettingsLoad()` | `mdm/settings.ts` | Begin async MDM load |
| `ensureMdmSettingsLoaded()` | `mdm/settings.ts` | Await MDM load completion |
| `getMdmSettings()` | `mdm/settings.ts` | Cached admin MDM settings |
| `getHkcuSettings()` | `mdm/settings.ts` | Cached HKCU settings |
| `refreshMdmSettings()` | `mdm/settings.ts` | Fresh MDM read (for polling) |

---

## 12. Drop-in Policy Fragments

The `managed-settings.d/` directory supports systemd/sudoers-style drop-in fragments:

```
/Library/Application Support/ClaudeCode/
├── managed-settings.json          ← base (lowest precedence)
└── managed-settings.d/
    ├── 10-otel.json               ← alphabetically merged on top
    ├── 20-security.json
    └── 30-custom-hooks.json       ← highest among drop-ins
```

- Base file merged first, then drop-ins in alphabetical order (later wins)
- Teams can ship independent policy fragments without coordinating edits
- Hidden files (`.` prefix) and non-`.json` files are ignored
- Symlinks are followed

---

## 13. Backward Compatibility Strategy

From `types.ts` header comments:

| Change Type | Allowed? | Approach |
|-------------|----------|----------|
| Add optional fields | Yes | Always use `.optional()` |
| Add enum values | Yes | Keep existing values |
| Remove fields | No | Mark deprecated instead |
| Remove enum values | No | Breaking change |
| Make optional required | No | Breaking change |
| Make types restrictive | No | Breaking change |
| Rename fields | No | Keep old name too |
| Unknown fields | Preserved | `.passthrough()` on schema |
| Invalid field values | Preserved in file | Not used but not deleted |
| Type coercion | Yes | `z.coerce` for env vars |
| Forward-compat preprocess | Yes | Drop unknown enum values silently |

Test suite: `backward-compatibility.test.ts` guards against breaking changes.

---

## 14. Key Architectural Decisions

### Circular Dependency Resolution
- `allErrors.ts` exists solely to break `settings.ts → mcp/config.ts → settings.ts` cycle
- `internalWrites.ts` extracted to break `settings.ts → changeDetector.ts → hooks.ts → settings.ts` cycle
- MDM split into 3 files (`constants.ts` → `rawRead.ts` → `settings.ts`) for zero-heavy-import startup

### Cache Invalidation Centralization
Previously each listener reset cache independently, causing N disk reloads per notification. Now `fanOut()` resets once, first listener pays the miss, subsequent ones hit cache.

### Internal Write Suppression
`markInternalWrite()` called before `writeFileSyncAndFlush_DEPRECATED()`. The chokidar handler checks via `consumeInternalWrite()` within a 5-second window. Mark is consumed on match to avoid suppressing the next real external change.

### Deletion Grace Period
1700ms grace window (stability threshold + poll interval + 200ms) handles delete-and-recreate patterns common during auto-updates. If `add`/`change` fires within the window, deletion is cancelled.

---

## 15. Dependency Graph

```
settings.ts ──────┬── constants.ts
                   ├── types.ts ──── permissionValidation.ts
                   │                      └── toolValidationConfig.ts
                   ├── settingsCache.ts
                   ├── managedPath.ts
                   ├── internalWrites.ts
                   ├── validation.ts ──── validationTips.ts
                   │                 └── schemaOutput.ts
                   └── mdm/settings.ts ──── mdm/rawRead.ts
                                       └── mdm/constants.ts

changeDetector.ts ── settings.ts
                  ── settingsCache.ts
                  ── internalWrites.ts
                  ── mdm/settings.ts

applySettingsChange.ts ── settings.ts
allErrors.ts ── settings.ts (breaks circular dep)
pluginOnlyPolicy.ts ── settings.ts
validateEditTool.ts ── validation.ts
```

---

## 16. Verification Confidence

| Aspect | Confidence | Evidence |
|--------|------------|---------|
| Source precedence order | 9.5/10 | Explicit in `SETTING_SOURCES` array and `loadSettingsFromDisk()` |
| Policy sub-precedence | 9.5/10 | Clear first-source-wins logic with comments |
| Schema fields | 9.0/10 | All 60+ fields documented from direct Zod schema reading |
| MDM integration | 9.5/10 | Full subprocess flow traced from rawRead through parsing |
| Cache architecture | 9.5/10 | Three-tier cache with centralized invalidation verified |
| Security exclusions | 9.5/10 | projectSettings exclusion confirmed in multiple functions |
| Change detection | 9.0/10 | Chokidar config, deletion grace, internal write suppression verified |
| Overall | **9.3/10** | Complete reading of all 19 files |

# Wave 3 Command Verification — Batch 2 (Commands 18-35)

> Generated: 2026-04-01 | Source: `CC-Source/src/commands/*/index.ts` (or `.js` stubs) | Verifier: Claude Opus 4.6

---

## Methodology

Each command directory's `index.ts` (or `index.js` fallback) was read directly. Fields extracted: registered name, description, type, aliases, availability, isHidden, isEnabled, feature-gating. Cross-referenced against existing `command-system.md` catalog.

---

## Verification Table

| # | Directory | Registered Name | Description | Type | Category | Interactive (JSX)? | Feature-Gated? | Hidden? | Notes |
|---|-----------|----------------|-------------|------|----------|-------------------|----------------|---------|-------|
| 18 | `cost/` | `cost` | Show the total cost and duration of the current session | local | Account | No | No (conditional hide) | Dynamic: hidden for claude-ai subscribers, visible for `ant` users | `isHidden` = `isClaudeAISubscriber()` unless `USER_TYPE=ant` |
| 19 | `ctx_viz/` | `stub` | *(none — stubbed out)* | *(stub)* | Internal/Debug | No | `isEnabled: () => false` | **Yes** (always) | JS-only stub; eliminated from external builds |
| 20 | `debug-tool-call/` | `stub` | *(none — stubbed out)* | *(stub)* | Internal/Debug | No | `isEnabled: () => false` | **Yes** (always) | JS-only stub; eliminated from external builds |
| 21 | `desktop/` | `desktop` | Continue the current session in Claude Desktop | local-jsx | Integrations | **Yes** | Platform-gated (macOS or Win64 only) | Dynamic: hidden on unsupported platforms | Aliases: `app`; Availability: `claude-ai` only |
| 22 | `diff/` | `diff` | View uncommitted changes and per-turn diffs | local-jsx | Navigation/UI | **Yes** | No | No | No aliases, no availability restriction |
| 23 | `doctor/` | `doctor` | Diagnose and verify your Claude Code installation and settings | local-jsx | System | **Yes** | Env-gated: `DISABLE_DOCTOR_COMMAND` | No | Disabled via env var only |
| 24 | `effort/` | `effort` | Set effort level for model usage | local-jsx | Config | **Yes** | No | No | `argumentHint: [low\|medium\|high\|max\|auto]`; dynamic `immediate` |
| 25 | `env/` | `stub` | *(none — stubbed out)* | *(stub)* | Internal/Debug | No | `isEnabled: () => false` | **Yes** (always) | JS-only stub; eliminated from external builds |
| 26 | `exit/` | `exit` | Exit the REPL | local-jsx | Navigation/UI | **Yes** | No | No | Aliases: `quit`; `immediate: true` |
| 27 | `export/` | `export` | Export the current conversation to a file or clipboard | local-jsx | Session | **Yes** | No | No | `argumentHint: [filename]` |
| 28 | `extra-usage/` | `extra-usage` | Configure extra usage to keep working when limits are hit | local-jsx / local | Account | **Yes** (interactive) / No (non-interactive) | Env + auth gated: `DISABLE_EXTRA_USAGE_COMMAND` + `isOverageProvisioningAllowed()` | Non-interactive variant hidden when interactive | Dual export: interactive JSX + non-interactive text variant |
| 29 | `fast/` | `fast` | Toggle fast mode (`FAST_MODE_MODEL_DISPLAY` only) | local-jsx | Config | **Yes** | Feature-gated: `isFastModeEnabled()` | Dynamic: hidden when fast mode not enabled | Availability: `claude-ai` + `console`; dynamic `immediate` |
| 30 | `feedback/` | `feedback` | Submit feedback about Claude Code | local-jsx | System | **Yes** | Multi-gated: Bedrock/Vertex/Foundry/env/privacy/policy/ant | No | Aliases: `bug`; `argumentHint: [report]`; disabled for ant users |
| 31 | `files/` | `files` | List all files currently in context | local | Navigation/UI | No | `isEnabled: () => USER_TYPE === 'ant'` | No (but ant-only) | Ant-internal only; `supportsNonInteractive: true` |
| 32 | `good-claude/` | `stub` | *(none — stubbed out)* | *(stub)* | Internal/Debug | No | `isEnabled: () => false` | **Yes** (always) | JS-only stub; eliminated from external builds |
| 33 | `heapdump/` | `heapdump` | Dump the JS heap to ~/Desktop | local | Debug | No | No | **Yes** (always) | Debug utility; `supportsNonInteractive: true` |
| 34 | `help/` | `help` | Show help and available commands | local-jsx | Navigation/UI | **Yes** | No | No | No aliases, no restrictions |
| 35 | `hooks/` | `hooks` | View hook configurations for tool events | local-jsx | Config | **Yes** | No | No | `immediate: true` |

---

## Cross-Reference with Existing Analysis (`command-system.md`)

### Confirmed Accurate

| # | Command | Existing Catalog Entry | Verdict |
|---|---------|----------------------|---------|
| 18 | `/cost` | "Show session cost" (Account & Auth) | **ACCURATE** — description slightly abbreviated but correct |
| 21 | `/desktop` | "Desktop handoff" (Agents & Tasks) | **ACCURATE** — real desc is "Continue the current session in Claude Desktop"; catalog is abbreviated |
| 22 | `/diff` | "View uncommitted changes and per-turn diffs" (Navigation & UI) → listed as "Show file changes" | **MINOR DISCREPANCY** — actual desc is more specific |
| 26 | `/exit` | "Exit the CLI" (Navigation & UI) | **MINOR DISCREPANCY** — actual desc is "Exit the REPL", not "the CLI" |
| 27 | `/export` | "Export conversation" (Session & History) | **ACCURATE** — abbreviated but correct |
| 31 | `/files` | "List tracked files" (Navigation & UI) | **MINOR DISCREPANCY** — actual desc is "List all files currently in context" |
| 34 | `/help` | "Show help screen" (Navigation & UI) | **MINOR DISCREPANCY** — actual desc is "Show help and available commands" |
| 35 | `/hooks` | "Manage hook scripts" (Configuration) | **DISCREPANCY** — actual desc is "View hook configurations for tool events" (view, not manage) |

### Confirmed in Internal-Only List

| # | Command | Listed in Internal-Only? | Verdict |
|---|---------|------------------------|---------|
| 19 | `/ctx_viz` | Yes | **CONFIRMED** — stub in external build |
| 20 | `/debug-tool-call` | Yes | **CONFIRMED** — stub in external build |
| 25 | `/env` | Yes | **CONFIRMED** — stub in external build |
| 32 | `/good-claude` | Yes | **CONFIRMED** — stub in external build |

### Not Previously Cataloged / Missing from Catalog

| # | Command | Status |
|---|---------|--------|
| 23 | `/doctor` | **MISSING** from catalog tables (mentioned nowhere in command-system.md tables) |
| 24 | `/effort` | Listed in Configuration table — **ACCURATE** ("Set reasoning effort level" vs actual "Set effort level for model usage") |
| 28 | `/extra-usage` | **MISSING** from catalog tables entirely |
| 29 | `/fast` | Listed in Configuration table — **ACCURATE** ("Toggle fast mode") |
| 30 | `/feedback` | **MISSING** from main catalog tables (only appears in REMOTE_SAFE_COMMANDS list) |
| 33 | `/heapdump` | **MISSING** from main catalog tables (only appears in COMMANDS() static list) |

---

## New Findings

### 1. Stub Pattern for Internal Commands
Commands `ctx_viz`, `debug-tool-call`, `env`, and `good-claude` use an identical JS-only stub pattern:
```js
export default { isEnabled: () => false, isHidden: true, name: 'stub' };
```
These directories exist in the source tree but are dead code in external builds. The `.ts` source files are stripped during build; only the `.js` stub remains.

### 2. Dual-Export Pattern (`extra-usage`)
`extra-usage` is unique in this batch: it exports **two** command objects — one `local-jsx` for interactive sessions and one `local` for non-interactive sessions. Both share the same registered name `extra-usage` but have different `type` and `load` targets.

### 3. Dynamic Description (`fast`)
The `/fast` command uses a getter for its description, incorporating `FAST_MODE_MODEL_DISPLAY` at runtime. This means the description changes based on which model is configured for fast mode.

### 4. Dynamic Hidden State
Commands `cost`, `desktop`, `fast`, and `extra-usage` all use dynamic `isHidden` getters that evaluate at runtime based on auth state, platform, or feature flags. These are not statically hidden.

### 5. `exit` Type Correction
The existing catalog lists `/exit` as `local` type. Actual source shows it is `local-jsx`. This is a **type error** in the existing analysis.

### 6. `export` Type Correction
The existing catalog lists `/export` as `local` type. Actual source shows it is `local-jsx`. This is a **type error** in the existing analysis.

### 7. Missing Commands in Catalog
`/doctor`, `/extra-usage`, `/feedback`, and `/heapdump` are missing from the main catalog tables in `command-system.md`. They appear only in code listings or footnotes.

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| Commands verified | 18 (18-35) |
| Active commands (real implementation) | 14 |
| Stubbed/dead commands | 4 (`ctx_viz`, `debug-tool-call`, `env`, `good-claude`) |
| JSX-interactive commands | 10 |
| Non-interactive (local) commands | 4 (cost, files, heapdump, extra-usage-noninteractive) |
| Always-hidden commands | 5 (4 stubs + heapdump) |
| Dynamically-hidden commands | 4 (cost, desktop, fast, extra-usage) |
| Catalog discrepancies found | 8 (2 type errors, 4 missing entries, 2 description mismatches) |
| New patterns documented | 5 (stub pattern, dual-export, dynamic desc, dynamic hidden, type corrections) |

---

## Corrections Required for `command-system.md`

1. **`/exit`**: Change type from `local` to `local-jsx`
2. **`/export`**: Change type from `local` to `local-jsx`
3. **`/diff`**: Update description from "Show file changes" to "View uncommitted changes and per-turn diffs"
4. **`/files`**: Update description from "List tracked files" to "List all files currently in context"
5. **`/help`**: Update description from "Show help screen" to "Show help and available commands"
6. **`/hooks`**: Update description from "Manage hook scripts" to "View hook configurations for tool events"
7. **Add `/doctor`** to System category table
8. **Add `/extra-usage`** to Account & Auth category table
9. **Add `/feedback`** to System category table (currently only in REMOTE_SAFE list)
10. **Add `/heapdump`** to Debug/Internal category with `isHidden: true` note

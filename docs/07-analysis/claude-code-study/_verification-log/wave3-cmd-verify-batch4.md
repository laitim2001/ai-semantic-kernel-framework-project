# Wave 3 Command Verification — Batch 4 (Commands 53–69)

> Verified: 2026-04-01 | Source: `CC-Source/src/commands/*/index.ts` | Verifier: Claude Opus 4.6

---

## Verification Matrix

| # | Dir Name | Registered Name | Type | Description (from source) | Aliases | Hidden? | Feature-Gated? | Interactive? | Notes |
|---|----------|----------------|------|---------------------------|---------|---------|----------------|--------------|-------|
| 53 | `permissions/` | `permissions` | local-jsx | Manage allow & deny tool permission rules | `allowed-tools` | No | No | Yes (JSX) | |
| 54 | `plan/` | `plan` | local-jsx | Enable plan mode or view the current session plan | — | No | No | Yes (JSX) | argumentHint: `[open\|<description>]` |
| 55 | `plugin/` | `plugin` | local-jsx | Manage Claude Code plugins | `plugins`, `marketplace` | No | No | Yes (JSX) | `immediate: true`; source file is `index.tsx` |
| 56 | `pr_comments/` | `pr-comments` | prompt | Get comments from a GitHub pull request | — | No | No | No (prompt) | Uses `createMovedToPluginCommand` pattern; ant users redirected to plugin |
| 57 | `privacy-settings/` | `privacy-settings` | local-jsx | View and update your privacy settings | — | No | Yes — `isConsumerSubscriber()` | Yes (JSX) | |
| 58 | `rate-limit-options/` | `rate-limit-options` | local-jsx | Show options when rate limit is reached | — | **Yes** (`isHidden: true`) | Yes — `isClaudeAISubscriber()` | Yes (JSX) | Internal-only; comment says "only used internally" |
| 59 | `release-notes/` | `release-notes` | local | View release notes | — | No | No | No (`supportsNonInteractive: true`) | |
| 60 | `reload-plugins/` | `reload-plugins` | local | Activate pending plugin changes in the current session | — | No | No | Yes (`supportsNonInteractive: false`) | SDK callers use `query.reloadPlugins()` instead |
| 61 | `remote-env/` | `remote-env` | local-jsx | Configure the default remote environment for teleport sessions | — | Conditional (`!isClaudeAISubscriber() \|\| !isPolicyAllowed('allow_remote_sessions')`) | Yes — `isClaudeAISubscriber() && isPolicyAllowed('allow_remote_sessions')` | Yes (JSX) | |
| 62 | `remote-setup/` | `web-setup` | local-jsx | Setup Claude Code on the web (requires connecting your GitHub account) | — | Conditional (`!isPolicyAllowed('allow_remote_sessions')`) | Yes — feature flag `tengu_cobalt_lantern` + `isPolicyAllowed('allow_remote_sessions')` | Yes (JSX) | `availability: ['claude-ai']`; registered name differs from directory name |
| 63 | `rename/` | `rename` | local-jsx | Rename the current conversation | — | No | No | Yes (JSX) | `immediate: true`; argumentHint: `[name]` |
| 64 | `reset-limits/` | `stub` | — | — | — | **Yes** | Yes (`isEnabled: () => false`) | — | **Stubbed out** — `index.js` exports a disabled hidden stub; likely dead-code-eliminated in external builds |
| 65 | `resume/` | `resume` | local-jsx | Resume a previous conversation | `continue` | No | No | Yes (JSX) | argumentHint: `[conversation id or search term]` |
| 66 | `review.ts` | `review` | prompt | Review a pull request | — | No | No | No (prompt) | Defined in `src/commands/review.ts` (not inside `review/` dir). Also exports `ultrareview` command |
| 66b | `review.ts` | `ultrareview` | local-jsx | ~10–20 min · Finds and verifies bugs in your branch. Runs in Claude Code on the web. | — | No | Yes — `isUltrareviewEnabled()` | Yes (JSX) | Sibling export from same file; remote bughunter path |
| 67 | `rewind/` | `rewind` | local | Restore the code and/or conversation to a previous point | `checkpoint` | No | No | Yes (`supportsNonInteractive: false`) | |
| 68 | `sandbox-toggle/` | `sandbox` | local-jsx | Dynamic description showing sandbox status + `(⏎ to configure)` | — | Conditional (`!isSupportedPlatform() \|\| !isPlatformInEnabledList()`) | No (but platform-gated via isHidden) | Yes (JSX) | `immediate: true`; argumentHint: `exclude "command pattern"` |
| 69 | `session/` | `session` | local-jsx | Show remote session URL and QR code | `remote` | Conditional (`!getIsRemoteMode()`) | Yes — `getIsRemoteMode()` | Yes (JSX) | Only visible/enabled in remote mode |

---

## Discrepancies vs. Existing Analysis (`command-system.md`)

| # | Field | Existing Analysis Says | Source Code Says | Severity |
|---|-------|----------------------|------------------|----------|
| 54 | Type | `local` | **`local-jsx`** | MEDIUM — type wrong in catalog |
| 56 | Name | `pr_comments` | **`pr-comments`** (hyphenated, via `createMovedToPluginCommand`) | LOW — name uses hyphen not underscore |
| 62 | Name | (not listed) | **`web-setup`** (dir is `remote-setup/`) | HIGH — command missing from catalog entirely |
| 64 | Category | Listed as internal-only ant command | **Stubbed out** (`isEnabled: false`, `isHidden: true`, name: `stub`) | MEDIUM — not just ant-only, it's a dead stub |
| 66 | — | (no entry) | `ultrareview` is a **separate command** exported from `review.ts` | HIGH — `ultrareview` missing from catalog |
| 68 | Name | (not listed explicitly) | **`sandbox`** (dir is `sandbox-toggle/`) | MEDIUM — registered name differs from dir name |
| 58 | Category | (not listed in any category) | `rate-limit-options` is hidden + internally used | LOW — correctly omitted from user-facing catalog but should be in internal list |
| 63 | Type | `local` (in Session & History) | **`local-jsx`** | MEDIUM — type wrong in catalog |
| 175 | Description | "Manage permission rules" | "Manage allow & deny tool permission rules" | LOW — description truncated but acceptable |
| 176 | Description | "Toggle plan mode" | "Enable plan mode or view the current session plan" | LOW — description truncated but acceptable |
| 177 | Name | `privacySettings` (camelCase) | **`privacy-settings`** (kebab-case) | MEDIUM — name format wrong in catalog |

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Commands verified | 17 (+ 1 bonus: `ultrareview`) |
| Exact match (name + type + description) | 8 / 17 |
| Type mismatches | 2 (`plan`, `rename` listed as `local` but are `local-jsx`) |
| Name mismatches | 3 (`pr_comments` → `pr-comments`, `privacySettings` → `privacy-settings`, `sandbox-toggle` → `sandbox`) |
| Missing from catalog | 2 (`web-setup`, `ultrareview`) |
| Stubbed/dead commands | 1 (`reset-limits` → stub) |
| Hidden commands found | 3 (`rate-limit-options`, `reset-limits` stub, conditionally: `remote-env`, `sandbox`, `session`) |
| Feature-gated commands | 6 (`privacy-settings`, `rate-limit-options`, `remote-env`, `web-setup`, `ultrareview`, `session`) |
| Commands with aliases | 5 (`permissions`, `plugin`, `resume`, `rewind`, `session`) |

---

## Key Findings

1. **`plan` and `rename` are `local-jsx`, not `local`** — The existing catalog has their types wrong. Both use lazy-loaded JSX components.

2. **`web-setup` command is missing from the catalog** — The `remote-setup/` directory registers as `/web-setup` with `availability: ['claude-ai']` and dual feature gates (GrowthBook flag + policy). This is a user-facing command not documented.

3. **`ultrareview` is a distinct command** — Exported alongside `/review` from `review.ts`, it launches a remote bughunter session (10-20 min) on Claude Code on the web with overage billing gates. Not in catalog.

4. **`reset-limits` is a dead stub** — The `index.js` exports `{ isEnabled: () => false, isHidden: true, name: 'stub' }`. This is not a real command; it's dead-code-eliminated in external builds.

5. **Name format inconsistencies in catalog** — `privacySettings` should be `privacy-settings`; `pr_comments` should be `pr-comments`. The registered names use kebab-case consistently.

6. **`sandbox-toggle/` registers as `/sandbox`** — The directory name and registered name differ. The description is dynamic (computed getter showing current sandbox status).

7. **`createMovedToPluginCommand` pattern** — `pr-comments` uses this factory which redirects ant-internal users to a marketplace plugin while providing a fallback prompt for external users.

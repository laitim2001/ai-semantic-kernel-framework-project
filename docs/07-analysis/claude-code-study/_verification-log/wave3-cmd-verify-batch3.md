# Wave 3 Command Verification -- Batch 3 (Commands 36-52)

> Verified: 2026-04-01 | Source: `CC-Source/src/commands/*/index.ts` (or `.js` for stubs)
> Verifier: Claude Opus 4.6 | Batch: 36-52 (17 commands)

---

## Summary

| Metric | Value |
|--------|-------|
| **Commands verified** | 17 |
| **Real commands (with .ts source)** | 12 |
| **Stubbed commands (ant-only, .js only)** | 5 |
| **Discrepancies found vs existing analysis** | 4 |
| **New findings** | 3 |

---

## Per-Command Verification

### 36. ide

| Field | Value |
|-------|-------|
| **Registered name** | `ide` |
| **Description** | "Manage IDE integrations and show status" |
| **Type** | `local-jsx` |
| **Category** | Configuration / IDE |
| **Interactive?** | Yes (JSX UI) |
| **Feature-gated?** | No |
| **Hidden?** | No |
| **argumentHint** | `[open]` |

**Existing analysis**: Listed under "Configuration" category as `/ide`. Description not explicitly listed in command-system.md catalog tables but referenced in `COMMANDS()` list. **MATCH** -- correctly identified.

---

### 37. install-github-app

| Field | Value |
|-------|-------|
| **Registered name** | `install-github-app` |
| **Description** | "Set up Claude GitHub Actions for a repository" |
| **Type** | `local-jsx` |
| **Category** | Integration / CI-CD |
| **Interactive?** | Yes (JSX UI) |
| **Feature-gated?** | Yes -- `isEnabled: () => !isEnvTruthy(process.env.DISABLE_INSTALL_GITHUB_APP_COMMAND)` |
| **Hidden?** | No |
| **Availability** | `['claude-ai', 'console']` (both auth types) |

**Existing analysis**: NOT listed in command-system.md catalog. **MISSING** from existing analysis.

---

### 38. install-slack-app

| Field | Value |
|-------|-------|
| **Registered name** | `install-slack-app` |
| **Description** | "Install the Claude Slack app" |
| **Type** | `local` |
| **Category** | Integration / Slack |
| **Interactive?** | No (`supportsNonInteractive: false` means it requires interactive mode but returns text, not JSX) |
| **Feature-gated?** | No |
| **Hidden?** | No |
| **Availability** | `['claude-ai']` (Claude.ai OAuth only) |

**Existing analysis**: NOT listed in command-system.md catalog. **MISSING** from existing analysis.

---

### 39. issue

| Field | Value |
|-------|-------|
| **Registered name** | `stub` |
| **Description** | (none -- stubbed) |
| **Type** | (none -- stubbed) |
| **Category** | Internal / Ant-only |
| **Interactive?** | N/A |
| **Feature-gated?** | `isEnabled: () => false` |
| **Hidden?** | Yes (`isHidden: true`) |

**Existing analysis**: Listed as internal-only ant-only command. **MATCH** -- correctly listed under "Internal-Only Commands (ant-only)" as `/issue`.

---

### 40. keybindings

| Field | Value |
|-------|-------|
| **Registered name** | `keybindings` |
| **Description** | "Open or create your keybindings configuration file" |
| **Type** | `local` |
| **Category** | Configuration |
| **Interactive?** | No (`supportsNonInteractive: false` -- requires interactive but returns text) |
| **Feature-gated?** | Yes -- `isEnabled: () => isKeybindingCustomizationEnabled()` |
| **Hidden?** | No |

**Existing analysis**: Listed as `local-jsx` type in command-system.md. **DISCREPANCY** -- actual type is `local`, not `local-jsx`. Description in existing analysis is "Manage keyboard shortcuts" vs actual "Open or create your keybindings configuration file".

---

### 41. login

| Field | Value |
|-------|-------|
| **Registered name** | `login` |
| **Description** | Dynamic: "Switch Anthropic accounts" (if has API key) or "Sign in with your Anthropic account" (default) |
| **Type** | `local-jsx` |
| **Category** | Account & Auth |
| **Interactive?** | Yes (JSX UI) |
| **Feature-gated?** | Yes -- `isEnabled: () => !isEnvTruthy(process.env.DISABLE_LOGIN_COMMAND)` |
| **Hidden?** | No |
| **Export pattern** | Factory function `() => ({...})` (not static object) -- description is computed at call time |

**Existing analysis**: Listed as `local-jsx` under "Account & Auth" with description "OAuth login". **PARTIAL MATCH** -- type correct; description is simplified. The dynamic description behavior is not documented.

---

### 42. logout

| Field | Value |
|-------|-------|
| **Registered name** | `logout` |
| **Description** | "Sign out from your Anthropic account" |
| **Type** | `local-jsx` |
| **Category** | Account & Auth |
| **Interactive?** | Yes (JSX UI) |
| **Feature-gated?** | Yes -- `isEnabled: () => !isEnvTruthy(process.env.DISABLE_LOGOUT_COMMAND)` |
| **Hidden?** | No |

**Existing analysis**: Listed as `local` type under "Account & Auth" with description "OAuth logout". **DISCREPANCY** -- actual type is `local-jsx`, not `local`. Description in existing analysis is "OAuth logout" vs actual "Sign out from your Anthropic account".

---

### 43. mcp

| Field | Value |
|-------|-------|
| **Registered name** | `mcp` |
| **Description** | "Manage MCP servers" |
| **Type** | `local-jsx` |
| **Category** | MCP & Plugins |
| **Interactive?** | Yes (JSX UI) |
| **Feature-gated?** | No |
| **Hidden?** | No |
| **immediate** | `true` |
| **argumentHint** | `[enable|disable [server-name]]` |

**Existing analysis**: Listed as `local-jsx` with description "Manage MCP servers". **MATCH**.

---

### 44. memory

| Field | Value |
|-------|-------|
| **Registered name** | `memory` |
| **Description** | "Edit Claude memory files" |
| **Type** | `local-jsx` |
| **Category** | Configuration / Memory |
| **Interactive?** | Yes (JSX UI) |
| **Feature-gated?** | No |
| **Hidden?** | No |

**Existing analysis**: Not explicitly listed in catalog tables of command-system.md. Present in the `COMMANDS()` registration list. **PARTIAL** -- exists in registration but no catalog row.

---

### 45. mobile

| Field | Value |
|-------|-------|
| **Registered name** | `mobile` |
| **Description** | "Show QR code to download the Claude mobile app" |
| **Type** | `local-jsx` |
| **Category** | Agents & Tasks |
| **Interactive?** | Yes (JSX UI) |
| **Feature-gated?** | No |
| **Hidden?** | No |
| **Aliases** | `['ios', 'android']` |

**Existing analysis**: Listed as `local-jsx` with description "Mobile QR code". **MATCH** -- but aliases `ios`/`android` not documented.

---

### 46. mock-limits

| Field | Value |
|-------|-------|
| **Registered name** | `stub` |
| **Description** | (none -- stubbed) |
| **Type** | (none -- stubbed) |
| **Category** | Internal / Ant-only |
| **Interactive?** | N/A |
| **Feature-gated?** | `isEnabled: () => false` |
| **Hidden?** | Yes (`isHidden: true`) |

**Existing analysis**: Listed under "Internal-Only Commands (ant-only)" as `/mock-limits`. **MATCH**.

---

### 47. model

| Field | Value |
|-------|-------|
| **Registered name** | `model` |
| **Description** | Dynamic: ``Set the AI model for Claude Code (currently ${renderModelName(getMainLoopModel())})`` |
| **Type** | `local-jsx` |
| **Category** | Configuration |
| **Interactive?** | Yes (JSX UI) |
| **Feature-gated?** | No |
| **Hidden?** | No |
| **immediate** | Dynamic via `shouldInferenceConfigCommandBeImmediate()` |
| **argumentHint** | `[model]` |

**Existing analysis**: Listed as `local-jsx` with description "Change model". **PARTIAL MATCH** -- type correct; dynamic description with current model name not documented.

---

### 48. oauth-refresh

| Field | Value |
|-------|-------|
| **Registered name** | `stub` |
| **Description** | (none -- stubbed) |
| **Type** | (none -- stubbed) |
| **Category** | Internal / Ant-only |
| **Interactive?** | N/A |
| **Feature-gated?** | `isEnabled: () => false` |
| **Hidden?** | Yes (`isHidden: true`) |

**Existing analysis**: Listed under "Internal-Only Commands (ant-only)" as `/oauth-refresh`. **MATCH**.

---

### 49. onboarding

| Field | Value |
|-------|-------|
| **Registered name** | `stub` |
| **Description** | (none -- stubbed) |
| **Type** | (none -- stubbed) |
| **Category** | Internal / Ant-only |
| **Interactive?** | N/A |
| **Feature-gated?** | `isEnabled: () => false` |
| **Hidden?** | Yes (`isHidden: true`) |

**Existing analysis**: Listed under "Internal-Only Commands (ant-only)" as `/onboarding`. **MATCH**.

---

### 50. output-style

| Field | Value |
|-------|-------|
| **Registered name** | `output-style` |
| **Description** | "Deprecated: use /config to change output style" |
| **Type** | `local-jsx` |
| **Category** | Configuration (deprecated) |
| **Interactive?** | Yes (JSX UI) |
| **Feature-gated?** | No |
| **Hidden?** | Yes (`isHidden: true`) |

**Existing analysis**: Listed as `local-jsx` under "Configuration" with description "Change output style" and name `/outputStyle`. **DISCREPANCY** -- (1) actual registered name is `output-style` (kebab-case), not `outputStyle` (camelCase); (2) actual description says "Deprecated: use /config to change output style"; (3) it is hidden (`isHidden: true`), not documented as hidden in existing analysis.

---

### 51. passes

| Field | Value |
|-------|-------|
| **Registered name** | `passes` |
| **Description** | Dynamic: "Share a free week of Claude Code with friends and earn extra usage" (if referrer reward exists) or "Share a free week of Claude Code with friends" (default) |
| **Type** | `local-jsx` |
| **Category** | Account & Auth / Referral |
| **Interactive?** | Yes (JSX UI) |
| **Feature-gated?** | No explicit `isEnabled`, but `isHidden` is dynamic based on `checkCachedPassesEligibility()` |
| **Hidden?** | Dynamic -- hidden unless user is eligible AND cache exists |

**Existing analysis**: Listed as `local` under "Account & Auth" with description "Show pass usage". **DISCREPANCY** -- (1) actual type is `local-jsx`, not `local`; (2) description is about sharing/referrals, not "Show pass usage"; (3) dynamic hidden state not documented.

---

### 52. perf-issue

| Field | Value |
|-------|-------|
| **Registered name** | `stub` |
| **Description** | (none -- stubbed) |
| **Type** | (none -- stubbed) |
| **Category** | Internal / Ant-only |
| **Interactive?** | N/A |
| **Feature-gated?** | `isEnabled: () => false` |
| **Hidden?** | Yes (`isHidden: true`) |

**Existing analysis**: Listed under "Internal-Only Commands (ant-only)" as `/perf-issue`. **MATCH**.

---

## Discrepancy Summary

| # | Command | Field | Existing Analysis | Actual Source | Severity |
|---|---------|-------|-------------------|---------------|----------|
| 1 | `/keybindings` | type | `local-jsx` | `local` | Medium -- incorrect type |
| 2 | `/logout` | type | `local` | `local-jsx` | Medium -- incorrect type |
| 3 | `/output-style` | name | `outputStyle` | `output-style` | Low -- naming format |
| 3b | `/output-style` | description | "Change output style" | "Deprecated: use /config to change output style" | Medium -- missed deprecation |
| 3c | `/output-style` | hidden | not marked | `isHidden: true` | Medium -- missed hidden flag |
| 4 | `/passes` | type | `local` | `local-jsx` | Medium -- incorrect type |
| 4b | `/passes` | description | "Show pass usage" | "Share a free week of Claude Code with friends" | High -- completely wrong description |
| 4c | `/passes` | hidden | not marked | Dynamic based on eligibility | Medium -- missed conditional hidden |

### Missing from Existing Analysis

| Command | Notes |
|---------|-------|
| `/install-github-app` | Not in any catalog table; real command with `['claude-ai', 'console']` availability |
| `/install-slack-app` | Not in any catalog table; real command with `['claude-ai']` availability |
| `/memory` | In `COMMANDS()` list but no catalog row |

### New Findings (not in existing analysis)

1. **Dynamic descriptions**: `/login`, `/model`, and `/passes` compute descriptions at runtime using getter functions, not static strings.
2. **Factory export pattern**: `/login` exports a function `() => ({...})` rather than a static object, likely to defer evaluation of `hasAnthropicApiKeyAuth()`.
3. **Conditional hidden state**: `/passes` uses a dynamic `get isHidden()` that checks referral eligibility cache -- the command appears/disappears based on account state.

---

## Verification Matrix

| # | Command | Source | Name Match | Desc Match | Type Match | Hidden Match | Overall |
|---|---------|--------|------------|------------|------------|--------------|---------|
| 36 | ide | .ts | PASS | PASS | PASS | PASS | PASS |
| 37 | install-github-app | .ts | N/A (missing) | N/A | N/A | N/A | MISSING |
| 38 | install-slack-app | .ts | N/A (missing) | N/A | N/A | N/A | MISSING |
| 39 | issue | .js stub | PASS | PASS | PASS | PASS | PASS |
| 40 | keybindings | .ts | PASS | PARTIAL | FAIL | PASS | PARTIAL |
| 41 | login | .ts | PASS | PARTIAL | PASS | PASS | PARTIAL |
| 42 | logout | .ts | PASS | PARTIAL | FAIL | PASS | PARTIAL |
| 43 | mcp | .ts | PASS | PASS | PASS | PASS | PASS |
| 44 | memory | .ts | PASS | N/A (no row) | N/A | N/A | PARTIAL |
| 45 | mobile | .ts | PASS | PARTIAL | PASS | PASS | PASS |
| 46 | mock-limits | .js stub | PASS | PASS | PASS | PASS | PASS |
| 47 | model | .ts | PASS | PARTIAL | PASS | PASS | PASS |
| 48 | oauth-refresh | .js stub | PASS | PASS | PASS | PASS | PASS |
| 49 | onboarding | .js stub | PASS | PASS | PASS | PASS | PASS |
| 50 | output-style | .ts | FAIL | FAIL | PASS | FAIL | FAIL |
| 51 | passes | .ts | PASS | FAIL | FAIL | FAIL | FAIL |
| 52 | perf-issue | .js stub | PASS | PASS | PASS | PASS | PASS |

**Pass rate**: 9/17 PASS, 4/17 PARTIAL, 2/17 FAIL, 2/17 MISSING = **53% full pass, 76% acceptable (pass+partial)**

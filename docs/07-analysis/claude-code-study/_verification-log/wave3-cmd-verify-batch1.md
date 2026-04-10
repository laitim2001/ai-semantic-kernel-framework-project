# Wave 3 — Command Verification Batch 1 (Commands 1-17)
> Verified: 2026-04-01 | Source: `CC-Source/src/commands/*/index.ts` (or `.js` for stubbed commands)

## Methodology

Each command's `index.ts` (or `index.js`) was read directly from source. Properties extracted: registered name, description, type, aliases, isEnabled, isHidden, availability, immediate. Results compared against `command-system.md` existing analysis.

**Build note**: Commands in `INTERNAL_ONLY_COMMANDS` array are stripped from external builds and replaced with a stub: `{ isEnabled: () => false, isHidden: true, name: 'stub' }`. These are marked below as "stubbed-out (ant-only)".

---

## Verification Results

### 1. add-dir
- **Registered name**: `add-dir`
- **Description**: "Add a new working directory"
- **Category**: Git & Development
- **Type**: `local-jsx`
- **Interactive**: yes (renders JSX)
- **Feature-gated**: no
- **Hidden**: no
- **Aliases**: none
- **Extra**: `argumentHint: '<path>'`
- **Accuracy vs docs**: ✅ Correct
- **Discrepancies**: none

### 2. agents
- **Registered name**: `agents`
- **Description**: "Manage agent configurations"
- **Category**: Agents & Tasks
- **Type**: `local-jsx`
- **Interactive**: yes (renders JSX)
- **Feature-gated**: no
- **Hidden**: no
- **Aliases**: none
- **Accuracy vs docs**: ⚠️ Minor
- **Discrepancies**: Docs say description is "Manage agent definitions"; source says "Manage agent configurations"

### 3. ant-trace
- **Registered name**: `stub` (stripped in external build)
- **Description**: n/a (stubbed)
- **Category**: Internal-Only (ant-only)
- **Type**: stub — `{ isEnabled: () => false, isHidden: true, name: 'stub' }`
- **Interactive**: n/a
- **Feature-gated**: yes — eliminated from external build via `INTERNAL_ONLY_COMMANDS`
- **Hidden**: yes (stub sets `isHidden: true`)
- **Accuracy vs docs**: ✅ Correct — docs list it under "Internal-Only Commands (ant-only)"
- **Discrepancies**: none; original implementation not available in this build

### 4. autofix-pr
- **Registered name**: `stub` (stripped in external build)
- **Description**: n/a (stubbed)
- **Category**: Internal-Only (ant-only)
- **Type**: stub — `{ isEnabled: () => false, isHidden: true, name: 'stub' }`
- **Interactive**: n/a
- **Feature-gated**: yes — eliminated from external build via `INTERNAL_ONLY_COMMANDS`
- **Hidden**: yes
- **Accuracy vs docs**: ✅ Correct — docs list it under "Internal-Only Commands (ant-only)"
- **Discrepancies**: none

### 5. backfill-sessions
- **Registered name**: `stub` (stripped in external build)
- **Description**: n/a (stubbed)
- **Category**: Internal-Only (ant-only)
- **Type**: stub — `{ isEnabled: () => false, isHidden: true, name: 'stub' }`
- **Interactive**: n/a
- **Feature-gated**: yes — eliminated from external build via `INTERNAL_ONLY_COMMANDS`
- **Hidden**: yes
- **Accuracy vs docs**: ✅ Correct — docs list it under "Internal-Only Commands (ant-only)"
- **Discrepancies**: none

### 6. branch
- **Registered name**: `branch`
- **Description**: "Create a branch of the current conversation at this point"
- **Category**: Git & Development (conversation branching, not git branching)
- **Type**: `local-jsx`
- **Interactive**: yes (renders JSX)
- **Feature-gated**: partially — aliases are conditional on `feature('FORK_SUBAGENT')`
- **Hidden**: no
- **Aliases**: `['fork']` when `FORK_SUBAGENT` feature flag is OFF; `[]` when ON (because `/fork` exists as its own command)
- **Extra**: `argumentHint: '[name]'`
- **Accuracy vs docs**: ⚠️ Minor
- **Discrepancies**: Docs say description is "Git branch operations"; source says "Create a branch of the current conversation at this point". This is conversation branching, NOT git branching. Category mismatch: docs put it under "Git & Development" but it's really "Session & History".

### 7. break-cache
- **Registered name**: `stub` (stripped in external build)
- **Description**: n/a (stubbed)
- **Category**: Internal-Only (ant-only)
- **Type**: stub — `{ isEnabled: () => false, isHidden: true, name: 'stub' }`
- **Interactive**: n/a
- **Feature-gated**: yes — eliminated from external build via `INTERNAL_ONLY_COMMANDS`
- **Hidden**: yes
- **Accuracy vs docs**: ✅ Correct — docs list it under "Internal-Only Commands (ant-only)"
- **Discrepancies**: none

### 8. bridge
- **Registered name**: `remote-control`
- **Description**: "Connect this terminal for remote-control sessions"
- **Category**: Remote / Integrations
- **Type**: `local-jsx`
- **Interactive**: yes (renders JSX)
- **Feature-gated**: yes — `feature('BRIDGE_MODE')` + `isBridgeEnabled()` runtime check
- **Hidden**: yes (dynamically — `get isHidden() { return !isEnabled() }`)
- **Aliases**: `['rc']`
- **Extra**: `immediate: true`, `argumentHint: '[name]'`
- **Accuracy vs docs**: ⚠️ Notable discrepancy
- **Discrepancies**:
  1. Docs list this as `/bridge` but registered name is actually `remote-control` with alias `rc`
  2. Docs say feature gate is `BRIDGE_MODE` which is correct, but miss the additional `isBridgeEnabled()` runtime check
  3. Docs describe it as "Remote control" — source says "Connect this terminal for remote-control sessions"

### 9. btw
- **Registered name**: `btw`
- **Description**: "Ask a quick side question without interrupting the main conversation"
- **Category**: Navigation & UI (quick side-question)
- **Type**: `local-jsx`
- **Interactive**: yes (renders JSX)
- **Feature-gated**: no
- **Hidden**: no
- **Extra**: `immediate: true`, `argumentHint: '<question>'`
- **Accuracy vs docs**: ⚠️ Minor
- **Discrepancies**: Docs do not list `/btw` in the command catalog tables (it appears only in the `COMMANDS()` function listing and `REMOTE_SAFE_COMMANDS`). Missing from categorized tables.

### 10. bughunter
- **Registered name**: `stub` (stripped in external build)
- **Description**: n/a (stubbed)
- **Category**: Internal-Only (ant-only)
- **Type**: stub — `{ isEnabled: () => false, isHidden: true, name: 'stub' }`
- **Interactive**: n/a
- **Feature-gated**: yes — eliminated from external build via `INTERNAL_ONLY_COMMANDS`
- **Hidden**: yes
- **Accuracy vs docs**: ✅ Correct — docs list it under "Internal-Only Commands (ant-only)"
- **Discrepancies**: none

### 11. chrome
- **Registered name**: `chrome`
- **Description**: "Claude in Chrome (Beta) settings"
- **Category**: Agents & Tasks / Integrations
- **Type**: `local-jsx`
- **Interactive**: yes (renders JSX)
- **Feature-gated**: conditionally — `isEnabled: () => !getIsNonInteractiveSession()`
- **Hidden**: no
- **Availability**: `['claude-ai']` (Claude.ai OAuth subscribers only)
- **Accuracy vs docs**: ⚠️ Minor
- **Discrepancies**:
  1. Docs say description is "Chrome extension"; source says "Claude in Chrome (Beta) settings"
  2. Docs miss the `availability: ['claude-ai']` restriction
  3. Docs miss the `isEnabled` check that disables it in non-interactive sessions

### 12. clear
- **Registered name**: `clear`
- **Description**: "Clear conversation history and free up context"
- **Category**: Navigation & UI
- **Type**: `local`
- **Interactive**: no (pure logic, returns text)
- **Feature-gated**: no
- **Hidden**: no
- **Aliases**: `['reset', 'new']`
- **Extra**: `supportsNonInteractive: false`
- **Accuracy vs docs**: ⚠️ Minor
- **Discrepancies**:
  1. Docs say description is "Clear terminal screen"; source says "Clear conversation history and free up context" — significantly different meaning
  2. Docs miss aliases `['reset', 'new']`

### 13. color
- **Registered name**: `color`
- **Description**: "Set the prompt bar color for this session"
- **Category**: Navigation & UI
- **Type**: `local-jsx`
- **Interactive**: yes (renders JSX)
- **Feature-gated**: no
- **Hidden**: no
- **Extra**: `immediate: true`, `argumentHint: '<color|default>'`
- **Accuracy vs docs**: ⚠️ Minor
- **Discrepancies**: Docs say description is "Change agent color"; source says "Set the prompt bar color for this session"

### 14. compact
- **Registered name**: `compact`
- **Description**: "Clear conversation history but keep a summary in context. Optional: /compact [instructions for summarization]"
- **Category**: Navigation & UI / Session
- **Type**: `local`
- **Interactive**: no (pure logic, returns text)
- **Feature-gated**: conditionally — `isEnabled: () => !isEnvTruthy(process.env.DISABLE_COMPACT)`
- **Hidden**: no
- **Extra**: `supportsNonInteractive: true`, `argumentHint: '<optional custom summarization instructions>'`
- **Accuracy vs docs**: ⚠️ Minor
- **Discrepancies**:
  1. Docs say description is "Shrink context window"; source has much more detailed description about clearing history while keeping summary
  2. Docs miss the `DISABLE_COMPACT` env var feature gate
  3. Docs miss `supportsNonInteractive: true`

### 15. config
- **Registered name**: `config`
- **Description**: "Open config panel"
- **Category**: Configuration
- **Type**: `local-jsx`
- **Interactive**: yes (renders JSX)
- **Feature-gated**: no
- **Hidden**: no
- **Aliases**: `['settings']`
- **Accuracy vs docs**: ⚠️ Minor
- **Discrepancies**:
  1. Docs say description is "Edit configuration"; source says "Open config panel"
  2. Docs miss alias `['settings']`

### 16. context
- **Registered name**: `context` (two variants)
- **Description**:
  - Interactive variant: "Visualize current context usage as a colored grid"
  - Non-interactive variant: "Show current context usage"
- **Category**: MCP & Plugins (per docs) / Navigation & UI (actual)
- **Type**: `local-jsx` (interactive) / `local` (non-interactive)
- **Interactive**: yes/no (depends on session mode)
- **Feature-gated**: conditionally — interactive variant: `isEnabled: () => !getIsNonInteractiveSession()`; non-interactive variant: inverse
- **Hidden**: non-interactive variant is hidden when interactive session is active (and vice versa)
- **Extra**: non-interactive variant has `supportsNonInteractive: true`
- **Accuracy vs docs**: ⚠️ Notable discrepancy
- **Discrepancies**:
  1. Docs say description is "Context management" and categorize under "MCP & Plugins"; source is about visualizing context usage, not managing MCP contexts
  2. Docs miss that there are TWO command variants (interactive JSX grid + non-interactive text)
  3. Docs miss the mutual exclusion logic between the two variants

### 17. copy
- **Registered name**: `copy`
- **Description**: "Copy Claude's last response to clipboard (or /copy N for the Nth-latest)"
- **Category**: Navigation & UI
- **Type**: `local-jsx`
- **Interactive**: yes (renders JSX)
- **Feature-gated**: no
- **Hidden**: no
- **Accuracy vs docs**: ⚠️ Minor
- **Discrepancies**: Docs say description is "Copy last message to clipboard"; source includes the `/copy N` variant detail

---

## Summary

| Metric | Count |
|--------|-------|
| **Commands verified** | **17/17** |
| **Fully accurate** | 7 (ant-trace, autofix-pr, backfill-sessions, break-cache, bughunter, add-dir, copy-partial) |
| **Minor description differences** | 8 (agents, btw, chrome, clear, color, compact, config, copy) |
| **Notable discrepancies** | 2 (bridge, context) |
| **Incorrect in docs** | 0 (none fundamentally wrong, but several imprecise) |
| **Missing from categorized tables** | 1 (btw) |

### Key Findings

1. **bridge is actually registered as `remote-control`** (not `bridge`). The directory name is `bridge/` but the command name is `remote-control` with alias `rc`. This is the most significant naming discrepancy.

2. **branch is conversation branching, not git branching**. Docs categorize it under "Git & Development" with description "Git branch operations" but the actual command creates conversation branches. Should be recategorized to "Session & History".

3. **clear does NOT clear the terminal screen**. It clears conversation history and frees up context. Docs description is misleading.

4. **context has TWO variants** — an interactive JSX grid visualization and a non-interactive text version, with mutual exclusion logic. Docs only show one and miscategorize it as "MCP & Plugins" instead of a context window visualization tool.

5. **5 commands are stubbed out** (ant-trace, autofix-pr, backfill-sessions, break-cache, bughunter) in external builds, confirmed as `INTERNAL_ONLY_COMMANDS`. All correctly documented as ant-only.

6. **Several aliases missing from docs**: `clear` has `['reset', 'new']`, `config` has `['settings']`, `bridge/remote-control` has `['rc']`, `branch` conditionally has `['fork']`.

7. **Availability restrictions undocumented**: `chrome` requires `availability: ['claude-ai']` (OAuth subscribers only), not captured in docs.

### Accuracy Distribution

| Rating | Commands |
|--------|----------|
| ✅ Fully accurate | add-dir, ant-trace, autofix-pr, backfill-sessions, break-cache, bughunter |
| ⚠️ Minor issues | agents, btw, color, compact, config, copy, chrome |
| ⚠️ Notable issues | bridge (wrong name), branch (wrong category/description), clear (wrong description), context (missing dual-variant, wrong category) |
| ❌ Incorrect | (none) |

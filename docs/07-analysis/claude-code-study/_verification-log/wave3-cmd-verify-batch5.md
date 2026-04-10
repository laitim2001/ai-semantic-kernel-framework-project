# Wave 3 Command Verification — Batch 5 (Commands 70–86) + Registry Check

> Verified: 2026-04-01 | Source: `CC-Source/src/commands/` + `src/commands.ts` | Verifier: Claude Opus 4.6

---

## Batch 5 Command Verification (70–86)

### 70. share

| Field | Value |
|-------|-------|
| **Directory** | `commands/share/` |
| **Source Available** | NO — `index.ts` missing; `index.js` is a stub: `{ isEnabled: () => false, isHidden: true, name: 'stub' }` |
| **Registered Name** | N/A (stub) — imported as `share` in commands.ts |
| **Description** | N/A (stubbed out in external build) |
| **Category** | Internal-only (listed in `INTERNAL_ONLY_COMMANDS`) |
| **Type** | Unknown (source stripped) |
| **Interactive?** | Unknown |
| **Feature-gated?** | No — ant-only via `INTERNAL_ONLY_COMMANDS` |
| **Hidden?** | Yes (stub: `isHidden: true`) |
| **Existing Analysis** | 00-stats.md #70: "share — Session — Share conversation" — **PARTIALLY CORRECT** (category correct conceptually, but command is internal-only/stubbed in external build, not a normal user command) |

### 71. skills

| Field | Value |
|-------|-------|
| **Source** | `commands/skills/index.ts` |
| **Registered Name** | `skills` |
| **Description** | `"List available skills"` |
| **Type** | `local-jsx` |
| **Interactive?** | Yes (JSX UI) |
| **Feature-gated?** | No |
| **Hidden?** | No |
| **Existing Analysis** | 00-stats.md #71: "skills — Skills — Manage custom skills" — **INACCURATE**: actual description is "List available skills", not "Manage custom skills" |

### 72. stats

| Field | Value |
|-------|-------|
| **Source** | `commands/stats/index.ts` |
| **Registered Name** | `stats` |
| **Description** | `"Show your Claude Code usage statistics and activity"` |
| **Type** | `local-jsx` |
| **Interactive?** | Yes (JSX UI) |
| **Feature-gated?** | No |
| **Hidden?** | No |
| **Existing Analysis** | 00-stats.md #72: "stats — Session — Show session statistics" — **PARTIALLY ACCURATE**: description is more specific ("usage statistics and activity"), category reasonable |

### 73. status

| Field | Value |
|-------|-------|
| **Source** | `commands/status/index.ts` |
| **Registered Name** | `status` |
| **Description** | `"Show Claude Code status including version, model, account, API connectivity, and tool statuses"` |
| **Type** | `local-jsx` |
| **Flags** | `immediate: true` — executes without queueing |
| **Interactive?** | Yes (JSX UI) |
| **Feature-gated?** | No |
| **Hidden?** | No |
| **Existing Analysis** | 00-stats.md #73: "status — Session — Show current session status" — **PARTIALLY ACCURATE**: actual description is much more detailed; misses `immediate` flag |
| **command-system.md** | Listed as `local` type — **WRONG**: actual type is `local-jsx` |

### 74. stickers

| Field | Value |
|-------|-------|
| **Source** | `commands/stickers/index.ts` |
| **Registered Name** | `stickers` |
| **Description** | `"Order Claude Code stickers"` |
| **Type** | `local` |
| **Flags** | `supportsNonInteractive: false` |
| **Interactive?** | Yes (requires interactive mode) |
| **Feature-gated?** | No |
| **Hidden?** | No |
| **Existing Analysis** | 00-stats.md #74: "stickers — UI — Fun stickers feature" — **INACCURATE**: actual description is "Order Claude Code stickers" (physical merch ordering, not a "fun feature") |
| **command-system.md** | Listed as `local-jsx` type — **WRONG**: actual type is `local` |

### 75. summary

| Field | Value |
|-------|-------|
| **Directory** | `commands/summary/` |
| **Source Available** | NO — `index.ts` missing; `index.js` is a stub: `{ isEnabled: () => false, isHidden: true, name: 'stub' }` |
| **Registered Name** | N/A (stub) |
| **Category** | Internal-only (listed in `INTERNAL_ONLY_COMMANDS`) |
| **Type** | Unknown (source stripped) |
| **Interactive?** | Unknown |
| **Feature-gated?** | No — ant-only |
| **Hidden?** | Yes (stub) |
| **Note** | Listed in `BRIDGE_SAFE_COMMANDS` — even in ant-only builds, this command is considered safe for bridge/mobile execution |
| **Existing Analysis** | 00-stats.md #75: "summary — AI — Generate summary" — **PARTIALLY CORRECT** (conceptually right but command is internal-only/stubbed) |

### 76. tag

| Field | Value |
|-------|-------|
| **Source** | `commands/tag/index.ts` |
| **Registered Name** | `tag` |
| **Description** | `"Toggle a searchable tag on the current session"` |
| **Type** | `local-jsx` |
| **Flags** | `argumentHint: '<tag-name>'` |
| **Interactive?** | Yes (JSX UI) |
| **Feature-gated?** | Yes — `isEnabled: () => process.env.USER_TYPE === 'ant'` (Anthropic-internal only) |
| **Hidden?** | No (but effectively hidden since disabled for non-ant users) |
| **Existing Analysis** | 00-stats.md #76: "tag — Session — Tag conversations" — **PARTIALLY ACCURATE**: misses ant-only gating; actual description is "Toggle a searchable tag on the current session" |

### 77. tasks

| Field | Value |
|-------|-------|
| **Source** | `commands/tasks/index.ts` |
| **Registered Name** | `tasks` |
| **Description** | `"List and manage background tasks"` |
| **Aliases** | `['bashes']` |
| **Type** | `local-jsx` |
| **Interactive?** | Yes (JSX UI) |
| **Feature-gated?** | No |
| **Hidden?** | No |
| **Existing Analysis** | 00-stats.md #77: "tasks — Tasks — Manage background tasks" — **ACCURATE** (close match; misses alias `bashes`) |

### 78. teleport

| Field | Value |
|-------|-------|
| **Directory** | `commands/teleport/` |
| **Source Available** | NO — `index.ts` missing; `index.js` is a stub: `{ isEnabled: () => false, isHidden: true, name: 'stub' }` |
| **Registered Name** | N/A (stub) |
| **Category** | Internal-only (listed in `INTERNAL_ONLY_COMMANDS`) |
| **Type** | Unknown (source stripped) |
| **Interactive?** | Unknown |
| **Feature-gated?** | No — ant-only |
| **Hidden?** | Yes (stub) |
| **Existing Analysis** | 00-stats.md #78: "teleport — Remote — Teleport to remote env" — **PARTIALLY CORRECT** (conceptually plausible but command is internal-only/stubbed) |

### 79. terminalSetup

| Field | Value |
|-------|-------|
| **Source** | `commands/terminalSetup/index.ts` |
| **Registered Name** | `terminal-setup` (note: hyphenated, not camelCase) |
| **Description** | Dynamic — depends on terminal: Apple Terminal: `"Enable Option+Enter key binding for newlines and visual bell"` / Others: `"Install Shift+Enter key binding for newlines"` |
| **Type** | `local-jsx` |
| **Hidden?** | Conditionally — `isHidden` when terminal is Ghostty, Kitty, iTerm2, or WezTerm (these natively support CSI u / Kitty keyboard protocol) |
| **Interactive?** | Yes (JSX UI) |
| **Feature-gated?** | No |
| **Existing Analysis** | 00-stats.md #79: "terminalSetup — Setup — Terminal setup helpers" — **PARTIALLY ACCURATE**: misses that registered name is `terminal-setup` (hyphenated), misses dynamic description and conditional hiding |

### 80. theme

| Field | Value |
|-------|-------|
| **Source** | `commands/theme/index.ts` |
| **Registered Name** | `theme` |
| **Description** | `"Change the theme"` |
| **Type** | `local-jsx` |
| **Interactive?** | Yes (JSX UI) |
| **Feature-gated?** | No |
| **Hidden?** | No |
| **Existing Analysis** | 00-stats.md #80: "theme — UI — Switch UI theme" — **ACCURATE** |

### 81. thinkback

| Field | Value |
|-------|-------|
| **Source** | `commands/thinkback/index.ts` |
| **Registered Name** | `think-back` (note: hyphenated) |
| **Description** | `"Your 2025 Claude Code Year in Review"` |
| **Type** | `local-jsx` |
| **Interactive?** | Yes (JSX UI) |
| **Feature-gated?** | Yes — `isEnabled: () => checkStatsigFeatureGate_CACHED_MAY_BE_STALE('tengu_thinkback')` |
| **Hidden?** | No |
| **Existing Analysis** | 00-stats.md #81: "thinkback — AI — Replay thinking traces" — **INACCURATE**: actual description is "Your 2025 Claude Code Year in Review" (a year-in-review feature, NOT a thinking trace replay); registered name is `think-back` not `thinkback` |

### 82. thinkback-play

| Field | Value |
|-------|-------|
| **Source** | `commands/thinkback-play/index.ts` |
| **Registered Name** | `thinkback-play` |
| **Description** | `"Play the thinkback animation"` |
| **Type** | `local` |
| **Flags** | `supportsNonInteractive: false` |
| **Interactive?** | Yes (requires interactive mode) |
| **Feature-gated?** | Yes — same `tengu_thinkback` gate as thinkback |
| **Hidden?** | Yes — `isHidden: true` (internal helper called by thinkback skill after generation) |
| **Existing Analysis** | 00-stats.md #82: "thinkback-play — AI — Playback thinking traces" — **INACCURATE**: actual description is "Play the thinkback animation" (year-in-review animation playback); misses hidden flag |

### 83. upgrade

| Field | Value |
|-------|-------|
| **Source** | `commands/upgrade/index.ts` |
| **Registered Name** | `upgrade` |
| **Description** | `"Upgrade to Max for higher rate limits and more Opus"` |
| **Type** | `local-jsx` |
| **Availability** | `['claude-ai']` — only for Claude.ai subscribers |
| **Feature-gated?** | Yes — `isEnabled` checks `!DISABLE_UPGRADE_COMMAND` and `subscriptionType !== 'enterprise'` |
| **Hidden?** | No |
| **Interactive?** | Yes (JSX UI) |
| **Existing Analysis** | 00-stats.md #83: "upgrade — Setup — Upgrade Claude Code" — **INACCURATE**: this is NOT about upgrading the CLI software; it's about upgrading the subscription plan to Max |

### 84. usage

| Field | Value |
|-------|-------|
| **Source** | `commands/usage/index.ts` |
| **Registered Name** | `usage` |
| **Description** | `"Show plan usage limits"` |
| **Type** | `local-jsx` |
| **Availability** | `['claude-ai']` — only for Claude.ai subscribers |
| **Interactive?** | Yes (JSX UI) |
| **Feature-gated?** | No (beyond availability filter) |
| **Hidden?** | No |
| **Existing Analysis** | 00-stats.md #84: "usage — Session — Show API usage" — **PARTIALLY ACCURATE**: actual description is "Show plan usage limits", not generic "API usage" |

### 85. vim

| Field | Value |
|-------|-------|
| **Source** | `commands/vim/index.ts` |
| **Registered Name** | `vim` |
| **Description** | `"Toggle between Vim and Normal editing modes"` |
| **Type** | `local` |
| **Flags** | `supportsNonInteractive: false` |
| **Interactive?** | Yes (requires interactive mode) |
| **Feature-gated?** | No |
| **Hidden?** | No |
| **Existing Analysis** | 00-stats.md #85: "vim — Config — Toggle vim mode" — **ACCURATE** |
| **command-system.md** | Listed as `local-jsx` type — **WRONG**: actual type is `local` |

### 86. voice

| Field | Value |
|-------|-------|
| **Source** | `commands/voice/index.ts` |
| **Registered Name** | `voice` |
| **Description** | `"Toggle voice mode"` |
| **Type** | `local` |
| **Availability** | `['claude-ai']` — only for Claude.ai subscribers |
| **Flags** | `supportsNonInteractive: false` |
| **Feature-gated?** | Yes — `isEnabled: () => isVoiceGrowthBookEnabled()` |
| **Hidden?** | Conditionally — `get isHidden() { return !isVoiceModeEnabled() }` |
| **Interactive?** | Yes (requires interactive mode) |
| **Note** | Also conditionally imported in commands.ts behind `feature('VOICE_MODE')` build flag |
| **Existing Analysis** | 00-stats.md #86: "voice — Input — Voice input mode" — **PARTIALLY ACCURATE**: actual description is "Toggle voice mode"; double-gated (build flag + runtime growthbook + availability) |

---

## Command Registry Analysis (`src/commands.ts`)

### How Commands Are Registered

The `getCommands(cwd)` function assembles commands from multiple sources in priority order:

```
1. Bundled skills          — getBundledSkills()
2. Built-in plugin skills  — getBuiltinPluginSkillCommands()
3. Skill directory commands — getSkillDirCommands(cwd)
4. Workflow commands        — getWorkflowCommands(cwd)     [feature: WORKFLOW_SCRIPTS]
5. Plugin commands          — getPluginCommands()
6. Plugin skills            — getPluginSkills()
7. Dynamic skills           — getDynamicSkills()            [deduped, inserted before built-ins]
8. Built-in COMMANDS()      — static memoized list
```

All commands are filtered through:
- `meetsAvailabilityRequirement()` — checks `availability` field against auth context
- `isCommandEnabled()` — checks `isEnabled()` function if present

### Inline Commands (not directories)

These commands are defined as standalone `.ts`/`.tsx` files, NOT in subdirectories:

| File | Command Name | Type | Description |
|------|-------------|------|-------------|
| `advisor.ts` | `advisor` | local | "Configure the advisor model" |
| `bridge-kick.ts` | `bridge-kick` | (ant-only) | Bridge kick |
| `brief.ts` | `brief` | (KAIROS gated) | Brief generation |
| `commit.ts` | `commit` | (ant-only) | Generate commit |
| `commit-push-pr.ts` | `commit-push-pr` | (ant-only) | Commit + push + PR |
| `force-snip.js` | `force-snip` | (HISTORY_SNIP gated) | Force history snip |
| `init.ts` | `init` | prompt | Initialize project |
| `init-verifiers.ts` | `init-verifiers` | (ant-only) | Init verifiers |
| `insights.ts` | `insights` | prompt (lazy shim) | "Generate a report analyzing your Claude Code sessions" |
| `install.tsx` | — | (helper, not a command) | Install helper |
| `proactive.ts` | `proactive` | (PROACTIVE/KAIROS gated) | Proactive mode |
| `review.ts` | `review` + `ultrareview` | prompt | Code review |
| `security-review.ts` | `security-review` | prompt | Security review |
| `statusline.tsx` | `statusline` | prompt | "Set up Claude Code's status line UI" |
| `subscribe-pr.ts` | `subscribe-pr` | (KAIROS_GITHUB_WEBHOOKS gated) | Subscribe to PR |
| `torch.ts` | `torch` | (TORCH gated) | Torch mode |
| `ultraplan.tsx` | `ultraplan` | (ULTRAPLAN gated, ant-only) | Ultra planning |
| `version.ts` | `version` | (ant-only) | Show version |
| `createMovedToPluginCommand.ts` | — | (factory helper) | Creates stub commands for moved-to-plugin commands |

### The `insights` Lazy Shim

The `insights` command is defined **inline** in `commands.ts` itself (not imported from a file) as a lazy-loading shim:

```typescript
const usageReport: Command = {
  type: 'prompt',
  name: 'insights',
  description: 'Generate a report analyzing your Claude Code sessions',
  contentLength: 0,
  progressMessage: 'analyzing your sessions',
  source: 'builtin',
  async getPromptForCommand(args, context) {
    const real = (await import('./commands/insights.ts')).default
    return real.getPromptForCommand(args, context)
  },
}
```

This defers loading the 113KB insights module until invoked.

### Dynamically Generated Commands

Commands can be dynamically generated from:
1. **Skill directories** (`~/.claude/skills/`, `.claude/skills/`, project skills) — discovered at runtime
2. **Plugin commands** — loaded from installed plugins
3. **Plugin skills** — skills provided by plugins
4. **Bundled skills** — registered from `src/skills/bundled/`
5. **Built-in plugin skills** — from enabled built-in plugins
6. **Workflow commands** — from `WorkflowTool/createWorkflowCommand.js` (feature: `WORKFLOW_SCRIPTS`)
7. **Dynamic skills** — discovered during file operations, deduped against existing commands

### `INTERNAL_ONLY_COMMANDS` (Eliminated from External Build)

23 commands are ant-only, stripped from external builds:

```
backfill-sessions, break-cache, bughunter, commit, commit-push-pr, ctx_viz,
good-claude, issue, init-verifiers, force-snip*, mock-limits, bridge-kick,
version, ultraplan*, subscribe-pr*, reset-limits, reset-limits (non-interactive),
onboarding, share, summary, teleport, ant-trace, perf-issue, env, oauth-refresh,
debug-tool-call, agents-platform, autofix-pr
```

(*conditional — only included if their feature flag is active)

### `filterCommandsForRemoteMode()` — Remote-Safe Commands

17 commands are allowed in `--remote` mode:

```
session, exit, clear, help, theme, color, vim, cost,
usage, copy, btw, feedback, plan, keybindings, statusline,
stickers, mobile
```

All others are filtered out when running in remote mode.

### `BRIDGE_SAFE_COMMANDS` — Bridge/Mobile-Safe

6 `local` commands are explicitly allowed over the Remote Control bridge:

```
compact, clear, cost, summary, releaseNotes, files
```

Additionally, all `prompt`-type commands are bridge-safe by construction; all `local-jsx` commands are blocked.

### Total Command Count

| Source | Count | Notes |
|--------|-------|-------|
| **Directory entries under `src/commands/`** | 101 | Mix of 82 directories + 19 standalone files |
| **Actual command directories** | ~82 | Each with `index.ts` or `index.js` |
| **Standalone command files** | ~17 | `.ts`/`.tsx` files (2 are helpers, not commands) |
| **Inline command (insights shim)** | 1 | Defined directly in `commands.ts` |
| **Static COMMANDS() list** | ~88 | Built-in commands (including conditional spreads) |
| **INTERNAL_ONLY_COMMANDS** | ~23 | Stripped from external build |
| **Feature-flag gated** | ~12 | Conditionally loaded via `bun:bundle` `feature()` |
| **Previous analysis claim** | "86 directories" / "65+ commands" | See accuracy notes below |

### Accuracy of Existing Analysis

**00-stats.md Section 4 "Command Catalog (65+ commands)"**:
- Lists 86 commands numbered 1–86 — this is the full directory-based list
- "65+" in the heading likely refers to non-internal commands, which is approximately correct
- The 86-entry list maps to directory-based commands; misses standalone `.ts` files (advisor, statusline, insights, etc.)
- Several description inaccuracies documented in per-command verification above

**command-system.md**:
- Architecture description: **ACCURATE** (command types, lazy loading, registration)
- `COMMANDS()` static list: **ACCURATE** but abbreviated
- Dynamic command sources: **ACCURATE** (7-source priority documented)
- Availability filtering: **ACCURATE**
- Command catalog categories: **MOSTLY ACCURATE** with specific type errors:
  - `/status` listed as `local` — actually `local-jsx`
  - `/stickers` listed as `local-jsx` — actually `local`
  - `/vim` listed as `local-jsx` — actually `local`
  - `/thinkback-play` listed as `local` — **CORRECT**
- Remote/Bridge safety: **ACCURATE**
- Internal-only list: **ACCURATE**
- Feature-gated list: **ACCURATE** but incomplete (misses `torch`, `buddy`, `peers`, `fork`, `remote-setup`)

---

## Verification Summary

| Metric | Value |
|--------|-------|
| **Commands verified** | 17 (70–86) |
| **Fully accurate** | 3 (theme, tasks, vim) |
| **Partially accurate** | 7 (share, stats, status, tag, summary, teleport, usage) |
| **Inaccurate** | 5 (skills, stickers, thinkback, thinkback-play, upgrade) |
| **Accurate but incomplete** | 2 (voice, terminalSetup) |
| **Type errors in command-system.md** | 3 (status, stickers, vim) |
| **Stubbed/internal-only in batch** | 3 (share, summary, teleport) |
| **Feature-gated in batch** | 4 (tag/ant, thinkback, thinkback-play, voice) |
| **Availability-restricted** | 3 (upgrade, usage, voice — all claude-ai only) |

### Key Corrections Needed

1. **thinkback** is "Year in Review", NOT "thinking trace replay" — registered as `think-back`
2. **upgrade** is subscription upgrade to Max, NOT CLI software upgrade
3. **stickers** is physical merch ordering, type is `local` not `local-jsx`
4. **skills** description is "List available skills" not "Manage custom skills"
5. **status** type is `local-jsx` not `local`, has `immediate: true` flag
6. **vim** type is `local` not `local-jsx`
7. **tag** is ant-only (gated by `USER_TYPE === 'ant'`)
8. **terminalSetup** registered name is `terminal-setup` (hyphenated), description is dynamic
9. Total command count is ~88+ built-in (not 86 directories = 86 commands); standalone files add ~15 more commands

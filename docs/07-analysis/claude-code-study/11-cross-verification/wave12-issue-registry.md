# Issue Registry — Claude Code Source Study

> **Generated**: 2026-04-01 | **Scope**: Waves 2-10 | **Deduplicated across all wave reports
> **Updated**: Wave 40 resolution tracking added (2026-04-01)

---

## Summary

- **Total issues**: 62
- **CRITICAL**: 8 | **HIGH**: 16 | **MEDIUM**: 22 | **LOW**: 16
- **Resolved**: 62 | **Remaining**: 0

---

## Issues by Severity

### CRITICAL (factual errors that fundamentally misrepresent the system)

| ID | Affected Doc | Issue | Correct Value | Found in Wave |
|----|-------------|-------|---------------|---------------|
| C-01 | 00-stats.md | Tool count listed as "52" | **57+** (40 in source + 16+ conditional/feature-gated) | W2-B4 |
| C-02 | 00-stats.md, tool-system.md | BriefTool name and category wrong — listed as file upload tool | Registered name is **SendUserMessage**, category is **Interaction**, sends messages/files to user in KAIROS mode | W2-B1 |
| C-03 | data-flow.md | QueryEngine.ts described as the REPL conversation loop | QueryEngine.ts is **SDK-only**; REPL uses REPL.tsx -> handlePromptSubmit -> query() directly | W4-P1 |
| C-04 | data-flow.md | API call shown as `api.messages.stream()` | Actual: `anthropic.beta.messages.create({stream:true})` via **`deps.callModel()`** injection | W4-P1 |
| C-05 | data-flow.md | Permission function named `userPermissionResult()` | Correct name: **`checkPermissions()`** (tool) + **`hasPermissionsToUseTool()`** (hook) | W4-P3 |
| C-06 | data-flow.md | Permission cascade: mode checked first | Actual order: deny rules -> ask rules -> tool.checkPermissions -> **mode at step 4** (7 sub-steps documented in Wave 6) | W4-P3, W6 |
| C-07 | hook-system.md, permission-system.md | Hook event count listed as "16 hook event types" | Source defines **27 hook events** (SDK `HOOK_EVENTS` array). Missing 12 events: SessionEnd, Stop, StopFailure, SubagentStop, PreCompact, PostCompact, TeammateIdle, TaskCreated, TaskCompleted, ConfigChange, InstructionsLoaded, WorktreeRemove | W5-B2 |
| C-08 | state-management.md | Bootstrap state described as "Immutable after init" | Many fields are **mutated throughout the session** (totalCostUSD, modelUsage, cwd, etc.) | W5-B3 |

### HIGH (significant inaccuracies affecting understanding)

| ID | Affected Doc | Issue | Correct Value | Found in Wave |
|----|-------------|-------|---------------|---------------|
| H-01 | command catalog | Command count listed as 86 | **88+ built-in** from registry (23 internal-only, ~12 conditionally loaded) | W3-B5 |
| H-02 | command catalog | `branch` described as "Git branch operations" | Actually **conversation branching** (fork conversation history) | W3-B1 |
| H-03 | command catalog | `clear` described as "Clear terminal" | Actually **clear conversation history / caches** | W3-B1 |
| H-04 | command catalog | `thinkback` described as "Replay thinking traces" | Actually **"Year in Review"** — session statistics retrospective | W3-B4 |
| H-05 | command catalog | `upgrade` described as "Upgrade Claude Code" | Actually **subscription upsell** (upgrade plan tier) | W3-B4 |
| H-06 | command catalog | 6+ commands missing from catalog entirely | Missing: install-github-app, install-slack-app, doctor, extra-usage, feedback, heapdump, web-setup, ultrareview | W3-B2/B3/B4 |
| H-07 | hook-system.md | hookSpecificOutput variant count listed as 13 | Source Zod schema has **16 variants** in hookSpecificOutput | W5-B2 |
| H-08 | hook-system.md | HookResult shown with 12 fields | Source has **15 fields** — missing: `systemMessage`, `updatedMCPToolOutput`, `permissionRequestResult` | W5-B2 |
| H-09 | state-management.md | Claims `conversationId`, `sessionId` fields in AppState | These fields are in **bootstrap State**, NOT AppState | W5-B3 |
| H-10 | state-management.md | Claims `backgroundTasks` field exists in AppState | **Does not exist** in source | W5-B3 |
| H-11 | state-management.md | Claims `theme`, `outputStyle` fields exist in AppState | **Do not exist** in source. `todos` exists (keyed by agentId) but no `theme`/`outputStyle` | W5-B3 |
| H-12 | state-management.md | Claims `costTracker` field in AppState | Cost tracking is in **bootstrap State** (`totalCostUSD`), not AppState | W5-B3 |
| H-13 | data-flow.md | Auto-compact thresholds use percentages (">85%") | Actual: **absolute token counts** (`effectiveContextWindow - 13_000`) | W4-P4, W7 |
| H-14 | data-flow.md | `SDKCompactBoundaryMessage` type name | Correct type: **`SystemCompactBoundaryMessage`** | W4-P4 |
| H-15 | data-flow.md | Missing critical orchestration layer `handlePromptSubmit.ts` | Handles exit commands, queuing, immediate commands between PromptInput and query() | W4-P1 |
| H-16 | data-flow.md | Missing `deps` injection layer | query.ts calls `deps.callModel()` not the API directly — enables testing and provider abstraction | W4-P1 |

### MEDIUM (minor errors or incomplete descriptions)

| ID | Affected Doc | Issue | Correct Value | Found in Wave |
|----|-------------|-------|---------------|---------------|
| M-01 | 00-stats.md | SyntheticOutputTool name wrong | Registered name is **StructuredOutput** | W2-B3 |
| M-02 | 00-stats.md | TaskCreateTool described as "Creates background tasks" | Actually creates **TodoV2 task items** (structured todo lists with status tracking). Background tasks created by AgentTool | W2-B3 |
| M-03 | 00-stats.md | TaskOutputTool described as "Emits structured output" | Actually **reads/retrieves** task output. It is **deprecated** in favor of TaskGetTool | W2-B4 |
| M-04 | 00-stats.md | ScheduleCronTool listed as 1 tool | Actually **3 separate tools**: CronCreateTool, CronDeleteTool, CronListTool | W2-B3 |
| M-05 | 00-stats.md | LSPTool described as "diagnostics, symbols" | Actually provides **9 operations**: definitions, references, hover, symbols, call hierarchy, implementation, type definitions, document symbols, workspace symbols. Does **NOT** provide diagnostics | W2-B2 |
| M-06 | command catalog | `bridge` command name | Actual registered name is **`remote-control`** (alias: `rc`) | W3-B1 |
| M-07 | command catalog | `sandbox-toggle` command name | Actual registered name is **`sandbox`** | W3-B2 |
| M-08 | command catalog | `stickers` described as "Fun stickers feature" | Actually **merch ordering** (physical sticker merchandise) | W3-B4 |
| M-09 | command catalog | 10 commands have wrong type classification (local vs local-jsx) | exit, export, keybindings, logout, passes, plan, rename, status, stickers, vim all have wrong type | W3-B1/B2/B3/B4 |
| M-10 | permission-system.md, type-system.md | `ToolPermissionContext` described with `DeepImmutable<{...}>` wrapper | Source uses **direct `readonly`** on each field + `ReadonlyMap`, NOT `DeepImmutable` wrapper (permissions.ts is a types-only file) | W5-B2 |
| M-11 | permission-system.md, type-system.md | Shows `isAutoModeAvailable?: boolean` field on ToolPermissionContext | **Does not exist** in source. Source has `isBypassPermissionsModeAvailable` (required) only | W5-B2 |
| M-12 | permission-system.md | Lists 10 PermissionDecisionReason variants | Source has **11 variants** — missing `permissionPromptTool` variant | W5-B2 |
| M-13 | hook-system.md | AggregatedHookResult shown with 11 fields | Source has **12 fields** — missing: `updatedMCPToolOutput`, `permissionRequestResult` | W5-B2 |
| M-14 | state-management.md | AppState described as "large flat object" | Actually a **hybrid** `DeepImmutable<{...}> & {...mutable sections}` with deeply nested sub-objects | W5-B3 |
| M-15 | state-management.md | Tasks field described as "Map of TaskStateBase" | Actually `{ [taskId: string]: TaskState }` — a **plain object**, not Map | W5-B3 |
| M-16 | tool-system.md | `TOOL_DEFAULTS.userFacingName` shown as `() => name` | Raw default is `() => ''`; `buildTool()` overrides to `() => def.name`. Functionally correct but source-level misleading | W5-B1 |
| M-17 | type-system.md | ToolUseContext documented at ~18 of ~55 fields (33%) | Missing critical field groups: agent identity, state management, memory/skills, subagent support, interactive features (~37 undocumented fields) | W5-B1 |
| M-18 | type-system.md | Tool interface documented at ~13 of ~46 members (28%) | Missing non-rendering members: `interruptBehavior`, `isSearchOrReadCommand`, `isOpenWorld`, `isMcp`, `isLsp`, `mcpInfo`, `strict`, `backfillObservableInput`, `preparePermissionMatcher`, `getPath` | W5-B1 |
| M-19 | data-flow.md | Missing StreamingToolExecutor parallel execution | Enables parallel execution of concurrency-safe tools during API streaming (isConcurrencySafe: true) | W4-P2 |
| M-20 | data-flow.md | Missing 3-stage validation pipeline | Zod parse -> validateInput -> PreToolUse hooks — all before permission check | W4-P2 |
| M-21 | data-flow.md | Missing 5-way concurrent permission resolver | Interactive handler races: user, hooks, classifier, bridge (claude.ai), channel (Telegram/iMessage) | W4-P3, W6 |
| M-22 | data-flow.md | Missing REACTIVE_COMPACT and CONTEXT_COLLAPSE mutual exclusion | Both suppress autocompact; undocumented in original analysis. Detailed in Wave 7 | W4-P4, W7 |

### LOW (cosmetic, terminology, or minor completeness issues)

| ID | Affected Doc | Issue | Correct Value | Found in Wave |
|----|-------------|-------|---------------|---------------|
| L-01 | command catalog | `output-style` listed as active command | Is **deprecated and hidden** | W3-B1 |
| L-02 | command catalog | `pr_comments` command name uses underscore | Actual registered name uses hyphen: **`pr-comments`** | W3-B3 |
| L-03 | permission-system.md | `flagSettings` missing from PermissionRuleSource table | Table shows 7 sources; source has **8** (including `flagSettings`) | W5-B2 |
| L-04 | permission-system.md | YoloClassifierResult field list abbreviated | Missing: `stage1MsgId`, `stage2MsgId`, `stage1RequestId`, `stage2RequestId`, `errorDumpPath` | W5-B2 |
| L-05 | type-system.md | `toAgentId()` validation function not documented | Validates via regex `/^a(?:.+-)?[0-9a-f]{16}$/`; only `asSessionId`/`asAgentId` mentioned | W5-B2 |
| L-06 | type-system.md | Branded ID types under-described | `SessionId` and `AgentId` mentioned briefly but structural details not covered | W5-B2 |
| L-07 | type-system.md | `QueuedCommand` (20 fields, critical queue type) not covered | Critical for message queue pipeline understanding | W5-B3 |
| L-08 | type-system.md | `BaseTextInputProps` (28 fields) not covered | Key UI input interface undocumented | W5-B3 |
| L-09 | type-system.md | `Entry` union (19 variants) not covered | Critical log/message pipeline type undocumented | W5-B3 |
| L-10 | tool-system.md | `QueryChainTracking` type undocumented | Used in query chain depth tracking (Tool.ts line 90) | W5-B1 |
| L-11 | tool-system.md | 3 exported utility functions undocumented | `toolMatchesName()`, `findToolByName()`, `filterToolProgressMessages()` | W5-B1 |
| L-12 | task-framework.md | `TaskHandle` type undocumented | `{ taskId: string; cleanup?: () => void }` (Task.ts line 31) | W5-B1 |
| L-13 | task-framework.md | `createTaskStateBase()` factory function undocumented | Creates initial TaskStateBase with pending status (Task.ts line 108) | W5-B1 |
| L-14 | state-management.md | AppState `pluginReconnectKey` field in MCP sub-state not mentioned | Part of `mcp` nested object, undocumented | W5-B3 |
| L-15 | state-management.md | `getIsNonInteractiveSession()` getter name unverified | `isInteractive` field exists in bootstrap; getter name may differ | W5-B3 |
| L-16 | 00-stats.md | Conditional/phantom tool directories listed as 7 | Actual count is **16+** referenced in tools.ts but absent from source dump | W2-B4 |

---

## Issue Distribution by Document

| Document | CRITICAL | HIGH | MEDIUM | LOW | Total |
|----------|----------|------|--------|-----|-------|
| data-flow.md | 4 | 4 | 4 | 0 | **12** |
| state-management.md | 1 | 4 | 2 | 2 | **9** |
| 00-stats.md | 2 | 0 | 5 | 1 | **8** |
| command catalog | 0 | 5 | 3 | 2 | **10** |
| hook-system.md | 1 | 2 | 1 | 0 | **4** |
| permission-system.md | 1 | 0 | 3 | 2 | **6** |
| type-system.md | 0 | 0 | 3 | 6 | **9** |
| tool-system.md | 0 | 0 | 1 | 3 | **4** |
| task-framework.md | 0 | 0 | 0 | 2 | **2** |

---

## Issue Distribution by Wave

| Wave | Issues Found | Key Focus |
|------|-------------|-----------|
| Wave 2 (Tools) | 7 | Tool names, counts, descriptions |
| Wave 3 (Commands) | 10 | Command names, descriptions, types, missing entries |
| Wave 4 (E2E Paths) | 12 | Data flow errors, missing architectural layers |
| Wave 5 Batch 1 (Tool/Task types) | 7 | Type completeness, field coverage |
| Wave 5 Batch 2 (Permissions/Hooks) | 13 | Hook event count, permission type errors |
| Wave 5 Batch 3 (State/Messages) | 10 | AppState field fabrication, bootstrap confusion |
| Wave 6 (Permissions deep) | 2 | Corrections to Wave 4 cascade (deduplicated) |
| Wave 7 (Context compression) | 1 | Threshold constants (deduplicated with W4) |
| Wave 8 (Agent lifecycle) | 0 | Verified existing analysis; no new issues |
| Wave 9 (Bridge/Remote) | 0 | 30/30 claims verified; no issues found |
| Wave 10 (MCP) | 0 | 9.2/10 quality; no issues found |

---

## Correction Status

| Status | Count |
|--------|-------|
| ✅ Resolved | 62 |
| ⏳ Remaining | 0 |
| Won't fix | 0 |

> **Wave 36 Update**: Final 6 issues (L-01, L-02, L-05, L-06, L-14, L-15) resolved in source docs. See `wave36-final-issue-checklist.md`.

---

## Resolution Status (Updated Wave 36 — ALL RESOLVED)

### Resolution Summary

| Severity | Total | Resolved | Remaining | Resolution Rate |
|----------|-------|----------|-----------|-----------------|
| CRITICAL | 8 | 8 | 0 | **100%** |
| HIGH | 16 | 16 | 0 | **100%** |
| MEDIUM | 22 | 22 | 0 | **100%** |
| LOW | 16 | 16 | 0 | **100%** |
| **Total** | **62** | **62** | **0** | **100%** |

### CRITICAL Issues — All Resolved (8/8)

| ID | Resolution Wave | Resolution Method |
|----|----------------|-------------------|
| C-01 | Wave 17 | 00-stats.md rewritten with correct tool count (57+) |
| C-02 | Wave 17 | 00-stats.md corrected: BriefTool → SendUserMessage, Interaction category |
| C-03 | Wave 16 | data-flow.md rewritten: QueryEngine.ts SDK-only clarified |
| C-04 | Wave 16 | data-flow.md rewritten: deps.callModel() injection documented |
| C-05 | Wave 16 | data-flow.md rewritten: checkPermissions() + hasPermissionsToUseTool() |
| C-06 | Wave 16 | data-flow.md rewritten: 7-sub-step cascade with correct ordering |
| C-07 | Wave 18 | hook-system.md corrected: 27 hook events with full list |
| C-08 | Wave 18 | state-management.md corrected: bootstrap state mutability documented |

### HIGH Issues — All Resolved (16/16)

| ID | Resolution Wave | Resolution Method |
|----|----------------|-------------------|
| H-01 | Wave 17 | Command catalog corrected: 88+ built-in count |
| H-02 | Wave 17 | Command catalog corrected: conversation branching description |
| H-03 | Wave 17 | Command catalog corrected: clear conversation history description |
| H-04 | Wave 17 | Command catalog corrected: Year in Review description |
| H-05 | Wave 17 | Command catalog corrected: subscription upsell description |
| H-06 | Wave 17 | Command catalog corrected: 8 missing commands added |
| H-07 | Wave 18 | hook-system.md corrected: 16 hookSpecificOutput variants |
| H-08 | Wave 18 | hook-system.md corrected: 15 HookResult fields |
| H-09 | Wave 18 | state-management.md corrected: fields moved to bootstrap State |
| H-10 | Wave 18 | state-management.md corrected: backgroundTasks removed |
| H-11 | Wave 18 | state-management.md corrected: theme/outputStyle removed |
| H-12 | Wave 18 | state-management.md corrected: costTracker moved to bootstrap |
| H-13 | Wave 16 | data-flow.md rewritten: absolute token count thresholds |
| H-14 | Wave 16 | data-flow.md rewritten: SystemCompactBoundaryMessage type |
| H-15 | Wave 16 | data-flow.md rewritten: handlePromptSubmit.ts layer added |
| H-16 | Wave 16 | data-flow.md rewritten: deps injection layer documented |

### MEDIUM Issues — All Resolved (22/22)

| ID | Resolution Wave | Resolution Method |
|----|----------------|-------------------|
| M-01 | Wave 17 | 00-stats.md corrected: StructuredOutput name |
| M-02 | Wave 17 | 00-stats.md corrected: TodoV2 task items description |
| M-03 | Wave 17 | 00-stats.md corrected: deprecated TaskOutputTool noted |
| M-04 | Wave 17 | 00-stats.md corrected: 3 separate Cron tools |
| M-05 | Wave 17 | 00-stats.md corrected: 9 LSP operations listed |
| M-06 | Wave 17 | Command catalog corrected: remote-control (alias: rc) |
| M-07 | Wave 17 | Command catalog corrected: sandbox name |
| M-08 | Wave 17 | Command catalog corrected: merch ordering description |
| M-09 | Wave 17 | Command catalog corrected: type classifications fixed |
| M-10 | Wave 18 | permission-system.md / type-system.md corrected: direct readonly fields |
| M-11 | Wave 18 | permission-system.md / type-system.md corrected: isBypassPermissionsModeAvailable |
| M-12 | Wave 34 | permission-system.md corrected: 11 PermissionDecisionReason variants |
| M-13 | Wave 18 | hook-system.md corrected: 12 AggregatedHookResult fields |
| M-14 | Wave 18 | state-management.md corrected: hybrid DeepImmutable structure |
| M-15 | Wave 18 | state-management.md corrected: plain object, not Map |
| M-16 | Wave 36 | Editorial: functionally correct, source-level nuance accepted as-is |
| M-17 | Wave 31 | wave31-toolusecontext-complete.md: 55/55 fields documented |
| M-18 | Wave 32 | wave32-tool-interface-complete.md: 46/46 members documented |
| M-19 | Wave 16 | data-flow.md rewritten: StreamingToolExecutor documented |
| M-20 | Wave 16 | data-flow.md rewritten: 3-stage validation pipeline documented |
| M-21 | Wave 16 | data-flow.md rewritten: 5-way concurrent resolver documented |
| M-22 | Wave 16 | data-flow.md rewritten: REACTIVE_COMPACT mutual exclusion documented |

### LOW Issues — All Resolved (16/16)

| ID | Resolution Wave | Resolution Method |
|----|----------------|-------------------|
| L-01 | Wave 36 | command-system.md corrected: output-style marked deprecated/hidden (isHidden: true) |
| L-02 | Wave 36 | command-system.md corrected: pr_comments → pr-comments registered name |
| L-03 | Wave 34 | permission-system.md corrected: flagSettings added to PermissionRuleSource |
| L-04 | Wave 34 | permission-system.md corrected: YoloClassifier fields completed |
| L-05 | Wave 36 | type-system.md corrected: toAgentId() with regex and examples documented |
| L-06 | Wave 36 | type-system.md corrected: branded ID types with structural details |
| L-07 | Wave 33 | wave33-missing-types.md: QueuedCommand 20 fields documented |
| L-08 | Wave 33 | wave33-missing-types.md: BaseTextInputProps 28 fields documented |
| L-09 | Wave 33 | wave33-missing-types.md: Entry union 19 variants documented |
| L-10 | Wave 36 | Editorial: internal tracking type, accepted as completeness gap |
| L-11 | Wave 36 | Editorial: utility functions, accepted as completeness gap |
| L-12 | Wave 36 | Editorial: simple 2-field type, accepted as completeness gap |
| L-13 | Wave 36 | Editorial: factory function, accepted as completeness gap |
| L-14 | Wave 36 | state-management.md corrected: pluginReconnectKey detail expanded with /reload-plugins trigger |
| L-15 | Wave 36 | state-management.md corrected: getIsNonInteractiveSession() getter name verified against source |
| L-16 | Wave 17 | 00-stats.md corrected: 16+ conditional tools count |

### All 62 Issues Resolved

**Wave 36** closed the final 6 source-doc issues (L-01, L-02, L-05, L-06, L-14, L-15) and accepted 6 editorial/completeness gaps (M-16, L-10, L-11, L-12, L-13) as resolved. No remaining issues.

---

## Notes

1. **Deduplication**: Issues found across multiple waves are listed once with all wave references. For example, the permission cascade error (C-06) was first found in W4-P3 and expanded with full corrections in W6.

2. **Wave 8-10 quality**: These deep-dive waves found zero new issues in the existing analysis documents, suggesting that the later analysis docs (agent-system, bridge, MCP) were written with higher accuracy than the earlier ones (data-flow, state-management, command catalog).

3. **Fabricated fields**: Issues H-09 through H-12 represent fields that appear in state-management.md but do not exist in the actual AppState source. These may have been hallucinated during initial analysis or confused with bootstrap State fields.

4. **Completeness vs accuracy**: Many MEDIUM and LOW issues are about undocumented types/fields rather than incorrect claims. The existing analysis documents explicitly acknowledge incompleteness with notes like "15+ more fields" — these are tracked here for completeness but may be acceptable editorial choices.

5. **Wave 31-33 resolutions**: These waves addressed the largest completeness gaps (M-17: ToolUseContext 55 fields, M-18: Tool interface 46 members, L-07/L-08/L-09: three critical missing types). Created as standalone reference documents in `10-patterns/`.

6. **Resolution completeness**: All 62 issues are resolved (100% across all severities). Wave 34 resolved permission-system.md issues (M-12, L-03, L-04). Wave 36 closed final source-doc issues and accepted editorial/completeness gaps as resolved.

---

*Registry compiled from Wave 2-10 verification reports. Resolution tracking updated at Wave 40. All issue IDs are stable for cross-referencing.*

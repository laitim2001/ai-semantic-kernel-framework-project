# Feature Flag Inventory

> **Wave 13** | Claude Code CLI Source Analysis
> **Date**: 2026-04-01
> **Source**: `CC-Source/src/` — grep for `feature('FLAG')` (bun:bundle) and `checkStatsigFeatureGate`/`getFeatureValue` (GrowthBook/Statsig)

---

## Build-Time Flags (bun:bundle `feature()`)

These flags are resolved at build time. When `false`, the gated code is tree-shaken out entirely.

| # | Flag Name | Files Using It | Purpose | Category |
|---|-----------|---------------|---------|----------|
| 1 | `ABLATION_BASELINE` | entrypoints/cli.tsx | A/B testing baseline for ablation experiments | Telemetry |
| 2 | `AGENT_MEMORY_SNAPSHOT` | main.tsx, tools/AgentTool/loadAgentsDir.ts | Agent memory snapshot persistence | Agent |
| 3 | `AGENT_TRIGGERS` | cli/print.ts, constants/tools.ts, screens/REPL.tsx, skills/bundled/index.ts, tools/ScheduleCronTool/prompt.ts, tools.ts | Scheduled agent triggers (cron-based) | Agent |
| 4 | `AGENT_TRIGGERS_REMOTE` | skills/bundled/index.ts, tools.ts | Remote/cloud agent triggers | Agent |
| 5 | `ALLOW_TEST_VERSIONS` | utils/nativeInstaller/download.ts | Allow downloading test/pre-release versions | Build |
| 6 | `ANTI_DISTILLATION_CC` | services/api/claude.ts | Anti-distillation protection for API calls | Security |
| 7 | `AUTO_THEME` | components/design-system/ThemeProvider.tsx, components/ThemePicker.tsx, tools/ConfigTool/supportedSettings.ts | Automatic theme switching (light/dark) | UI |
| 8 | `AWAY_SUMMARY` | hooks/useAwaySummary.ts, screens/REPL.tsx | Summary generation when user is away | UX |
| 9 | `BASH_CLASSIFIER` | cli/structuredIO.ts, components/permissions/BashPermissionRequest/..., hooks/toolPermission/handlers/*.ts (10 files) | ML-based bash command permission classification | Permissions |
| 10 | `BG_SESSIONS` | commands/exit/exit.tsx, entrypoints/cli.tsx, main.tsx, query.ts, screens/REPL.tsx, utils/concurrentSessions.ts, utils/conversationRecovery.ts | Background session support | Sessions |
| 11 | `BREAK_CACHE_COMMAND` | context.ts | Command to break prompt cache | Debug |
| 12 | `BRIDGE_MODE` | bridge/bridgeEnabled.ts, commands/bridge/index.ts, commands.ts, components/PromptInput/..., entrypoints/cli.tsx, hooks/useReplBridge.tsx, main.tsx, screens/REPL.tsx (10 files) | Bridge mode for IDE/editor integrations | Integration |
| 13 | `BUDDY` | buddy/CompanionSprite.tsx, buddy/prompt.ts, buddy/useBuddyNotification.tsx, commands.ts, components/PromptInput/PromptInput.tsx, screens/REPL.tsx, utils/attachments.ts | Companion sprite (Larder the cat) | UX |
| 14 | `BUILDING_CLAUDE_APPS` | skills/bundled/index.ts | Skill for building Claude API apps | Skills |
| 15 | `BUILTIN_EXPLORE_PLAN_AGENTS` | tools/AgentTool/builtInAgents.ts | Built-in explore/plan agent presets | Agent |
| 16 | `BYOC_ENVIRONMENT_RUNNER` | entrypoints/cli.tsx | Bring-your-own-cloud environment runner | Cloud |
| 17 | `CACHED_MICROCOMPACT` | constants/prompts.ts, query.ts, services/api/claude.ts, services/api/logging.ts, services/compact/microCompact.ts | Cached micro-compaction for context management | Compaction |
| 18 | `CCR_AUTO_CONNECT` | bridge/bridgeEnabled.ts, utils/config.ts | Auto-connect to Claude Code Remote | Remote |
| 19 | `CCR_MIRROR` | bridge/bridgeEnabled.ts, bridge/remoteBridgeCore.ts, main.tsx | CCR mirror mode for remote sessions | Remote |
| 20 | `CCR_REMOTE_SETUP` | commands.ts | `/web` command for CCR remote setup | Remote |
| 21 | `CHICAGO_MCP` | entrypoints/cli.tsx, main.tsx, query/stopHooks.ts, query.ts, services/analytics/metadata.ts, services/mcp/client.ts, services/mcp/config.ts, state/AppStateStore.ts, utils/computerUse/*.ts (10 files) | MCP server infrastructure (codename "Chicago") | MCP |
| 22 | `COMMIT_ATTRIBUTION` | cli/print.ts, commands/clear/caches.ts, screens/REPL.tsx, services/compact/postCompactCleanup.ts, setup.ts, utils/attribution.ts, utils/sessionRestore.ts, utils/shell/bashProvider.ts, utils/worktree.ts | Git commit attribution tracking | Git |
| 23 | `COMPACTION_REMINDERS` | utils/attachments.ts | Reminders about context compaction | UX |
| 24 | `CONNECTOR_TEXT` | components/Message.tsx, constants/betas.ts, services/api/claude.ts, services/api/logging.ts, utils/messages.ts | Connector text beta feature for API | API |
| 25 | `CONTEXT_COLLAPSE` | commands/context/context-noninteractive.ts, commands/context/context.tsx, components/ContextVisualization.tsx, components/TokenWarning.tsx, query.ts, screens/REPL.tsx, services/compact/*.ts, setup.ts (10 files) | Context window collapse/visualization | Context |
| 26 | `COORDINATOR_MODE` | cli/print.ts, commands/clear/conversation.ts, components/PromptInput/..., coordinator/coordinatorMode.ts, main.tsx, QueryEngine.ts, screens/REPL.tsx, tools/AgentTool/*.ts (10 files) | Multi-agent coordinator orchestration mode | Agent |
| 27 | `COWORKER_TYPE_TELEMETRY` | services/analytics/metadata.ts | Telemetry for coworker/collaborator type | Telemetry |
| 28 | `DAEMON` | commands.ts, entrypoints/cli.tsx | Daemon/background process mode | System |
| 29 | `DIRECT_CONNECT` | main.tsx | Direct API connection (bypass proxy) | API |
| 30 | `DOWNLOAD_USER_SETTINGS` | cli/print.ts, commands/reload-plugins/reload-plugins.ts, services/settingsSync/index.ts | Download/sync user settings from cloud | Settings |
| 31 | `DUMP_SYSTEM_PROMPT` | entrypoints/cli.tsx | Debug: dump system prompt to output | Debug |
| 32 | `ENHANCED_TELEMETRY_BETA` | utils/telemetry/sessionTracing.ts | Enhanced telemetry with session tracing | Telemetry |
| 33 | `EXPERIMENTAL_SKILL_SEARCH` | commands.ts, components/messages/AttachmentMessage.tsx, constants/prompts.ts, query.ts, services/compact/compact.ts, services/mcp/useManageMCPConnections.ts, tools/SkillTool/SkillTool.ts, utils/attachments.ts, utils/messages.ts | Experimental skill search/indexing system | Skills |
| 34 | `EXTRACT_MEMORIES` | cli/print.ts, memdir/paths.ts, query/stopHooks.ts, utils/backgroundHousekeeping.ts | Auto-extract memories from conversations | Memory |
| 35 | `FILE_PERSISTENCE` | cli/print.ts, utils/filePersistence/filePersistence.ts | File-based persistence for session state | Sessions |
| 36 | `FORK_SUBAGENT` | commands/branch/index.ts, commands.ts, components/messages/UserTextMessage.tsx, tools/AgentTool/forkSubagent.ts, tools/ToolSearchTool/prompt.ts | Fork conversation as subagent | Agent |
| 37 | `HARD_FAIL` | main.tsx, utils/log.ts | Hard failure mode (crash on errors) | Debug |
| 38 | `HISTORY_PICKER` | components/PromptInput/PromptInput.tsx, hooks/useHistorySearch.ts | Interactive history search picker | UX |
| 39 | `HISTORY_SNIP` | commands.ts, components/Message.tsx, query.ts, QueryEngine.ts, tools.ts, utils/attachments.ts, utils/collapseReadSearch.ts, utils/messages.ts | Snip/collapse old history entries | Context |
| 40 | `HOOK_PROMPTS` | screens/REPL.tsx | Hook-injected prompts | Hooks |
| 41 | `IO` | *(no files found — possibly internal/unused)* | I/O related flag | System |
| 42 | `IS_LIBC_GLIBC` | utils/envDynamic.ts | Detect glibc runtime (Linux) | Build |
| 43 | `IS_LIBC_MUSL` | utils/envDynamic.ts | Detect musl runtime (Alpine Linux) | Build |
| 44 | `KAIROS` | bridge/bridgeMain.ts, bridge/initReplBridge.ts, cli/print.ts, commands/bridge/bridge.tsx, commands/brief.ts, commands/clear/conversation.ts, commands.ts, components/LogoV2/*.tsx, components/messages/UserPromptMessage.tsx (10+ files) | Kairos: background agent / proactive assistant | Agent |
| 45 | `KAIROS_BRIEF` | commands/brief.ts, commands.ts, components/messages/*.tsx, components/Messages.tsx, components/PromptInput/*.tsx, components/Settings/Config.tsx, components/Spinner.tsx (10 files) | Kairos brief/notification display | Agent |
| 46 | `KAIROS_CHANNELS` | cli/print.ts, components/LogoV2/*.tsx, components/messages/UserTextMessage.tsx, hooks/toolPermission/handlers/interactiveHandler.ts, hooks/useCanUseTool.tsx, interactiveHelpers.tsx, main.tsx, services/mcp/channelNotification.ts, services/mcp/useManageMCPConnections.ts (10 files) | Kairos multi-channel support | Agent |
| 47 | `KAIROS_DREAM` | skills/bundled/index.ts | Kairos dream mode (background processing) | Agent |
| 48 | `KAIROS_GITHUB_WEBHOOKS` | commands.ts, components/messages/UserTextMessage.tsx, hooks/useReplBridge.tsx, tools.ts | Kairos GitHub webhook subscriptions | Agent |
| 49 | `KAIROS_PUSH_NOTIFICATION` | components/Settings/Config.tsx, tools/ConfigTool/supportedSettings.ts, tools.ts | Kairos push notification support | Agent |
| 50 | `LODESTONE` | interactiveHelpers.tsx, main.tsx, utils/backgroundHousekeeping.ts, utils/settings/types.ts | Lodestone: persistent background service | System |
| 51 | `MCP_RICH_OUTPUT` | tools/MCPTool/UI.tsx | Rich output rendering for MCP tool results | MCP |
| 52 | `MCP_SKILLS` | commands.ts, services/mcp/client.ts, services/mcp/useManageMCPConnections.ts | MCP-based skill discovery | MCP |
| 53 | `MCPC` | *(no files found — possibly internal)* | MCP client flag | MCP |
| 54 | `MCPT` | *(no files found — possibly internal)* | MCP transport flag | MCP |
| 55 | `MEMORY_SHAPE_TELEMETRY` | memdir/findRelevantMemories.ts, utils/sessionFileAccessHooks.ts | Telemetry on memory shape/access patterns | Telemetry |
| 56 | `MESSAGE_ACTIONS` | keybindings/defaultBindings.ts, screens/REPL.tsx | Message-level action buttons (copy, edit, etc.) | UX |
| 57 | `MONITOR_TOOL` | components/permissions/PermissionRequest.tsx, components/tasks/BackgroundTasksDialog.tsx, tasks/LocalShellTask/LocalShellTask.tsx, tasks.ts, tools/AgentTool/runAgent.ts, tools/BashTool/*.ts, tools/PowerShellTool/PowerShellTool.tsx, tools.ts (10 files) | Background task monitoring tool | Tools |
| 58 | `NATIVE_CLIENT_ATTESTATION` | constants/system.ts | Native client attestation for API auth | Security |
| 59 | `NATIVE_CLIPBOARD_IMAGE` | utils/imagePaste.ts | Native clipboard image paste support | UX |
| 60 | `NEW_INIT` | commands/init.ts | Redesigned `/init` command flow | Commands |
| 61 | `OVERFLOW_TEST_TOOL` | tools.ts, utils/permissions/classifierDecision.ts | Test tool for context overflow scenarios | Debug |
| 62 | `PERFETTO_TRACING` | utils/telemetry/perfettoTracing.ts | Perfetto performance tracing integration | Telemetry |
| 63 | `POWERSHELL_AUTO_MODE` | utils/permissions/permissions.ts, utils/permissions/yoloClassifier.ts | Auto-approve PowerShell commands | Permissions |
| 64 | `PROACTIVE` | cli/print.ts, commands/clear/conversation.ts, commands.ts, components/Messages.tsx, components/PromptInput/*.ts, constants/prompts.ts, main.tsx, screens/REPL.tsx, services/compact/prompt.ts (10 files) | Proactive suggestions from Claude | Agent |
| 65 | `PROMPT_CACHE_BREAK_DETECTION` | commands/compact/compact.ts, services/api/claude.ts, services/compact/autoCompact.ts, services/compact/compact.ts, services/compact/microCompact.ts, tools/AgentTool/runAgent.ts | Detect and handle prompt cache breaks | Context |
| 66 | `QUICK_SEARCH` | components/PromptInput/PromptInput.tsx, keybindings/defaultBindings.ts | Quick search keybinding in prompt input | UX |
| 67 | `REACTIVE_COMPACT` | commands/compact/compact.ts, components/TokenWarning.tsx, query.ts, services/compact/autoCompact.ts, utils/analyzeContext.ts | Reactive (automatic) context compaction | Compaction |
| 68 | `REPL` | *(no files found — possibly internal)* | REPL mode flag | System |
| 69 | `REVIEW_ARTIFACT` | components/permissions/PermissionRequest.tsx, skills/bundled/index.ts | Code review artifact generation | Skills |
| 70 | `RUN_SKILL_GENERATOR` | skills/bundled/index.ts | Skill generator execution | Skills |
| 71 | `SELF_HOSTED_RUNNER` | entrypoints/cli.tsx | Self-hosted runner mode | Cloud |
| 72 | `SHOT_STATS` | components/Stats.tsx, utils/stats.ts, utils/statsCache.ts | Token/cost statistics display | UX |
| 73 | `SKILL_IMPROVEMENT` | utils/hooks/skillImprovement.ts | Auto-improve skills based on usage | Skills |
| 74 | `SKIP_DETECTION_WHEN_AUTOUPDATES_DISABLED` | components/AutoUpdaterWrapper.tsx | Skip update detection when auto-updates off | Build |
| 75 | `SLOW_OPERATION_LOGGING` | utils/slowOperations.ts | Log slow operations for perf debugging | Telemetry |
| 76 | `SSH_REMOTE` | main.tsx | SSH remote connection mode | Remote |
| 77 | `STREAMLINED_OUTPUT` | cli/print.ts | Streamlined/minimal output formatting | UX |
| 78 | `STT` | *(no files found — possibly internal)* | Speech-to-text flag | Voice |
| 79 | `TEAMMEM` | components/memory/MemoryFileSelector.tsx, components/messages/*.tsx, memdir/memdir.ts, services/extractMemories/*.ts, services/teamMemorySync/*.ts (10 files) | Team shared memory system | Memory |
| 80 | `TEMPLATES` | entrypoints/cli.tsx, query/stopHooks.ts, query.ts, utils/markdownConfigLoader.ts, utils/permissions/filesystem.ts | Template system for project scaffolding | Commands |
| 81 | `TERMINAL_PANEL` | components/PromptInput/PromptInputHelpMenu.tsx, hooks/useGlobalKeybindings.tsx, keybindings/defaultBindings.ts, tools.ts, utils/permissions/classifierDecision.ts | Embedded terminal panel in UI | Tools |
| 82 | `TOKEN_BUDGET` | components/PromptInput/PromptInput.tsx, components/Spinner.tsx, constants/prompts.ts, query.ts, screens/REPL.tsx, utils/attachments.ts | Token budget management and display | Context |
| 83 | `TORCH` | commands.ts | Torch command (unknown purpose) | Commands |
| 84 | `TRANSCRIPT_CLASSIFIER` | cli/print.ts, cli/structuredIO.ts, commands/login/login.tsx, components/messages/UserToolResultMessage/*.tsx, components/permissions/*.ts, components/PromptInput/PromptInput.tsx (10+ files) | ML transcript classifier for permissions | Permissions |
| 85 | `TREE_SITTER_BASH` | utils/bash/parser.ts | Tree-sitter based bash command parsing | Permissions |
| 86 | `TREE_SITTER_BASH_SHADOW` | tools/BashTool/bashPermissions.ts, utils/bash/parser.ts | Shadow-mode tree-sitter bash (comparison) | Permissions |
| 87 | `UDS_INBOX` | cli/print.ts, commands.ts, components/messages/UserTextMessage.tsx, main.tsx, setup.ts, tools/SendMessageTool/*.ts, tools.ts, utils/concurrentSessions.ts, utils/messages/systemInit.ts | Unix domain socket inbox (peer messaging) | Communication |
| 88 | `ULTRAPLAN` | commands.ts, components/permissions/ExitPlanModePermissionRequest/..., components/PromptInput/PromptInput.tsx, screens/REPL.tsx, utils/processUserInput/processUserInput.ts | Ultra-plan mode (deep planning) | Commands |
| 89 | `ULTRATHINK` | utils/thinking.ts | Ultra-think extended reasoning mode | Commands |
| 90 | `UNATTENDED_RETRY` | services/api/withRetry.ts | Auto-retry in unattended/headless mode | API |
| 91 | `UPLOAD_USER_SETTINGS` | main.tsx, services/settingsSync/index.ts | Upload/sync user settings to cloud | Settings |
| 92 | `VERIFICATION_AGENT` | constants/prompts.ts, tools/AgentTool/builtInAgents.ts, tools/TaskUpdateTool/TaskUpdateTool.ts, tools/TodoWriteTool/TodoWriteTool.ts | Built-in verification agent | Agent |
| 93 | `VOICE_MODE` | commands.ts, components/LogoV2/VoiceModeNotice.tsx, components/PromptInput/*.tsx, components/TextInput.tsx, hooks/useVoiceIntegration.tsx, keybindings/defaultBindings.ts, screens/REPL.tsx, services/voiceStreamSTT.ts (10 files) | Voice input/output mode | Voice |
| 94 | `WEB_BROWSER_TOOL` | main.tsx, screens/REPL.tsx, tools.ts | Web browser tool (computer use) | Tools |
| 95 | `WORKFLOW_SCRIPTS` | commands.ts, components/permissions/PermissionRequest.tsx, components/tasks/BackgroundTasksDialog.tsx, constants/tools.ts, tasks.ts, tools.ts, utils/permissions/classifierDecision.ts | Workflow script execution system | Commands |

---

## Runtime Flags (GrowthBook / Statsig)

These flags are evaluated at runtime via cached GrowthBook/Statsig calls. They allow server-side A/B testing and gradual rollouts without rebuilding.

| # | Flag Name | Type | Files Using It | Purpose |
|---|-----------|------|---------------|---------|
| 1 | `tengu_amber_quartz_disabled` | `getFeatureValue` | voice/voiceModeEnabled.ts | Kill-switch for voice mode (inverted: disabled=off) |
| 2 | `tengu_attribution_header` | `getFeatureValue` | constants/system.ts | Enable attribution header in API requests |
| 3 | `tengu_chair_sermon` | `getFeatureValue` | utils/messages.ts | Unknown — message processing behavior |
| 4 | `tengu_scratch` | `checkStatsigFeatureGate` | coordinator/coordinatorMode.ts, utils/permissions/filesystem.ts | Gate for coordinator mode + filesystem permissions |
| 5 | `tengu_slate_prism` | `getFeatureValue` | cli/print.ts, utils/betas.ts | Output formatting / beta features toggle |
| 6 | `tengu_thinkback` | `getFeatureValue` | commands/thinkback/index.ts, commands/thinkback-play/index.ts | Thinkback command (conversation replay) |
| 7 | `tengu_tool_pear` | `getFeatureValue` | Tool.ts, utils/api.ts, utils/betas.ts, utils/toolSchemaCache.ts | Tool schema / API behavior modifications |

---

## Summary

| Metric | Count |
|--------|-------|
| **Total build-time flags** | **95** |
| **Total runtime flags** | **7** |
| **Grand total** | **102** |

### By Category (Build-Time)

| Category | Count | Flags |
|----------|-------|-------|
| **Agent** | 13 | AGENT_MEMORY_SNAPSHOT, AGENT_TRIGGERS, AGENT_TRIGGERS_REMOTE, BUILTIN_EXPLORE_PLAN_AGENTS, COORDINATOR_MODE, FORK_SUBAGENT, KAIROS, KAIROS_BRIEF, KAIROS_CHANNELS, KAIROS_DREAM, KAIROS_GITHUB_WEBHOOKS, KAIROS_PUSH_NOTIFICATION, PROACTIVE, VERIFICATION_AGENT |
| **UX** | 9 | AUTO_THEME, AWAY_SUMMARY, COMPACTION_REMINDERS, HISTORY_PICKER, MESSAGE_ACTIONS, NATIVE_CLIPBOARD_IMAGE, QUICK_SEARCH, SHOT_STATS, STREAMLINED_OUTPUT |
| **Commands** | 6 | NEW_INIT, TEMPLATES, TORCH, ULTRAPLAN, ULTRATHINK, WORKFLOW_SCRIPTS |
| **Context/Compaction** | 6 | CACHED_MICROCOMPACT, CONTEXT_COLLAPSE, HISTORY_SNIP, PROMPT_CACHE_BREAK_DETECTION, REACTIVE_COMPACT, TOKEN_BUDGET |
| **Permissions** | 5 | BASH_CLASSIFIER, POWERSHELL_AUTO_MODE, TRANSCRIPT_CLASSIFIER, TREE_SITTER_BASH, TREE_SITTER_BASH_SHADOW |
| **MCP** | 4 | CHICAGO_MCP, MCP_RICH_OUTPUT, MCP_SKILLS, MCPC, MCPT |
| **Remote** | 4 | CCR_AUTO_CONNECT, CCR_MIRROR, CCR_REMOTE_SETUP, SSH_REMOTE |
| **Skills** | 4 | BUILDING_CLAUDE_APPS, EXPERIMENTAL_SKILL_SEARCH, REVIEW_ARTIFACT, RUN_SKILL_GENERATOR, SKILL_IMPROVEMENT |
| **Telemetry** | 5 | COWORKER_TYPE_TELEMETRY, ENHANCED_TELEMETRY_BETA, MEMORY_SHAPE_TELEMETRY, PERFETTO_TRACING, SLOW_OPERATION_LOGGING |
| **Tools** | 3 | MONITOR_TOOL, TERMINAL_PANEL, WEB_BROWSER_TOOL |
| **Sessions** | 2 | BG_SESSIONS, FILE_PERSISTENCE |
| **Memory** | 2 | EXTRACT_MEMORIES, TEAMMEM |
| **Security** | 2 | ANTI_DISTILLATION_CC, NATIVE_CLIENT_ATTESTATION |
| **API** | 3 | CONNECTOR_TEXT, DIRECT_CONNECT, UNATTENDED_RETRY |
| **Cloud** | 2 | BYOC_ENVIRONMENT_RUNNER, SELF_HOSTED_RUNNER |
| **Voice** | 2 | STT, VOICE_MODE |
| **Settings** | 2 | DOWNLOAD_USER_SETTINGS, UPLOAD_USER_SETTINGS |
| **Build** | 4 | ALLOW_TEST_VERSIONS, IS_LIBC_GLIBC, IS_LIBC_MUSL, SKIP_DETECTION_WHEN_AUTOUPDATES_DISABLED |
| **Git** | 1 | COMMIT_ATTRIBUTION |
| **Communication** | 1 | UDS_INBOX |
| **Debug** | 4 | BREAK_CACHE_COMMAND, DUMP_SYSTEM_PROMPT, HARD_FAIL, OVERFLOW_TEST_TOOL |
| **Hooks** | 1 | HOOK_PROMPTS |
| **Integration** | 1 | BRIDGE_MODE |
| **System** | 4 | ABLATION_BASELINE, DAEMON, IO, LODESTONE, REPL |

### Flags Affecting Tool Availability

These flags gate whether specific tools appear in the tool list:

| Flag | Tool Gated |
|------|-----------|
| `AGENT_TRIGGERS` / `AGENT_TRIGGERS_REMOTE` | ScheduleCronTool |
| `MONITOR_TOOL` | MonitorTool (background task monitor) |
| `TERMINAL_PANEL` | Terminal panel tool |
| `WEB_BROWSER_TOOL` | Web browser / computer-use tool |
| `OVERFLOW_TEST_TOOL` | Test overflow tool (debug) |
| `KAIROS_PUSH_NOTIFICATION` | Push notification tool |
| `KAIROS_GITHUB_WEBHOOKS` | GitHub webhook subscription tool |
| `UDS_INBOX` | SendMessageTool (peer messaging) |
| `WORKFLOW_SCRIPTS` | Workflow script tools |
| `CHICAGO_MCP` | MCP server tools |

### Flags Affecting Command Availability

These flags gate whether specific slash commands are registered:

| Flag | Command Gated |
|------|--------------|
| `KAIROS` / `KAIROS_BRIEF` | `/assistant`, `/brief` |
| `BRIDGE_MODE` | `/bridge` |
| `VOICE_MODE` | `/voice` |
| `HISTORY_SNIP` | `/snip` |
| `WORKFLOW_SCRIPTS` | `/workflows` |
| `CCR_REMOTE_SETUP` | `/web` |
| `EXPERIMENTAL_SKILL_SEARCH` | `/clear-skill-index-cache` |
| `KAIROS_GITHUB_WEBHOOKS` | `/subscribe-pr` |
| `ULTRAPLAN` | `/ultraplan` |
| `TORCH` | `/torch` |
| `UDS_INBOX` | `/peers` |
| `FORK_SUBAGENT` | `/fork` |
| `BUDDY` | `/buddy` |
| `DAEMON` | `/daemon` (with BRIDGE_MODE) |
| `PROACTIVE` | Affects `/assistant` availability |
| `BG_SESSIONS` | `/bg`, `/sessions` |

### Flags with No File References Found

These flags were detected in the `feature()` pattern but no source files matched (may be used only in build config or conditionally):

- `IO`
- `MCPC`
- `MCPT`
- `REPL`
- `STT`

### Notable Patterns

1. **Kairos Family** (6 flags): A major feature group for background/proactive agent capabilities — `KAIROS`, `KAIROS_BRIEF`, `KAIROS_CHANNELS`, `KAIROS_DREAM`, `KAIROS_GITHUB_WEBHOOKS`, `KAIROS_PUSH_NOTIFICATION`
2. **CCR Family** (3 flags): Claude Code Remote — `CCR_AUTO_CONNECT`, `CCR_MIRROR`, `CCR_REMOTE_SETUP`
3. **Tengu Naming** (7 runtime flags): All runtime flags use a `tengu_` prefix with obfuscated codenames, making their purpose less discoverable
4. **Permission System** (5 flags): Heavy investment in ML-based permission classification — `BASH_CLASSIFIER`, `TRANSCRIPT_CLASSIFIER`, `TREE_SITTER_BASH`, `TREE_SITTER_BASH_SHADOW`, `POWERSHELL_AUTO_MODE`
5. **Context Management** (6 flags): Multiple strategies for context window management — `CONTEXT_COLLAPSE`, `HISTORY_SNIP`, `REACTIVE_COMPACT`, `CACHED_MICROCOMPACT`, `TOKEN_BUDGET`, `PROMPT_CACHE_BREAK_DETECTION`

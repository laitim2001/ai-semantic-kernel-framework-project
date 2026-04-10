# Claude Code CLI — Codebase Statistics

> **Wave 58 Updated** — All Wave 2 (tool), Wave 3 (command), Wave 41-46 (service + utility) corrections applied.
> Generated: 2026-04-01 | Scope: Claude Code CLI source (CC-Source/src/) | Baseline: manual file inventory

---

## 1. Overall Metrics

| Metric | Value |
|--------|-------|
| **Total Source Files** | ~1,884 TypeScript files in src/ |
| **Total LOC** | ~40,713 lines of code |
| **Runtime** | Bun (bundled) + Node.js compatible |
| **Language** | TypeScript (strict) + TSX (React/Ink) |
| **UI Framework** | Ink v5 (React for terminal) |
| **Build System** | Bun bundle with feature-flag dead-code elimination |
| **Primary Entry** | `src/entrypoints/cli.tsx` → `src/main.tsx` |

---

## 2. Directory File Counts

| Directory | Files | Notes |
|-----------|-------|-------|
| `src/utils/` | 564 | Largest directory; auth, model, settings, permissions, git, plugins |
| `src/components/` | 389 | React/Ink UI components |
| `src/commands/` | 189 | ~86 command directories, each with index.ts + implementation |
| `src/tools/` | 184 | ~40 tool directories, each with Tool.ts + UI.tsx + prompt.ts |
| `src/services/` | 130 | 24 service sub-systems |
| `src/hooks/` | 104 | React hooks (notifications, permissions, IDE, etc.) |
| `src/ink/` | 96 | Ink terminal I/O infrastructure |
| `src/bridge/` | 31 | REPL bridge for remote/IDE connections |
| `src/constants/` | 21 | App-wide constants |
| `src/skills/` | 20 | Bundled slash-command skills |
| `src/cli/` | 19 | CLI I/O, transports (SSE, WebSocket, CCR) |
| `src/keybindings/` | 14 | Vim/custom keybinding system |
| `src/tasks/` | 12 | Background task runners (Agent, Shell, Remote) |
| `src/types/` | 11 | Shared TypeScript type definitions |
| `src/migrations/` | 11 | Config/settings migration scripts |
| `src/context/` | 9 | React context providers |
| `src/memdir/` | 8 | Memory directory (CLAUDE.md/memory management) |
| `src/entrypoints/` | 8 | Entry point files + SDK type exports |
| `src/state/` | 6 | AppState store (Zustand-like) |
| `src/buddy/` | 6 | Buddy/pair-programming feature |
| `src/vim/` | 5 | Vim mode implementation |
| `src/remote/` | 4 | Remote session management |
| `src/query/` | 4 | Query engine config, token budget, stop hooks |
| `src/native-ts/` | 4 | Native TypeScript modules (cross-platform) |
| `src/server/` | 3 | Direct-connect server |
| `src/screens/` | 3 | Top-level screen components (REPL, Doctor, Resume) |
| `src/upstreamproxy/` | 2 | Upstream proxy support |
| `src/plugins/` | 2 | Plugin bundling infrastructure |
| `src/coordinator/` | 1 | Coordinator mode (multi-agent orchestration) |
| `src/bootstrap/` | 1 | Global state singleton (`state.ts`) |
| `src/assistant/` | 1 | KAIROS assistant mode |
| `src/schemas/` | 1 | JSON schema definitions |
| Others (voice, outputStyles, etc.) | ~5 | Miscellaneous |
| **Total** | **1,884** | |

### Root-level Key Files

| File | Role |
|------|------|
| `src/main.tsx` | Primary application entry; Commander.js CLI setup, REPL launch |
| `src/Tool.ts` | Tool interface definition and type system |
| `src/tools.ts` | Tool registry; imports and exposes all tools to the engine |
| `src/commands.ts` | Command registry |
| `src/query.ts` | Core query loop (single-turn API call with tool execution) |
| `src/QueryEngine.ts` | Multi-turn conversation loop (wraps `query.ts`) |
| `src/context.ts` | System/user context builders |
| `src/replLauncher.ts` | REPL mode launcher |
| `src/cost-tracker.ts` | Token cost accounting |
| `src/history.ts` | Conversation history persistence |
| `src/dialogLaunchers.ts` | Modal dialog orchestration |
| `src/interactiveHelpers.ts` | Interactive mode setup helpers |

---

## 3. Tool Catalog (57+ tools: 40 directories + 16+ conditional/feature-gated)

### Core Tools — Always Available (43)

| # | Tool Name | Directory | Category | Description |
|---|-----------|-----------|----------|-------------|
| 1 | AgentTool | `tools/AgentTool/` | Agent | Spawns sub-agents; full AgentTool.tsx + runAgent.ts |
| 2 | AskUserQuestionTool | `tools/AskUserQuestionTool/` | Interaction | Prompts user for input during autonomous runs |
| 3 | BashTool | `tools/BashTool/` | Shell | Executes shell commands; sandboxing, security validation |
| 4 | **SendUserMessage** | `tools/BriefTool/` | **Interaction** | Sends messages/files to the user in KAIROS assistant mode |
| 5 | ConfigTool | `tools/ConfigTool/` | Config | Reads/writes Claude Code configuration settings |
| 6 | EnterPlanModeTool | `tools/EnterPlanModeTool/` | Mode | Switches session to plan-only mode |
| 7 | EnterWorktreeTool | `tools/EnterWorktreeTool/` | Mode | Switches working directory to a git worktree |
| 8 | ExitPlanModeV2Tool | `tools/ExitPlanModeTool/` | Mode | Exits plan mode and executes approved plan |
| 9 | ExitWorktreeTool | `tools/ExitWorktreeTool/` | Mode | Returns from worktree to main directory |
| 10 | FileEditTool | `tools/FileEditTool/` | Files | Applies targeted string replacements to files |
| 11 | FileReadTool | `tools/FileReadTool/` | Files | Reads file contents; handles images, token limits |
| 12 | FileWriteTool | `tools/FileWriteTool/` | Files | Creates or overwrites files |
| 13 | GlobTool | `tools/GlobTool/` | Search | Pattern-based file path matching |
| 14 | GrepTool | `tools/GrepTool/` | Search | Regex content search across files |
| 15 | ListMcpResourcesTool | `tools/ListMcpResourcesTool/` | MCP | Lists available MCP server resources |
| 16 | LSPTool | `tools/LSPTool/` | IDE | Language Server Protocol integration (9 operations: definitions, references, hover, symbols, call hierarchy, implementation, type definitions, document symbols, workspace symbols) |
| 17 | McpAuthTool | `tools/McpAuthTool/` | MCP | Handles MCP server OAuth authentication |
| 18 | MCPTool | `tools/MCPTool/` | MCP | Generic bridge to MCP server tools |
| 19 | NotebookEditTool | `tools/NotebookEditTool/` | Files | Edits Jupyter notebook cells |
| 20 | PowerShellTool | `tools/PowerShellTool/` | Shell | Executes PowerShell commands (Windows) |
| 21 | ReadMcpResourceTool | `tools/ReadMcpResourceTool/` | MCP | Reads content from MCP server resources |
| 22 | RemoteTriggerTool | `tools/RemoteTriggerTool/` | Remote | Triggers remote agent execution |
| 23 | CronCreateTool | `tools/ScheduleCronTool/` | Tasks | Creates scheduled cron tasks |
| 24 | CronDeleteTool | `tools/ScheduleCronTool/` | Tasks | Deletes scheduled cron tasks |
| 25 | CronListTool | `tools/ScheduleCronTool/` | Tasks | Lists scheduled cron tasks |
| 26 | SendMessageTool | `tools/SendMessageTool/` | Swarm | Sends messages between agents in a swarm |
| 27 | SkillTool | `tools/SkillTool/` | Skills | Executes registered slash-command skills |
| 28 | **StructuredOutput** | `tools/SyntheticOutputTool/` | Internal | Emits structured JSON output for SDK consumers |
| 29 | TaskCreateTool | `tools/TaskCreateTool/` | Tasks | Creates TodoV2 task items (structured todo lists with status tracking) |
| 30 | TaskGetTool | `tools/TaskGetTool/` | Tasks | Gets task status/details |
| 31 | TaskListTool | `tools/TaskListTool/` | Tasks | Lists all tasks |
| 32 | TaskOutputTool **(deprecated)** | `tools/TaskOutputTool/` | Tasks | Reads/retrieves task output (deprecated in favor of TaskGetTool) |
| 33 | TaskStopTool | `tools/TaskStopTool/` | Tasks | Stops a running task |
| 34 | TaskUpdateTool | `tools/TaskUpdateTool/` | Tasks | Updates task state |
| 35 | TeamCreateTool | `tools/TeamCreateTool/` | Swarm | Creates an agent team (swarm) |
| 36 | TeamDeleteTool | `tools/TeamDeleteTool/` | Swarm | Dissolves an agent team |
| 37 | TestingPermissionTool | `tools/testing/` | Testing | Validates permission logic in tests |
| 38 | TodoWriteTool | `tools/TodoWriteTool/` | Tasks | Writes structured todo lists |
| 39 | ToolSearchTool | `tools/ToolSearchTool/` | Meta | Searches for available tools by description |
| 40 | WebFetchTool | `tools/WebFetchTool/` | Web | Fetches and extracts content from URLs |
| 41 | WebSearchTool | `tools/WebSearchTool/` | Web | Performs web searches |

### Conditionally Loaded Tools (16+)

> These tools are feature-gated or stripped from external builds. 14+ tool directories are referenced in `tools.ts` but absent from the CC-Source dump (phantom directories). Count is approximate due to build-time elimination.

| # | Tool Name | Condition | Description |
|---|-----------|-----------|-------------|
| 42 | REPLTool | `USER_TYPE=ant` | Interactive REPL for Anthropic internal use |
| 43 | SleepTool | `feature('PROACTIVE') \| feature('KAIROS')` | Pauses agent execution |
| 44 | MonitorTool | `feature('MONITOR_TOOL')` | Monitors system events |
| 45 | SendUserFileTool | `feature('KAIROS')` | Sends files to user (assistant mode) |
| 46 | PushNotificationTool | `feature('KAIROS')` | Sends push notifications |
| 47 | SubscribePRTool | `feature('KAIROS_GITHUB_WEBHOOKS')` | Subscribes to GitHub PR webhooks |
| 48 | VerifyPlanExecutionTool | `CLAUDE_CODE_VERIFY_PLAN=true` | Verifies plan execution correctness |
| 49-57+ | *(14+ phantom directories)* | Various feature flags | Referenced in `tools.ts` but stripped from external builds |

---

## 4. Command Catalog (88+ built-in commands)

Commands are registered in `src/commands.ts` (755 lines) and implemented in `src/commands/<name>/`.

> **Notes**:
> - 23 commands are internal-only (`INTERNAL_ONLY_COMMANDS` array)
> - ~12 commands are conditionally loaded via `feature()` flags
> - ~12-17 commands use identical JS-only stub pattern in external builds: `{ isEnabled: () => false, isHidden: true, name: 'stub' }`
> - Some directories export multiple commands (dual-export pattern): `remote-setup/` → `remote-setup` + `web-setup`; `review/` → `review` + `ultrareview`

| # | Command | Registered Name | Category | Description |
|---|---------|-----------------|----------|-------------|
| 1 | `add-dir` | `add-dir` | Config | Add additional working directory |
| 2 | `agents` | `agents` | Agents | Manage custom agents |
| 3 | `ant-trace` | `ant-trace` | Debug | Anthropic internal trace **(stub in external builds)** |
| 4 | `autofix-pr` | `autofix-pr` | Git | Auto-fix PR issues |
| 5 | `backfill-sessions` | `backfill-sessions` | Session | Backfill session data **(stub in external builds)** |
| 6 | `branch` | `branch` | Session | **Conversation branching** (fork conversation history) |
| 7 | `break-cache` | `break-cache` | Debug | Break internal caches **(stub in external builds)** |
| 8 | `bridge` | **`remote-control`** (alias: `rc`) | Remote | REPL bridge connection |
| 9 | `btw` | `btw` | Internal | BTW (Anthropic internal) **(stub in external builds)** |
| 10 | `bughunter` | `bughunter` | AI | Bug hunting mode |
| 11 | `chrome` | `chrome` | Integrations | Chrome extension setup |
| 12 | `clear` | `clear` | Session | **Clear conversation history / caches** |
| 13 | `color` | `color` | UI | Configure terminal color theme |
| 14 | `compact` | `compact` | Session | Compact conversation history |
| 15 | `config` | `config` | Config | Show/edit configuration |
| 16 | `context` | `context` | Session | Show context window usage |
| 17 | `copy` | `copy` | UI | Copy output to clipboard |
| 18 | `cost` | `cost` | Session | Show session cost / token usage |
| 19 | `ctx_viz` | `ctx_viz` | Debug | Context visualization **(stub in external builds)** |
| 20 | `debug-tool-call` | `debug-tool-call` | Debug | Debug tool call execution **(stub in external builds)** |
| 21 | `desktop` | `desktop` | Integrations | Desktop app handoff |
| 22 | `diff` | `diff` | Files | Show file diffs |
| 23 | `doctor` | `doctor` | Diagnostics | System health check |
| 24 | `effort` | `effort` | AI | Set reasoning effort level |
| 25 | `env` | `env` | Config | Environment variable management **(stub in external builds)** |
| 26 | `exit` | `exit` | Session | Exit Claude Code |
| 27 | `export` | `export` | Session | Export conversation transcript |
| 28 | `extra-usage` | `extra-usage` | Session | Show extended usage stats |
| 29 | `fast` | `fast` | AI | Toggle fast mode |
| 30 | `feedback` | `feedback` | UI | Submit feedback |
| 31 | `files` | `files` | Files | File management helpers |
| 32 | `good-claude` | `good-claude` | UI | Positive feedback shortcut **(stub in external builds)** |
| 33 | `heapdump` | `heapdump` | Debug | Generate heap dump |
| 34 | `help` | `help` | UI | Show help text |
| 35 | `hooks` | `hooks` | Config | Manage event hooks |
| 36 | `ide` | `ide` | Integrations | IDE integration setup |
| 37 | `install-github-app` | `install-github-app` | Integrations | Install GitHub Actions app |
| 38 | `install-slack-app` | `install-slack-app` | Integrations | Install Slack integration |
| 39 | `issue` | `issue` | Internal | Issue reporting **(stub in external builds)** |
| 40 | `keybindings` | `keybindings` | Config | Manage keyboard shortcuts |
| 41 | `login` | `login` | Auth | Authenticate with Anthropic |
| 42 | `logout` | `logout` | Auth | Log out / clear credentials |
| 43 | `mcp` | `mcp` | MCP | Manage MCP servers |
| 44 | `memory` | `memory` | Memory | Manage CLAUDE.md memory files |
| 45 | `mobile` | `mobile` | Remote | Mobile device connection |
| 46 | `mock-limits` | `mock-limits` | Debug | Mock rate limits for testing **(stub in external builds)** |
| 47 | `model` | `model` | AI | Select/change AI model |
| 48 | `oauth-refresh` | `oauth-refresh` | Auth | Refresh OAuth token **(stub in external builds)** |
| 49 | `onboarding` | `onboarding` | Setup | Run onboarding flow **(stub in external builds)** |
| 50 | `output-style` | `output-style` | UI | Configure output style **(deprecated, hidden)** |
| 51 | `passes` | `passes` | Auth | Manage usage passes |
| 52 | `perf-issue` | `perf-issue` | Debug | Performance issue reporting **(stub in external builds)** |
| 53 | `permissions` | `permissions` | Security | Manage tool permissions |
| 54 | `plan` | `plan` | AI | Enter plan mode |
| 55 | `plugin` | `plugin` | Plugins | Manage plugins |
| 56 | `pr_comments` | **`pr-comments`** | Git | Show PR comments |
| 57 | `privacy-settings` | `privacy-settings` | Config | Configure privacy settings |
| 58 | `rate-limit-options` | `rate-limit-options` | Config | Configure rate limit behavior |
| 59 | `release-notes` | `release-notes` | Info | Show release notes |
| 60 | `reload-plugins` | `reload-plugins` | Plugins | Reload plugin configurations |
| 61 | `remote-env` | `remote-env` | Remote | Remote environment config |
| 62 | `remote-setup` | `remote-setup` | Remote | Remote session setup |
| 63 | `rename` | `rename` | Session | Rename current session |
| 64 | `reset-limits` | `reset-limits` | Debug | Reset rate limits **(stub in external builds)** |
| 65 | `resume` | `resume` | Session | Resume a previous session |
| 66 | `review` | `review` | AI | Code review mode |
| 67 | `rewind` | `rewind` | Session | Rewind conversation history |
| 68 | `sandbox-toggle` | **`sandbox`** | Security | Toggle sandbox mode |
| 69 | `session` | `session` | Session | Session management |
| 70 | `share` | `share` | Session | Share conversation **(stub in external builds)** |
| 71 | `skills` | `skills` | Skills | Manage custom skills |
| 72 | `stats` | `stats` | Session | Show session statistics |
| 73 | `status` | `status` | Session | Show current session status |
| 74 | `stickers` | `stickers` | UI | **Merchandise ordering** (physical sticker merchandise) |
| 75 | `summary` | `summary` | AI | Generate summary **(stub in external builds)** |
| 76 | `tag` | `tag` | Session | Tag conversations |
| 77 | `tasks` | `tasks` | Tasks | Manage background tasks |
| 78 | `teleport` | `teleport` | Remote | Teleport to remote env **(stub in external builds)** |
| 79 | `terminalSetup` | `terminalSetup` | Setup | Terminal setup helpers |
| 80 | `theme` | `theme` | UI | Switch UI theme |
| 81 | `thinkback` | `thinkback` | AI | **Year in Review** — session statistics retrospective |
| 82 | `thinkback-play` | `thinkback-play` | AI | Animation playback for thinkback review |
| 83 | `ultrareview` | `ultrareview` | AI | Extended code review (exported from `review/`) |
| 84 | `upgrade` | `upgrade` | Setup | **Subscription plan upsell** (upgrade plan tier) |
| 85 | `usage` | `usage` | Session | Show API usage |
| 86 | `vim` | `vim` | Config | Toggle vim mode |
| 87 | `voice` | `voice` | Input | Voice input mode |
| 88 | `web-setup` | `web-setup` | Remote | Web session setup (exported from `remote-setup/`) |

### 23 Internal-Only Commands (`INTERNAL_ONLY_COMMANDS`)

ant-trace, backfill-sessions, break-cache, btw, bughunter, ctx_viz, debug-tool-call, env, good-claude, heapdump, issue, mock-limits, oauth-refresh, onboarding, perf-issue, reset-limits, share, stickers, summary, teleport, and others.

---

## 5. Service Catalog (24 subsystems) — Deep Inventory

| Subsystem | Directory | Files | LOC | Responsibility |
|-----------|-----------|-------|-----|----------------|
| **Analytics** | `services/analytics/` | — | — | Event logging, A/B testing (GrowthBook), DataDog integration |
| **API** | `services/api/` | 21 | ~5,800 | Anthropic API client, 4-provider factory (Direct/Bedrock/Foundry/Vertex), retry logic (10 max, 529 fallback), streaming (raw events), prompt cache break detection, 10+ supporting API clients (bootstrap, filesApi, grove, referral, adminRequests, usage, ultrareviewQuota, overageCreditGrant, metricsOptOut, firstTokenDate, sessionIngress, dumpPrompts) |
| **AgentSummary** | `services/AgentSummary/` | 1 | ~180 | Periodic 30s forked-agent summarization for coordinator sub-agents (3-5 word present-tense labels) |
| **AutoDream** | `services/autoDream/` | 4 | ~554 | Background memory consolidation — 6-gate trigger (feature/env/time/throttle/session/lock), 4-phase consolidation prompt, file-based distributed lock with mtime timestamp |
| **Compact** | `services/compact/` | — | — | Context window compaction strategies |
| **ExtractMemories** | `services/extractMemories/` | — | — | Extracts learnings to CLAUDE.md |
| **LSP** | `services/lsp/` | 7 | ~2,467 | Language Server Protocol client management — 4-layer architecture (client/instance/manager/singleton), state machine (5 states), crash recovery (3 max restarts), diagnostic registry with LRU dedup (500 max), volume limiting (10/file, 30 total) |
| **LSPTool** | `tools/LSPTool/` | 6 | ~2,133 | LSP tool layer — 9 operations, Zod input schema, 8 result formatters, gitignore filtering, symbol context extraction |
| **MagicDocs** | `services/MagicDocs/` | — | — | AI-powered documentation generation |
| **MCP** | `services/mcp/` | — | — | MCP server connection management, OAuth, config parsing |
| **OAuth** | `services/oauth/` | — | — | OAuth 2.0 PKCE authentication flow |
| **Plugins** | `services/plugins/` | — | — | Plugin install/update lifecycle |
| **PolicyLimits** | `services/policyLimits/` | — | — | Enterprise policy limit enforcement |
| **PromptSuggestion** | `services/PromptSuggestion/` | 2 | ~1,516 | Predictive prompt suggestions (13-rule filter chain) + speculation engine (copy-on-write overlay filesystem, pipelined suggestions, 20-turn/100-message limits) |
| **RemoteManagedSettings** | `services/remoteManagedSettings/` | — | — | MDM/enterprise remote settings |
| **SessionMemory** | `services/SessionMemory/` | — | — | Session memory persistence |
| **SettingsSync** | `services/settingsSync/` | — | — | Settings synchronization |
| **TeamMemorySync** | `services/teamMemorySync/` | — | — | Team memory synchronization |
| **Tips** | `services/tips/` | 3 | ~764 | Contextual tip display — 40+ tips with relevance predicates, cooldown periods, LRU selection algorithm |
| **ToolUseSummary** | `services/toolUseSummary/` | 1 | ~113 | Tool batch summarization via Haiku model (~30 char git-commit-style labels for SDK/mobile) |

> **Note**: Services marked with "—" for Files/LOC have not yet been deep-analyzed. The 5 deep-analyzed services (API, LSP, AutoDream, PromptSuggestion+Tips+ToolUseSummary+AgentSummary) collectively account for 39 files and ~13,527 LOC.

### Background Intelligence Services (Wave 44)

These 5 services form the **background intelligence layer** that makes Claude Code feel proactive:

| Service | Execution Model | Trigger | Frequency | Cost Profile |
|---------|----------------|---------|-----------|-------------|
| **autoDream** | Background forked agent | Post-sampling hook | ~1/day (24h + 5 sessions) | High per-run, cheap per-turn |
| **PromptSuggestion** | Background forked agent | Post-sampling hook | Every turn | Low (cache hit) |
| **Speculation** | Background forked agent | After suggestion | Every suggestion | Medium-High (runs tools in overlay) |
| **tips** | Foreground sync | Spinner display | Every spinner | Negligible (local predicates) |
| **toolUseSummary** | Foreground Haiku call | SDK tool batch | Per batch | Low (Haiku, short) |
| **AgentSummary** | Background forked agent | 30s timer | Per sub-agent | Low (cache hit) |

---

## 6. Utils Infrastructure (Wave 46)

The `src/utils/` directory (564 files) contains major subsystems. Key inventories from deep analysis:

### Settings System (`utils/settings/` — 19 files, ~2,800 LOC)

The largest utility subsystem. A layered configuration pipeline merging 6+ sources with strict precedence:

| File | LOC | Purpose |
|------|-----|---------|
| `types.ts` | ~1,150 | Master Zod v4 schema — 60+ setting fields, backward-compatible |
| `settings.ts` | ~1,016 | Core merge engine, file loading, source resolution |
| `changeDetector.ts` | ~489 | Chokidar filesystem watcher, MDM polling (30min), deletion grace (1700ms) |
| `permissionValidation.ts` | ~263 | Permission rule parser (parentheses, MCP, Bash, file patterns) |
| `validation.ts` | ~266 | Zod error formatting, invalid rule filtering |
| `validationTips.ts` | ~164 | Context-aware validation tips with doc links |
| `constants.ts` | ~202 | Source definitions, `SETTING_SOURCES` array |
| `toolValidationConfig.ts` | ~103 | Tool-specific validation (file pattern, bash prefix, WebSearch/WebFetch) |
| `settingsCache.ts` | ~81 | Three-tier cache: session, per-source, per-file |
| Other 7 files | ~266 | applySettingsChange, pluginOnlyPolicy, managedPath, internalWrites, validateEditTool, allErrors, schemaOutput |
| **MDM subdirectory** (3 files) | ~530 | `mdm/settings.ts` (317), `mdm/rawRead.ts` (131), `mdm/constants.ts` (82) — macOS plist, Windows registry, Linux file-based |

**Settings Sources (lowest → highest priority)**:
`pluginSettings` → `userSettings` → `projectSettings` → `localSettings` → `flagSettings` → `policySettings`

**Policy sub-precedence (first wins)**: remote API → HKLM/macOS plist → managed-settings.json + drop-ins → HKCU

### Other Key Utility Subsystems (Not Yet Deep-Analyzed)

| Subsystem | Estimated Scope | Key Responsibility |
|-----------|----------------|-------------------|
| `utils/auth/` | Large | Authentication, OAuth, API key management |
| `utils/model/` | Large | Model selection, cost calculation, capability detection |
| `utils/permissions/` | Medium | Permission rule evaluation, tool permission checks |
| `utils/git/` | Medium | Git operations, worktree management |
| `utils/plugins/` | Medium | Plugin loading, marketplace, lifecycle |
| `utils/sandbox/` | Medium | Sandbox enforcement, security boundaries |

---

## 7. Key Constants

Notable large files and modules identified across deep analyses:

| File/Module | Size | Significance |
|-------------|------|-------------|
| `services/api/claude.ts` | ~125KB / ~3,000+ LOC | Core API orchestrator — largest single file in the codebase |
| `services/api/errors.ts` | ~42KB | 30+ error patterns → user-facing messages |
| `utils/settings/types.ts` | ~1,150 LOC | Master settings schema (60+ fields, Zod v4) |
| `services/PromptSuggestion/speculation.ts` | ~992 LOC | Speculative execution with COW overlay filesystem |
| `tools/LSPTool/LSPTool.ts` | ~861 LOC | 9 LSP operations + file sync + gitignore filtering |
| `services/tips/tipRegistry.ts` | ~687 LOC | 40+ contextual tips with async relevance predicates |
| `tools/LSPTool/formatters.ts` | ~593 LOC | 8 result formatters (SymbolKind enum: 26 kinds) |
| `services/lsp/LSPServerInstance.ts` | ~512 LOC | Server lifecycle state machine (5 states, crash recovery) |
| `services/PromptSuggestion/promptSuggestion.ts` | ~524 LOC | 13-rule suggestion filter chain |
| `services/lsp/LSPClient.ts` | ~448 LOC | JSON-RPC over stdio (closure-based, not class-based) |

---

## 8. Vendor Modules

Located in `vendor/`:

| Module | Description |
|--------|-------------|
| `audio-capture-src/` | Native audio capture (voice input) |
| `image-processor-src/` | Image processing for FileReadTool |
| `modifiers-napi-src/` | Native Node.js API modifiers |
| `url-handler-src/` | URL protocol handler registration |

---

## 9. Bundled Skills

Skills are reusable prompt templates executed via `SkillTool`. Located in `src/skills/bundled/`.

| Skill | Description |
|-------|-------------|
| batch | Batch processing helper |
| claudeApi | Claude API usage guidance |
| claudeInChrome | Chrome extension integration |
| debug | Debugging assistance |
| keybindings | Keybinding reference |
| loop | Iteration/loop patterns |
| loremIpsum | Placeholder text generation |
| remember | Memory/note-taking |
| scheduleRemoteAgents | Remote agent scheduling |
| simplify | Code simplification |
| skillify | Convert workflows to skills |
| stuck | Unstick/unblock prompts |
| updateConfig | Configuration update helper |
| verify | Code verification |

---

## Correction Log

### Wave 58 (2026-04-01) — Service + Utility Deep Inventory

**Service catalog expansion (Waves 41-44)**:
1. **API service**: 21 files, ~5,800 LOC — 4 providers, 10+ supporting API clients, raw stream events, prompt cache break detection
2. **LSP service**: 7 files (service) + 6 files (tool) = 13 files, ~4,600 LOC — 4-layer architecture, state machine, diagnostic registry
3. **Background services**: 11 files total — autoDream (4/554 LOC), PromptSuggestion (2/1,516 LOC), tips (3/764 LOC), toolUseSummary (1/113 LOC), AgentSummary (1/180 LOC)
4. Added **Background Intelligence Services** comparison table (execution model, trigger, frequency, cost)
5. Service catalog table expanded with Files and LOC columns for deep-analyzed services

**Utils infrastructure (Wave 46)**:
6. Added **Section 6: Utils Infrastructure** with settings system deep inventory (19 files, ~2,800 LOC)
7. Settings sources precedence chain documented (6-layer + policy sub-precedence)
8. Listed other key utility subsystems pending deep analysis

**Key constants (new section)**:
9. Added **Section 7: Key Constants** listing the 10 largest/most significant individual files
10. `claude.ts` confirmed as largest single file (~125KB), `types.ts` as largest schema (~1,150 LOC)

### Wave 17 (2026-04-01) — Applied Wave 2 + Wave 3 corrections

**Tool corrections (Wave 2)**:
1. Tool count: 52 → **57+** (40 directories + 16+ conditional/feature-gated)
2. BriefTool → **SendUserMessage** (category: Interaction, not Files)
3. SyntheticOutputTool → **StructuredOutput**
4. TaskCreateTool: "Creates background tasks" → **"Creates TodoV2 task items"**
5. TaskOutputTool: added **(deprecated)**, fixed to "Reads/retrieves task output"
6. ScheduleCronTool: confirmed split into **CronCreateTool, CronDeleteTool, CronListTool**
7. LSPTool: "diagnostics, symbols" → **9 operations** (definitions, references, hover, symbols, call hierarchy, implementation, type definitions, document symbols, workspace symbols)
8. Conditional tools section expanded from 9+ to **16+** with phantom directory note

**Command corrections (Wave 3)**:
1. Command count: 65+ → **88+ built-in**
2. `branch`: "Git branch operations" → **"Conversation branching (fork conversation history)"**
3. `bridge`: registered as **`remote-control`** (alias: `rc`)
4. `thinkback`: "Replay thinking traces" → **"Year in Review — session statistics retrospective"**
5. `upgrade`: "Upgrade Claude Code" → **"Subscription plan upsell"**
6. `stickers`: "Fun stickers feature" → **"Merchandise ordering"**
7. Added missing commands: **install-github-app, install-slack-app, doctor, extra-usage, feedback, heapdump, web-setup, ultrareview**
8. Marked **~12 stub commands** with "(stub in external builds)"
9. Added note about **23 internal-only commands** (`INTERNAL_ONLY_COMMANDS`)
10. Fixed registered names: `sandbox-toggle` → **`sandbox`**, `pr_comments` → **`pr-comments`**
11. Marked `output-style` as **(deprecated, hidden)**

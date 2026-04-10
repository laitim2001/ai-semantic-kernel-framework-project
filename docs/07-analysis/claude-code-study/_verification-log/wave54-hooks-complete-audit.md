# Wave 54: Complete Hooks Directory Audit

**Date**: 2026-04-01
**Scope**: `src/hooks/` — 104 files (87 root-level + 17 in subdirectories)
**Quality**: Deep read of 25+ hooks, structural scan of all 104

---

## 1. Complete Hook Inventory (104 Files)

### 1.1 Root-Level Hooks (85 files)

#### A. Command Queue & Processing (3 files)
| File | Purpose | Pattern |
|------|---------|---------|
| `useCommandQueue.ts` | Subscribe to unified command queue via `useSyncExternalStore` | External store subscription |
| `useQueueProcessor.ts` | Process queued commands when idle (no active query, no JSX UI) | Effect + external store |
| `useMergedCommands.ts` | Merge built-in commands with plugin commands | Memoized merge |

#### B. Tool Permission & Security (2 files + subdirectory)
| File | Purpose | Pattern |
|------|---------|---------|
| `useCanUseTool.tsx` | **Core permission gate** — decides allow/deny/ask for every tool use | Promise-based with React state callbacks |
| `useMergedTools.ts` | Assemble full tool pool: built-in + MCP, apply deny rules + dedup | useMemo composition |

#### C. IDE & Editor Integration (7 files)
| File | Purpose | Pattern |
|------|---------|---------|
| `useIDEIntegration.tsx` | Auto-connect to IDE (VS Code, etc.) via SSE/WS MCP config | useEffect + env detection |
| `useIdeConnectionStatus.ts` | Track IDE connection state | State subscription |
| `useIdeAtMentioned.ts` | Handle IDE @ mentions | Event listener |
| `useIdeSelection.ts` | Track IDE text selection | State sync |
| `useIdeLogging.ts` | IDE-specific logging | Effect |
| `useDiffInIDE.ts` | Open diffs in IDE | Callback |
| `useDiffData.ts` | Compute diff data for display | Memoized computation |

#### D. Input Handling & Text (10 files)
| File | Purpose | Pattern |
|------|---------|---------|
| `useTextInput.ts` | **Core text input engine** — keymap, cursor, kill-ring, submit | Complex state machine |
| `usePasteHandler.ts` | Detect paste (bracketed paste mode), handle image paste, chunk assembly | Debounced effect + state |
| `useArrowKeyHistory.tsx` | Arrow key history navigation with lazy chunk loading | Async state + refs |
| `useHistorySearch.ts` | Ctrl+R history search | State machine |
| `useInputBuffer.ts` | Buffer input during processing | Ref-based buffer |
| `useSearchInput.ts` | Search input handling | State |
| `useVimInput.ts` | Vim-mode key bindings | Key mapper |
| `useCopyOnSelect.ts` | Copy-on-select behavior | Effect |
| `useDoublePress.ts` | Double-press detection (800ms timeout) | Ref timer pattern |
| `useTypeahead.tsx` | Typeahead/autocomplete UI | State + suggestions |

#### E. Prompt Suggestions & File Suggestions (4 files)
| File | Purpose | Pattern |
|------|---------|---------|
| `usePromptSuggestion.ts` | Prompt suggestion display, accept (Tab), telemetry logging | AppState + analytics |
| `fileSuggestions.ts` | **Non-hook module** — file index (git ls-files / ripgrep), fuzzy search, FileIndex singleton | Singleton + async |
| `unifiedSuggestions.ts` | Unified suggestion pipeline (files + commands) | Aggregator |
| `renderPlaceholder.ts` | Render placeholder text in input | Pure function |

#### F. Session & Background Tasks (6 files)
| File | Purpose | Pattern |
|------|---------|---------|
| `useSessionBackgrounding.ts` | Ctrl+B to background/foreground sessions, sync task messages | AppState + callbacks |
| `useBackgroundTaskNavigation.ts` | Navigate between background tasks | State navigation |
| `useScheduledTasks.ts` | Scheduled task management | Timer + state |
| `useTaskListWatcher.ts` | Watch task list for changes | File watcher |
| `useTasksV2.ts` | Task state management v2 | AppState slice |
| `useRemoteSession.ts` | Remote session management | Connection state |

#### G. Swarm / Agent Team (3 files)
| File | Purpose | Pattern |
|------|---------|---------|
| `useSwarmInitialization.ts` | Initialize swarm: teammate hooks, context (fresh + resumed) | useEffect with conditional init |
| `useSwarmPermissionPoller.ts` | Poll for leader permission responses (500ms interval), callback registry | useInterval + module-level Map registry |
| `useTeammateViewAutoExit.ts` | Auto-exit teammate view | Effect |

#### H. Model & API (4 files)
| File | Purpose | Pattern |
|------|---------|---------|
| `useMainLoopModel.ts` | Resolve current model name (session > global > default), re-render on GrowthBook refresh | AppState + forceRerender |
| `useApiKeyVerification.ts` | Verify API key (loading/valid/invalid/missing/error states) | Async state machine |
| `useDirectConnect.ts` | Direct API connection mode | State |
| `useMergedClients.ts` | Merge API clients | Memoized merge |

#### I. Voice Input (3 files)
| File | Purpose | Pattern |
|------|---------|---------|
| `useVoice.ts` | Hold-to-talk voice input via Anthropic voice_stream STT (Deepgram backend) | Complex state: recording, WebSocket, language detection |
| `useVoiceEnabled.ts` | Check if voice feature is enabled | Feature flag |
| `useVoiceIntegration.tsx` | Wire voice into REPL UI | Integration hook |

#### J. Terminal & Display (6 files)
| File | Purpose | Pattern |
|------|---------|---------|
| `useTerminalSize.ts` | Get terminal dimensions from TerminalSizeContext | useContext (throws if missing) |
| `useVirtualScroll.ts` | **Virtual scrolling engine** — overscan, scroll quantization, slide-step mounting | useSyncExternalStore + layout measurement |
| `useBlink.ts` | Cursor blink animation | Timer |
| `useElapsedTime.ts` | Elapsed time display | Timer |
| `useMinDisplayTime.ts` | Minimum display time for UI elements | Timer |
| `useTurnDiffs.ts` | Compute turn-level diffs | Memoized |

#### K. Settings & Configuration (5 files)
| File | Purpose | Pattern |
|------|---------|---------|
| `useSettings.ts` | Read settings | State |
| `useSettingsChange.ts` | React to settings file changes | File watcher |
| `useSkillsChange.ts` | React to skills configuration changes | File watcher |
| `useDynamicConfig.ts` | GrowthBook dynamic config values | Async state |
| `useManagePlugins.ts` | Plugin management | State |

#### L. Keybindings & Navigation (4 files)
| File | Purpose | Pattern |
|------|---------|---------|
| `useCommandKeybindings.tsx` | Command keybinding registration | Effect |
| `useGlobalKeybindings.tsx` | Global keybinding handler | Effect |
| `useExitOnCtrlCD.ts` | Ctrl+C/D exit handling | Double-press |
| `useExitOnCtrlCDWithKeybindings.ts` | Exit with configurable keybindings | Keybinding integration |

#### M. Bridge & Communication (4 files)
| File | Purpose | Pattern |
|------|---------|---------|
| `useReplBridge.tsx` | REPL bridge connection (OAuth, WebSocket, permission forwarding) | Complex lifecycle |
| `useMailboxBridge.ts` | Mailbox message polling — submit messages when idle | useSyncExternalStore + effect |
| `useInboxPoller.ts` | Poll inbox for incoming messages | Interval |
| `useSSHSession.ts` | SSH session management | Connection state |

#### N. Notifications & Status (7 files in root)
| File | Purpose | Pattern |
|------|---------|---------|
| `useLogMessages.ts` | Log message display | State |
| `useNotifyAfterTimeout.ts` | Notify after timeout | Timer |
| `usePrStatus.ts` | PR status tracking | Polling |
| `useCancelRequest.ts` | Cancel ongoing request | AbortController |
| `useIssueFlagBanner.ts` | Issue flag banner display | State |
| `useUpdateNotification.ts` | Update available notification | Version check |
| `useDeferredHookMessages.ts` | Deferred hook message handling | Queue |

#### O. Analytics & Memory (2 files)
| File | Purpose | Pattern |
|------|---------|---------|
| `useMemoryUsage.ts` | Memory usage monitoring | Polling |
| `useSkillImprovementSurvey.ts` | Skill improvement survey | State |

#### P. Miscellaneous (8 files)
| File | Purpose | Pattern |
|------|---------|---------|
| `useAfterFirstRender.ts` | Execute callback after first render | Ref flag |
| `useTimeout.ts` | Generic timeout hook | Timer |
| `useAssistantHistory.ts` | Assistant conversation history | State |
| `useAwaySummary.ts` | Away summary generation | Async |
| `useTeleportResume.tsx` | Teleport resume handling | State |
| `useClipboardImageHint.ts` | Clipboard image hint | State |
| `useFileHistorySnapshotInit.ts` | File history snapshot initialization | Effect |
| `useChromeExtensionNotification.tsx` | Chrome extension notification | Feature flag |
| `useClaudeCodeHintRecommendation.tsx` | Claude Code hint recommendations | Feature flag |
| `useLspPluginRecommendation.tsx` | LSP plugin recommendation | Feature flag |
| `useOfficialMarketplaceNotification.tsx` | Official marketplace notification | Feature flag |
| `usePluginRecommendationBase.tsx` | Base plugin recommendation logic | Shared base |
| `usePromptsFromClaudeInChrome.tsx` | Chrome extension prompt integration | Bridge |

### 1.2 Notification Hooks Subdirectory (`notifs/`, 17 files)

| File | Purpose | Trigger |
|------|---------|---------|
| `useStartupNotification.ts` | **Base hook** — fire notification(s) once on mount with remote-mode gate | Mount |
| `useAutoModeUnavailableNotification.ts` | Auto-mode unavailable warning | Feature gate |
| `useCanSwitchToExistingSubscription.tsx` | Subscription switch prompt | Auth check |
| `useDeprecationWarningNotification.tsx` | Deprecation warnings | Version check |
| `useFastModeNotification.tsx` | Fast mode activation notice | Mode change |
| `useIDEStatusIndicator.tsx` | IDE connection status indicator | Connection state |
| `useInstallMessages.tsx` | Install/setup messages | First run |
| `useLspInitializationNotification.tsx` | LSP initialization progress | Async init |
| `useMcpConnectivityStatus.tsx` | MCP server connectivity status | Connection polling |
| `useModelMigrationNotifications.tsx` | Model migration notices | Config change |
| `useNpmDeprecationNotification.tsx` | npm deprecation warning | Version check |
| `usePluginAutoupdateNotification.tsx` | Plugin auto-update notice | Update check |
| `usePluginInstallationStatus.tsx` | Plugin installation progress | Async install |
| `useRateLimitWarningNotification.tsx` | Rate limit / overage warnings | API limits |
| `useSettingsErrors.tsx` | Settings validation errors | Settings change |
| `useTeammateShutdownNotification.ts` | Teammate agent shutdown notice | Swarm event |

### 1.3 Tool Permission Subdirectory (`toolPermission/`, 5 files)

| File | Purpose | Role |
|------|---------|------|
| `PermissionContext.ts` | **Core context factory** — `createPermissionContext()` with resolve-once guard, hook runner, classifier, queue ops | Factory + types |
| `permissionLogging.ts` | Centralized analytics/OTel logging for all permission decisions | Telemetry fan-out |
| `handlers/coordinatorHandler.ts` | Coordinator worker flow: hooks then classifier, fall through to dialog | Sequential async |
| `handlers/interactiveHandler.ts` | Interactive (main agent) flow: push to confirm queue, race hooks/classifier vs user | Callback + race |
| `handlers/swarmWorkerHandler.ts` | Swarm worker flow: classifier then forward to leader via mailbox | Async + IPC |

---

## 2. Deep Analysis of Top 15 Hooks

### 2.1 useCanUseTool (useCanUseTool.tsx) — ~700 lines

**Purpose**: The central permission gate for every tool invocation in the system.

**Signature**:
```typescript
function useCanUseTool(
  setToolUseConfirmQueue: Dispatch<SetStateAction<ToolUseConfirm[]>>,
  setToolPermissionContext: (context: ToolPermissionContext) => void,
): CanUseToolFn
```

**Return Type**: `CanUseToolFn<Input>` — async function returning `PermissionDecision<Input>`

**Key Behavior**:
1. Creates a `PermissionContext` via `createPermissionContext()` for each tool use
2. Checks abort signal first (resolves immediately if aborted)
3. If `forceDecision` provided, uses it directly; otherwise calls `hasPermissionsToUseTool()`
4. **Allow path**: logs decision, resolves with `buildAllow()`
5. **Deny path**: logs rejection, records auto-mode denial if classifier-based, shows notification
6. **Ask path**: Routes to one of three handlers based on context:
   - `handleCoordinatorPermission()` — coordinator workers (hooks then classifier)
   - `handleSwarmWorkerPermission()` — swarm workers (classifier then leader mailbox)
   - `handleInteractivePermission()` — main agent (dialog with race against hooks/classifier)
7. Uses speculative classifier checks for bash commands (`BASH_CLASSIFIER` feature flag)
8. Compiled with React Compiler (`_c` memoization cache)

**Architectural Significance**: This is the security boundary — every tool use in Claude Code flows through this hook.

### 2.2 useCommandQueue (useCommandQueue.ts) — 15 lines

**Purpose**: Subscribe to the unified command queue.

**Signature**: `function useCommandQueue(): readonly QueuedCommand[]`

**Key Behavior**: Thin wrapper around `useSyncExternalStore` subscribing to `messageQueueManager`. Returns frozen array that changes reference only on mutation.

### 2.3 useQueueProcessor (useQueueProcessor.ts) — 68 lines

**Purpose**: Process queued commands when conditions are met.

**Params**: `{ executeQueuedInput, hasActiveLocalJsxUI, queryGuard }`

**Key Behavior**:
- Subscribes to both `queryGuard` and command queue via `useSyncExternalStore`
- Processes when: no active query AND no active JSX UI AND queue non-empty
- Priority ordering: `'now'` > `'next'` (user input) > `'later'` (task notifications)
- Reservation is owned by `handlePromptSubmit` to prevent race conditions

### 2.4 useIDEIntegration (useIDEIntegration.tsx) — 70 lines

**Purpose**: Auto-connect to IDE (VS Code, JetBrains, etc.) via dynamic MCP config.

**Params**: `{ autoConnectIdeFlag, ideToInstallExtension, setDynamicMcpConfig, setShowIdeOnboarding, setIDEInstallationState }`

**Key Behavior**:
- Detects IDE via `initializeIdeIntegration()` utility
- Auto-connect enabled when: global config flag OR supported terminal OR `CLAUDE_CODE_SSE_PORT` env var
- Sets MCP config type to `'ws-ide'` or `'sse-ide'` based on URL scheme
- Compiled with React Compiler

### 2.5 useTerminalSize (useTerminalSize.ts) — 15 lines

**Purpose**: Get terminal dimensions from React context.

**Return**: `TerminalSize` (rows, columns)

**Key Behavior**: Simple `useContext(TerminalSizeContext)` with a throw guard if used outside Ink App.

### 2.6 useSwarmInitialization (useSwarmInitialization.ts) — 81 lines

**Purpose**: Initialize swarm features for teammate sessions.

**Params**: `(setAppState, initialMessages, { enabled })`

**Key Behavior**:
- Guards on `isAgentSwarmsEnabled()` feature flag
- **Resumed sessions**: Reads `teamName`/`agentName` from first transcript message, calls `initializeTeammateContextFromSession()`, reads team file for `agentId`
- **Fresh spawns**: Reads `getDynamicTeamContext()` for environment-provided context
- Both paths end with `initializeTeammateHooks()` to set up teammate polling/communication

### 2.7 useSessionBackgrounding (useSessionBackgrounding.ts) — 158 lines

**Purpose**: Ctrl+B to background/foreground sessions.

**Params**: `{ setMessages, setIsLoading, resetLoadingState, setAbortController, onBackgroundQuery }`

**Return**: `{ handleBackgroundSession: () => void }`

**Key Behavior**:
- If foregrounded task exists: re-backgrounds it, clears messages, resets loading
- If no foregrounded task: calls `onBackgroundQuery()` to spawn background task
- Syncs foregrounded task messages to main view (only updates when length changes)
- Handles aborted tasks: clears foregrounded state immediately
- Handles completed tasks: restores to background automatically

### 2.8 usePasteHandler (usePasteHandler.ts) — 285 lines

**Purpose**: Detect and handle paste events including images.

**Params**: `{ onPaste, onInput, onImagePaste }`

**Return**: `{ wrappedOnInput, pasteState, isPasting }`

**Key Behavior**:
- Detects paste via `event.keypress.isPasted` (bracketed paste mode)
- Chunks large pastes with 100ms completion timeout
- Image detection: checks file paths for image extensions, handles drag-and-drop of multiple images
- macOS clipboard image: empty paste triggers `getImageFromClipboard()`
- Uses `pastePendingRef` for synchronous paste state (avoids React batch staleness)
- Handles both Unix and Windows path formats

### 2.9 useDoublePress (useDoublePress.ts) — 62 lines

**Purpose**: Detect double-press of a key within 800ms timeout.

**Params**: `(setPending, onDoublePress, onFirstPress?)`

**Return**: `() => void` — the press handler

**Key Behavior**: Used for Ctrl+C double-press to exit. Tracks `lastPressRef` timestamp, clears pending state on timeout.

### 2.10 usePromptSuggestion (usePromptSuggestion.ts) — 177 lines

**Purpose**: Manage prompt suggestion display, acceptance, and telemetry.

**Params**: `{ inputValue, isAssistantResponding }`

**Return**: `{ suggestion, markAccepted, markShown, logOutcomeAtSubmission }`

**Key Behavior**:
- Shows suggestion only when: not responding AND input empty
- Tracks engagement: `firstKeystrokeAt`, `wasFocusedWhenShown`, acceptance method (Tab vs Enter)
- `logOutcomeAtSubmission()`: logs `tengu_prompt_suggestion` analytics event with timing, similarity, outcome
- Calls `abortSpeculation()` on reset to cancel speculative generation

### 2.11 useApiKeyVerification (useApiKeyVerification.ts) — 84 lines

**Purpose**: Verify API key validity with status state machine.

**Return**: `{ status: VerificationStatus, reverify, error }`

**States**: `'loading' | 'valid' | 'invalid' | 'missing' | 'error'`

**Key Behavior**:
- Initial state: skips `apiKeyHelper` execution before trust dialog (RCE prevention)
- `verify()`: warms apiKeyHelper cache, then checks key via `verifyApiKey()`
- Handles Claude AI subscriber pass-through (always valid)

### 2.12 useMainLoopModel (useMainLoopModel.ts) — 34 lines

**Purpose**: Resolve current model name for API calls.

**Return**: `ModelName`

**Key Behavior**:
- Priority: `mainLoopModelForSession` > `mainLoopModel` > default
- Subscribes to GrowthBook refresh signal to re-resolve aliases after init
- Uses `parseUserSpecifiedModel()` for alias resolution

### 2.13 useArrowKeyHistory (useArrowKeyHistory.tsx) — ~400 lines

**Purpose**: Navigate command history with arrow keys.

**Params**: `(onSetInput, currentInput, pastedContents, setCursorOffset?, currentMode?)`

**Return**: `{ historyIndex, setHistoryIndex, onHistoryUp, onHistoryDown, resetHistory, dismissSearchHint }`

**Key Behavior**:
- Lazy chunk loading: loads history in chunks of 10 to reduce disk reads
- Batches concurrent load requests into a single disk read (module-level `pendingLoad`)
- Mode filtering: can filter history by input mode (e.g., slash commands only)
- Shows Ctrl+R search hint after first history navigation

### 2.14 useSwarmPermissionPoller (useSwarmPermissionPoller.ts) — 330 lines

**Purpose**: Poll for permission responses when running as swarm worker.

**Module-level exports** (not just hook):
- `registerPermissionCallback()` / `unregisterPermissionCallback()`
- `processMailboxPermissionResponse()` — process from inbox
- `processSandboxPermissionResponse()` — process sandbox permission
- `clearAllPendingCallbacks()` — cleanup on `/clear`

**Key Behavior**:
- Polls every 500ms when `isSwarmWorker()` is true
- Module-level `Map<string, PermissionResponseCallback>` registry persists across renders
- Validates permission updates with Zod schema before invoking callbacks
- Dual registry: permission callbacks + sandbox permission callbacks

### 2.15 useVoice (useVoice.ts) — ~400 lines

**Purpose**: Hold-to-talk voice input using Anthropic voice_stream STT.

**Key Behavior**:
- Records audio via native module (macOS) or SoX
- Streams to Anthropic's `voice_stream` endpoint (Deepgram backend)
- Auto-repeat key detection with `RELEASE_TIMEOUT_MS`
- Language normalization: maps language names to BCP-47 codes
- Supported languages: en, es, fr, ja, de, pt, it, ko (subset of server-side allowlist)

---

## 3. Hook Registration Pattern

### 3.1 Where Hooks Are Consumed

The hooks are primarily consumed in the main REPL component tree:

```
App.tsx (Ink root)
  └── REPL.tsx (main REPL component)
       ├── useCanUseTool         → permission gate
       ├── useCommandQueue       → command queue subscription
       ├── useQueueProcessor     → command processing
       ├── useTextInput          → input handling
       ├── usePasteHandler       → paste detection
       ├── useArrowKeyHistory    → history navigation
       ├── usePromptSuggestion   → prompt suggestions
       ├── useSessionBackgrounding → Ctrl+B backgrounding
       ├── useSwarmInitialization → swarm setup
       ├── useSwarmPermissionPoller → worker permission polling
       ├── useIDEIntegration     → IDE auto-connect
       ├── useMainLoopModel      → model resolution
       ├── useMergedTools        → tool pool assembly
       ├── useReplBridge         → bridge connection
       ├── useMailboxBridge      → mailbox polling
       ├── useVoice              → voice input
       ├── useVirtualScroll      → message list virtualization
       └── notifs/*              → all notification hooks
```

### 3.2 Hook Composition Patterns

1. **External Store Pattern** (`useSyncExternalStore`): Used by `useCommandQueue`, `useQueueProcessor`, `useMailboxBridge`, `useVirtualScroll` for module-level stores that bypass React context propagation delays in Ink.

2. **AppState Pattern** (`useAppState` / `useSetAppState`): Used by `usePromptSuggestion`, `useSessionBackgrounding`, `useSwarmInitialization`, `useMainLoopModel` for centralized state.

3. **React Compiler Pattern** (`_c` cache): Used by `useCanUseTool`, `useIDEIntegration`, `useRateLimitWarningNotification`, `useSettingsErrors` — compiled output with manual memoization slots.

4. **Startup Notification Pattern** (`useStartupNotification`): Base hook used by 16 notification hooks — encapsulates remote-mode gate + once-per-session guard.

5. **Module-level Registry Pattern**: Used by `useSwarmPermissionPoller` (pending callbacks Map) and `fileSuggestions.ts` (FileIndex singleton) for state that must persist across renders.

---

## 4. Lifecycle Integration

### 4.1 Session Lifecycle

```
Session Start:
  useApiKeyVerification → verify key
  useSwarmInitialization → init swarm context
  useIDEIntegration → auto-connect IDE
  notifs/useStartupNotification → all startup notifications
  fileSuggestions → start background file index

Session Active:
  useQueueProcessor → process commands
  useCanUseTool → gate every tool use
  useSessionBackgrounding → background/foreground tasks
  useSwarmPermissionPoller → poll leader (if worker)
  useMainLoopModel → track model changes
  useVirtualScroll → virtualize message list

Session End:
  clearAllPendingCallbacks() → clean swarm state
  clearFileSuggestionCaches() → clean file index
```

### 4.2 Feature Flag Dependencies

| Feature Flag | Hooks Affected |
|-------------|----------------|
| `BASH_CLASSIFIER` | useCanUseTool, coordinatorHandler, interactiveHandler, swarmWorkerHandler |
| `TRANSCRIPT_CLASSIFIER` | useCanUseTool, permissionLogging |
| `ENABLE_AGENT_SWARMS` | useSwarmInitialization, useSwarmPermissionPoller, swarmWorkerHandler |

---

## 5. Architectural Observations

### 5.1 Strengths

1. **Clean separation of concerns**: Each hook has a single, well-defined responsibility
2. **External store pattern**: `useSyncExternalStore` for module-level stores avoids Ink context propagation delays
3. **Permission system layering**: Clean three-handler architecture (coordinator/interactive/swarm) behind unified `useCanUseTool`
4. **Startup notification abstraction**: `useStartupNotification` eliminates boilerplate across 16 notification hooks
5. **React Compiler adoption**: Several performance-critical hooks are compiled

### 5.2 Complexity Hotspots

1. **useCanUseTool.tsx** (~700 lines): Most complex hook — handles all permission decision paths with multiple feature flag branches
2. **usePasteHandler.ts** (285 lines): Complex paste detection with image handling, platform-specific behavior, and race condition prevention
3. **fileSuggestions.ts** (812 lines): Not a hook but lives in hooks/ — a complex file indexing module with git ls-files, ripgrep fallback, signature-based rebuild optimization
4. **useReplBridge.tsx**: OAuth + WebSocket lifecycle management with retry logic and failure caps
5. **useVoice.ts**: Audio recording + WebSocket STT streaming with language detection

### 5.3 Design Patterns Summary

| Pattern | Count | Examples |
|---------|-------|---------|
| `useSyncExternalStore` | 5+ | useCommandQueue, useQueueProcessor, useMailboxBridge, useVirtualScroll |
| `useAppState` selector | 10+ | usePromptSuggestion, useSessionBackgrounding, useMainLoopModel |
| React Compiler (`_c`) | 4+ | useCanUseTool, useIDEIntegration, useRateLimitWarning, useSettingsErrors |
| `useStartupNotification` base | 16 | All notifs/ hooks |
| Module-level singleton | 3 | fileSuggestions (FileIndex), useSwarmPermissionPoller (Map), useArrowKeyHistory (pendingLoad) |
| Timer/interval | 6+ | useDoublePress, useElapsedTime, useSwarmPermissionPoller, useBlink |
| File watcher | 3 | useSettingsChange, useSkillsChange, useTaskListWatcher |

---

## 6. Statistics

| Metric | Value |
|--------|-------|
| Total files | 104 |
| Root-level hooks | 85 |
| Notification hooks (notifs/) | 17 |
| Tool permission files (toolPermission/) | 5 |
| Non-hook modules in hooks/ | 3 (fileSuggestions, renderPlaceholder, unifiedSuggestions) |
| React Compiler compiled | 4+ hooks |
| Lines of code (estimated) | ~8,000-10,000 |
| External dependencies | usehooks-ts (useInterval, useDebounceCallback), strip-ansi, ignore |

---

*Wave 54 complete. This audit covers all 104 files in `src/hooks/` with deep analysis of the 15 most architecturally significant hooks.*

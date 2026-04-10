# Wave 5 Type Signature Verification — Batch 3: AppState, Messages, Log Entry Types

> Source-verified type extraction from Claude Code. Batch covers AppState shape, Store pattern, Entry union, SerializedMessage, text input types, and bootstrap global state.
> Verification date: 2026-04-01

## Verification Scope

| File | Types Extracted |
|------|----------------|
| `src/state/AppStateStore.ts` | `AppState`, `CompletionBoundary`, `SpeculationResult`, `SpeculationState`, `FooterItem`, `AppStateStore` |
| `src/state/store.ts` | `Store<T>`, `Listener`, `OnChange<T>` |
| `src/types/logs.ts` | `Entry` (19-variant union), `SerializedMessage`, `LogOption`, `TranscriptMessage`, + 17 individual entry types |
| `src/types/textInputTypes.ts` | `VimMode`, `QueuedCommand`, `QueuePriority`, `BaseTextInputProps`, `PromptInputMode`, `OrphanedPermission`, `InlineGhostText`, `BaseInputState` |
| `src/bootstrap/state.ts` | `State` (bootstrap), `ChannelEntry`, `AttributedCounter`, `SessionCronTask` |

---

## 1. Store Pattern (`src/state/store.ts`)

### `Store<T>`

```typescript
type Listener = () => void
type OnChange<T> = (args: { newState: T; oldState: T }) => void

type Store<T> = {
  getState: () => T
  setState: (updater: (prev: T) => T) => void
  subscribe: (listener: Listener) => () => void
}
```

**Implementation**: `createStore<T>(initialState, onChange?)` — minimal pub/sub with `Object.is` equality check to skip no-op updates. Listeners stored in a `Set<Listener>`.

### Existing Analysis Accuracy (state-management.md)

| Claim | Verdict | Detail |
|-------|---------|--------|
| "Store has getState, setState, subscribe" | **CORRECT** | Exact match |
| "setState uses updater function pattern" | **CORRECT** | `(prev: T) => T` confirmed |
| "Object.is equality check" | **CORRECT** | Line 23: `if (Object.is(next, prev)) return` |
| "`AppStateStore` = `Store<AppState>`" | **CORRECT** | Line 454: `type AppStateStore = Store<AppState>` |

---

## 2. AppState (`src/state/AppStateStore.ts`)

### Structure

`AppState` is a hybrid type: `DeepImmutable<{...}> & {...mutable sections}`. The `DeepImmutable` wrapper covers ~50 scalar/config fields; the mutable `&` section contains fields with function types, Maps, Sets, and complex nested objects that `DeepImmutable` cannot handle.

### Complete Field Inventory (105 fields)

#### DeepImmutable Section (lines 89-157, 37 fields)

| Field | Type | Default |
|-------|------|---------|
| `settings` | `SettingsJson` | `getInitialSettings()` |
| `verbose` | `boolean` | `false` |
| `mainLoopModel` | `ModelSetting` | `null` |
| `mainLoopModelForSession` | `ModelSetting` | `null` |
| `statusLineText` | `string \| undefined` | `undefined` |
| `expandedView` | `'none' \| 'tasks' \| 'teammates'` | `'none'` |
| `isBriefOnly` | `boolean` | `false` |
| `showTeammateMessagePreview?` | `boolean` | `false` |
| `selectedIPAgentIndex` | `number` | `-1` |
| `coordinatorTaskIndex` | `number` | `-1` |
| `viewSelectionMode` | `'none' \| 'selecting-agent' \| 'viewing-agent'` | `'none'` |
| `footerSelection` | `FooterItem \| null` | `null` |
| `toolPermissionContext` | `ToolPermissionContext` | `getEmptyToolPermissionContext() + mode` |
| `spinnerTip?` | `string` | (not in default) |
| `agent` | `string \| undefined` | `undefined` |
| `kairosEnabled` | `boolean` | `false` |
| `remoteSessionUrl` | `string \| undefined` | `undefined` |
| `remoteConnectionStatus` | `'connecting' \| 'connected' \| 'reconnecting' \| 'disconnected'` | `'connecting'` |
| `remoteBackgroundTaskCount` | `number` | `0` |
| `replBridgeEnabled` | `boolean` | `false` |
| `replBridgeExplicit` | `boolean` | `false` |
| `replBridgeOutboundOnly` | `boolean` | `false` |
| `replBridgeConnected` | `boolean` | `false` |
| `replBridgeSessionActive` | `boolean` | `false` |
| `replBridgeReconnecting` | `boolean` | `false` |
| `replBridgeConnectUrl` | `string \| undefined` | `undefined` |
| `replBridgeSessionUrl` | `string \| undefined` | `undefined` |
| `replBridgeEnvironmentId` | `string \| undefined` | `undefined` |
| `replBridgeSessionId` | `string \| undefined` | `undefined` |
| `replBridgeError` | `string \| undefined` | `undefined` |
| `replBridgeInitialName` | `string \| undefined` | `undefined` |
| `showRemoteCallout` | `boolean` | `false` |

#### Mutable Section (lines 158-452, 68 fields)

| Field | Type | Default |
|-------|------|---------|
| `tasks` | `{ [taskId: string]: TaskState }` | `{}` |
| `agentNameRegistry` | `Map<string, AgentId>` | `new Map()` |
| `foregroundedTaskId?` | `string` | (not in default) |
| `viewingAgentTaskId?` | `string` | (not in default) |
| `companionReaction?` | `string` | (not in default) |
| `companionPetAt?` | `number` | (not in default) |
| `mcp` | `{ clients, tools, commands, resources, pluginReconnectKey }` | all empty + `0` |
| `plugins` | `{ enabled, disabled, commands, errors, installationStatus, needsRefresh }` | all empty + `false` |
| `agentDefinitions` | `AgentDefinitionsResult` | `{ activeAgents: [], allAgents: [] }` |
| `fileHistory` | `FileHistoryState` | `{ snapshots: [], trackedFiles: new Set(), snapshotSequence: 0 }` |
| `attribution` | `AttributionState` | `createEmptyAttributionState()` |
| `todos` | `{ [agentId: string]: TodoList }` | `{}` |
| `remoteAgentTaskSuggestions` | `{ summary: string; task: string }[]` | `[]` |
| `notifications` | `{ current: Notification \| null, queue: Notification[] }` | `{ current: null, queue: [] }` |
| `elicitation` | `{ queue: ElicitationRequestEvent[] }` | `{ queue: [] }` |
| `thinkingEnabled` | `boolean \| undefined` | `shouldEnableThinkingByDefault()` |
| `promptSuggestionEnabled` | `boolean` | `shouldEnablePromptSuggestion()` |
| `sessionHooks` | `SessionHooksState` | `new Map()` |
| `tungstenActiveSession?` | `{ sessionName, socketName, target }` | (not in default) |
| `tungstenLastCapturedTime?` | `number` | (not in default) |
| `tungstenLastCommand?` | `{ command, timestamp }` | (not in default) |
| `tungstenPanelVisible?` | `boolean` | (not in default) |
| `tungstenPanelAutoHidden?` | `boolean` | (not in default) |
| `bagelActive?` | `boolean` | (not in default) |
| `bagelUrl?` | `string` | (not in default) |
| `bagelPanelVisible?` | `boolean` | (not in default) |
| `computerUseMcpState?` | complex (see below) | (not in default) |
| `replContext?` | `{ vmContext, registeredTools, console }` | (not in default) |
| `teamContext?` | `{ teamName, teamFilePath, leadAgentId, selfAgentId?, ... teammates }` | (not in default) |
| `standaloneAgentContext?` | `{ name, color? }` | (not in default) |
| `inbox` | `{ messages: Array<{id, from, text, timestamp, status, color?, summary?}> }` | `{ messages: [] }` |
| `workerSandboxPermissions` | `{ queue: Array<{requestId, workerId, workerName, ...}>, selectedIndex }` | `{ queue: [], selectedIndex: 0 }` |
| `pendingWorkerRequest` | `{ toolName, toolUseId, description } \| null` | `null` |
| `pendingSandboxRequest` | `{ requestId, host } \| null` | `null` |
| `promptSuggestion` | `{ text, promptId, shownAt, acceptedAt, generationRequestId }` | all null/0 |
| `speculation` | `SpeculationState` | `{ status: 'idle' }` |
| `speculationSessionTimeSavedMs` | `number` | `0` |
| `skillImprovement` | `{ suggestion: {...} \| null }` | `{ suggestion: null }` |
| `authVersion` | `number` | `0` |
| `initialMessage` | `{ message: UserMessage, clearContext?, mode?, allowedPrompts? } \| null` | `null` |
| `pendingPlanVerification?` | `{ plan, verificationStarted, verificationCompleted }` | (not in default) |
| `denialTracking?` | `DenialTrackingState` | (not in default) |
| `activeOverlays` | `ReadonlySet<string>` | `new Set<string>()` |
| `fastMode?` | `boolean` | `false` |
| `advisorModel?` | `string` | (not in default) |
| `effortValue?` | `EffortValue` | `undefined` |
| `ultraplanLaunching?` | `boolean` | (not in default) |
| `ultraplanSessionUrl?` | `string` | (not in default) |
| `ultraplanPendingChoice?` | `{ plan, sessionId, taskId }` | (not in default) |
| `ultraplanLaunchPending?` | `{ blurb: string }` | (not in default) |
| `isUltraplanMode?` | `boolean` | (not in default) |
| `replBridgePermissionCallbacks?` | `BridgePermissionCallbacks` | (not in default) |
| `channelPermissionCallbacks?` | `ChannelPermissionCallbacks` | (not in default) |

### Helper Types

```typescript
type CompletionBoundary =
  | { type: 'complete'; completedAt: number; outputTokens: number }
  | { type: 'bash'; command: string; completedAt: number }
  | { type: 'edit'; toolName: string; filePath: string; completedAt: number }
  | { type: 'denied_tool'; toolName: string; detail: string; completedAt: number }

type SpeculationState =
  | { status: 'idle' }
  | { status: 'active'; id: string; abort: () => void; startTime: number;
      messagesRef: { current: Message[] }; writtenPathsRef: { current: Set<string> };
      boundary: CompletionBoundary | null; suggestionLength: number;
      toolUseCount: number; isPipelined: boolean;
      contextRef: { current: REPLHookContext };
      pipelinedSuggestion?: { text: string; promptId: 'user_intent' | 'stated_intent'; generationRequestId: string | null } | null }

type FooterItem = 'tasks' | 'tmux' | 'bagel' | 'teams' | 'bridge' | 'companion'
```

### Existing Analysis Accuracy (state-management.md)

| Claim | Verdict | Detail |
|-------|---------|--------|
| "Session fields: conversationId, sessionId" | **INCORRECT** | No `conversationId` or `sessionId` in AppState. These are in bootstrap state |
| "Permissions: toolPermissionContext (mode, rules, directories)" | **CORRECT** | Confirmed in DeepImmutable section |
| "MCP: mcp.tools, mcp.commands, mcp.resources, mcp.clients" | **CORRECT** | Plus `pluginReconnectKey` not mentioned |
| "Tasks: Map of TaskStateBase, backgroundTasks" | **PARTIALLY INCORRECT** | It is `{ [taskId: string]: TaskState }` not Map, and no `backgroundTasks` field |
| "UI: theme, outputStyle, todoItems" | **INCORRECT** | No `theme` or `outputStyle` fields. `todos` exists (keyed by agentId) |
| "Cost: costTracker" | **INCORRECT** | No `costTracker` in AppState. Cost tracking is in bootstrap `State` (`totalCostUSD`) |
| "Agents: agentDefinitions, activeAgents" | **PARTIALLY CORRECT** | `agentDefinitions` exists (type `AgentDefinitionsResult`). No separate `activeAgents` field — it is inside `agentDefinitions.activeAgents` |
| "Large flat object" | **INCORRECT** | Hybrid `DeepImmutable<{...}> & {...}` with deeply nested sub-objects (mcp, plugins, computerUseMcpState, teamContext) |

---

## 3. Entry Union (`src/types/logs.ts`)

### `Entry` — 19-variant discriminated union

```typescript
type Entry =
  | TranscriptMessage        // type from Message + metadata
  | SummaryMessage           // type: 'summary'
  | CustomTitleMessage       // type: 'custom-title'
  | AiTitleMessage           // type: 'ai-title'
  | LastPromptMessage        // type: 'last-prompt'
  | TaskSummaryMessage       // type: 'task-summary'
  | TagMessage               // type: 'tag'
  | AgentNameMessage         // type: 'agent-name'
  | AgentColorMessage        // type: 'agent-color'
  | AgentSettingMessage       // type: 'agent-setting'
  | PRLinkMessage            // type: 'pr-link'
  | FileHistorySnapshotMessage // type: 'file-history-snapshot'
  | AttributionSnapshotMessage // type: 'attribution-snapshot'
  | QueueOperationMessage    // (imported from messageQueueTypes.ts)
  | SpeculationAcceptMessage // type: 'speculation-accept'
  | ModeEntry                // type: 'mode'
  | WorktreeStateEntry       // type: 'worktree-state'
  | ContentReplacementEntry  // type: 'content-replacement'
  | ContextCollapseCommitEntry   // type: 'marble-origami-commit'
  | ContextCollapseSnapshotEntry // type: 'marble-origami-snapshot'
```

**Note**: `TranscriptMessage` discriminates via its `Message` base (which has `role` not `type`), while all other variants use a `type` discriminator. This is an imperfect discriminated union — callers must check `'type' in entry` first.

### `SerializedMessage`

```typescript
type SerializedMessage = Message & {
  cwd: string
  userType: string
  entrypoint?: string    // CLAUDE_CODE_ENTRYPOINT
  sessionId: string
  timestamp: string
  version: string
  gitBranch?: string
  slug?: string          // Session slug for plans (resume)
}
```

### `TranscriptMessage`

```typescript
type TranscriptMessage = SerializedMessage & {
  parentUuid: UUID | null
  logicalParentUuid?: UUID | null
  isSidechain: boolean
  gitBranch?: string
  agentId?: string
  teamName?: string
  agentName?: string
  agentColor?: string
  promptId?: string
}
```

### `LogOption` (53 lines, 30 fields)

Key fields: `date`, `messages: SerializedMessage[]`, `fullPath?`, `value`, `created`, `modified`, `firstPrompt`, `messageCount`, `fileSize?`, `isSidechain`, `isLite?`, `sessionId?`, `teamName?`, `agentName?`, `agentColor?`, `agentSetting?`, `isTeammate?`, `leafUuid?`, `summary?`, `customTitle?`, `tag?`, `fileHistorySnapshots?`, `attributionSnapshots?`, `contextCollapseCommits?`, `contextCollapseSnapshot?`, `gitBranch?`, `projectPath?`, `prNumber?`, `prUrl?`, `prRepository?`, `mode?`, `worktreeSession?`, `contentReplacements?`.

### Obfuscated Entry Types

Two context-collapse entries use obfuscated type discriminators:
- `ContextCollapseCommitEntry`: `type: 'marble-origami-commit'`
- `ContextCollapseSnapshotEntry`: `type: 'marble-origami-snapshot'`

Source comment explains: "Discriminator is obfuscated to match the gate name... a descriptive string here would leak into external builds."

---

## 4. Text Input Types (`src/types/textInputTypes.ts`)

### `VimMode`

```typescript
type VimMode = 'INSERT' | 'NORMAL'
```

### `QueuePriority`

```typescript
type QueuePriority = 'now' | 'next' | 'later'
```

Semantics (from JSDoc):
- `now` — Interrupt immediately, abort in-flight tool call
- `next` — Mid-turn drain after current tool finishes
- `later` — End-of-turn drain, new query

### `QueuedCommand` (20 fields)

```typescript
type QueuedCommand = {
  value: string | Array<ContentBlockParam>
  mode: PromptInputMode
  priority?: QueuePriority
  uuid?: UUID
  orphanedPermission?: OrphanedPermission
  pastedContents?: Record<number, PastedContent>
  preExpansionValue?: string
  skipSlashCommands?: boolean
  bridgeOrigin?: boolean
  isMeta?: boolean
  origin?: MessageOrigin
  workload?: string
  agentId?: AgentId
}
```

### `PromptInputMode`

```typescript
type PromptInputMode = 'bash' | 'prompt' | 'orphaned-permission' | 'task-notification'
type EditablePromptInputMode = Exclude<PromptInputMode, `${string}-notification`>
// = 'bash' | 'prompt' | 'orphaned-permission'
```

### `BaseTextInputProps` (28 fields)

Key fields: `value: string`, `onChange`, `onSubmit?`, `onExit?`, `columns: number`, `cursorOffset: number`, `onChangeCursorOffset`, `placeholder?`, `multiline?`, `focus?`, `mask?`, `showCursor?`, `highlightPastedText?`, `maxVisibleLines?`, `onImagePaste?`, `onPaste?`, `disableCursorMovementForUpDownKeys?`, `disableEscapeDoublePress?`, `argumentHint?`, `onUndo?`, `dimColor?`, `highlights?: TextHighlight[]`, `placeholderElement?: React.ReactNode`, `inlineGhostText?: InlineGhostText`, `inputFilter?`.

### `InlineGhostText`

```typescript
type InlineGhostText = {
  readonly text: string
  readonly fullCommand: string
  readonly insertPosition: number
}
```

### `BaseInputState`

```typescript
type BaseInputState = {
  onInput: (input: string, key: Key) => void
  renderedValue: string
  offset: number
  setOffset: (offset: number) => void
  cursorLine: number
  cursorColumn: number
  viewportCharOffset: number
  viewportCharEnd: number
  isPasting?: boolean
  pasteState?: { chunks: string[]; timeoutId: ReturnType<typeof setTimeout> | null }
}
```

### Existing Analysis Accuracy (type-system.md)

| Claim | Verdict | Detail |
|-------|---------|--------|
| "VimMode listed in key type files" | **CORRECT** | `textInputTypes.ts` correctly listed |
| "No detailed QueuedCommand coverage" | **GAP** | QueuedCommand is a critical 20-field type not covered in type-system.md |
| "No BaseTextInputProps coverage" | **GAP** | 28-field props interface not documented |

---

## 5. Bootstrap State (`src/bootstrap/state.ts`)

### `State` type (~90 fields)

Key categories:

| Category | Fields (count) | Examples |
|----------|---------------|----------|
| **Session** (11) | `originalCwd`, `projectRoot`, `cwd`, `sessionId`, `parentSessionId`, `isInteractive`, `kairosActive`, `clientType`, `sessionSource`, `isRemoteMode`, `sessionProjectDir` |
| **Cost/Timing** (12) | `totalCostUSD`, `totalAPIDuration`, `totalAPIDurationWithoutRetries`, `totalToolDuration`, `startTime`, `lastInteractionTime`, `turnHookDurationMs`, `turnToolDurationMs`, `turnClassifierDurationMs`, `turnToolCount`, `turnHookCount`, `turnClassifierCount` |
| **Code Metrics** (3) | `totalLinesAdded`, `totalLinesRemoved`, `hasUnknownModelCost` |
| **Model** (4) | `modelUsage`, `mainLoopModelOverride`, `initialMainLoopModel`, `modelStrings` |
| **Telemetry** (11) | `meter`, `sessionCounter`, `locCounter`, `prCounter`, `commitCounter`, `costCounter`, `tokenCounter`, `codeEditToolDecisionCounter`, `activeTimeCounter`, `statsStore`, `meterProvider` |
| **Logger/Tracer** (3) | `loggerProvider`, `eventLogger`, `tracerProvider` |
| **Agent Color** (2) | `agentColorMap`, `agentColorIndex` |
| **API Debug** (4) | `lastAPIRequest`, `lastAPIRequestMessages`, `lastClassifierRequests`, `cachedClaudeMdContent` |
| **Session Flags** (12) | `sessionBypassPermissionsMode`, `scheduledTasksEnabled`, `sessionTrustAccepted`, `sessionPersistenceDisabled`, `hasExitedPlanMode`, `needsPlanModeExitAttachment`, `needsAutoModeExitAttachment`, `lspRecommendationShownThisSession`, `chromeFlagOverride`, `useCoworkPlugins`, `strictToolResultPairing`, `sdkAgentProgressSummariesEnabled` |
| **Skills/Hooks** (4) | `invokedSkills`, `registeredHooks`, `initJsonSchema`, `planSlugCache` |
| **Cache Latches** (7) | `promptCache1hAllowlist`, `promptCache1hEligible`, `afkModeHeaderLatched`, `fastModeHeaderLatched`, `cacheEditingHeaderLatched`, `thinkingClearLatched`, `pendingPostCompaction` |
| **Channels** (3) | `allowedChannels`, `hasDevChannels`, `additionalDirectoriesForClaudeMd` |
| **Other** (7) | `inMemoryErrorLog`, `inlinePlugins`, `slowOperations`, `sdkBetas`, `mainThreadAgentType`, `teleportedSessionInfo`, `sessionCronTasks`, `sessionCreatedTeams` |

### `ChannelEntry`

```typescript
type ChannelEntry =
  | { kind: 'plugin'; name: string; marketplace: string; dev?: boolean }
  | { kind: 'server'; name: string; dev?: boolean }
```

### `AttributedCounter`

```typescript
type AttributedCounter = {
  add(value: number, additionalAttributes?: Attributes): void
}
```

### Bootstrap vs AppState — Key Distinction

Bootstrap `State` is a **module-level singleton** (`const STATE: State = getInitialState()`) accessed via getter/setter functions. It is NOT reactive — React components cannot subscribe to it. AppState is a **reactive store** with pub/sub for UI rendering.

### Existing Analysis Accuracy (state-management.md)

| Claim | Verdict | Detail |
|-------|---------|--------|
| "getSessionId(), getOriginalCwd()" | **CORRECT** | Confirmed as exported getters |
| "getIsNonInteractiveSession()" | **NOT FOUND IN FIRST 500 LINES** | `isInteractive` field exists; getter name may differ |
| "getAdditionalDirectoriesForClaudeMd()" | **CORRECT** | Field confirmed |
| "setMeter()" | **LIKELY CORRECT** | `meter` field exists; setter in later portion of file |
| "getCachedClaudeMdContent()" | **CORRECT** | `cachedClaudeMdContent` field confirmed |
| "getKairosActive()" | **CORRECT** | `kairosActive` field confirmed |
| "Bootstrap: Immutable after init" | **INCORRECT** | Many fields are mutated throughout the session (totalCostUSD, modelUsage, cwd, etc.) |

---

## 6. Verification Summary

### Errors Found in Existing Analysis

| # | File | Error | Severity |
|---|------|-------|----------|
| 1 | state-management.md | AppState listed as "large flat object" — actually hybrid `DeepImmutable<> & {}` | MEDIUM |
| 2 | state-management.md | Claims `conversationId`, `sessionId` in AppState — they are in bootstrap State | HIGH |
| 3 | state-management.md | Claims `backgroundTasks` field — does not exist | HIGH |
| 4 | state-management.md | Claims `theme`, `outputStyle` fields — do not exist | HIGH |
| 5 | state-management.md | Claims `costTracker` in AppState — cost is in bootstrap State | HIGH |
| 6 | state-management.md | Tasks described as "Map of TaskStateBase" — actually `{ [taskId: string]: TaskState }` (plain object) | MEDIUM |
| 7 | state-management.md | Bootstrap state described as "Immutable after init" — many fields are mutated | HIGH |
| 8 | type-system.md | QueuedCommand (20 fields, critical queue type) not covered | GAP |
| 9 | type-system.md | BaseTextInputProps (28 fields) not covered | GAP |
| 10 | type-system.md | Entry union (19 variants) not covered | GAP |

### Correct Claims Confirmed

- Store pattern (getState/setState/subscribe) — exact match
- MCP sub-state shape — correct (plus undocumented `pluginReconnectKey`)
- ToolPermissionContext in AppState — correct
- VimMode = 'INSERT' | 'NORMAL' — correct
- Bootstrap getter functions (sessionId, cwd, kairos, claudeMd) — correct

### Statistics

- **AppState total fields**: ~105 (37 DeepImmutable + 68 mutable)
- **Entry union variants**: 19 (was not previously quantified)
- **QueuedCommand fields**: 13 typed fields + JSDoc
- **Bootstrap State fields**: ~90
- **Existing analysis accuracy**: ~50% for AppState field inventory, ~85% for Store pattern, ~70% for bootstrap

### Quality Score: 6.8/10

The existing analysis correctly captures the architectural patterns (Store, selectors, bootstrap vs AppState split) but has significant field-level inaccuracies in the AppState inventory table. Several fields were fabricated or mislocated between AppState and bootstrap State. The type-system.md has no coverage of Entry, QueuedCommand, or BaseTextInputProps — all critical types for the message/log pipeline.

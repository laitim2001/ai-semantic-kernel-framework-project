# V9 Frontend Module Deep-Dive Analysis

> **Scan Date**: 2026-03-29
> **Scanner**: Claude Opus 4.6 (1M context) — Phase C Module Deep-Dive
> **Scope**: All frontend modules under `frontend/src/`
> **Total Files Analyzed**: ~211 source files (excluding node_modules, dist, test files)

---

## Table of Contents

1. [Module: unified-chat](#module-unified-chat)
2. [Module: agent-swarm](#module-agent-swarm)
3. [Module: ag-ui](#module-ag-ui)
4. [Module: DevUI](#module-devui)
5. [Module: workflow-editor](#module-workflow-editor)
6. [Module: pages](#module-pages)
7. [Module: hooks](#module-hooks)
8. [Module: api](#module-api)
9. [Module: stores](#module-stores)
10. [Module: types](#module-types)
11. [Cross-Module Dependency Graph](#cross-module-dependency-graph)
12. [Known Issues Summary](#known-issues-summary)

---

## Module: unified-chat

- **Path**: `frontend/src/components/unified-chat/`
- **Files**: 29 (+ 4 renderers sub-module: 3 components + 1 barrel)
- **Sprint Origin**: Sprint 62 (Phase 16) through Sprint 147

### Public API / Exports

Barrel file `index.ts` exports 30+ named components and their props types:

| Export | Type | Sprint |
|--------|------|--------|
| `ChatHeader` | Component | S62-1 |
| `ChatInput` | Component | S62-1 |
| `StatusBar` | Component | S62-1 |
| `ChatArea` | Component | S62-3 |
| `MessageList` / `MessageListProps` | Component + Type | S62-3 |
| `InlineApproval` | Component | S62-3 |
| `WorkflowSidePanel` | Component | S62-4 |
| `StepProgress` | Component | S62-4 |
| `ToolCallTracker` | Component | S62-4 |
| `CheckpointList` | Component | S62-4 |
| `StepProgressEnhanced`, `StatusIcon`, `SubStepItem` | Components | S69-2 |
| `ModeIndicator` / `ModeIndicatorProps` | Component + Type | S63-3 |
| `ModeSwitchConfirmDialog` | Component | S64-1 |
| `ApprovalDialog` / `ApprovalDialogProps` | Component + Type | S64-2 |
| `ApprovalMessageCard` / `ApprovalMessageCardProps` | Component + Type | S99 |
| `RiskIndicator` / `RiskIndicatorProps` | Component + Type | S64-3 |
| `RestoreConfirmDialog` | Component | S65-2 |
| `ErrorBoundary`, `ErrorBoundaryWrapper` | Components | S65-3 |
| `ConnectionStatus` | Component | S65-3 |
| `ChatHistoryPanel`, `ChatHistoryToggleButton` | Components | S74-1 |
| `FileUpload`, `AttachButton`, `HiddenFileInput` | Components | S75-2 |
| `AttachmentPreview`, `CompactAttachmentPreview` | Components | S75-3 |
| `FileMessage`, `FileMessageList`, `CompactFileMessage` | Components | S76-2 |
| `FileRenderer`, `getFileType` | Component + Helper | S76-3 |
| `ImagePreview`, `CodePreview`, `TextPreview` | Renderers | S76-3 |
| `IntentStatusChip` | Component | Phase 41 |
| `TaskProgressCard` | Component | Phase 41 |
| `MemoryHint` | Component | Phase 41 |

Re-exports all prop types from `@/types/unified-chat` for convenience.

### Component Tree

```
UnifiedChat (page)
├── ChatHistoryPanel (left sidebar)
├── ChatHeader
│   └── ModeIndicator
├── ChatArea
│   └── MessageList
│       ├── MessageBubble (from ag-ui/chat)
│       ├── ApprovalMessageCard
│       ├── IntentStatusChip
│       ├── ToolCallTracker
│       ├── TaskProgressCard
│       ├── CustomUIRenderer (from ag-ui/advanced)
│       └── Knowledge Sources (inline)
├── ChatInput
│   ├── CompactAttachmentPreview
│   └── Textarea + Send/Cancel buttons
├── OrchestrationPanel (right sidebar, collapsible)
│   ├── PhaseIndicator
│   ├── Routing Decision Section
│   ├── Risk Assessment Section
│   ├── Dialog Questions Section
│   └── AgentSwarmPanel (embedded)
├── WorkflowSidePanel (conditional on mode)
│   ├── StepProgress / StepProgressEnhanced
│   ├── ToolCallTracker
│   └── CheckpointList
├── StatusBar
│   ├── Mode Badge
│   ├── Risk Badge
│   ├── Token Usage
│   ├── Tool Statistics
│   ├── Message Count
│   ├── Execution Time
│   ├── Heartbeat Indicator
│   └── Checkpoint Restore
├── MemoryHint (floating)
├── AgentSwarmPanel (bottom panel, conditional)
└── WorkerDetailDrawer (overlay)
```

### Hook Dependencies

- `useUnifiedChat` — primary orchestration hook
- `useSSEChat` — SSE streaming for pipeline
- `useExecutionMetrics` — timer and metrics
- `useChatThreads` — thread CRUD + localStorage persistence
- `useFileUpload` — file attachment management
- `useOrchestration` — Phase 28 orchestration state
- `useSwarmStore` — Zustand store for swarm state
- `useAuthStore` — user/token for isolation

### Store Dependencies

- `unifiedChatStore` — messages, mode, workflow state, approvals, checkpoints, metrics
- `swarmStore` — swarm status, worker details, drawer state
- `authStore` — user identity for thread isolation

### Known Issues

1. **UnifiedChat.tsx is 1403 lines** — heavy page component with 15+ state hooks, mixing orchestration logic, SSE handlers, memory fetching, and swarm integration. Candidate for extraction into sub-hooks.
2. **Dual streaming paths**: `useUnifiedChat` (AG-UI SSE) and `useSSEChat` (pipeline SSE) coexist. The page component manually bridges them via `sendSSE` handlers that update `messages` state directly.
3. **Unused variables suppressed**: Multiple `void varName` patterns in UnifiedChat.tsx to suppress TypeScript warnings for imported-but-not-yet-used symbols.
4. **localStorage for thread persistence**: Thread messages are stored in localStorage (via `useChatThreads.saveMessages`), bypassing the Zustand persist middleware. Two parallel persistence mechanisms.
5. **`DEFAULT_TOOLS` hardcoded in page**: Tool definitions (8 tools) are hardcoded constants in UnifiedChat.tsx rather than fetched from config or backend.

---

## Module: agent-swarm

- **Path**: `frontend/src/components/unified-chat/agent-swarm/`
- **Files**: 16 components + 5 hooks (4 hooks + 1 barrel) + 2 type files + 12 test files = 35 total
- **Sprint Origin**: Sprint 101-105 (Phase 29)

### Public API / Exports

Barrel `index.ts` re-exports everything from `types/` and `hooks/`, plus named component exports:

**Components (Sprint 102-104)**:
`AgentSwarmPanel`, `SwarmHeader`, `OverallProgress`, `WorkerCard`, `WorkerCardList`, `SwarmStatusBadges`, `WorkerDetailDrawer`, `WorkerDetailHeader`, `CurrentTask`, `ToolCallItem`, `ToolCallsPanel`, `MessageHistory`, `CheckpointPanel`, `ExtendedThinkingPanel`, `WorkerActionList`

**Hooks**:
| Hook | Purpose | Source |
|------|---------|--------|
| `useSwarmEvents` | Parse SSE EventSource for swarm event types | S101 |
| `useWorkerDetail` | Fetch worker detail via REST API | S103 |
| `useSwarmStatus` | Derived selectors from swarmStore | S105 |
| `useSwarmEventHandler` | Bridge SSE events to Zustand store | S105 |

**Utility exports**: `isSwarmEvent`, `getSwarmEventCategory`, `inferActionType`

### Component Tree

```
AgentSwarmPanel
├── SwarmHeader (mode, status, totalWorkers, startedAt)
├── OverallProgress (progress bar + status)
└── WorkerCardList
    └── WorkerCard[] (per worker)
        ├── Status badge
        ├── Progress bar
        └── Current action

WorkerDetailDrawer (overlay)
├── WorkerDetailHeader
├── CurrentTask
├── ExtendedThinkingPanel
├── ToolCallsPanel
│   └── ToolCallItem[]
├── WorkerActionList
├── MessageHistory
└── CheckpointPanel
```

### Type Duality (snake_case vs camelCase)

The type system has an explicit dual-layer architecture:

| Layer | Convention | File | Purpose |
|-------|-----------|------|---------|
| **SSE Events** | snake_case | `types/events.ts` | Wire format from backend SSE |
| **UI Components** | camelCase | `types/index.ts` | React component props |

**SSE Event Types** (9 events):
`swarm_created`, `swarm_status_update`, `swarm_completed`, `worker_started`, `worker_progress`, `worker_thinking`, `worker_tool_call`, `worker_message`, `worker_completed`

**UI Types**: `UIAgentSwarmStatus`, `UIWorkerSummary`, `WorkerDetail`, `ToolCallInfo`, `ThinkingContent`, `WorkerMessage`

**Component Props**: `AgentSwarmPanelProps`, `SwarmHeaderProps`, `OverallProgressProps`, `WorkerCardProps`, `WorkerCardListProps`, `SwarmStatusBadgesProps`

**Conversion**: `useSwarmEventHandler` maps snake_case payloads to camelCase UI types and dispatches to `swarmStore`.

### Hook Chain

```
EventSource (SSE)
  → useSwarmEvents (parse & dispatch by event name)
    → useSwarmEventHandler (convert snake→camel, update store)
      → useSwarmStore (Zustand state)
        → useSwarmStatus (derived selectors)
          → AgentSwarmPanel (render)
```

### Store Dependencies

- `swarmStore` — all swarm state management

### Known Issues

1. **`useSwarmEventHandler` creates many store selectors**: 8 individual `useSwarmStore(s => s.action)` calls which could cause unnecessary re-renders. Should use a single selector or `useShallow`.
2. **Worker detail drawer auth**: `WorkerDetailDrawer` fetches worker detail via `useWorkerDetail` REST API, but the swarm store also receives worker data via SSE. Two data sources for the same entity.
3. **Test coverage**: 12 test files covering 6 components and 1 hook — good coverage for UI layer.

---

## Module: ag-ui

- **Path**: `frontend/src/components/ag-ui/`
- **Files**: 19 files across 3 subdirectories
- **Sprint Origin**: Sprint 60-61 (AG-UI Protocol)

### Public API / Exports

**`chat/` (5 files)**:
| Component | Props | Purpose |
|-----------|-------|---------|
| `ChatContainer` | `ChatContainerProps` | Standalone chat interface using `useAGUI` hook |
| `MessageBubble` | message, isStreaming, onToolCallAction, onDownload | Individual message display |
| `MessageInput` | onSend, disabled, isStreaming, onCancel, placeholder | Text input with send/cancel |
| `StreamingIndicator` | isStreaming | Typing animation dots |
| `ToolCallCard` | — | Tool call result display |

**`hitl/` (4 files)**:
| Component | Props | Purpose |
|-----------|-------|---------|
| `ApprovalDialog` | approval, isOpen, onApprove, onReject, onClose | Full modal for high-risk approvals |
| `ApprovalBanner` | — | Banner notification for pending approvals |
| `ApprovalList` | — | List of all pending approvals |
| `RiskBadge` | level, score, showScore | Color-coded risk level badge |

**`advanced/` (8 files)**:
| Component | Props | Purpose |
|-----------|-------|---------|
| `CustomUIRenderer` | definition, onEvent, className, isLoading, error | Routes to DynamicForm/Chart/Card/Table |
| `DynamicForm` | fields, submitLabel, onSubmit, onCancel | Backend-defined forms |
| `DynamicChart` | chartType, data, options, onDataPointClick | Recharts wrapper |
| `DynamicCard` | title, subtitle, content, actions, onAction | Info/action cards |
| `DynamicTable` | columns, rows, pagination, onRowSelect, onSort | Data tables |
| `StateDebugger` | — | Shared state inspector |
| `OptimisticIndicator` | — | Prediction status display |

### Component API

**ChatContainer** is the self-contained AG-UI chat widget:
- Params: `{ threadId, sessionId?, tools?, mode?, apiUrl?, onError?, showStatus?, debug? }`
- Returns: Full chat UI with SSE connection management
- Internally uses `useAGUI` hook for AG-UI protocol integration

**CustomUIRenderer** dispatches by `definition.componentType`:
- `'form'` → `DynamicForm`
- `'chart'` → `DynamicChart`
- `'card'` → `DynamicCard`
- `'table'` → `DynamicTable`
- `'custom'` → JSON preview fallback

**ApprovalDialog** features:
- Countdown timer with auto-close on expiry
- Risk badge with score
- JSON argument preview
- Optional comment field
- Timestamps in `zh-TW` locale

### Hook Dependencies

- `useAGUI` — AG-UI protocol SSE connection, message management, tool calls, approvals

### Known Issues

1. **ChatContainer duplicates ChatArea patterns**: Both `ChatContainer` (ag-ui) and `ChatArea` (unified-chat) implement message lists with auto-scroll, empty states, and streaming indicators. The unified-chat version is the actively-used one; `ChatContainer` exists for standalone demo use.
2. **No barrel exports at `ag-ui/` level**: Each subdirectory has its own `index.ts` but there is no top-level `ag-ui/index.ts`. Imports require specifying `ag-ui/chat/`, `ag-ui/hitl/`, or `ag-ui/advanced/`.

---

## Module: DevUI

- **Path**: `frontend/src/components/DevUI/`
- **Files**: 15 components
- **Sprint Origin**: Sprint 87-89 (Phase 26)

### Public API / Exports

| Component | Purpose |
|-----------|---------|
| `EventFilter` | Multi-faceted filter panel (event type, severity, executor, search) |
| `FilterBar` | Compact inline filter bar (inline sub-component within `EventFilter.tsx`, not a separate file) |
| `Timeline` | Main execution timeline with zoom, filter, view modes |
| `TimelineNode` | Individual timeline event node |
| `EventList` | Flat event list view |
| `EventTree` | Hierarchical event tree |
| `EventDetail` | Selected event detail panel |
| `EventPanel` | Combined event view container |
| `EventPieChart` | Event distribution chart |
| `DurationBar` | Duration visualization bar |
| `StatCard` | Metric summary card |
| `Statistics` | Aggregated statistics dashboard |
| `LLMEventPanel` | LLM-specific event details |
| `ToolEventPanel` | Tool-specific event details |
| `LiveIndicator` | Real-time connection status |
| `TreeNode` | Recursive tree node component |

### Component Set

DevUI provides a complete developer tools suite:

```
DevUI Pages
├── Overview (index.tsx)
├── TraceList → TraceDetail
│   ├── Timeline
│   │   └── TimelineNode[] (with DurationBar)
│   ├── EventFilter / FilterBar
│   ├── EventList / EventTree
│   │   └── TreeNode[] (recursive)
│   └── EventDetail
│       ├── LLMEventPanel
│       └── ToolEventPanel
├── LiveMonitor
│   ├── LiveIndicator
│   ├── Statistics
│   │   ├── StatCard[]
│   │   └── EventPieChart
│   └── EventPanel
├── AGUITestPanel
└── Settings
```

### Hook Dependencies

- `useDevTools` — trace data fetching
- `useDevToolsStream` — SSE real-time event stream
- `useEventFilter` — filter state management (multi-selector pattern)

### Store Dependencies

None — DevUI components are self-contained with local state and hook-managed server state.

### Known Issues

1. **Chinese/English UI text mix**: `EventFilter` uses Chinese labels (`篩選器`, `搜索事件`, `僅顯示錯誤`, `清除`, `事件類型`, `嚴重性`, `執行器`), while `Timeline` uses English labels. Inconsistent i18n approach.
2. **No barrel export**: No `index.ts` at `DevUI/` component level. Pages import individual components directly.

---

## Module: workflow-editor

- **Path**: `frontend/src/components/workflow-editor/`
- **Files**: 10 files (1 canvas + 4 nodes + 2 edges + 1 layout util + 2 hooks)
- **Sprint Origin**: Sprint 133 (Phase 34)

### Public API / Exports

**Components**:
| Component | Type | Purpose |
|-----------|------|---------|
| `WorkflowCanvas` | Main | ReactFlow canvas with controls, minimap, legend, detail panel |
| `AgentNode` | Custom Node | Agent step visualization |
| `ConditionNode` | Custom Node | Gateway/decision diamond |
| `ActionNode` | Custom Node | Task/approval rectangle |
| `StartEndNode` | Custom Node | Start/End circle |
| `DefaultEdge` | Custom Edge | Standard flow connection |
| `ConditionalEdge` | Custom Edge | Conditional branch with label |

**Hooks**:
| Hook | Params → Return | Purpose |
|------|----------------|---------|
| `useWorkflowData(workflowId)` | `→ { nodes, edges, isLoading, workflow, saveLayout, isSaving, autoLayout, exportToJson }` | Fetch + transform workflow to ReactFlow format |
| `useNodeDrag({ onSave, debounceMs })` | `→ { isDragging, hasUnsavedChanges, onNodeDragStart, onNodeDragStop, markSaved }` | Drag-to-save with debounce |

**Utilities**:
| Utility | Purpose |
|---------|---------|
| `applyDagreLayout(nodes, edges, options?)` | Dagre-based auto-layout (TB/LR direction) |

### ReactFlow Integration

**Node types registered**: `{ agent, condition, action, startEnd }`
**Edge types registered**: `{ default, conditional }`

**Data flow**:
```
Backend API (/workflows/:id/graph)
  → useWorkflowData (React Query)
    → graphNodesToReactFlow / graphEdgesToReactFlow (transform)
      → applyDagreLayout (if no saved positions)
        → useNodesState / useEdgesState (ReactFlow state)
          → WorkflowCanvas (render)
```

**Features**: Auto-layout (dagre, TB/LR), drag-to-save (debounced 2s), export to JSON, minimap, zoom controls, node/edge detail panel, unsaved changes indicator.

### Hook Dependencies

- `useWorkflowData` uses `useQuery` + `useMutation` from TanStack React Query
- `api.get` / `api.put` / `api.post` from `@/api/client`

### Store Dependencies

None — uses React Query for server state, local state for UI.

### Known Issues

1. **Legacy format fallback**: `useWorkflowData` handles 3 data formats (graph endpoint → `graph_definition` → legacy `definition`). The legacy path produces nodes at `{x:0, y:0}` requiring auto-layout.
2. **Type assertions in DetailPanel**: Multiple `(node.data as Record<string, unknown>)` casts due to ReactFlow's generic node data type.

---

## Module: pages

- **Path**: `frontend/src/pages/`
- **Files**: 46 files across 14 subdirectories + 2 standalone pages
- **Sprint Origin**: Sprint 5 through Sprint 140

### Page Inventory

| Directory | Pages | Sprint |
|-----------|-------|--------|
| `dashboard/` | `DashboardPage`, `PerformancePage` + 4 sub-components | S5, S12 |
| `agents/` | `AgentsPage`, `AgentDetailPage`, `CreateAgentPage`, `EditAgentPage` | S5 |
| `workflows/` | `WorkflowsPage`, `WorkflowDetailPage`, `CreateWorkflowPage`, `EditWorkflowPage`, `WorkflowEditorPage` | S5, S133 |
| `auth/` | `LoginPage`, `SignupPage` | S71 |
| `ag-ui/` | `AGUIDemoPage` + 7 demo sub-components | S61 |
| `approvals/` | `ApprovalsPage` | S5 |
| `audit/` | `AuditPage` | S5 |
| `templates/` | `TemplatesPage` | S5 |
| `DevUI/` | `Layout`, `index`, `TraceList`, `TraceDetail`, `LiveMonitor`, `Settings`, `AGUITestPanel` | S87-89 |
| `sessions/` | `SessionsPage`, `SessionDetailPage` | S138 |
| `tasks/` | `TaskDashboardPage`, `TaskDetailPage` | S139 |
| `knowledge/` | `KnowledgePage` | S140 |
| `memory/` | `MemoryPage` | S140 |
| (standalone) | `UnifiedChat.tsx` | S62 |
| (standalone) | `SwarmTestPage.tsx` | Phase 29 |

### Route Map (from App.tsx)

```
/login                → LoginPage (standalone)
/signup               → SignupPage (standalone)
/ag-ui-demo           → AGUIDemoPage (standalone)
/swarm-test           → SwarmTestPage (standalone)

/ (ProtectedRoute + AppLayout)
├── /dashboard        → DashboardPage
├── /chat             → UnifiedChat
├── /performance      → PerformancePage
├── /workflows        → WorkflowsPage
├── /workflows/new    → CreateWorkflowPage
├── /workflows/:id    → WorkflowDetailPage
├── /workflows/:id/edit    → EditWorkflowPage
├── /workflows/:id/editor  → WorkflowEditorPage
├── /agents           → AgentsPage
├── /agents/new       → CreateAgentPage
├── /agents/:id       → AgentDetailPage
├── /agents/:id/edit  → EditAgentPage
├── /templates        → TemplatesPage
├── /sessions         → SessionsPage
├── /sessions/:id     → SessionDetailPage
├── /tasks            → TaskDashboardPage
├── /tasks/:id        → TaskDetailPage
├── /knowledge        → KnowledgePage
├── /memory           → MemoryPage
├── /approvals        → ApprovalsPage
├── /audit            → AuditPage
├── /devui            → DevUILayout
│   ├── (index)       → DevUIOverview
│   ├── /ag-ui-test   → AGUITestPanel
│   ├── /traces       → TraceList
│   ├── /traces/:id   → TraceDetail
│   ├── /monitor      → LiveMonitor
│   └── /settings     → DevUISettings
└── /*                → Navigate(/dashboard)
```

**Route Count**: 27 routes (4 standalone + 23 protected)

### Key Page: UnifiedChat.tsx

The main chat page (`/chat`) is the most complex page component:

**Hooks consumed** (15+):
`useUnifiedChat`, `useSSEChat`, `useExecutionMetrics`, `useChatThreads`, `useFileUpload`, `useOrchestration`, `useAuthStore`, `useSwarmStore`, `memoryApi`, `sessionsApi`, `filesApi`

**State variables** (20+):
`historyCollapsed`, `orchestrationEnabled`, `showOrchestrationPanel`, `dialogQuestions`, `orchestratorSessionId`, `isPipelineSending`, `swarmStatus`, `showSwarmPanel`, `pendingApproval`, `pipelineMode`, `suggestedMode`, `typewriterContent`, `typewriterMessageId`, `relatedMemories`, `showMemoryHint`, `activeThreadId`

**External integrations**: Memory API (search related memories), Sessions API, Files API, Orchestrator pipeline (SSE streaming)

### Known Issues

1. **UnifiedChat.tsx god-component**: 1403 lines, 15+ hooks, 20+ state vars. Should be decomposed into `usePipelineChat`, `useMemoryIntegration`, `useSwarmIntegration` sub-hooks.
2. **4 standalone (unprotected) routes**: `/login`, `/signup`, `/ag-ui-demo`, `/swarm-test` bypass `ProtectedRoute`. The demo/test pages should be dev-only.

---

## Module: hooks

- **Path**: `frontend/src/hooks/`
- **Files**: 24 hook files + 1 index
- **Sprint Origin**: Sprint 60 through Sprint 145

### Hook API Reference

| Hook | Params | Return Value | Data Source |
|------|--------|-------------|-------------|
| `useAGUI` | `{ threadId, sessionId?, tools?, mode?, apiUrl? }` | `{ messages, isStreaming, connectionStatus, runAgent, cancelRun, approveToolCall, rejectToolCall, ... }` | AG-UI SSE |
| `useUnifiedChat` | `{ threadId, sessionId?, apiUrl?, tools?, modePreference? }` | `{ messages, isStreaming, sendMessage, cancelStream, currentMode, pendingApprovals, toolCalls, checkpoints, tokenUsage, heartbeat, ... }` | AG-UI SSE + REST |
| `useSSEChat` | (none) | `{ sendSSE(request, handlers), isStreaming, cancelStream }` | POST SSE (pipeline) |
| `useApprovalFlow` | `{ autoShowDialog?, defaultTimeout?, onApprovalProcessed? }` | `{ pendingApprovals, dialogApproval, approve, reject, dismissDialog, requestModeSwitch, ... }` | REST API |
| `useHybridMode` | `{ initialMode, sessionId, onModeChange }` | `{ currentMode, autoMode, manualOverride, setManualOverride }` | Local state + events |
| `useOrchestration` | `{ sessionId, userId, includeRiskAssessment?, autoExecute? }` | `{ state, startOrchestration, respondToDialog, proceedWithExecution, reset }` | REST API |
| `useExecutionMetrics` | (options?) | `{ time, tokens, tools, messages, startTimer, stopTimer, resetTimer, ... }` | Local state |
| `useCheckpoints` | (options?) | `{ checkpoints, save, restore, canRestore, ... }` | REST API |
| `useFileUpload` | `{ maxFiles?, onUploadComplete?, onUploadError? }` | `{ attachments, isUploading, addFiles, removeAttachment, uploadAll, clearAttachments }` | REST API |
| `useChatThreads` | (none) | `{ threads, createThread, updateThread, deleteThread, getMessages, saveMessages, generateTitle }` | localStorage |
| `useSwarmMock` | (none) | `{ swarmStatus, createSwarm, addWorker, loadETLScenario, ... }` | Local mock data |
| `useSwarmReal` | (none) | `{ swarmStatus, startDemo, stopDemo, scenarios, isConnected, ... }` | SSE + REST |
| `useSharedState` | (options?) | `{ state, updateState, syncStatus, ... }` | SSE (STATE_SNAPSHOT/DELTA) |
| `useOptimisticState` | (options?) | `{ state, applyOptimistic, confirm, rollback, ... }` | Local + server validation |
| `useDevTools` | (none) | Trace data fetching | REST API |
| `useDevToolsStream` | (options?) | `{ events, connectionStatus }` | SSE |
| `useEventFilter` | (options?) | `{ filteredEvents, toggleEventType, toggleSeverity, searchQuery, ... }` | Local state |
| `useOrchestratorChat` | (options?) | Orchestrator chat integration | REST API |
| `useSessions` | (none) | Session CRUD via React Query | REST API |
| `useTasks` | (none) | Task management via React Query | REST API |
| `useKnowledge` | (none) | Knowledge search, document CRUD | REST API |
| `useMemory` | (none) | Memory search, user memories | REST API |
| `useTypewriterEffect` | (content, options) | Animated text output | Local state |
| `useToolCallEvents` | (options) | Tool call event tracking | SSE events |

### Notable Patterns

1. **Dual SSE paths**: `useAGUI` connects to AG-UI SSE endpoint; `useSSEChat` connects to pipeline POST SSE. Both are used by `UnifiedChat.tsx`.
2. **Mock/Real pattern**: `useSwarmMock` / `useSwarmReal` provide identical interfaces for dev vs production swarm data.
3. **React Query hooks**: `useSessions`, `useTasks`, `useKnowledge`, `useMemory` follow consistent TanStack React Query patterns with `queryKey` factories.

### Known Issues

1. **`useUnifiedChat` is ~360 lines**: Complex hook managing SSE connection lifecycle, 15 AG-UI event types, mode detection, store synchronization, history loading, heartbeat tracking. Should be decomposed.
2. **`useSSEChat` reads auth state outside React**: `useAuthStore.getState().token` is called inside the `sendSSE` callback, which is correct for Zustand but unusual pattern.
3. **`useSwarmMock` has 3 preset scenarios** with hardcoded Chinese text — works for demo but not i18n-ready.

---

## Module: api

- **Path**: `frontend/src/api/`
- **Files**: 11 files (1 client + 1 devtools + 8 endpoint modules + 1 barrel index)

### fetchApi Pattern

Core client in `api/client.ts`:

```typescript
async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T>
```

**Request pipeline**:
1. Read token from `useAuthStore.getState()`
2. Merge guest headers from `getGuestHeaders()` (X-Guest-Id)
3. Set `Content-Type: application/json`
4. Set `Authorization: Bearer ${token}` if authenticated
5. Call `fetch(API_BASE_URL + endpoint, mergedOptions)`
6. Handle 401 → logout + redirect to `/login`
7. Handle other errors → throw `ApiError(message, status, details)`
8. Handle 204 → return `{} as T`
9. Return `response.json()`

**Exported API object**:
```typescript
export const api = {
  get: <T>(endpoint) => fetchApi<T>(endpoint),
  post: <T>(endpoint, body?) => fetchApi<T>(endpoint, { method: 'POST', ... }),
  put: <T>(endpoint, body) => fetchApi<T>(endpoint, { method: 'PUT', ... }),
  patch: <T>(endpoint, body) => fetchApi<T>(endpoint, { method: 'PATCH', ... }),
  delete: <T>(endpoint) => fetchApi<T>(endpoint, { method: 'DELETE' }),
};
```

### Endpoint Modules

| Module | Exported API | Endpoints Used |
|--------|-------------|----------------|
| `endpoints/ag-ui.ts` | `aguiApi` | `/ag-ui/sessions/`, approve/reject |
| `endpoints/files.ts` | `filesApi` | `/files/` upload, download, list |
| `endpoints/orchestration.ts` | `orchestrationApi` | `/orchestration/` routing, risk, dialog |
| `endpoints/knowledge.ts` | `knowledgeApi` | `/knowledge/` search, documents, skills |
| `endpoints/memory.ts` | `memoryApi` | `/memory/` search, user memories, stats |
| `endpoints/sessions.ts` | `sessionsApi` | `/sessions/` CRUD, messages, recover |
| `endpoints/tasks.ts` | `tasksApi` | `/tasks/` CRUD, steps, cancel, retry |
| `endpoints/orchestrator.ts` | `orchestratorApi` | `/orchestrator/` chat, stream |
| `devtools.ts` | `devtoolsApi` | `/devtools/` traces, events |

### Known Issues

1. **`API_BASE_URL` default differs**: `client.ts` defaults to `'/api/v1'` (relative), while `useSwarmReal.ts` defaults to `'http://localhost:8000/api/v1'` (absolute). Should be consistent.
2. **No request/response interceptor pattern**: Each endpoint module reimplements error handling. A middleware layer would reduce duplication.

---

## Module: stores

- **Path**: `frontend/src/store/` + `frontend/src/stores/`
- **Files**: 3 stores (split across 2 directories)

### Store Shapes

#### authStore (`store/authStore.ts`)

```typescript
interface AuthState {
  user: User | null;           // { id, email, fullName, role, isActive, createdAt, lastLogin }
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  // Actions
  login(email, password): Promise<boolean>;
  register(email, password, fullName?): Promise<boolean>;
  logout(): void;
  refreshSession(): Promise<boolean>;
  clearError(): void;
}
```
- **Middleware**: `persist` (to `ipa-auth-storage` in localStorage)
- **Persisted fields**: `token`, `refreshToken`, `user`, `isAuthenticated`
- **Notable**: Contains inline API call functions (`apiLogin`, `apiRegister`, `apiGetMe`, `apiRefreshToken`) using raw `fetch()` — not using the shared `api` client.

#### unifiedChatStore (`stores/unifiedChatStore.ts`)

```typescript
interface UnifiedChatState {
  threadId: string;
  sessionId: string;
  mode: ExecutionMode;                    // 'chat' | 'workflow'
  autoMode: ExecutionMode;
  manualOverride: ExecutionMode | null;
  messages: ChatMessage[];
  isStreaming: boolean;
  streamingMessageId: string | null;
  workflowState: WorkflowState | null;
  toolCalls: TrackedToolCall[];
  pendingApprovals: PendingApproval[];
  dialogApproval: PendingApproval | null;
  checkpoints: Checkpoint[];
  currentCheckpoint: string | null;
  metrics: ExecutionMetrics;
  connection: ConnectionStatus;
  error: string | null;
}
```
- **Middleware**: `devtools` + `persist` (to `unified-chat-storage` in localStorage)
- **Persisted fields**: `threadId`, `sessionId`, `mode`, `manualOverride`, `autoMode`, `messages` (last 100), `workflowState`, `checkpoints` (last 20), `currentCheckpoint`
- **Storage**: Custom localStorage wrapper with quota exceeded error handling
- **Migration**: Version 1, with v0→v1 migration stub

#### swarmStore (`stores/swarmStore.ts`)

```typescript
interface SwarmState {
  swarmStatus: UIAgentSwarmStatus | null;
  selectedWorkerId: string | null;
  selectedWorkerDetail: WorkerDetail | null;
  isDrawerOpen: boolean;
  isLoading: boolean;
  error: string | null;
}
```
- **Middleware**: `devtools` + `immer` (for immutable updates)
- **Not persisted**: Swarm state is ephemeral (resets on page reload)
- **Selectors**: 9 exported selector functions (`selectSwarmStatus`, `selectWorkers`, `selectRunningWorkers`, etc.)

### Known Issues

1. **Two store directories**: `store/` (singular, for auth) and `stores/` (plural, for features). Inconsistent naming.
2. **authStore uses raw fetch**: Login/register/refresh API calls bypass the shared `api` client, duplicating headers and error handling logic.
3. **unifiedChatStore + useUnifiedChat dual state**: The hook maintains its own local state (via `useState`) AND syncs to the Zustand store. Messages exist in both places.

---

## Module: types

- **Path**: `frontend/src/types/`
- **Files**: 4 type definition files

### Type Exports

#### `types/ag-ui.ts` (458 lines)

**Generative UI types**: `UIComponentType`, `UIComponentDefinition`, `UIComponentSchema`, `UIComponentEvent`, `FormFieldDefinition`, `TableColumnDefinition`, `ChartData`, `CardAction`

**Shared State types**: `StateDiff`, `StateVersion`, `StateConflict`, `SharedState`, `StateSyncStatus`, `StateSyncEvent`

**Predictive State types**: `PredictionResult`, `PredictionConfig`, `OptimisticUpdateRequest`, `OptimisticState<T>`

**AG-UI Event types**: `AGUIEventType` (16 event types), `BaseAGUIEvent`, `StateSnapshotEvent`, `StateDeltaEvent`, `CustomEvent`

**Core types**: `ChatMessage`, `ToolCallState`, `ToolCallStatus`, `RiskLevel`, `PendingApproval`, `ApprovalStatus`, `ToolDefinition`, `RunAgentInput`, `SSEConnectionStatus`, `RunStatus`, `AGUIRunState`, `MessageRole`, `GeneratedFile`, `PipelineToolCall`, `OrchestrationMetadata`

#### `types/unified-chat.ts`

Props interfaces for all unified-chat components: `ChatHeaderProps`, `ChatInputProps`, `ChatAreaProps`, `StatusBarProps`, `InlineApprovalProps`, `WorkflowSidePanelProps`, etc.

State types: `ExecutionMode`, `ConnectionStatus`, `ExecutionMetrics`, `WorkflowState`, `WorkflowStep`, `TrackedToolCall`, `Checkpoint`, `Attachment`

Store types: `UnifiedChatState`, `UnifiedChatActions`

#### `types/devtools.ts`

DevTools types: `TraceEvent`, `TraceSession`, `EventSeverity`, `TraceEventType`

#### `types/index.ts`

Core shared types: `Agent`, `Workflow`, `WorkflowGraphNode`, `WorkflowGraphEdge`, `Execution`, etc.

### Known Issues

1. **`types/ag-ui.ts` is a mega-file (458 lines)**: Mixes Generative UI, Shared State, Predictive State, AG-UI Events, and core chat types in one file. Should be split by domain.
2. **OrchestrationMetadata type duality**: Defined in `types/ag-ui.ts` with `riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'` (uppercase), while `RiskLevel` in the same file uses `'low' | 'medium' | 'high' | 'critical'` (lowercase). Two different casing conventions for the same concept.

---

## Cross-Module Dependency Graph

```
pages/UnifiedChat.tsx
  ├── components/unified-chat/* (29 components)
  │   ├── components/ag-ui/chat/MessageBubble
  │   ├── components/ag-ui/chat/StreamingIndicator
  │   ├── components/ag-ui/advanced/CustomUIRenderer
  │   └── components/unified-chat/agent-swarm/* (16 components)
  ├── hooks/useUnifiedChat
  │   ├── hooks/useHybridMode
  │   ├── stores/unifiedChatStore
  │   └── types/ag-ui + types/unified-chat
  ├── hooks/useSSEChat
  │   └── store/authStore
  ├── hooks/useOrchestration
  │   └── api/endpoints/orchestration
  ├── hooks/useExecutionMetrics
  ├── hooks/useChatThreads
  ├── hooks/useFileUpload
  │   └── api/endpoints/files
  ├── stores/swarmStore
  ├── store/authStore
  └── api/endpoints/* (memory, sessions, files)

pages/SwarmTestPage.tsx
  ├── hooks/useSwarmMock
  ├── hooks/useSwarmReal
  └── components/unified-chat/agent-swarm/*

pages/DevUI/*
  ├── components/DevUI/* (15 components)
  ├── hooks/useDevTools
  ├── hooks/useDevToolsStream
  └── hooks/useEventFilter

pages/workflows/WorkflowEditorPage.tsx
  └── components/workflow-editor/WorkflowCanvas
      ├── hooks/useWorkflowData (React Query)
      ├── hooks/useNodeDrag
      └── utils/layoutEngine (dagre)
```

---

## Known Issues Summary

| # | Severity | Module | Description |
|---|----------|--------|-------------|
| FE-001 | HIGH | unified-chat | `UnifiedChat.tsx` god-component (1403 lines, 15+ hooks, 20+ state vars) |
| FE-002 | HIGH | hooks | Dual SSE streaming paths (`useUnifiedChat` AG-UI SSE vs `useSSEChat` pipeline SSE) coexist without clear boundary |
| FE-003 | MEDIUM | stores | Two store directories (`store/` vs `stores/`) with inconsistent naming |
| FE-004 | MEDIUM | stores | `authStore` uses raw `fetch()` bypassing shared `api` client |
| FE-005 | MEDIUM | stores | `unifiedChatStore` + `useUnifiedChat` dual state — messages in both local state and Zustand |
| FE-006 | MEDIUM | types | `OrchestrationMetadata.riskLevel` uses UPPERCASE while `RiskLevel` uses lowercase — casing mismatch |
| FE-007 | MEDIUM | types | `types/ag-ui.ts` is 458-line mega-file mixing 5 domains |
| FE-008 | MEDIUM | api | `API_BASE_URL` default inconsistency (relative in client.ts vs absolute in useSwarmReal.ts) |
| FE-009 | LOW | DevUI | Chinese/English UI text mix in DevUI components — inconsistent i18n |
| FE-010 | LOW | ag-ui | `ChatContainer` duplicates `ChatArea` patterns (both exist, only ChatArea used in prod) |
| FE-011 | LOW | agent-swarm | `useSwarmEventHandler` creates 8 individual store selectors — potential re-render issue |
| FE-012 | LOW | unified-chat | `DEFAULT_TOOLS` hardcoded in page component rather than config/backend |
| FE-013 | LOW | unified-chat | Dual persistence: localStorage (useChatThreads) + Zustand persist (unifiedChatStore) |
| FE-014 | LOW | workflow-editor | Type assertions (`as Record<string, unknown>`) in DetailPanel due to ReactFlow generics |
| FE-015 | LOW | hooks | `useSwarmMock` Chinese preset text not i18n-ready |

---

*End of V9 Frontend Module Deep-Dive Analysis*

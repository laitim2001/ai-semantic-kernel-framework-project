# Layer 01: Frontend (React 18 + TypeScript)

> V9 Architecture Analysis | Layer 01 | 2026-03-29
> Scope: `frontend/src/` -- 236 files, ~54K LOC

---

## 1. Identity Card

| Attribute | Value |
|-----------|-------|
| **Framework** | React 18 (functional components only) |
| **Language** | TypeScript 5 (strict mode) |
| **Build** | Vite 5 (HMR, path alias `@/`) |
| **Styling** | Tailwind CSS 3 + Shadcn UI (Radix) |
| **State** | Zustand 4 (global) + React Query 5 (server) + useState (local) |
| **Routing** | React Router v6 (client-side) |
| **HTTP** | Native Fetch API (NOT Axios) |
| **Charts** | Recharts 2 |
| **Icons** | Lucide React |
| **Immutability** | Immer (swarmStore only) |
| **Testing** | Vitest + Playwright |
| **Dev Port** | 3005 |
| **API Proxy** | `VITE_API_URL` -> `localhost:8000/api/v1` |

---

## 2. Module Summary

| Module | Path | Files | Description |
|--------|------|-------|-------------|
| **components/unified-chat** | `components/unified-chat/` | 68 | Main chat interface + agent-swarm sub-module |
| **components/ag-ui** | `components/ag-ui/` | 15 | AG-UI Protocol components (advanced, chat, hitl) |
| **components/DevUI** | `components/DevUI/` | 14 | Developer tools (event timeline, statistics) |
| **components/ui** | `components/ui/` | 16 | Shadcn UI base components (Button, Card, Dialog...) |
| **components/layout** | `components/layout/` | 4 | AppLayout, Header, Sidebar, UserMenu |
| **components/shared** | `components/shared/` | 4 | EmptyState, LoadingSpinner, StatusBadge |
| **components/auth** | `components/auth/` | 1 | ProtectedRoute |
| **pages** | `pages/` | 46 | Route-level page components (11 modules) |
| **hooks** | `hooks/` | 25 | Custom React hooks (SSE, chat, swarm, orchestration) |
| **stores** | `stores/` | 2+tests | Zustand feature stores (unifiedChat, swarm) |
| **store** | `store/` | 1 | Zustand auth store (persisted) |
| **api** | `api/` | 6+ | Fetch wrapper + domain endpoint modules |
| **types** | `types/` | 4 | TypeScript type definitions |
| **utils** | `utils/` | 1 | guestUser utility |
| **lib** | `lib/` | 1 | Tailwind merge helper `cn()` |

**Total: ~236 TypeScript files**

---

## 3. Top Files by LOC

| # | File | LOC | Role |
|---|------|-----|------|
| 1 | `pages/UnifiedChat.tsx` | 1,403 | Main chat page orchestrator |
| 2 | `hooks/useUnifiedChat.ts` | 1,313 | AG-UI SSE hook (event handler, state sync) |
| 3 | `hooks/useSwarmMock.ts` | 623 | Mock swarm data for testing |
| 4 | `hooks/useSwarmReal.ts` | 603 | Real swarm SSE connection |
| 5 | `stores/unifiedChatStore.ts` | 508 | Chat Zustand store |
| 6 | `types/unified-chat.ts` | 505 | Chat type definitions |
| 7 | `types/ag-ui.ts` | 457 | AG-UI Protocol types |
| 8 | `stores/swarmStore.ts` | 444 | Swarm Zustand store (immer) |
| 9 | `store/authStore.ts` | 322 | Auth Zustand store (persisted) |
| 10 | `hooks/useSSEChat.ts` | 212 | Pipeline SSE hook (fetch ReadableStream) |

> The top 2 files alone (UnifiedChat.tsx + useUnifiedChat.ts) account for ~2,716 LOC -- roughly 5% of the total codebase but nearly all the business logic.

---

## 4. Route Map (App.tsx)

```
/login                -> LoginPage (standalone)
/signup               -> SignupPage (standalone)
/ag-ui-demo           -> AGUIDemoPage (standalone)
/swarm-test           -> SwarmTestPage (standalone)

/ [ProtectedRoute + AppLayout]
  /dashboard          -> DashboardPage
  /chat               -> UnifiedChat          *** PRIMARY PAGE ***
  /performance        -> PerformancePage
  /workflows          -> WorkflowsPage
  /workflows/new      -> CreateWorkflowPage
  /workflows/:id      -> WorkflowDetailPage
  /workflows/:id/edit -> EditWorkflowPage
  /workflows/:id/editor -> WorkflowEditorPage (DAG editor, Phase 34)
  /agents             -> AgentsPage
  /agents/new         -> CreateAgentPage
  /agents/:id         -> AgentDetailPage
  /agents/:id/edit    -> EditAgentPage
  /templates          -> TemplatesPage
  /sessions           -> SessionsPage (Phase 40)
  /sessions/:id       -> SessionDetailPage
  /tasks              -> TaskDashboardPage (Phase 40)
  /tasks/:id          -> TaskDetailPage
  /knowledge          -> KnowledgePage (Phase 40)
  /memory             -> MemoryPage (Phase 40)
  /approvals          -> ApprovalsPage
  /audit              -> AuditPage
  /devui              -> DevUILayout (nested)
    /devui/ag-ui-test -> AGUITestPanel
    /devui/traces     -> TraceList
    /devui/traces/:id -> TraceDetail
    /devui/monitor    -> LiveMonitor
    /devui/settings   -> DevUISettings
  *                   -> redirect to /dashboard
```

**30 routes total** (4 standalone + 26 protected under AppLayout).

---

## 5. Component Hierarchy (UnifiedChat Page)

The `/chat` route renders `UnifiedChat`, the single most complex page in the application.

```
UnifiedChat (1,403 LOC page orchestrator)
├── ChatHistoryPanel          -- Left sidebar: thread list + session resume
│   └── ChatHistoryToggleButton
├── ChatHeader                -- Mode toggle, connection status, title
├── <main> flex container
│   ├── ChatArea              -- Message list + streaming display
│   │   ├── MessageList
│   │   │   ├── MessageBubble (per message)
│   │   │   │   ├── IntentStatusChip     -- orchestration metadata display
│   │   │   │   ├── ApprovalMessageCard  -- inline HITL approval (Sprint 99)
│   │   │   │   ├── FileMessage          -- file attachment rendering
│   │   │   │   ├── ToolCallTracker      -- tool call status cards
│   │   │   │   └── CustomUIRenderer     -- AG-UI Generative UI components
│   │   │   │       ├── DynamicForm
│   │   │   │       ├── DynamicChart
│   │   │   │       ├── DynamicCard
│   │   │   │       └── DynamicTable
│   │   │   └── StreamingIndicator
│   │   └── InlineApproval (legacy)
│   ├── WorkflowSidePanel     -- Right panel (workflow mode only)
│   │   ├── StepProgressEnhanced
│   │   ├── ToolCallTracker
│   │   └── CheckpointList
│   ├── AgentSwarmPanel        -- Right panel (swarm mode, xl: breakpoint)
│   │   ├── SwarmHeader
│   │   ├── OverallProgress
│   │   └── WorkerCardList
│   │       └── WorkerCard (per worker)
│   ├── WorkerDetailDrawer     -- Slide-over drawer for worker details
│   │   ├── WorkerDetailHeader
│   │   ├── CurrentTask
│   │   ├── ExtendedThinkingPanel
│   │   ├── ToolCallsPanel
│   │   │   └── ToolCallItem
│   │   ├── MessageHistory
│   │   └── CheckpointPanel
│   └── OrchestrationPanel     -- Collapsible debug panel (Phase 28)
├── MemoryHint                 -- mem0 related memories display
├── Mode Selector Buttons      -- chat | workflow | swarm toggle
├── ChatInput                  -- Message input + file attachments
│   ├── AttachmentPreview
│   └── FileUpload
└── StatusBar                  -- Mode, risk, metrics, checkpoint, heartbeat
```

---

## 6. State Management Architecture

### 6.1 Three-Layer State Model

```
Layer 1: React Query 5 (TanStack)
  └── Server state: agents, workflows, sessions, tasks, knowledge
  └── Cache invalidation, background refetch, pagination

Layer 2: Zustand 4 (Global State)
  ├── authStore (store/)         -- user, token, refreshToken
  │   └── persist middleware -> localStorage('ipa-auth-storage')
  ├── unifiedChatStore (stores/) -- messages, mode, approvals, metrics
  │   └── persist middleware -> localStorage('unified-chat-storage')
  │   └── devtools middleware
  │   └── partialize: last 100 messages + 20 checkpoints
  └── swarmStore (stores/)       -- swarmStatus, workers, drawer
      └── immer middleware (mutable drafts)
      └── devtools middleware

Layer 3: useState / useRef (Component-Local)
  └── UnifiedChat.tsx alone has 20+ useState calls
  └── Typewriter animation, pipeline mode, pending approval, etc.
```

### 6.2 Store Details

| Store | File | Middleware | Persistence | Key State |
|-------|------|-----------|-------------|-----------|
| `useAuthStore` | `store/authStore.ts` | persist | `ipa-auth-storage` | user, token, refreshToken, isAuthenticated |
| `useUnifiedChatStore` | `stores/unifiedChatStore.ts` | persist + devtools | `unified-chat-storage` | messages (100 cap), mode, threadId, workflowState, checkpoints (20 cap) |
| `useSwarmStore` | `stores/swarmStore.ts` | immer + devtools | none | swarmStatus, workers[], selectedWorkerDetail, drawerState |

### 6.3 State Flow Diagram

```
User Input (ChatInput)
    │
    ▼
UnifiedChat.handleSend()
    │
    ├── [orchestrationEnabled=true] ──► useSSEChat.sendSSE()
    │       │                              │
    │       │   POST /orchestrator/chat/stream
    │       │                              │
    │       │   ◄── SSE events ────────────┘
    │       │   onTextDelta → setMessages(...)
    │       │   onRoutingComplete → orchMetadata
    │       │   onSwarmWorkerStart → useSwarmStore.getState().addWorker()
    │       │   onSwarmProgress → useSwarmStore.getState().updateWorkerProgress()
    │       │   onPipelineComplete → final message + metadata
    │       │
    │       └── messagesRef.current (bypass React state cycle)
    │
    └── [orchestrationEnabled=false] ──► useUnifiedChat.sendMessage()
            │
            │   EventSource GET /api/v1/ag-ui/run
            │
            │   ◄── SSE events (AG-UI Protocol)
            │   TEXT_MESSAGE_START/CONTENT/END
            │   TOOL_CALL_START/ARGS/END
            │   STATE_SNAPSHOT/DELTA
            │   CUSTOM (APPROVAL_REQUIRED, TOKEN_UPDATE, etc.)
            │
            └── setMessages() + storeAddMessage() (dual write)
```

---

## 7. Dual SSE Transport Mechanisms

The frontend has **two independent SSE implementations** that coexist:

### 7.1 AG-UI EventSource (GET) -- `useUnifiedChat.ts`

| Attribute | Value |
|-----------|-------|
| **Transport** | `new EventSource(url)` (browser native) |
| **HTTP Method** | GET |
| **Endpoint** | `/api/v1/ag-ui/run?thread_id=X&session_id=Y` |
| **Event Types** | 15 AG-UI events (RUN_STARTED, TEXT_MESSAGE_*, TOOL_CALL_*, STATE_*, CUSTOM) |
| **Reconnect** | Auto-reconnect with exponential backoff (3s base, 5 max attempts) |
| **Auth** | Query params (no headers on EventSource) |
| **State Target** | `useUnifiedChatStore` (dual-write: local state + Zustand) |
| **LOC** | ~600 lines in useUnifiedChat.ts |

### 7.2 Pipeline Fetch ReadableStream (POST) -- `useSSEChat.ts`

| Attribute | Value |
|-----------|-------|
| **Transport** | `fetch() + response.body.getReader()` |
| **HTTP Method** | POST |
| **Endpoint** | `/api/v1/orchestrator/chat/stream` |
| **Event Types** | 12 pipeline events (PIPELINE_START, ROUTING_COMPLETE, TEXT_DELTA, SWARM_*, etc.) |
| **Reconnect** | None (single request lifecycle) |
| **Auth** | Bearer token + X-Guest-Id headers |
| **State Target** | Direct `setMessages()` via `messagesRef.current` |
| **LOC** | 212 lines in useSSEChat.ts |
| **Abort** | `AbortController` for cancellation |

### 7.3 Selection Logic

In `UnifiedChat.handleSend()`:

```typescript
if (orchestrationEnabled) {
  // Pipeline SSE path (Phase 41+, default=true)
  await sendSSE(request, handlers);
} else {
  // AG-UI SSE path (Phase 16 legacy)
  sendMessage(content, fileIds);
}
```

`orchestrationEnabled` defaults to `true` and is never toggled in current UI, making the Pipeline SSE path the **de facto production path**. The AG-UI EventSource path is retained as fallback.

---

## 8. API Layer

### 8.1 Fetch Wrapper (`api/client.ts`)

```typescript
fetchApi<T>(endpoint, options?) -> Promise<T>
  ├── Auto-injects Authorization: Bearer {token}
  ├── Auto-injects X-Guest-Id header (sandbox isolation)
  ├── Handles 401 -> logout + redirect to /login
  ├── Handles 204 No Content -> {}
  └── Throws ApiError(message, status, details)

export const api = {
  get:    <T>(endpoint) => fetchApi<T>(endpoint),
  post:   <T>(endpoint, body?) => fetchApi<T>(endpoint, { method:'POST', body }),
  put:    <T>(endpoint, body) => fetchApi<T>(endpoint, { method:'PUT', body }),
  patch:  <T>(endpoint, body) => fetchApi<T>(endpoint, { method:'PATCH', body }),
  delete: <T>(endpoint) => fetchApi<T>(endpoint, { method:'DELETE' }),
};
```

### 8.2 Endpoint Modules (`api/endpoints/`)

| Module | Key Functions |
|--------|--------------|
| `ag-ui.ts` | AG-UI session/event endpoints |
| `files.ts` | File upload/download |
| `orchestration.ts` | Orchestration pipeline endpoints |
| `memory.ts` | mem0 memory search/CRUD |
| `sessions.ts` | Session management + message history |

### 8.3 Guest User Isolation

```
utils/guestUser.ts
  ├── getOrCreateGuestUserId() -> localStorage('ipa_guest_user_id')
  ├── getGuestHeaders() -> { 'X-Guest-Id': id }
  ├── migrateGuestData(token) -> POST /api/v1/auth/migrate-guest
  └── clearGuestUserId()
```

Unauthenticated users get a UUID-based guest ID. On login, guest data is migrated to the authenticated user's scope.

---

## 9. TypeScript Type System

### 9.1 Type Files

| File | LOC | Scope |
|------|-----|-------|
| `types/ag-ui.ts` | 457 | AG-UI protocol types: events, messages, tools, approvals, shared state, predictions |
| `types/unified-chat.ts` | 505 | Chat UI types: modes, workflows, metrics, component props, hook returns |
| `types/index.ts` | ~50 | Core shared types (Agent, Workflow, Execution) |
| `types/devtools.ts` | ~80 | DevTools event types |
| `agent-swarm/types/index.ts` | 180 | Swarm UI types: WorkerSummary, WorkerDetail, SwarmStatus, component props |
| `agent-swarm/types/events.ts` | ~170 | Swarm SSE event payloads (snake_case) |

### 9.2 Swarm Type Duality (camelCase vs snake_case)

The swarm module maintains a deliberate two-layer type system:

```
SSE Events (snake_case)           UI Components (camelCase)
─────────────────────────         ──────────────────────────
events.ts                         types/index.ts
  SwarmCreatedPayload               UIAgentSwarmStatus
    swarm_id                          swarmId
    session_id                        sessionId
    workers[]                         workers[]
      worker_id                         workerId
      worker_name                       workerName
      worker_type                       workerType
      tool_calls_count                  toolCallsCount
```

The `useSwarmEventHandler` hook bridges these two worlds, converting snake_case SSE payloads to camelCase UI types when updating the Zustand store.

A `SnakeToCamelCase<S>` utility type exists in `types/index.ts` but is **not used in runtime code** -- conversion is done manually in each event handler.

---

## 10. Mock vs Real Patterns (Swarm)

### 10.1 Architecture

```
SwarmTestPage (/swarm-test)
├── useSwarmMock (623 LOC)   -- Full local state, no backend
│   ├── useState for swarmStatus, selectedWorker, drawer
│   ├── Preset scenarios: ETL, SecurityAudit, DataPipeline
│   ├── Granular actions: addThinking, addToolCall, setWorkerProgress
│   └── MockMessage[] for simulated chat
│
└── useSwarmReal (603 LOC)   -- SSE connection to demo endpoint
    ├── useState for swarmStatus, selectedWorker, drawer
    ├── EventSource to /api/v1/swarm/demo/{swarmId}/events
    ├── DemoScenario selection API
    └── Converts snake_case events to camelCase state

UnifiedChat (/chat)
└── useSwarmStore (Zustand)  -- Production path
    ├── SSE handlers in UnifiedChat.tsx call useSwarmStore.getState()
    └── AgentSwarmPanel reads from useSwarmStore
```

### 10.2 Critical Issue: H-08 SwarmStore Bypass

**Both `useSwarmMock` and `useSwarmReal` maintain their own local `useState` instead of using `useSwarmStore`.**

This creates three independent state trees for swarm data:

| Path | State Source | Used By |
|------|-------------|---------|
| `/chat` (production) | `useSwarmStore` (Zustand) | UnifiedChat + AgentSwarmPanel |
| `/swarm-test` mock mode | `useSwarmMock` local state | SwarmTestPage |
| `/swarm-test` real mode | `useSwarmReal` local state | SwarmTestPage |

The mock/real hooks duplicate ~1,200 LOC of state management that the swarmStore already provides. They were written before the store existed (Phase 29) and never refactored.

---

## 11. Hook Inventory

| Hook | File | LOC | Purpose |
|------|------|-----|---------|
| `useUnifiedChat` | `useUnifiedChat.ts` | 1,313 | AG-UI SSE + message + approval orchestration |
| `useSSEChat` | `useSSEChat.ts` | 212 | Pipeline SSE (fetch ReadableStream) |
| `useSwarmMock` | `useSwarmMock.ts` | 623 | Mock swarm for testing |
| `useSwarmReal` | `useSwarmReal.ts` | 603 | Real swarm SSE demo |
| `useAGUI` | `useAGUI.ts` | ~400 | Low-level AG-UI hook (superseded by useUnifiedChat) |
| `useHybridMode` | `useHybridMode.ts` | ~200 | MAF/Claude SDK mode detection |
| `useOrchestration` | `useOrchestration.ts` | ~350 | Phase 28 orchestration (partially superseded) |
| `useOrchestratorChat` | `useOrchestratorChat.ts` | ~200 | Orchestrator chat integration |
| `useApprovalFlow` | `useApprovalFlow.ts` | ~150 | HITL approval workflow |
| `useExecutionMetrics` | `useExecutionMetrics.ts` | ~100 | Timer + token tracking |
| `useFileUpload` | `useFileUpload.ts` | ~200 | File upload queue management |
| `useChatThreads` | `useChatThreads.ts` | ~200 | Thread CRUD (localStorage) |
| `useCheckpoints` | `useCheckpoints.ts` | ~100 | Checkpoint management |
| `useSharedState` | `useSharedState.ts` | ~100 | AG-UI shared state |
| `useOptimisticState` | `useOptimisticState.ts` | ~100 | Optimistic UI updates |
| `useDevTools` | `useDevTools.ts` | ~150 | DevUI data fetching |
| `useDevToolsStream` | `useDevToolsStream.ts` | ~100 | DevUI SSE streaming |
| `useEventFilter` | `useEventFilter.ts` | ~80 | Event filtering |
| `useKnowledge` | `useKnowledge.ts` | ~150 | Knowledge base CRUD |
| `useMemory` | `useMemory.ts` | ~150 | mem0 memory operations |
| `useSessions` | `useSessions.ts` | ~150 | Session management |
| `useTasks` | `useTasks.ts` | ~150 | Task dashboard |
| `useToolCallEvents` | `useToolCallEvents.ts` | ~100 | Tool call event tracking |
| `useTypewriterEffect` | `useTypewriterEffect.ts` | ~80 | Text animation |

**25 hooks total**, with `useUnifiedChat` being the central orchestrator.

---

## 12. Known Issues

### 12.1 Critical / High

| ID | Severity | Title | Detail |
|----|----------|-------|--------|
| **H-08** | HIGH | Swarm store bypass | `useSwarmMock` and `useSwarmReal` maintain independent `useState` trees instead of using `useSwarmStore`. ~1,200 LOC of duplicated state logic. The production path (`/chat`) uses the store correctly. |
| **H-09** | HIGH | UnifiedChat.tsx monolith | 1,403 LOC single component with 20+ useState, 15+ useCallback, 10+ useEffect. Mixes pipeline SSE event handling (inline in handleSend), swarm store manipulation via `getState()`, typewriter animation, file upload, orchestration, memory search, and HITL approval in one file. |
| **H-10** | HIGH | Dual-write state inconsistency | `useUnifiedChat` writes to both local `useState` AND `useUnifiedChatStore` (Zustand) for every message/tool-call/approval. If either path fails or diverges, the UI and persisted state become inconsistent. |

### 12.2 Medium

| ID | Severity | Title | Detail |
|----|----------|-------|--------|
| **M-01** | MEDIUM | Page monolith | UnifiedChat.tsx should be decomposed into sub-hooks: `usePipelineSSE`, `useSwarmSSEBridge`, `useThreadManagement`, `useOrchestrationBridge`. |
| **M-02** | MEDIUM | Dual SSE transport | Two completely independent SSE mechanisms with different event schemas, reconnection strategies, and state targets. Should be unified behind a common transport abstraction. |
| **M-03** | MEDIUM | Inline fetch in JSX | The HITL approval buttons (lines 1205-1240) contain raw `fetch()` calls with inline `useAuthStore.getState()` -- should be extracted to a hook or API function. |
| **M-04** | MEDIUM | `messagesRef.current` pattern | Pipeline SSE path uses a mutable ref to track messages, bypassing React's state cycle. This works but creates an implicit contract that is fragile and hard to debug. |
| **M-05** | MEDIUM | Token estimation fallback | Frontend estimates tokens at ~3 chars/token when backend doesn't send TOKEN_UPDATE. This is inaccurate for Chinese text (~1.5-2 chars/token) and may mislead users. |
| **M-06** | MEDIUM | `useSwarmStore.getState()` in render | UnifiedChat.tsx calls `useSwarmStore.getState()` inside JSX event handlers and the render body (line 1296). While technically safe, it bypasses React's subscription model. |
| **M-07** | MEDIUM | Persisted message cap | `unifiedChatStore` persists only the last 100 messages. Users with longer conversations will lose earlier messages on page refresh without any warning. |

### 12.3 Low

| ID | Severity | Title | Detail |
|----|----------|-------|--------|
| **L-01** | LOW | Stale hook: `useAGUI` | The standalone `useAGUI.ts` hook is superseded by `useUnifiedChat` but still exists and is imported by `AGUIDemoPage`. |
| **L-02** | LOW | Stale hook: `useOrchestration` | Phase 28 orchestration hook is mostly superseded by SSE pipeline but retained for OrchestrationPanel debug view. |
| **L-03** | LOW | Two store directories | Auth lives in `store/` while feature stores live in `stores/`. Historical artifact, not a bug. |
| **L-04** | LOW | Unused `SnakeToCamelCase` type | Defined in `agent-swarm/types/index.ts` but conversion is done manually in handlers. |
| **L-05** | LOW | `void` suppression pattern | UnifiedChat.tsx uses `void _swarmReset;` and `void useSwarmStore;` to suppress unused-variable warnings. Indicates dead code paths. |
| **L-06** | LOW | Missing error boundaries | Only `ErrorBoundary.tsx` exists in unified-chat. No top-level error boundary in App.tsx or around major feature areas. |

---

## 13. Auth & Security

### 13.1 Authentication Flow

```
LoginPage
  └── authStore.login(email, password)
      ├── POST /api/v1/auth/login (OAuth2 form-encoded)
      ├── GET /api/v1/auth/me (with Bearer token)
      ├── Store token + user in Zustand (persist -> localStorage)
      └── migrateGuestData(token) (non-blocking)

ProtectedRoute
  └── Checks useAuthStore.isAuthenticated
      ├── true  -> render children (AppLayout + nested routes)
      └── false -> redirect to /login

fetchApi (api/client.ts)
  └── 401 response -> authStore.logout() + redirect /login
```

### 13.2 Token Storage

- Access token: Zustand persist -> `localStorage('ipa-auth-storage')`
- Refresh token: Same store, `refreshSession()` calls `/auth/refresh`
- Guest ID: `localStorage('ipa_guest_user_id')` -- UUID v4

---

## 14. Phase Evolution Timeline

| Phase | Sprint(s) | Contribution |
|-------|-----------|-------------|
| **Phase 2** | S5, S12 | App shell, API client, performance page |
| **Phase 15** | S60 | AG-UI Protocol types (Generative UI, Shared State, Predictions) |
| **Phase 16** | S62-63 | UnifiedChat core: layout, mode switching, store, persistence |
| **Phase 16** | S65-66 | Tool call tracking, reconnection, default tools |
| **Phase 16** | S67-68 | Heartbeat handling, history loading |
| **Phase 16** | S69 | Dashboard integration (h-full layout) |
| **Phase 18** | S71 | Auth system: login, signup, token interceptor, guest migration |
| **Phase 19** | S73-74 | Metrics fix, token estimation, chat history panel, thread mgmt |
| **Phase 19** | S75-76 | File upload, file download, attachment preview |
| **Phase 26** | S87 | DevUI developer tools (15 components) |
| **Phase 28** | S99 | Orchestration panel, inline approval cards, dialog flow |
| **Phase 29** | S100-105 | Agent Swarm: 15 components + 4 hooks + types + tests + store |
| **Phase 34** | S133 | Workflow DAG editor page |
| **Phase 40** | S138-140 | Sessions, Tasks, Knowledge, Memory pages |
| **Phase 41** | S143-144 | Pipeline mode selector, memory hints, typewriter effect |
| **Phase 42** | S145-146 | SSE streaming hook, swarm SSE integration, HITL approval |
| **Phase 42** | S147 | Knowledge sources in orchestration metadata |

---

## 15. Dependency Graph (Simplified)

```
App.tsx
  └── UnifiedChat.tsx
        ├── useUnifiedChat (hooks/)
        │     ├── useHybridMode
        │     ├── useUnifiedChatStore (stores/)
        │     └── AG-UI SSE EventSource
        ├── useSSEChat (hooks/)
        │     └── Pipeline fetch ReadableStream
        ├── useSwarmStore (stores/)
        │     └── immer middleware
        ├── useChatThreads (hooks/)
        │     └── localStorage
        ├── useOrchestration (hooks/)
        │     └── api/endpoints/orchestration
        ├── useExecutionMetrics (hooks/)
        ├── useFileUpload (hooks/)
        │     └── api/endpoints/files
        ├── useAuthStore (store/)
        │     └── persist -> localStorage
        ├── memoryApi (api/endpoints/memory)
        ├── sessionsApi (api/endpoints/sessions)
        └── filesApi (api/endpoints/files)
```

---

## 16. Testing Coverage

### 16.1 Existing Tests

| Area | Files | Framework |
|------|-------|-----------|
| Agent Swarm components | 9 test files | Vitest |
| Stores | `stores/__tests__/` | Vitest |
| E2E | Playwright config present | Playwright |

### 16.2 Test Gap Analysis

- **UnifiedChat.tsx** (1,403 LOC): No unit tests
- **useUnifiedChat.ts** (1,313 LOC): No unit tests
- **useSSEChat.ts** (212 LOC): No unit tests
- **authStore.ts** (322 LOC): No unit tests visible
- **api/client.ts** (172 LOC): No unit tests visible
- Swarm components have the best coverage (9 test files for 15 components)

---

## 17. Recommendations Summary

| Priority | Action | Effort | Impact |
|----------|--------|--------|--------|
| **P1** | Decompose `UnifiedChat.tsx` into sub-hooks | High | Maintainability, testability |
| **P1** | Refactor `useSwarmMock`/`useSwarmReal` to use `useSwarmStore` | Medium | Eliminate 1,200 LOC duplication |
| **P2** | Unify dual SSE transports behind common abstraction | High | Architecture consistency |
| **P2** | Extract inline fetch calls from JSX to proper API functions | Low | Code quality |
| **P2** | Add unit tests for top-5 files | Medium | Reliability |
| **P3** | Fix token estimation for Chinese text | Low | UX accuracy |
| **P3** | Add top-level ErrorBoundary in App.tsx | Low | Resilience |
| **P3** | Consolidate `store/` and `stores/` directories | Low | Organization |

---

*Analysis conducted on 2026-03-29 based on source reading of 14 key files.*
*V9 Layer 01 -- Frontend Architecture Report*

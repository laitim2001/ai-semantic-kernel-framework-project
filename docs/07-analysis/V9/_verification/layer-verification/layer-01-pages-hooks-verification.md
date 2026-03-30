# V9 Layer 01 — Pages, Hooks, API, Stores, Types, Utils, Lib Verification

> **Verification Date**: 2026-03-29
> **Method**: Full source reading of every .ts/.tsx file in target directories
> **Verified By**: Claude Opus 4.6 (1M context) — line-by-line code review
> **Total Files Read**: 90 files across 8 directories

---

## Table of Contents

1. [Pages Verification (45 files)](#1-pages-verification)
2. [Hooks Verification (25 files)](#2-hooks-verification)
3. [API Verification (11 files)](#3-api-verification)
4. [Stores Verification (3+1 files)](#4-stores-verification)
5. [Types Verification (4 files)](#5-types-verification)
6. [Utils Verification (1 file)](#6-utils-verification)
7. [Lib Verification (1 file)](#7-lib-verification)
8. [App.tsx Route Map (Complete)](#8-apptsx-route-map)
9. [Cross-Reference & Corrections](#9-cross-reference--corrections)

---

## 1. Pages Verification

### 1.1 Dashboard Module (6 files)

| File | Component | LOC | Route | Hooks Consumed | API Calls | Key Patterns |
|------|-----------|-----|-------|----------------|-----------|--------------|
| `DashboardPage.tsx` | `DashboardPage` | 87 | `/dashboard` | useQuery | `GET /dashboard/stats` | TanStack Query, StatsCards/ExecutionChart/RecentExecutions/PendingApprovals sub-components |
| `PerformancePage.tsx` | `PerformancePage` | 469 | `/performance` | useState, useQuery | `GET /performance/metrics?range=` | Recharts (AreaChart, LineChart), mock fallback, 30s refetch, MetricCard/FeatureStatCard/RecommendationCard sub-components |
| `components/StatsCards.tsx` | `StatsCards` | 75 | (sub) | — | — | 4 stat cards (total executions, success rate, pending approvals, LLM cost), lucide-react icons |
| `components/ExecutionChart.tsx` | `ExecutionChart` | 104 | (sub) | useQuery | `GET /dashboard/executions/chart` | Recharts LineChart, mock fallback |
| `components/PendingApprovals.tsx` | `PendingApprovals` | 99 | (sub) | useQuery | `GET /checkpoints/pending?limit=5` | Links to `/approvals`, mock fallback |
| `components/RecentExecutions.tsx` | `RecentExecutions` | 108 | (sub) | useQuery | `GET /executions/?page=1&page_size=10` | Table, StatusBadge, mock fallback |
| `components/index.ts` | barrel export | 9 | — | — | — | Re-exports 4 components |

### 1.2 Agents Module (4 files)

| File | Component | LOC | Route | Hooks Consumed | API Calls | Key Patterns |
|------|-----------|-----|-------|----------------|-----------|--------------|
| `AgentsPage.tsx` | `AgentsPage` | 189 | `/agents` | useState, useQuery | `GET /agents/?search=` | Grid layout, search, Badge, StatusBadge, mock fallback |
| `AgentDetailPage.tsx` | `AgentDetailPage` | 314 | `/agents/:id` | useState, useRef, useEffect, useParams, useQuery, useMutation | `GET /agents/:id`, `POST /agents/:id/run` | Chat test interface with message bubbles, loading animation |
| `CreateAgentPage.tsx` | `CreateAgentPage` | 1015 | `/agents/new` | useState, useNavigate, useMutation | `POST /agents` | Multi-step wizard (5 steps), multi-provider model selection (Azure/OpenAI/Anthropic/Google/Local) |
| `EditAgentPage.tsx` | `EditAgentPage` | 958 | `/agents/:id/edit` | useState, useEffect, useNavigate, useParams, useQuery, useMutation, useQueryClient | `GET /agents/:id`, `PUT /agents/:id`, `DELETE /agents/:id` | Pre-filled form, multi-provider model config |

### 1.3 Workflows Module (5 files)

| File | Component | LOC | Route | Hooks Consumed | API Calls | Key Patterns |
|------|-----------|-----|-------|----------------|-----------|--------------|
| `WorkflowsPage.tsx` | `WorkflowsPage` | 166 | `/workflows` | useState, useQuery | `GET /workflows/?search=` | Grid, search, StatusBadge, mock fallback |
| `WorkflowDetailPage.tsx` | `WorkflowDetailPage` | 355 | `/workflows/:id` | useState, useParams, useQuery, useMutation, useQueryClient | `GET /workflows/:id`, `GET /executions/?workflow_id=`, `POST /workflows/:id/execute`, `POST /workflows/:id/activate`, `POST /workflows/:id/deactivate` | Execute dialog, activate/deactivate toggle, execution history, DAG Editor link |
| `CreateWorkflowPage.tsx` | `CreateWorkflowPage` | 887 | `/workflows/new` | useState, useNavigate, useQuery, useMutation | `POST /workflows`, `GET /agents` | Multi-step wizard (5 steps), node/edge visual config |
| `EditWorkflowPage.tsx` | `EditWorkflowPage` | 1040 | `/workflows/:id/edit` | useState, useEffect, useNavigate, useParams, useQuery, useMutation, useQueryClient | `GET /workflows/:id`, `PUT /workflows/:id`, `GET /agents` | Pre-filled workflow editor |
| `WorkflowEditorPage.tsx` | `WorkflowEditorPage` | 21 | `/workflows/:id/editor` | useParams | — | Thin wrapper for `WorkflowCanvas` (React Flow) |

### 1.4 Auth Module (2 files)

| File | Component | LOC | Route | Hooks Consumed | API Calls | Key Patterns |
|------|-----------|-----|-------|----------------|-----------|--------------|
| `LoginPage.tsx` | `LoginPage` | 209 | `/login` | useState, useNavigate, useLocation, useAuthStore | (via authStore) `POST /auth/login`, `GET /auth/me` | Email/password form, validation, redirect from ProtectedRoute |
| `SignupPage.tsx` | `SignupPage` | 273 | `/signup` | useState, useNavigate, useAuthStore | (via authStore) `POST /auth/register`, `GET /auth/me` | Email/password/name form, confirm password, validation |

### 1.5 Approvals Module (1 file)

| File | Component | LOC | Route | Hooks Consumed | API Calls |
|------|-----------|-----|-------|----------------|-----------|
| `ApprovalsPage.tsx` | `ApprovalsPage` | 239 | `/approvals` | useState, useQuery, useMutation, useQueryClient | `GET /checkpoints/pending`, `POST /checkpoints/:id/approve`, `POST /checkpoints/:id/reject` |

### 1.6 Audit Module (1 file)

| File | Component | LOC | Route | Hooks Consumed | API Calls |
|------|-----------|-----|-------|----------------|-----------|
| `AuditPage.tsx` | `AuditPage` | 162 | `/audit` | useState, useQuery | `GET /audit/logs?search=` |

### 1.7 Templates Module (1 file)

| File | Component | LOC | Route | Hooks Consumed | API Calls |
|------|-----------|-----|-------|----------------|-----------|
| `TemplatesPage.tsx` | `TemplatesPage` | 230 | `/templates` | useState, useQuery | `GET /templates/?search=&category=` |

### 1.8 Sessions Module (2 files, Phase 40)

| File | Component | LOC | Route | Hooks Consumed | API Calls |
|------|-----------|-----|-------|----------------|-----------|
| `SessionsPage.tsx` | `SessionsPage` | 259 | `/sessions` | useState, useNavigate, useSessions, useResumeSession, useDeleteSession | `GET /sessions`, `POST /sessions/:id/resume`, `DELETE /sessions/:id` |
| `SessionDetailPage.tsx` | `SessionDetailPage` | 280 | `/sessions/:id` | useParams, useNavigate, useSession, useSessionMessages, useResumeSession | `GET /sessions/:id`, `GET /sessions/:id/messages`, `POST /sessions/:id/resume` |

### 1.9 Tasks Module (2 files, Phase 40)

| File | Component | LOC | Route | Hooks Consumed | API Calls |
|------|-----------|-----|-------|----------------|-----------|
| `TaskDashboardPage.tsx` | `TaskDashboardPage` | 330 | `/tasks` | useState, useNavigate, useTasks, useCancelTask, useRetryTask | `GET /tasks`, `POST /tasks/:id/cancel`, `POST /tasks/:id/retry` |
| `TaskDetailPage.tsx` | `TaskDetailPage` | 315 | `/tasks/:id` | useParams, useNavigate, useTask, useTaskSteps, useCancelTask, useRetryTask | `GET /tasks/:id`, `GET /tasks/:id/steps`, `POST /tasks/:id/cancel`, `POST /tasks/:id/retry` |

### 1.10 Knowledge Module (1 file, Phase 40)

| File | Component | LOC | Route | Hooks Consumed | API Calls |
|------|-----------|-----|-------|----------------|-----------|
| `KnowledgePage.tsx` | `KnowledgePage` | 400 | `/knowledge` | useState, useRef, useDocuments, useKnowledgeSearch, useUploadDocument, useDeleteDocument, useSkills, useKnowledgeStatus | `GET /knowledge/documents`, `POST /knowledge/search`, `POST /knowledge/upload`, `DELETE /knowledge/documents/:id`, `GET /knowledge/skills`, `GET /knowledge/status` |

### 1.11 Memory Module (1 file, Phase 40)

| File | Component | LOC | Route | Hooks Consumed | API Calls |
|------|-----------|-----|-------|----------------|-----------|
| `MemoryPage.tsx` | `MemoryPage` | 289 | `/memory` | useState, useMemorySearch, useUserMemories, useMemoryStats, useDeleteMemory | `POST /memory/search`, `GET /memory/users/:id`, `GET /memory/stats`, `DELETE /memory/:id` |

### 1.12 AG-UI Demo Module (8 files)

| File | Component | LOC | Route | Key Patterns |
|------|-----------|-----|-------|--------------|
| `AGUIDemoPage.tsx` | `AGUIDemoPage` | 200 | `/ag-ui-demo` | 7 tabbed demos, EventLogPanel, standalone full-screen |
| `components/index.ts` | barrel export | 41 | — | Exports 7 demo + EventLogPanel |
| `components/AgenticChatDemo.tsx` | `AgenticChatDemo` | 109 | (tab) | Wraps ChatContainer, message/approval callbacks |
| `components/ToolRenderingDemo.tsx` | `ToolRenderingDemo` | 158 | (tab) | 4 sample tool calls, ToolCallCard |
| `components/HITLDemo.tsx` | `HITLDemo` | 178 | (tab) | 4 risk levels, ApprovalDialog/ApprovalList |
| `components/GenerativeUIDemo.tsx` | `GenerativeUIDemo` | 228 | (tab) | Progress steps simulation, useEffect animation |
| `components/ToolUIDemo.tsx` | `ToolUIDemo` | 174 | (tab) | DynamicForm/Chart/Card/Table |
| `components/SharedStateDemo.tsx` | `SharedStateDemo` | 201 | (tab) | Counter, text, items list, server update simulation |
| `components/PredictiveDemo.tsx` | `PredictiveDemo` | 251 | (tab) | Task list, optimistic toggle, rollback simulation |
| `components/EventLogPanel.tsx` | `EventLogPanel` | 193 | (panel) | Real-time event log, filter, auto-scroll, pause |

### 1.13 DevUI Module (7 files)

| File | Component | LOC | Route | Hooks Consumed | Key Patterns |
|------|-----------|-----|-------|----------------|--------------|
| `Layout.tsx` | `DevUILayout` | 166 | `/devui` (layout) | useLocation | Sidebar nav (5 items), breadcrumbs, Outlet |
| `index.tsx` | `DevUIOverview` | 216 | `/devui` (index) | useTraces | Stat cards, quick links, recent activity |
| `AGUITestPanel.tsx` | `AGUITestPanel` | 461 | `/devui/ag-ui-test` | useState, useCallback | 7 AG-UI features, test endpoints, thread ID input |
| `TraceList.tsx` | `TraceList` | 304 | `/devui/traces` | useState, useMemo, useTraces | Table, status filter, workflow filter, pagination |
| `TraceDetail.tsx` | `TraceDetail` | 563 | `/devui/traces/:id` | useState, useParams, useNavigate, useTrace, useTraceEvents, useDeleteTrace, useEventFilter | 4 view modes (timeline/tree/list/stats), EventFilter, EventPanel, delete modal |
| `LiveMonitor.tsx` | `LiveMonitor` | 67 | `/devui/monitor` | — | Placeholder (Coming Soon) |
| `Settings.tsx` | `Settings` | 67 | `/devui/settings` | — | Placeholder (Coming Soon) |

### 1.14 Standalone Pages (2 files)

| File | Component | LOC | Route | Hooks Consumed | Key Patterns |
|------|-----------|-----|-------|----------------|--------------|
| `UnifiedChat.tsx` | `UnifiedChat` | 1403 | `/chat` | useUnifiedChat, useExecutionMetrics, useChatThreads, useFileUpload, useOrchestration, useSSEChat, useSwarmStore, useAuthStore | Main chat page, ChatArea/ChatInput/ChatHeader/StatusBar/OrchestrationPanel/ChatHistoryPanel/AgentSwarmPanel/WorkerDetailDrawer/MemoryHint, DEFAULT_TOOLS (Read/Bash/Edit/Write/Glob/Grep), SSE streaming |
| `SwarmTestPage.tsx` | `SwarmTestPage` | 845 | `/swarm-test` | useState, useCallback, useSwarmMock, useSwarmReal | Mock/Real mode switch, 3 preset scenarios, worker controls, chat panel, AgentSwarmPanel |

---

## 2. Hooks Verification

### 25 files (24 hooks + 1 index)

| # | File | Hook Name | LOC (est) | useState | useEffect | External Dependencies | Key Purpose |
|---|------|-----------|-----------|----------|-----------|----------------------|-------------|
| 1 | `index.ts` | (barrel) | 144 | — | — | — | Central export for all hooks |
| 2 | `useAGUI.ts` | `useAGUI` | ~600 | 8+ | 3+ | useSharedState, useOptimisticState, EventSource | AG-UI protocol: SSE, messages, tool calls, approvals, shared+optimistic state |
| 3 | `useApprovalFlow.ts` | `useApprovalFlow` | 461 | 4 | 2 | aguiApi | HITL approval flow, pending approvals, dialog, timeout, mode switch |
| 4 | `useCheckpoints.ts` | `useCheckpoints` | 368 | 5 | 1 | aguiApi | Checkpoint CRUD, restore with confirmation |
| 5 | `useDevTools.ts` | `useTraces/useTrace/useTraceEvents/useDeleteTrace` | ~100 | 0 | 0 | useQuery, useMutation, devToolsApi | React Query wrappers for DevTools API |
| 6 | `useDevToolsStream.ts` | `useDevToolsStream` | ~200 | 6+ | 2+ | EventSource | SSE streaming for real-time trace events |
| 7 | `useEventFilter.ts` | `useEventFilter` | ~200 | 5+ | 2+ | useSearchParams | Event type/severity/executor filtering with URL sync |
| 8 | `useExecutionMetrics.ts` | `useExecutionMetrics` | ~300 | 4+ | 2+ | — | Token/time/tool/message metrics with timer |
| 9 | `useFileUpload.ts` | `useFileUpload` | ~150 | 1 | 0 | uploadFile (files API) | File attachment: add/remove/upload/clear |
| 10 | `useHybridMode.ts` | `useHybridMode` | 270 | 5 | 3 | — | Chat/Workflow mode auto-detection + manual override, sessionStorage persistence |
| 11 | `useOptimisticState.ts` | `useOptimisticState` | 409 | 2 | 1 | — | Optimistic updates with prediction, confirm, rollback, timeout |
| 12 | `useSharedState.ts` | `useSharedState` | 506 | 5 | 3 | EventSource | Bidirectional state sync, conflict resolution, offline support, SSE |
| 13 | `useUnifiedChat.ts` | `useUnifiedChat` | ~800 | 8+ | 4+ | useUnifiedChatStore, useHybridMode, EventSource | Main chat orchestration: SSE lifecycle, AG-UI events, mode management, store sync |
| 14 | `useSwarmMock.ts` | `useSwarmMock` | ~400 | 5+ | 0 | — | Mock swarm state for UI testing, worker CRUD, scenarios |
| 15 | `useSwarmReal.ts` | `useSwarmReal` | ~350 | 6+ | 2+ | EventSource, fetch | Real swarm backend connection, SSE events, demo start/stop |
| 16 | `useOrchestration.ts` | `useOrchestration` | ~250 | 3+ | 0 | orchestrationApi | Three-layer intent routing, dialog, risk assessment, HITL, execution |
| 17 | `useKnowledge.ts` | `useKnowledgeSearch/useDocuments/useUploadDocument/useDeleteDocument/useSkills/useKnowledgeStatus` | ~120 | 0 | 0 | useQuery, useMutation, knowledgeApi | React Query wrappers for knowledge API |
| 18 | `useMemory.ts` | `useMemorySearch/useUserMemories/useMemoryStats/useDeleteMemory` | ~80 | 0 | 0 | useQuery, useMutation, memoryApi | React Query wrappers for memory API |
| 19 | `useOrchestratorChat.ts` | `useOrchestratorChat` | ~200 | 5+ | 2+ | orchestratorApi, EventSource | Orchestrator chat: send/receive, SSE streaming, metadata |
| 20 | `useSessions.ts` | `useSessions/useSession/useSessionMessages/useRecoverableSessions/useResumeSession/useDeleteSession` | ~100 | 0 | 0 | useQuery, useMutation, sessionsApi | React Query wrappers for session API |
| 21 | `useTasks.ts` | `useTasks/useTask/useTaskSteps/useCancelTask/useRetryTask` | ~100 | 0 | 0 | useQuery, useMutation, tasksApi | React Query wrappers for task API, auto-refetch for running tasks |
| 22 | `useChatThreads.ts` | `useChatThreads` | ~200 | 3+ | 2+ | useAuthStore, localStorage | Thread CRUD with localStorage persistence, user-isolated |
| 23 | `useSSEChat.ts` | `useSSEChat` | ~200 | 3+ | 0 | useAuthStore, guestUser, fetch + ReadableStream | POST-based SSE streaming for pipeline, 12 event types |
| 24 | `useTypewriterEffect.ts` | `useTypewriterEffect` | ~80 | 2 | 1 | requestAnimationFrame | Character-by-character text reveal, skip-to-end |
| 25 | `useToolCallEvents.ts` | `useToolCallEvents` | ~80 | 1 | 0 | — | Pipeline tool call -> TrackedToolCall mapping |

---

## 3. API Verification

### 11 files (1 core client + 1 devtools + 8 endpoint modules + 1 index)

| # | File | Exported Functions/Objects | Methods | Key Endpoints |
|---|------|--------------------------|---------|---------------|
| 1 | `client.ts` | `api` (get/post/put/patch/delete), `ApiError`, `API_BASE_URL` | GET/POST/PUT/PATCH/DELETE | Core Fetch wrapper with auth token, guest headers, 401 handling |
| 2 | `devtools.ts` | `devToolsApi` | 4 | `GET /devtools/traces`, `GET /devtools/traces/:id`, `GET /devtools/traces/:id/events`, `DELETE /devtools/traces/:id` |
| 3 | `endpoints/index.ts` | barrel export | — | Re-exports: aguiApi, filesApi, orchestratorApi, sessionsApi, tasksApi, knowledgeApi, memoryApi, orchestrationApi |
| 4 | `endpoints/ag-ui.ts` | `aguiApi` | 7+ | `POST /ag-ui/approve/:id`, `POST /ag-ui/reject/:id`, `GET /ag-ui/threads/:id`, `POST /ag-ui/threads`, `GET /ag-ui/checkpoints/:id`, `POST /ag-ui/checkpoints/:id/restore` |
| 5 | `endpoints/files.ts` | `filesApi`, `uploadFile`, `listFiles`, `getFile`, `deleteFile`, `getFileContentUrl`, utilities | 5+ | `POST /files/upload` (multipart), `GET /files`, `GET /files/:id`, `DELETE /files/:id`, `GET /files/:id/content` |
| 6 | `endpoints/orchestration.ts` | `orchestrationApi` | 7+ | `POST /orchestration/classify`, `POST /orchestration/dialog/start`, `POST /orchestration/dialog/respond`, `GET /orchestration/dialog/:id/status`, `POST /orchestration/risk/assess`, `GET /orchestration/approvals`, `POST /orchestration/approvals/:id`, `POST /orchestration/execute` |
| 7 | `endpoints/orchestrator.ts` | `orchestratorApi` | 3+ | `POST /orchestrator/chat`, `GET /orchestrator/health`, SSE: `POST /orchestrator/chat/stream` |
| 8 | `endpoints/sessions.ts` | `sessionsApi` | 6 | `GET /sessions`, `GET /sessions/:id`, `GET /sessions/:id/messages`, `GET /sessions/recoverable`, `POST /sessions/:id/resume`, `DELETE /sessions/:id` |
| 9 | `endpoints/tasks.ts` | `tasksApi` | 5 | `GET /tasks`, `GET /tasks/:id`, `GET /tasks/:id/steps`, `POST /tasks/:id/cancel`, `POST /tasks/:id/retry` |
| 10 | `endpoints/knowledge.ts` | `knowledgeApi` | 6 | `GET /knowledge/documents`, `POST /knowledge/search`, `POST /knowledge/upload` (multipart), `DELETE /knowledge/documents/:id`, `GET /knowledge/skills`, `GET /knowledge/status` |
| 11 | `endpoints/memory.ts` | `memoryApi` | 4 | `POST /memory/search`, `GET /memory/users/:id`, `GET /memory/stats`, `DELETE /memory/:id` |

---

## 4. Stores Verification

### 4 files (1 in `store/`, 2 in `stores/`, 1 test)

| # | File | Store Name | State Shape | Actions | Middleware | Persistence |
|---|------|-----------|-------------|---------|------------|-------------|
| 1 | `store/authStore.ts` | `useAuthStore` | `{ user, token, refreshToken, isAuthenticated, isLoading, error }` | login, register, logout, refreshSession, clearError, setLoading | `persist` (localStorage: `ipa-auth-storage`) | token, refreshToken, user, isAuthenticated |
| 2 | `stores/unifiedChatStore.ts` | `useUnifiedChatStore` | `{ threadId, sessionId, mode, autoMode, manualOverride, messages, isStreaming, streamingMessageId, workflowState, toolCalls, pendingApprovals, dialogApproval, checkpoints, currentCheckpoint, metrics, connection, error }` | setMode, setManualOverride, setAutoMode, addMessage, updateMessage, setMessages, setStreaming, clearMessages, clearPersistence, setWorkflowState, updateWorkflowStep, addToolCall, updateToolCall, addPendingApproval, removePendingApproval, setDialogApproval, addCheckpoint, setCurrentCheckpoint, updateMetrics, setConnection, setError, reset | `devtools` + `persist` (localStorage: `unified-chat-storage`, v1 migration, 100 msg limit) | threadId, sessionId, mode, manualOverride, autoMode, messages(100), workflowState, checkpoints(20) |
| 3 | `stores/swarmStore.ts` | `useSwarmStore` | `{ swarmStatus, selectedWorkerId, selectedWorkerDetail, isDrawerOpen, isLoading, error }` | setSwarmStatus, updateSwarmProgress, completeSwarm, addWorker, updateWorkerProgress, updateWorkerThinking, updateWorkerToolCall, completeWorker, selectWorker, setWorkerDetail, openDrawer, closeDrawer, setLoading, setError, reset | `devtools` + `immer` | None |
| 4 | `stores/__tests__/swarmStore.test.ts` | (test) | — | — | — | — |

---

## 5. Types Verification

### 4 files

| # | File | Exported Types/Interfaces | Field Count (approx) | Key Types |
|---|------|--------------------------|---------------------|-----------|
| 1 | `types/index.ts` | 15 types/interfaces | ~120 fields | `Status`, `PaginatedResponse<T>`, `Workflow`, `WorkflowDefinition`, `WorkflowGraphDefinition`, `WorkflowNode`, `WorkflowGraphNode`, `WorkflowEdge`, `WorkflowGraphEdge`, `Execution`, `ExecutionStep`, `Agent`, `ModelConfig`, `Template`, `Checkpoint`, `AuditLog`, `DashboardStats`, `ExecutionChartData`, `CostChartData` |
| 2 | `types/ag-ui.ts` | 50+ types/interfaces | ~300+ fields | `UIComponentType`, `ChartType`, `FormFieldType`, `FormFieldDefinition`, `TableColumnDefinition`, `ChartData`, `CardAction`, `AGUIEventType` (15 event types), `ChatMessage`, `ToolCallState`, `ToolCallStatus`, `PendingApproval`, `RiskLevel`, `RunAgentInput`, `ToolDefinition`, `SSEConnectionStatus`, `AGUIRunState`, `MessageRole`, `SharedState`, `StateDiff`, `StateConflict`, `PredictionResult`, `PredictionConfig`, `OrchestrationMetadata`, `PipelineToolCall` |
| 3 | `types/unified-chat.ts` | 15+ types/interfaces | ~80+ fields | `ExecutionMode`, `ModeSource`, `WorkflowStepStatus`, `WorkflowStep`, `WorkflowState`, `TrackedToolCall`, `Checkpoint`, `ConnectionStatus`, `ExecutionMetrics`, `UnifiedChatState`, `UnifiedChatActions`, `UnifiedChatProps`, `Attachment` |
| 4 | `types/devtools.ts` | 10+ types/interfaces | ~50+ fields | `TraceStatus`, `EventSeverity`, `Trace`, `TraceEvent`, `ListTracesParams`, `ListEventsParams`, `PaginatedResponse<T>`, `TraceDetail`, `DeleteTraceResponse` |

---

## 6. Utils Verification

### 1 file

| File | Exported Functions | LOC | Key Functionality |
|------|-------------------|-----|-------------------|
| `utils/guestUser.ts` | `getGuestUserId`, `isGuestUser`, `clearGuestUserId`, `migrateGuestData`, `hasGuestData`, `getGuestHeaders`, `ensureGuestUserId`, `GUEST_USER_KEY` | 171 | Guest UUID management (localStorage), X-Guest-Id header, migration API call to `/auth/migrate-guest` |

---

## 7. Lib Verification

### 1 file

| File | Exported Functions | LOC | Key Functionality |
|------|-------------------|-----|-------------------|
| `lib/utils.ts` | `cn`, `formatRelativeTime`, `formatDate`, `formatDateTime`, `truncateText`, `sleep`, `generateId`, `formatNumber`, `formatCurrency`, `formatPercent`/`formatPercentage`, `formatDuration` | 171 | Tailwind merge (`clsx` + `twMerge`), Traditional Chinese locale formatting |

---

## 8. App.tsx Route Map

**Total Routes: 30** (including nested)

### Standalone Routes (no AppLayout)
| Route | Component | Auth Required |
|-------|-----------|--------------|
| `/login` | `LoginPage` | No |
| `/signup` | `SignupPage` | No |
| `/ag-ui-demo` | `AGUIDemoPage` | No |
| `/swarm-test` | `SwarmTestPage` | No |

### Protected Routes (inside AppLayout + ProtectedRoute)
| Route | Component | Phase |
|-------|-----------|-------|
| `/` | Redirect to `/dashboard` | Sprint 5 |
| `/dashboard` | `DashboardPage` | Sprint 5 |
| `/chat` | `UnifiedChat` | Sprint 62/69 |
| `/performance` | `PerformancePage` | Sprint 12 |
| `/workflows` | `WorkflowsPage` | Sprint 5 |
| `/workflows/new` | `CreateWorkflowPage` | Sprint 5 |
| `/workflows/:id` | `WorkflowDetailPage` | Sprint 5 |
| `/workflows/:id/edit` | `EditWorkflowPage` | Sprint 5 |
| `/workflows/:id/editor` | `WorkflowEditorPage` | Sprint 133 |
| `/agents` | `AgentsPage` | Sprint 5 |
| `/agents/new` | `CreateAgentPage` | Sprint 5 |
| `/agents/:id` | `AgentDetailPage` | Sprint 5 |
| `/agents/:id/edit` | `EditAgentPage` | Sprint 5 |
| `/templates` | `TemplatesPage` | Sprint 5 |
| `/sessions` | `SessionsPage` | Sprint 138 |
| `/sessions/:id` | `SessionDetailPage` | Sprint 138 |
| `/tasks` | `TaskDashboardPage` | Sprint 139 |
| `/tasks/:id` | `TaskDetailPage` | Sprint 139 |
| `/knowledge` | `KnowledgePage` | Sprint 140 |
| `/memory` | `MemoryPage` | Sprint 140 |
| `/approvals` | `ApprovalsPage` | Sprint 5 |
| `/audit` | `AuditPage` | Sprint 5 |
| `/devui` | `DevUILayout` (nested) | Sprint 87 |
| `/devui` (index) | `DevUIOverview` | Sprint 87 |
| `/devui/ag-ui-test` | `AGUITestPanel` | Sprint 99 |
| `/devui/traces` | `TraceList` | Sprint 87 |
| `/devui/traces/:id` | `TraceDetail` | Sprint 87 |
| `/devui/monitor` | `LiveMonitor` | Sprint 87 (placeholder) |
| `/devui/settings` | `DevUISettings` | Sprint 87 (placeholder) |
| `*` | Redirect to `/dashboard` | — |

---

## 9. Cross-Reference & Corrections

### Corrections vs Previous Analysis (CLAUDE.md / frontend/CLAUDE.md)

| Item | Previous Claim | Actual Finding | Severity |
|------|---------------|----------------|----------|
| **Pages count** | "~38 files" (CLAUDE.md) | **45 files** (including sub-components and barrel exports in pages/) | LOW — sub-components not separately counted before |
| **Hooks count** | "17 files" (frontend/CLAUDE.md) / "25 files" (CLAUDE.md) | **25 files** (24 hooks + 1 index.ts) — the newer CLAUDE.md is correct | NONE |
| **API count** | "11 files" mentioned | **11 files** confirmed | NONE |
| **Stores directories** | "store/ (auth)" + "stores/ (features)" | Confirmed: `store/authStore.ts` (1 file) + `stores/` (2 stores + 1 test) | NONE |
| **Types count** | "4 files" | **4 files** confirmed | NONE |
| **Route count** | Not explicitly listed | **30 total routes** documented (4 standalone + 22 protected + 4 nested DevUI) | NEW |
| **DevUI LiveMonitor** | Listed as page | Actually a **placeholder** (Coming Soon) — no real functionality | INFO |
| **DevUI Settings** | Listed as page | Actually a **placeholder** (Coming Soon) — no real functionality | INFO |
| **UnifiedChat.tsx** | Listed as simple page | **1403 LOC** — largest page, consumes 6+ hooks, integrates swarm/SSE/orchestration | INFO |
| **AG-UI Demo** | Not detailed | 8 component files + 7 tabbed feature demos + EventLogPanel | NEW |
| **HTTP client** | "NOT Axios" | Confirmed: **native Fetch API** throughout. `devtools.ts` comment says "Axios" but code uses `api` (Fetch wrapper) | LOW — misleading comment only |

### Key Architectural Findings

1. **API Pattern**: All API calls go through `api/client.ts` fetchApi wrapper. No direct `fetch()` except in authStore (login/register), files upload (multipart), orchestrator SSE stream, and guestUser migration.

2. **State Management Split**:
   - **Zustand**: authStore (persisted), unifiedChatStore (persisted), swarmStore (immer)
   - **React Query**: All data-fetching hooks (useTraces, useSessions, useTasks, useKnowledge, useMemory)
   - **Local useState**: Page-level UI state (filters, pagination, forms)

3. **SSE/Streaming Pattern**: 4 independent SSE implementations:
   - `useAGUI` — AG-UI protocol EventSource
   - `useDevToolsStream` — DevTools trace EventSource
   - `useSwarmReal` — Swarm backend EventSource
   - `useSSEChat` — POST-based fetch+ReadableStream (NOT EventSource)

4. **Mock Data Pattern**: Every list/detail page has a `generateMock*()` fallback function for development without backend.

5. **Shared UI Components**: All pages use consistent Shadcn UI (`Card`, `Badge`, `Button`, `Input`, `Table`, `Select`, `Progress`, `Separator`) from `@/components/ui/`.

---

*End of V9 Layer 01 Verification Report*

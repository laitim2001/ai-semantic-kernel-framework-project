# Phase 3E: Frontend Part 4 — Hooks, API Client, Stores, Types & Utilities

**Agent**: E4
**Scope**: `frontend/src/hooks/`, `api/`, `store/`, `stores/`, `types/`, `utils/`, `lib/`, `App.tsx`, `main.tsx`
**Total Files Analyzed**: 35 files
**Date**: 2026-03-15

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Hooks Layer (17 files)](#2-hooks-layer)
3. [API Client Layer (6 files)](#3-api-client-layer)
4. [Stores Layer (4 files)](#4-stores-layer)
5. [Types Layer (4 files)](#5-types-layer)
6. [Utilities & Lib (2 files)](#6-utilities--lib)
7. [App Entry Points (2 files)](#7-app-entry-points)
8. [Cross-Cutting Issues](#8-cross-cutting-issues)
9. [Architecture Summary](#9-architecture-summary)

---

## 1. Executive Summary

The frontend "glue" layer consists of 35 TypeScript files that form the bridge between UI components/pages and the backend API. The architecture follows a clean layered pattern:

- **Hooks** (17 files, ~3,500 lines): Custom React hooks managing SSE connections, state, orchestration flows, approval workflows, file uploads, and dev tools
- **API Client** (6 files, ~700 lines): Fetch-based HTTP client with auth token injection, guest user support, and structured error handling
- **Stores** (4 files, ~900 lines): Zustand state management with persistence, immer for immutable updates, devtools integration
- **Types** (4 files, ~750 lines): Comprehensive TypeScript interfaces covering AG-UI protocol, unified chat, devtools, and core domain types
- **Utils/Lib** (2 files, ~170 lines): Guest user ID management and Tailwind CSS utility
- **Entry Points** (2 files, ~90 lines): React 18 app bootstrap with React Query, React Router, and route definitions

**Key Strengths**: Well-typed throughout, comprehensive AG-UI protocol implementation, clean separation of concerns, proper auth token lifecycle
**Key Concerns**: 35+ console.log/warn/error statements in production code, 2 hardcoded localhost fallback URLs, SSE reconnection logic incomplete in useAGUI

---

## 2. Hooks Layer

### 2.1 useUnifiedChat.ts (Core Hook)

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/hooks/useUnifiedChat.ts` |
| **Lines** | ~750 |
| **Purpose** | Main orchestration hook for the unified chat interface |
| **Sprint** | S63-1 (8 pts), S68-5 History Loading |

**State Managed**:
- Messages array (ChatMessage[])
- SSE connection lifecycle (EventSource + fetch-based SSE)
- Streaming state (isStreaming, streamingMessageId)
- Tool calls tracking
- Pending approvals
- Heartbeat state (S67-BF-1)
- Step progress (S69-3)
- Workflow state

**API Calls**:
- POST to AG-UI SSE endpoint (`/api/v1/ag-ui`) for `runAgent`
- GET `/api/v1/ag-ui/sessions/{sessionId}/messages` for history loading (Sprint 68)
- POST `/api/v1/ag-ui/approvals/{approvalId}/approve` and `/reject` for HITL
- Integrates with `useHybridMode` for mode detection
- Syncs with `useUnifiedChatStore` (Zustand)

**SSE Event Types Handled (15 total)**:
- `RUN_STARTED`, `RUN_FINISHED`, `RUN_ERROR`
- `TEXT_MESSAGE_START`, `TEXT_MESSAGE_CONTENT`, `TEXT_MESSAGE_END`
- `TOOL_CALL_START`, `TOOL_CALL_ARGS`, `TOOL_CALL_END`
- `STATE_SNAPSHOT`, `STATE_DELTA`
- `CUSTOM` (APPROVAL_REQUIRED, heartbeat, step_progress)

**Key Return Values**:
- `sendMessage(content: string)`: Send user message and trigger AG-UI run
- `messages`, `isStreaming`, `connectionStatus`
- `pendingApprovals`, `approveToolCall`, `rejectToolCall`
- `heartbeat`, `stepProgress`, `currentStepProgress`
- `mode`, `setManualMode`, `clearManualMode`

**Architecture Notes**:
- Uses fetch-based SSE (not EventSource) for POST support
- Reads SSE stream via ReadableStream reader with TextDecoder
- Manual SSE line parsing (`data: ` prefix detection)
- Manages message streaming by accumulating deltas into currentMessageRef
- Syncs every state change to Zustand store via useEffect
- History loading integrates with existing message state (deduplication by ID)

**Issues Found**:
- `console.warn` at line 170 for SSE parse failures
- `console.error` at line 575 for approval failures
- `console.error` at line 635 for run agent errors
- Large file (~750 lines) — could benefit from extraction of SSE handling logic

---

### 2.2 useOrchestration.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/hooks/useOrchestration.ts` |
| **Lines** | 353 |
| **Purpose** | Three-layer orchestration flow management |
| **Sprint** | S99 (Phase 28) |

**State Managed**:
- `OrchestrationPhase`: idle | routing | dialog | risk_assessment | awaiting_approval | executing | completed | error
- `RoutingDecision`, `RiskAssessment`, `DialogStatusResponse`, `HybridExecuteResponse`

**API Calls** (via `orchestrationApi`):
- `orchestrationApi.classify()` → POST `/orchestration/intent/classify`
- `orchestrationApi.startDialog()` → POST `/orchestration/dialog/start`
- `orchestrationApi.respondToDialog()` → POST `/orchestration/dialog/{dialogId}/respond`
- `orchestrationApi.execute()` → POST `/orchestration/hybrid/execute`

**Flow**:
1. Intent Routing (classify message, get routing decision + risk assessment)
2. Guided Dialog (if completeness < 0.7, start dialog for missing info)
3. Risk Assessment Check (if requires_approval, pause for HITL)
4. Auto-execute (if enabled and no approval needed)

**Callbacks**: `onRoutingComplete`, `onDialogQuestions`, `onApprovalRequired`, `onExecutionComplete`, `onError`

**Return Values**: `state`, `startOrchestration`, `respondToDialog`, `proceedWithExecution`, `executeDirectly`, `reset`, `cancel`

**Issues**: None significant. Clean implementation with proper cancellation support via `cancelledRef`.

---

### 2.3 useAGUI.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/hooks/useAGUI.ts` |
| **Lines** | 983 |
| **Purpose** | AG-UI Protocol main hook (standalone, not used in UnifiedChat) |
| **Sprint** | S60+ |

**State Managed**:
- SSE connection status, messages, tool calls, pending approvals
- Run state (runId, status, timestamps)
- Heartbeat state (S67-BF-1)
- Step progress state (S69-3) with Map<string, StepProgressEvent>
- Integrates `useSharedState` and `useOptimisticState`

**API Calls**:
- POST to `apiUrl` (default `/api/v1/ag-ui`) with SSE streaming
- POST to `approvalApiUrl` (default `/api/v1/ag-ui/approvals`) for approve/reject
- Uses raw `fetch()` directly (not the api client) for SSE and approvals

**Key Difference from useUnifiedChat**: This is the standalone AG-UI hook. `useUnifiedChat` wraps/extends this pattern with Zustand store sync, mode management, and history loading. Both handle the same 15 SSE event types.

**Issues**:
- `console.warn` line 178 (SSE parse)
- `console.log` line 732 (unhandled SSE event — production leak)
- `console.error` lines 488, 509, 526, 547, 860 (approval/rejection/run errors)
- Approval API calls use raw `fetch()` instead of the centralized `api` client — inconsistent with the rest of the codebase
- Reconnection logic is a stub: `reconnect()` just sets status to 'connecting' but doesn't actually reconnect

---

### 2.4 useHybridMode.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/hooks/useHybridMode.ts` |
| **Lines** | ~200 |
| **Purpose** | Auto-detect execution mode (chat vs workflow) based on message content |
| **Sprint** | S63 |

**Mode Detection Algorithm**:
- Pattern-based keyword analysis on user message content
- Workflow keywords: "workflow", "execute", "run", "deploy", "automate", "batch", "pipeline", "schedule"
- Chat keywords: "what", "how", "why", "explain", "help", "tell", "describe"
- Scoring system: workflow score vs chat score, threshold-based
- Returns `ExecutionMode` ('chat' | 'workflow') with `ModeSource` ('auto' | 'manual')

**State**: Manual override support (user can force mode), auto-detection as fallback

**Exported**: `useHybridMode` hook + `dispatchModeDetection` utility function

**Issues**: None. Clean, focused hook.

---

### 2.5 useSharedState.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/hooks/useSharedState.ts` |
| **Lines** | ~450 |
| **Purpose** | AG-UI shared state synchronization between frontend and backend |
| **Sprint** | S60-2 |

**State Managed**: Generic state object with diff-based updates

**API Calls**:
- GET `{apiUrl}` to fetch initial state
- POST `{apiUrl}` to push local state changes
- SSE connection to `{apiUrl}/stream` for real-time sync

**Mechanisms**:
- `applyDiffs()`: Apply state diffs (add/replace/remove operations) to local state
- `syncState()`: Push local state to server
- Deep merge/patch utility for nested state objects
- SSE-based real-time sync with server-pushed state changes

**Return Type**: `UseSharedStateReturn` with state, getState, setState, applyDiffs, syncState, isSyncing, lastSyncAt

**Issues**: `console.error` at line 320 (sync error), line 440 (SSE parse error)

---

### 2.6 useOptimisticState.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/hooks/useOptimisticState.ts` |
| **Lines** | ~400 |
| **Purpose** | Optimistic UI updates with prediction/confirmation cycle |
| **Sprint** | S60-3 |

**State Managed**: Pending predictions queue, confirmed state, optimistic merged view

**Mechanism**:
- `predict(key, value)`: Optimistically apply change, queue prediction
- `confirm(predictionId)`: Server confirmed, remove from pending queue
- `reject(predictionId)`: Server rejected, rollback prediction
- Max pending predictions limit (default 10)
- Automatic timeout for unconfirmed predictions

**API Calls**: POST to `{apiUrl}/predictions` to send predictions to server

**Issues**: `console.warn` line 236 (max pending predictions reached), `console.error` line 290 (prediction send failure)

---

### 2.7 useCheckpoints.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/hooks/useCheckpoints.ts` |
| **Lines** | ~340 |
| **Purpose** | State checkpoint and restore for workflow recovery |
| **Sprint** | S65 |

**API Calls** (via `aguiApi`):
- `aguiApi.listCheckpoints(threadId)` → GET `/ag-ui/threads/{threadId}/checkpoints`
- `aguiApi.createCheckpoint(threadId, data)` → POST `/ag-ui/threads/{threadId}/checkpoints`
- `aguiApi.restoreCheckpoint(threadId, checkpointId)` → POST `/ag-ui/threads/{threadId}/checkpoints/{id}/restore`

**State**: checkpoints array, isLoading, error, currentCheckpoint

**Callbacks**: `onRestoreSuccess`, `onRestoreError`

**Issues**: Multiple `console.error` statements (lines 168, 216, 221, 291)

---

### 2.8 useApprovalFlow.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/hooks/useApprovalFlow.ts` |
| **Lines** | ~380 |
| **Purpose** | HITL approval workflow management |
| **Sprint** | S64 |

**API Calls** (via `aguiApi`):
- `aguiApi.approve(toolCallId)` → POST `/ag-ui/tool-calls/{id}/approve`
- `aguiApi.reject(toolCallId, reason)` → POST `/ag-ui/tool-calls/{id}/reject`

**State**: pendingApprovals array, processingApprovals Set, approvalHistory

**Features**:
- Auto-approve for low-risk tool calls (configurable threshold)
- Expiration tracking (auto-reject expired approvals)
- Approval history tracking
- Batch approve/reject support

**Callbacks**: `onApprovalProcessed`, `onAutoApproved`, `onExpired`

**Issues**: `console.error` lines 279, 324

---

### 2.9 useExecutionMetrics.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/hooks/useExecutionMetrics.ts` |
| **Lines** | ~380 |
| **Purpose** | Track execution metrics (tokens, time, tool calls) |
| **Sprint** | S63 |

**State Managed**:
- Token usage: { used, limit, percentage }
- Time tracking: { total, isRunning } with interval-based timer
- Tool call count, message count
- Cost estimation (configurable per-token rate)

**No API calls** — purely frontend metric aggregation

**Features**:
- `startTimer()` / `stopTimer()` for execution timing
- `addTokens(count)` for token tracking
- `incrementToolCalls()`, `incrementMessages()`
- `estimateCost()` based on token usage
- Auto-cleanup of timer interval on unmount

**Issues**: None. Clean utility hook.

---

### 2.10 useChatThreads.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/hooks/useChatThreads.ts` |
| **Lines** | ~340 |
| **Purpose** | Multi-thread chat session management |
| **Sprint** | S68 |

**State Managed**: Thread list, active thread ID, per-thread messages (localStorage)

**API Calls** (via `aguiApi`):
- `aguiApi.listThreads()` → GET `/ag-ui/threads`
- `aguiApi.createThread(data)` → POST `/ag-ui/threads`
- `aguiApi.getThread(threadId)` → GET `/ag-ui/threads/{id}`

**Persistence**: localStorage for thread list and per-thread messages (with error handling for quota exceeded)

**Return Values**: `threads`, `activeThread`, `createThread`, `switchThread`, `deleteThread`, `loadMessages`, `saveMessages`, `clearMessages`

**Issues**: Multiple `console.warn` for localStorage failures (lines 130, 159, 284, 302, 326). Appropriate defensive coding.

---

### 2.11 useFileUpload.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/hooks/useFileUpload.ts` |
| **Lines** | ~220 |
| **Purpose** | File upload with progress tracking |
| **Sprint** | S75 |

**API Calls** (via `filesApi`):
- `uploadFile(file, sessionId, onProgress)` → POST `/files/upload` (multipart/form-data via XHR)

**State**: uploadedFiles array, isUploading, uploadProgress (percent), error

**Features**:
- File validation (type, size) via `isAllowedFileType()` and `getMaxFileSize()`
- Progress tracking via XHR `progress` event
- Multiple file support
- Remove uploaded file
- Clear all files

**Issues**: None significant.

---

### 2.12 useDevTools.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/hooks/useDevTools.ts` |
| **Lines** | ~60 |
| **Purpose** | Re-export of devtools API functions |
| **Sprint** | S87 |

**Essentially a thin wrapper** that re-exports `devtoolsApi` methods as a hook interface.

---

### 2.13 useDevToolsStream.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/hooks/useDevToolsStream.ts` |
| **Lines** | ~200 |
| **Purpose** | SSE streaming for DevTools live monitor |
| **Sprint** | S87 |

**SSE Connection**: EventSource to `{apiBase}/devtools/traces/{executionId}/stream`

**State**: events array, isConnected, error

**Issues**:
- **Hardcoded fallback URL**: `import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'` (line 119)
- `console.error` lines 143, 148

---

### 2.14 useEventFilter.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/hooks/useEventFilter.ts` |
| **Lines** | ~340 |
| **Purpose** | Event filtering and search for DevTools |
| **Sprint** | S87 |

**State**: filter criteria (event type, severity, time range, search text), filtered results

**No API calls** — purely frontend filtering logic

**Features**:
- Multi-criteria filtering (type, severity, time range, text search)
- Debounced search for performance
- Filter preset management
- `hasActiveFilters` computed property

---

### 2.15 useSwarmMock.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/hooks/useSwarmMock.ts` |
| **Lines** | ~550 |
| **Purpose** | Mock data generator for agent swarm visualization testing |
| **Sprint** | S105 (Phase 29) |

**No API calls** — generates synthetic swarm data with realistic timing

**Features**:
- Simulates swarm lifecycle: initializing → executing → completed
- Generates 3-5 mock workers with realistic progress updates
- Simulated thinking content, tool calls, progress events
- Timer-based progression (configurable speed)
- Used by SwarmTestPage for development/testing

---

### 2.16 useSwarmReal.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/hooks/useSwarmReal.ts` |
| **Lines** | ~400 |
| **Purpose** | Real API integration for agent swarm |
| **Sprint** | S105 (Phase 29) |

**API Calls**:
- GET `{API_BASE_URL}/swarm/scenarios` → List available swarm scenarios
- POST `{API_BASE_URL}/swarm/demo/start` → Start swarm demo
- POST `{API_BASE_URL}/swarm/demo/stop` → Stop swarm demo
- SSE: EventSource to `{API_BASE_URL}/swarm/demo/stream/{sessionId}`

**SSE Events Handled**:
- `swarm_started`, `worker_started`, `worker_progress`
- `worker_thinking`, `worker_tool_call`, `worker_completed`
- `swarm_progress`, `swarm_completed`

**State**: Managed via `useSwarmStore` (Zustand)

**Issues**:
- **Hardcoded fallback URL**: `const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'` (line 122)
- `console.log` line 299 (swarm completed — production leak)
- `console.error` lines 218, 337, 350

---

### 2.17 hooks/index.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/hooks/index.ts` |
| **Lines** | ~50 |
| **Purpose** | Barrel export for all hooks |

**Exports all 16 hooks** with both named and type exports. Clean organization.

---

## 3. API Client Layer

### 3.1 api/client.ts (Core HTTP Client)

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/api/client.ts` |
| **Lines** | 173 |
| **Purpose** | Centralized fetch wrapper with auth, guest ID, error handling |
| **Sprint** | S5, S69-5, S71-4 |

**Base URL**: `import.meta.env.VITE_API_URL || '/api/v1'` (relative URL fallback — good)

**Auth Token**: Read from `useAuthStore.getState().token` (Zustand persist → localStorage)

**Headers Attached**:
- `Content-Type: application/json` (all requests)
- `Authorization: Bearer {token}` (if authenticated)
- `X-Guest-Id: guest-{uuid}` (if guest user, for sandbox isolation)

**Error Handling**:
- 401 → `handleUnauthorized()` → calls `authStore.logout()` + redirects to `/login`
- Other errors → parses JSON error body → throws `ApiError(message, status, details)`
- 204 No Content → returns `{} as T`

**Exported Methods**: `api.get<T>()`, `api.post<T>()`, `api.put<T>()`, `api.patch<T>()`, `api.delete<T>()`

**Issues**: None significant. Well-structured client.

---

### 3.2 api/endpoints/ag-ui.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/api/endpoints/ag-ui.ts` |
| **Lines** | ~250 |
| **Purpose** | AG-UI protocol API endpoints |
| **Sprint** | S64-4, S65 |

**Endpoints Defined**:
- `approve(toolCallId)` → POST `/ag-ui/tool-calls/{id}/approve`
- `reject(toolCallId, reason?)` → POST `/ag-ui/tool-calls/{id}/reject`
- `getPendingApprovals(threadId?)` → GET `/ag-ui/approvals?thread_id={id}`
- `listThreads()` → GET `/ag-ui/threads`
- `createThread(data)` → POST `/ag-ui/threads`
- `getThread(threadId)` → GET `/ag-ui/threads/{id}`
- `listCheckpoints(threadId)` → GET `/ag-ui/threads/{id}/checkpoints`
- `createCheckpoint(threadId, data)` → POST `/ag-ui/threads/{id}/checkpoints`
- `restoreCheckpoint(threadId, checkpointId)` → POST `/ag-ui/threads/{id}/checkpoints/{cpId}/restore`

**All use centralized `api` client** — consistent error handling.

---

### 3.3 api/endpoints/orchestration.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/api/endpoints/orchestration.ts` |
| **Lines** | ~300 |
| **Purpose** | Phase 28 orchestration endpoints |
| **Sprint** | S99 |

**Endpoints Defined**:
- `classify(request)` → POST `/orchestration/intent/classify`
- `startDialog(request)` → POST `/orchestration/dialog/start`
- `respondToDialog(dialogId, request)` → POST `/orchestration/dialog/{id}/respond`
- `getDialogStatus(dialogId)` → GET `/orchestration/dialog/{id}/status`
- `listApprovals(params?)` → GET `/orchestration/approvals`
- `decideApproval(approvalId, decision)` → POST `/orchestration/approvals/{id}/decision`
- `execute(request)` → POST `/orchestration/hybrid/execute`

**Rich type definitions** for all request/response types (ITIntentCategory, RoutingDecision, RiskAssessment, DialogQuestion, etc.)

---

### 3.4 api/endpoints/files.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/api/endpoints/files.ts` |
| **Lines** | ~320 |
| **Purpose** | File upload and management |
| **Sprint** | S75-76 |

**Endpoints Defined**:
- `uploadFile(file, sessionId?, onProgress?)` → POST `/files/upload` (XHR for progress tracking)
- `listFiles()` → GET `/files`
- `getFile(fileId)` → GET `/files/{id}`
- `deleteFile(fileId)` → DELETE `/files/{id}`
- `getFileContentUrl(fileId)` → Returns URL string `/files/{id}/content`
- `getFileDownloadUrl(fileId)` → Returns URL string `/files/{id}/download`
- `downloadFile(fileId, filename?)` → Fetch + Blob download with Content-Disposition parsing

**Notable**: Uses XHR (not fetch) for upload to get progress events. Manually attaches auth headers.

**Utility Functions**: `formatFileSize()`, `getFileCategory()`, `isAllowedFileType()`, `getMaxFileSize()`

**Allowed Types**: text/plain, text/csv, text/markdown, application/json, application/pdf, image/png, image/jpeg, image/gif, image/webp

**Max Sizes**: text: 10MB, image: 5MB, pdf: 20MB

---

### 3.5 api/endpoints/index.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/api/endpoints/index.ts` |
| **Lines** | 60 |
| **Purpose** | Barrel export for all endpoint modules |

Re-exports all API objects and types from ag-ui, files, and orchestration.

---

### 3.6 api/devtools.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/api/devtools.ts` |
| **Lines** | 87 |
| **Purpose** | DevTools tracing API |
| **Sprint** | S87-2 |

**Endpoints Defined**:
- `listTraces(params?)` → GET `/devtools/traces`
- `getTrace(executionId)` → GET `/devtools/traces/{id}`
- `getEvents(executionId, params?)` → GET `/devtools/traces/{id}/events`
- `deleteTrace(executionId)` → DELETE `/devtools/traces/{id}`

**Note**: Comment says "Axios client" but actually uses the fetch-based `api` client — stale comment.

---

## 4. Stores Layer

### 4.1 store/authStore.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/store/authStore.ts` |
| **Lines** | 323 |
| **Purpose** | Authentication state management |
| **Sprint** | S71-1 (Phase 18) |

**State Shape**:
```typescript
{
  user: User | null,           // { id, email, fullName, role, isActive, createdAt, lastLogin }
  token: string | null,        // JWT access token
  refreshToken: string | null, // JWT refresh token
  isAuthenticated: boolean,
  isLoading: boolean,
  error: string | null,
}
```

**Actions**:
- `login(email, password)` → POST `/auth/login` (OAuth2 form-urlencoded) → GET `/auth/me` → set state → migrate guest data
- `register(email, password, fullName?)` → POST `/auth/register` → GET `/auth/me` → set state → clear guest ID
- `logout()` → clear all state + clear guest ID
- `refreshSession()` → POST `/auth/refresh` → GET `/auth/me` → update tokens
- `clearError()`, `setLoading()`

**Persistence**: Zustand `persist` middleware → localStorage key `ipa-auth-storage`
**Partialize**: Only persists `token`, `refreshToken`, `user`, `isAuthenticated` (not loading/error)

**API Helpers**: Internal functions (`apiLogin`, `apiRegister`, `apiGetMe`, `apiRefreshToken`) using raw `fetch()` — deliberately not using the `api` client to avoid circular dependency (api client reads from this store).

**Selectors**: `selectUser`, `selectIsAuthenticated`, `selectIsLoading`, `selectError`, `selectToken`

**Issues**:
- `console.warn` for guest migration failure (non-blocking, appropriate)
- `console.error` for login/registration/refresh failures (appropriate for debugging)
- Login uses `application/x-www-form-urlencoded` (OAuth2 spec), register uses `application/json` — intentional difference

---

### 4.2 stores/unifiedChatStore.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/stores/unifiedChatStore.ts` |
| **Lines** | 509 |
| **Purpose** | Central state for unified chat interface |
| **Sprint** | S62-2, S63-4 |

**State Shape**:
```typescript
{
  threadId: string, sessionId: string,
  mode: ExecutionMode, autoMode: ExecutionMode, manualOverride: ExecutionMode | null,
  messages: ChatMessage[], isStreaming: boolean, streamingMessageId: string | null,
  workflowState: WorkflowState | null,
  toolCalls: TrackedToolCall[],
  pendingApprovals: PendingApproval[], dialogApproval: PendingApproval | null,
  checkpoints: Checkpoint[], currentCheckpoint: string | null,
  metrics: ExecutionMetrics,
  connection: ConnectionStatus,
  error: string | null,
}
```

**Actions** (25 total):
- Mode: `setMode`, `setManualOverride`, `setAutoMode`
- Messages: `addMessage`, `updateMessage`, `setMessages`, `setStreaming`, `clearMessages`, `clearPersistence`
- Workflow: `setWorkflowState`, `updateWorkflowStep`
- Tool Calls: `addToolCall`, `updateToolCall`
- Approvals: `addPendingApproval` (auto-show dialog for high/critical), `removePendingApproval`, `setDialogApproval`
- Checkpoints: `addCheckpoint`, `setCurrentCheckpoint`
- Metrics: `updateMetrics`
- Connection: `setConnection`
- Error: `setError`
- Reset: `reset`

**Persistence**: Zustand `persist` middleware → localStorage key `unified-chat-storage`
- Custom storage wrapper with quota exceeded error handling
- Partializes: threadId, sessionId, mode, manualOverride, autoMode, messages (last 100), workflowState, checkpoints (last 20), currentCheckpoint
- Version 1 with migration support

**Middleware**: `devtools` (Redux DevTools integration) + `persist`

**Selectors**: `selectMode`, `selectMessages`, `selectIsStreaming`, `selectPendingApprovals`, `selectWorkflowState`, `selectMetrics`, `selectConnection`

---

### 4.3 stores/swarmStore.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/stores/swarmStore.ts` |
| **Lines** | 445 |
| **Purpose** | Agent swarm state management |
| **Sprint** | S105 (Phase 29) |

**State Shape**:
```typescript
{
  swarmStatus: UIAgentSwarmStatus | null,  // overall swarm state
  selectedWorkerId: string | null,
  selectedWorkerDetail: WorkerDetail | null,
  isDrawerOpen: boolean,
  isLoading: boolean,
  error: string | null,
}
```

**Actions**:
- Swarm-level: `setSwarmStatus`, `updateSwarmProgress`, `completeSwarm`
- Worker-level: `addWorker`, `updateWorkerProgress`, `updateWorkerThinking`, `updateWorkerToolCall`, `completeWorker`
- UI: `selectWorker`, `setWorkerDetail`, `openDrawer`, `closeDrawer`
- Utility: `setLoading`, `setError`, `reset`

**Middleware**: `devtools` + `immer` (immutable updates via direct mutation syntax)

**No persistence** — swarm state is transient (session-only)

**Selectors**: `selectSwarmStatus`, `selectWorkers`, `selectSelectedWorkerId`, `selectSelectedWorkerDetail`, `selectIsDrawerOpen`, `selectIsLoading`, `selectError`, `selectCompletedWorkers`, `selectRunningWorkers`, `selectFailedWorkers`, `selectIsSwarmActive`

---

### 4.4 stores/__tests__/swarmStore.test.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/stores/__tests__/swarmStore.test.ts` |
| **Lines** | ~380 |
| **Purpose** | Unit tests for swarmStore |

**Test Coverage**: Comprehensive tests covering all store actions (setSwarmStatus, addWorker, updateWorkerProgress, updateWorkerThinking, updateWorkerToolCall, completeWorker, selectWorker, drawer state, reset). Good edge case coverage.

---

## 5. Types Layer

### 5.1 types/index.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/types/index.ts` |
| **Lines** | ~200 |
| **Purpose** | Core shared type definitions |
| **Sprint** | S5 |

**Key Types**:
- `Status`: 'pending' | 'running' | 'completed' | 'failed' | 'paused'
- `PaginatedResponse<T>`: { items, total, page, page_size, total_pages }
- `Workflow`: Full workflow definition with graph, triggers, metadata
- `WorkflowDefinition`, `WorkflowGraphDefinition`: Node/edge definitions
- `WorkflowNode`, `WorkflowGraphNode`, `WorkflowEdge`, `WorkflowGraphEdge`
- `Execution`: Execution record with status, timing, error info
- `Agent`: Agent definition with name, type, model, capabilities, tools
- `AgentCapability`, `AgentTool`
- `Template`: Workflow template with steps and metadata

**Note**: Two PaginatedResponse definitions exist — one here (page/page_size based) and one in devtools.ts (limit/offset based). Inconsistency.

---

### 5.2 types/ag-ui.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/types/ag-ui.ts` |
| **Lines** | ~350 |
| **Purpose** | AG-UI Protocol type definitions |
| **Sprint** | S60 |

**Key Types**:
- **UI Components**: `UIComponentType`, `FormFieldDefinition`, `TableColumnDefinition`, `ChartData`, `UIComponentSchema`, `UIComponentDefinition`
- **Messages**: `MessageRole` ('user' | 'assistant' | 'system' | 'tool'), `ChatMessage` (id, role, content, timestamp, toolCalls?, uiComponents?, metadata?)
- **Tool Calls**: `ToolCallStatus` (7 states), `ToolCallState` (id, name, args, status, result, error, timing)
- **Approvals**: `RiskLevel` (low | medium | high | critical), `PendingApproval` (approvalId, toolCallId, toolName, args, riskLevel, riskScore, reasoning, runId, sessionId, timing)
- **Events**: `AGUIEventType` (15 event types), `AGUIEvent` (type, data, timestamp)
- **Connection**: `SSEConnectionStatus` (disconnected | connecting | connected | error | reconnecting)
- **Run State**: `AGUIRunState` (runId, status, error, timing)
- **Run Input**: `RunAgentInput` (threadId, runId, prompt, mode, messages, tools, etc.)
- **Tools**: `ToolDefinition` (name, description, parameters)

**Quality**: Comprehensive and well-organized. Matches backend AG-UI protocol exactly.

---

### 5.3 types/unified-chat.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/types/unified-chat.ts` |
| **Lines** | ~450 |
| **Purpose** | Unified chat interface types |
| **Sprint** | S62 |

**Key Types**:
- `ExecutionMode`: 'chat' | 'workflow'
- `ModeSource`: 'auto' | 'manual'
- `WorkflowStepStatus`: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
- `WorkflowStep`: { id, name, description?, status, timing, error?, metadata? }
- `WorkflowState`: { workflowId, steps, currentStepIndex, totalSteps, progress, status, timing }
- `TrackedToolCall`: extends ToolCallState with duration?, queuedAt?
- `Checkpoint`: { id, timestamp, label?, canRestore, stepIndex?, metadata? }
- `ConnectionStatus`: 'connected' | 'connecting' | 'disconnected' | 'error'
- `ExecutionMetrics`: { tokens: {used, limit, percentage}, time: {total, isRunning}, toolCallCount, messageCount }
- `UnifiedChatState`: Full state interface (all state properties)
- `UnifiedChatActions`: Full actions interface (all 25 action methods)

**Quality**: Very comprehensive. State and action types are fully separated. Good use of TypeScript discriminated unions.

---

### 5.4 types/devtools.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/types/devtools.ts` |
| **Lines** | ~105 |
| **Purpose** | DevTools tracing types |
| **Sprint** | S87-2 |

**Key Types**:
- `TraceStatus`: 'running' | 'completed' | 'failed'
- `EventSeverity`: 'debug' | 'info' | 'warning' | 'error' | 'critical'
- `Trace`: { id, execution_id, workflow_id, timing, status, event_count, span_count, metadata }
- `TraceEvent`: { id, trace_id, event_type, timestamp, data, severity, parent_event_id?, executor_id?, step_number?, duration_ms?, tags, metadata }
- `TraceDetail`: extends Trace with events_summary
- `ListTracesParams`, `ListEventsParams`: Query parameters
- `PaginatedResponse<T>`: { items, total, limit, offset } — Note: different from types/index.ts version
- `DeleteTraceResponse`: { success, message }

---

## 6. Utilities & Lib

### 6.1 utils/guestUser.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/utils/guestUser.ts` |
| **Lines** | ~130 |
| **Purpose** | Guest user ID management for sandbox isolation |
| **Sprint** | S68-5, S69-5 |

**Functions**:
- `getGuestUserId()`: Get or create guest UUID (`guest-{uuid}`), stored in localStorage key `ipa_guest_user_id`
- `isGuestUser()`: Check if guest ID exists in localStorage
- `clearGuestUserId()`: Remove guest ID from localStorage
- `migrateGuestData(authToken)`: POST `/api/v1/auth/migrate-guest` with { guest_id } to transfer sessions/files/sandbox data to authenticated user. Returns { success, sessionsMigrated, directoriesMigrated }
- `getGuestHeaders()`: Returns `{ 'X-Guest-Id': guestId }` header object for API requests

**Issues**:
- `console.log` at line 36 (guest user creation) and line 62 (guest ID cleared) — production information leak
- `migrateGuestData` uses hardcoded `/api/v1/auth/migrate-guest` instead of using the `api` client — but this is intentional (called during login before api client may be ready)

---

### 6.2 lib/utils.ts

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/lib/utils.ts` |
| **Lines** | ~15 + additional utility functions |
| **Purpose** | Tailwind CSS class merge utility |

**Functions**:
- `cn(...inputs: ClassValue[])`: Merges class names using `clsx` + `tailwind-merge` for Tailwind CSS conflict resolution

**Standard Shadcn UI utility** — used across all components.

---

## 7. App Entry Points

### 7.1 App.tsx

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/App.tsx` |
| **Lines** | ~100 |
| **Purpose** | Root component with route definitions |
| **Sprint** | S5, S61, S62, S69-4, S71-2, S87-1, S133 |

**Route Structure**:

| Path | Component | Auth | Layout |
|------|-----------|------|--------|
| `/login` | LoginPage | No | Standalone |
| `/signup` | SignupPage | No | Standalone |
| `/ag-ui-demo` | AGUIDemoPage | No | Standalone |
| `/swarm-test` | SwarmTestPage | No | Standalone |
| `/` | redirect → `/dashboard` | Protected | AppLayout |
| `/dashboard` | DashboardPage | Protected | AppLayout |
| `/dashboard/performance` | PerformancePage | Protected | AppLayout |
| `/workflows` | WorkflowsPage | Protected | AppLayout |
| `/workflows/:id` | WorkflowDetailPage | Protected | AppLayout |
| `/workflows/editor` | WorkflowEditorPage | Protected | AppLayout |
| `/workflows/editor/:id` | WorkflowEditorPage | Protected | AppLayout |
| `/agents` | AgentsPage | Protected | AppLayout |
| `/agents/:id` | AgentDetailPage | Protected | AppLayout |
| `/approvals` | ApprovalsPage | Protected | AppLayout |
| `/audit` | AuditPage | Protected | AppLayout |
| `/templates` | TemplatesPage | Protected | AppLayout |
| `/devui` | DevUILayout → DevUIOverview | Protected | AppLayout |
| `/devui/traces` | DevUILayout → TraceList | Protected | AppLayout |
| `/devui/traces/:id` | DevUILayout → TraceDetail | Protected | AppLayout |
| `/devui/live` | DevUILayout → LiveMonitor | Protected | AppLayout |
| `/devui/settings` | DevUILayout → DevUISettings | Protected | AppLayout |

**Auth Protection**: `<ProtectedRoute>` wrapper component (from `@/components/auth/ProtectedRoute`)

**Notes**:
- UnifiedChat is integrated into AppLayout sidebar (S69-4), not a standalone route
- DevUI has its own nested layout (DevUILayout)
- `/swarm-test` and `/ag-ui-demo` are unprotected (development/testing pages)

---

### 7.2 main.tsx

| Attribute | Value |
|-----------|-------|
| **Path** | `frontend/src/main.tsx` |
| **Lines** | 40 |
| **Purpose** | Application entry point |
| **Sprint** | S5 |

**Provider Stack** (outside → inside):
1. `React.StrictMode`
2. `QueryClientProvider` (TanStack React Query)
3. `BrowserRouter` (React Router 6)
4. `App` (routes)

**QueryClient Configuration**:
- `staleTime`: 5 minutes
- `retry`: 1 (single retry)
- `refetchOnWindowFocus`: false

**Render**: `ReactDOM.createRoot` (React 18 concurrent mode)

---

## 8. Cross-Cutting Issues

### 8.1 Console Statements in Production Code

**Total: 35+ console.log/warn/error statements across the scoped files**

| Severity | Count | Files |
|----------|-------|-------|
| `console.log` | 4 | useAGUI (1), useSwarmReal (1), guestUser (2) |
| `console.warn` | 9 | useAGUI (1), useChatThreads (5), useOptimisticState (1), unifiedChatStore (2) |
| `console.error` | 22+ | useAGUI (5), useApprovalFlow (2), useCheckpoints (4), useDevToolsStream (2), useSharedState (2), useOptimisticState (1), useSwarmReal (3), useUnifiedChat (2), authStore (3) |

**Recommendation**: Replace with a proper logging service that can be disabled in production. At minimum, the `console.log` calls should be removed. `console.error` calls are acceptable for development but should use a configurable logger.

### 8.2 Hardcoded Localhost URLs

| File | Line | URL |
|------|------|-----|
| `useDevToolsStream.ts` | 119 | `'http://localhost:8000/api/v1'` |
| `useSwarmReal.ts` | 122 | `'http://localhost:8000/api/v1'` |

Both use `import.meta.env.VITE_API_URL ||` as primary — the hardcoded URL is a fallback. However, the main `api/client.ts` uses `'/api/v1'` (relative URL) as fallback, which is better for production deployment. These two files should be updated to use relative URL fallback or import from `api/client.ts`.

### 8.3 Inconsistent API Client Usage

| Pattern | Files Using It |
|---------|---------------|
| Centralized `api` client | api/endpoints/ag-ui.ts, orchestration.ts, devtools.ts |
| Raw `fetch()` | useAGUI.ts (approvals), authStore.ts (login/register/refresh), guestUser.ts (migration), files.ts (upload via XHR) |

The raw `fetch()` usage in `authStore.ts` is intentional (avoids circular dependency — api client reads from auth store). The `guestUser.ts` migration is also intentional (called during login flow). However, `useAGUI.ts` approval calls should use the centralized client.

### 8.4 Duplicate PaginatedResponse Types

- `types/index.ts`: `PaginatedResponse<T>` with `{ page, page_size, total_pages }` (page-based)
- `types/devtools.ts`: `PaginatedResponse<T>` with `{ limit, offset }` (offset-based)

These represent two different pagination strategies from the backend, but having the same type name is confusing. Consider renaming to `PagedResponse` and `OffsetResponse` or using a discriminated union.

### 8.5 Stale Comment

- `api/devtools.ts` line 9: Comment says "Axios client" but the file uses the Fetch-based `api` client.

### 8.6 No TODO/FIXME/HACK Comments

Zero TODO or FIXME comments found in the scoped files — clean codebase.

### 8.7 No `any` Type Usage

Only one match found: `useEventFilter.ts` line 70: `/** Has any active filters */` — this is a JSDoc comment, not a type annotation. Zero actual `any` type usage in the scoped files — excellent TypeScript discipline.

---

## 9. Architecture Summary

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────┐
│                    main.tsx                          │
│  React.StrictMode → QueryClientProvider → Router    │
└───────────────────────┬─────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│                    App.tsx                           │
│  Routes → ProtectedRoute → AppLayout → Pages        │
└───────────────────────┬─────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│              Pages (UnifiedChat, etc.)               │
│  Use hooks to connect UI to backend                  │
└───────┬───────────┬──────────────┬──────────────────┘
        ↓           ↓              ↓
┌───────────┐ ┌──────────┐ ┌──────────────┐
│  Hooks    │ │  Stores  │ │  API Client  │
│           │ │ (Zustand)│ │  (Fetch)     │
│ useUnified│←→│ unified  │ │              │
│   Chat    │ │ ChatStore│ │  api.get()   │
│ useAGUI   │ │ swarm    │ │  api.post()  │
│ useOrch.  │ │ Store    │ │  api.put()   │
│ useHybrid │ │ auth     │ │  api.delete()│
│ useSwarm  │ │ Store    │ │              │
│ useApprv. │ │          │ │ Endpoints:   │
│ useCheck. │ │          │ │  ag-ui       │
│ useFile   │ │          │ │  orchestr.   │
│ useDevTls │ │          │ │  files       │
│ useChatTh │ │          │ │  devtools    │
└───────┬───┘ └──────────┘ └──────┬───────┘
        ↓                          ↓
┌─────────────────────────────────────────────────────┐
│                Backend API (FastAPI :8000)           │
│  /api/v1/ag-ui, /orchestration, /files, /devtools   │
│  SSE streaming for real-time events                  │
└─────────────────────────────────────────────────────┘
```

### Hook Dependency Graph

```
useUnifiedChat (core orchestrator)
├── useHybridMode (mode detection)
├── useUnifiedChatStore (Zustand state)
├── SSE connection (fetch-based)
└── History loading (GET messages)

useAGUI (standalone AG-UI)
├── useSharedState (state sync)
├── useOptimisticState (predictions)
└── SSE connection (fetch-based)

useOrchestration (intent routing)
└── orchestrationApi (classify, dialog, execute)

useCheckpoints
└── aguiApi (list, create, restore checkpoints)

useApprovalFlow
└── aguiApi (approve, reject)

useChatThreads
└── aguiApi (list, create, get threads)

useFileUpload
└── filesApi (upload with XHR progress)

useSwarmReal
├── useSwarmStore (Zustand state)
└── SSE connection (EventSource)

useDevToolsStream
└── SSE connection (EventSource)

useExecutionMetrics (no API, pure frontend)
useEventFilter (no API, pure frontend)
useSwarmMock (no API, mock data generator)
```

### Key Architecture Observations

1. **Two SSE Patterns**: `useUnifiedChat`/`useAGUI` use fetch-based SSE (for POST support), while `useSwarmReal`/`useDevToolsStream` use native EventSource (GET only)

2. **Store Strategy**: Auth state in `store/` (singleton), feature state in `stores/` (multiple stores). Both use Zustand. Auth and chat stores use `persist` middleware; swarm store is transient.

3. **Auth Flow**: authStore → raw fetch for login/register → sets token in Zustand persist → api/client.ts reads token from store → attaches Bearer header to all API calls → 401 triggers logout + redirect

4. **Guest User Flow**: First visit → generate UUID → attach X-Guest-Id header to all API calls → on login, migrate guest data to authenticated user → clear guest ID

5. **Orchestration Pipeline**: User message → useOrchestration.startOrchestration() → classify intent → guided dialog (if needed) → risk assessment → HITL approval (if needed) → hybrid execute

6. **Code Quality**: Zero `any` types, zero TODO/FIXME comments, comprehensive TypeScript interfaces. The main concern is production console statements (35+) and 2 hardcoded localhost fallback URLs.

---

*Analysis complete. 35 files fully read and documented.*

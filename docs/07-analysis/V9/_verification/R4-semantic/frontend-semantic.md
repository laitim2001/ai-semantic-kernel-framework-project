# Frontend Semantic File Summary (R4)

> V9 Round 4 Semantic Analysis | 2026-03-29
> Scope: `frontend/src/` -- all .ts/.tsx files excluding __tests__

---

## Root Files

### frontend/src/main.tsx (41 lines)
Application entry point. Renders `<App>` inside React.StrictMode with BrowserRouter, QueryClientProvider (TanStack Query, 5-min staleTime). No custom logic.

### frontend/src/App.tsx (149 lines)
Root routing component. Defines 30 routes: 4 standalone (login, signup, ag-ui-demo, swarm-test) + 26 protected under `<ProtectedRoute><AppLayout>`. Imports all page components.

### frontend/src/vite-env.d.ts (11 lines)
Vite environment type declarations. Defines `VITE_API_URL` and `VITE_APP_TITLE` in ImportMetaEnv.

---

## lib/

### frontend/src/lib/utils.ts (171 lines)
Utility library. Exports `cn()` (Tailwind merge), `formatRelativeTime()` (Traditional Chinese), `formatDate()`, `formatDateTime()`, `truncateText()`, `sleep()`, `generateId()`, `formatNumber()`, `formatCurrency()` (TWD), `formatPercent()`, `formatDuration()`. All locale-aware for zh-TW.

---

## utils/

### frontend/src/utils/guestUser.ts (171 lines)
Guest user ID management. Generates `guest-{UUID}` stored in localStorage(`ipa_guest_user_id`). Exports `getGuestUserId()`, `isGuestUser()`, `clearGuestUserId()`, `migrateGuestData(token)` (POST /auth/migrate-guest), `hasGuestData()`, `getGuestHeaders()` (X-Guest-Id header), `ensureGuestUserId()`.

---

## types/

### frontend/src/types/index.ts (232 lines)
Core shared type definitions. Defines `Status`, `PaginatedResponse<T>`, `Workflow`, `WorkflowDefinition`, `WorkflowGraphDefinition`, `WorkflowNode`, `WorkflowGraphNode`, `WorkflowEdge`, `Execution`, `ExecutionStep`, `Agent`, `ModelConfig`, `Template`, `Checkpoint`, `AuditLog`, `DashboardStats`, `ExecutionChartData`, `CostChartData`.

### frontend/src/types/devtools.ts (105 lines)
DevTools type definitions. Defines `TraceStatus`, `EventSeverity`, `Trace`, `TraceEvent`, `ListTracesParams`, `ListEventsParams`, `PaginatedResponse<T>` (devtools variant), `TraceDetail`, `DeleteTraceResponse`.

### frontend/src/types/unified-chat.ts (506 lines)
Unified chat type definitions. Defines `ExecutionMode`, `ModeSource`, `WorkflowStep`, `WorkflowState`, `TrackedToolCall`, `Checkpoint`, `TokenUsage`, `ExecutionTime`, `ToolCallStatistics`, `MessageStatistics`, `ExecutionMetrics`, `ConnectionStatus`, `StatusBarState`, `ModeToggleState`, `ChatInputState`, `FileAttachment`, `Attachment`, `ApprovalAction`, `ApprovalFlowState`, `UnifiedChatState`, `UnifiedChatActions`, plus all component props interfaces (`ChatHeaderProps`, `ChatAreaProps`, `ChatInputProps`, `StatusBarProps`, etc.) and hook return types.

### frontend/src/types/ag-ui.ts (458 lines)
AG-UI Protocol type definitions. Defines UI component types (`UIComponentType`, `FormFieldType`, `ChartType`), component schemas (`FormFieldDefinition`, `TableColumnDefinition`, `ChartData`, `UIComponentDefinition`), shared state types (`StateDiff`, `StateVersion`, `StateConflict`, `SharedState`), predictive state types (`PredictionResult`, `PredictionConfig`, `OptimisticState<T>`), AG-UI event types (`AGUIEventType`, `BaseAGUIEvent`, `StateSnapshotEvent`, `StateDeltaEvent`), chat types (`ChatMessage`, `ToolCallState`, `PendingApproval`, `OrchestrationMetadata`, `PipelineToolCall`, `GeneratedFile`), and run types (`RunAgentInput`, `AGUIRunState`).

---

## store/

### frontend/src/store/authStore.ts (323 lines)
Authentication Zustand store with `persist` middleware to `localStorage('ipa-auth-storage')`. Defines `User` and `AuthState` interfaces. Implements `login()` (OAuth2 form-encoded POST), `register()`, `logout()`, `refreshSession()`. Includes `apiLogin`, `apiRegister`, `apiGetMe`, `apiRefreshToken` helper functions. Auto-migrates guest data on login. Exports selectors: `selectUser`, `selectIsAuthenticated`, `selectIsLoading`, `selectError`, `selectToken`.

---

## stores/

### frontend/src/stores/unifiedChatStore.ts (509 lines)
Unified chat Zustand store with `persist` + `devtools` middleware. Persists to `localStorage('unified-chat-storage')` with partialize (last 100 messages, 20 checkpoints). Manages mode, messages, workflow state, tool calls, approvals, checkpoints, metrics, connection, error. Custom storage wrapper handles quota exceeded errors. Exports `initializeUnifiedChat()` and selectors (`selectMode`, `selectMessages`, `selectIsStreaming`, etc.).

### frontend/src/stores/swarmStore.ts (445 lines)
Agent swarm Zustand store with `immer` + `devtools` middleware. Manages `swarmStatus` (UIAgentSwarmStatus), selected worker, drawer state. Actions: `setSwarmStatus`, `updateSwarmProgress`, `completeSwarm`, `addWorker`, `updateWorkerProgress`, `updateWorkerThinking`, `updateWorkerToolCall`, `completeWorker`, `selectWorker`, `openDrawer`, `closeDrawer`. Exports 10 selectors including `selectCompletedWorkers`, `selectRunningWorkers`, `selectIsSwarmActive`.

---

## api/

### frontend/src/api/client.ts (173 lines)
Core Fetch API wrapper. Defines `ApiError` class and `fetchApi<T>()` function. Auto-injects Authorization Bearer token from `useAuthStore` and X-Guest-Id from `getGuestHeaders()`. Handles 401 (logout + redirect), 204 (empty response). Exports `api` object with `get`, `post`, `put`, `patch`, `delete` methods and `API_BASE_URL`.

### frontend/src/api/devtools.ts (88 lines)
DevTools API client. Exports `devToolsApi` with `listTraces()`, `getTrace()`, `getEvents()`, `deleteTrace()`. Uses `buildQueryString()` helper for query params. All use the core `api` fetch wrapper.

### frontend/src/api/endpoints/index.ts (126 lines)
Central barrel export for all API endpoint modules: `aguiApi`, `filesApi`, `orchestratorApi`, `sessionsApi`, `tasksApi`, `knowledgeApi`, `memoryApi`, `orchestrationApi`. Re-exports all types from each module.

### frontend/src/api/endpoints/ag-ui.ts (333 lines)
AG-UI API endpoints. Exports `aguiApi` with approval endpoints (`approve`, `reject`, `getPendingApprovals`), thread endpoints (`createThread`, `getThread`, `closeThread`), run endpoints (`getRunEndpoint`, `cancelRun`, `getRunStatus`), checkpoint endpoints (`getCheckpoints`, `restoreCheckpoint`, `deleteCheckpoint`). All methods include error wrapping with `ApiError`.

### frontend/src/api/endpoints/files.ts (389 lines)
File management API. Exports `filesApi` and standalone functions. Uses `XMLHttpRequest` for upload with progress tracking. Defines `FileMetadata`, `FileUploadResponse`, `GeneratedFile` types. Utility functions: `formatFileSize()`, `getFileCategory()`, `isAllowedFileType()`, `getMaxFileSize()`. CRUD: `uploadFile`, `listFiles`, `getFile`, `deleteFile`, `downloadFile`, `getFileContentText`, `getFileContentBlob`, `listFilesWithSession`.

### frontend/src/api/endpoints/orchestration.ts (326 lines)
Orchestration API endpoints. Exports `orchestrationApi` with intent routing (`classify`, `quickClassify`), guided dialog (`startDialog`, `respondToDialog`, `getDialogStatus`, `cancelDialog`), risk assessment (`assessRisk`), HITL approvals (`listApprovals`, `submitDecision`), hybrid execute (`execute`), metrics/health. Defines extensive types: `RoutingDecision`, `RiskAssessment`, `DialogStatusResponse`, `HybridExecuteRequest/Response`, etc.

### frontend/src/api/endpoints/knowledge.ts (184 lines)
Knowledge management API. Exports `knowledgeApi` with `uploadDocument` (multipart FormData), `searchKnowledge`, `getDocuments`, `deleteDocument`, `getSkills`, `getStatus`. Defines `KnowledgeDocument`, `KnowledgeSearchResult`, `AgentSkill`, `KnowledgeStatusResponse` types.

### frontend/src/api/endpoints/memory.ts (105 lines)
Memory system API. Exports `memoryApi` with `searchMemories`, `getUserMemories`, `getMemoryStats`, `deleteMemory`. Defines `MemoryItem`, `MemorySearchResponse`, `UserMemoriesResponse`, `MemoryStats` types.

### frontend/src/api/endpoints/sessions.ts (142 lines)
Session management API. Exports `sessionsApi` with `getSessions`, `getSession`, `getSessionMessages`, `getRecoverableSessions`, `resumeSession`, `deleteSession`. Defines `SessionStatus`, `SessionSummary`, `SessionDetail`, `SessionMessage`, `SessionResumeResponse` types.

### frontend/src/api/endpoints/tasks.ts (152 lines)
Task management API. Exports `tasksApi` with `getTasks` (wraps array into paginated response), `getTask`, `getTaskSteps`, `cancelTask`, `retryTask`. Defines `TaskStatus`, `TaskPriority`, `TaskStepStatus`, `TaskSummary`, `TaskStep`, `TaskDetail` types.

### frontend/src/api/endpoints/orchestrator.ts (145 lines)
Orchestrator chat API. Exports `orchestratorApi` with `sendMessage` (POST /orchestrator/chat), `getHealth`, `createStream` (SSE EventSource). Defines `OrchestratorMessage`, `OrchestratorMessageMetadata`, `OrchestratorToolCall`, `SendOrchestratorMessageRequest/Response`, `OrchestratorSSEEventType` types.

---

## hooks/

### frontend/src/hooks/index.ts (144 lines)
Central barrel export for all 25 custom hooks. Re-exports hooks and their associated types from individual files.

### frontend/src/hooks/useAGUI.ts (983 lines)
AG-UI Protocol main hook. Manages SSE connection via fetch ReadableStream, messages, tool calls (start/args/end), HITL approvals, heartbeat (S67-BF-1), step progress (S69-3). Integrates `useSharedState` and `useOptimisticState`. Handles 15 AG-UI event types in `handleSSEEvent()`. Supports auto-reconnect and abort control.

### frontend/src/hooks/useUnifiedChat.ts (~1313 lines)
Main chat orchestration hook. Manages AG-UI SSE connection lifecycle, all 15 event types, mode management via `useHybridMode`, dual-write to local state + `useUnifiedChatStore`, STATE_SNAPSHOT/DELTA handling, history loading from backend. The central orchestrator for the unified chat interface.

### frontend/src/hooks/useSSEChat.ts (~212 lines)
Pipeline SSE hook using fetch + ReadableStream. POST to /orchestrator/chat/stream. Parses SSE format, dispatches events to callbacks. Uses AbortController for cancellation. Sprint 145 Phase 42.

### frontend/src/hooks/useHybridMode.ts (270 lines)
Hybrid mode management. Auto-detects chat/workflow mode from AG-UI events with confidence threshold (>0.7). Supports manual override with session persistence. Tracks switch reason, confidence, timestamp. Exposes `dispatchModeDetection()` utility for triggering from anywhere.

### frontend/src/hooks/useApprovalFlow.ts (461 lines)
HITL approval flow management. Manages pending approvals, dialog state, timeout handling (auto-expire), mode switch confirmations. Optimistic updates with rollback on API failure. Auto-shows dialog for high/critical risk. Periodic expired approval cleanup (10s interval).

### frontend/src/hooks/useCheckpoints.ts (368 lines)
Checkpoint management. Loads checkpoints from API, tracks current checkpoint, provides restore with confirmation dialog. Supports both direct restore and confirmation-based restore. Disables restore during execution.

### frontend/src/hooks/useExecutionMetrics.ts (464 lines)
Execution metrics tracking. Manages token usage (with formatted display like "1.2K/4K"), execution timer (interval-based), tool call statistics (total/completed/failed/pending), message counts by role. Exports `isHighUsage` (>75%) and `isCriticalUsage` (>90%) computed values.

### frontend/src/hooks/useFileUpload.ts (~200 lines)
File upload queue management. Handles file validation (type, size), upload with progress tracking, attachment state management. Integrates with filesApi.

### frontend/src/hooks/useChatThreads.ts (~200 lines)
Chat thread CRUD with localStorage persistence. Per-user isolation. Message persistence per thread for thread switching. Handles race conditions on re-login.

### frontend/src/hooks/useSwarmMock.ts (~623 lines)
Mock swarm hook for testing. Provides complete local state management without backend. Includes preset scenarios (ETL, SecurityAudit, DataPipeline). Granular actions for thinking, tool calls, progress. Uses independent useState (does NOT use useSwarmStore).

### frontend/src/hooks/useSwarmReal.ts (~603 lines)
Real swarm SSE hook. Connects to /api/v1/swarm/demo/{swarmId}/events via EventSource. Converts snake_case events to camelCase state. Demo scenario selection. Uses independent useState (does NOT use useSwarmStore).

### frontend/src/hooks/useOrchestration.ts (~350 lines)
Phase 28 orchestration flow. Manages three-layer intent routing, guided dialog, risk assessment, HITL approval flow, hybrid execution. Partially superseded by pipeline SSE path.

### frontend/src/hooks/useOrchestratorChat.ts (~200 lines)
Orchestrator chat integration. Manages message send/receive via /orchestrator/chat, SSE streaming responses, intent/risk/execution mode metadata.

### frontend/src/hooks/useSharedState.ts (~100 lines)
AG-UI shared state hook. Bidirectional server sync via SSE, conflict resolution, offline support. Manages state diffs and version tracking.

### frontend/src/hooks/useOptimisticState.ts (~100 lines)
Optimistic/predictive state updates. Immediate UI updates with server confirmation or rollback. Manages prediction lifecycle (pending/confirmed/rolled_back/expired).

### frontend/src/hooks/useDevTools.ts (~150 lines)
DevUI data fetching. React Query hooks wrapping devToolsApi for traces and events.

### frontend/src/hooks/useDevToolsStream.ts (~100 lines)
DevUI SSE streaming. EventSource-based hook for real-time trace event updates.

### frontend/src/hooks/useEventFilter.ts (~80 lines)
Event filtering with URL sync via useSearchParams. Manages filter state for DevUI event views.

### frontend/src/hooks/useKnowledge.ts (~150 lines)
Knowledge base React Query hooks. Exports useKnowledgeSearch, useDocuments, useUploadDocument, useDeleteDocument, useSkills, useKnowledgeStatus.

### frontend/src/hooks/useMemory.ts (~150 lines)
Memory system React Query hooks. Exports useMemorySearch, useUserMemories, useMemoryStats, useDeleteMemory.

### frontend/src/hooks/useSessions.ts (~150 lines)
Session management React Query hooks. Exports useSessions, useSession, useSessionMessages, useRecoverableSessions, useResumeSession, useDeleteSession.

### frontend/src/hooks/useTasks.ts (~150 lines)
Task management React Query hooks. Exports useTasks, useTask, useTaskSteps, useCancelTask, useRetryTask.

### frontend/src/hooks/useToolCallEvents.ts (~100 lines)
Tool call event management. Converts pipeline tool call data to TrackedToolCall format for ToolCallTracker display.

### frontend/src/hooks/useTypewriterEffect.ts (~80 lines)
Typewriter animation effect. Progressively reveals text character-by-character to simulate LLM streaming for synchronous responses.

---

## components/ui/ (Shadcn UI Base)

### frontend/src/components/ui/Badge.tsx
Shadcn Badge component. Renders styled span with variant support (default, secondary, destructive, outline).

### frontend/src/components/ui/Button.tsx
Shadcn Button component. Variants: default, destructive, outline, secondary, ghost, link. Sizes: default, sm, lg, icon. Uses Slot for asChild pattern.

### frontend/src/components/ui/Card.tsx
Shadcn Card component. Exports Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter.

### frontend/src/components/ui/index.ts
Barrel export for all UI components.

### frontend/src/components/ui/Input.tsx
Shadcn Input component. Styled native input with className merge.

### frontend/src/components/ui/Textarea.tsx
Shadcn Textarea component. Styled native textarea.

### frontend/src/components/ui/Label.tsx
Shadcn Label component. Based on @radix-ui/react-label.

### frontend/src/components/ui/Checkbox.tsx
Shadcn Checkbox component. Based on @radix-ui/react-checkbox with check indicator.

### frontend/src/components/ui/RadioGroup.tsx
Shadcn RadioGroup component. Based on @radix-ui/react-radio-group.

### frontend/src/components/ui/Table.tsx
Shadcn Table component. Exports Table, TableHeader, TableBody, TableFooter, TableRow, TableHead, TableCell, TableCaption.

### frontend/src/components/ui/Tooltip.tsx
Shadcn Tooltip component. Based on @radix-ui/react-tooltip with Provider, Trigger, Content.

### frontend/src/components/ui/Collapsible.tsx
Shadcn Collapsible component. Re-exports @radix-ui/react-collapsible primitives.

### frontend/src/components/ui/Select.tsx
Shadcn Select component. Based on @radix-ui/react-select with Trigger, Content, Item, Group, Separator.

### frontend/src/components/ui/dialog.tsx
Shadcn Dialog component. Based on @radix-ui/react-dialog with Overlay, Content, Header, Footer, Title, Description.

### frontend/src/components/ui/Progress.tsx
Shadcn Progress component. Based on @radix-ui/react-progress with animated indicator bar.

### frontend/src/components/ui/Sheet.tsx
Shadcn Sheet component. Slide-over panel based on @radix-ui/react-dialog with side variants (top, bottom, left, right).

### frontend/src/components/ui/Separator.tsx
Shadcn Separator component. Based on @radix-ui/react-separator (horizontal/vertical).

### frontend/src/components/ui/ScrollArea.tsx
Shadcn ScrollArea component. Based on @radix-ui/react-scroll-area with custom scrollbar styling.

---

## components/shared/

### frontend/src/components/shared/EmptyState.tsx
Empty state placeholder. Renders icon, title, description, optional action button. Used across list views.

### frontend/src/components/shared/LoadingSpinner.tsx
Loading spinner component. Animated SVG spinner with configurable size and color.

### frontend/src/components/shared/StatusBadge.tsx
Status badge component. Color-coded badge for status display (pending=yellow, running=blue, completed=green, failed=red).

### frontend/src/components/shared/index.ts
Barrel export for EmptyState, LoadingSpinner, StatusBadge.

---

## components/auth/

### frontend/src/components/auth/ProtectedRoute.tsx
Route guard component. Checks `useAuthStore.isAuthenticated`. Redirects to /login if not authenticated. Renders children if authenticated.

---

## components/layout/

### frontend/src/components/layout/AppLayout.tsx
Main application layout. Renders Header + Sidebar + Outlet (React Router). Responsive sidebar toggle. Uses Zustand auth state for user display.

### frontend/src/components/layout/Header.tsx
Top navigation header. Displays app title, navigation links, user menu. Responsive hamburger menu for mobile.

### frontend/src/components/layout/UserMenu.tsx
User dropdown menu. Shows user email/name, role, logout button. Uses authStore for user data and logout action.

### frontend/src/components/layout/Sidebar.tsx
Side navigation component. Navigation links to dashboard, chat, workflows, agents, templates, sessions, tasks, knowledge, memory, approvals, audit, devui. Active route highlighting.

### frontend/src/components/layout/index.ts
Barrel export for AppLayout, Header, Sidebar, UserMenu.

---

## components/ag-ui/chat/

### frontend/src/components/ag-ui/chat/ChatContainer.tsx
AG-UI chat container. Renders message list with streaming indicator. Manages scroll-to-bottom behavior.

### frontend/src/components/ag-ui/chat/MessageInput.tsx
AG-UI message input. Text input with send button. Handles Enter key submission and multi-line support.

### frontend/src/components/ag-ui/chat/MessageBubble.tsx
AG-UI message bubble. Renders user/assistant messages with role-based styling. Supports markdown rendering.

### frontend/src/components/ag-ui/chat/StreamingIndicator.tsx
Streaming indicator. Animated dots/pulse showing LLM is generating response.

### frontend/src/components/ag-ui/chat/ToolCallCard.tsx
Tool call display card. Shows tool name, arguments, status (pending/executing/completed/failed), result. Color-coded status.

### frontend/src/components/ag-ui/chat/index.ts
Barrel export for AG-UI chat components.

---

## components/ag-ui/hitl/

### frontend/src/components/ag-ui/hitl/ApprovalBanner.tsx
HITL approval banner. Top-of-chat notification when tool call requires approval. Shows tool name, risk level.

### frontend/src/components/ag-ui/hitl/ApprovalDialog.tsx
HITL approval dialog. Modal dialog for approving/rejecting tool calls. Shows tool details, arguments, risk assessment, reasoning.

### frontend/src/components/ag-ui/hitl/ApprovalList.tsx
Pending approvals list. Renders list of pending HITL approvals with approve/reject actions per item.

### frontend/src/components/ag-ui/hitl/RiskBadge.tsx
Risk level badge. Color-coded: low=green, medium=yellow, high=orange, critical=red. Shows risk level text.

### frontend/src/components/ag-ui/hitl/index.ts
Barrel export for HITL components.

---

## components/ag-ui/advanced/

### frontend/src/components/ag-ui/advanced/CustomUIRenderer.tsx
AG-UI Generative UI renderer. Dispatches to DynamicForm, DynamicChart, DynamicCard, DynamicTable based on componentType. Handles component events.

### frontend/src/components/ag-ui/advanced/DynamicForm.tsx
Dynamic form renderer. Generates form from FormFieldDefinition array. Supports text, number, email, select, checkbox, radio, date, file inputs. Handles validation and submission.

### frontend/src/components/ag-ui/advanced/DynamicTable.tsx
Dynamic table renderer. Generates table from column definitions and row data. Supports sorting, filtering, pagination.

### frontend/src/components/ag-ui/advanced/DynamicCard.tsx
Dynamic card renderer. Renders card with title, subtitle, content, image, action buttons.

### frontend/src/components/ag-ui/advanced/DynamicChart.tsx
Dynamic chart renderer. Renders charts using Recharts based on ChartData. Supports line, bar, pie, area, scatter, doughnut types.

### frontend/src/components/ag-ui/advanced/StateDebugger.tsx
State debugger panel. Displays shared state as formatted JSON. Shows state version, sync status, pending diffs, conflicts.

### frontend/src/components/ag-ui/advanced/OptimisticIndicator.tsx
Optimistic update indicator. Shows pending predictions count and status (optimistic/synced). Visual feedback for predictive state updates.

### frontend/src/components/ag-ui/advanced/index.ts
Barrel export for advanced AG-UI components.

---

## components/DevUI/

### frontend/src/components/DevUI/EventDetail.tsx
Event detail panel. Shows full event data as formatted JSON with metadata, tags, severity, duration.

### frontend/src/components/DevUI/DurationBar.tsx
Duration visualization bar. Horizontal bar showing relative duration. Color-coded by severity.

### frontend/src/components/DevUI/TimelineNode.tsx
Timeline node component. Single node in event timeline with timestamp, event type icon, duration.

### frontend/src/components/DevUI/Timeline.tsx
Event timeline component. Vertical timeline of trace events. Connects TimelineNode components.

### frontend/src/components/DevUI/EventPanel.tsx
Event panel container. Combines EventList, EventDetail, and EventFilter in a tabbed layout.

### frontend/src/components/DevUI/EventList.tsx
Event list view. Sortable, filterable list of trace events with severity indicators.

### frontend/src/components/DevUI/EventTree.tsx
Event tree view. Hierarchical tree of parent-child events using TreeNode.

### frontend/src/components/DevUI/LLMEventPanel.tsx
LLM-specific event panel. Shows LLM call details: model, tokens, latency, prompt/response.

### frontend/src/components/DevUI/ToolEventPanel.tsx
Tool-specific event panel. Shows tool execution details: tool name, input args, output, duration, status.

### frontend/src/components/DevUI/TreeNode.tsx
Tree node component. Expandable/collapsible tree node with indent levels. Used by EventTree.

### frontend/src/components/DevUI/StatCard.tsx
Statistics card. Displays metric with label, value, trend indicator, and optional chart sparkline.

### frontend/src/components/DevUI/EventPieChart.tsx
Event distribution pie chart. Shows event type distribution using Recharts PieChart.

### frontend/src/components/DevUI/LiveIndicator.tsx
Live connection indicator. Pulsing dot with "Live" text when SSE is connected.

### frontend/src/components/DevUI/EventFilter.tsx
Event filter controls. Dropdowns and search for filtering by event type, severity, time range.

### frontend/src/components/DevUI/Statistics.tsx
Statistics dashboard. Aggregates and displays event statistics: counts by type, severity distribution, avg duration.

---

## components/unified-chat/ (Main Chat Interface)

### frontend/src/components/unified-chat/index.ts
Barrel export for unified-chat components.

### frontend/src/components/unified-chat/ChatHeader.tsx
Chat header bar. Mode toggle (chat/workflow), connection status indicator, reconnect button, title display. Props: currentMode, autoMode, isManuallyOverridden, connection, onModeChange.

### frontend/src/components/unified-chat/ChatArea.tsx
Chat message area. Renders MessageList + streaming indicator. Handles scroll-to-bottom, auto-scroll on new messages. Props: messages, isStreaming, pendingApprovals, onApprove, onReject.

### frontend/src/components/unified-chat/ChatInput.tsx
Message input component. Multi-line textarea with send button, file attachment support, streaming cancel button. Handles Enter/Shift+Enter, paste, drag-drop. Props: onSend, disabled, isStreaming, attachments, onAttach.

### frontend/src/components/unified-chat/MessageList.tsx
Message list renderer. Maps ChatMessage array to message bubbles with IntentStatusChip, ApprovalMessageCard, FileMessage, ToolCallTracker, CustomUIRenderer per message.

### frontend/src/components/unified-chat/ConnectionStatus.tsx
SSE connection status display. Shows connected/connecting/disconnected/error with color-coded indicator.

### frontend/src/components/unified-chat/ModeIndicator.tsx
Execution mode indicator. Shows current mode (chat/workflow) with auto/manual source badge.

### frontend/src/components/unified-chat/RiskIndicator.tsx
Risk level indicator. Color-coded risk badge (low/medium/high/critical) with score display.

### frontend/src/components/unified-chat/StatusBar.tsx
Bottom status bar. Displays mode, risk level, execution metrics (tokens, time), checkpoint indicator, heartbeat status.

### frontend/src/components/unified-chat/InlineApproval.tsx
Inline approval component. Renders approve/reject buttons within message flow for HITL tool calls. Compact variant available.

### frontend/src/components/unified-chat/ApprovalDialog.tsx
Approval confirmation dialog. Modal for tool call approval with risk details, arguments display, approve/reject with optional reason.

### frontend/src/components/unified-chat/ApprovalMessageCard.tsx
Approval message card (Sprint 99). Inline card within chat showing approval request with tool details, risk badge, approve/reject buttons.

### frontend/src/components/unified-chat/ModeSwitchConfirmDialog.tsx
Mode switch confirmation dialog. Shows when mode auto-detection triggers a switch. Displays current/new mode, confidence, reason. Confirm/cancel buttons.

### frontend/src/components/unified-chat/RestoreConfirmDialog.tsx
Checkpoint restore confirmation. Dialog confirming restore to a specific checkpoint with timestamp and label.

### frontend/src/components/unified-chat/ErrorBoundary.tsx
React error boundary for unified-chat. Catches render errors, displays fallback UI with retry button.

### frontend/src/components/unified-chat/StepProgress.tsx
Workflow step progress. Shows numbered steps with status indicators (pending/running/completed/failed). Linear progress display.

### frontend/src/components/unified-chat/StepProgressEnhanced.tsx
Enhanced step progress (Sprint 69). Hierarchical progress with expandable substeps. Shows step name, progress bar, substep status.

### frontend/src/components/unified-chat/ToolCallTracker.tsx
Tool call tracking display. Shows list of tool calls with name, status, timing, arguments preview. Configurable maxVisible and showTimings.

### frontend/src/components/unified-chat/CheckpointList.tsx
Checkpoint list component. Displays available checkpoints with timestamps, labels, restore buttons. Configurable maxVisible.

### frontend/src/components/unified-chat/WorkflowSidePanel.tsx
Right side panel for workflow mode. Contains StepProgressEnhanced, ToolCallTracker, CheckpointList. Collapsible.

### frontend/src/components/unified-chat/FileUpload.tsx
File upload component (Sprint 75). Drag-drop zone + file picker. Validates file type and size. Shows upload progress.

### frontend/src/components/unified-chat/AttachmentPreview.tsx
Attachment preview bar. Shows thumbnails of attached files before sending. Remove button per attachment. Progress indicator for uploading files.

### frontend/src/components/unified-chat/FileMessage.tsx
File message renderer (Sprint 76). Displays file attachments in messages with icon, name, size, download button.

### frontend/src/components/unified-chat/FileRenderer.tsx
File content renderer. Dispatches to ImagePreview, CodePreview, or TextPreview based on MIME type.

### frontend/src/components/unified-chat/OrchestrationPanel.tsx
Orchestration debug panel (Phase 28). Collapsible panel showing intent routing results, risk assessment, dialog state, execution history.

### frontend/src/components/unified-chat/ChatHistoryPanel.tsx
Left sidebar chat history. Lists chat threads with timestamps, message preview. New thread button. Session resume for interrupted sessions.

### frontend/src/components/unified-chat/IntentStatusChip.tsx
Intent classification chip (Phase 41). Displays intent category, confidence, routing layer, risk level. Expandable detail view with processing time and framework used.

### frontend/src/components/unified-chat/MemoryHint.tsx
Memory hint display (Phase 41). Shows related memories from mem0 system. Expandable memory items with relevance scores.

### frontend/src/components/unified-chat/TaskProgressCard.tsx
Task progress card. Shows task name, status, progress bar, agent info, duration. Links to task detail page.

---

## components/unified-chat/renderers/

### frontend/src/components/unified-chat/renderers/ImagePreview.tsx
Image file preview. Renders image with lightbox support, zoom, alt text.

### frontend/src/components/unified-chat/renderers/CodePreview.tsx
Code file preview. Syntax-highlighted code display with language detection, line numbers, copy button.

### frontend/src/components/unified-chat/renderers/TextPreview.tsx
Text file preview. Plain text display with word wrap and scrollable container.

### frontend/src/components/unified-chat/renderers/index.ts
Barrel export for file renderers.

---

## components/unified-chat/agent-swarm/

### frontend/src/components/unified-chat/agent-swarm/index.ts
Barrel export for agent swarm components.

### frontend/src/components/unified-chat/agent-swarm/AgentSwarmPanel.tsx
Main swarm container panel. Renders SwarmHeader, OverallProgress, WorkerCardList. Conditionally shows when swarm is active.

### frontend/src/components/unified-chat/agent-swarm/SwarmHeader.tsx
Swarm header. Displays swarm title, status badge, worker count, elapsed time.

### frontend/src/components/unified-chat/agent-swarm/SwarmStatusBadges.tsx
Swarm status badges. Shows counts: running workers, completed, failed. Color-coded badges.

### frontend/src/components/unified-chat/agent-swarm/OverallProgress.tsx
Overall swarm progress. Horizontal progress bar with percentage. Shows completed/total workers.

### frontend/src/components/unified-chat/agent-swarm/WorkerCard.tsx
Individual worker card. Shows worker name, type icon, status, progress bar, current action, tool call count. Click opens detail drawer.

### frontend/src/components/unified-chat/agent-swarm/WorkerCardList.tsx
Worker card list. Maps workers array to WorkerCard components. Handles empty state.

### frontend/src/components/unified-chat/agent-swarm/WorkerActionList.tsx
Worker action list. Timeline of worker actions (thinking, tool calls, messages) in chronological order.

### frontend/src/components/unified-chat/agent-swarm/WorkerDetailDrawer.tsx
Worker detail slide-over drawer. Uses Sheet component. Contains WorkerDetailHeader, CurrentTask, ExtendedThinkingPanel, ToolCallsPanel, MessageHistory, CheckpointPanel.

### frontend/src/components/unified-chat/agent-swarm/WorkerDetailHeader.tsx
Worker detail header. Shows worker name, type, status badge, progress, start/completion times.

### frontend/src/components/unified-chat/agent-swarm/CurrentTask.tsx
Current task display. Shows the worker's current task description and progress.

### frontend/src/components/unified-chat/agent-swarm/ExtendedThinkingPanel.tsx
Extended thinking display. Shows AI thinking process text with timestamps. Collapsible thinking blocks.

### frontend/src/components/unified-chat/agent-swarm/ToolCallsPanel.tsx
Tool calls panel. Lists all tool calls for a worker. Uses ToolCallItem sub-component.

### frontend/src/components/unified-chat/agent-swarm/ToolCallItem.tsx
Individual tool call item. Shows tool name, status, input/output, duration, error if any.

### frontend/src/components/unified-chat/agent-swarm/MessageHistory.tsx
Worker message history. Chronological list of messages from/to the worker agent.

### frontend/src/components/unified-chat/agent-swarm/CheckpointPanel.tsx
Worker checkpoint panel. Shows checkpoints for a specific worker with restore capability.

---

## components/unified-chat/agent-swarm/hooks/

### frontend/src/components/unified-chat/agent-swarm/hooks/index.ts
Barrel export for swarm hooks.

### frontend/src/components/unified-chat/agent-swarm/hooks/useSwarmEvents.ts
Swarm SSE event handler. Processes swarm lifecycle events (created, worker_started, progress, thinking, tool_call, completed). Converts snake_case payloads to camelCase.

### frontend/src/components/unified-chat/agent-swarm/hooks/useWorkerDetail.ts
Worker detail hook. Fetches detailed worker info when drawer opens. Manages loading and error state.

### frontend/src/components/unified-chat/agent-swarm/hooks/useSwarmStatus.ts
Swarm status hook. Derives computed status values from swarmStore: isActive, completionPercentage, runningCount, etc.

### frontend/src/components/unified-chat/agent-swarm/hooks/useSwarmEventHandler.ts
Swarm event handler bridge. Converts SSE events to swarmStore actions. Maps snake_case event payloads to camelCase store updates.

---

## components/unified-chat/agent-swarm/types/

### frontend/src/components/unified-chat/agent-swarm/types/index.ts
Swarm UI type definitions. Defines `UIAgentSwarmStatus`, `UIWorkerSummary`, `WorkerDetail`, `ThinkingContent`, `ToolCallInfo`, `WorkerType`, component props interfaces, and `SnakeToCamelCase<S>` utility type.

### frontend/src/components/unified-chat/agent-swarm/types/events.ts
Swarm SSE event payload types (snake_case). Defines `SwarmCreatedPayload`, `WorkerStartedPayload`, `WorkerProgressPayload`, `WorkerThinkingPayload`, `WorkerToolCallPayload`, `WorkerCompletedPayload`, `SwarmCompletedPayload`.

---

## pages/

### frontend/src/pages/UnifiedChat.tsx (~1403 lines)
Main chat page orchestrator. The most complex component. 20+ useState, 15+ useCallback, 10+ useEffect. Integrates useSSEChat (pipeline path), useUnifiedChat (AG-UI path), useSwarmStore, useChatThreads, useFileUpload, useOrchestration, useExecutionMetrics. Handles mode selection (chat/workflow/swarm), inline HITL approval, memory search, typewriter effect, orchestration metadata display.

### frontend/src/pages/SwarmTestPage.tsx
Agent Swarm test page. Standalone full-screen layout. Toggles between useSwarmMock and useSwarmReal. Renders AgentSwarmPanel with mock/real data.

### frontend/src/pages/auth/LoginPage.tsx
Login page. Email/password form, calls authStore.login(). Links to signup. Full-screen standalone layout.

### frontend/src/pages/auth/SignupPage.tsx
Registration page. Email/password/name form, calls authStore.register(). Links to login. Full-screen standalone layout.

### frontend/src/pages/dashboard/DashboardPage.tsx
Main dashboard. Renders StatsCards, ExecutionChart, PendingApprovals, RecentExecutions. Uses React Query for data fetching.

### frontend/src/pages/dashboard/PerformancePage.tsx
Performance monitoring page. Charts for execution times, success rates, LLM costs.

### frontend/src/pages/dashboard/components/StatsCards.tsx
Dashboard statistics cards. Displays total workflows, active, executions, success rate, pending approvals, LLM costs.

### frontend/src/pages/dashboard/components/ExecutionChart.tsx
Execution trend chart. Line/bar chart showing daily execution counts (success/failed) using Recharts.

### frontend/src/pages/dashboard/components/PendingApprovals.tsx
Pending approvals widget. Lists recent pending HITL approvals on dashboard with quick actions.

### frontend/src/pages/dashboard/components/RecentExecutions.tsx
Recent executions widget. Table of recent workflow executions with status, duration, workflow name.

### frontend/src/pages/dashboard/components/index.ts
Barrel export for dashboard components.

### frontend/src/pages/agents/AgentsPage.tsx
Agent list page. Displays agents in card/list view with search, filter by category. Create agent button.

### frontend/src/pages/agents/AgentDetailPage.tsx
Agent detail page. Shows agent configuration, instructions, tools, model config, execution stats.

### frontend/src/pages/agents/CreateAgentPage.tsx
Create agent form. Name, description, category, instructions, tools selection, model configuration.

### frontend/src/pages/agents/EditAgentPage.tsx
Edit agent form. Pre-filled form for existing agent. Same fields as create.

### frontend/src/pages/workflows/WorkflowsPage.tsx
Workflow list page. Card/list view with status filter, search. Create workflow button.

### frontend/src/pages/workflows/WorkflowDetailPage.tsx
Workflow detail page. Shows workflow definition, execution history, graph visualization.

### frontend/src/pages/workflows/CreateWorkflowPage.tsx
Create workflow form. Name, description, trigger type, trigger config, graph definition.

### frontend/src/pages/workflows/EditWorkflowPage.tsx
Edit workflow form. Pre-filled form for existing workflow.

### frontend/src/pages/workflows/WorkflowEditorPage.tsx
Workflow DAG editor (Phase 34, Sprint 133). Visual workflow editor using React Flow for node/edge editing.

### frontend/src/pages/approvals/ApprovalsPage.tsx
Approvals management page. Lists all pending/resolved approvals with filters and actions.

### frontend/src/pages/audit/AuditPage.tsx
Audit log page. Searchable, filterable audit log table with timestamp, action, resource, user.

### frontend/src/pages/templates/TemplatesPage.tsx
Template marketplace page. Displays available agent templates with categories, search, ratings.

### frontend/src/pages/sessions/SessionsPage.tsx
Session list page (Phase 40, Sprint 138). Lists sessions with status filter, message count, last activity.

### frontend/src/pages/sessions/SessionDetailPage.tsx
Session detail page. Shows session metadata, message history, associated tasks.

### frontend/src/pages/tasks/TaskDashboardPage.tsx
Task dashboard page (Phase 40, Sprint 139). Task list with status/priority filters, progress bars.

### frontend/src/pages/tasks/TaskDetailPage.tsx
Task detail page. Shows task steps, progress, agent info, input/output, error details.

### frontend/src/pages/knowledge/KnowledgePage.tsx
Knowledge management page (Phase 40, Sprint 140). Document list, upload, search, skills display, service status.

### frontend/src/pages/memory/MemoryPage.tsx
Memory management page (Phase 40, Sprint 140). Memory search, user memories list, statistics.

### frontend/src/pages/ag-ui/AGUIDemoPage.tsx
AG-UI demo page. Standalone full-screen. Tabbed demo sections for all AG-UI features.

### frontend/src/pages/ag-ui/components/AgenticChatDemo.tsx
AG-UI chat demo. Uses useAGUI hook for interactive chat demonstration.

### frontend/src/pages/ag-ui/components/ToolRenderingDemo.tsx
Tool rendering demo. Demonstrates ToolCallCard with various tool states.

### frontend/src/pages/ag-ui/components/ToolUIDemo.tsx
Tool UI demo. Demonstrates tool-based Generative UI with CustomUIRenderer.

### frontend/src/pages/ag-ui/components/HITLDemo.tsx
HITL demo. Demonstrates ApprovalDialog, ApprovalBanner, InlineApproval components.

### frontend/src/pages/ag-ui/components/SharedStateDemo.tsx
Shared state demo. Demonstrates useSharedState with state sync visualization.

### frontend/src/pages/ag-ui/components/PredictiveDemo.tsx
Predictive state demo. Demonstrates useOptimisticState with optimistic updates.

### frontend/src/pages/ag-ui/components/GenerativeUIDemo.tsx
Generative UI demo. Demonstrates DynamicForm, DynamicChart, DynamicCard, DynamicTable generation.

### frontend/src/pages/ag-ui/components/EventLogPanel.tsx
Event log panel. Displays AG-UI SSE events in real-time log format.

### frontend/src/pages/ag-ui/components/index.ts
Barrel export for AG-UI demo components.

### frontend/src/pages/DevUI/index.tsx
DevUI overview page. Dashboard with trace summary, event statistics, connection status.

### frontend/src/pages/DevUI/Layout.tsx
DevUI layout component. Side navigation (overview, traces, monitor, settings, AG-UI test) + Outlet.

### frontend/src/pages/DevUI/TraceList.tsx
Trace list page. Paginated table of execution traces with status, duration, event count. Delete action.

### frontend/src/pages/DevUI/TraceDetail.tsx
Trace detail page. Shows trace metadata + event timeline/tree/list views with EventPanel.

### frontend/src/pages/DevUI/LiveMonitor.tsx
Live monitor page. Real-time SSE event stream display using useDevToolsStream. Auto-scroll, pause/resume.

### frontend/src/pages/DevUI/Settings.tsx
DevUI settings page. Configuration for trace retention, event filters, connection settings.

### frontend/src/pages/DevUI/AGUITestPanel.tsx
AG-UI test panel. Interactive testing interface for AG-UI protocol events.

---

## File Count Summary

| Category | Non-test Files |
|----------|---------------|
| Root (main, App, vite-env) | 3 |
| lib/ | 1 |
| utils/ | 1 |
| types/ | 4 |
| store/ | 1 |
| stores/ | 2 |
| api/ | 11 |
| hooks/ | 25 |
| components/ui/ | 18 |
| components/shared/ | 4 |
| components/auth/ | 1 |
| components/layout/ | 5 |
| components/ag-ui/ | 19 |
| components/DevUI/ | 15 |
| components/unified-chat/ (core) | 27 |
| components/unified-chat/renderers/ | 4 |
| components/unified-chat/agent-swarm/ (components) | 16 |
| components/unified-chat/agent-swarm/hooks/ | 5 |
| components/unified-chat/agent-swarm/types/ | 2 |
| pages/ | 46 |
| **TOTAL** | **210** |

> Note: With __tests__ files included, the total is ~236 files. Test files (26) are excluded from this semantic analysis.

---

*Analysis conducted on 2026-03-29 based on full source reading of all frontend/src files.*
*V9 R4 Semantic Analysis -- Frontend*

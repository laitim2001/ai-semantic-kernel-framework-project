# Phase 3E: Frontend Pages Analysis (Part 1)

> Agent E1 — Full analysis of `frontend/src/pages/` (41 files)
> Analysis Date: 2026-03-15

---

## Table of Contents

1. [Summary Statistics](#1-summary-statistics)
2. [UnifiedChat.tsx — Primary User Page (Deep Analysis)](#2-unifiedchattsx)
3. [SwarmTestPage.tsx](#3-swarmtestpagetsx)
4. [Dashboard Pages](#4-dashboard-pages)
5. [Agent Management Pages](#5-agent-management-pages)
6. [Workflow Management Pages](#6-workflow-management-pages)
7. [Auth Pages](#7-auth-pages)
8. [Approvals & Audit Pages](#8-approvals--audit-pages)
9. [Templates Page](#9-templates-page)
10. [DevUI Pages](#10-devui-pages)
11. [AG-UI Demo Pages](#11-ag-ui-demo-pages)
12. [Cross-Cutting Issues](#12-cross-cutting-issues)
13. [D-Series Cross-Reference](#13-d-series-cross-reference)

---

## 1. Summary Statistics

| Metric | Value |
|--------|-------|
| Total files scanned | 41 |
| Total estimated lines | ~10,200 |
| Pages using real API calls | 15 |
| Pages with mock/hardcoded fallback | 10 |
| Pages that are placeholders | 2 (LiveMonitor, Settings) |
| Pages with console.log in production code | 2 (UnifiedChat, TraceDetail) |
| TODO comments found | 2 (UnifiedChat) |

### File Inventory

| # | File Path | Lines | Component |
|---|-----------|-------|-----------|
| 1 | `pages/UnifiedChat.tsx` | ~900 | UnifiedChat |
| 2 | `pages/SwarmTestPage.tsx` | ~845 | SwarmTestPage |
| 3 | `pages/dashboard/DashboardPage.tsx` | ~87 | DashboardPage |
| 4 | `pages/dashboard/PerformancePage.tsx` | ~469 | PerformancePage |
| 5 | `pages/dashboard/components/StatsCards.tsx` | ~70 | StatsCards |
| 6 | `pages/dashboard/components/ExecutionChart.tsx` | ~100 | ExecutionChart |
| 7 | `pages/dashboard/components/PendingApprovals.tsx` | ~110 | PendingApprovals |
| 8 | `pages/dashboard/components/RecentExecutions.tsx` | ~130 | RecentExecutions |
| 9 | `pages/dashboard/components/index.ts` | ~5 | barrel export |
| 10 | `pages/agents/AgentsPage.tsx` | ~230 | AgentsPage |
| 11 | `pages/agents/AgentDetailPage.tsx` | ~360 | AgentDetailPage |
| 12 | `pages/agents/CreateAgentPage.tsx` | ~750 | CreateAgentPage |
| 13 | `pages/agents/EditAgentPage.tsx` | ~700 | EditAgentPage |
| 14 | `pages/workflows/WorkflowsPage.tsx` | ~170 | WorkflowsPage |
| 15 | `pages/workflows/WorkflowDetailPage.tsx` | ~400 | WorkflowDetailPage |
| 16 | `pages/workflows/CreateWorkflowPage.tsx` | ~700 | CreateWorkflowPage |
| 17 | `pages/workflows/EditWorkflowPage.tsx` | ~750 | EditWorkflowPage |
| 18 | `pages/workflows/WorkflowEditorPage.tsx` | ~21 | WorkflowEditorPage |
| 19 | `pages/auth/LoginPage.tsx` | ~230 | LoginPage |
| 20 | `pages/auth/SignupPage.tsx` | ~290 | SignupPage |
| 21 | `pages/approvals/ApprovalsPage.tsx` | ~260 | ApprovalsPage |
| 22 | `pages/audit/AuditPage.tsx` | ~180 | AuditPage |
| 23 | `pages/templates/TemplatesPage.tsx` | ~230 | TemplatesPage |
| 24 | `pages/DevUI/index.tsx` | ~160 | DevUIOverview |
| 25 | `pages/DevUI/Layout.tsx` | ~140 | DevUILayout |
| 26 | `pages/DevUI/TraceList.tsx` | ~340 | TraceList |
| 27 | `pages/DevUI/TraceDetail.tsx` | ~530 | TraceDetail |
| 28 | `pages/DevUI/LiveMonitor.tsx` | ~66 | LiveMonitor (placeholder) |
| 29 | `pages/DevUI/Settings.tsx` | ~66 | Settings (placeholder) |
| 30 | `pages/DevUI/AGUITestPanel.tsx` | ~380 | AGUITestPanel |
| 31 | `pages/ag-ui/AGUIDemoPage.tsx` | ~200 | AGUIDemoPage |
| 32 | `pages/ag-ui/components/index.ts` | ~40 | barrel export |
| 33 | `pages/ag-ui/components/AgenticChatDemo.tsx` | ~107 | AgenticChatDemo |
| 34 | `pages/ag-ui/components/ToolRenderingDemo.tsx` | ~150 | ToolRenderingDemo |
| 35 | `pages/ag-ui/components/HITLDemo.tsx` | ~190 | HITLDemo |
| 36 | `pages/ag-ui/components/GenerativeUIDemo.tsx` | ~230 | GenerativeUIDemo |
| 37 | `pages/ag-ui/components/ToolUIDemo.tsx` | ~190 | ToolUIDemo |
| 38 | `pages/ag-ui/components/SharedStateDemo.tsx` | ~200 | SharedStateDemo |
| 39 | `pages/ag-ui/components/PredictiveDemo.tsx` | ~260 | PredictiveDemo |
| 40 | `pages/ag-ui/components/EventLogPanel.tsx` | ~210 | EventLogPanel |

---

## 2. UnifiedChat.tsx — Primary User Page (Deep Analysis)

**File**: `frontend/src/pages/UnifiedChat.tsx`
**Lines**: ~900
**Sprint History**: S62, S66, S69, S73, S74, S75, S99 (Phase 16, 18, 19, 28)

### 2.1 Component Purpose

The **primary user-facing chat interface** for the entire IPA Platform. Integrates:
- Agentic chat with Claude API via AG-UI protocol
- Chat history panel with thread management
- Workflow mode side panel
- Three-tier orchestration (Phase 28) with routing, dialog, and risk assessment
- HITL approval flow (inline via ApprovalMessageCard)
- File upload/download support
- Token/time metrics display
- Checkpoint system (stub)

### 2.2 Imports & Dependencies

| Category | Dependencies |
|----------|-------------|
| **Hooks** | `useUnifiedChat`, `useExecutionMetrics`, `useChatThreads`, `useFileUpload`, `useOrchestration` |
| **Store** | `useAuthStore` (Zustand, for user ID isolation) |
| **API** | `filesApi` (for file download) |
| **Components** | `ChatHeader`, `ChatArea`, `ChatInput`, `WorkflowSidePanel`, `StatusBar`, `OrchestrationPanel`, `ChatHistoryPanel`, `ChatHistoryToggleButton` |
| **Types** | `DialogQuestion`, `Attachment`, `UnifiedChatProps`, `ExecutionMode`, `ExecutionMetrics`, `RiskLevel`, `ToolDefinition` |

### 2.3 State Management

| State Variable | Type | Source | Purpose |
|---------------|------|--------|---------|
| `historyCollapsed` | boolean | useState | Chat history panel toggle |
| `orchestrationEnabled` | boolean | useState (hardcoded `true`) | Enable orchestration routing |
| `showOrchestrationPanel` | boolean | useState (hardcoded `true`) | Show orchestration debug panel |
| `dialogQuestions` | DialogQuestion[] | useState | Current dialog questions |
| `activeThreadId` | string | useState + localStorage | Current thread |
| User auth | User | useAuthStore | User ID for isolation |
| Chat state | messages, isStreaming, etc. | useUnifiedChat hook | Core chat logic |
| Metrics | time, tokens | useExecutionMetrics | Timer display |
| Files | attachments, isUploading | useFileUpload | File handling |
| Orchestration | phase, routing, risk | useOrchestration | Three-tier routing |

### 2.4 API Calls

| What | Endpoint | Method | Via |
|------|----------|--------|-----|
| Chat messages | AG-UI SSE stream | SSE | `useUnifiedChat` hook |
| Tool approvals | `/approvals/{id}/approve` | POST | `useUnifiedChat` hook |
| Tool rejections | `/approvals/{id}/reject` | POST | `useUnifiedChat` hook |
| File upload | `/files/upload` | POST | `useFileUpload` hook |
| File download | `/files/{id}/download` | GET | `filesApi.download()` |
| Orchestration routing | `/orchestration/route` | POST | `useOrchestration` hook |
| Dialog response | `/orchestration/dialog` | POST | `useOrchestration` hook |

### 2.5 User Interactions

1. **Send message** — text input with optional file attachments
2. **Switch execution mode** — Chat vs Workflow mode toggle
3. **Create new thread** — starts fresh conversation
4. **Select thread** — switches between saved conversations
5. **Delete thread** — removes conversation
6. **Rename thread** — manual title override
7. **Approve/reject tool calls** — HITL inline approval cards
8. **Cancel streaming** — stop active response
9. **File attach/remove** — file management before send
10. **File download** — download files from messages
11. **Orchestration dialog** — respond to clarifying questions
12. **Orchestration approve/reject** — approve high-risk operations
13. **Skip dialog** — bypass clarification, execute directly
14. **Toggle history panel** — collapse/expand left panel
15. **Restore checkpoint** — (stub, not implemented)

### 2.6 Data Display

| Data | Source | Real/Mock |
|------|--------|-----------|
| Chat messages | SSE stream + localStorage | **Real API** |
| Thread list | localStorage via `useChatThreads` | **Local storage** |
| Token usage | Backend TOKEN_UPDATE event or frontend estimation | **Hybrid** (real when available, estimated fallback) |
| Execution time | `useExecutionMetrics` timer | **Real** (client-side timer) |
| Pending approvals | SSE APPROVAL_REQUIRED events | **Real API** |
| Orchestration state | `useOrchestration` hook | **Real API** |
| Risk level | Derived from pending approvals | **Computed** |

### 2.7 DEFAULT_TOOLS Configuration

The component defines 8 default tools (lines 64-204):
- **Low-risk (auto-execute)**: Read, Glob, Grep, WebSearch, WebFetch
- **High-risk (require HITL)**: Write, Edit, Bash

### 2.8 Problems Found

| Severity | Issue | Location |
|----------|-------|----------|
| **Medium** | `console.log` statements in production code | Lines 372, 399, 401, 403, 407, 409, 434, 646, 651, 691, 704, 710, 731, 737, 757 |
| **Medium** | `console.error` statements | Lines 344, 375, 741, 749, 761 |
| **Low** | TODO: "Add UI toggles in ChatHeader to control these settings" | Line 239 |
| **Low** | TODO: "Implement checkpoint restoration via API" | Line 732 |
| **Low** | `orchestrationEnabled` and `showOrchestrationPanel` are hardcoded to `true` with no UI toggle | Lines 240-241 |
| **Low** | `void _setOrchestrationEnabled` workaround to suppress unused warnings | Lines 245-246 |
| **Info** | Token estimation uses ~3 chars/token heuristic as fallback | Line 476 |

---

## 3. SwarmTestPage.tsx

**File**: `frontend/src/pages/SwarmTestPage.tsx`
**Lines**: ~845
**Phase**: 29 (Agent Swarm Visualization)
**Route**: `/swarm-test`

### 3.1 Purpose

Standalone test page for Phase 29 Agent Swarm UI components. Supports **Mock mode** (UI testing with `useSwarmMock`) and **Real mode** (backend-connected via `useSwarmReal`).

### 3.2 State Management

- `testMode`: 'mock' | 'real' — switches between hook implementations
- Multiple local input states for worker controls
- `useSwarmMock` hook: full mock swarm lifecycle
- `useSwarmReal` hook: SSE connection to backend `/swarm/demo/start`

### 3.3 API Calls

| What | Endpoint | Method | Mode |
|------|----------|--------|------|
| Start demo | `/swarm/demo/start` | POST+SSE | Real mode |
| Stop demo | `/swarm/demo/stop` | POST | Real mode |
| Worker detail | `/swarm/{id}/workers/{workerId}` | GET | Real mode |

### 3.4 User Interactions

- **Mock mode**: Load preset scenarios (ETL, Security Audit, Data Pipeline), create swarm, add workers, set worker status/progress, add thinking/tool calls, complete/fail workers
- **Real mode**: Select scenario, set speed multiplier, start/stop demo
- **Both modes**: Click worker cards to open detail drawer, send chat messages

### 3.5 Data Display

- Swarm status panel with worker cards
- Mock chat messages area
- Debug info card (swarm ID, session, progress)
- Worker detail drawer (via `WorkerDetailDrawer` component)

### 3.6 Problems Found

| Severity | Issue |
|----------|-------|
| **None** | Clean implementation, well-structured with proper TypeScript types |

---

## 4. Dashboard Pages

### 4.1 DashboardPage.tsx (~87 lines)

**Purpose**: Main dashboard with system overview.
**API**: `GET /dashboard/stats` via React Query
**State**: React Query only
**Data**: `DashboardStats` type — delegates to sub-components
**Components used**: StatsCards, ExecutionChart, RecentExecutions, PendingApprovals
**Problems**: None — clean, simple page

### 4.2 PerformancePage.tsx (~469 lines)

**Purpose**: Phase 2 performance monitoring dashboard.
**API**: `GET /performance/metrics?range={timeRange}` via React Query
**State**: `timeRange` (1h/24h/7d), React Query
**Data**: **Falls back to mock data** if API fails (lines 148-153)
**User interactions**: Time range selector buttons
**Sub-components**: MetricCard, FeatureStatCard, RecommendationCard (all inline)

**Problems**:

| Severity | Issue |
|----------|-------|
| **High** | Full `mockPerformanceData` object hardcoded (lines 92-138) — always used as fallback |
| **Medium** | `try/catch` silently swallows API error and returns mock data (line 148) |
| **Low** | Chart data uses `Math.random()` for history mock — not deterministic |

### 4.3 Dashboard Sub-Components

#### StatsCards.tsx (~70 lines)
- **Purpose**: Display 4 stat cards (agents, workflows, executions, pending approvals)
- **Data**: Receives `stats` prop from parent
- **Problems**: None

#### ExecutionChart.tsx (~100 lines)
- **API**: `GET /dashboard/executions/chart`
- **Data**: Falls back to `generateMockData()` if API fails
- **Problems**: Mock data fallback with `Math.random()`

#### PendingApprovals.tsx (~110 lines)
- **API**: `GET /checkpoints/pending`
- **Data**: Falls back to `generateMockApprovals()`
- **Problems**: Mock data fallback

#### RecentExecutions.tsx (~130 lines)
- **API**: `GET /executions/?page_size=5`
- **Data**: Falls back to `generateMockExecutions()`
- **Problems**: Mock data fallback

---

## 5. Agent Management Pages

### 5.1 AgentsPage.tsx (~230 lines)

**Purpose**: Agent listing page with search and grid display.
**API**: `GET /agents/?search={query}` via React Query
**State**: `searchQuery` (string)
**Data**: Falls back to `generateMockAgents()` if API fails
**User interactions**: Search input, click agent cards (navigate to detail), "Create Agent" button

**Problems**:

| Severity | Issue |
|----------|-------|
| **Medium** | Mock data fallback with 4 hardcoded agents |

### 5.2 AgentDetailPage.tsx (~360 lines)

**Purpose**: Detailed agent view with integrated test chat interface.
**API**:
- `GET /agents/{id}` — fetch agent details
- `POST /agents/{id}/run` — test agent with message
**State**: `testInput`, `messages[]` (local chat state), `messagesEndRef`
**Data**: Falls back to `generateMockAgent(id)` if API fails
**User interactions**: Send test message, clear chat, navigate to edit page, back to list

**Problems**:

| Severity | Issue |
|----------|-------|
| **Medium** | Mock agent fallback |
| **Low** | Chat test interface uses local state — not connected to thread system |

### 5.3 CreateAgentPage.tsx (~750 lines)

**Purpose**: Multi-step wizard for creating new agents.
**API**:
- `POST /agents/` — create agent
**State**: `currentStep` (1-4), `formData` (AgentFormData), `errors`
**Data**: Hardcoded tool list (`AVAILABLE_TOOLS`), model providers, model lists
**User interactions**: 4-step wizard (Basic Info, Instructions, Tools & Model, Review), form validation, navigation between steps

**Problems**:

| Severity | Issue |
|----------|-------|
| **Low** | Tool list is hardcoded — should come from API |
| **Low** | Model/provider lists hardcoded — should be dynamic |

### 5.4 EditAgentPage.tsx (~700 lines)

**Purpose**: Edit existing agent with same form structure as Create.
**API**:
- `GET /agents/{id}` — load agent
- `PUT /agents/{id}` — update agent
- `DELETE /agents/{id}` — delete agent
**State**: `formData`, `errors`, `showDeleteConfirm`
**Data**: Real API data populated into form
**User interactions**: Edit all fields, delete with confirmation, save changes, navigate back

**Problems**:

| Severity | Issue |
|----------|-------|
| **Low** | Same hardcoded tool/model lists as CreateAgentPage (DRY violation) |

---

## 6. Workflow Management Pages

### 6.1 WorkflowsPage.tsx (~170 lines)

**Purpose**: Workflow listing with search.
**API**: `GET /workflows/?search={query}`
**Data**: Falls back to `generateMockWorkflows()`
**User interactions**: Search, click workflow cards, "Create Workflow" button

**Problems**:

| Severity | Issue |
|----------|-------|
| **Medium** | Mock data fallback |

### 6.2 WorkflowDetailPage.tsx (~400 lines)

**Purpose**: Detailed workflow view with execution history and execute button.
**API**:
- `GET /workflows/{id}`
- `GET /executions/?workflow_id={id}&page_size=10`
- `POST /workflows/{id}/execute`
**State**: `showExecuteDialog`, `executionResult`
**Data**: Real API — no mock fallback (fails gracefully)
**User interactions**: Execute workflow, view execution results, refresh executions, navigate to edit

**Problems**: None significant

### 6.3 CreateWorkflowPage.tsx (~700 lines)

**Purpose**: Multi-step workflow creation with visual node editor.
**API**:
- `GET /agents/?status=active&page_size=100` — fetch available agents for nodes
- `POST /workflows/` — create workflow
**State**: `currentStep` (1-4), `formData`, `selectedNodeId`, `errors`
**Data**: Fetches real agent list for node assignment
**User interactions**: 4-step wizard (Basic Info, Nodes, Connections, Review), add/remove/configure nodes, auto-connect nodes

**Problems**:

| Severity | Issue |
|----------|-------|
| **Low** | Trigger type options hardcoded |

### 6.4 EditWorkflowPage.tsx (~750 lines)

**Purpose**: Edit existing workflow (mirrors Create structure).
**API**:
- `GET /workflows/{id}` — load workflow
- `GET /agents/?status=active&page_size=100` — available agents
- `PUT /workflows/{id}` — update
- `DELETE /workflows/{id}` — delete
**Data**: Real API data
**User interactions**: Same as Create + delete with confirmation, status change

**Problems**:

| Severity | Issue |
|----------|-------|
| **Low** | Significant code duplication with CreateWorkflowPage (DRY violation) |

### 6.5 WorkflowEditorPage.tsx (~21 lines)

**Purpose**: Thin wrapper for ReactFlow `WorkflowCanvas` component (Sprint 133, Phase 34).
**Route**: `/workflows/:id/editor`
**API**: None directly — delegates to `WorkflowCanvas`
**Data**: Passes `workflowId` to canvas component

**Problems**: None — minimal and clean

---

## 7. Auth Pages

### 7.1 LoginPage.tsx (~230 lines)

**Purpose**: Login form with email/password.
**API**: Via `useAuthStore.login()` — calls auth API internally
**State**: `email`, `password`, `formErrors`
**Store**: `useAuthStore` (login, isLoading, error, clearError)
**User interactions**: Email/password input, form submission, link to signup
**Validation**: Email format, password min 8 chars
**Error handling**: Server errors displayed, field-level validation

**Problems**: None — well-implemented

### 7.2 SignupPage.tsx (~290 lines)

**Purpose**: Registration form.
**API**: Via `useAuthStore.register()`
**State**: `email`, `password`, `confirmPassword`, `fullName`, `formErrors`
**Validation**: Email format, password strength (uppercase + lowercase + digits), password confirmation match, name length
**User interactions**: Form fields, submit, link to login

**Problems**: None — well-implemented

---

## 8. Approvals & Audit Pages

### 8.1 ApprovalsPage.tsx (~260 lines)

**Purpose**: Approval workbench for pending checkpoints.
**API**:
- `GET /checkpoints/pending`
- `POST /checkpoints/{id}/approve`
- `POST /checkpoints/{id}/reject`
**State**: `selectedCheckpoint`, `feedback`
**Data**: Falls back to `generateMockCheckpoints()`
**User interactions**: Select checkpoint, provide feedback, approve/reject

**Problems**:

| Severity | Issue |
|----------|-------|
| **Medium** | Mock data fallback |

### 8.2 AuditPage.tsx (~180 lines)

**Purpose**: Audit log viewer with search.
**API**: `GET /audit/logs?search={query}`
**State**: `searchQuery`
**Data**: Falls back to `generateMockAuditLogs()`
**User interactions**: Search logs

**Problems**:

| Severity | Issue |
|----------|-------|
| **Medium** | Mock data fallback |

---

## 9. Templates Page

### 9.1 TemplatesPage.tsx (~230 lines)

**Purpose**: Template marketplace/browser with category filtering.
**API**: `GET /templates/?search={query}&category={cat}`
**State**: `searchQuery`, `selectedCategory`
**Data**: Falls back to `generateMockTemplates()`
**User interactions**: Search, category filter, "Use Template" button (no handler yet)

**Problems**:

| Severity | Issue |
|----------|-------|
| **Medium** | Mock data fallback with 5 hardcoded templates |
| **Medium** | "Use Template" button has no onClick handler — non-functional |

---

## 10. DevUI Pages

### 10.1 DevUIOverview (index.tsx, ~160 lines)

**Purpose**: DevUI landing page with summary statistics and quick links.
**API**: Uses `useTraces({ limit: 100 })` custom hook
**State**: React Query via useTraces
**Data**: Real API data — computes stats from trace list
**User interactions**: Quick links to Traces and Live Monitor

**Problems**: None

### 10.2 DevUILayout (Layout.tsx, ~140 lines)

**Purpose**: Sidebar navigation + breadcrumbs layout for all DevUI pages.
**Navigation items**: Overview, AG-UI Test, Traces, Live Monitor, Settings
**Uses**: React Router `NavLink`, `Outlet`, `useLocation`

**Problems**: None — clean layout component

### 10.3 TraceList (TraceList.tsx, ~340 lines)

**Purpose**: Paginated trace listing with status filter and search.
**API**: Uses `useTraces()` hook + `useDeleteTrace()` mutation
**State**: `statusFilter`, `searchQuery`, `page`
**Data**: Real API data from DevTools hooks
**User interactions**: Search, status filter, pagination, delete trace, click to view detail

**Problems**: None significant

### 10.4 TraceDetail (TraceDetail.tsx, ~530 lines)

**Purpose**: Detailed trace view with event timeline, filtering, and statistics.
**API**:
- `useTrace(executionId)` — trace details
- `useTraceEvents(executionId)` — event list
- `useDeleteTrace()` — delete mutation
**State**: `viewMode`, `selectedEvent`, `showFilters`, `filters`
**Data**: Real API data with rich event visualization
**User interactions**: View mode toggle (timeline/tree/stats), event type filtering, event selection, delete, refresh
**Components used**: EventTimeline, EventTreeView, EventFilter, EventPanel, StatisticsSummary

**Problems**:

| Severity | Issue |
|----------|-------|
| **Low** | `console.error` on delete failure (line 184) |

### 10.5 LiveMonitor (LiveMonitor.tsx, ~66 lines)

**Purpose**: **PLACEHOLDER** — "Coming Soon" notice.
**Status**: Not implemented. Shows Construction icon with planned features: WebSocket Events, Real-time Updates, Live Metrics.

### 10.6 Settings (Settings.tsx, ~66 lines)

**Purpose**: **PLACEHOLDER** — "Coming Soon" notice.
**Status**: Not implemented. Shows planned features: Trace Retention, Display Options, Filters.

### 10.7 AGUITestPanel (AGUITestPanel.tsx, ~380 lines)

**Purpose**: Interactive testing panel for all 7 AG-UI features within DevUI.
**API**: SSE connections to test endpoints:
- Feature 3 (HITL): `/api/v1/ag-ui/test/hitl/stream`
- Feature 4 (Generative UI): `/api/v1/ag-ui/test/workflow-progress/stream`
- Feature 5 (Tool UI): `/api/v1/ag-ui/test/ui-component/stream`
- Feature 6 (Shared State): `/api/v1/ag-ui/test/shared-state/stream`
- Feature 7 (Predictive): `/api/v1/ag-ui/test/predictive-state/stream`
**Features 1 & 2**: Manual test only (link to /chat)
**State**: `testStatuses` per feature, `runningTests`
**User interactions**: Run individual feature tests, view results, navigate to manual tests

**Problems**: None — well-structured test interface

---

## 11. AG-UI Demo Pages

### 11.1 AGUIDemoPage.tsx (~200 lines)

**Purpose**: Main demo page showcasing all 7 AG-UI features with tabbed navigation.
**Layout**: Left (feature demos) + Right (event log panel)
**State**: `activeTab`, `events[]`, `threadId`
**Data**: All local/simulated — no direct API calls from this page
**Tabs**: Chat, Tools, HITL, Generative UI, Tool UI, Shared State, Predictive

### 11.2 Demo Components Summary

| Component | Feature | Lines | Data Source | Real API? |
|-----------|---------|-------|-------------|-----------|
| `AgenticChatDemo` | F1: Agentic Chat | ~107 | `ChatContainer` component (real SSE) | **Yes** — connects to real chat API |
| `ToolRenderingDemo` | F2: Tool Rendering | ~150 | Hardcoded mock tool calls | **No** — static mock data |
| `HITLDemo` | F3: HITL | ~190 | Simulated approval flow | **No** — simulated with setTimeout |
| `GenerativeUIDemo` | F4: Generative UI | ~230 | Simulated progress steps | **No** — simulated with setInterval |
| `ToolUIDemo` | F5: Tool-based UI | ~190 | Hardcoded form/chart/card/table data | **No** — static mock data |
| `SharedStateDemo` | F6: Shared State | ~200 | Local state with simulated sync | **No** — simulated sync delay |
| `PredictiveDemo` | F7: Predictive State | ~260 | Local task list with optimistic updates | **No** — simulated with random failures |
| `EventLogPanel` | Shared | ~210 | Receives events from parent | N/A — display only |

### 11.3 Key Finding

Only **Feature 1 (Agentic Chat)** connects to real backend API. Features 2-7 demos are **purely client-side simulations** for UI demonstration purposes. This is acceptable for a demo page but should be noted.

---

## 12. Cross-Cutting Issues

### 12.1 Mock Data Proliferation (HIGH Priority)

**10 pages** fall back to mock/hardcoded data when API calls fail:

| Page | Mock Function | Impact |
|------|---------------|--------|
| PerformancePage | inline `mockPerformanceData` | Always used as fallback (try/catch) |
| ExecutionChart | `generateMockData()` | Silent fallback |
| PendingApprovals | `generateMockApprovals()` | Silent fallback |
| RecentExecutions | `generateMockExecutions()` | Silent fallback |
| AgentsPage | `generateMockAgents()` | Silent fallback |
| AgentDetailPage | `generateMockAgent()` | Silent fallback |
| WorkflowsPage | `generateMockWorkflows()` | Silent fallback |
| ApprovalsPage | `generateMockCheckpoints()` | Silent fallback |
| AuditPage | `generateMockAuditLogs()` | Silent fallback |
| TemplatesPage | `generateMockTemplates()` | Silent fallback |

**Risk**: Users may see mock data without knowing it. No visual indicator distinguishes real vs mock data.

**Recommendation**: Add a visible "Demo Data" badge when mock data is displayed, or remove fallbacks and show proper error states.

### 12.2 console.log/console.error in Production Code

**UnifiedChat.tsx** contains **~20 console statements** across the component. While many are prefixed with `[UnifiedChat]` for debugging, these should be removed or replaced with a proper logging utility.

**TraceDetail.tsx** has 1 `console.error` for delete failure.

### 12.3 Code Duplication

| Files | Duplication |
|-------|-------------|
| CreateAgentPage / EditAgentPage | ~80% identical form structure, validation, tool/model lists |
| CreateWorkflowPage / EditWorkflowPage | ~80% identical form structure, node editor, validation |

**Recommendation**: Extract shared form components (`AgentForm`, `WorkflowForm`) to reduce duplication.

### 12.4 Placeholder Pages

- **DevUI/LiveMonitor.tsx** — "Coming Soon" placeholder
- **DevUI/Settings.tsx** — "Coming Soon" placeholder

These are explicitly marked as Sprint 87 placeholders — acceptable for current phase.

### 12.5 Missing Features

| Feature | Location | Status |
|---------|----------|--------|
| Checkpoint restoration | UnifiedChat.tsx:732 | TODO — stub only |
| Orchestration UI toggles | UnifiedChat.tsx:239 | TODO — hardcoded to true |
| "Use Template" action | TemplatesPage.tsx | Button exists, no handler |

---

## 13. D-Series Cross-Reference

| Finding ID | Category | Description | Files Affected |
|-----------|----------|-------------|----------------|
| D1 | Mock Data | 10 pages silently fall back to hardcoded mock data | Dashboard sub-components, AgentsPage, WorkflowsPage, ApprovalsPage, AuditPage, TemplatesPage |
| D2 | console.log | ~20 console statements in primary chat page | UnifiedChat.tsx |
| D3 | TODO Items | 2 TODO comments for unimplemented features | UnifiedChat.tsx (lines 239, 732) |
| D4 | Code Duplication | Create/Edit pages share ~80% code | agents/, workflows/ |
| D5 | Placeholder Pages | 2 "Coming Soon" pages | DevUI/LiveMonitor.tsx, DevUI/Settings.tsx |
| D6 | AG-UI Demos | 6 of 7 AG-UI feature demos use simulated data | ag-ui/components/ (all except AgenticChatDemo) |
| D7 | Non-functional Button | "Use Template" button has no handler | TemplatesPage.tsx |
| D8 | Hardcoded Config | Tool lists, model providers hardcoded in form pages | CreateAgentPage.tsx, EditAgentPage.tsx |
| D9 | State Management | Chat threads stored in localStorage only, not synced to backend | UnifiedChat.tsx via useChatThreads |
| D10 | No Error Boundary | No React Error Boundary wrapping individual pages | All pages |
| D11 | Token Estimation | Frontend uses ~3 chars/token heuristic when backend doesn't send TOKEN_UPDATE | UnifiedChat.tsx:476 |

---

## Appendix: API Endpoint Map

Complete list of API endpoints called from pages:

| Endpoint | Method | Page(s) |
|----------|--------|---------|
| `/dashboard/stats` | GET | DashboardPage |
| `/dashboard/executions/chart` | GET | ExecutionChart |
| `/performance/metrics` | GET | PerformancePage |
| `/agents/` | GET | AgentsPage, CreateWorkflowPage, EditWorkflowPage |
| `/agents/{id}` | GET | AgentDetailPage, EditAgentPage |
| `/agents/` | POST | CreateAgentPage |
| `/agents/{id}` | PUT | EditAgentPage |
| `/agents/{id}` | DELETE | EditAgentPage |
| `/agents/{id}/run` | POST | AgentDetailPage |
| `/workflows/` | GET | WorkflowsPage |
| `/workflows/{id}` | GET | WorkflowDetailPage, EditWorkflowPage |
| `/workflows/` | POST | CreateWorkflowPage |
| `/workflows/{id}` | PUT | EditWorkflowPage |
| `/workflows/{id}` | DELETE | EditWorkflowPage |
| `/workflows/{id}/execute` | POST | WorkflowDetailPage |
| `/executions/` | GET | RecentExecutions, WorkflowDetailPage |
| `/checkpoints/pending` | GET | PendingApprovals, ApprovalsPage |
| `/checkpoints/{id}/approve` | POST | ApprovalsPage |
| `/checkpoints/{id}/reject` | POST | ApprovalsPage |
| `/audit/logs` | GET | AuditPage |
| `/templates/` | GET | TemplatesPage |
| `/files/upload` | POST | UnifiedChat (via useFileUpload) |
| `/files/{id}/download` | GET | UnifiedChat (via filesApi) |
| `/approvals/{id}/approve` | POST | UnifiedChat (via useUnifiedChat) |
| `/approvals/{id}/reject` | POST | UnifiedChat (via useUnifiedChat) |
| `/orchestration/route` | POST | UnifiedChat (via useOrchestration) |
| `/ag-ui/test/*/stream` | SSE | AGUITestPanel (5 test endpoints) |
| `/swarm/demo/start` | POST+SSE | SwarmTestPage |
| `/swarm/demo/stop` | POST | SwarmTestPage |
| DevTools traces/events | GET | DevUI pages (via useTraces hook) |

---

*Analysis complete. 41 files fully read and documented.*

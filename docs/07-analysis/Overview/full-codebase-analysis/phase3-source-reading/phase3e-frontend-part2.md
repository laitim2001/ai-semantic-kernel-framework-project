# Phase 3E Frontend Analysis Part 2: Unified-Chat & AG-UI Components

**Agent**: E2
**Scope**: `frontend/src/components/unified-chat/` (29 components + agent-swarm sub-module) and `frontend/src/components/ag-ui/` (19 files across 3 subdirectories)
**Total Files Analyzed**: 82 files (63 unified-chat + 19 ag-ui)
**Cross-references**: D5 (AG-UI), D6 (UnifiedChat), D9 (Swarm), H3 (Swarm Frontend)

---

## Table of Contents

1. [Summary Statistics](#1-summary-statistics)
2. [Unified-Chat Components](#2-unified-chat-components)
3. [Unified-Chat / Agent-Swarm Sub-module](#3-unified-chat--agent-swarm-sub-module)
4. [AG-UI Components](#4-ag-ui-components)
5. [Cross-Reference Analysis](#5-cross-reference-analysis)
6. [Issues and Findings](#6-issues-and-findings)

---

## 1. Summary Statistics

| Metric | unified-chat | agent-swarm | ag-ui | Total |
|--------|-------------|-------------|-------|-------|
| Component files | 29 | 15 | 12 | 56 |
| Hook files | 0 | 4 | 0 | 4 |
| Type files | 0 | 2 | 0 | 2 |
| Index/barrel files | 2 | 2 | 4 | 8 |
| Test files | 0 | 12 | 0 | 12 |
| **Total files** | **31** | **33** | **12** | **82** |
| **Total lines** | ~6,200 | ~4,700 | ~2,900 | ~13,800 |

### Console.log Issues

| File | Count | Nature |
|------|-------|--------|
| `agent-swarm/hooks/useSwarmEventHandler.ts` | 9 | Debug logging with `[SwarmEventHandler]` prefix, gated by `debug` option |
| `agent-swarm/hooks/useSwarmEvents.ts` | 3 | In JSDoc comments only (examples) |
| `ErrorBoundary.tsx` | 1 | `console.error` in error boundary (appropriate) |
| `renderers/CodePreview.tsx` | 1 | `console.error` for clipboard failure |
| `renderers/TextPreview.tsx` | 1 | `console.error` for clipboard failure |
| **ag-ui/** | **0** | Clean |

### TODO/FIXME Issues

- **WorkerActionList.tsx**: 11 matches - all false positives (`read_todo`/`write_todo` are action type names)
- **No genuine TODO/FIXME comments found** in any component

---

## 2. Unified-Chat Components

### 2.1 Core Chat Components

#### ChatArea.tsx
- **Path**: `frontend/src/components/unified-chat/ChatArea.tsx`
- **Lines**: 123
- **Purpose**: Main conversation area container with auto-scroll and empty state
- **Props**: `ChatAreaProps` (from `@/types/unified-chat`) - messages, isStreaming, streamingMessageId, pendingApprovals, onApprove, onReject, onExpired, onDownload
- **State/Hooks**: useRef x2 (scrollContainer, messagesEnd), useEffect (auto-scroll)
- **Children**: `MessageList`, `StreamingIndicator` (from ag-ui), `EmptyState` (internal)
- **User Interaction**: Passive display, auto-scrolls on new messages
- **Problems**: None. Clean component with proper data-testid.

#### ChatInput.tsx
- **Path**: `frontend/src/components/unified-chat/ChatInput.tsx`
- **Lines**: 245
- **Purpose**: Text input area with file attachments, keyboard shortcuts, send/cancel buttons
- **Props**: `ChatInputProps` (from `@/types/unified-chat`) - onSend, disabled, isStreaming, onCancel, placeholder, attachments, onAttach, onRemoveAttachment
- **State/Hooks**: useState (value), useRef x2 (textarea, fileInput), useEffect x2 (auto-focus, auto-resize), useMemo x2 (uploadedFileIds, shortcutKey), useCallback x3 (handleSend, handleAttachClick, handleFileChange)
- **Children**: `CompactAttachmentPreview`, `Button`, `Textarea`, `Paperclip`, `Send`, `Square`, `Loader2`
- **User Interaction**: Text input (Enter to send, Shift+Enter newline, Cmd/Ctrl+Enter force send), file attach button, send/cancel buttons
- **Accessibility**: aria-label on textarea, aria-describedby for keyboard hints, keyboard shortcut display
- **Problems**: None. Well-structured with platform detection for shortcut display.

#### MessageList.tsx
- **Path**: `frontend/src/components/unified-chat/MessageList.tsx`
- **Lines**: 238
- **Purpose**: Renders messages with tool calls, inline approvals, and custom UI in a sorted timeline
- **Props Interface** (defined locally):
  ```
  MessageListProps {
    messages: ChatMessage[]
    isStreaming?: boolean
    streamingMessageId?: string | null
    pendingApprovals: PendingApproval[]
    onApprove: (approvalId: string) => void
    onReject: (approvalId: string, reason?: string) => void
    onExpired?: (approvalId: string) => void
    onUIEvent?: (event: UIComponentEvent) => void
    onDownload?: (fileId: string) => Promise<void>
  }
  ```
- **State/Hooks**: useState (animatedIds Set), useRef (prevMessagesLength), useMemo x2 (reduceMotion, timeline), useEffect (animation tracking), useCallback (handleUIEvent)
- **Children**: `MessageBubble` (from ag-ui/chat), `CustomUIRenderer` (from ag-ui/advanced), `ApprovalMessageCard`
- **User Interaction**: Passive display with entrance animations (respects prefers-reduced-motion)
- **Accessibility**: role="log", aria-live="polite", aria-label per message, sr-only streaming announcement
- **Problems**: None. Timeline-based merging of messages and approvals is well-implemented.

#### ChatHeader.tsx
- **Path**: `frontend/src/components/unified-chat/ChatHeader.tsx`
- **Lines**: 131
- **Purpose**: Header with mode toggle (Chat/Workflow), connection status, and settings
- **Props**: `ChatHeaderProps` (from `@/types/unified-chat`) - title, currentMode, autoMode, isManuallyOverridden, connection, onModeChange, onSettingsClick, onReconnect, retryCount, maxRetries, connectionError
- **State/Hooks**: useCallback (handleModeClick)
- **Children**: `ConnectionStatus`, `Button`, `Badge`, `MessageSquare`, `Workflow`, `Settings`
- **User Interaction**: Mode toggle buttons, settings button, manual override indicator
- **Problems**: None.

### 2.2 HITL Approval Components

#### ApprovalMessageCard.tsx
- **Path**: `frontend/src/components/unified-chat/ApprovalMessageCard.tsx`
- **Lines**: 491
- **Purpose**: Inline approval card displayed as AI message in chat flow, with countdown timer, risk-based styling, and resolved status history
- **Props Interface**:
  ```
  ApprovalMessageCardProps {
    approval: PendingApproval
    onApprove: () => void
    onReject: (reason?: string) => void
    onExpired?: () => void
    isProcessing?: boolean
  }
  ```
- **State/Hooks**: useState x4 (localExpired, showRejectInput, rejectReason, localProcessing), useCallback x3 (handleApprove, handleReject, handleExpired), useEffect (in TimeoutCountdown sub-component)
- **Sub-components**: `TimeoutCountdown` (internal), `ResolvedStatus` (internal)
- **Children**: `Bot`, `Terminal`, `Badge`, `Button`, `Check`, `X`, `Loader2`, `Shield`, `AlertTriangle`, `AlertOctagon`, `Clock`, `CheckCircle2`, `XCircle`, `Timer`
- **User Interaction**: Approve button, Reject button (with optional reason input), countdown timer, expandable arguments
- **Risk Levels**: low (green), medium (yellow), high (orange), critical (red) with dedicated configs
- **Problems**: None. Comprehensive component with dark mode support.

#### InlineApproval.tsx
- **Path**: `frontend/src/components/unified-chat/InlineApproval.tsx`
- **Lines**: 233
- **Purpose**: Inline approval widget for low/medium risk tool calls
- **Props**: `InlineApprovalProps` (from `@/types/unified-chat`)
- **State/Hooks**: useState x3 (loading, expanded, rejectReason), useCallback x2
- **Children**: `Badge`, `Button`, `Check`, `RiskIcon`
- **User Interaction**: Approve/reject buttons with loading state
- **Problems**: None.

#### ApprovalDialog.tsx
- **Path**: `frontend/src/components/unified-chat/ApprovalDialog.tsx`
- **Lines**: 384
- **Purpose**: Modal dialog for high-risk tool call approvals with detailed risk display
- **Props Interface**:
  ```
  ApprovalDialogProps {
    approval: PendingApproval
    onApprove: () => void
    onReject: (reason?: string) => void
    onDismiss: () => void
    isProcessing?: boolean
  }
  ```
- **State/Hooks**: useState x4 (remaining via TimeoutCountdown, showArgs, rejectReason, isRejecting), useEffect (countdown), useCallback x2
- **Children**: `Dialog`/`DialogContent`/`DialogHeader`/`DialogTitle`/`DialogDescription`/`DialogFooter`, `RiskIndicator`, `TimeoutCountdown`, `Textarea`, `Button`, `Terminal`, `Badge`
- **User Interaction**: Approve/reject with reason, auto-close on expiry, argument toggle
- **Problems**: None.

### 2.3 Mode & Status Components

#### ModeIndicator.tsx
- **Path**: `frontend/src/components/unified-chat/ModeIndicator.tsx`
- **Lines**: 188
- **Purpose**: Displays current execution mode with confidence and auto-detection status
- **Props Interface**:
  ```
  ModeIndicatorProps {
    currentMode: ExecutionMode
    isManuallyOverridden: boolean
    switchReason: string | null
    confidence: number
    onReset: () => void
  }
  ```
- **State/Hooks**: None (pure presentational)
- **Children**: `TooltipProvider`, `Tooltip`, `TooltipTrigger`/`TooltipContent`, `Icon`, `Badge`, `RefreshCw`
- **User Interaction**: Tooltip on hover, reset button
- **Problems**: None.

#### RiskIndicator.tsx
- **Path**: `frontend/src/components/unified-chat/RiskIndicator.tsx`
- **Lines**: 292
- **Purpose**: Visual risk level indicator with score, factors, and tooltip
- **Props Interface**:
  ```
  RiskIndicatorProps {
    level: RiskLevel
    score: number
    factors?: string[]
    reasoning?: string
    size?: 'sm' | 'md' | 'lg'
    showScore?: boolean
    showTooltip?: boolean
  }
  ```
- **State/Hooks**: None (pure presentational)
- **Children**: `TooltipProvider`, `Tooltip`, `TooltipTrigger`/`TooltipContent`, `Icon`
- **Problems**: None.

#### ConnectionStatus.tsx
- **Path**: `frontend/src/components/unified-chat/ConnectionStatus.tsx`
- **Lines**: 239
- **Purpose**: Connection status indicator with reconnect support
- **Props Interface**:
  ```
  ConnectionStatusProps {
    status: ConnectionStatusType
    retryCount?: number
    maxRetries?: number
    onReconnect?: () => void
    errorMessage?: string
    compact?: boolean
  }
  ```
- **State/Hooks**: useMemo (statusConfig)
- **Children**: `TooltipProvider`, `Tooltip`, `Button`, `RefreshCw`
- **User Interaction**: Reconnect button, tooltip with error details
- **Problems**: None.

#### StatusBar.tsx
- **Path**: `frontend/src/components/unified-chat/StatusBar.tsx`
- **Lines**: 328
- **Purpose**: Bottom status bar showing risk level, token usage, tool calls, message count, uptime
- **Props**: `StatusBarProps` (from `@/types/unified-chat`)
- **State/Hooks**: useMemo (various computed values)
- **Children**: `TooltipProvider`, `Badge`, `Tooltip`, `Button`, `RotateCcw`, `Coins`, `AlertTriangle`, `Loader2`, `Wrench`, `MessageSquare`, `Clock`, `CheckCircle2`
- **User Interaction**: Tooltip details on each status item
- **Problems**: None.

### 2.4 Workflow Components

#### WorkflowSidePanel.tsx
- **Path**: `frontend/src/components/unified-chat/WorkflowSidePanel.tsx`
- **Lines**: 192
- **Purpose**: Collapsible side panel for workflow mode showing steps, tool calls, and checkpoints
- **Props**: `WorkflowSidePanelProps` (from `@/types/unified-chat`)
- **State/Hooks**: useState (collapsed), useMemo, useCallback
- **Children**: `StepProgress`, `ToolCallTracker`, `CheckpointList`, `Button`, `ChevronLeft`/`ChevronRight`
- **User Interaction**: Collapse/expand toggle
- **Problems**: None.

#### StepProgress.tsx
- **Path**: `frontend/src/components/unified-chat/StepProgress.tsx`
- **Lines**: 191
- **Purpose**: Displays workflow steps with status indicators
- **Props**: `StepProgressProps` (from `@/types/unified-chat`), internal `StepItemProps { step: WorkflowStep, index: number, isCurrent: boolean }`
- **State/Hooks**: useMemo
- **Children**: `StepItem` (internal), `Icon`
- **Problems**: None.

#### StepProgressEnhanced.tsx
- **Path**: `frontend/src/components/unified-chat/StepProgressEnhanced.tsx`
- **Lines**: 287
- **Purpose**: Enhanced step progress with sub-steps, progress bars, and collapsible detail
- **Exported Types**: `SubStepStatusType`, `SubStep`, `StepProgressEvent`, `StepProgressEnhancedProps`
- **Exported Components**: `StatusIcon`, `SubStepItem`, `StepProgressEnhanced`
- **Props Interface**:
  ```
  StepProgressEnhancedProps {
    step: StepProgressEvent
    isExpanded?: boolean
    onToggle?: () => void
    showSubsteps?: boolean
  }
  ```
- **State/Hooks**: useState x2, useMemo, useCallback
- **Children**: `StatusIcon` (internal), `SubStepItem` (internal), `Check`, `Loader2`, `AlertCircle`, `Slash`, `Circle`, `ChevronDown`/`ChevronRight`
- **Problems**: None.

#### ToolCallTracker.tsx
- **Path**: `frontend/src/components/unified-chat/ToolCallTracker.tsx`
- **Lines**: 198
- **Purpose**: Tracks and displays tool call executions with timing
- **Props**: `ToolCallTrackerProps` (from `@/types/unified-chat`), internal `ToolCallItemProps { toolCall: TrackedToolCall, showTiming: boolean }`
- **State/Hooks**: useMemo
- **Children**: `ToolCallItem` (internal), `Icon`
- **Problems**: None.

#### CheckpointList.tsx
- **Path**: `frontend/src/components/unified-chat/CheckpointList.tsx`
- **Lines**: 205
- **Purpose**: Displays checkpoint history with restore capability
- **Props**: `CheckpointListProps` (from `@/types/unified-chat`), internal `CheckpointItemProps { checkpoint, isCurrent, isRestoring, onRestore }`
- **State/Hooks**: useState x2 (expandedId, isRestoring), useMemo, useCallback
- **Children**: `CheckpointItem` (internal), `Button`, `BookmarkCheck`, `Clock`, `RotateCcw`, `ChevronUp`/`ChevronDown`
- **User Interaction**: Expand/collapse checkpoints, restore button
- **Problems**: None.

### 2.5 Dialog Components

#### ModeSwitchConfirmDialog.tsx
- **Path**: `frontend/src/components/unified-chat/ModeSwitchConfirmDialog.tsx`
- **Lines**: 241
- **Purpose**: Confirmation dialog when switching between Chat and Workflow modes
- **Props Interface**:
  ```
  ModeSwitchConfirmDialogProps {
    open: boolean
    from: ExecutionMode
    to: ExecutionMode
    reason: string
    confidence: number
    onConfirm: () => void
    onCancel: () => void
  }
  ```
- **State/Hooks**: None (pure presentational)
- **Children**: `Dialog`, `DialogContent`, `DialogHeader`, `DialogTitle`, `DialogDescription`, `DialogFooter`, `Button`, `AlertCircle`, `ArrowRight`, `Badge`, `Progress`, `Check`
- **User Interaction**: Confirm/cancel buttons, confidence progress bar display
- **Problems**: None.

#### RestoreConfirmDialog.tsx
- **Path**: `frontend/src/components/unified-chat/RestoreConfirmDialog.tsx`
- **Lines**: 201
- **Purpose**: Confirmation dialog for restoring a checkpoint
- **Props Interface**:
  ```
  RestoreConfirmDialogProps {
    isOpen: boolean
    checkpoint: Checkpoint | null
    isRestoring?: boolean
    onConfirm: () => void
    onCancel: () => void
  }
  ```
- **State/Hooks**: None
- **Children**: `Dialog`, `DialogContent`, `DialogHeader`, `DialogTitle`, `DialogDescription`, `DialogFooter`, `Button`, `RotateCcw`, `BookmarkCheck`, `Clock`, `AlertTriangle`
- **User Interaction**: Confirm/cancel buttons
- **Problems**: None.

### 2.6 Error Handling

#### ErrorBoundary.tsx
- **Path**: `frontend/src/components/unified-chat/ErrorBoundary.tsx`
- **Lines**: 221
- **Purpose**: React error boundary with recovery options and stack trace display
- **Component Type**: Class component (required for error boundaries)
- **Exports**: `ErrorBoundary` (class), `ErrorBoundaryWrapper` (FC wrapper)
- **Props Interface**:
  ```
  ErrorBoundaryProps {
    children: ReactNode
    fallback?: ReactNode
    onError?: (error: Error, errorInfo: ErrorInfo) => void
    showDetails?: boolean
    onReset?: () => void
  }
  ```
- **State**: `{ hasError, error, errorInfo, showStackTrace }`
- **Children**: `AlertTriangle`, `Button`, `RefreshCw`, `Bug`, `ChevronUp`/`ChevronDown`
- **User Interaction**: Reset/retry button, toggle stack trace details
- **Console**: `console.error` in componentDidCatch (appropriate for error logging)
- **Problems**: None. Correctly uses class component for error boundary lifecycle.

### 2.7 File Handling Components

#### FileUpload.tsx
- **Path**: `frontend/src/components/unified-chat/FileUpload.tsx`
- **Lines**: 323
- **Purpose**: Drag-and-drop file upload zone with validation
- **Exports**: `FileUpload`, `AttachButton`, `HiddenFileInput`
- **Props Interfaces**:
  ```
  FileUploadProps { onFilesSelected, accept?, maxSize?, multiple?, disabled?, className? }
  AttachButtonProps { onClick, disabled?, hasAttachments?, attachmentCount?, className? }
  HiddenFileInputProps { inputRef, onFilesSelected, accept?, multiple? }
  ```
- **State/Hooks**: useState x3 (isDragging, error, files), useCallback
- **Children**: `Upload`, `AlertCircle`, `Button`
- **User Interaction**: Drag-and-drop zone, file input, attach button
- **Problems**: None.

#### AttachmentPreview.tsx
- **Path**: `frontend/src/components/unified-chat/AttachmentPreview.tsx`
- **Lines**: 337
- **Purpose**: Preview attached files before sending with upload status
- **Exports**: `AttachmentPreview`, `CompactAttachmentPreview`
- **Props Interfaces**:
  ```
  AttachmentPreviewProps { attachments: Attachment[], onRemove, disabled?, className? }
  AttachmentItemProps { attachment: Attachment, onRemove, disabled? }
  CompactAttachmentPreviewProps { attachments: Attachment[], onRemove, disabled?, className? }
  ```
- **State/Hooks**: useMemo
- **Children**: `ImageIcon`, `FileCode`, `FileText`, `File`, `Loader2`, `CheckCircle`, `AlertCircle`, `Button`
- **User Interaction**: Remove attachment button
- **Problems**: None.

#### FileMessage.tsx
- **Path**: `frontend/src/components/unified-chat/FileMessage.tsx`
- **Lines**: 313
- **Purpose**: Displays generated/downloaded files in chat messages
- **Exports**: `FileMessage`, `FileMessageList`, `CompactFileMessage`
- **Props Interfaces**:
  ```
  FileMessageProps { file: GeneratedFile, onDownload, className? }
  FileMessageListProps { files: GeneratedFile[], onDownload, className? }
  CompactFileMessageProps { file: GeneratedFile, onDownload, className? }
  ```
- **Exported Type**: `DownloadStatus`
- **State/Hooks**: useState x4 (downloadStatus, progress, error, preview), useCallback
- **Children**: `Button`, `Loader2`, `CheckCircle`, `AlertCircle`, `Download`, `ExternalLink`
- **User Interaction**: Download button with progress indicator
- **Problems**: None.

#### FileRenderer.tsx
- **Path**: `frontend/src/components/unified-chat/FileRenderer.tsx`
- **Lines**: 257
- **Purpose**: Type-based file preview renderer (dispatches to ImagePreview, CodePreview, TextPreview)
- **Exports**: `getFileType` (function), `FileRenderer` (component)
- **Exported Type**: `FileType`
- **Props Interface**:
  ```
  FileRendererProps { file: GeneratedFile, content?, preview?, onDownload, isLoading?, className? }
  ```
- **State/Hooks**: useMemo (fileType detection)
- **Children**: `ImagePreview`, `CodePreview`, `TextPreview`, `GenericFileCard` (internal), `Loader2`, `Button`, `Download`
- **Problems**: None.

### 2.8 Renderers Sub-directory

#### renderers/ImagePreview.tsx
- **Path**: `frontend/src/components/unified-chat/renderers/ImagePreview.tsx`
- **Lines**: 228
- **Purpose**: Image file preview with zoom, lightbox, and download
- **Props**: `ImagePreviewProps { src, alt, filename?, onDownload?, className? }`
- **State/Hooks**: useState x5 (isLoaded, hasError, isExpanded, isZoomed, naturalSize), useCallback
- **Children**: `Button`, `Download`, `ZoomIn`, `ZoomOut`, `ExternalLink`
- **User Interaction**: Click to expand, zoom in/out, download
- **Problems**: None.

#### renderers/CodePreview.tsx
- **Path**: `frontend/src/components/unified-chat/renderers/CodePreview.tsx`
- **Lines**: 222
- **Purpose**: Code file preview with syntax highlighting info, copy, and line limiting
- **Props**: `CodePreviewProps { code, language?, filename?, maxLines?, onDownload?, className? }`
- **State/Hooks**: useState x3 (isCopied, isExpanded, copyError), useMemo, useCallback
- **Children**: `FileCode`, `Button`, `Check`, `Copy`, `Download`, `ChevronUp`/`ChevronDown`
- **User Interaction**: Copy to clipboard, expand/collapse, download
- **Console**: `console.error` on clipboard API failure (appropriate)
- **Problems**: None.

#### renderers/TextPreview.tsx
- **Path**: `frontend/src/components/unified-chat/renderers/TextPreview.tsx`
- **Lines**: 245
- **Purpose**: Plain text file preview with search, copy, line limiting
- **Props**: `TextPreviewProps { content, filename?, maxLines?, searchable?, onDownload?, className? }`
- **State/Hooks**: useState x5 (isCopied, isExpanded, copyError, searchQuery, matchCount), useMemo, useCallback
- **Children**: `FileText`, `Button`, `Search`, `Check`, `Copy`, `Download`, `ChevronUp`/`ChevronDown`
- **User Interaction**: Search within text, copy to clipboard, expand/collapse, download
- **Console**: `console.error` on clipboard API failure (appropriate)
- **Problems**: None.

#### renderers/index.ts
- **Path**: `frontend/src/components/unified-chat/renderers/index.ts`
- **Lines**: 18
- **Purpose**: Barrel export for ImagePreview, CodePreview, TextPreview

### 2.9 Other Components

#### ChatHistoryPanel.tsx
- **Path**: `frontend/src/components/unified-chat/ChatHistoryPanel.tsx`
- **Lines**: 304
- **Purpose**: Side panel showing chat thread history with create/delete/rename
- **Exports**: `ChatHistoryPanel`, `ChatHistoryToggleButton`
- **Exported Type**: `ChatThread`
- **Props Interfaces**:
  ```
  ChatThread { id, title, lastMessage?, updatedAt, messageCount }
  ChatHistoryPanelProps { threads, activeThreadId, onSelectThread, onNewThread, onDeleteThread, onRenameThread?, isLoading? }
  ThreadItemProps { thread, isActive, onSelect, onDelete, onRename? }
  ```
- **State/Hooks**: useState x4 (editingId, editTitle, confirmDeleteId, searchQuery), useEffect
- **Children**: `MessageSquare`, `Check`, `Pencil`, `Trash2`, `Button`, `Plus`, `ChevronLeft`/`ChevronRight`, `ThreadItem` (internal)
- **User Interaction**: Select thread, new thread, rename (inline edit), delete with confirmation, search
- **Problems**: None.

#### OrchestrationPanel.tsx
- **Path**: `frontend/src/components/unified-chat/OrchestrationPanel.tsx`
- **Lines**: 509
- **Purpose**: Three-tier intent routing display panel showing routing decisions, risk assessments, dialog questions, and embedded swarm visualization
- **Props Interface**:
  ```
  OrchestrationPanelProps {
    phase: OrchestrationPhase
    routingDecision: RoutingDecision | null
    riskAssessment: RiskAssessment | null
    dialogQuestions: DialogQuestion[] | null
    isLoading: boolean
    onDialogAnswer?: (questionId: string, answer: string) => void
    swarmStatus?: UIAgentSwarmStatus | null
  }
  ```
- **State/Hooks**: useState x7 (collapsed sections, selected worker, drawer open, etc.), useSwarmStatus hook
- **Children**: `PhaseIndicator` (internal), `SectionHeader` (internal), `LayerBadge` (internal), `RiskBadge` (internal), `AgentSwarmPanel`, `WorkerDetailDrawer`, `Badge`, `Button`, `Input`, various Lucide icons
- **User Interaction**: Collapse/expand sections, answer dialog questions, select workers, open worker detail drawer
- **Problems**: None. Most complex component in unified-chat at 509 lines. Well-structured with internal sub-components.

### 2.10 Barrel Export (index.ts)
- **Path**: `frontend/src/components/unified-chat/index.ts`
- **Lines**: 107
- **Purpose**: Central barrel export for all unified-chat components and types
- **Exports**: All 27+ components, associated Props types, and type re-exports from `@/types/unified-chat`

---

## 3. Unified-Chat / Agent-Swarm Sub-module

### 3.1 Type Definitions

#### types/index.ts
- **Path**: `frontend/src/components/unified-chat/agent-swarm/types/index.ts`
- **Lines**: 180
- **Purpose**: All swarm UI types including WorkerType, WorkerStatus, SwarmMode, SwarmStatus, ToolCallInfo, ThinkingContent, WorkerMessage, UIWorkerSummary, WorkerDetail, UIAgentSwarmStatus
- **Key Types**:
  - `WorkerType`: 'claude_sdk' | 'maf' | 'hybrid' | 'research' | 'custom'
  - `WorkerStatus`: 'pending' | 'running' | 'paused' | 'completed' | 'failed'
  - `SwarmMode`: 'sequential' | 'parallel' | 'pipeline' | 'hierarchical' | 'hybrid'
  - `SwarmStatus`: 'initializing' | 'executing' | 'aggregating' | 'completed' | 'failed'

#### types/events.ts
- **Path**: `frontend/src/components/unified-chat/agent-swarm/types/events.ts`
- **Lines**: 211
- **Purpose**: SSE event type definitions for swarm real-time updates
- **Event Names**: `SwarmEventNames` const object with 9 event types
- **Payload Interfaces**: SwarmCreatedPayload, SwarmStatusUpdatePayload, SwarmCompletedPayload, WorkerStartedPayload, WorkerProgressPayload, WorkerThinkingPayload, WorkerToolCallPayload, WorkerMessagePayload, WorkerCompletedPayload
- **Convention**: snake_case for SSE payloads (matches backend)

### 3.2 Hooks

#### hooks/useSwarmEvents.ts
- **Path**: `frontend/src/components/unified-chat/agent-swarm/hooks/useSwarmEvents.ts`
- **Lines**: 210
- **Purpose**: Hook for subscribing to swarm SSE events with typed callbacks
- **Exports**: `useSwarmEvents`, `isSwarmEvent`, `getSwarmEventCategory`
- **State**: useState (single state)
- **Hooks Used**: useCallback, useEffect
- **Console**: 2x console.log (in event processing), 2x console.error (error handling)
- **Problems**: console.log calls should be removed or gated behind debug flag

#### hooks/useWorkerDetail.ts
- **Path**: `frontend/src/components/unified-chat/agent-swarm/hooks/useWorkerDetail.ts`
- **Lines**: 199
- **Purpose**: Fetches and polls worker detail data via native fetch API
- **Options Interface**: `UseWorkerDetailOptions { swarmId, workerId, enabled?, pollInterval? }`
- **Return Interface**: `UseWorkerDetailResult { worker, isLoading, error, refetch }`
- **State**: useState x4 (worker, isLoading, error, isMounted)
- **Hooks Used**: useRef, useCallback, useEffect
- **API Call**: `fetch()` to `/api/v1/swarm/{swarmId}/workers/{workerId}`
- **Problems**: None. Clean fetch with polling and cleanup.

#### hooks/useSwarmStatus.ts
- **Path**: `frontend/src/components/unified-chat/agent-swarm/hooks/useSwarmStatus.ts`
- **Lines**: 222
- **Purpose**: Derives swarm status, computed properties, and actions from Zustand store
- **Return Interface**: `UseSwarmStatusReturn { swarmStatus, selectedWorkerId, selectedWorkerDetail, isDrawerOpen, isLoading, error, isSwarmActive, isSwarmCompleted, completedWorkers, runningWorkers, ... }`
- **Hooks Used**: useSwarmStore (Zustand), useMemo, useCallback
- **Problems**: None. Clean selector pattern from Zustand.

#### hooks/useSwarmEventHandler.ts
- **Path**: `frontend/src/components/unified-chat/agent-swarm/hooks/useSwarmEventHandler.ts`
- **Lines**: 304
- **Purpose**: Processes incoming swarm SSE events and dispatches to Zustand store
- **Options Interface**: `UseSwarmEventHandlerOptions { onSwarmCreated?, onSwarmCompleted?, onError?, debug? }`
- **Hooks Used**: useEventSource, useSwarmStatus, useSwarmStore, useCallback, useSwarmEvents
- **Console**: 9x console.log (gated by `debug` option), 1x console.error
- **Problems**: console.log calls present but properly gated behind `debug` option. Acceptable for development.

### 3.3 Components (Sprint 102 - Panel & Cards)

#### AgentSwarmPanel.tsx
- **Path**: `frontend/src/components/unified-chat/agent-swarm/AgentSwarmPanel.tsx`
- **Lines**: 147
- **Purpose**: Main container for swarm visualization with loading/empty states
- **Props**: `AgentSwarmPanelProps` (implied, not locally defined - likely from types/)
- **Children**: `SwarmHeader`, `OverallProgress`, `WorkerCardList`, `Card`, `CardHeader`, `CardContent`, `Skeleton` (loading), `LoadingState`/`EmptyState` (internal)
- **Problems**: None.

#### SwarmHeader.tsx
- **Path**: `frontend/src/components/unified-chat/agent-swarm/SwarmHeader.tsx`
- **Lines**: 146
- **Purpose**: Swarm status header with mode badge and status icon
- **Props**: `SwarmHeaderProps` (implied)
- **Children**: `Bug`, `Badge`, `StatusIcon`, `Clock`
- **Problems**: None.

#### OverallProgress.tsx
- **Path**: `frontend/src/components/unified-chat/agent-swarm/OverallProgress.tsx`
- **Lines**: 69
- **Purpose**: Overall swarm progress bar with percentage
- **Props**: `OverallProgressProps` (implied)
- **Problems**: None. Simple presentational component.

#### WorkerCard.tsx
- **Path**: `frontend/src/components/unified-chat/agent-swarm/WorkerCard.tsx`
- **Lines**: 229
- **Purpose**: Individual worker agent card showing status, type, role, progress, and current action
- **Props**: `WorkerCardProps` (implied)
- **Internal types**: `StatusConfigItem { icon, color, bgColor }`, `TypeConfigItem { icon, label }`
- **Children**: `Card`, `CardContent`, `Badge`, `Button`, `ChevronRight`, icons
- **User Interaction**: Click to open worker detail drawer
- **Problems**: None.

#### WorkerCardList.tsx
- **Path**: `frontend/src/components/unified-chat/agent-swarm/WorkerCardList.tsx`
- **Lines**: 60
- **Purpose**: Renders a list of WorkerCards
- **Props**: `WorkerCardListProps` (implied)
- **Children**: `WorkerCard`
- **Problems**: None.

#### SwarmStatusBadges.tsx
- **Path**: `frontend/src/components/unified-chat/agent-swarm/SwarmStatusBadges.tsx`
- **Lines**: 111
- **Purpose**: Status badge indicators for worker counts by status
- **Props**: `SwarmStatusBadgesProps` (implied)
- **Children**: `TooltipProvider`, `Tooltip`, `Badge`, `User`, icons
- **Problems**: None.

### 3.4 Components (Sprint 103 - Worker Detail Drawer)

#### WorkerDetailDrawer.tsx
- **Path**: `frontend/src/components/unified-chat/agent-swarm/WorkerDetailDrawer.tsx`
- **Lines**: 285
- **Purpose**: Side drawer showing detailed worker information with tabs for task, thinking, tools, messages, checkpoints
- **Props Interface**:
  ```
  WorkerDetailDrawerProps {
    open: boolean
    onClose: () => void
    swarmId: string
    worker: UIWorkerSummary | null
    workerDetail?: WorkerDetail | null
    className?: string
  }
  ```
- **Internal**: `ErrorDisplayProps { error: Error, onRetry? }`
- **Hooks Used**: useWorkerDetail
- **Children**: `Sheet`/`SheetContent`/`SheetHeader`/`SheetTitle`, `WorkerDetailHeader`, `CurrentTask`, `ExtendedThinkingPanel`, `ToolCallsPanel`, `MessageHistory`, `CheckpointPanel`, `Separator`, `Skeleton` (loading), `ErrorDisplay`/`LoadingSkeleton` (internal)
- **User Interaction**: Close drawer, retry on error
- **Problems**: None. Well-structured with loading/error states.

#### WorkerDetailHeader.tsx
- **Path**: `frontend/src/components/unified-chat/agent-swarm/WorkerDetailHeader.tsx`
- **Lines**: 180
- **Purpose**: Header section of worker detail drawer with back button, name, status, type
- **Props**: `WorkerDetailHeaderProps { worker: WorkerDetail, onBack? }`
- **Children**: `Button`, `ArrowLeft`, `Badge`, icons
- **User Interaction**: Back button
- **Problems**: None.

#### CurrentTask.tsx
- **Path**: `frontend/src/components/unified-chat/agent-swarm/CurrentTask.tsx`
- **Lines**: 106
- **Purpose**: Displays current task description with expand/collapse for long text
- **Props**: `CurrentTaskProps { taskDescription, maxLength?, className? }`
- **State**: useState x2 (isExpanded, truncated)
- **Children**: `ClipboardList`, `Button`, `ChevronUp`/`ChevronDown`
- **User Interaction**: Expand/collapse long descriptions
- **Problems**: None.

#### ToolCallsPanel.tsx
- **Path**: `frontend/src/components/unified-chat/agent-swarm/ToolCallsPanel.tsx`
- **Lines**: 94
- **Purpose**: Panel listing tool calls for a worker
- **Props**: `ToolCallsPanelProps { toolCalls: ToolCallInfo[], className? }`
- **Children**: `Wrench`, `ToolCallItem`
- **Problems**: None.

#### ToolCallItem.tsx
- **Path**: `frontend/src/components/unified-chat/agent-swarm/ToolCallItem.tsx`
- **Lines**: 298
- **Purpose**: Individual tool call display with status, timing, collapsible input/output
- **Props**: `ToolCallItemProps { toolCall: ToolCallInfo, defaultExpanded?, showLiveTimer? }`
- **State**: useState x4 (isOpen, elapsed, various)
- **Custom Hook**: `useLiveTimer` (internal)
- **Children**: `Card`, `Collapsible`/`CollapsibleTrigger`/`CollapsibleContent`, `Button`, `Badge`, `Timer`, `CardContent`, icons
- **User Interaction**: Expand/collapse to see arguments and results, live elapsed timer
- **Problems**: None.

#### MessageHistory.tsx
- **Path**: `frontend/src/components/unified-chat/agent-swarm/MessageHistory.tsx`
- **Lines**: 238
- **Purpose**: Displays message history for a worker with role-based styling
- **Props**: `MessageHistoryProps { messages: WorkerMessage[], defaultExpanded?, maxPreviewLength?, className? }`
- **Internal**: `RoleConfig { icon, color, bgColor, label }`, `MessageItemProps`
- **State**: useState x3 (expanded, messageExpanded, various)
- **Children**: `Collapsible`, `MessageSquare`, `Badge`, `Button`, `MessageItem` (internal), icons
- **User Interaction**: Expand/collapse section, expand individual messages
- **Problems**: None.

#### CheckpointPanel.tsx
- **Path**: `frontend/src/components/unified-chat/agent-swarm/CheckpointPanel.tsx`
- **Lines**: 103
- **Purpose**: Displays checkpoint info with restore capability
- **Props**: `CheckpointPanelProps { checkpointId, backend?, onRestore?, className? }`
- **Children**: `Save`, `Database`, `Badge`, `CheckCircle`, `Button`, `RotateCcw`
- **User Interaction**: Restore button
- **Problems**: None.

### 3.5 Components (Sprint 104 - Extended Thinking & Action List)

#### ExtendedThinkingPanel.tsx
- **Path**: `frontend/src/components/unified-chat/agent-swarm/ExtendedThinkingPanel.tsx`
- **Lines**: 232
- **Purpose**: Displays AI extended thinking/reasoning content with auto-scroll and collapsible blocks
- **Props**: `ExtendedThinkingPanelProps { thinkingHistory: ThinkingContent[], maxHeight?, defaultExpanded?, autoScroll?, className? }`
- **Internal**: `ThinkingBlockProps { thinking, index, isLatest }`
- **State**: useState x2 (isExpanded, autoScroll)
- **Hooks**: useMemo (totalTokens), useEffect (auto-scroll)
- **Children**: `Card`, `CardHeader`/`CardTitle`/`CardContent`, `Collapsible`/`CollapsibleTrigger`/`CollapsibleContent`, `ScrollArea`, `ThinkingBlock` (internal), `Brain`, `Badge`, `Hash`, `Clock`, `Button`, icons
- **User Interaction**: Expand/collapse panel, auto-scroll toggle
- **Problems**: None.

#### WorkerActionList.tsx
- **Path**: `frontend/src/components/unified-chat/agent-swarm/WorkerActionList.tsx`
- **Lines**: 334
- **Purpose**: Displays chronological list of worker actions with type inference and icons
- **Exports**: `WorkerActionList` (component), `inferActionType` (function)
- **Exported Types**: `ActionType` (union of 14 action types), `WorkerAction` (interface)
- **Props Interfaces**:
  ```
  WorkerAction { id, type: ActionType, title, description?, timestamp, metadata?, expandable? }
  WorkerActionListProps { actions: WorkerAction[], onActionClick?, maxHeight?, className? }
  ActionItemProps { action, onClick? }
  ```
- **Action Types**: 'tool_call' | 'thinking' | 'message' | 'checkpoint' | 'file_read' | 'file_write' | 'search' | 'code_execute' | 'api_call' | 'analysis' | 'read_todo' | 'write_todo' | 'delegate' | 'unknown'
- **Children**: `ActionItem` (internal), `ChevronRight`, icons
- **User Interaction**: Click on action items (if expandable)
- **Problems**: None (the "todo" matches in search were action type names, not TODO comments)

### 3.6 Tests

| Test File | Lines | Component Tested |
|-----------|-------|-----------------|
| `SwarmHeader.test.tsx` | 83 | SwarmHeader |
| `OverallProgress.test.tsx` | 79 | OverallProgress |
| `WorkerCard.test.tsx` | 157 | WorkerCard |
| `WorkerCardList.test.tsx` | ~80 | WorkerCardList |
| `SwarmStatusBadges.test.tsx` | ~80 | SwarmStatusBadges |
| `AgentSwarmPanel.test.tsx` | ~100 | AgentSwarmPanel |
| `useWorkerDetail.test.ts` | ~120 | useWorkerDetail hook |
| `ToolCallItem.test.tsx` | ~150 | ToolCallItem |
| `MessageHistory.test.tsx` | ~120 | MessageHistory |
| `WorkerDetailDrawer.test.tsx` | ~150 | WorkerDetailDrawer |
| `ExtendedThinkingPanel.test.tsx` | ~120 | ExtendedThinkingPanel |
| `WorkerActionList.test.tsx` | ~310 | WorkerActionList + inferActionType |

### 3.7 Barrel Exports

#### agent-swarm/index.ts (48 lines)
- Exports all types from `./types`
- Exports all hooks from `./hooks`
- Exports 15 components across Sprint 102, 103, 104

#### agent-swarm/hooks/index.ts (27 lines)
- Exports `useSwarmEvents`, `isSwarmEvent`, `getSwarmEventCategory`
- Exports `useWorkerDetail` with types
- Exports `useSwarmStatus` with types
- Exports `useSwarmEventHandler` with types

---

## 4. AG-UI Components

### 4.1 Chat Sub-directory (`ag-ui/chat/`)

#### ChatContainer.tsx
- **Path**: `frontend/src/components/ag-ui/chat/ChatContainer.tsx`
- **Lines**: 237
- **Purpose**: Self-contained AG-UI chat container with full protocol integration
- **Props Interface**:
  ```
  ChatContainerProps {
    threadId: string
    sessionId?: string
    tools?: ToolDefinition[]
    mode?: 'auto' | 'workflow' | 'chat' | 'hybrid'
    apiUrl?: string
    onError?: (error: Error) => void
  }
  ```
- **Hooks Used**: useAGUI (main protocol hook), useEffect, useCallback
- **Children**: `Badge`, `MessageBubble`, `StreamingIndicator`, `MessageInput`
- **User Interaction**: Full chat experience (send messages, view responses, tool calls)
- **Problems**: None. Uses useAGUI hook for all protocol handling.

#### MessageBubble.tsx
- **Path**: `frontend/src/components/ag-ui/chat/MessageBubble.tsx`
- **Lines**: 161
- **Purpose**: Individual message display with role-based styling, tool call cards, and file messages
- **Props Interface**:
  ```
  MessageBubbleProps {
    message: ChatMessage
    isStreaming?: boolean
    onToolCallAction?: (toolCallId: string, action: 'approve' | 'reject') => void
    onDownload?: (fileId: string) => Promise<void>
  }
  ```
- **Hooks Used**: useCallback, useMemo
- **Children**: `ToolCallCard`, `FileMessageList`
- **User Interaction**: Tool call approve/reject buttons, file download
- **Problems**: None.

#### MessageInput.tsx
- **Path**: `frontend/src/components/ag-ui/chat/MessageInput.tsx`
- **Lines**: 152
- **Purpose**: Simple text input for AG-UI chat with character limit and streaming cancel
- **Props Interface**:
  ```
  MessageInputProps {
    onSend: (content: string) => void
    disabled?: boolean
    placeholder?: string
    maxLength?: number
    isStreaming?: boolean
    onCancel?: () => void
  }
  ```
- **State/Hooks**: useState x2 (value, charCount), useEffect (auto-resize), useCallback
- **Children**: `Textarea`, `Button`
- **User Interaction**: Text input, send, cancel streaming
- **Problems**: None.

#### StreamingIndicator.tsx
- **Path**: `frontend/src/components/ag-ui/chat/StreamingIndicator.tsx`
- **Lines**: 76
- **Purpose**: Animated dots indicator during AI response streaming
- **Props Interface**:
  ```
  StreamingIndicatorProps {
    isStreaming?: boolean
    text?: string
    size?: 'sm' | 'md' | 'lg'
    className?: string
  }
  ```
- **State/Hooks**: None (pure CSS animation)
- **Children**: None (self-contained)
- **Problems**: None. Clean, simple component.

#### ToolCallCard.tsx
- **Path**: `frontend/src/components/ag-ui/chat/ToolCallCard.tsx`
- **Lines**: 212
- **Purpose**: Card display for tool call state with arguments, results, and approval actions
- **Props Interface**:
  ```
  ToolCallCardProps {
    toolCall: ToolCallState
    compact?: boolean
    showArguments?: boolean
    showResult?: boolean
    onAction?: (toolCallId: string, action: 'approve' | 'reject') => void
    className?: string
  }
  ```
- **State/Hooks**: useState x2 (showArgs, showResult), useMemo
- **Children**: `Badge`, `Button`
- **User Interaction**: Toggle arguments/results, approve/reject actions
- **Problems**: None.

#### chat/index.ts (30 lines)
- Barrel export for ChatContainer, MessageBubble, MessageInput, ToolCallCard, StreamingIndicator

### 4.2 HITL Sub-directory (`ag-ui/hitl/`)

#### ApprovalBanner.tsx
- **Path**: `frontend/src/components/ag-ui/hitl/ApprovalBanner.tsx`
- **Lines**: 142
- **Purpose**: Inline banner for approval requests with compact mode
- **Props Interface**:
  ```
  ApprovalBannerProps {
    approval: PendingApproval
    onApprove: (approvalId: string) => void
    onReject: (approvalId: string) => void
    onShowDetails?: (approval: PendingApproval) => void
    compact?: boolean
    className?: string
  }
  ```
- **Hooks Used**: useMemo
- **Children**: `RiskBadge`, `Button`
- **User Interaction**: Approve, reject, show details
- **Problems**: None.

#### ApprovalDialog.tsx (ag-ui version)
- **Path**: `frontend/src/components/ag-ui/hitl/ApprovalDialog.tsx`
- **Lines**: 245
- **Purpose**: Modal approval dialog for AG-UI protocol with comment support
- **Props Interface**:
  ```
  ApprovalDialogProps {
    approval: PendingApproval
    isOpen: boolean
    onApprove: (approvalId: string, comment?: string) => void
    onReject: (approvalId: string, comment?: string) => void
    onClose: () => void
  }
  ```
- **State/Hooks**: useState x3 (comment, isSubmitting, tab), useMemo, useEffect, useCallback
- **Children**: `RiskBadge`, `Textarea`, `Button`
- **User Interaction**: Approve/reject with optional comment, close dialog
- **Note**: Differs from unified-chat's ApprovalDialog - this one uses approvalId in callbacks and supports comments

#### ApprovalList.tsx
- **Path**: `frontend/src/components/ag-ui/hitl/ApprovalList.tsx`
- **Lines**: 227
- **Purpose**: Filterable list of pending approvals with batch operations
- **Props Interface**:
  ```
  ApprovalListProps {
    approvals: PendingApproval[]
    onApprove: (approvalId: string) => void
    onReject: (approvalId: string) => void
    onShowDetails?: (approval: PendingApproval) => void
    enableBatchOps?: boolean
    className?: string
  }
  ```
- **State/Hooks**: useState x2 (selectedIds, filterLevel), useMemo, useCallback
- **Children**: `Button`, `ApprovalBanner`
- **User Interaction**: Filter by risk level, batch select, batch approve/reject, individual approve/reject
- **Problems**: None.

#### RiskBadge.tsx
- **Path**: `frontend/src/components/ag-ui/hitl/RiskBadge.tsx`
- **Lines**: 101
- **Purpose**: Visual badge for risk level (low/medium/high/critical)
- **Props Interface**:
  ```
  RiskBadgeProps {
    level: RiskLevel
    showScore?: boolean
    score?: number
    size?: 'sm' | 'md' | 'lg'
    className?: string
  }
  ```
- **State/Hooks**: None (pure presentational)
- **Problems**: None.

#### hitl/index.ts (26 lines)
- Barrel export for ApprovalDialog, ApprovalBanner, RiskBadge, ApprovalList

### 4.3 Advanced Sub-directory (`ag-ui/advanced/`)

#### CustomUIRenderer.tsx
- **Path**: `frontend/src/components/ag-ui/advanced/CustomUIRenderer.tsx`
- **Lines**: 179
- **Purpose**: Renders dynamic UI components from backend definitions (forms, charts, cards, tables)
- **Props Interface**:
  ```
  CustomUIRendererProps {
    definition: UIComponentDefinition
    onEvent?: (event: UIComponentEvent) => void
    className?: string
    isLoading?: boolean
    error?: string
  }
  ```
- **Hooks Used**: useMemo
- **Children**: `Card`, `CardHeader`/`CardTitle`/`CardDescription`/`CardContent`, `DynamicForm`, `DynamicChart`, `DynamicCard`, `DynamicTable`
- **Dispatches to**: DynamicForm (type='form'), DynamicChart (type='chart'), DynamicCard (type='card'), DynamicTable (type='table')
- **Problems**: None. Clean dispatcher pattern.

#### DynamicForm.tsx
- **Path**: `frontend/src/components/ag-ui/advanced/DynamicForm.tsx`
- **Lines**: 335
- **Purpose**: Dynamic form renderer from field definitions with validation
- **Props Interface**:
  ```
  DynamicFormProps {
    fields: FormFieldDefinition[]
    submitLabel?: string
    cancelLabel?: string
    onSubmit?: (data: Record<string, unknown>) => void
    onCancel?: () => void
    className?: string
  }
  ```
- **State/Hooks**: useState x3 (values, errors, isSubmitting), useCallback
- **Supported Field Types**: text, textarea, select, checkbox, radio, number, email, date
- **Children**: `Input`, `Textarea`, `Select`/`SelectTrigger`/`SelectValue`/`SelectContent`/`SelectItem`, `Checkbox`, `Label`, `RadioGroup`/`RadioGroupItem`, `Button`
- **User Interaction**: Form fill and submit, validation feedback
- **Problems**: None.

#### DynamicTable.tsx
- **Path**: `frontend/src/components/ag-ui/advanced/DynamicTable.tsx`
- **Lines**: 304
- **Purpose**: Dynamic data table with sorting, filtering, pagination, and row selection
- **Props Interface**:
  ```
  DynamicTableProps {
    columns: TableColumnDefinition[]
    rows: Record<string, unknown>[]
    pagination?: boolean
    pageSize?: number
    onRowSelect?: (row) => void
    onSort?: (column, direction) => void
    className?: string
  }
  ```
- **State/Hooks**: useState x4 (sort, page, filter, selected), useCallback, useMemo
- **Children**: `Table`/`TableHeader`/`TableRow`/`TableHead`/`TableBody`/`TableCell`, `Input`, `Button`
- **User Interaction**: Sort columns, filter, paginate, select rows
- **Problems**: None.

#### DynamicCard.tsx
- **Path**: `frontend/src/components/ag-ui/advanced/DynamicCard.tsx`
- **Lines**: 101
- **Purpose**: Dynamic card with optional image, title, subtitle, content, and action buttons
- **Props Interface**:
  ```
  DynamicCardProps {
    title?: string
    subtitle?: string
    content?: string
    imageUrl?: string
    actions?: CardAction[]
    onAction?: (action: string) => void
    className?: string
  }
  ```
- **State/Hooks**: None (pure presentational)
- **Children**: `Card`/`CardHeader`/`CardTitle`/`CardDescription`/`CardContent`/`CardFooter`, `Button`
- **User Interaction**: Action buttons
- **Problems**: None.

#### DynamicChart.tsx
- **Path**: `frontend/src/components/ag-ui/advanced/DynamicChart.tsx`
- **Lines**: 387
- **Purpose**: Dynamic chart renderer supporting bar, line, pie, scatter chart types via Recharts
- **Props Interface**:
  ```
  DynamicChartProps {
    chartType: ChartType
    data?: ChartData
    options?: Record<string, unknown>
    onDataPointClick?: (data: { label, value, datasetIndex }) => void
    className?: string
  }
  ```
- **Hooks Used**: useMemo
- **Children**: `Card`/`CardContent`/`CardHeader`/`CardTitle`, `BarChart`, `LineChart`, `PieChart`, `ScatterChart` (from Recharts)
- **User Interaction**: Click on data points
- **Problems**: None.

#### StateDebugger.tsx
- **Path**: `frontend/src/components/ag-ui/advanced/StateDebugger.tsx`
- **Lines**: 347
- **Purpose**: Debug panel for AG-UI shared state with JSON tree viewer, diff viewer, and conflict resolution
- **Props Interface**:
  ```
  StateDebuggerProps {
    state: SharedState
    syncStatus: StateSyncStatus
    onForceSync?: () => void
    onClearState?: () => void
    onResolveConflict?: (conflict: StateConflict, resolution: 'client' | 'server') => void
    className?: string
  }
  ```
- **State/Hooks**: useState x3 (expandedPaths, searchQuery, activeTab), useMemo
- **Internal Components**: `JsonTreeViewer`, `DiffViewer`, `ConflictViewer`
- **Children**: `Card`, `Collapsible`, `Badge`, `Button`
- **User Interaction**: Expand/collapse JSON paths, search state, force sync, clear state, resolve conflicts
- **Problems**: None. Development-focused tool.

#### OptimisticIndicator.tsx
- **Path**: `frontend/src/components/ag-ui/advanced/OptimisticIndicator.tsx`
- **Lines**: 295
- **Purpose**: Visual indicator for optimistic/predictive state updates with confirm/rollback controls
- **Props Interface**:
  ```
  OptimisticIndicatorProps {
    predictions: PredictionResult[]
    isOptimistic: boolean
    onConfirm?: (predictionId: string) => void
    onRollback?: (predictionId: string) => void
    compact?: boolean
    className?: string
  }
  ```
- **Exported**: `STATUS_LABELS` constant, `OptimisticIndicator` component
- **Hooks Used**: useMemo
- **Internal Components**: `CompactIndicator`, `PredictionItem`
- **Children**: `Badge`, `Tooltip`/`TooltipProvider`/`TooltipTrigger`/`TooltipContent`
- **User Interaction**: Confirm or rollback predictions
- **Problems**: None.

#### advanced/index.ts (35 lines)
- Barrel export for CustomUIRenderer, DynamicForm, DynamicChart, DynamicCard, DynamicTable, StateDebugger, OptimisticIndicator

---

## 5. Cross-Reference Analysis

### 5.1 Component Dependency Graph

```
UnifiedChat.tsx (page)
  ├── ChatHeader ← ConnectionStatus
  ├── ChatArea
  │   ├── MessageList
  │   │   ├── MessageBubble (ag-ui/chat)
  │   │   │   ├── ToolCallCard (ag-ui/chat)
  │   │   │   └── FileMessageList (unified-chat)
  │   │   ├── ApprovalMessageCard (unified-chat)
  │   │   │   └── TimeoutCountdown (internal)
  │   │   └── CustomUIRenderer (ag-ui/advanced)
  │   │       ├── DynamicForm
  │   │       ├── DynamicChart
  │   │       ├── DynamicCard
  │   │       └── DynamicTable
  │   └── StreamingIndicator (ag-ui/chat)
  ├── ChatInput
  │   └── CompactAttachmentPreview
  ├── WorkflowSidePanel
  │   ├── StepProgress
  │   ├── ToolCallTracker
  │   └── CheckpointList
  ├── OrchestrationPanel
  │   ├── AgentSwarmPanel
  │   │   ├── SwarmHeader
  │   │   ├── OverallProgress
  │   │   └── WorkerCardList → WorkerCard
  │   └── WorkerDetailDrawer
  │       ├── WorkerDetailHeader
  │       ├── CurrentTask
  │       ├── ExtendedThinkingPanel
  │       ├── ToolCallsPanel → ToolCallItem
  │       ├── MessageHistory
  │       └── CheckpointPanel
  ├── StatusBar
  ├── ModeIndicator
  ├── RiskIndicator
  ├── ChatHistoryPanel
  ├── ModeSwitchConfirmDialog
  ├── RestoreConfirmDialog
  ├── ApprovalDialog
  ├── ErrorBoundary (wrapping ChatArea)
  └── FileUpload / AttachmentPreview / FileRenderer
```

### 5.2 Cross-directory Dependencies

| From | To | Components |
|------|----|-----------|
| unified-chat/MessageList | ag-ui/chat | MessageBubble |
| unified-chat/MessageList | ag-ui/advanced | CustomUIRenderer |
| unified-chat/ChatArea | ag-ui/chat | StreamingIndicator |
| unified-chat/ChatInput | unified-chat | CompactAttachmentPreview |
| unified-chat/OrchestrationPanel | agent-swarm | AgentSwarmPanel, WorkerDetailDrawer |
| unified-chat/WorkerDetailDrawer | agent-swarm/hooks | useWorkerDetail |
| agent-swarm/hooks/useSwarmEventHandler | stores | useSwarmStore (Zustand) |
| agent-swarm/hooks/useSwarmStatus | stores | useSwarmStore (Zustand) |
| ag-ui/hitl/ApprovalList | ag-ui/hitl | ApprovalBanner |
| ag-ui/advanced/CustomUIRenderer | ag-ui/advanced | DynamicForm, DynamicChart, DynamicCard, DynamicTable |

### 5.3 Relationship to D5 (AG-UI), D6 (UnifiedChat), D9 (Swarm), H3 (Swarm Frontend)

- **D5 (AG-UI Protocol)**: ag-ui/ components provide the protocol-level UI. ChatContainer uses useAGUI hook. MessageBubble renders ChatMessage types. ToolCallCard renders ToolCallState. HITL components handle PendingApproval flows.
- **D6 (UnifiedChat)**: unified-chat/ provides the application-level chat interface that composes ag-ui/ protocol components. ChatArea orchestrates MessageList (which uses ag-ui/MessageBubble). ChatInput adds file attachment layer on top.
- **D9 (Swarm)**: agent-swarm/ sub-module provides complete swarm visualization. Types mirror backend SSE events (snake_case). Hooks bridge SSE events to Zustand store.
- **H3 (Swarm Frontend)**: OrchestrationPanel integrates swarm visualization into the main chat interface. useSwarmEventHandler processes real-time events. useSwarmStatus provides derived state from store.

---

## 6. Issues and Findings

### 6.1 Console.log in Production Code

| Severity | File | Issue |
|----------|------|-------|
| LOW | `agent-swarm/hooks/useSwarmEventHandler.ts` | 9 console.log calls - but gated behind `debug` option parameter |
| LOW | `agent-swarm/hooks/useSwarmEvents.ts` | 3 console.log in JSDoc examples (not executable) |
| OK | `ErrorBoundary.tsx` | console.error in componentDidCatch (appropriate) |
| OK | `renderers/CodePreview.tsx` | console.error for clipboard failure (appropriate) |
| OK | `renderers/TextPreview.tsx` | console.error for clipboard failure (appropriate) |

**Recommendation**: The useSwarmEventHandler.ts console.log calls are properly gated behind a `debug` flag. No action needed, but consider using a logging utility for consistency.

### 6.2 Duplicate Components

| Component | unified-chat | ag-ui | Notes |
|-----------|-------------|-------|-------|
| ApprovalDialog | Yes (384 lines) | Yes (245 lines) | Different prop signatures. unified-chat version has TimeoutCountdown; ag-ui version supports comments with approvalId |
| Streaming indicator | Via ag-ui import | StreamingIndicator.tsx | No duplication - unified-chat imports from ag-ui |

**Assessment**: The two ApprovalDialog components serve different purposes. The unified-chat version is more feature-rich (timeout countdown, risk indicator integration), while the ag-ui version is protocol-focused (comment support, simpler interface). This is intentional layering, not unnecessary duplication.

### 6.3 Accessibility Analysis

| Category | Status | Details |
|----------|--------|---------|
| ARIA roles | GOOD | MessageList uses role="log", aria-live="polite" |
| ARIA labels | GOOD | ChatInput has aria-label, aria-describedby |
| Screen reader | GOOD | sr-only announcements for streaming state |
| Keyboard nav | GOOD | Enter/Shift+Enter/Cmd+Enter in ChatInput |
| Reduced motion | GOOD | MessageList respects prefers-reduced-motion |
| Focus management | GOOD | Auto-focus on mount in ChatInput |
| Color contrast | OK | Risk levels use distinct color schemes with dark mode support |
| Missing | MODERATE | Some swarm components lack explicit aria-labels (WorkerCard, ToolCallItem) |

### 6.4 Error Boundary Coverage

- `ErrorBoundary.tsx` wraps `ChatArea` (via `ErrorBoundaryWrapper`)
- No error boundaries around:
  - `OrchestrationPanel` (contains complex swarm visualization)
  - `WorkerDetailDrawer` (external data fetching)
  - `FileRenderer` (handles various file types)
  - `CustomUIRenderer` (renders dynamic backend-defined UI)

**Recommendation**: Add error boundaries around OrchestrationPanel, WorkerDetailDrawer, and CustomUIRenderer since they handle dynamic external data.

### 6.5 Missing Tests

| Directory | Has Tests | Coverage |
|-----------|-----------|----------|
| unified-chat/ (core) | No | 0% - ChatArea, ChatInput, MessageList, etc. have no tests |
| unified-chat/agent-swarm/ | Yes | Good - 12 test files covering all Sprint 102-104 components |
| ag-ui/ | No | 0% - No tests for any ag-ui components |

**Recommendation**: Priority test additions needed for ChatInput (keyboard handling), MessageList (timeline merging), ApprovalMessageCard (timeout/state transitions), and ag-ui/ChatContainer (protocol integration).

### 6.6 Component Size Analysis

| Component | Lines | Complexity | Notes |
|-----------|-------|-----------|-------|
| OrchestrationPanel.tsx | 509 | HIGH | Largest component. Consider splitting phase sections into sub-components |
| ApprovalMessageCard.tsx | 491 | MODERATE | Well-structured with internal sub-components |
| ApprovalDialog.tsx (unified-chat) | 384 | MODERATE | Acceptable |
| DynamicChart.tsx | 387 | MODERATE | Multiple chart types warrant the size |
| StateDebugger.tsx | 347 | MODERATE | Development tool, acceptable |
| AttachmentPreview.tsx | 337 | LOW | Two variant components |
| DynamicForm.tsx | 335 | MODERATE | Many field types warrant the size |
| WorkerActionList.tsx | 334 | LOW | Mostly config/mapping data |

### 6.7 Architecture Quality

**Strengths**:
1. Clean layered architecture: ag-ui (protocol) -> unified-chat (application) -> pages
2. Consistent use of TypeScript interfaces for all props
3. Barrel exports at every directory level
4. Good separation of concerns (types, hooks, components, tests in agent-swarm)
5. Consistent naming conventions (PascalCase components, camelCase hooks)
6. Dark mode support throughout
7. Proper use of Zustand for global state (swarm), local state for UI
8. SSE event types properly use snake_case to match backend convention
9. All components are functional (except ErrorBoundary which requires class)

**Weaknesses**:
1. No tests for unified-chat core components or ag-ui components
2. Missing error boundaries for external-data-dependent components
3. Some swarm components lack explicit accessibility attributes
4. OrchestrationPanel could benefit from sub-component extraction (509 lines)
5. Two ApprovalDialog variants could share common base logic

---

*Analysis complete. 82 files fully read and documented.*
*Agent E2 - Phase 3E Frontend Part 2*

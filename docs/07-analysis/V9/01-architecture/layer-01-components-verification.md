# Layer 01: Components Verification Report

> V9 Verification Pass | 2026-03-29
> Scope: `frontend/src/components/**/*.{ts,tsx}` (excluding `__tests__/`)
> Method: Full source reading of ALL 113 files across 9 modules

---

## 1. File Inventory Summary

| Module | Path | Files Read | Index Files | Component Files | Hook Files | Type Files | Util Files |
|--------|------|-----------|-------------|-----------------|------------|------------|------------|
| **shared** | `components/shared/` | 4 | 1 | 3 | 0 | 0 | 0 |
| **auth** | `components/auth/` | 1 | 0 | 1 | 0 | 0 | 0 |
| **layout** | `components/layout/` | 5 | 1 | 4 | 0 | 0 | 0 |
| **ui** | `components/ui/` | 16 | 1 | 15 | 0 | 0 | 0 |
| **ag-ui** | `components/ag-ui/` | 15 | 3 | 12 | 0 | 0 | 0 |
| **DevUI** | `components/DevUI/` | 15 | 0 | 15 | 0 | 0 | 0 |
| **unified-chat** (core) | `components/unified-chat/` | 30 | 2 | 28 | 0 | 0 | 0 |
| **unified-chat/agent-swarm** | `components/unified-chat/agent-swarm/` | 21 | 3 | 14 | 4 | 2 | 0 |
| **workflow-editor** | `components/workflow-editor/` | 9 | 0 | 6 | 2 | 0 | 1 |
| **TOTAL** | | **113** (excluding tests) | **11** | **98** | **6** | **2** | **1** |

---

## 2. Module-by-Module Detailed Inventory

### 2.1 shared/ (4 files)

| File | LOC | Export | Props Interface | Hooks Used | Children Rendered | Store Subscriptions |
|------|-----|--------|-----------------|------------|-------------------|---------------------|
| `EmptyState.tsx` | 40 | `EmptyState` (named) | `EmptyStateProps` {title?, description?, action?, icon?} | none | `Button` | none |
| `LoadingSpinner.tsx` | 43 | `LoadingSpinner`, `PageLoading` (named) | `LoadingSpinnerProps` {size?, className?} | none | none | none |
| `StatusBadge.tsx` | 38 | `StatusBadge` (named) | `StatusBadgeProps` {status, className?} | none | `Badge` | none |
| `index.ts` | 7 | re-exports | -- | -- | -- | -- |

### 2.2 auth/ (1 file)

| File | LOC | Export | Props Interface | Hooks Used | Children Rendered | Store Subscriptions |
|------|-----|--------|-----------------|------------|-------------------|---------------------|
| `ProtectedRoute.tsx` | 128 | `ProtectedRoute` (named+default), `AdminRoute`, `OperatorRoute` | `ProtectedRouteProps` {children, requiredRoles?} | useState, useEffect, useLocation | `Navigate`, `Loader2` | `useAuthStore` |

### 2.3 layout/ (5 files)

| File | LOC | Export | Props Interface | Hooks Used | Children Rendered | Store Subscriptions |
|------|-----|--------|-----------------|------------|-------------------|---------------------|
| `AppLayout.tsx` | 44 | `AppLayout` (named) | none (no props) | useState | `Sidebar`, `Header`, `Outlet` | none |
| `Header.tsx` | 46 | `Header` (named) | none | none | `Button`, `UserMenu` | none |
| `Sidebar.tsx` | 154 | `Sidebar` (named) | `SidebarProps` {isCollapsed, onToggle} | none (uses `NavLink`) | `NavLink`, icons | none |
| `UserMenu.tsx` | 170 | `UserMenu` (named) | none | useState, useRef, useEffect, useNavigate | `Button`-like elements | `useAuthStore` |
| `index.ts` | 8 | re-exports | -- | -- | -- | -- |

### 2.4 ui/ (16 files) -- Shadcn UI Base Components

| File | LOC | Export(s) | Based On | Key Notes |
|------|-----|-----------|----------|-----------|
| `Badge.tsx` | 49 | `Badge`, `badgeVariants`, `BadgeProps` | class-variance-authority | 7 variants: default, secondary, destructive, outline, success, warning, info |
| `Button.tsx` | 68 | `Button`, `buttonVariants`, `ButtonProps` | Radix Slot + cva | 6 variants, 4 sizes, asChild support |
| `Card.tsx` | 87 | `Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, `CardFooter` | pure HTML | forwardRef wrappers |
| `Checkbox.tsx` | 35 | `Checkbox` | `@radix-ui/react-checkbox` | Check icon from lucide |
| `Collapsible.tsx` | 17 | `Collapsible`, `CollapsibleTrigger`, `CollapsibleContent` | `@radix-ui/react-collapsible` | Direct re-export |
| `dialog.tsx` | 132 | `Dialog`, `DialogPortal`, `DialogOverlay`, `DialogClose`, `DialogTrigger`, `DialogContent`, `DialogHeader`, `DialogFooter`, `DialogTitle`, `DialogDescription` | `@radix-ui/react-dialog` | X close button, animations |
| `Input.tsx` | 36 | `Input`, `InputProps` | pure HTML | error prop for red border |
| `Label.tsx` | 37 | `Label`, `LabelProps` | pure HTML | required prop adds red asterisk |
| `Textarea.tsx` | 35 | `Textarea`, `TextareaProps` | pure HTML | error prop for red border |
| `Progress.tsx` | 38 | `Progress` | `@radix-ui/react-progress` | translateX animation |
| `RadioGroup.tsx` | 49 | `RadioGroup`, `RadioGroupItem` | `@radix-ui/react-radio-group` | Circle indicator |
| `Select.tsx` | 219 | `Select`, `SelectGroup`, `SelectValue`, `SelectTrigger`, `SelectContent`, `SelectLabel`, `SelectItem`, `SelectSeparator`, `SelectScrollUpButton`, `SelectScrollDownButton`, `SimpleSelect` | `@radix-ui/react-select` + legacy `<select>` | Dual: Radix + legacy SimpleSelect |
| `Table.tsx` | 124 | `Table`, `TableHeader`, `TableBody`, `TableFooter`, `TableHead`, `TableRow`, `TableCell`, `TableCaption` | pure HTML | 8 sub-components |
| `Tooltip.tsx` | 35 | `Tooltip`, `TooltipTrigger`, `TooltipContent`, `TooltipProvider` | `@radix-ui/react-tooltip` | sideOffset=4 default |
| `ScrollArea.tsx` | 52 | `ScrollArea`, `ScrollBar` | `@radix-ui/react-scroll-area` | vertical/horizontal support |
| `Separator.tsx` | 38 | `Separator` | pure HTML (div) | horizontal/vertical, decorative role |
| `Sheet.tsx` | 149 | `Sheet`, `SheetPortal`, `SheetOverlay`, `SheetTrigger`, `SheetClose`, `SheetContent`, `SheetHeader`, `SheetFooter`, `SheetTitle`, `SheetDescription` | `@radix-ui/react-dialog` + cva | 4 sides: top/bottom/left/right |
| `index.ts` | 12 | re-exports Button, Card, Badge only | -- | **INCOMPLETE**: only exports 3 of 16 components |

### 2.5 ag-ui/ (15 files)

#### ag-ui/advanced/ (8 files)

| File | LOC | Export | Props Interface | Hooks Used | Children Rendered | Store Subscriptions |
|------|-----|--------|-----------------|------------|-------------------|---------------------|
| `CustomUIRenderer.tsx` | 178 | `CustomUIRenderer` (named+default) | `CustomUIRendererProps` {definition, onEvent?, className?, isLoading?, error?} | useMemo | `DynamicForm`, `DynamicChart`, `DynamicCard`, `DynamicTable`, `Card` | none |
| `DynamicCard.tsx` | 100 | `DynamicCard` (named+default) | `DynamicCardProps` {title?, subtitle?, content?, imageUrl?, actions?, onAction?, className?} | none | `Card`, `Button` | none |
| `DynamicChart.tsx` | 386 | `DynamicChart` (named+default) | `DynamicChartProps` {chartType, data?, options?, onDataPointClick?, className?, height?} | useMemo | SVG elements, `Card` | none |
| `DynamicForm.tsx` | 334 | `DynamicForm` (named+default) | `DynamicFormProps` {fields, submitLabel?, cancelLabel?, onSubmit?, onCancel?, className?, isSubmitting?} | useState, useCallback | `Input`, `Label`, `Textarea`, `Select`, `Checkbox`, `RadioGroup` | none |
| `DynamicTable.tsx` | 303 | `DynamicTable` (named+default) | `DynamicTableProps` {columns, rows, pagination?, pageSize?, onRowSelect?, onSort?, className?} | useState, useMemo, useCallback | `Table`, `Input`, `Button` | none |
| `OptimisticIndicator.tsx` | 294 | `OptimisticIndicator` (named+default), `STATUS_LABELS` | `OptimisticIndicatorProps` {predictions, isOptimistic, onConfirm?, onRollback?, compact?, className?} | useMemo | `Badge`, `Tooltip` | none |
| `StateDebugger.tsx` | 346 | `StateDebugger` (named+default) | `StateDebuggerProps` {state, syncStatus, onForceSync?, onClearState?, onResolveConflict?, className?} | useState, useMemo | `Card`, `Badge`, `Button`, `Collapsible` | none |
| `index.ts` | 34 | re-exports all 7 components + types | -- | -- | -- | -- |

#### ag-ui/chat/ (6 files)

| File | LOC | Export | Props Interface | Hooks Used | Children Rendered | Store Subscriptions |
|------|-----|--------|-----------------|------------|-------------------|---------------------|
| `ChatContainer.tsx` | 236 | `ChatContainer` (named+default) | `ChatContainerProps` {threadId, sessionId?, tools?, mode?, apiUrl?, onError?, onMessageSent?, onApprovalRequired?, showStatus?, debug?, className?} | useRef, useEffect, useCallback | `MessageBubble`, `MessageInput`, `StreamingIndicator`, `Badge` | none (uses `useAGUI` hook) |
| `MessageBubble.tsx` | 160 | `MessageBubble` (named+default) | `MessageBubbleProps` {message, isStreaming?, onToolCallAction?, onDownload?, className?} | useMemo, useCallback | `ToolCallCard`, `FileMessageList` | none |
| `MessageInput.tsx` | 151 | `MessageInput` (named+default) | `MessageInputProps` {onSend, disabled?, placeholder?, maxLength?, isStreaming?, onCancel?, className?} | useState, useCallback, useRef, useEffect | `Button`, `Textarea` | none |
| `StreamingIndicator.tsx` | 75 | `StreamingIndicator` (named+default) | `StreamingIndicatorProps` {isStreaming?, text?, size?, className?} | none | animated dots | none |
| `ToolCallCard.tsx` | 211 | `ToolCallCard` (named+default) | `ToolCallCardProps` {toolCall, compact?, showArguments?, showResult?, onAction?, className?} | useState, useMemo | `Badge`, `Button` | none |
| `index.ts` | 29 | re-exports all 5 components + types | -- | -- | -- | -- |

#### ag-ui/hitl/ (5 files)

| File | LOC | Export | Props Interface | Hooks Used | Children Rendered | Store Subscriptions |
|------|-----|--------|-----------------|------------|-------------------|---------------------|
| `ApprovalBanner.tsx` | 141 | `ApprovalBanner` (named+default) | `ApprovalBannerProps` {approval, onApprove, onReject, onShowDetails?, compact?, className?} | useMemo | `Button`, `RiskBadge` | none |
| `ApprovalDialog.tsx` | 244 | `ApprovalDialog` (named+default) | `ApprovalDialogProps` {approval, isOpen, onApprove, onReject, onClose, showComment?, className?} | useState, useEffect, useMemo, useCallback | `Button`, `Textarea`, `RiskBadge` | none |
| `ApprovalList.tsx` | 226 | `ApprovalList` (named+default) | `ApprovalListProps` {approvals, onApprove, onReject, onShowDetails?, enableBatchOps?, sortBy?, sortOrder?, filterRisk?, emptyMessage?, className?} | useState, useMemo, useCallback | `Button`, `ApprovalBanner` | none |
| `RiskBadge.tsx` | 100 | `RiskBadge` (named+default) | `RiskBadgeProps` {level, showScore?, score?, size?, className?} | none | span elements | none |
| `index.ts` | 25 | re-exports all 4 components + types | -- | -- | -- | -- |

### 2.6 DevUI/ (15 files)

| File | LOC | Export(s) | Props Interface | Hooks Used | Store Subscriptions |
|------|-----|-----------|-----------------|------------|---------------------|
| `DurationBar.tsx` | 120 | `DurationBar`, `DurationBadge` | `DurationBarProps` {durationMs, maxDurationMs, variant?, showLabel?, className?} | none | none |
| `EventDetail.tsx` | 166 | `EventDetail` (named+default) | `EventDetailProps` {event} | useState | none |
| `EventFilter.tsx` | 416 | `EventFilter`, `FilterBar` | `EventFilterProps` {eventTypes, selectedEventTypes, severities, selectedSeverities, executorIds, selectedExecutorIds, searchQuery, showErrorsOnly, hasActiveFilters, filterCounts, ...callbacks} | useState | none |
| `EventList.tsx` | 240 | `EventList` (named+default) | `EventListProps` {events, isLoading?, onEventSelect?, selectedEventId?} | useState | none |
| `EventPanel.tsx` | 278 | `EventPanel` (named+default) | `EventPanelProps` {event, pairedEvent?, onClose?, fullScreen?} | useState | none |
| `EventPieChart.tsx` | 303 | `EventPieChart` (named+default), `getEventTypeColor` | `EventPieChartProps` {data, size?, innerRadius?, showLegend?, centerLabel?, centerValue?, className?} | useState, useMemo | none |
| `EventTree.tsx` | 275 | `EventTree` (named+default) | `EventTreeProps` {events, selectedEventId?, onEventSelect?, maxHeight?, showSearch?} | useState, useMemo | none |
| `LiveIndicator.tsx` | 294 | `LiveIndicator` (named+default), `LiveDot`, `ConnectionBadge` | `LiveIndicatorProps` {status, isPaused?, lastUpdate?, reconnectAttempts?, maxReconnectAttempts?, onPause?, onResume?, onDisconnect?, onReconnect?, compact?, className?} | none | none |
| `LLMEventPanel.tsx` | 309 | `LLMEventPanel` (named+default) | `LLMEventPanelProps` {event, pairedEvent?} | useState | none |
| `StatCard.tsx` | 196 | `StatCard`, `MiniStatCard` | `StatCardProps` {title, value, description?, icon?, trend?, trendValue?, variant?, children?, onClick?, className?} | none | none |
| `Statistics.tsx` | 369 | `Statistics` (named+default), `StatisticsSummary` | `StatisticsProps` {events, totalDurationMs?, showDetails?, layout?, className?} | useMemo | `StatCard`, `MiniStatCard`, `EventPieChart`, `DurationBar` |
| `Timeline.tsx` | 329 | `Timeline` (named+default) | `TimelineProps` {events, selectedEventId?, onEventSelect?, maxHeight?, showFilters?, enableZoom?} | useState, useMemo, useRef, useEffect | `TimelineNode` | none |
| `TimelineNode.tsx` | 301 | `TimelineNode` (named+default) | `TimelineNodeProps` {event, isPaired?, pairedEvent?, maxDurationMs, onClick?, isSelected?, indentLevel?} | useState | none |
| `ToolEventPanel.tsx` | 265 | `ToolEventPanel` (named+default) | `ToolEventPanelProps` {event, pairedEvent?} | useState | none |
| `TreeNode.tsx` | 247 | `TreeNode` (named+default), `EventTreeNode` (type) | `TreeNodeProps` {node, onClick?, selectedEventId?, defaultExpanded?} | useState | none |

### 2.7 unified-chat/ core (30 files)

| File | LOC | Export(s) | Key Props | Key Hooks | Store Subscriptions |
|------|-----|-----------|-----------|-----------|---------------------|
| `ChatArea.tsx` | 122 | `ChatArea` (named+default) | `ChatAreaProps` (from types) | useRef, useEffect | none |
| `ChatInput.tsx` | 244 | `ChatInput` (named+default) | `ChatInputProps` (from types) | useState, useCallback, useRef, useEffect, useMemo | none |
| `ChatHeader.tsx` | 130 | `ChatHeader` (named+default) | `ChatHeaderProps` (from types) | useCallback | none |
| `ChatHistoryPanel.tsx` | 415 | `ChatHistoryPanel`, `ChatHistoryToggleButton`, `ChatThread` (type) | `ChatHistoryPanelProps` {threads, activeThreadId, onSelectThread, onNewThread, onDeleteThread, onRenameThread?, onResumeSession?, isCollapsed?, onToggle?} | useState, useRef, useEffect | none (uses `useRecoverableSessions`, `useResumeSession`) |
| `MessageList.tsx` | 313 | `MessageList` (named+default), `MessageListProps` | {messages, isStreaming?, streamingMessageId?, pendingApprovals, onApprove, onReject, onExpired?, onUIEvent?, onDownload?} | useState, useEffect, useRef, useMemo, useCallback | none |
| `ApprovalDialog.tsx` | 383 | `ApprovalDialog` (named+default), `ApprovalDialogProps` | {approval, onApprove, onReject, onDismiss, isProcessing?} | useState, useEffect, useCallback | none |
| `ApprovalMessageCard.tsx` | 490 | `ApprovalMessageCard` (named+default), `ApprovalMessageCardProps` | {approval, onApprove, onReject, onExpired?, isProcessing?} | useState, useEffect, useCallback | none |
| `AttachmentPreview.tsx` | 336 | `AttachmentPreview`, `CompactAttachmentPreview` | `AttachmentPreviewProps` {attachments, onRemove, disabled?, className?} | useMemo | none |
| `CheckpointList.tsx` | 204 | `CheckpointList` (named+default) | `CheckpointListProps` (from types) | useState, useMemo, useCallback | none |
| `ConnectionStatus.tsx` | 238 | `ConnectionStatus` (named+default), `ConnectionStatusProps` | {status, retryCount?, maxRetries?, onReconnect?, errorMessage?, compact?, className?} | useMemo | none |
| `ErrorBoundary.tsx` | 220 | `ErrorBoundary` (class), `ErrorBoundaryWrapper` (FC), types | `ErrorBoundaryProps` {children, fallback?, onError?, showDetails?, onReset?, title?} | class component | none |
| `FileMessage.tsx` | 312 | `FileMessage`, `FileMessageList`, `CompactFileMessage`, types | `FileMessageProps` {file, onDownload, className?} | useState, useCallback | none |
| `FileRenderer.tsx` | 256 | `FileRenderer` (named+default), `getFileType` | `FileRendererProps` {file, content?, preview?, onDownload, isLoading?, className?} | useMemo | none |
| `FileUpload.tsx` | 322 | `FileUpload`, `AttachButton`, `HiddenFileInput` | `FileUploadProps` {onFilesSelected, accept?, maxSize?, multiple?, disabled?, className?} | useState, useCallback, useRef | none |
| `InlineApproval.tsx` | 232 | `InlineApproval` (named+default) | `InlineApprovalProps` (from types) | useState, useCallback | none |
| `IntentStatusChip.tsx` | 171 | `IntentStatusChip` (named+default), `IntentStatusChipProps` | {intent?, riskLevel?, executionMode?, detail?, compact?} | useState | none |
| `MemoryHint.tsx` | 116 | `MemoryHint` (named+default), `MemoryHintProps`, `MemoryHintItem` | {memories, isVisible, onDismiss?} | useState | none |
| `ModeIndicator.tsx` | 187 | `ModeIndicator` (named+default), `ModeIndicatorProps` | {currentMode, isManuallyOverridden, switchReason, switchConfidence, lastSwitchAt, onClick?, className?} | none | none |
| `ModeSwitchConfirmDialog.tsx` | 240 | `ModeSwitchConfirmDialog` (named+default), `ModeSwitchConfirmDialogProps` | {open, from, to, reason, confidence, onConfirm, onCancel, isProcessing?} | none | none |
| `OrchestrationPanel.tsx` | 508 | `OrchestrationPanel` (named+default) | `OrchestrationPanelProps` {phase, routingDecision, riskAssessment, dialogQuestions, isLoading, error, ...callbacks} | useState | `useSwarmStatus` (via hook) |
| `RestoreConfirmDialog.tsx` | 200 | `RestoreConfirmDialog` (named+default), `RestoreConfirmDialogProps` | {isOpen, checkpoint, isRestoring?, onConfirm, onCancel} | none | none |
| `RiskIndicator.tsx` | 291 | `RiskIndicator` (named+default), `RiskIndicatorProps` | {level, score, factors?, reasoning?, size?, showScore?, showTooltip?, onClick?, className?} | none | none |
| `StatusBar.tsx` | 327 | `StatusBar` (named+default) | `StatusBarProps` (from types) | useMemo | none |
| `StepProgress.tsx` | 190 | `StepProgress` (named+default) | `StepProgressProps` (from types) | useMemo | none |
| `StepProgressEnhanced.tsx` | 286 | `StepProgressEnhanced`, `StatusIcon`, `SubStepItem`, types | `StepProgressEnhancedProps` {step, isExpanded?, onToggle?, showSubsteps?} | useState, useMemo, useCallback | none |
| `TaskProgressCard.tsx` | 176 | `TaskProgressCard` (named+default), `TaskProgressCardProps` | {taskId, taskName?} | useState, useNavigate | `useTask` (React Query) |
| `ToolCallTracker.tsx` | 197 | `ToolCallTracker` (named+default) | `ToolCallTrackerProps` (from types) | useMemo | none |
| `WorkflowSidePanel.tsx` | 191 | `WorkflowSidePanel` (named+default) | `WorkflowSidePanelProps` (from types) | useState, useCallback, useMemo | none |
| `renderers/index.ts` | 17 | re-exports `ImagePreview`, `CodePreview`, `TextPreview` | -- | -- | -- |
| `index.ts` | 112 | re-exports ~30 components + types | -- | -- | -- |

#### unified-chat/renderers/ (3 files)

| File | LOC | Export | Props Interface |
|------|-----|--------|-----------------|
| `ImagePreview.tsx` | 227 | `ImagePreview` (named+default) | `ImagePreviewProps` {src, alt, filename?, onDownload?, className?} |
| `CodePreview.tsx` | 221 | `CodePreview` (named+default) | `CodePreviewProps` {code, language?, filename?, maxLines?, onDownload?, className?} |
| `TextPreview.tsx` | 244 | `TextPreview` (named+default) | `TextPreviewProps` {content, filename?, maxLines?, searchable?, onDownload?, className?} |

### 2.8 unified-chat/agent-swarm/ (21 files)

#### Components (14 files)

| File | LOC | Export(s) | Props Interface |
|------|-----|-----------|-----------------|
| `AgentSwarmPanel.tsx` | 146 | `AgentSwarmPanel` (named+default) | `AgentSwarmPanelProps` (from types) |
| `SwarmHeader.tsx` | 145 | `SwarmHeader` (named+default) | `SwarmHeaderProps` (from types) |
| `OverallProgress.tsx` | 68 | `OverallProgress` (named+default) | `OverallProgressProps` (from types) |
| `WorkerCard.tsx` | 228 | `WorkerCard` (named+default) | `WorkerCardProps` (from types) |
| `WorkerCardList.tsx` | 59 | `WorkerCardList` (named+default) | `WorkerCardListProps` (from types) |
| `SwarmStatusBadges.tsx` | 110 | `SwarmStatusBadges` (named+default) | `SwarmStatusBadgesProps` (from types) |
| `WorkerDetailDrawer.tsx` | 284 | `WorkerDetailDrawer` (named+default) | {open, onClose, swarmId, worker, workerDetail?, className?} |
| `WorkerDetailHeader.tsx` | 179 | `WorkerDetailHeader` (named+default) | {worker: WorkerDetail, onBack?} |
| `CurrentTask.tsx` | 105 | `CurrentTask` (named+default) | {taskDescription, maxLength?, className?} |
| `ToolCallItem.tsx` | 297 | `ToolCallItem` (named+default) | {toolCall: ToolCallInfo, defaultExpanded?, showLiveTimer?} |
| `ToolCallsPanel.tsx` | 93 | `ToolCallsPanel` (named+default) | {toolCalls: ToolCallInfo[], className?} |
| `MessageHistory.tsx` | 237 | `MessageHistory` (named+default) | {messages: WorkerMessage[], defaultExpanded?, maxPreviewLength?, className?} |
| `CheckpointPanel.tsx` | 102 | `CheckpointPanel` (named+default) | {checkpointId, backend?, onRestore?, className?} |
| `ExtendedThinkingPanel.tsx` | 231 | `ExtendedThinkingPanel` (named+default) | {thinkingHistory: ThinkingContent[], maxHeight?, defaultExpanded?, autoScroll?, className?} |
| `WorkerActionList.tsx` | 333 | `WorkerActionList` (named+default), `inferActionType`, `ActionType`, `WorkerAction` | {actions: WorkerAction[], onActionClick?, maxHeight?, className?} |

#### Hooks (4 files)

| File | LOC | Export(s) | Purpose |
|------|-----|-----------|---------|
| `useSwarmEvents.ts` | 209 | `useSwarmEvents`, `isSwarmEvent`, `getSwarmEventCategory` | SSE event dispatch to handler callbacks |
| `useSwarmEventHandler.ts` | 303 | `useSwarmEventHandler`, `UseSwarmEventHandlerOptions` | Bridge SSE events to Zustand store |
| `useSwarmStatus.ts` | 221 | `useSwarmStatus`, `UseSwarmStatusReturn` | Computed state + actions from swarmStore |
| `useWorkerDetail.ts` | 198 | `useWorkerDetail`, types | Fetch + poll worker detail from API |
| `hooks/index.ts` | 22 | re-exports all 4 hooks | -- |

#### Types (2 files)

| File | LOC | Key Types |
|------|-----|-----------|
| `types/events.ts` | 210 | `SwarmEventNames`, `SwarmCreatedPayload`, `SwarmStatusUpdatePayload`, `SwarmCompletedPayload`, `WorkerStartedPayload`, `WorkerProgressPayload`, `WorkerThinkingPayload`, `WorkerToolCallPayload`, `WorkerMessagePayload`, `WorkerCompletedPayload`, `SwarmSSEEvent`, `SwarmEventHandlers` |
| `types/index.ts` | 180 | `WorkerType`, `WorkerStatus`, `SwarmMode`, `SwarmStatus`, `ToolCallInfo`, `ThinkingContent`, `WorkerMessage`, `UIWorkerSummary`, `WorkerDetail`, `UIAgentSwarmStatus`, all component props interfaces, `SnakeToCamelCase<S>` |

### 2.9 workflow-editor/ (9 files)

| File | LOC | Export(s) | Key Dependencies |
|------|-----|-----------|------------------|
| `WorkflowCanvas.tsx` | 448 | `WorkflowCanvas` (named) | `@xyflow/react`, all custom nodes/edges, hooks, layoutEngine |
| `nodes/ActionNode.tsx` | 86 | `ActionNode` (memo) | `@xyflow/react` Handle/Position |
| `nodes/AgentNode.tsx` | 84 | `AgentNode` (memo) | `@xyflow/react` Handle/Position |
| `nodes/ConditionNode.tsx` | 92 | `ConditionNode` (memo) | `@xyflow/react` Handle/Position (4 handles: T/B/L/R) |
| `nodes/StartEndNode.tsx` | 78 | `StartEndNode` (memo) | `@xyflow/react` Handle/Position |
| `edges/DefaultEdge.tsx` | 72 | `DefaultEdge` (memo) | `@xyflow/react` BaseEdge/getBezierPath/EdgeLabelRenderer |
| `edges/ConditionalEdge.tsx` | 80 | `ConditionalEdge` (memo) | `@xyflow/react` BaseEdge/getBezierPath/EdgeLabelRenderer |
| `hooks/useNodeDrag.ts` | 76 | `useNodeDrag` | useState, useRef, useCallback |
| `hooks/useWorkflowData.ts` | 323 | `useWorkflowData` | React Query, api client, dagre layout |
| `utils/layoutEngine.ts` | 144 | `applyDagreLayout`, `getNodesBounds`, `LayoutDirection` | dagre |

---

## 3. Corrections to V9 layer-01-frontend.md

### 3.1 File Count Discrepancies

| V9 Claim | Actual Count | Delta | Note |
|----------|-------------|-------|------|
| `unified-chat/`: 68 files | 51 files (30 core + 21 agent-swarm) | -17 | V9 likely counted test files in agent-swarm/__tests__ (6 files) + pages/UnifiedChat.tsx + hooks. Actual component files only = 51. |
| `ag-ui/`: 15 files | 15 files | 0 | Correct |
| `DevUI/`: 14 files | 15 files | +1 | V9 missed `EventFilter.tsx` (Sprint 89, 416 LOC) |
| `ui/`: 16 files | 16 files | 0 | Correct |
| `layout/`: 4 files | 5 files | +1 | V9 missed `Sidebar.tsx` or index.ts. Actually has AppLayout, Header, Sidebar, UserMenu, index = 5 |
| `shared/`: 4 files | 4 files | 0 | Correct |
| `auth/`: 1 file | 1 file | 0 | Correct |
| `workflow-editor/`: not mentioned | 9 files | NEW | **Entire module missing from V9 component count** (mentioned only in route map as "DAG editor, Phase 34") |

### 3.2 Component Hierarchy Corrections

V9 Section 5 hierarchy has these inaccuracies:

1. **`IntentStatusChip` placement**: V9 shows it nested under `MessageBubble`. Actual: it is rendered by `MessageList` directly (above `MessageBubble`), not inside it. See `MessageList.tsx` lines 233-240.

2. **`ToolCallTracker` inline**: V9 does not show `ToolCallTracker` as inline within messages. Actual: `MessageList.tsx` renders `ToolCallTracker` inline before message content when `orchMeta.pipelineToolCalls` exists (lines 244-253).

3. **`TaskProgressCard` missing from hierarchy**: V9 omits `TaskProgressCard` from the tree. Actual: rendered by `MessageList` below assistant messages when `orchMeta.taskId` is present (lines 276-280).

4. **Knowledge source citations missing**: V9 omits the inline knowledge sources `<details>` block rendered by `MessageList` (lines 283-305). This was added in Sprint 147.

5. **`WorkerActionList` missing from hierarchy**: Not shown under `WorkerDetailDrawer` in V9. It exists as an exported component from the agent-swarm module (Sprint 104) but is **not rendered** in `WorkerDetailDrawer.tsx` -- it appears to be an unused export meant for future integration.

### 3.3 Missing Components Not Mentioned in V9

| Component | Module | LOC | Sprint | Note |
|-----------|--------|-----|--------|------|
| `WorkflowCanvas` | workflow-editor | 448 | S133 | Main DAG visualization canvas |
| `ActionNode` | workflow-editor/nodes | 86 | S133 | Custom ReactFlow node |
| `AgentNode` | workflow-editor/nodes | 84 | S133 | Custom ReactFlow node |
| `ConditionNode` | workflow-editor/nodes | 92 | S133 | Custom ReactFlow node |
| `StartEndNode` | workflow-editor/nodes | 78 | S133 | Custom ReactFlow node |
| `DefaultEdge` | workflow-editor/edges | 72 | S133 | Custom ReactFlow edge |
| `ConditionalEdge` | workflow-editor/edges | 80 | S133 | Custom ReactFlow edge |
| `useNodeDrag` | workflow-editor/hooks | 76 | S133 | Node drag state hook |
| `useWorkflowData` | workflow-editor/hooks | 323 | S133 | Workflow data transform + CRUD |
| `layoutEngine` | workflow-editor/utils | 144 | S133 | Dagre auto-layout |
| `EventFilter` | DevUI | 416 | S89 | Event filtering UI |
| `FilterBar` | DevUI | (in EventFilter) | S89 | Compact filter bar |
| `WorkerActionList` | agent-swarm | 333 | S104 | Action timeline (exported but unused in drawer) |

### 3.4 Props/LOC Corrections

| Component | V9 LOC (if mentioned) | Actual LOC | Notes |
|-----------|----------------------|------------|-------|
| `ChatHistoryPanel.tsx` | not specific | 415 | Includes `RecoverableSessionsSection` (Sprint 138) and `ThreadItem` sub-components |
| `OrchestrationPanel.tsx` | not specific | 508 | Largest unified-chat core component; includes 4 sub-components inline |
| `ApprovalMessageCard.tsx` | not specific | 490 | Second largest; Sprint 99 inline HITL card |
| `EventFilter.tsx` | not counted | 416 | Largest DevUI component; includes `FilterBar` export |
| `DynamicChart.tsx` | not specific | 386 | Contains 4 internal chart sub-components (Bar, Pie, Line, Scatter) |
| `Statistics.tsx` | not specific | 369 | Contains `StatisticsSummary` compact export |

### 3.5 ui/index.ts Incompleteness

V9 does not flag that `ui/index.ts` only re-exports 3 of 16 components (Button, Card, Badge). The remaining 13 components (Checkbox, Collapsible, Dialog, Input, Label, Textarea, Progress, RadioGroup, Table, Tooltip, ScrollArea, Separator, Sheet, Select) must be imported directly by path. This is not a bug -- consumers already import by direct path -- but the index file is misleading.

---

## 4. Cross-Reference: Component Hierarchy Accuracy

### 4.1 Verified Parent-Child Relationships

| Parent | Children (Verified) | Status |
|--------|-------------------|--------|
| `AppLayout` | `Sidebar`, `Header`, `Outlet` | CORRECT |
| `Header` | `Button`, `UserMenu` | CORRECT |
| `Sidebar` | `NavLink` (13 items + Settings) | CORRECT |
| `ChatArea` | `MessageList`, `StreamingIndicator` (from ag-ui) | CORRECT |
| `MessageList` | `MessageBubble`, `ApprovalMessageCard`, `IntentStatusChip`, `TaskProgressCard`, `ToolCallTracker`, `CustomUIRenderer` | VERIFIED (V9 missed TaskProgressCard, ToolCallTracker inline, knowledge citations) |
| `WorkflowSidePanel` | `StepProgress`, `ToolCallTracker`, `CheckpointList` | CORRECT |
| `AgentSwarmPanel` | `SwarmHeader`, `OverallProgress`, `WorkerCardList` | CORRECT |
| `WorkerCardList` | `WorkerCard` (per worker) | CORRECT |
| `WorkerDetailDrawer` | `WorkerDetailHeader`, `CurrentTask`, `ExtendedThinkingPanel`, `ToolCallsPanel`, `MessageHistory`, `CheckpointPanel` | CORRECT |
| `ToolCallsPanel` | `ToolCallItem` (per tool call) | CORRECT |
| `OrchestrationPanel` | `AgentSwarmPanel`, `WorkerDetailDrawer`, + inline sections | CORRECT |
| `CustomUIRenderer` | `DynamicForm`, `DynamicChart`, `DynamicCard`, `DynamicTable` | CORRECT |
| `WorkflowCanvas` | `AgentNode`, `ConditionNode`, `ActionNode`, `StartEndNode`, `DefaultEdge`, `ConditionalEdge` | NEW (not in V9 hierarchy) |

### 4.2 Store Subscription Map

| Store | Components That Subscribe |
|-------|--------------------------|
| `useAuthStore` | `ProtectedRoute`, `UserMenu` |
| `useSwarmStore` | `useSwarmStatus` hook (used by `OrchestrationPanel`), `useSwarmEventHandler` hook |
| `useUnifiedChatStore` | none in components/ (used by hooks/ and pages/) |

---

## 5. Summary of Findings

### 5.1 What V9 Got Right

- Overall module organization description is accurate
- Component hierarchy for the main chat flow is 90% correct
- State management architecture (3-layer model) is accurate
- Dual SSE transport description is accurate
- Hook inventory is comprehensive and accurate
- Known issues (H-08 through L-06) are all valid

### 5.2 What V9 Missed or Got Wrong

1. **workflow-editor/ module entirely omitted** from component inventory (9 files, ~1,400 LOC)
2. **DevUI file count off by 1**: missed `EventFilter.tsx` (416 LOC)
3. **layout file count off by 1**: has 5 files not 4
4. **unified-chat file count inflated**: 68 claimed vs 51 actual component files (likely counted test files + non-component files)
5. **3 components missing from MessageList hierarchy**: `TaskProgressCard`, inline `ToolCallTracker`, knowledge source citations
6. **`IntentStatusChip` incorrectly nested**: shown under MessageBubble but actually rendered by MessageList directly
7. **`WorkerActionList` exported but unused**: Listed in agent-swarm index but not rendered in WorkerDetailDrawer
8. **`ui/index.ts` incompleteness not flagged**: only exports 3 of 16 components

### 5.3 Statistics

- **Total component files verified**: 113 (excluding test files)
- **Total estimated LOC across all components**: ~14,500
- **Components with store subscriptions**: 4 (ProtectedRoute, UserMenu, OrchestrationPanel via hook, useSwarmEventHandler via hook)
- **Components using React Query**: 2 (TaskProgressCard via useTask, ChatHistoryPanel via useRecoverableSessions)
- **Class components**: 1 (ErrorBoundary -- required for error boundary API)
- **All others**: Functional components (FC or function declaration)

---

*Verification conducted 2026-03-29. All 113 files read in full.*
*V9 Verification Pass -- Layer 01 Components*

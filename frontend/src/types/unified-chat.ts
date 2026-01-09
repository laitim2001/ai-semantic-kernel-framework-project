/**
 * Unified Chat Interface Types
 *
 * Sprint 62: Core Architecture & Adaptive Layout
 * Phase 16: Unified Agentic Chat Interface
 *
 * TypeScript type definitions for the unified chat window.
 * Integrates with AG-UI Protocol and Hybrid Architecture.
 */

import type {
  ChatMessage,
  ToolCallState,
  PendingApproval,
  RiskLevel,
  ToolDefinition,
} from './ag-ui';

// =============================================================================
// Execution Mode Types
// =============================================================================

/** Execution mode for the unified chat interface */
export type ExecutionMode = 'chat' | 'workflow';

/** Mode source - how the current mode was determined */
export type ModeSource = 'auto' | 'manual';

// =============================================================================
// Workflow Step Types
// =============================================================================

/** Workflow step status */
export type WorkflowStepStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped';

/** Workflow step definition */
export interface WorkflowStep {
  id: string;
  name: string;
  description?: string;
  status: WorkflowStepStatus;
  startedAt?: string;
  completedAt?: string;
  error?: string;
  metadata?: Record<string, unknown>;
}

/** Workflow state for tracking progress */
export interface WorkflowState {
  workflowId: string;
  steps: WorkflowStep[];
  currentStepIndex: number;
  totalSteps: number;
  progress: number; // 0-100
  status: 'pending' | 'running' | 'completed' | 'failed' | 'paused';
  startedAt?: string;
  completedAt?: string;
}

// =============================================================================
// Tool Tracking Types
// =============================================================================

/** Extended tool call with timing info */
export interface TrackedToolCall extends ToolCallState {
  duration?: number; // milliseconds
  queuedAt?: string;
}

// =============================================================================
// Checkpoint Types
// =============================================================================

/** Checkpoint for state recovery */
export interface Checkpoint {
  id: string;
  timestamp: string;
  label?: string;
  canRestore: boolean;
  stepIndex?: number;
  metadata?: Record<string, unknown>;
}

// =============================================================================
// Execution Metrics Types
// =============================================================================

/** Token usage tracking */
export interface TokenUsage {
  used: number;
  limit: number;
  percentage: number;
}

/** Execution time tracking */
export interface ExecutionTime {
  total: number; // milliseconds
  isRunning: boolean;
  startedAt?: string;
}

/** Tool call statistics (Sprint 65 enhancement) */
export interface ToolCallStatistics {
  total: number;
  completed: number;
  failed: number;
  pending: number;
}

/** Message statistics by role (Sprint 65 enhancement) */
export interface MessageStatistics {
  total: number;
  user: number;
  assistant: number;
  tool: number;
}

/** Combined execution metrics */
export interface ExecutionMetrics {
  tokens: TokenUsage;
  time: ExecutionTime;
  toolCallCount: number;
  messageCount: number;
  /** Sprint 65: Enhanced tool statistics */
  toolStats?: ToolCallStatistics;
  /** Sprint 65: Enhanced message statistics */
  messageStats?: MessageStatistics;
}

// =============================================================================
// Status Bar Types
// =============================================================================

/** Connection status for SSE */
export type ConnectionStatus = 'connected' | 'connecting' | 'disconnected' | 'error';

/** Status bar display state */
export interface StatusBarState {
  mode: ExecutionMode;
  modeSource: ModeSource;
  riskLevel: RiskLevel;
  riskScore: number;
  connection: ConnectionStatus;
  metrics: ExecutionMetrics;
  hasCheckpoint: boolean;
  canRestore: boolean;
}

// =============================================================================
// Chat Header Types
// =============================================================================

/** Mode toggle button state */
export interface ModeToggleState {
  currentMode: ExecutionMode;
  autoMode: ExecutionMode;
  manualOverride: ExecutionMode | null;
  isManuallyOverridden: boolean;
}

// =============================================================================
// Chat Input Types
// =============================================================================

/** Chat input state */
export interface ChatInputState {
  value: string;
  isSubmitting: boolean;
  canSubmit: boolean;
  placeholder: string;
}

/** File attachment (legacy - for compatibility) */
export interface FileAttachment {
  id: string;
  name: string;
  type: string;
  size: number;
  url?: string;
  uploading?: boolean;
}

/**
 * Attachment status for upload tracking
 * Sprint 75: File Upload Feature
 */
export type AttachmentStatus = 'pending' | 'uploading' | 'uploaded' | 'error';

/**
 * Attachment with upload status and file reference
 * Sprint 75: File Upload Feature
 */
export interface Attachment {
  id: string;
  file: File;
  preview?: string;  // For images
  status: AttachmentStatus;
  progress?: number;
  error?: string;
  serverFileId?: string;  // ID from server after upload
}

// =============================================================================
// Approval Flow Types
// =============================================================================

/** Approval action type */
export type ApprovalAction = 'approve' | 'reject' | 'defer';

/** Approval flow state */
export interface ApprovalFlowState {
  pendingApprovals: PendingApproval[];
  dialogApproval: PendingApproval | null;
  isProcessing: boolean;
}

// =============================================================================
// Unified Chat Store Types
// =============================================================================

/** Main unified chat state */
export interface UnifiedChatState {
  // Core state
  threadId: string;
  sessionId: string;

  // Mode management
  mode: ExecutionMode;
  autoMode: ExecutionMode;
  manualOverride: ExecutionMode | null;

  // Messages and conversation
  messages: ChatMessage[];
  isStreaming: boolean;
  streamingMessageId: string | null;

  // Workflow tracking (Workflow mode only)
  workflowState: WorkflowState | null;

  // Tool calls
  toolCalls: TrackedToolCall[];

  // Approvals
  pendingApprovals: PendingApproval[];
  dialogApproval: PendingApproval | null;

  // Checkpoints
  checkpoints: Checkpoint[];
  currentCheckpoint: string | null;

  // Metrics
  metrics: ExecutionMetrics;

  // Connection
  connection: ConnectionStatus;

  // Error state
  error: string | null;
}

/** Unified chat store actions */
export interface UnifiedChatActions {
  // Mode management
  setMode: (mode: ExecutionMode) => void;
  setManualOverride: (mode: ExecutionMode | null) => void;
  setAutoMode: (mode: ExecutionMode) => void;

  // Messages
  addMessage: (message: ChatMessage) => void;
  updateMessage: (id: string, content: Partial<ChatMessage>) => void;
  setMessages: (messages: ChatMessage[]) => void;  // S71: Bulk set messages (for history loading)
  setStreaming: (isStreaming: boolean, messageId?: string) => void;
  clearMessages: () => void;

  // Workflow
  setWorkflowState: (state: WorkflowState | null) => void;
  updateWorkflowStep: (stepId: string, status: WorkflowStepStatus) => void;

  // Tool calls
  addToolCall: (toolCall: TrackedToolCall) => void;
  updateToolCall: (id: string, update: Partial<TrackedToolCall>) => void;

  // Approvals
  addPendingApproval: (approval: PendingApproval) => void;
  removePendingApproval: (approvalId: string) => void;
  setDialogApproval: (approval: PendingApproval | null) => void;

  // Checkpoints
  addCheckpoint: (checkpoint: Checkpoint) => void;
  setCurrentCheckpoint: (id: string | null) => void;

  // Metrics
  updateMetrics: (metrics: Partial<ExecutionMetrics>) => void;

  // Connection
  setConnection: (status: ConnectionStatus) => void;

  // Error
  setError: (error: string | null) => void;

  // Reset
  reset: () => void;

  // S63-4: Persistence management
  clearPersistence: () => void;
}

// =============================================================================
// Component Props Types
// =============================================================================

/** UnifiedChat page props */
export interface UnifiedChatProps {
  initialThreadId?: string;
  initialSessionId?: string;
  tools?: ToolDefinition[];
  apiUrl?: string;
}

/** ChatHeader props */
export interface ChatHeaderProps {
  title?: string;
  currentMode: ExecutionMode;
  autoMode: ExecutionMode;
  isManuallyOverridden: boolean;
  connection: ConnectionStatus;
  onModeChange: (mode: ExecutionMode) => void;
  onSettingsClick?: () => void;
  /** Sprint 65: Reconnection support */
  onReconnect?: () => void;
  /** Sprint 65: Current retry count */
  retryCount?: number;
  /** Sprint 65: Max retry attempts */
  maxRetries?: number;
  /** Sprint 65: Error message if connection failed */
  connectionError?: string;
}

/** ChatArea props */
export interface ChatAreaProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  streamingMessageId?: string | null;
  pendingApprovals: PendingApproval[];
  onApprove: (toolCallId: string) => void;
  onReject: (toolCallId: string, reason?: string) => void;
  /** Sprint 76: Callback when file download is triggered */
  onDownload?: (fileId: string) => Promise<void>;
}

/** WorkflowSidePanel props */
export interface WorkflowSidePanelProps {
  workflowState: WorkflowState | null;
  toolCalls: TrackedToolCall[];
  checkpoints: Checkpoint[];
  onRestoreCheckpoint: (checkpointId: string) => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

/** ChatInput props */
export interface ChatInputProps {
  onSend: (content: string, fileIds?: string[]) => void;
  disabled?: boolean;
  isStreaming?: boolean;
  onCancel?: () => void;
  placeholder?: string;
  /** Sprint 75: Attachments with upload status */
  attachments?: Attachment[];
  onAttach?: (files: File[]) => void;
  onRemoveAttachment?: (id: string) => void;
  /** Legacy: FileAttachment support (deprecated) */
  legacyAttachments?: FileAttachment[];
}

/** Heartbeat state for long-running operations (S67-BF-1) */
export interface HeartbeatState {
  count: number;
  elapsedSeconds: number;
  message: string;
  status: 'processing' | 'idle';
}

/** StatusBar props */
export interface StatusBarProps {
  mode: ExecutionMode;
  modeSource: ModeSource;
  riskLevel: RiskLevel;
  riskScore?: number;
  metrics: ExecutionMetrics;
  hasCheckpoint: boolean;
  canRestore: boolean;
  onRestore?: () => void;
  heartbeat?: HeartbeatState | null;  // S67-BF-1
}

/** InlineApproval props */
export interface InlineApprovalProps {
  approval: PendingApproval;
  onApprove: () => void;
  onReject: (reason?: string) => void;
  compact?: boolean;
}

/** StepProgress props */
export interface StepProgressProps {
  steps: WorkflowStep[];
  currentStep: number;
  totalSteps: number;
}

// =============================================================================
// Enhanced Step Progress Types (Sprint 69)
// =============================================================================

/** Sub-step status for hierarchical progress */
export type SubStepStatusType = 'pending' | 'running' | 'completed' | 'failed' | 'skipped';

/** Sub-step within a main step */
export interface SubStep {
  id: string;
  name: string;
  status: SubStepStatusType;
  progress?: number;
  message?: string;
  startedAt?: string;
  completedAt?: string;
}

/** Step progress event from backend */
export interface StepProgressEvent {
  stepId: string;
  stepName: string;
  current: number;
  total: number;
  progress: number;
  status: SubStepStatusType;
  substeps: SubStep[];
  metadata?: Record<string, unknown>;
}

/** Step progress state for tracking multiple steps */
export interface StepProgressState {
  steps: Map<string, StepProgressEvent>;
  currentStep: string | null;
}

/** StepProgressEnhanced props */
export interface StepProgressEnhancedProps {
  step: StepProgressEvent;
  isExpanded?: boolean;
  onToggle?: () => void;
  showSubsteps?: boolean;
}

/** ToolCallTracker props */
export interface ToolCallTrackerProps {
  toolCalls: TrackedToolCall[];
  maxVisible?: number;
  showTimings?: boolean;
}

/** CheckpointList props */
export interface CheckpointListProps {
  checkpoints: Checkpoint[];
  currentCheckpoint?: string | null;
  onRestore: (checkpointId: string) => void;
  maxVisible?: number;
}

// =============================================================================
// Hook Return Types
// =============================================================================

/** useHybridMode hook return type */
export interface UseHybridModeReturn {
  currentMode: ExecutionMode;
  autoMode: ExecutionMode;
  manualOverride: ExecutionMode | null;
  isManuallyOverridden: boolean;
  setManualOverride: (mode: ExecutionMode | null) => void;
}

/** useApprovalFlow hook return type */
export interface UseApprovalFlowReturn {
  pendingApprovals: PendingApproval[];
  dialogApproval: PendingApproval | null;
  isProcessing: boolean;
  approveToolCall: (approvalId: string) => Promise<void>;
  rejectToolCall: (approvalId: string, reason?: string) => Promise<void>;
  closeDialog: () => void;
}

/** useExecutionMetrics hook return type */
export interface UseExecutionMetricsReturn {
  metrics: ExecutionMetrics;
  startTimer: () => void;
  stopTimer: () => void;
  resetMetrics: () => void;
  updateTokens: (used: number, limit: number) => void;
}

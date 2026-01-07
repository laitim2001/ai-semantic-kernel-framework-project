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

/** Combined execution metrics */
export interface ExecutionMetrics {
  tokens: TokenUsage;
  time: ExecutionTime;
  toolCallCount: number;
  messageCount: number;
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

/** File attachment (future support) */
export interface FileAttachment {
  id: string;
  name: string;
  type: string;
  size: number;
  url?: string;
  uploading?: boolean;
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
}

/** ChatArea props */
export interface ChatAreaProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  streamingMessageId?: string | null;
  pendingApprovals: PendingApproval[];
  onApprove: (toolCallId: string) => void;
  onReject: (toolCallId: string, reason?: string) => void;
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
  onSend: (content: string) => void;
  disabled?: boolean;
  isStreaming?: boolean;
  onCancel?: () => void;
  placeholder?: string;
  attachments?: FileAttachment[];
  onAttach?: (files: File[]) => void;
  onRemoveAttachment?: (id: string) => void;
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

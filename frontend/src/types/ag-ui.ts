/**
 * AG-UI Protocol Types
 *
 * Sprint 60: AG-UI Advanced Features
 * S60-1: Tool-based Generative UI
 * S60-2: Shared State
 * S60-3: Predictive State Updates
 *
 * TypeScript type definitions matching backend AG-UI protocol implementation.
 */

// =============================================================================
// S60-1: Tool-based Generative UI Types
// =============================================================================

/** UI Component Type - matches backend UIComponentType */
export type UIComponentType = 'form' | 'chart' | 'card' | 'table' | 'custom';

/** Chart Type - matches backend ChartType */
export type ChartType = 'line' | 'bar' | 'pie' | 'area' | 'scatter' | 'doughnut';

/** Form Field Type - matches backend FormFieldType */
export type FormFieldType =
  | 'text'
  | 'number'
  | 'email'
  | 'password'
  | 'textarea'
  | 'select'
  | 'checkbox'
  | 'radio'
  | 'date'
  | 'datetime'
  | 'file';

/** Form Field Definition */
export interface FormFieldDefinition {
  name: string;
  label: string;
  fieldType: FormFieldType;
  required: boolean;
  placeholder?: string;
  defaultValue?: unknown;
  options?: Array<{ label: string; value: string }>;
  validation?: Record<string, unknown>;
}

/** Table Column Definition */
export interface TableColumnDefinition {
  key: string;
  header: string;
  sortable: boolean;
  filterable: boolean;
  width?: string;
  align?: 'left' | 'center' | 'right';
  format?: string;
}

/** Chart Data Point */
export interface ChartDataPoint {
  label: string;
  value: number;
  color?: string;
}

/** Chart Dataset */
export interface ChartDataset {
  label: string;
  data: number[];
  backgroundColor?: string | string[];
  borderColor?: string;
}

/** Chart Data */
export interface ChartData {
  labels: string[];
  datasets: ChartDataset[];
}

/** Card Action */
export interface CardAction {
  label: string;
  action: string;
  variant?: 'default' | 'outline' | 'destructive';
}

/** UI Component Schema - type-specific props */
export interface UIComponentSchema {
  // Form schema
  fields?: FormFieldDefinition[];
  submitLabel?: string;
  cancelLabel?: string;

  // Chart schema
  chartType?: ChartType;
  data?: ChartData;
  options?: Record<string, unknown>;

  // Card schema
  title?: string;
  subtitle?: string;
  content?: string;
  imageUrl?: string;
  actions?: CardAction[];

  // Table schema
  columns?: TableColumnDefinition[];
  rows?: Record<string, unknown>[];
  pagination?: boolean;
  pageSize?: number;

  // Custom schema
  customType?: string;
  customProps?: Record<string, unknown>;
}

/** UI Component Definition - matches backend UIComponentDefinition.to_dict() */
export interface UIComponentDefinition {
  componentId: string;
  componentType: UIComponentType;
  props: UIComponentSchema;
  title?: string;
  description?: string;
  createdAt: string;
}

/** UI Component Event - emitted when user interacts with component */
export interface UIComponentEvent {
  componentId: string;
  eventType: 'submit' | 'click' | 'change' | 'select';
  data: Record<string, unknown>;
  timestamp: string;
}

// =============================================================================
// S60-2: Shared State Types
// =============================================================================

/** Diff Operation - matches backend DiffOperation */
export type DiffOperation = 'add' | 'remove' | 'replace' | 'move';

/** Conflict Resolution Strategy - matches backend ConflictResolutionStrategy */
export type ConflictResolutionStrategy =
  | 'server_wins'
  | 'client_wins'
  | 'last_write_wins'
  | 'merge'
  | 'manual';

/** State Diff - represents a single state change */
export interface StateDiff {
  path: string;
  operation: DiffOperation;
  oldValue?: unknown;
  newValue?: unknown;
}

/** State Version - tracks state versioning */
export interface StateVersion {
  version: number;
  timestamp: string;
  source: 'client' | 'server';
  hash?: string;
}

/** State Conflict - represents a conflict between client and server */
export interface StateConflict {
  path: string;
  clientValue: unknown;
  serverValue: unknown;
  resolvedValue?: unknown;
  strategy: ConflictResolutionStrategy;
}

/** Shared State - complete state object with metadata */
export interface SharedState {
  sessionId: string;
  state: Record<string, unknown>;
  version: StateVersion;
  lastSync: string;
  pendingDiffs: StateDiff[];
  conflicts: StateConflict[];
}

/** State Sync Status */
export type StateSyncStatus = 'synced' | 'syncing' | 'pending' | 'conflict' | 'error';

/** State Sync Event - SSE event for state sync */
export interface StateSyncEvent {
  type: 'snapshot' | 'delta' | 'conflict' | 'ack';
  sessionId: string;
  version: number;
  data: unknown;
  timestamp: string;
}

// =============================================================================
// S60-3: Predictive State Updates Types
// =============================================================================

/** Prediction Status - matches backend PredictionStatus */
export type PredictionStatus =
  | 'pending'
  | 'confirmed'
  | 'rolled_back'
  | 'expired'
  | 'conflicted';

/** Prediction Type - matches backend PredictionType */
export type PredictionType = 'optimistic' | 'speculative' | 'prefetch';

/** Prediction Result - matches backend PredictionResult */
export interface PredictionResult {
  predictionId: string;
  predictionType: PredictionType;
  status: PredictionStatus;
  predictedState: Record<string, unknown>;
  originalState: Record<string, unknown>;
  confidence: number;
  expiresAt?: string;
  confirmedAt?: string;
  rolledBackAt?: string;
  conflictReason?: string;
}

/** Prediction Config - matches backend PredictionConfig */
export interface PredictionConfig {
  enabled: boolean;
  defaultTimeout: number;
  maxPendingPredictions: number;
  autoRollbackOnConflict: boolean;
  confidenceThreshold: number;
}

/** Optimistic Update Request */
export interface OptimisticUpdateRequest {
  path: string;
  operation: DiffOperation;
  value: unknown;
  predictionType?: PredictionType;
  timeout?: number;
}

/** Optimistic State - state with pending predictions */
export interface OptimisticState<T = Record<string, unknown>> {
  currentState: T;
  pendingPredictions: PredictionResult[];
  optimisticState: T;
  isOptimistic: boolean;
}

// =============================================================================
// AG-UI Event Types (from backend events/state.py)
// =============================================================================

/** AG-UI Event Type */
export type AGUIEventType =
  | 'TEXT_MESSAGE_START'
  | 'TEXT_MESSAGE_CONTENT'
  | 'TEXT_MESSAGE_END'
  | 'TOOL_CALL_START'
  | 'TOOL_CALL_ARGS'
  | 'TOOL_CALL_END'
  | 'STATE_SNAPSHOT'
  | 'STATE_DELTA'
  | 'MESSAGES_SNAPSHOT'
  | 'RAW'
  | 'CUSTOM'
  | 'RUN_STARTED'
  | 'RUN_FINISHED'
  | 'RUN_ERROR'
  | 'STEP_STARTED'
  | 'STEP_FINISHED';

/** Base AG-UI Event */
export interface BaseAGUIEvent {
  type: AGUIEventType;
  timestamp: string;
}

/** State Snapshot Event */
export interface StateSnapshotEvent extends BaseAGUIEvent {
  type: 'STATE_SNAPSHOT';
  snapshot: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

/** State Delta Item */
export interface StateDeltaItem {
  path: string;
  operation: 'set' | 'delete' | 'append' | 'increment';
  value?: unknown;
}

/** State Delta Event */
export interface StateDeltaEvent extends BaseAGUIEvent {
  type: 'STATE_DELTA';
  delta: StateDeltaItem[];
}

/** Custom Event */
export interface CustomEvent extends BaseAGUIEvent {
  type: 'CUSTOM';
  eventName: string;
  payload: Record<string, unknown>;
}

// =============================================================================
// useAGUI Hook Types (Sprint 60+)
// =============================================================================

/** Message Role */
export type MessageRole = 'user' | 'assistant' | 'system' | 'tool';

/** Generated File - Sprint 76 */
export interface GeneratedFile {
  id: string;
  name: string;
  size: number;
  mimeType: string;
  createdAt: string;
  downloadUrl?: string;
}

/** Chat Message */
export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  toolCalls?: ToolCallState[];
  metadata?: Record<string, unknown>;
  /** Sprint 65: S65-5 - Custom UI component to render instead of text */
  customUI?: UIComponentDefinition;
  /** Sprint 76: Files generated by Claude SDK */
  files?: GeneratedFile[];
}

/** Tool Call Status */
export type ToolCallStatus =
  | 'pending'
  | 'executing'
  | 'completed'
  | 'failed'
  | 'requires_approval'
  | 'approved'
  | 'rejected';

/** Tool Call State */
export interface ToolCallState {
  id: string;
  toolCallId: string;
  name: string;
  arguments: Record<string, unknown>;
  status: ToolCallStatus;
  result?: unknown;
  error?: string;
  startedAt?: string;
  completedAt?: string;
}

/** Risk Level */
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

/** Pending Approval */
/** Approval Status */
export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'expired';

export interface PendingApproval {
  approvalId: string;
  toolCallId: string;
  toolName: string;
  arguments: Record<string, unknown>;
  riskLevel: RiskLevel;
  riskScore: number;
  reasoning: string;
  runId?: string;
  sessionId?: string;
  createdAt: string;
  expiresAt: string;
  /** Approval status - defaults to 'pending' */
  status?: ApprovalStatus;
  /** Timestamp when resolved (approved/rejected/expired) */
  resolvedAt?: string;
  /** User's rejection reason if rejected */
  rejectReason?: string;
}

/** Tool Definition */
export interface ToolDefinition {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
}

/** Run Agent Input */
export interface RunAgentInput {
  prompt?: string;
  threadId: string;
  runId?: string;
  sessionId?: string;
  mode?: 'auto' | 'workflow' | 'chat' | 'hybrid';
  tools?: ToolDefinition[];
  maxTokens?: number;
  timeout?: number;
  metadata?: Record<string, unknown>;
}

/** SSE Connection Status */
export type SSEConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

/** Run Status */
export type RunStatus = 'idle' | 'running' | 'completed' | 'error' | 'cancelled';

/** AG-UI Run State */
export interface AGUIRunState {
  runId: string | null;
  status: RunStatus;
  error?: string;
  startedAt?: string;
  finishedAt?: string;
}

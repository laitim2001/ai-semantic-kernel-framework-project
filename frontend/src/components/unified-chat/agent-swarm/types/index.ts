/**
 * Swarm Types - Index
 *
 * Export all swarm-related types for UI components.
 * Sprint 101: Event types (snake_case for SSE)
 * Sprint 102: Component types (camelCase for UI)
 */

// Re-export event types for SSE handling
export * from './events';

// =============================================================================
// Basic Types (for UI components)
// =============================================================================

export type WorkerType = 'claude_sdk' | 'maf' | 'hybrid' | 'research' | 'custom';
export type WorkerStatus = 'pending' | 'running' | 'paused' | 'completed' | 'failed';
export type SwarmMode = 'sequential' | 'parallel' | 'pipeline' | 'hierarchical' | 'hybrid';
export type SwarmStatus = 'initializing' | 'executing' | 'aggregating' | 'completed' | 'failed';

// =============================================================================
// Tool Call (for WorkerDetail)
// =============================================================================

export interface ToolCallInfo {
  toolCallId: string;
  toolName: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  inputArgs: Record<string, unknown>;
  outputResult?: Record<string, unknown>;
  error?: string;
  startedAt?: string;
  completedAt?: string;
  durationMs?: number;
}

// =============================================================================
// Thinking Content (for WorkerDetail)
// =============================================================================

export interface ThinkingContent {
  content: string;
  timestamp: string;
  tokenCount?: number;
}

// =============================================================================
// Worker Message (for WorkerDetail)
// =============================================================================

export interface WorkerMessage {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string;
  timestamp: string;
  toolCallId?: string;
}

// =============================================================================
// Worker Summary (for WorkerCard display)
// =============================================================================

export interface UIWorkerSummary {
  workerId: string;
  workerName: string;
  workerType: WorkerType;
  role: string;
  status: WorkerStatus;
  progress: number;
  currentAction?: string;
  toolCallsCount: number;
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
}

// =============================================================================
// Worker Detail (for Drawer display)
// =============================================================================

export interface WorkerDetail extends UIWorkerSummary {
  taskId: string;
  taskDescription: string;
  thinkingHistory: ThinkingContent[];
  toolCalls: ToolCallInfo[];
  messages: WorkerMessage[];
  result?: Record<string, unknown>;
  error?: string;
  checkpointId?: string;
  checkpointBackend?: string;
}

// =============================================================================
// Agent Swarm Status (for AgentSwarmPanel)
// =============================================================================

export interface UIAgentSwarmStatus {
  swarmId: string;
  sessionId: string;
  mode: SwarmMode;
  status: SwarmStatus;
  totalWorkers: number;
  overallProgress: number;
  workers: UIWorkerSummary[];
  createdAt: string;
  startedAt?: string;
  estimatedCompletion?: string;
  completedAt?: string;
  metadata: Record<string, unknown>;
}

// =============================================================================
// Component Props
// =============================================================================

export interface AgentSwarmPanelProps {
  swarmStatus: UIAgentSwarmStatus | null;
  onWorkerClick?: (worker: UIWorkerSummary) => void;
  isLoading?: boolean;
  className?: string;
}

export interface SwarmHeaderProps {
  mode: SwarmMode;
  status: SwarmStatus;
  totalWorkers: number;
  startedAt?: string;
}

export interface OverallProgressProps {
  progress: number;
  status: SwarmStatus;
  animated?: boolean;
}

export interface WorkerCardProps {
  worker: UIWorkerSummary;
  index: number;
  isSelected?: boolean;
  onClick?: () => void;
}

export interface WorkerCardListProps {
  workers: UIWorkerSummary[];
  selectedWorkerId?: string;
  onWorkerClick?: (worker: UIWorkerSummary) => void;
}

export interface SwarmStatusBadgesProps {
  workers: UIWorkerSummary[];
  onWorkerClick?: (worker: UIWorkerSummary) => void;
}

// =============================================================================
// Utility Types
// =============================================================================

/**
 * Convert snake_case event payload to camelCase UI format
 */
export type SnakeToCamelCase<S extends string> = S extends `${infer T}_${infer U}`
  ? `${T}${Capitalize<SnakeToCamelCase<U>>}`
  : S;

/**
 * Status configuration for UI
 */
export interface StatusConfig {
  color: string;
  bgColor: string;
  label: string;
}

/**
 * Worker type configuration for UI
 */
export interface WorkerTypeConfig {
  label: string;
  iconName: string;
}

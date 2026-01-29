/**
 * Swarm Event Types
 *
 * TypeScript definitions for Swarm SSE events.
 * Sprint 101: Swarm Event System + SSE Integration
 */

// =============================================================================
// Swarm Event Names
// =============================================================================

export const SwarmEventNames = {
  // Swarm lifecycle events
  SWARM_CREATED: 'swarm_created',
  SWARM_STATUS_UPDATE: 'swarm_status_update',
  SWARM_COMPLETED: 'swarm_completed',

  // Worker lifecycle events
  WORKER_STARTED: 'worker_started',
  WORKER_PROGRESS: 'worker_progress',
  WORKER_THINKING: 'worker_thinking',
  WORKER_TOOL_CALL: 'worker_tool_call',
  WORKER_MESSAGE: 'worker_message',
  WORKER_COMPLETED: 'worker_completed',
} as const;

export type SwarmEventName = (typeof SwarmEventNames)[keyof typeof SwarmEventNames];

// =============================================================================
// Swarm Lifecycle Event Payloads
// =============================================================================

/**
 * Worker summary in swarm events
 */
export interface WorkerSummary {
  worker_id: string;
  worker_name: string;
  worker_type: string;
  role: string;
  status?: string;
  progress?: number;
  current_action?: string | null;
  tool_calls_count?: number;
}

/**
 * Swarm created event payload
 */
export interface SwarmCreatedPayload {
  swarm_id: string;
  session_id: string;
  mode: 'sequential' | 'parallel' | 'hierarchical';
  workers: WorkerSummary[];
  created_at: string;
}

/**
 * Swarm status update event payload (full snapshot)
 */
export interface SwarmStatusUpdatePayload {
  swarm_id: string;
  session_id: string;
  mode: 'sequential' | 'parallel' | 'hierarchical';
  status: 'initializing' | 'running' | 'paused' | 'completed' | 'failed';
  total_workers: number;
  overall_progress: number;
  workers: WorkerSummary[];
  metadata: Record<string, unknown>;
}

/**
 * Swarm completed event payload
 */
export interface SwarmCompletedPayload {
  swarm_id: string;
  status: 'completed' | 'failed';
  summary?: string | null;
  total_duration_ms: number;
  completed_at: string;
}

// =============================================================================
// Worker Lifecycle Event Payloads
// =============================================================================

/**
 * Worker started event payload
 */
export interface WorkerStartedPayload {
  swarm_id: string;
  worker_id: string;
  worker_name: string;
  worker_type: string;
  role: string;
  task_description: string;
  started_at: string;
}

/**
 * Worker progress event payload
 */
export interface WorkerProgressPayload {
  swarm_id: string;
  worker_id: string;
  progress: number;
  current_action?: string | null;
  status: string;
  updated_at: string;
}

/**
 * Worker thinking event payload
 */
export interface WorkerThinkingPayload {
  swarm_id: string;
  worker_id: string;
  thinking_content: string;
  token_count?: number | null;
  timestamp: string;
}

/**
 * Worker tool call event payload
 */
export interface WorkerToolCallPayload {
  swarm_id: string;
  worker_id: string;
  tool_call_id: string;
  tool_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  input_args: Record<string, unknown>;
  output_result?: Record<string, unknown> | null;
  error?: string | null;
  duration_ms?: number | null;
  timestamp: string;
}

/**
 * Worker message event payload
 */
export interface WorkerMessagePayload {
  swarm_id: string;
  worker_id: string;
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string;
  tool_call_id?: string | null;
  timestamp: string;
}

/**
 * Worker completed event payload
 */
export interface WorkerCompletedPayload {
  swarm_id: string;
  worker_id: string;
  status: 'completed' | 'failed';
  result?: Record<string, unknown> | null;
  error?: string | null;
  duration_ms: number;
  completed_at: string;
}

// =============================================================================
// Event Union Types
// =============================================================================

/**
 * All swarm event payloads
 */
export type SwarmEventPayload =
  | SwarmCreatedPayload
  | SwarmStatusUpdatePayload
  | SwarmCompletedPayload
  | WorkerStartedPayload
  | WorkerProgressPayload
  | WorkerThinkingPayload
  | WorkerToolCallPayload
  | WorkerMessagePayload
  | WorkerCompletedPayload;

/**
 * Swarm SSE event structure (from AG-UI CustomEvent)
 */
export interface SwarmSSEEvent {
  type: 'CUSTOM';
  event_name: SwarmEventName;
  payload: SwarmEventPayload;
  timestamp: string;
}

// =============================================================================
// Event Handlers Interface
// =============================================================================

/**
 * Event handlers for swarm events
 */
export interface SwarmEventHandlers {
  onSwarmCreated?: (payload: SwarmCreatedPayload) => void;
  onSwarmStatusUpdate?: (payload: SwarmStatusUpdatePayload) => void;
  onSwarmCompleted?: (payload: SwarmCompletedPayload) => void;
  onWorkerStarted?: (payload: WorkerStartedPayload) => void;
  onWorkerProgress?: (payload: WorkerProgressPayload) => void;
  onWorkerThinking?: (payload: WorkerThinkingPayload) => void;
  onWorkerToolCall?: (payload: WorkerToolCallPayload) => void;
  onWorkerMessage?: (payload: WorkerMessagePayload) => void;
  onWorkerCompleted?: (payload: WorkerCompletedPayload) => void;
  onError?: (error: Error) => void;
}

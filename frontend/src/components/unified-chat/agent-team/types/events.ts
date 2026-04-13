/**
 * Team Event Types
 *
 * TypeScript definitions for Agent Team SSE events.
 * Sprint 101: Agent Team Event System + SSE Integration
 */

// =============================================================================
// Team Event Names
// =============================================================================

export const SwarmEventNames = {
  // Team lifecycle events
  SWARM_CREATED: 'team_created',
  SWARM_STATUS_UPDATE: 'team_status_update',
  SWARM_COMPLETED: 'team_completed',

  // Agent lifecycle events
  WORKER_STARTED: 'agent_started',
  WORKER_PROGRESS: 'agent_progress',
  WORKER_THINKING: 'agent_thinking',
  WORKER_TOOL_CALL: 'agent_tool_call',
  WORKER_MESSAGE: 'agent_message',
  WORKER_COMPLETED: 'agent_completed',
} as const;

export type SwarmEventName = (typeof SwarmEventNames)[keyof typeof SwarmEventNames];

// =============================================================================
// Team Lifecycle Event Payloads
// =============================================================================

/**
 * Agent summary in team events
 */
export interface WorkerSummary {
  agent_id: string;
  agent_name: string;
  agent_type: string;
  role: string;
  status?: string;
  progress?: number;
  current_action?: string | null;
  tool_calls_count?: number;
}

/**
 * Team created event payload
 */
export interface TeamCreatedPayload {
  team_id: string;
  session_id: string;
  mode: 'sequential' | 'parallel' | 'hierarchical';
  agents: WorkerSummary[];
  created_at: string;
}

/**
 * Team status update event payload (full snapshot)
 */
export interface TeamStatusUpdatePayload {
  team_id: string;
  session_id: string;
  mode: 'sequential' | 'parallel' | 'hierarchical';
  status: 'initializing' | 'running' | 'paused' | 'completed' | 'failed';
  total_agents: number;
  overall_progress: number;
  agents: WorkerSummary[];
  metadata: Record<string, unknown>;
}

/**
 * Team completed event payload
 */
export interface TeamCompletedPayload {
  team_id: string;
  status: 'completed' | 'failed';
  summary?: string | null;
  total_duration_ms: number;
  completed_at: string;
}

// =============================================================================
// Agent Lifecycle Event Payloads
// =============================================================================

/**
 * Agent started event payload
 */
export interface AgentStartedPayload {
  team_id: string;
  agent_id: string;
  agent_name: string;
  agent_type: string;
  role: string;
  task_description: string;
  started_at: string;
}

/**
 * Agent progress event payload
 */
export interface AgentProgressPayload {
  team_id: string;
  agent_id: string;
  progress: number;
  current_action?: string | null;
  status: string;
  updated_at: string;
}

/**
 * Agent thinking event payload
 */
export interface AgentThinkingPayload {
  team_id: string;
  agent_id: string;
  thinking_content: string;
  token_count?: number | null;
  timestamp: string;
}

/**
 * Agent tool call event payload
 */
export interface AgentToolCallPayload {
  team_id: string;
  agent_id: string;
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
 * Agent message event payload
 */
export interface AgentMessagePayload {
  team_id: string;
  agent_id: string;
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string;
  tool_call_id?: string | null;
  timestamp: string;
}

/**
 * Agent completed event payload
 */
export interface AgentCompletedPayload {
  team_id: string;
  agent_id: string;
  status: 'completed' | 'failed';
  result?: Record<string, unknown> | null;
  error?: string | null;
  duration_ms: number;
  completed_at: string;
}

// =============================================================================
// Inter-Agent Communication Event Payloads (Phase 45: Sprint D)
// =============================================================================

/**
 * Team message event payload — agent-to-agent communication
 */
export interface TeamMessagePayload {
  team_id: string;
  from_agent: string;
  to_agent?: string | null;
  content: string;
  directed: boolean;
}

/**
 * Inbox received event payload — agent received a directed message
 */
export interface InboxReceivedPayload {
  team_id: string;
  agent_id: string;
  from_agent: string;
  content: string;
}

/**
 * Per-tool HITL approval required — agent waiting for human decision
 */
export interface AgentApprovalRequiredPayload {
  team_id: string;
  approval_id: string;
  agent_name: string;
  tool_name: string;
  risk_level: string;
  message: string;
  arguments?: Record<string, unknown>;
}

// =============================================================================
// Event Union Types
// =============================================================================

/**
 * All team event payloads
 */
export type SwarmEventPayload =
  | TeamCreatedPayload
  | TeamStatusUpdatePayload
  | TeamCompletedPayload
  | AgentStartedPayload
  | AgentProgressPayload
  | AgentThinkingPayload
  | AgentToolCallPayload
  | AgentMessagePayload
  | AgentCompletedPayload
  | TeamMessagePayload
  | InboxReceivedPayload
  | AgentApprovalRequiredPayload;

/**
 * Agent Team SSE event structure (from AG-UI CustomEvent)
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
 * Event handlers for team events
 */
export interface SwarmEventHandlers {
  onTeamCreated?: (payload: TeamCreatedPayload) => void;
  onTeamStatusUpdate?: (payload: TeamStatusUpdatePayload) => void;
  onTeamCompleted?: (payload: TeamCompletedPayload) => void;
  onWorkerStarted?: (payload: AgentStartedPayload) => void;
  onWorkerProgress?: (payload: AgentProgressPayload) => void;
  onWorkerThinking?: (payload: AgentThinkingPayload) => void;
  onWorkerToolCall?: (payload: AgentToolCallPayload) => void;
  onAgentMessage?: (payload: AgentMessagePayload) => void;
  onWorkerCompleted?: (payload: AgentCompletedPayload) => void;
  onError?: (error: Error) => void;
}

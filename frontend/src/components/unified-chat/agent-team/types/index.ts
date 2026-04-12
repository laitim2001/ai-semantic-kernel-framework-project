/**
 * Agent Team Types - Index
 *
 * Export all agent-team-related types for UI components.
 * Sprint 101: Event types (snake_case for SSE)
 * Sprint 102: Component types (camelCase for UI)
 */

// Re-export event types for SSE handling
export * from './events';

// =============================================================================
// Basic Types (for UI components)
// =============================================================================

export type AgentType = 'claude_sdk' | 'maf' | 'hybrid' | 'research' | 'custom';
export type AgentMemberStatus = 'pending' | 'running' | 'paused' | 'completed' | 'failed';
export type TeamMode = 'sequential' | 'parallel' | 'pipeline' | 'hierarchical' | 'hybrid';
export type TeamStatus = 'initializing' | 'executing' | 'aggregating' | 'completed' | 'failed';

// =============================================================================
// Tool Call (for AgentDetail)
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
// Thinking Content (for AgentDetail)
// =============================================================================

export interface ThinkingContent {
  content: string;
  timestamp: string;
  tokenCount?: number;
}

// =============================================================================
// Agent Message (for AgentDetail)
// =============================================================================

export interface AgentMessage {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string;
  timestamp: string;
  toolCallId?: string;
}

// =============================================================================
// Agent Summary (for AgentCard display)
// =============================================================================

export interface UIAgentSummary {
  agentId: string;
  agentName: string;
  agentType: AgentType;
  role: string;
  status: AgentMemberStatus;
  progress: number;
  currentAction?: string;
  toolCallsCount: number;
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
}

// =============================================================================
// Agent Detail (for Drawer display)
// =============================================================================

export interface AgentDetail extends UIAgentSummary {
  taskId: string;
  taskDescription: string;
  thinkingHistory: ThinkingContent[];
  toolCalls: ToolCallInfo[];
  messages: AgentMessage[];
  result?: Record<string, unknown>;
  error?: string;
  checkpointId?: string;
  checkpointBackend?: string;
}

// =============================================================================
// Agent Team Status (for AgentTeamPanel)
// =============================================================================

export interface UIAgentTeamStatus {
  teamId: string;
  sessionId: string;
  mode: TeamMode;
  status: TeamStatus;
  totalAgents: number;
  overallProgress: number;
  agents: UIAgentSummary[];
  createdAt: string;
  startedAt?: string;
  estimatedCompletion?: string;
  completedAt?: string;
  metadata: Record<string, unknown>;
}

// =============================================================================
// Component Props
// =============================================================================

export interface AgentTeamPanelProps {
  agentTeamStatus: UIAgentTeamStatus | null;
  onAgentClick?: (agent: UIAgentSummary) => void;
  isLoading?: boolean;
  className?: string;
}

export interface AgentTeamHeaderProps {
  mode: TeamMode;
  status: TeamStatus;
  totalAgents: number;
  startedAt?: string;
}

export interface OverallProgressProps {
  progress: number;
  status: TeamStatus;
  animated?: boolean;
}

export interface AgentCardProps {
  agent: UIAgentSummary;
  index: number;
  isSelected?: boolean;
  onClick?: () => void;
}

export interface AgentCardListProps {
  agents: UIAgentSummary[];
  selectedAgentId?: string;
  onAgentClick?: (agent: UIAgentSummary) => void;
}

export interface AgentTeamStatusBadgesProps {
  agents: UIAgentSummary[];
  onAgentClick?: (agent: UIAgentSummary) => void;
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
 * Agent type configuration for UI
 */
export interface AgentTypeConfig {
  label: string;
  iconName: string;
}

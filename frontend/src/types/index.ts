// =============================================================================
// IPA Platform - TypeScript Type Definitions
// =============================================================================
// Sprint 5: Frontend UI - Shared Types
//
// Central type definitions for the frontend application.
// =============================================================================

// -----------------------------------------------------------------------------
// Common Types
// -----------------------------------------------------------------------------

export type Status = 'pending' | 'running' | 'completed' | 'failed' | 'paused';

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// -----------------------------------------------------------------------------
// Workflow Types
// -----------------------------------------------------------------------------

export interface Workflow {
  id: string;
  name: string;
  description: string;
  version: string | number;
  status: 'active' | 'inactive' | 'draft';
  trigger_type: 'manual' | 'schedule' | 'event' | 'webhook';
  trigger_config?: Record<string, unknown>;
  // API returns graph_definition, but mock data uses definition
  definition?: WorkflowDefinition;
  graph_definition?: WorkflowGraphDefinition;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
  last_execution_at?: string;
  execution_count?: number;
}

export interface WorkflowDefinition {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

export interface WorkflowGraphDefinition {
  nodes: WorkflowGraphNode[];
  edges: WorkflowGraphEdge[];
  variables?: Record<string, unknown>;
}

export interface WorkflowNode {
  id: string;
  type: 'start' | 'end' | 'task' | 'decision' | 'agent' | 'approval' | 'gateway';
  name: string;
  config: Record<string, unknown>;
}

export interface WorkflowGraphNode {
  id: string;
  type: string;
  name: string | null;
  agent_id: string | null;
  config: Record<string, unknown>;
  position?: { x: number; y: number } | null;
}

export interface WorkflowEdge {
  id?: string;
  source: string;
  target: string;
  condition?: string;
}

export interface WorkflowGraphEdge {
  source: string;
  target: string;
  condition?: string;
  label?: string;
}

// -----------------------------------------------------------------------------
// Execution Types
// -----------------------------------------------------------------------------

export interface Execution {
  id: string;
  workflow_id: string;
  workflow_name: string;
  status: Status;
  started_at: string;
  completed_at?: string;
  duration_ms?: number;
  current_step: number;
  total_steps: number;
  error?: string;
  llm_calls: number;
  llm_tokens: number;
  llm_cost: number;
}

export interface ExecutionStep {
  id: string;
  execution_id: string;
  step_number: number;
  node_id: string;
  node_name: string;
  status: Status;
  started_at: string;
  completed_at?: string;
  input: Record<string, unknown>;
  output?: Record<string, unknown>;
  error?: string;
}

// -----------------------------------------------------------------------------
// Agent Types
// -----------------------------------------------------------------------------

export interface Agent {
  id: string;
  name: string;
  description: string;
  category: string;
  template_id?: string;
  instructions: string;
  tools: string[];
  // API returns model_config_data, but mock data uses model_config
  model_config?: ModelConfig;
  model_config_data?: ModelConfig;
  max_iterations?: number;
  version?: number;
  status: 'active' | 'inactive';
  created_at: string;
  updated_at: string;
  execution_count?: number;
  avg_response_time_ms?: number;
}

export interface ModelConfig {
  model?: string;
  temperature?: number;
  max_tokens?: number;
}

// -----------------------------------------------------------------------------
// Template Types
// -----------------------------------------------------------------------------

export interface Template {
  id: string;
  name: string;
  description: string;
  category: string;
  version: string;
  author: string;
  tags: string[];
  config_schema: Record<string, unknown>;
  default_config: Record<string, unknown>;
  downloads: number;
  rating: number;
  created_at: string;
}

// -----------------------------------------------------------------------------
// Checkpoint / Approval Types
// -----------------------------------------------------------------------------

export interface Checkpoint {
  id: string;
  execution_id: string;
  workflow_id: string;
  workflow_name: string;
  step: number;
  step_name: string;
  status: 'pending' | 'approved' | 'rejected';
  content: string;
  context: Record<string, unknown>;
  created_at: string;
  resolved_at?: string;
  resolved_by?: string;
  feedback?: string;
}

// -----------------------------------------------------------------------------
// Audit Types
// -----------------------------------------------------------------------------

export interface AuditLog {
  id: string;
  timestamp: string;
  action: string;
  resource_type: string;
  resource_id: string;
  user_id?: string;
  user_name?: string;
  details: Record<string, unknown>;
  ip_address?: string;
}

// -----------------------------------------------------------------------------
// Dashboard Types
// -----------------------------------------------------------------------------

export interface DashboardStats {
  total_workflows: number;
  active_workflows: number;
  total_executions: number;
  success_rate: number;
  pending_approvals: number;
  llm_cost_today: number;
  llm_cost_month: number;
  avg_execution_time_ms: number;
}

export interface ExecutionChartData {
  date: string;
  total: number;
  success: number;
  failed: number;
}

export interface CostChartData {
  date: string;
  cost: number;
  tokens: number;
}

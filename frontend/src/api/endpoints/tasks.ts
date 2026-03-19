/**
 * Task Management API Endpoints
 *
 * Sprint 139: Phase 40 - Task Dashboard
 *
 * API client for task CRUD and lifecycle:
 * - List / get tasks with filters
 * - Get task steps
 * - Cancel / retry tasks
 */

import { api } from '../client';

// =============================================================================
// Types
// =============================================================================

/** Task status */
export type TaskStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled';

/** Task priority */
export type TaskPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

/** Task step status */
export type TaskStepStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'skipped';

/** Task summary for list views */
export interface TaskSummary {
  task_id: string;
  name: string;
  status: TaskStatus;
  priority: TaskPriority;
  progress: number;
  agent_id?: string;
  agent_name?: string;
  session_id?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  duration_ms?: number;
  error?: string;
}

/** Task step detail */
export interface TaskStep {
  step_id: string;
  name: string;
  status: TaskStepStatus;
  order: number;
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  output_summary?: string;
  error?: string;
}

/** Task detail (full) */
export interface TaskDetail extends TaskSummary {
  description?: string;
  type?: string;
  input?: Record<string, unknown>;
  result?: Record<string, unknown>;
  steps?: TaskStep[];
  metadata?: Record<string, unknown>;
}

/** Task list response */
export interface TaskListResponse {
  tasks: TaskSummary[];
  total: number;
  page: number;
  page_size: number;
}

/** Task steps response */
export interface TaskStepsResponse {
  steps: TaskStep[];
  total: number;
}

/** Filters for task list */
export interface TaskFilters {
  status?: TaskStatus;
  priority?: TaskPriority;
  agent_id?: string;
  session_id?: string;
  page?: number;
  page_size?: number;
}

// =============================================================================
// Tasks API Client
// =============================================================================

export const tasksApi = {
  /**
   * List tasks with optional filters
   */
  getTasks: (filters?: TaskFilters): Promise<TaskListResponse> => {
    const params = new URLSearchParams();
    if (filters?.status) params.set('status', filters.status);
    if (filters?.priority) params.set('priority', filters.priority);
    if (filters?.agent_id) params.set('agent_id', filters.agent_id);
    if (filters?.session_id) params.set('session_id', filters.session_id);
    if (filters?.page) params.set('page', String(filters.page));
    if (filters?.page_size) params.set('page_size', String(filters.page_size));
    const query = params.toString();
    return api.get<TaskListResponse>(`/tasks${query ? `?${query}` : ''}`);
  },

  /**
   * Get a single task by ID
   */
  getTask: (id: string): Promise<TaskDetail> =>
    api.get<TaskDetail>(`/tasks/${id}`),

  /**
   * Get steps for a task
   */
  getTaskSteps: (id: string): Promise<TaskStepsResponse> =>
    api.get<TaskStepsResponse>(`/tasks/${id}/steps`),

  /**
   * Cancel a running task
   */
  cancelTask: (id: string): Promise<TaskDetail> =>
    api.post<TaskDetail>(`/tasks/${id}/cancel`),

  /**
   * Retry a failed task
   */
  retryTask: (id: string): Promise<TaskDetail> =>
    api.post<TaskDetail>(`/tasks/${id}/retry`),
};

export default tasksApi;

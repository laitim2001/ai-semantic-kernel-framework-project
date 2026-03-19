/**
 * useTasks - Task Management Hooks
 *
 * Sprint 139: Phase 40 - Task Dashboard
 *
 * React Query hooks for task lifecycle:
 * - useTasks: List tasks with filters + pagination
 * - useTask: Single task detail with auto-refetch
 * - useTaskSteps: Task step list
 * - useCancelTask / useRetryTask: Mutation hooks
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  tasksApi,
  type TaskFilters,
  type TaskListResponse,
  type TaskDetail,
  type TaskStepsResponse,
} from '@/api/endpoints/tasks';

// =============================================================================
// Query Keys
// =============================================================================

export const taskKeys = {
  all: ['tasks'] as const,
  lists: () => [...taskKeys.all, 'list'] as const,
  list: (filters?: TaskFilters) => [...taskKeys.lists(), filters] as const,
  details: () => [...taskKeys.all, 'detail'] as const,
  detail: (id: string) => [...taskKeys.details(), id] as const,
  steps: (id: string) => [...taskKeys.all, 'steps', id] as const,
};

// =============================================================================
// Hooks
// =============================================================================

/**
 * Fetch tasks list with optional filters and pagination
 */
export function useTasks(filters?: TaskFilters) {
  return useQuery<TaskListResponse>({
    queryKey: taskKeys.list(filters),
    queryFn: () => tasksApi.getTasks(filters),
    refetchInterval: filters?.status === 'running' ? 5000 : false,
  });
}

/**
 * Fetch a single task detail with auto-refetch for running tasks
 */
export function useTask(id: string) {
  return useQuery<TaskDetail>({
    queryKey: taskKeys.detail(id),
    queryFn: () => tasksApi.getTask(id),
    enabled: !!id,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'running' || status === 'pending') return 3000;
      return false;
    },
  });
}

/**
 * Fetch task steps
 */
export function useTaskSteps(id: string) {
  return useQuery<TaskStepsResponse>({
    queryKey: taskKeys.steps(id),
    queryFn: () => tasksApi.getTaskSteps(id),
    enabled: !!id,
  });
}

/**
 * Cancel a running task
 */
export function useCancelTask() {
  const queryClient = useQueryClient();

  return useMutation<TaskDetail, Error, string>({
    mutationFn: (id: string) => tasksApi.cancelTask(id),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() });
      queryClient.setQueryData(taskKeys.detail(data.task_id), data);
    },
  });
}

/**
 * Retry a failed task
 */
export function useRetryTask() {
  const queryClient = useQueryClient();

  return useMutation<TaskDetail, Error, string>({
    mutationFn: (id: string) => tasksApi.retryTask(id),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() });
      queryClient.setQueryData(taskKeys.detail(data.task_id), data);
    },
  });
}

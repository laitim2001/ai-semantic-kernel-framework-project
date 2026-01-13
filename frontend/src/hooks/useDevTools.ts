// =============================================================================
// IPA Platform - DevTools React Hooks
// =============================================================================
// Sprint 87: S87-2 - DevUI Core Pages
//
// React Query hooks for DevTools API integration.
//
// Dependencies:
//   - React Query (TanStack Query)
//   - DevTools API client
// =============================================================================

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { devToolsApi } from '@/api/devtools';
import type { ListTracesParams, ListEventsParams } from '@/types/devtools';

/**
 * Query keys for DevTools
 */
export const devToolsKeys = {
  all: ['devtools'] as const,
  traces: () => [...devToolsKeys.all, 'traces'] as const,
  traceList: (params?: ListTracesParams) => [...devToolsKeys.traces(), params] as const,
  trace: (executionId: string) => [...devToolsKeys.traces(), executionId] as const,
  events: (executionId: string) => [...devToolsKeys.trace(executionId), 'events'] as const,
  eventList: (executionId: string, params?: ListEventsParams) =>
    [...devToolsKeys.events(executionId), params] as const,
};

/**
 * Hook to fetch traces list
 */
export function useTraces(params?: ListTracesParams) {
  return useQuery({
    queryKey: devToolsKeys.traceList(params),
    queryFn: () => devToolsApi.listTraces(params),
    staleTime: 30 * 1000, // 30 seconds
  });
}

/**
 * Hook to fetch a single trace
 */
export function useTrace(executionId: string) {
  return useQuery({
    queryKey: devToolsKeys.trace(executionId),
    queryFn: () => devToolsApi.getTrace(executionId),
    enabled: !!executionId,
  });
}

/**
 * Hook to fetch events for a trace
 */
export function useTraceEvents(executionId: string, params?: ListEventsParams) {
  return useQuery({
    queryKey: devToolsKeys.eventList(executionId, params),
    queryFn: () => devToolsApi.getEvents(executionId, params),
    enabled: !!executionId,
  });
}

/**
 * Hook to delete a trace
 */
export function useDeleteTrace() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (executionId: string) => devToolsApi.deleteTrace(executionId),
    onSuccess: () => {
      // Invalidate traces list to refetch
      queryClient.invalidateQueries({ queryKey: devToolsKeys.traces() });
    },
  });
}

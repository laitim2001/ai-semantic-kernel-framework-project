/**
 * useSessions - Session Management Hooks
 *
 * Sprint 138: Phase 40 - Session Management
 *
 * React Query hooks for session CRUD and recovery:
 * - useSessions: List sessions with filters
 * - useSession: Get single session detail
 * - useSessionMessages: Get session message history
 * - useRecoverableSessions: Get recoverable sessions
 * - useResumeSession: Resume mutation
 * - useDeleteSession: Delete mutation
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  sessionsApi,
  type SessionFilters,
  type SessionListResponse,
  type SessionDetail,
  type SessionMessagesResponse,
  type SessionResumeResponse,
} from '@/api/endpoints/sessions';

// =============================================================================
// Query Keys
// =============================================================================

export const sessionKeys = {
  all: ['sessions'] as const,
  lists: () => [...sessionKeys.all, 'list'] as const,
  list: (filters?: SessionFilters) =>
    [...sessionKeys.lists(), filters] as const,
  details: () => [...sessionKeys.all, 'detail'] as const,
  detail: (id: string) => [...sessionKeys.details(), id] as const,
  messages: (id: string) => [...sessionKeys.all, 'messages', id] as const,
  recoverable: () => [...sessionKeys.all, 'recoverable'] as const,
};

// =============================================================================
// Hooks
// =============================================================================

/**
 * Fetch sessions list with optional filters
 */
export function useSessions(filters?: SessionFilters) {
  return useQuery<SessionListResponse>({
    queryKey: sessionKeys.list(filters),
    queryFn: () => sessionsApi.getSessions(filters),
  });
}

/**
 * Fetch a single session detail
 */
export function useSession(id: string) {
  return useQuery<SessionDetail>({
    queryKey: sessionKeys.detail(id),
    queryFn: () => sessionsApi.getSession(id),
    enabled: !!id,
  });
}

/**
 * Fetch session message history
 */
export function useSessionMessages(id: string) {
  return useQuery<SessionMessagesResponse>({
    queryKey: sessionKeys.messages(id),
    queryFn: () => sessionsApi.getSessionMessages(id),
    enabled: !!id,
  });
}

/**
 * Fetch recoverable sessions
 */
export function useRecoverableSessions() {
  return useQuery<SessionListResponse>({
    queryKey: sessionKeys.recoverable(),
    queryFn: () => sessionsApi.getRecoverableSessions(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });
}

/**
 * Resume an interrupted session
 */
export function useResumeSession() {
  const queryClient = useQueryClient();

  return useMutation<SessionResumeResponse, Error, string>({
    mutationFn: (id: string) => sessionsApi.resumeSession(id),
    onSuccess: () => {
      // Invalidate session lists to reflect status change
      queryClient.invalidateQueries({ queryKey: sessionKeys.lists() });
      queryClient.invalidateQueries({ queryKey: sessionKeys.recoverable() });
    },
  });
}

/**
 * Delete a session
 */
export function useDeleteSession() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: (id: string) => sessionsApi.deleteSession(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sessionKeys.lists() });
      queryClient.invalidateQueries({ queryKey: sessionKeys.recoverable() });
    },
  });
}

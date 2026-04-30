/**
 * useMemory - Memory System Hooks
 *
 * Sprint 140: Phase 40 - Memory Management
 *
 * React Query hooks for memory system:
 * - useMemorySearch: Search memories
 * - useUserMemories: User memory listing
 * - useMemoryStats: Statistics
 * - useDeleteMemory: Deletion mutation
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  memoryApi,
  type MemorySearchResponse,
  type UserMemoriesResponse,
  type MemoryStats,
  type UserMemoryOptions,
} from '@/api/endpoints/memory';

// =============================================================================
// Query Keys
// =============================================================================

export const memoryKeys = {
  all: ['memory'] as const,
  search: (query: string, userId?: string) =>
    [...memoryKeys.all, 'search', query, userId] as const,
  userMemories: (userId: string) =>
    [...memoryKeys.all, 'user', userId] as const,
  stats: () => [...memoryKeys.all, 'stats'] as const,
};

// =============================================================================
// Hooks
// =============================================================================

/**
 * Search memories
 */
export function useMemorySearch(query: string, userId?: string) {
  return useQuery<MemorySearchResponse>({
    queryKey: memoryKeys.search(query, userId),
    queryFn: () => memoryApi.searchMemories(query, userId),
    enabled: query.length > 0,
  });
}

/**
 * Get user memories
 */
export function useUserMemories(userId: string, options?: UserMemoryOptions) {
  return useQuery<UserMemoriesResponse>({
    queryKey: memoryKeys.userMemories(userId),
    queryFn: () => memoryApi.getUserMemories(userId, options),
    enabled: !!userId,
  });
}

/**
 * Get memory statistics
 */
export function useMemoryStats() {
  return useQuery<MemoryStats>({
    queryKey: memoryKeys.stats(),
    queryFn: () => memoryApi.getMemoryStats(),
  });
}

/**
 * Delete a memory
 */
export function useDeleteMemory() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: (id: string) => memoryApi.deleteMemory(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: memoryKeys.all });
    },
  });
}

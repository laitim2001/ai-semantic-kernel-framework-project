/**
 * Memory System API Endpoints
 *
 * Sprint 140: Phase 40 - Memory Management
 *
 * API client for memory system operations:
 * - Search memories
 * - User memory listing
 * - Memory statistics
 * - Memory deletion
 */

import { api } from '../client';

// =============================================================================
// Types
// =============================================================================

/** Memory item */
export interface MemoryItem {
  id: string;
  content: string;
  user_id: string;
  score?: number;
  created_at: string;
  updated_at?: string;
  metadata?: Record<string, unknown>;
}

/** Memory search response */
export interface MemorySearchResponse {
  memories: MemoryItem[];
  total: number;
  query: string;
}

/** User memories response */
export interface UserMemoriesResponse {
  memories: MemoryItem[];
  total: number;
  user_id: string;
}

/** Memory statistics */
export interface MemoryStats {
  total_memories: number;
  total_users: number;
  last_updated: string;
  storage_size?: string;
}

/** User memory options */
export interface UserMemoryOptions {
  limit?: number;
  offset?: number;
}

// =============================================================================
// Memory API Client
// =============================================================================

export const memoryApi = {
  /**
   * Search memories
   */
  searchMemories: (
    query: string,
    userId?: string
  ): Promise<MemorySearchResponse> =>
    api.post<MemorySearchResponse>('/memory/search', {
      query,
      user_id: userId,
    }),

  /**
   * Get user memories
   */
  getUserMemories: (
    userId: string,
    options?: UserMemoryOptions
  ): Promise<UserMemoriesResponse> => {
    const params = new URLSearchParams();
    if (options?.limit) params.set('limit', String(options.limit));
    if (options?.offset) params.set('offset', String(options.offset));
    const query = params.toString();
    return api.get<UserMemoriesResponse>(
      `/memory/user/${userId}${query ? `?${query}` : ''}`
    );
  },

  /**
   * Get memory health/stats
   */
  getMemoryStats: (): Promise<MemoryStats> =>
    api.get<MemoryStats>('/memory/health'),

  /**
   * Delete a memory
   */
  deleteMemory: (id: string): Promise<void> =>
    api.delete(`/memory/${id}`),
};

export default memoryApi;

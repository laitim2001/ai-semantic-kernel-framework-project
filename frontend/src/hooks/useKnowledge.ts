/**
 * useKnowledge - Knowledge Management Hooks
 *
 * Sprint 140: Phase 40 - Knowledge Management
 *
 * React Query hooks for knowledge base operations:
 * - useKnowledgeSearch: Semantic search
 * - useDocuments: Document listing
 * - useUploadDocument / useDeleteDocument: Mutations
 * - useSkills: Skills listing
 * - useKnowledgeStatus: Service health
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  knowledgeApi,
  type DocumentFilters,
  type DocumentListResponse,
  type KnowledgeSearchResponse,
  type KnowledgeSearchOptions,
  type KnowledgeDocument,
  type SkillsResponse,
  type KnowledgeStatusResponse,
} from '@/api/endpoints/knowledge';

// =============================================================================
// Query Keys
// =============================================================================

export const knowledgeKeys = {
  all: ['knowledge'] as const,
  documents: () => [...knowledgeKeys.all, 'documents'] as const,
  documentList: (filters?: DocumentFilters) =>
    [...knowledgeKeys.documents(), filters] as const,
  search: (query: string) => [...knowledgeKeys.all, 'search', query] as const,
  skills: () => [...knowledgeKeys.all, 'skills'] as const,
  status: () => [...knowledgeKeys.all, 'status'] as const,
};

// =============================================================================
// Hooks
// =============================================================================

/**
 * Semantic search in knowledge base
 */
export function useKnowledgeSearch(
  query: string,
  options?: KnowledgeSearchOptions
) {
  return useQuery<KnowledgeSearchResponse>({
    queryKey: knowledgeKeys.search(query),
    queryFn: () => knowledgeApi.searchKnowledge(query, options),
    enabled: query.length > 0,
  });
}

/**
 * List documents
 */
export function useDocuments(filters?: DocumentFilters) {
  return useQuery<DocumentListResponse>({
    queryKey: knowledgeKeys.documentList(filters),
    queryFn: () => knowledgeApi.getDocuments(filters),
  });
}

/**
 * Upload a document
 */
export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation<
    KnowledgeDocument,
    Error,
    { file: File; metadata?: Record<string, string> }
  >({
    mutationFn: ({ file, metadata }) =>
      knowledgeApi.uploadDocument(file, metadata),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: knowledgeKeys.documents() });
    },
  });
}

/**
 * Delete a document
 */
export function useDeleteDocument() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: (id: string) => knowledgeApi.deleteDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: knowledgeKeys.documents() });
    },
  });
}

/**
 * Get available skills
 */
export function useSkills() {
  return useQuery<SkillsResponse>({
    queryKey: knowledgeKeys.skills(),
    queryFn: () => knowledgeApi.getSkills(),
  });
}

/**
 * Get knowledge service status
 */
export function useKnowledgeStatus() {
  return useQuery<KnowledgeStatusResponse>({
    queryKey: knowledgeKeys.status(),
    queryFn: () => knowledgeApi.getStatus(),
    refetchInterval: 30000,
  });
}

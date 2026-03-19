/**
 * Knowledge Management API Endpoints
 *
 * Sprint 140: Phase 40 - Knowledge Management
 *
 * API client for knowledge base operations:
 * - Document upload/list/delete
 * - Semantic search
 * - Skills listing
 * - Service status
 */

import { api, API_BASE_URL } from '../client';
import { useAuthStore } from '@/store/authStore';
import { getGuestHeaders } from '@/utils/guestUser';

// =============================================================================
// Types
// =============================================================================

/** Document status */
export type DocumentStatus = 'processing' | 'indexed' | 'failed' | 'deleted';

/** Document metadata */
export interface KnowledgeDocument {
  id: string;
  name: string;
  size: number;
  format: string;
  status: DocumentStatus;
  chunk_count?: number;
  uploaded_at: string;
  metadata?: Record<string, unknown>;
}

/** Document list response */
export interface DocumentListResponse {
  documents: KnowledgeDocument[];
  total: number;
}

/** Search result item */
export interface KnowledgeSearchResult {
  content: string;
  score: number;
  source_document: string;
  source_id: string;
  metadata?: Record<string, unknown>;
}

/** Search response */
export interface KnowledgeSearchResponse {
  results: KnowledgeSearchResult[];
  total: number;
  query: string;
}

/** Search options */
export interface KnowledgeSearchOptions {
  top_k?: number;
  min_score?: number;
  filter?: Record<string, unknown>;
}

/** Agent skill */
export interface AgentSkill {
  name: string;
  description: string;
  status: 'active' | 'inactive';
  source?: string;
}

/** Skills response */
export interface SkillsResponse {
  skills: AgentSkill[];
  total: number;
}

/** Knowledge service status */
export interface KnowledgeStatusResponse {
  status: 'healthy' | 'degraded' | 'unavailable';
  vector_store: string;
  document_count: number;
  embedding_model: string;
  message?: string;
}

/** Document filters */
export interface DocumentFilters {
  status?: DocumentStatus;
  format?: string;
  limit?: number;
  offset?: number;
}

// =============================================================================
// Knowledge API Client
// =============================================================================

export const knowledgeApi = {
  /**
   * Upload a document (multipart/form-data)
   */
  uploadDocument: async (
    file: File,
    metadata?: Record<string, string>
  ): Promise<KnowledgeDocument> => {
    const token = useAuthStore.getState().token;
    const guestHeaders = getGuestHeaders();

    const formData = new FormData();
    formData.append('file', file);
    if (metadata) {
      formData.append('metadata', JSON.stringify(metadata));
    }

    const headers: Record<string, string> = { ...guestHeaders };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const response = await fetch(
      `${API_BASE_URL}/knowledge/documents`,
      {
        method: 'POST',
        headers,
        body: formData,
      }
    );

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Upload failed');
    }

    return response.json();
  },

  /**
   * Search knowledge base
   */
  searchKnowledge: (
    query: string,
    options?: KnowledgeSearchOptions
  ): Promise<KnowledgeSearchResponse> =>
    api.post<KnowledgeSearchResponse>('/knowledge/search', {
      query,
      ...options,
    }),

  /**
   * List documents
   */
  getDocuments: (filters?: DocumentFilters): Promise<DocumentListResponse> => {
    const params = new URLSearchParams();
    if (filters?.status) params.set('status', filters.status);
    if (filters?.format) params.set('format', filters.format);
    if (filters?.limit) params.set('limit', String(filters.limit));
    if (filters?.offset) params.set('offset', String(filters.offset));
    const query = params.toString();
    return api.get<DocumentListResponse>(
      `/knowledge/documents${query ? `?${query}` : ''}`
    );
  },

  /**
   * Delete a document
   */
  deleteDocument: (id: string): Promise<void> =>
    api.delete(`/knowledge/documents/${id}`),

  /**
   * Get available skills
   */
  getSkills: (): Promise<SkillsResponse> =>
    api.get<SkillsResponse>('/knowledge/skills'),

  /**
   * Get knowledge service status
   */
  getStatus: (): Promise<KnowledgeStatusResponse> =>
    api.get<KnowledgeStatusResponse>('/knowledge/status'),
};

export default knowledgeApi;

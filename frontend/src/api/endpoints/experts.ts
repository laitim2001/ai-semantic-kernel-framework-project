/**
 * Expert Management API Client
 *
 * Sprint 164 — Phase 46 Agent Expert Registry.
 */

import { api } from '../client';

// =============================================================================
// Types
// =============================================================================

export interface ExpertSummary {
  id: string;
  name: string;
  display_name: string;
  display_name_zh: string;
  description: string;
  domain: string;
  capabilities: string[];
  model: string | null;
  max_iterations: number;
  tools: string[];
  enabled: boolean;
  is_builtin: boolean;
  metadata: Record<string, unknown>;
  version: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface ExpertListResponse {
  experts: ExpertSummary[];
  total: number;
}

export interface CreateExpertRequest {
  name: string;
  display_name: string;
  display_name_zh: string;
  description?: string;
  domain: string;
  capabilities?: string[];
  model?: string | null;
  max_iterations?: number;
  system_prompt: string;
  tools?: string[];
  enabled?: boolean;
  metadata?: Record<string, unknown>;
}

export interface UpdateExpertRequest {
  display_name?: string;
  display_name_zh?: string;
  description?: string;
  domain?: string;
  capabilities?: string[];
  model?: string | null;
  max_iterations?: number;
  system_prompt?: string;
  tools?: string[];
  enabled?: boolean;
  metadata?: Record<string, unknown>;
}

export interface ReloadResponse {
  status: string;
  experts_loaded: number;
  expert_names: string[];
}

// =============================================================================
// API Functions
// =============================================================================

export const expertsApi = {
  list: async (domain?: string, enabled?: boolean): Promise<ExpertListResponse> => {
    const params = new URLSearchParams();
    if (domain) params.set('domain', domain);
    if (enabled !== undefined) params.set('enabled', String(enabled));
    const query = params.toString();
    return api.get<ExpertListResponse>(`/experts/${query ? `?${query}` : ''}`);
  },

  get: async (name: string): Promise<ExpertSummary> => {
    return api.get<ExpertSummary>(`/experts/${name}`);
  },

  create: async (data: CreateExpertRequest): Promise<ExpertSummary> => {
    return api.post<ExpertSummary>('/experts/', data);
  },

  update: async (name: string, data: UpdateExpertRequest): Promise<ExpertSummary> => {
    return api.put<ExpertSummary>(`/experts/${name}`, data);
  },

  delete: async (name: string): Promise<{ status: string; name: string }> => {
    return api.delete<{ status: string; name: string }>(`/experts/${name}`);
  },

  reload: async (): Promise<ReloadResponse> => {
    return api.post<ReloadResponse>('/experts/reload', {});
  },
};

// =============================================================================
// IPA Platform - DevTools API Client
// =============================================================================
// Sprint 87: S87-2 - DevUI Core Pages
//
// API client for DevTools tracing endpoints.
//
// Dependencies:
//   - Axios client
//   - DevTools types
// =============================================================================

import { api } from './client';
import type {
  Trace,
  TraceDetail,
  TraceEvent,
  ListTracesParams,
  ListEventsParams,
  PaginatedResponse,
  DeleteTraceResponse,
} from '@/types/devtools';

/**
 * DevTools API endpoints
 */
/**
 * Build query string from params
 */
function buildQueryString(params?: Record<string, unknown>): string {
  if (!params) return '';
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.append(key, String(value));
    }
  });
  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : '';
}

export const devToolsApi = {
  /**
   * List all traces with optional filtering
   */
  listTraces: async (params?: ListTracesParams): Promise<PaginatedResponse<Trace>> => {
    const queryString = buildQueryString({
      workflow_id: params?.workflow_id,
      status: params?.status,
      limit: params?.limit ?? 20,
      offset: params?.offset ?? 0,
    });
    return api.get<PaginatedResponse<Trace>>(`/devtools/traces${queryString}`);
  },

  /**
   * Get a single trace by execution ID
   */
  getTrace: async (executionId: string): Promise<TraceDetail> => {
    return api.get<TraceDetail>(`/devtools/traces/${executionId}`);
  },

  /**
   * Get events for a specific trace
   */
  getEvents: async (
    executionId: string,
    params?: ListEventsParams
  ): Promise<PaginatedResponse<TraceEvent>> => {
    const queryString = buildQueryString({
      event_type: params?.event_type,
      severity: params?.severity,
      limit: params?.limit ?? 50,
      offset: params?.offset ?? 0,
    });
    return api.get<PaginatedResponse<TraceEvent>>(
      `/devtools/traces/${executionId}/events${queryString}`
    );
  },

  /**
   * Delete a trace by execution ID
   */
  deleteTrace: async (executionId: string): Promise<DeleteTraceResponse> => {
    return api.delete<DeleteTraceResponse>(`/devtools/traces/${executionId}`);
  },
};

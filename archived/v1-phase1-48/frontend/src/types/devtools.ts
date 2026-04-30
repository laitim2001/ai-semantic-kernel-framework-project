// =============================================================================
// IPA Platform - DevTools Type Definitions
// =============================================================================
// Sprint 87: S87-2 - DevUI Core Pages
//
// Type definitions for DevTools tracing and events.
//
// Dependencies:
//   - None
// =============================================================================

/**
 * Trace status enumeration
 */
export type TraceStatus = 'running' | 'completed' | 'failed';

/**
 * Event severity levels
 */
export type EventSeverity = 'debug' | 'info' | 'warning' | 'error' | 'critical';

/**
 * Trace summary interface
 * Represents a workflow execution trace
 */
export interface Trace {
  id: string;
  execution_id: string;
  workflow_id: string;
  started_at: string;
  ended_at?: string;
  duration_ms?: number;
  status: TraceStatus;
  event_count: number;
  span_count: number;
  metadata: Record<string, unknown>;
}

/**
 * Trace event interface
 * Represents a single event within a trace
 */
export interface TraceEvent {
  id: string;
  trace_id: string;
  event_type: string;
  timestamp: string;
  data: Record<string, unknown>;
  severity: EventSeverity;
  parent_event_id?: string;
  executor_id?: string;
  step_number?: number;
  duration_ms?: number;
  tags: string[];
  metadata: Record<string, unknown>;
}

/**
 * Parameters for listing traces
 */
export interface ListTracesParams {
  workflow_id?: string;
  status?: TraceStatus;
  limit?: number;
  offset?: number;
}

/**
 * Parameters for listing events
 */
export interface ListEventsParams {
  event_type?: string;
  severity?: EventSeverity;
  limit?: number;
  offset?: number;
}

/**
 * Paginated response wrapper
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * Trace detail response (includes events summary)
 */
export interface TraceDetail extends Trace {
  events_summary?: {
    by_type: Record<string, number>;
    by_severity: Record<EventSeverity, number>;
  };
}

/**
 * Delete trace response
 */
export interface DeleteTraceResponse {
  success: boolean;
  message: string;
}

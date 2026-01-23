/**
 * Orchestration API Endpoints
 *
 * Sprint 99: Phase 28 Integration - Chat Page Orchestration Flow
 *
 * API client for Phase 28 orchestration endpoints:
 * - Three-layer intent routing
 * - Guided dialog
 * - Risk assessment
 * - HITL approvals
 */

import { api } from '../client';

// =============================================================================
// Types - Intent Routing
// =============================================================================

/** IT Intent categories */
export type ITIntentCategory =
  | 'incident'
  | 'change'
  | 'request'
  | 'query'
  | 'unknown';

/** Risk level */
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

/** Workflow type */
export type WorkflowType = 'simple' | 'sequential' | 'magentic' | 'handoff';

/** Completeness info from routing */
export interface CompletenessInfo {
  is_complete: boolean;
  missing_fields: string[];
  optional_missing: string[];
  completeness_score: number;
  suggestions: string[];
}

/** Routing decision from three-layer router */
export interface RoutingDecision {
  intent_category: ITIntentCategory;
  sub_intent: string | null;
  confidence: number;
  workflow_type: WorkflowType;
  risk_level: RiskLevel;
  completeness: CompletenessInfo;
  routing_layer: 'pattern' | 'semantic' | 'llm' | 'none';
  rule_id: string | null;
  reasoning: string;
  processing_time_ms: number;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

/** Risk factor from assessment */
export interface RiskFactor {
  name: string;
  description: string;
  weight: number;
  value: string;
  impact: 'increase' | 'decrease' | 'neutral';
}

/** Risk assessment result */
export interface RiskAssessment {
  level: RiskLevel;
  score: number;
  requires_approval: boolean;
  approval_type: 'single' | 'multi' | 'none';
  factors: RiskFactor[];
  reasoning: string;
  policy_id: string;
  adjustments_applied: string[];
}

/** Intent classification response */
export interface IntentClassifyResponse {
  routing_decision: RoutingDecision;
  risk_assessment: RiskAssessment | null;
  metadata: Record<string, unknown>;
}

/** Intent classification request */
export interface IntentClassifyRequest {
  content: string;
  include_risk_assessment?: boolean;
  context?: Record<string, unknown>;
}

// =============================================================================
// Types - Guided Dialog
// =============================================================================

/** Dialog question */
export interface DialogQuestion {
  question_id: string;
  question: string;
  field_name: string;
  options: string[] | null;
  required: boolean;
}

/** Dialog status response */
export interface DialogStatusResponse {
  dialog_id: string;
  status: 'active' | 'completed' | 'cancelled';
  needs_more_info: boolean;
  message: string | null;
  questions: DialogQuestion[] | null;
  current_intent: string | null;
  completeness_score: number;
  turn_count: number;
  created_at: string;
  updated_at: string;
}

/** Start dialog request */
export interface StartDialogRequest {
  content: string;
  user_id?: string;
  session_id?: string;
  initial_context?: Record<string, unknown>;
}

/** Respond to dialog request */
export interface RespondToDialogRequest {
  responses: Record<string, unknown>;
  additional_message?: string;
}

// =============================================================================
// Types - HITL Approvals
// =============================================================================

/** Approval summary */
export interface ApprovalSummary {
  approval_id: string;
  status: 'pending' | 'approved' | 'rejected' | 'expired';
  requester: string;
  intent_category: string | null;
  risk_level: string | null;
  created_at: string;
  expires_at: string | null;
}

/** Approval list response */
export interface ApprovalListResponse {
  approvals: ApprovalSummary[];
  total: number;
}

/** Approval decision request */
export interface ApprovalDecisionRequest {
  decision: 'approve' | 'reject';
  reason?: string;
  approver?: string;
}

/** Approval decision response */
export interface ApprovalDecisionResponse {
  approval_id: string;
  status: string;
  decision: string;
  decided_at: string;
  decided_by: string | null;
}

// =============================================================================
// Types - Hybrid Execute
// =============================================================================

/** Hybrid execute request */
export interface HybridExecuteRequest {
  input_text: string;
  session_id?: string;
  force_mode?: 'workflow' | 'chat' | 'hybrid';
  tools?: Record<string, unknown>[];
  max_tokens?: number;
  timeout?: number;
  context?: Record<string, unknown>;
}

/** Hybrid execute response */
export interface HybridExecuteResponse {
  success: boolean;
  content: string;
  error: string | null;
  framework_used: string;
  execution_mode: string;
  session_id: string | null;
  intent_analysis: Record<string, unknown> | null;
  tool_results: Record<string, unknown>[];
  duration: number;
  tokens_used: number;
  metadata: Record<string, unknown>;
}

// =============================================================================
// Orchestration API Client
// =============================================================================

export const orchestrationApi = {
  // ===========================================================================
  // Intent Routing
  // ===========================================================================

  /**
   * Classify user intent using three-layer routing
   */
  classify: (request: IntentClassifyRequest): Promise<IntentClassifyResponse> =>
    api.post<IntentClassifyResponse>('/orchestration/intent/classify', request),

  /**
   * Quick classification (pattern layer only)
   */
  quickClassify: async (content: string): Promise<RoutingDecision> => {
    const response = await api.post<{ routing_decision: RoutingDecision }>(
      '/orchestration/intent/quick',
      { content }
    );
    return response.routing_decision;
  },

  // ===========================================================================
  // Guided Dialog
  // ===========================================================================

  /**
   * Start a guided dialog session
   */
  startDialog: (request: StartDialogRequest): Promise<DialogStatusResponse> =>
    api.post<DialogStatusResponse>('/orchestration/dialog/start', request),

  /**
   * Respond to dialog questions
   */
  respondToDialog: (
    dialogId: string,
    request: RespondToDialogRequest
  ): Promise<DialogStatusResponse> =>
    api.post<DialogStatusResponse>(`/orchestration/dialog/${dialogId}/respond`, request),

  /**
   * Get dialog status
   */
  getDialogStatus: (dialogId: string): Promise<DialogStatusResponse> =>
    api.get<DialogStatusResponse>(`/orchestration/dialog/${dialogId}/status`),

  /**
   * Cancel dialog session
   */
  cancelDialog: (dialogId: string): Promise<void> =>
    api.delete(`/orchestration/dialog/${dialogId}`),

  // ===========================================================================
  // Risk Assessment
  // ===========================================================================

  /**
   * Assess risk for an intent
   */
  assessRisk: (
    intentCategory: string,
    subIntent?: string,
    context?: Record<string, unknown>
  ): Promise<RiskAssessment> =>
    api.post<RiskAssessment>('/orchestration/risk/assess', {
      intent_category: intentCategory,
      sub_intent: subIntent,
      context,
    }),

  // ===========================================================================
  // HITL Approvals
  // ===========================================================================

  /**
   * List pending approvals
   */
  listApprovals: (): Promise<ApprovalListResponse> =>
    api.get<ApprovalListResponse>('/orchestration/approvals'),

  /**
   * Submit approval decision
   */
  submitDecision: (
    approvalId: string,
    request: ApprovalDecisionRequest
  ): Promise<ApprovalDecisionResponse> =>
    api.post<ApprovalDecisionResponse>(
      `/orchestration/approvals/${approvalId}/decision`,
      request
    ),

  // ===========================================================================
  // Hybrid Execute
  // ===========================================================================

  /**
   * Execute using hybrid orchestrator
   */
  execute: (request: HybridExecuteRequest): Promise<HybridExecuteResponse> =>
    api.post<HybridExecuteResponse>('/hybrid/execute', request),

  // ===========================================================================
  // Metrics & Health
  // ===========================================================================

  /**
   * Get orchestration metrics
   */
  getMetrics: (): Promise<Record<string, unknown>> =>
    api.get<Record<string, unknown>>('/orchestration/metrics'),

  /**
   * Check orchestration health
   */
  checkHealth: (): Promise<{ status: string; policies_loaded: number }> =>
    api.get<{ status: string; policies_loaded: number }>('/orchestration/health'),
};

export default orchestrationApi;

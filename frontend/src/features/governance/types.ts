/**
 * File: frontend/src/features/governance/types.ts
 * Purpose: Shared types mirroring backend ApprovalSummaryDTO (Sprint 53.5 US-1).
 * Category: Frontend / governance / types
 * Scope: Phase 53 / Sprint 53.5 US-1
 *
 * Created: 2026-05-04 (Sprint 53.5 Day 3)
 *
 * Related:
 *   - backend/src/api/v1/governance/router.py (ApprovalSummaryDTO)
 *   - backend/src/agent_harness/_contracts/hitl.py (RiskLevel / DecisionType)
 */

export type RiskLevelLabel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type DecisionLabel = "approved" | "rejected" | "escalated";

export type ApprovalSummary = {
  request_id: string;
  tenant_id: string;
  session_id: string;
  requester: string;
  risk_level: RiskLevelLabel;
  payload: {
    tool_name?: string;
    tool_arguments?: Record<string, unknown>;
    reason?: string;
    summary?: string;
    [key: string]: unknown;
  };
  sla_deadline: string; // ISO 8601
  context_snapshot: Record<string, unknown>;
};

export type PendingListResponse = {
  items: ApprovalSummary[];
  count: number;
};

export type DecisionResponse = {
  request_id: string;
  decision: string;
  reviewer: string;
};

/**
 * File: frontend/src/features/governance/services/governanceService.ts
 * Purpose: REST client for HITL approval endpoints (list + decide).
 * Category: Frontend / governance / services
 * Scope: Phase 53 / Sprint 53.5 US-1
 *
 * Description:
 *   Wraps GET /api/v1/governance/approvals + POST /api/v1/governance/approvals/{id}/decide.
 *   Authentication: Bearer JWT carried by the existing fetch credentials path
 *   (tenant + role enforcement happens server-side via TenantContextMiddleware
 *   and require_approver_role).
 *
 *   Errors are surfaced as `Error` with the HTTP status / detail; callers
 *   should display in their own UI.
 *
 * Created: 2026-05-04 (Sprint 53.5 Day 3)
 *
 * Related:
 *   - backend/src/api/v1/governance/router.py
 *   - ../types.ts (ApprovalSummary / DecisionLabel)
 */

import type {
  ApprovalSummary,
  DecisionLabel,
  DecisionResponse,
  PendingListResponse,
} from "../types";

const API_BASE = "/api/v1/governance";

async function _handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // ignore JSON parse failure; use status only
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

export const governanceService = {
  /** List pending approvals for the current JWT tenant. */
  async listPending(signal?: AbortSignal): Promise<ApprovalSummary[]> {
    const response = await fetch(`${API_BASE}/approvals`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      signal,
    });
    const body = await _handleResponse<PendingListResponse>(response);
    return body.items;
  },

  /** Apply a reviewer decision. */
  async decide(
    requestId: string,
    decision: DecisionLabel,
    reason?: string,
    signal?: AbortSignal,
  ): Promise<DecisionResponse> {
    const response = await fetch(`${API_BASE}/approvals/${requestId}/decide`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ decision, reason: reason ?? null }),
      signal,
    });
    return _handleResponse<DecisionResponse>(response);
  },
};

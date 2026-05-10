/**
 * File: frontend/src/features/verification/services/verificationService.ts
 * Purpose: REST client for /api/v1/verification/{recent,*correction-trace} — auditor-RBAC + JWT tenant scoped.
 * Category: Frontend / verification / services
 * Scope: Phase 57 / Sprint 57.11 Day 2 / US-3
 *
 * Description:
 *   Wraps two backend verification endpoints (Sprint 57.11 US-2):
 *
 *   - GET /api/v1/verification/recent
 *       Paginated verification_log read scoped to the JWT tenant. Filters:
 *       session_id, verifier_type, passed. Cursor pagination via offset +
 *       limit; response carries total + has_more + next_offset.
 *
 *   - GET /api/v1/verification/{session_id}/correction-trace
 *       Full sorted trace for one session. 404 if no entries (no
 *       cross-tenant existence reveal per multi-tenant 鐵律).
 *
 *   Mirrors `auditService.ts` style: fetchWithAuth (D-PRE-3 — exported from
 *   authService.ts:74; NOT separate fetchWithAuth.ts file), URLSearchParams
 *   omit-undefined helper, JSON error surface (Error with detail).
 *
 *   403 forbidden = auditor RBAC denial — UI must show clear message
 *   rather than raw HTTP 403.
 *
 * Created: 2026-05-10 (Sprint 57.11 Day 2 / US-3)
 *
 * Modification History (newest-first):
 *   - 2026-05-10: Initial creation (Sprint 57.11 Day 2 / US-3)
 *
 * Related:
 *   - backend/src/api/v1/verification.py (Pydantic DTOs)
 *   - ../types.ts (VerificationLogPage / VerificationLogFilter / CorrectionTraceResponse)
 *   - ../../auth/services/authService.ts (fetchWithAuth helper)
 *   - ../../governance/services/auditService.ts (sibling pattern reference)
 */

import { fetchWithAuth } from "../../auth/services/authService";
import type {
  CorrectionTraceResponse,
  VerificationLogFilter,
  VerificationLogPage,
} from "../types";

const API_BASE = "/api/v1/verification";

/**
 * Build URLSearchParams from filter, omitting undefined / empty-string keys.
 * Mirrors Sprint 57.4 admin-tenants buildListSearchParams + Sprint 57.9
 * audit _buildAuditLogSearchParams pattern.
 */
function _buildVerificationSearchParams(filter: VerificationLogFilter): URLSearchParams {
  const params = new URLSearchParams();
  if (filter.session_id && filter.session_id.trim() !== "") {
    params.set("session_id", filter.session_id.trim());
  }
  if (filter.verifier_type) {
    params.set("verifier_type", filter.verifier_type);
  }
  if (filter.passed !== undefined) {
    params.set("passed", String(filter.passed));
  }
  params.set("limit", String(filter.limit));
  params.set("offset", String(filter.offset));
  return params;
}

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

export const verificationService = {
  /** Paginated verification_log read scoped to the JWT tenant. */
  async fetchVerificationRecent(
    filter: VerificationLogFilter,
    signal?: AbortSignal,
  ): Promise<VerificationLogPage> {
    const params = _buildVerificationSearchParams(filter);
    const url = `${API_BASE}/recent?${params.toString()}`;
    const response = await fetchWithAuth(url, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      signal,
    });
    return _handleResponse<VerificationLogPage>(response);
  },

  /** Full sorted trace for one session. 404 if no entries. */
  async fetchCorrectionTrace(
    sessionId: string,
    signal?: AbortSignal,
  ): Promise<CorrectionTraceResponse> {
    const url = `${API_BASE}/${sessionId}/correction-trace`;
    const response = await fetchWithAuth(url, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      signal,
    });
    return _handleResponse<CorrectionTraceResponse>(response);
  },
};

// Exported for unit tests so the URLSearchParams omit-undefined contract has
// direct coverage without going through the full fetch round-trip.
export const _testing = { _buildVerificationSearchParams };

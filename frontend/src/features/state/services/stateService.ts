/**
 * File: frontend/src/features/state/services/stateService.ts
 * Purpose: REST client for Cat 7 GET /api/v1/sessions/{id}/state (Sprint 57.19 US-B3).
 * Category: Frontend / state / services
 * Scope: Phase 57 / Sprint 57.19 Day 4 / US-C4
 *
 * Created: 2026-05-17 (Sprint 57.19 Day 4 / US-C4)
 *
 * Modification History (newest-first):
 *   - 2026-05-17: Initial creation (Sprint 57.19 Day 4 / US-C4)
 *
 * Related:
 *   - backend/src/api/v1/sessions.py
 *   - ../types.ts (StateSnapshot)
 *   - ../../auth/services/authService.ts (fetchWithAuth)
 */

import { fetchWithAuth } from "../../auth/services/authService";
import type { StateSnapshot } from "../types";

const API_BASE = "/api/v1";

async function _handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

export async function fetchStateSnapshot(
  sessionId: string,
  signal?: AbortSignal,
): Promise<StateSnapshot> {
  const response = await fetchWithAuth(
    `${API_BASE}/sessions/${encodeURIComponent(sessionId)}/state`,
    { method: "GET", signal },
  );
  return _handleResponse<StateSnapshot>(response);
}

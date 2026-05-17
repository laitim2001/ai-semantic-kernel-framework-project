/**
 * File: frontend/src/features/loops/services/loopsService.ts
 * Purpose: REST client for Cat 1 GET /api/v1/loops (Sprint 57.19 US-B1).
 * Category: Frontend / loops / services
 * Scope: Phase 57 / Sprint 57.19 Day 3 / US-C1
 *
 * Description:
 *   Wraps GET /api/v1/loops?status=running&cursor=...&limit=50. Uses
 *   `fetchWithAuth` so requests carry Sprint 57.7 IAM JWT (mirrors
 *   costService.ts pattern from Sprint 57.9 US-6 Day 4).
 *
 * Created: 2026-05-17 (Sprint 57.19 Day 3 / US-C1)
 *
 * Modification History (newest-first):
 *   - 2026-05-17: Initial creation (Sprint 57.19 Day 3 / US-C1)
 *
 * Related:
 *   - backend/src/api/v1/loops.py (endpoint — Sprint 57.19 US-B1)
 *   - ../types.ts (LoopsPage)
 *   - ../hooks/useActiveLoops.ts (TanStack consumer)
 *   - ../../auth/services/authService.ts (fetchWithAuth helper)
 */

import { fetchWithAuth } from "../../auth/services/authService";
import type { LoopsPage } from "../types";

const API_BASE = "/api/v1";

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

export interface FetchLoopsParams {
  status?: string;
  cursor?: string | null;
  limit?: number;
}

export async function fetchLoops(
  params: FetchLoopsParams = {},
  signal?: AbortSignal,
): Promise<LoopsPage> {
  const q = new URLSearchParams();
  if (params.status) q.set("status", params.status);
  if (params.cursor) q.set("cursor", params.cursor);
  if (params.limit) q.set("limit", String(params.limit));
  const qs = q.toString();
  const response = await fetchWithAuth(
    `${API_BASE}/loops${qs ? `?${qs}` : ""}`,
    { method: "GET", signal },
  );
  return _handleResponse<LoopsPage>(response);
}

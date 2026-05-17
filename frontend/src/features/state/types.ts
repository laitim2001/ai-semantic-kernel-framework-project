/**
 * File: frontend/src/features/state/types.ts
 * Purpose: TypeScript contracts for Cat 7 state snapshot endpoint (GET /api/v1/sessions/{id}/state).
 * Category: Frontend / state / types
 * Scope: Phase 57 / Sprint 57.19 Day 4 / US-C4
 *
 * Description:
 *   Mirrors `StateSnapshot` ORM exposed by backend/src/api/v1/sessions.py
 *   (Sprint 57.19 US-B3). Returns the LATEST snapshot for a session
 *   (single row, ORDER BY version DESC LIMIT 1) — no version-chain endpoint
 *   exists yet. Version chain is rendered from mockup fixture pending
 *   AD-State-VersionChain-Phase58.
 *
 * Created: 2026-05-17 (Sprint 57.19 Day 4 / US-C4)
 *
 * Modification History (newest-first):
 *   - 2026-05-17: Initial creation (Sprint 57.19 Day 4 / US-C4)
 *
 * Related:
 *   - backend/src/api/v1/sessions.py
 *   - backend/src/infrastructure/db/models/state.py
 *   - ./services/stateService.ts
 *   - ./hooks/useStateSnapshot.ts
 */

export interface StateSnapshot {
  session_id: string;
  tenant_id: string;
  version: number;
  parent_version: number | null;
  turn_num: number;
  state_data: Record<string, unknown>;
  state_hash: string;
  reason: string;
}

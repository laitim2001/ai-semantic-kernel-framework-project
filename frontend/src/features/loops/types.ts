/**
 * File: frontend/src/features/loops/types.ts
 * Purpose: TypeScript contracts for Cat 1 loops list endpoint (GET /api/v1/loops).
 * Category: Frontend / loops / types
 * Scope: Phase 57 / Sprint 57.19 Day 3 / US-C1
 *
 * Description:
 *   Mirrors backend `LoopItem` + `LoopsPage` Pydantic models in
 *   backend/src/api/v1/loops.py (Sprint 57.19 US-B1, Session ORM pivot).
 *
 *   IMPORTANT — backend gap awareness (per Sprint 57.19 US-B1 D-PRE-SCHEMA-2):
 *   The Session ORM table does NOT carry agent_name / max_turns / model fields;
 *   mockup ACTIVE_LOOPS row layout shows those columns so the frontend renders
 *   placeholder strings until a follow-up sprint adds Session.agent_name +
 *   Session.max_turns + Session.model (tracked as AD-Loop-Session-Enrich-Phase58).
 *
 * Created: 2026-05-17 (Sprint 57.19 Day 3 / US-C1)
 *
 * Modification History (newest-first):
 *   - 2026-05-17: Initial creation (Sprint 57.19 Day 3 / US-C1)
 *
 * Related:
 *   - backend/src/api/v1/loops.py (LoopItem + LoopsPage Pydantic models)
 *   - ./services/loopsService.ts (HTTP client)
 *   - ./hooks/useActiveLoops.ts (TanStack consumer)
 */

export interface Loop {
  session_id: string;
  status: string;
  started_at_ms: number;
  ended_at_ms: number | null;
  turn_count: number;
  token_usage: number;
  total_cost_usd: string; // Decimal serialized as string by Pydantic
}

export interface LoopsPage {
  items: Loop[];
  next_cursor: string | null;
  page_size: number;
}

export type LoopStatus = "running" | "ended" | "error" | "hitl-paused" | "verifying";

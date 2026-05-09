/**
 * File: frontend/src/features/verification/types.ts
 * Purpose: TypeScript types mirroring backend verification_log Pydantic DTOs + SSE event payloads.
 * Category: Frontend / verification / types
 * Scope: Phase 57 / Sprint 57.11 Day 2 / US-3
 *
 * Description:
 *   Single-source TS contract for verification feature folder consumed by:
 *     - services/verificationService.ts (REST DTOs)
 *     - hooks/useVerificationRecent.ts + useCorrectionTrace.ts (TanStack Query)
 *     - components/VerificationList.tsx + CorrectionTraceView.tsx (US-4)
 *     - components/VerificationPanel.tsx (US-5 chat-v2 inline)
 *
 *   Backend authority:
 *     - VerificationLogItem  ↔ backend Pydantic VerificationLogItem (api/v1/verification.py:55-86)
 *     - VerificationLogPage  ↔ VerificationLogPage (verification.py:89-95)
 *     - CorrectionTraceResponse ↔ CorrectionTraceResponse (verification.py:98-101)
 *     - VerificationEvent    ↔ SSE serialize_loop_event (api/v1/chat/sse.py:243-265)
 *       Two SSE event types: 'verification_passed' / 'verification_failed'
 *
 *   created_at_ms is Unix epoch milliseconds (backend converts datetime →
 *   epoch ms in `VerificationLogItem.from_row()`) for direct JS Date interop.
 *
 * Created: 2026-05-10 (Sprint 57.11 Day 2 / US-3)
 *
 * Modification History (newest-first):
 *   - 2026-05-10: Initial creation (Sprint 57.11 Day 2 / US-3)
 *
 * Related:
 *   - backend/src/api/v1/verification.py (Pydantic DTOs)
 *   - backend/src/api/v1/chat/sse.py:243-265 (SSE event schema)
 *   - sprint-57-11-plan.md §US-3
 */

export type VerifierType = "rules_based" | "llm_judge" | "external";

export interface VerificationLogItem {
  id: number;
  tenant_id: string;
  session_id: string;
  turn_index: number;
  verifier_name: string;
  verifier_type: VerifierType;
  passed: boolean;
  score: number | null;
  reason: string | null;
  suggested_correction: string | null;
  correction_attempt: number;
  created_at_ms: number;
}

export interface VerificationLogPage {
  items: VerificationLogItem[];
  total: number;
  has_more: boolean;
  next_offset: number | null;
  page_size: number;
}

/**
 * Filter shape consumed by useVerificationRecent + verificationService.
 * Optional fields are omitted from URLSearchParams when undefined / empty.
 */
export interface VerificationLogFilter {
  session_id?: string;
  verifier_type?: VerifierType;
  passed?: boolean;
  limit: number;
  offset: number;
}

export interface CorrectionTraceResponse {
  session_id: string;
  entries: VerificationLogItem[];
}

/**
 * SSE event payload mirror for chat-v2 inline VerificationPanel (US-5).
 * Discriminated union by `type`; data shape differs (failed carries
 * reason + suggested_correction, passed carries score).
 */
export type VerificationEvent =
  | {
      type: "verification_passed";
      data: {
        verifier: string;
        verifier_type: VerifierType;
        score: number | null;
      };
    }
  | {
      type: "verification_failed";
      data: {
        verifier: string;
        verifier_type: VerifierType;
        reason: string | null;
        suggested_correction: string | null;
      };
    };

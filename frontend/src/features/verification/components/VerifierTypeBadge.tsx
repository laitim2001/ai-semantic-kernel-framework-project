/**
 * File: frontend/src/features/verification/components/VerifierTypeBadge.tsx
 * Purpose: Visual badge for VerifierType with 3 color variants (shared by US-4 list + US-5 inline panel).
 * Category: Frontend / verification / components
 * Scope: Phase 57 / Sprint 57.11 Day 2 / US-3 + US-4
 *
 * Description:
 *   Tailwind-only utility classes per .claude/rules/frontend-react.md (no
 *   inline styles). 3 variants:
 *     - rules_based → blue
 *     - llm_judge   → purple
 *     - external    → gray
 *
 * Created: 2026-05-10 (Sprint 57.11 Day 2 / US-3 + US-4)
 *
 * Related:
 *   - ../types.ts (VerifierType)
 *   - VerificationList.tsx (US-4 consumer)
 *   - VerificationPanel.tsx (US-5 consumer)
 */

import type { VerifierType } from "../types";

const VARIANT_CLASSES: Record<VerifierType, string> = {
  rules_based: "bg-blue-100 text-blue-800",
  llm_judge: "bg-purple-100 text-purple-800",
  external: "bg-gray-100 text-gray-800",
};

const LABELS: Record<VerifierType, string> = {
  rules_based: "Rules",
  llm_judge: "LLM Judge",
  external: "External",
};

export interface VerifierTypeBadgeProps {
  type: VerifierType;
}

export function VerifierTypeBadge({ type }: VerifierTypeBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${VARIANT_CLASSES[type]}`}
      data-testid={`verifier-type-badge-${type}`}
    >
      {LABELS[type]}
    </span>
  );
}

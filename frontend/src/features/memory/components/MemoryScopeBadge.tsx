/**
 * File: frontend/src/features/memory/components/MemoryScopeBadge.tsx
 * Purpose: Visual badge for MemoryLayer with 5 color variants (shared by MemoryRecentList + MemoryByScopeBrowser).
 * Category: Frontend / memory / components
 * Scope: Phase 57 / Sprint 57.12 Day 2 / US-3 + US-5
 *
 * Description:
 *   Tailwind-only utility classes per .claude/rules/frontend-react.md + STYLE.md
 *   §3. 5 variants (one per Cat 3 layer):
 *     - system  → indigo (cross-tenant; auditor-only)
 *     - tenant  → blue
 *     - role    → teal
 *     - user    → green
 *     - session → amber
 *
 *   Mirrors VerifierTypeBadge.tsx (Sprint 57.11) pattern.
 *
 * Created: 2026-05-10 (Sprint 57.12 Day 2 / US-3 + US-5)
 *
 * Related:
 *   - ../types.ts (MemoryLayer)
 *   - MemoryRecentList.tsx (US-5 consumer)
 *   - MemoryByScopeBrowser.tsx (US-5 consumer)
 *   - frontend/src/features/verification/components/VerifierTypeBadge.tsx (sibling pattern)
 */

import type { MemoryLayer } from "../types";

const VARIANT_CLASSES: Record<MemoryLayer, string> = {
  system: "bg-indigo-100 text-indigo-800",
  tenant: "bg-blue-100 text-blue-800",
  role: "bg-teal-100 text-teal-800",
  user: "bg-green-100 text-green-800",
  session: "bg-amber-100 text-amber-800",
};

const LABELS: Record<MemoryLayer, string> = {
  system: "System",
  tenant: "Tenant",
  role: "Role",
  user: "User",
  session: "Session",
};

export interface MemoryScopeBadgeProps {
  layer: MemoryLayer;
}

export function MemoryScopeBadge({ layer }: MemoryScopeBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${VARIANT_CLASSES[layer]}`}
      data-testid={`memory-scope-badge-${layer}`}
    >
      {LABELS[layer]}
    </span>
  );
}

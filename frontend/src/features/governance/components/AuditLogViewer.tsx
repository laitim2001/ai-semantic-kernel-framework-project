/**
 * File: frontend/src/features/governance/components/AuditLogViewer.tsx
 * Purpose: Audit log paginated viewer with filter form + chain verify badge.
 * Category: Frontend / governance / components
 * Scope: Phase 57 / Sprint 57.9 US-4 Day 3 (stub created Day 1 for Routes import)
 *
 * Description:
 *   STUB only as of Sprint 57.9 Day 1 — exists so pages/governance/index.tsx
 *   <Route path="audit-log" element={<AuditLogViewer />}> import resolves +
 *   TypeScript strict pass during Day 1 (US-1).
 *
 *   Real implementation lands in Sprint 57.9 Day 3 (US-4):
 *   - Filter form (4 fields: operation / resource_type / user_id / date range)
 *   - Paginated table consuming /api/v1/audit/log via useAuditLog hook
 *   - <AuditChainBadge /> mounted top-right (US-5)
 *
 * Created: 2026-05-09 (Sprint 57.9 Day 1 stub)
 *
 * Modification History (newest-first):
 *   - 2026-05-09: Initial creation as Day 1 stub (Sprint 57.9 US-1 enabler;
 *     real impl Day 3 US-4)
 *
 * Related:
 *   - sprint-57-9-plan.md §US-4 (audit log viewer real impl scope)
 *   - sprint-57-9-plan.md §US-5 (chain badge mount target)
 */

export function AuditLogViewer() {
  return (
    <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
      <p className="font-semibold">Audit Log Viewer</p>
      <p className="mt-1">
        Sprint 57.9 Day 3 (US-4) will replace this stub with the real implementation
        — filter form + paginated table consuming <code>/api/v1/audit/log</code>.
      </p>
    </div>
  );
}

/**
 * File: frontend/src/features/tenant-settings/components/tabs/HITLPoliciesTab.tsx
 * Purpose: HITL policies tab — risk-tiered approval policy table (real backend via useHITLPolicies).
 * Category: Frontend / tenant-settings / components / tabs
 * Scope: Phase 57 / Sprint 57.49 Day 1 (Track A 1.1.4 — fixture → real backend migration)
 *
 * Description:
 *   Sprint 57.49 migration: previously consumed `HITL_POLICIES` from `_fixtures.ts`;
 *   now fetches via `useHITLPolicies(tenantId)` hook (Sprint 57.48 Track A endpoint).
 *
 *   Backend HITLPolicyItem shape: `{risk: "LOW"|"MEDIUM"|"HIGH"|"CRITICAL",
 *   policy: "auto"|"ask_once"|"always_ask", sla_seconds, reviewers}`. Fields
 *   missing vs mockup fixture: `off` (off-platform channels) — render empty
 *   array stub. `risk` toLowerCase'd for sev-dot CSS class match.
 *
 *   Loading/Empty/Error states added; BackendGapBanner kept for honesty
 *   (off-platform channels Phase 58+).
 *
 * Created: 2026-05-26 (Sprint 57.44 Day 1) — original fixture port
 * Last Modified: 2026-05-26
 *
 * Modification History (newest-first):
 *   - 2026-05-26: Sprint 57.49 — fixture → useHITLPolicies real backend (Sprint 57.48 Track A)
 *   - 2026-05-26: Initial creation (Sprint 57.44 Day 1)
 *
 * Related:
 *   - backend/src/api/v1/admin/tenants.py L675-790 (HITLPolicyItem / list_tenant_hitl_policies)
 *   - ../../hooks/useHITLPolicies.ts (TanStack consumer)
 */

import { Badge, Card } from "../../../../components/mockup-ui";
import { BackendGapBanner } from "../../../../components/ui/BackendGapBanner";
import { useHITLPolicies } from "../../hooks/useHITLPolicies";

export interface HITLPoliciesTabProps {
  tenantId: string;
}

function policyTone(policy: string): string {
  if (policy === "auto") return "success";
  if (policy === "ask_once") return "info";
  return "warning";
}

function formatSla(sla_seconds: number | null): string {
  if (sla_seconds === null || sla_seconds === undefined) return "—";
  if (sla_seconds < 60) return `${sla_seconds}s`;
  if (sla_seconds < 3600) return `${Math.round(sla_seconds / 60)}m`;
  return `${Math.round(sla_seconds / 3600)}h`;
}

export function HITLPoliciesTab({ tenantId }: HITLPoliciesTabProps): JSX.Element {
  const { data, isLoading, error } = useHITLPolicies(tenantId);

  if (isLoading) {
    return (
      <Card title="HITL policies" subtitle="Per-tool · risk-tiered · escalation routing">
        <p className="muted">Loading HITL policies…</p>
      </Card>
    );
  }

  if (error) {
    return (
      <Card title="HITL policies" subtitle="Per-tool · risk-tiered · escalation routing">
        {/* eslint-disable-next-line no-restricted-syntax -- inline-style error hint */}
        <p style={{ color: "var(--danger)", fontSize: 12 }}>
          Error loading HITL policies: {error.message}
        </p>
      </Card>
    );
  }

  const items = data?.items ?? [];

  return (
    <Card title="HITL policies" subtitle="Per-tool · risk-tiered · escalation routing">
      <BackendGapBanner reason="Off-platform channel routing + policy edit API: backend extension Phase 58+ — risk/policy/SLA shown are tenant-effective" />
      {items.length === 0 ? (
        <p className="muted">No HITL policy override configured. Platform defaults apply.</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Risk tier</th>
              <th>Default policy</th>
              <th>SLA</th>
              <th>Approvers</th>
              <th>Off-platform</th>
            </tr>
          </thead>
          <tbody>
            {items.map((p) => {
              const riskLower = p.risk.toLowerCase();
              return (
                <tr key={p.risk}>
                  <td>
                    {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: row gap */}
                    <span className="row" style={{ gap: 6 }}>
                      <span className={`sev-dot sev-${riskLower}`} />
                      {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: fontSize + capitalize */}
                      <span style={{ fontSize: 12, textTransform: "capitalize" }}>{riskLower}</span>
                    </span>
                  </td>
                  <td><Badge tone={policyTone(p.policy)}>{p.policy}</Badge></td>
                  <td className="mono">{formatSla(p.sla_seconds)}</td>
                  {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: mono subtle fontSize */}
                  <td className="mono subtle" style={{ fontSize: 11.5 }}>{p.reviewers || "—"}</td>
                  <td>
                    <span className="subtle">—</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </Card>
  );
}

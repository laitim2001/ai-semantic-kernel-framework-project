/**
 * File: frontend/src/features/tenant-settings/components/tabs/HITLPoliciesTab.tsx
 * Purpose: HITL policies tab — risk-tiered approval policy table with edit mode (real backend persistence).
 * Category: Frontend / tenant-settings / components / tabs
 * Scope: Phase 57 / Sprint 57.54 Track B (edit mode + useHITLPoliciesSave wiring)
 *
 * Description:
 *   Read side: useHITLPolicies(tenantId) → projected items list (Sprint 57.49).
 *   Write side (Sprint 57.54): Edit button toggles edit form for the composite
 *   HITLPolicy (auto_approve_max_risk + require_approval_min_risk + per-risk
 *   reviewer_groups + per-risk sla_seconds). Save invokes useHITLPoliciesSave
 *   mutation → PUT /admin/tenants/{id}/hitl-policies → query invalidation
 *   refreshes the table.
 *
 *   Per-risk reviewers entered as CSV (split on comma into list[str]); per-risk
 *   SLA seconds entered as integer (positive int validated by backend).
 *
 *   AP-2 BackendGapBanner copy updated: off-platform channel routing remains
 *   Phase 58+; risk/policy/SLA now editable.
 *
 * Created: 2026-05-26 (Sprint 57.44 Day 1) — original fixture port
 * Last Modified: 2026-05-26
 *
 * Modification History (newest-first):
 *   - 2026-05-26: Sprint 57.54 — add edit mode (useHITLPoliciesSave + form + soften BackendGapBanner copy)
 *   - 2026-05-26: Sprint 57.49 — fixture → useHITLPolicies real backend (Sprint 57.48 Track A)
 *   - 2026-05-26: Initial creation (Sprint 57.44 Day 1)
 *
 * Related:
 *   - backend/src/api/v1/admin/tenants.py L795-877 (HITLPolicyUpsertRequest / upsert_tenant_hitl_policies)
 *   - ../../hooks/useHITLPolicies.ts (read TanStack consumer)
 *   - ../../hooks/useHITLPoliciesSave.ts (write TanStack consumer)
 */

import { useEffect, useState } from "react";

import { Badge, Card } from "../../../../components/mockup-ui";
import { BackendGapBanner } from "../../../../components/ui/BackendGapBanner";
import { useHITLPolicies } from "../../hooks/useHITLPolicies";
import { useHITLPoliciesSave } from "../../hooks/useHITLPoliciesSave";
import type { HITLPolicyUpsertRequest, RiskLevelName } from "../../types";

export interface HITLPoliciesTabProps {
  tenantId: string;
}

const RISK_LEVELS: readonly RiskLevelName[] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const;

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

function defaultDraft(): HITLPolicyUpsertRequest {
  return {
    auto_approve_max_risk: "LOW",
    require_approval_min_risk: "MEDIUM",
    reviewer_groups_by_risk: {},
    sla_seconds_by_risk: {},
  };
}

/**
 * Reconstruct composite HITLPolicy draft from projected items list.
 *
 * Backend GET projects the composite to a 4-row items list (one per risk
 * tier); we reverse-project to populate the edit form's composite state.
 *
 * Heuristics:
 *   - auto_approve_max_risk = highest risk tier whose row policy == "auto"
 *     (defaults to "LOW" if no row marked "auto")
 *   - require_approval_min_risk = lowest risk tier whose row policy == "always_ask"
 *     (defaults to "MEDIUM" if no row marked "always_ask")
 *   - reviewer_groups_by_risk[risk] = csv.split(",") for each non-empty reviewers
 *   - sla_seconds_by_risk[risk] = sla_seconds for each non-null sla_seconds
 */
function draftFromItems(items: ReadonlyArray<{ risk: string; policy: string; sla_seconds: number | null; reviewers: string }>): HITLPolicyUpsertRequest {
  const draft = defaultDraft();
  const riskOrder: Record<string, number> = { LOW: 0, MEDIUM: 1, HIGH: 2, CRITICAL: 3 };

  // Find highest "auto" risk
  let autoMaxIdx = -1;
  let alwaysMinIdx = 4;
  for (const item of items) {
    const idx = riskOrder[item.risk] ?? -1;
    if (idx < 0) continue;
    if (item.policy === "auto" && idx > autoMaxIdx) autoMaxIdx = idx;
    if (item.policy === "always_ask" && idx < alwaysMinIdx) alwaysMinIdx = idx;

    if (item.reviewers && item.reviewers.trim().length > 0) {
      draft.reviewer_groups_by_risk[item.risk] = item.reviewers
        .split(",")
        .map((s) => s.trim())
        .filter((s) => s.length > 0);
    }
    if (item.sla_seconds !== null && item.sla_seconds !== undefined) {
      draft.sla_seconds_by_risk[item.risk] = item.sla_seconds;
    }
  }
  if (autoMaxIdx >= 0) draft.auto_approve_max_risk = RISK_LEVELS[autoMaxIdx];
  if (alwaysMinIdx <= 3) draft.require_approval_min_risk = RISK_LEVELS[alwaysMinIdx];
  return draft;
}

export function HITLPoliciesTab({ tenantId }: HITLPoliciesTabProps): JSX.Element {
  const { data, isLoading, error } = useHITLPolicies(tenantId);
  const saveMutation = useHITLPoliciesSave(tenantId);

  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<HITLPolicyUpsertRequest | null>(null);

  // Reset on tenant switch
  useEffect(() => {
    setEditing(false);
    setDraft(null);
    saveMutation.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- mutation reset on tenant switch only
  }, [tenantId]);

  // Auto-exit edit mode after successful save
  useEffect(() => {
    if (saveMutation.isSuccess && editing) {
      setEditing(false);
      setDraft(null);
    }
  }, [saveMutation.isSuccess, editing]);

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

  const handleEdit = (): void => {
    setDraft(draftFromItems(items));
    setEditing(true);
    saveMutation.reset();
  };

  const handleCancel = (): void => {
    setDraft(null);
    setEditing(false);
    saveMutation.reset();
  };

  const handleSave = (): void => {
    if (draft) saveMutation.mutate(draft);
  };

  const updateRiskThreshold = (
    field: "auto_approve_max_risk" | "require_approval_min_risk",
    value: RiskLevelName,
  ): void => {
    setDraft((d) => (d ? { ...d, [field]: value } : d));
  };

  const updateReviewers = (risk: RiskLevelName, csv: string): void => {
    setDraft((d) => {
      if (!d) return d;
      const next = { ...d.reviewer_groups_by_risk };
      const parsed = csv.split(",").map((s) => s.trim()).filter((s) => s.length > 0);
      if (parsed.length === 0) {
        delete next[risk];
      } else {
        next[risk] = parsed;
      }
      return { ...d, reviewer_groups_by_risk: next };
    });
  };

  const updateSla = (risk: RiskLevelName, value: string): void => {
    setDraft((d) => {
      if (!d) return d;
      const next = { ...d.sla_seconds_by_risk };
      const parsed = parseInt(value, 10);
      if (!Number.isFinite(parsed) || parsed <= 0) {
        delete next[risk];
      } else {
        next[risk] = parsed;
      }
      return { ...d, sla_seconds_by_risk: next };
    });
  };

  return (
    <Card title="HITL policies" subtitle="Per-tool · risk-tiered · escalation routing">
      <BackendGapBanner reason="Off-platform channel routing (Slack/email/SMS): Phase 58+ — risk/policy/SLA shown are tenant-effective + editable via Edit button" />

      {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: row flex gap */}
      <div className="row" style={{ gap: 8, marginBottom: 12, justifyContent: "flex-end" }}>
        {!editing ? (
          <button
            type="button"
            className="btn-secondary"
            onClick={handleEdit}
            data-testid="hitl-edit-btn"
          >
            Edit
          </button>
        ) : (
          <>
            <button
              type="button"
              className="btn-secondary"
              onClick={handleCancel}
              disabled={saveMutation.isPending}
              data-testid="hitl-cancel-btn"
            >
              Cancel
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={handleSave}
              disabled={saveMutation.isPending || !draft}
              data-testid="hitl-save-btn"
            >
              {saveMutation.isPending ? "Saving…" : "Save"}
            </button>
          </>
        )}
      </div>

      {saveMutation.error ? (
        // eslint-disable-next-line no-restricted-syntax -- inline-style error hint
        <p style={{ color: "var(--danger)", fontSize: 12, marginBottom: 8 }} data-testid="hitl-save-error">
          Save failed: {saveMutation.error.message}
        </p>
      ) : null}

      {editing && draft ? (
        <div data-testid="hitl-edit-form">
          {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: form layout */}
          <div className="row" style={{ gap: 16, marginBottom: 12, flexWrap: "wrap" }}>
            <label className="field">
              {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: label fontSize */}
              <span className="subtle" style={{ fontSize: 12 }}>Auto-approve max risk</span>
              <select
                value={draft.auto_approve_max_risk}
                onChange={(e) => updateRiskThreshold("auto_approve_max_risk", e.target.value as RiskLevelName)}
                data-testid="hitl-auto-approve-select"
              >
                {RISK_LEVELS.map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </label>
            <label className="field">
              {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: label fontSize */}
              <span className="subtle" style={{ fontSize: 12 }}>Require-approval min risk</span>
              <select
                value={draft.require_approval_min_risk}
                onChange={(e) => updateRiskThreshold("require_approval_min_risk", e.target.value as RiskLevelName)}
                data-testid="hitl-require-approval-select"
              >
                {RISK_LEVELS.map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </label>
          </div>

          <table className="table">
            <thead>
              <tr>
                <th>Risk tier</th>
                <th>Reviewer groups (comma-separated)</th>
                <th>SLA seconds</th>
              </tr>
            </thead>
            <tbody>
              {RISK_LEVELS.map((risk) => (
                <tr key={risk}>
                  <td>
                    {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: row gap */}
                    <span className="row" style={{ gap: 6 }}>
                      <span className={`sev-dot sev-${risk.toLowerCase()}`} />
                      {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: fontSize + capitalize */}
                      <span style={{ fontSize: 12, textTransform: "capitalize" }}>{risk.toLowerCase()}</span>
                    </span>
                  </td>
                  <td>
                    <input
                      type="text"
                      value={(draft.reviewer_groups_by_risk[risk] ?? []).join(", ")}
                      onChange={(e) => updateReviewers(risk, e.target.value)}
                      placeholder="@platform-l1, @platform-l2"
                      data-testid={`hitl-reviewers-${risk}`}
                      // eslint-disable-next-line no-restricted-syntax -- verbatim port: input width
                      style={{ width: "100%", fontSize: 12 }}
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      min="1"
                      value={draft.sla_seconds_by_risk[risk] ?? ""}
                      onChange={(e) => updateSla(risk, e.target.value)}
                      placeholder="—"
                      data-testid={`hitl-sla-${risk}`}
                      // eslint-disable-next-line no-restricted-syntax -- verbatim port: input width
                      style={{ width: 100, fontSize: 12 }}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : items.length === 0 ? (
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

/**
 * File: frontend/src/features/tenant-settings/components/tabs/HarnessPolicyTab.tsx
 * Purpose: Harness Policy tab — view/edit the tenant's guardrail-escalation, verification, and risky-action policy.
 * Category: Frontend / tenant-settings / components / tabs
 * Scope: Phase 57 / Sprint 57.106 C3 (Harness Policy tab)
 *
 * Description:
 *   Read side: useHarnessPolicy(tenantId) → GET /admin/tenants/{id}/harness-policy
 *   (sparse: unset fields render "System default").
 *
 *   Write side: Edit button toggles edit mode. The 9 fields render type-aware
 *   editors: the 5 list fields (escalate_*_phrases / escalate_tools /
 *   risky_action_extra_patterns) use comma-or-newline text inputs (parsed to
 *   string[] on save; blank input = null/cleared); verification_mode uses a
 *   select (System default / enabled / disabled); verification_judge_template a
 *   select of the 5 shipped names + System default; the two booleans
 *   (verification_escalate_on_max / risky_action_enabled) tri-state selects
 *   (System default / on / off). Save invokes useHarnessPolicySave → PUT
 *   (composite-replace: the FULL desired policy; "System default" selections →
 *   null, cleared server-side). A 422 (`detail` string — unknown template /
 *   bad/oversize regex / >20 patterns / invalid mode) surfaces inline via the
 *   same error banner pattern as ModelPolicyTab. Cancel restores the loaded
 *   policy and exits.
 *
 *   Mirrors the ModelPolicyTab view/edit structure (Sprint 57.104 C1).
 *
 * Created: 2026-06-12 (Sprint 57.106 C3)
 *
 * Modification History (newest-first):
 *   - 2026-06-12: Initial creation (Sprint 57.106 C3)
 *
 * Related:
 *   - backend GET/PUT /admin/tenants/{id}/harness-policy
 *   - ../../hooks/useHarnessPolicy.ts + useHarnessPolicySave.ts (read/write)
 *   - ./ModelPolicyTab.tsx (view/edit pattern authority)
 */

import { useEffect, useState } from "react";

import { Card } from "../../../../components/mockup-ui";
import { useHarnessPolicy } from "../../hooks/useHarnessPolicy";
import { useHarnessPolicySave } from "../../hooks/useHarnessPolicySave";
import type {
  HarnessJudgeTemplate,
  HarnessPolicy,
  HarnessVerificationMode,
} from "../../types";

export interface HarnessPolicyTabProps {
  tenantId: string;
}

/** The 5 shipped judge templates (mirrors backend allow-list). */
const JUDGE_TEMPLATES: ReadonlyArray<HarnessJudgeTemplate> = [
  "factual_consistency",
  "format_compliance",
  "output_quality",
  "pii_leak_check",
  "safety_review",
];

/**
 * Edit draft: every field a string so the form controls are always controlled.
 * - list fields: comma/newline-joined text ("" = cleared → null)
 * - verification_mode: "" | "enabled" | "disabled"   ("" = System default)
 * - verification_judge_template: "" | one of JUDGE_TEMPLATES
 * - boolean fields: "" | "true" | "false"             ("" = System default)
 */
interface HarnessPolicyDraft {
  escalateInputPhrases: string;
  escalateBetweenTurnsPhrases: string;
  escalateOutputPhrases: string;
  escalateTools: string;
  verificationMode: "" | HarnessVerificationMode;
  verificationJudgeTemplate: "" | HarnessJudgeTemplate;
  verificationEscalateOnMax: "" | "true" | "false";
  riskyActionEnabled: "" | "true" | "false";
  riskyActionExtraPatterns: string;
}

const EMPTY_DRAFT: HarnessPolicyDraft = {
  escalateInputPhrases: "",
  escalateBetweenTurnsPhrases: "",
  escalateOutputPhrases: "",
  escalateTools: "",
  verificationMode: "",
  verificationJudgeTemplate: "",
  verificationEscalateOnMax: "",
  riskyActionEnabled: "",
  riskyActionExtraPatterns: "",
};

/** The 5 list fields in display order — label + testid suffix + draft key. */
const LIST_FIELDS: ReadonlyArray<{
  key: keyof Pick<
    HarnessPolicyDraft,
    | "escalateInputPhrases"
    | "escalateBetweenTurnsPhrases"
    | "escalateOutputPhrases"
    | "escalateTools"
    | "riskyActionExtraPatterns"
  >;
  policyKey: keyof Pick<
    HarnessPolicy,
    | "escalateInputPhrases"
    | "escalateBetweenTurnsPhrases"
    | "escalateOutputPhrases"
    | "escalateTools"
    | "riskyActionExtraPatterns"
  >;
  label: string;
  testid: string;
}> = [
  {
    key: "escalateInputPhrases",
    policyKey: "escalateInputPhrases",
    label: "Escalate input phrases",
    testid: "escalate-input-phrases",
  },
  {
    key: "escalateBetweenTurnsPhrases",
    policyKey: "escalateBetweenTurnsPhrases",
    label: "Escalate between-turns phrases",
    testid: "escalate-between-turns-phrases",
  },
  {
    key: "escalateOutputPhrases",
    policyKey: "escalateOutputPhrases",
    label: "Escalate output phrases",
    testid: "escalate-output-phrases",
  },
  {
    key: "escalateTools",
    policyKey: "escalateTools",
    label: "Escalate tools",
    testid: "escalate-tools",
  },
  {
    key: "riskyActionExtraPatterns",
    policyKey: "riskyActionExtraPatterns",
    label: "Risky action extra patterns",
    testid: "risky-action-extra-patterns",
  },
];

/** Join a stored string[] for display in a text input (comma-separated). */
function listToText(list: string[] | null): string {
  return list && list.length > 0 ? list.join(", ") : "";
}

/** Parse a comma-or-newline text input to string[] (blank → null = cleared). */
function textToList(text: string): string[] | null {
  const items = text
    .split(/[,\n]/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
  return items.length > 0 ? items : null;
}

/** Tri-state select value → boolean | null ("" → null). */
function selectToBool(value: "" | "true" | "false"): boolean | null {
  if (value === "true") return true;
  if (value === "false") return false;
  return null;
}

/** boolean | null → tri-state select value. */
function boolToSelect(value: boolean | null): "" | "true" | "false" {
  if (value === true) return "true";
  if (value === false) return "false";
  return "";
}

/** Render a boolean | null for the read view. */
function boolToDisplay(value: boolean | null): string {
  if (value === true) return "On";
  if (value === false) return "Off";
  return "System default";
}

/** Seed an editable draft from the loaded policy (null → "" for controls). */
function draftFromPolicy(policy: HarnessPolicy | undefined): HarnessPolicyDraft {
  if (!policy) return { ...EMPTY_DRAFT };
  return {
    escalateInputPhrases: listToText(policy.escalateInputPhrases),
    escalateBetweenTurnsPhrases: listToText(policy.escalateBetweenTurnsPhrases),
    escalateOutputPhrases: listToText(policy.escalateOutputPhrases),
    escalateTools: listToText(policy.escalateTools),
    verificationMode: policy.verificationMode ?? "",
    verificationJudgeTemplate: policy.verificationJudgeTemplate ?? "",
    verificationEscalateOnMax: boolToSelect(policy.verificationEscalateOnMax),
    riskyActionEnabled: boolToSelect(policy.riskyActionEnabled),
    riskyActionExtraPatterns: listToText(policy.riskyActionExtraPatterns),
  };
}

/** Build the COMPLETE desired policy from a draft (composite-replace). */
function policyFromDraft(draft: HarnessPolicyDraft): HarnessPolicy {
  return {
    escalateInputPhrases: textToList(draft.escalateInputPhrases),
    escalateBetweenTurnsPhrases: textToList(draft.escalateBetweenTurnsPhrases),
    escalateOutputPhrases: textToList(draft.escalateOutputPhrases),
    escalateTools: textToList(draft.escalateTools),
    verificationMode: draft.verificationMode === "" ? null : draft.verificationMode,
    verificationJudgeTemplate:
      draft.verificationJudgeTemplate === "" ? null : draft.verificationJudgeTemplate,
    verificationEscalateOnMax: selectToBool(draft.verificationEscalateOnMax),
    riskyActionEnabled: selectToBool(draft.riskyActionEnabled),
    riskyActionExtraPatterns: textToList(draft.riskyActionExtraPatterns),
  };
}

export function HarnessPolicyTab({ tenantId }: HarnessPolicyTabProps): JSX.Element {
  const policyQuery = useHarnessPolicy(tenantId);
  const saveMutation = useHarnessPolicySave(tenantId);

  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<HarnessPolicyDraft>({ ...EMPTY_DRAFT });

  // Reset on tenant switch
  useEffect(() => {
    setEditing(false);
    setDraft({ ...EMPTY_DRAFT });
    saveMutation.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- mutation reset on tenant switch only
  }, [tenantId]);

  // Auto-exit edit mode after successful save
  useEffect(() => {
    if (saveMutation.isSuccess && editing) {
      setEditing(false);
    }
  }, [saveMutation.isSuccess, editing]);

  const policy = policyQuery.data;

  const handleEdit = (): void => {
    setDraft(draftFromPolicy(policy));
    setEditing(true);
    saveMutation.reset();
  };

  const handleCancel = (): void => {
    setDraft(draftFromPolicy(policy));
    setEditing(false);
    saveMutation.reset();
  };

  const handleSave = (): void => {
    saveMutation.mutate(policyFromDraft(draft));
  };

  const updateDraft = <K extends keyof HarnessPolicyDraft>(
    field: K,
    value: HarnessPolicyDraft[K],
  ): void => {
    setDraft((d) => ({ ...d, [field]: value }));
  };

  return (
    <div className="grid-main">
      <Card title="Harness policy">
        {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: row flex gap */}
        <div className="row" style={{ gap: 8, marginBottom: 12, justifyContent: "flex-end" }}>
          {!editing ? (
            <button
              type="button"
              className="btn-secondary"
              onClick={handleEdit}
              disabled={policyQuery.isLoading}
              data-testid="harness-policy-edit-btn"
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
                data-testid="harness-policy-cancel-btn"
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-primary"
                onClick={handleSave}
                disabled={saveMutation.isPending}
                data-testid="harness-policy-save-btn"
              >
                {saveMutation.isPending ? "Saving…" : "Save"}
              </button>
            </>
          )}
        </div>

        {saveMutation.error ? (
          // eslint-disable-next-line no-restricted-syntax -- inline-style error hint
          <p style={{ color: "var(--danger)", fontSize: 12, marginBottom: 8 }} data-testid="harness-policy-save-error">
            Save failed: {saveMutation.error.message}
          </p>
        ) : null}

        {policyQuery.isLoading ? (
          <p className="muted">Loading harness policy…</p>
        ) : policyQuery.error ? (
          // eslint-disable-next-line no-restricted-syntax -- inline-style error hint
          <p style={{ color: "var(--danger)", fontSize: 12 }} data-testid="harness-policy-load-error">
            Error loading harness policy: {policyQuery.error.message}
          </p>
        ) : (
          // eslint-disable-next-line no-restricted-syntax -- verbatim port: col gap
          <div className="col" style={{ gap: 14, marginTop: 8 }}>
            {/* === Guardrail escalation list fields (4 of 5 list fields) === */}
            {LIST_FIELDS.filter((f) => f.key !== "riskyActionExtraPatterns").map((field) => {
              const currentValue = policy ? policy[field.policyKey] : null;
              return (
                <div key={field.key} className="spread">
                  {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: fontSize */}
                  <span style={{ fontSize: 12.5 }}>{field.label}</span>
                  {editing ? (
                    <input
                      type="text"
                      value={draft[field.key]}
                      placeholder="System default (comma or newline separated)"
                      onChange={(e) => updateDraft(field.key, e.target.value)}
                      // eslint-disable-next-line no-restricted-syntax -- verbatim port: input sizing
                      style={{ width: 320, fontSize: 12, padding: "2px 6px" }}
                      data-testid={`harness-policy-input-${field.testid}`}
                      aria-label={`${field.label} override`}
                    />
                  ) : currentValue && currentValue.length > 0 ? (
                    // eslint-disable-next-line no-restricted-syntax -- verbatim port: mono fontSize
                    <span className="mono" style={{ fontSize: 11.5 }} data-testid={`harness-policy-value-${field.testid}`}>
                      {currentValue.join(", ")}
                    </span>
                  ) : (
                    <span className="subtle" data-testid={`harness-policy-value-${field.testid}`}>
                      System default
                    </span>
                  )}
                </div>
              );
            })}

            {/* === Verification mode (select) === */}
            <div className="spread">
              {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: fontSize */}
              <span style={{ fontSize: 12.5 }}>Verification mode</span>
              {editing ? (
                <select
                  value={draft.verificationMode}
                  onChange={(e) =>
                    updateDraft("verificationMode", e.target.value as HarnessPolicyDraft["verificationMode"])
                  }
                  data-testid="harness-policy-input-verification-mode"
                  aria-label="Verification mode override"
                >
                  <option value="">System default</option>
                  <option value="enabled">enabled</option>
                  <option value="disabled">disabled</option>
                </select>
              ) : policy?.verificationMode ? (
                // eslint-disable-next-line no-restricted-syntax -- verbatim port: mono fontSize
                <span className="mono" style={{ fontSize: 11.5 }} data-testid="harness-policy-value-verification-mode">
                  {policy.verificationMode}
                </span>
              ) : (
                <span className="subtle" data-testid="harness-policy-value-verification-mode">
                  System default
                </span>
              )}
            </div>

            {/* === Verification judge template (select) === */}
            <div className="spread">
              {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: fontSize */}
              <span style={{ fontSize: 12.5 }}>Verification judge template</span>
              {editing ? (
                <select
                  value={draft.verificationJudgeTemplate}
                  onChange={(e) =>
                    updateDraft(
                      "verificationJudgeTemplate",
                      e.target.value as HarnessPolicyDraft["verificationJudgeTemplate"],
                    )
                  }
                  data-testid="harness-policy-input-verification-judge-template"
                  aria-label="Verification judge template override"
                >
                  <option value="">System default</option>
                  {JUDGE_TEMPLATES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              ) : policy?.verificationJudgeTemplate ? (
                // eslint-disable-next-line no-restricted-syntax -- verbatim port: mono fontSize
                <span className="mono" style={{ fontSize: 11.5 }} data-testid="harness-policy-value-verification-judge-template">
                  {policy.verificationJudgeTemplate}
                </span>
              ) : (
                <span className="subtle" data-testid="harness-policy-value-verification-judge-template">
                  System default
                </span>
              )}
            </div>

            {/* === Verification escalate-on-max (tri-state boolean) === */}
            <div className="spread">
              {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: fontSize */}
              <span style={{ fontSize: 12.5 }}>Verification escalate on max</span>
              {editing ? (
                <select
                  value={draft.verificationEscalateOnMax}
                  onChange={(e) =>
                    updateDraft(
                      "verificationEscalateOnMax",
                      e.target.value as HarnessPolicyDraft["verificationEscalateOnMax"],
                    )
                  }
                  data-testid="harness-policy-input-verification-escalate-on-max"
                  aria-label="Verification escalate on max override"
                >
                  <option value="">System default</option>
                  <option value="true">On</option>
                  <option value="false">Off</option>
                </select>
              ) : (
                <span
                  className={policy?.verificationEscalateOnMax == null ? "subtle" : "mono"}
                  // eslint-disable-next-line no-restricted-syntax -- verbatim port: mono fontSize
                  style={{ fontSize: 11.5 }}
                  data-testid="harness-policy-value-verification-escalate-on-max"
                >
                  {boolToDisplay(policy ? policy.verificationEscalateOnMax : null)}
                </span>
              )}
            </div>

            {/* === Risky action detection (tri-state boolean) === */}
            <div className="spread">
              {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: fontSize */}
              <span style={{ fontSize: 12.5 }}>Risky action detection</span>
              {editing ? (
                <select
                  value={draft.riskyActionEnabled}
                  onChange={(e) =>
                    updateDraft("riskyActionEnabled", e.target.value as HarnessPolicyDraft["riskyActionEnabled"])
                  }
                  data-testid="harness-policy-input-risky-action-enabled"
                  aria-label="Risky action detection override"
                >
                  <option value="">System default</option>
                  <option value="true">On</option>
                  <option value="false">Off</option>
                </select>
              ) : (
                <span
                  className={policy?.riskyActionEnabled == null ? "subtle" : "mono"}
                  // eslint-disable-next-line no-restricted-syntax -- verbatim port: mono fontSize
                  style={{ fontSize: 11.5 }}
                  data-testid="harness-policy-value-risky-action-enabled"
                >
                  {boolToDisplay(policy ? policy.riskyActionEnabled : null)}
                </span>
              )}
            </div>

            {/* === Risky action extra patterns (list field, after the toggle) === */}
            {LIST_FIELDS.filter((f) => f.key === "riskyActionExtraPatterns").map((field) => {
              const currentValue = policy ? policy[field.policyKey] : null;
              return (
                <div key={field.key} className="spread">
                  {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: fontSize */}
                  <span style={{ fontSize: 12.5 }}>{field.label}</span>
                  {editing ? (
                    <input
                      type="text"
                      value={draft[field.key]}
                      placeholder="System default (comma or newline separated)"
                      onChange={(e) => updateDraft(field.key, e.target.value)}
                      // eslint-disable-next-line no-restricted-syntax -- verbatim port: input sizing
                      style={{ width: 320, fontSize: 12, padding: "2px 6px" }}
                      data-testid={`harness-policy-input-${field.testid}`}
                      aria-label={`${field.label} override`}
                    />
                  ) : currentValue && currentValue.length > 0 ? (
                    // eslint-disable-next-line no-restricted-syntax -- verbatim port: mono fontSize
                    <span className="mono" style={{ fontSize: 11.5 }} data-testid={`harness-policy-value-${field.testid}`}>
                      {currentValue.join(", ")}
                    </span>
                  ) : (
                    <span className="subtle" data-testid={`harness-policy-value-${field.testid}`}>
                      System default
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Card>
    </div>
  );
}

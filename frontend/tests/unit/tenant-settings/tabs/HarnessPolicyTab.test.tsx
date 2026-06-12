/**
 * File: frontend/tests/unit/tenant-settings/tabs/HarnessPolicyTab.test.tsx
 * Purpose: Vitest coverage for HarnessPolicyTab — view/edit + Save PUT (composite-replace) + 422 inline error.
 * Category: Frontend / Tests / tenant-settings / unit / tabs
 * Scope: Phase 57 / Sprint 57.106 C3 (Harness Policy tab)
 *
 * Modification History (newest-first):
 *   - 2026-06-12: Initial creation (Sprint 57.106 C3)
 *
 * Related:
 *   - frontend/src/features/tenant-settings/components/tabs/HarnessPolicyTab.tsx
 *   - ./ModelPolicyTab.test.tsx (mock structure authority)
 */

import "@testing-library/jest-dom/vitest";

import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/features/tenant-settings/hooks/useHarnessPolicy", () => ({
  useHarnessPolicy: vi.fn(),
  HARNESS_POLICY_QUERY_KEY_BASE: ["tenant-settings", "harness-policy"],
}));
vi.mock("@/features/tenant-settings/hooks/useHarnessPolicySave", () => ({
  useHarnessPolicySave: vi.fn(),
}));

import { HarnessPolicyTab } from "@/features/tenant-settings/components/tabs/HarnessPolicyTab";
import { useHarnessPolicy } from "@/features/tenant-settings/hooks/useHarnessPolicy";
import { useHarnessPolicySave } from "@/features/tenant-settings/hooks/useHarnessPolicySave";
import type { HarnessPolicy } from "@/features/tenant-settings/types";

function mockSave(
  overrides: Partial<{
    mutate: ReturnType<typeof vi.fn>;
    isPending: boolean;
    isSuccess: boolean;
    error: Error | null;
    reset: ReturnType<typeof vi.fn>;
  }> = {},
): void {
  vi.mocked(useHarnessPolicySave).mockReturnValue({
    mutate: overrides.mutate ?? vi.fn(),
    isPending: overrides.isPending ?? false,
    isSuccess: overrides.isSuccess ?? false,
    error: overrides.error ?? null,
    reset: overrides.reset ?? vi.fn(),
  } as unknown as ReturnType<typeof useHarnessPolicySave>);
}

function mockPolicy(
  policy: HarnessPolicy | undefined,
  overrides: Partial<{ isLoading: boolean; error: Error | null }> = {},
): void {
  vi.mocked(useHarnessPolicy).mockReturnValue({
    data: policy,
    isLoading: overrides.isLoading ?? false,
    error: overrides.error ?? null,
  } as unknown as ReturnType<typeof useHarnessPolicy>);
}

const SPARSE_POLICY: HarnessPolicy = {
  escalateInputPhrases: null,
  escalateBetweenTurnsPhrases: null,
  escalateOutputPhrases: null,
  escalateTools: null,
  verificationMode: null,
  verificationJudgeTemplate: null,
  verificationEscalateOnMax: null,
  riskyActionEnabled: null,
  riskyActionExtraPatterns: null,
};

const FULL_POLICY: HarnessPolicy = {
  escalateInputPhrases: ["wire money", "delete prod"],
  escalateBetweenTurnsPhrases: ["approval required"],
  escalateOutputPhrases: ["ssn"],
  escalateTools: ["mock_delete_database"],
  verificationMode: "enabled",
  verificationJudgeTemplate: "factual_consistency",
  verificationEscalateOnMax: true,
  riskyActionEnabled: false,
  riskyActionExtraPatterns: ["rm -rf"],
};

describe("HarnessPolicyTab (Sprint 57.106 C3)", () => {
  beforeEach(() => {
    mockPolicy(SPARSE_POLICY);
    mockSave();
  });
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders the 'Harness policy' Card title", () => {
    render(<HarnessPolicyTab tenantId="t1" />);
    expect(screen.getByText("Harness policy")).toBeInTheDocument();
  });

  it("renders loading state", () => {
    mockPolicy(undefined, { isLoading: true });
    render(<HarnessPolicyTab tenantId="t1" />);
    expect(screen.getByText(/Loading harness policy/)).toBeInTheDocument();
  });

  it("renders load-error state", () => {
    mockPolicy(undefined, { error: new Error("HTTP 404: tenant not found") });
    render(<HarnessPolicyTab tenantId="t1" />);
    const err = screen.getByTestId("harness-policy-load-error");
    expect(err).toBeInTheDocument();
    expect(err).toHaveTextContent(/tenant not found/);
  });

  it("view mode: sparse policy renders 'System default' for all 9 fields", () => {
    mockPolicy(SPARSE_POLICY);
    render(<HarnessPolicyTab tenantId="t1" />);
    const values = screen.getAllByText("System default");
    // 4 escalate list fields + mode + template + 2 booleans + risky patterns = 9
    expect(values.length).toBe(9);
    expect(screen.getByTestId("harness-policy-value-escalate-tools")).toHaveTextContent(
      "System default",
    );
    expect(screen.getByTestId("harness-policy-value-verification-mode")).toHaveTextContent(
      "System default",
    );
    expect(
      screen.getByTestId("harness-policy-value-verification-escalate-on-max"),
    ).toHaveTextContent("System default");
  });

  it("view mode: set fields render their current values", () => {
    mockPolicy(FULL_POLICY);
    render(<HarnessPolicyTab tenantId="t1" />);
    expect(screen.getByTestId("harness-policy-value-escalate-input-phrases")).toHaveTextContent(
      "wire money, delete prod",
    );
    expect(screen.getByTestId("harness-policy-value-escalate-tools")).toHaveTextContent(
      "mock_delete_database",
    );
    expect(screen.getByTestId("harness-policy-value-verification-mode")).toHaveTextContent(
      "enabled",
    );
    expect(
      screen.getByTestId("harness-policy-value-verification-judge-template"),
    ).toHaveTextContent("factual_consistency");
    expect(
      screen.getByTestId("harness-policy-value-verification-escalate-on-max"),
    ).toHaveTextContent("On");
    expect(screen.getByTestId("harness-policy-value-risky-action-enabled")).toHaveTextContent(
      "Off",
    );
    expect(
      screen.getByTestId("harness-policy-value-risky-action-extra-patterns"),
    ).toHaveTextContent("rm -rf");
  });

  it("Edit button disabled while loading, enabled once loaded", () => {
    mockPolicy(undefined, { isLoading: true });
    const { rerender } = render(<HarnessPolicyTab tenantId="t1" />);
    expect(screen.getByTestId("harness-policy-edit-btn")).toBeDisabled();

    mockPolicy(FULL_POLICY);
    rerender(<HarnessPolicyTab tenantId="t1" />);
    expect(screen.getByTestId("harness-policy-edit-btn")).not.toBeDisabled();
  });

  it("entering edit mode reveals Save/Cancel + controls seeded from current policy", () => {
    mockPolicy(FULL_POLICY);
    render(<HarnessPolicyTab tenantId="t1" />);
    fireEvent.click(screen.getByTestId("harness-policy-edit-btn"));

    expect(screen.getByTestId("harness-policy-save-btn")).toBeInTheDocument();
    expect(screen.getByTestId("harness-policy-cancel-btn")).toBeInTheDocument();

    const inputPhrases = screen.getByTestId(
      "harness-policy-input-escalate-input-phrases",
    ) as HTMLInputElement;
    expect(inputPhrases.value).toBe("wire money, delete prod");

    const mode = screen.getByTestId(
      "harness-policy-input-verification-mode",
    ) as HTMLSelectElement;
    expect(mode.value).toBe("enabled");

    const template = screen.getByTestId(
      "harness-policy-input-verification-judge-template",
    ) as HTMLSelectElement;
    expect(template.value).toBe("factual_consistency");

    const escalateOnMax = screen.getByTestId(
      "harness-policy-input-verification-escalate-on-max",
    ) as HTMLSelectElement;
    expect(escalateOnMax.value).toBe("true");

    const riskyEnabled = screen.getByTestId(
      "harness-policy-input-risky-action-enabled",
    ) as HTMLSelectElement;
    expect(riskyEnabled.value).toBe("false");
  });

  it("edit mode seeds blank/System-default controls from a sparse policy", () => {
    mockPolicy(SPARSE_POLICY);
    render(<HarnessPolicyTab tenantId="t1" />);
    fireEvent.click(screen.getByTestId("harness-policy-edit-btn"));

    const inputPhrases = screen.getByTestId(
      "harness-policy-input-escalate-input-phrases",
    ) as HTMLInputElement;
    expect(inputPhrases.value).toBe("");

    const mode = screen.getByTestId(
      "harness-policy-input-verification-mode",
    ) as HTMLSelectElement;
    expect(mode.value).toBe(""); // "System default"

    const escalateOnMax = screen.getByTestId(
      "harness-policy-input-verification-escalate-on-max",
    ) as HTMLSelectElement;
    expect(escalateOnMax.value).toBe(""); // "System default"
  });

  it("Save sends the COMPLETE desired policy (composite-replace) — sparse policy → all null", () => {
    const mutate = vi.fn();
    mockSave({ mutate });
    mockPolicy(SPARSE_POLICY);
    render(<HarnessPolicyTab tenantId="t1" />);

    fireEvent.click(screen.getByTestId("harness-policy-edit-btn"));
    fireEvent.click(screen.getByTestId("harness-policy-save-btn"));

    expect(mutate).toHaveBeenCalledWith({
      escalateInputPhrases: null,
      escalateBetweenTurnsPhrases: null,
      escalateOutputPhrases: null,
      escalateTools: null,
      verificationMode: null,
      verificationJudgeTemplate: null,
      verificationEscalateOnMax: null,
      riskyActionEnabled: null,
      riskyActionExtraPatterns: null,
    });
  });

  it("Save parses a comma/newline list input to string[] and reads the selects", () => {
    const mutate = vi.fn();
    mockSave({ mutate });
    mockPolicy(SPARSE_POLICY);
    render(<HarnessPolicyTab tenantId="t1" />);

    fireEvent.click(screen.getByTestId("harness-policy-edit-btn"));

    // Single-line <input>: comma-separated (jsdom strips newlines from inputs;
    // the component supports comma-OR-newline, but only commas are observable
    // through a single-line input control).
    fireEvent.change(screen.getByTestId("harness-policy-input-escalate-tools"), {
      target: { value: "tool_a, tool_b, tool_c" },
    });
    fireEvent.change(screen.getByTestId("harness-policy-input-verification-mode"), {
      target: { value: "disabled" },
    });
    fireEvent.change(
      screen.getByTestId("harness-policy-input-verification-judge-template"),
      { target: { value: "safety_review" } },
    );
    fireEvent.change(
      screen.getByTestId("harness-policy-input-verification-escalate-on-max"),
      { target: { value: "false" } },
    );
    fireEvent.change(screen.getByTestId("harness-policy-input-risky-action-enabled"), {
      target: { value: "true" },
    });

    fireEvent.click(screen.getByTestId("harness-policy-save-btn"));

    expect(mutate).toHaveBeenCalledWith({
      escalateInputPhrases: null,
      escalateBetweenTurnsPhrases: null,
      escalateOutputPhrases: null,
      escalateTools: ["tool_a", "tool_b", "tool_c"],
      verificationMode: "disabled",
      verificationJudgeTemplate: "safety_review",
      verificationEscalateOnMax: false,
      riskyActionEnabled: true,
      riskyActionExtraPatterns: null,
    });
  });

  it("Cancel button resets the draft + exits edit mode", () => {
    mockPolicy(FULL_POLICY);
    render(<HarnessPolicyTab tenantId="t1" />);
    fireEvent.click(screen.getByTestId("harness-policy-edit-btn"));
    fireEvent.click(screen.getByTestId("harness-policy-cancel-btn"));

    expect(screen.queryByTestId("harness-policy-save-btn")).toBeNull();
    expect(screen.queryByTestId("harness-policy-cancel-btn")).toBeNull();
    expect(screen.getByTestId("harness-policy-edit-btn")).toBeInTheDocument();
  });

  it("Save button disabled + 'Saving…' label while mutation isPending", () => {
    mockSave({ isPending: true });
    mockPolicy(FULL_POLICY);
    render(<HarnessPolicyTab tenantId="t1" />);
    fireEvent.click(screen.getByTestId("harness-policy-edit-btn"));

    const saveBtn = screen.getByTestId("harness-policy-save-btn");
    expect(saveBtn).toBeDisabled();
    expect(saveBtn).toHaveTextContent(/Saving…/);
    expect(screen.getByTestId("harness-policy-cancel-btn")).toBeDisabled();
  });

  it("surfaces a 422 save error inline (the detail string)", () => {
    mockSave({ error: new Error("HTTP 422: unknown judge template 'bogus'") });
    mockPolicy(FULL_POLICY);
    render(<HarnessPolicyTab tenantId="t1" />);
    fireEvent.click(screen.getByTestId("harness-policy-edit-btn"));

    const err = screen.getByTestId("harness-policy-save-error");
    expect(err).toBeInTheDocument();
    expect(err).toHaveTextContent(/unknown judge template/);
  });
});

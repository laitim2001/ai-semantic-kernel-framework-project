/**
 * File: frontend/tests/unit/tenant-settings/tabs/HITLPoliciesTab.test.tsx
 * Purpose: Vitest coverage for HITLPoliciesTab — real backend useHITLPolicies hook integration.
 * Category: Frontend / Tests / tenant-settings / unit / tabs
 * Scope: Phase 57 / Sprint 57.49 Day 1 (fixture → real backend migration)
 *
 * Modification History (newest-first):
 *   - 2026-05-26: Sprint 57.54 Track B — add edit mode coverage + mock useHITLPoliciesSave + soften banner assertion
 *   - 2026-05-26: Sprint 57.49 — rewrite to mock useHITLPolicies hook
 *   - 2026-05-26: Initial creation (Sprint 57.44 Day 2)
 */

import "@testing-library/jest-dom/vitest";

import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/features/tenant-settings/hooks/useHITLPolicies", () => ({
  useHITLPolicies: vi.fn(),
  HITL_POLICIES_QUERY_KEY_BASE: ["tenant-settings", "hitl-policies"],
}));

vi.mock("@/features/tenant-settings/hooks/useHITLPoliciesSave", () => ({
  useHITLPoliciesSave: vi.fn(),
}));

import { HITLPoliciesTab } from "@/features/tenant-settings/components/tabs/HITLPoliciesTab";
import { useHITLPolicies } from "@/features/tenant-settings/hooks/useHITLPolicies";
import { useHITLPoliciesSave } from "@/features/tenant-settings/hooks/useHITLPoliciesSave";

function mockSave(
  overrides: Partial<{ mutate: ReturnType<typeof vi.fn>; isPending: boolean; isSuccess: boolean; error: Error | null; reset: ReturnType<typeof vi.fn> }> = {},
): void {
  vi.mocked(useHITLPoliciesSave).mockReturnValue({
    mutate: overrides.mutate ?? vi.fn(),
    isPending: overrides.isPending ?? false,
    isSuccess: overrides.isSuccess ?? false,
    error: overrides.error ?? null,
    reset: overrides.reset ?? vi.fn(),
  } as unknown as ReturnType<typeof useHITLPoliciesSave>);
}

function mockData(items: unknown[]): void {
  vi.mocked(useHITLPolicies).mockReturnValue({
    data: { items, total: items.length, limit: 50, offset: 0 },
    isLoading: false,
    error: null,
  } as unknown as ReturnType<typeof useHITLPolicies>);
}

describe("HITLPoliciesTab (Sprint 57.49)", () => {
  beforeEach(() => {
    mockData([]);
    mockSave();
  });
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders Card title 'HITL policies' + subtitle", () => {
    render(<HITLPoliciesTab tenantId="t1" />);
    expect(screen.getByText("HITL policies")).toBeInTheDocument();
    expect(screen.getByText(/Per-tool · risk-tiered · escalation routing/)).toBeInTheDocument();
  });

  it("renders 'Loading HITL policies…' when isLoading=true", () => {
    vi.mocked(useHITLPolicies).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as unknown as ReturnType<typeof useHITLPolicies>);
    render(<HITLPoliciesTab tenantId="t1" />);
    expect(screen.getByText(/Loading HITL policies/)).toBeInTheDocument();
  });

  it("renders empty state message when no policy configured", () => {
    mockData([]);
    render(<HITLPoliciesTab tenantId="t1" />);
    expect(screen.getByText(/No HITL policy override configured/)).toBeInTheDocument();
  });

  it("renders 4 risk-tier rows + lowercases risk labels for CSS class", () => {
    mockData([
      { risk: "CRITICAL", policy: "always_ask", sla_seconds: 300, reviewers: "@platform-l2" },
      { risk: "HIGH", policy: "always_ask", sla_seconds: 900, reviewers: "@platform-l2" },
      { risk: "MEDIUM", policy: "ask_once", sla_seconds: 3600, reviewers: "@platform-l1" },
      { risk: "LOW", policy: "auto", sla_seconds: null, reviewers: "" },
    ]);
    const { container } = render(<HITLPoliciesTab tenantId="t1" />);
    expect(screen.getByText("critical")).toBeInTheDocument();
    expect(screen.getByText("high")).toBeInTheDocument();
    expect(screen.getByText("medium")).toBeInTheDocument();
    expect(screen.getByText("low")).toBeInTheDocument();
    expect(container.querySelector(".sev-critical")).toBeTruthy();
    expect(container.querySelector(".sev-low")).toBeTruthy();
  });

  it("formats sla_seconds: 300s → '5m', null → '—'", () => {
    mockData([
      { risk: "CRITICAL", policy: "always_ask", sla_seconds: 300, reviewers: "@a" },
      { risk: "LOW", policy: "auto", sla_seconds: null, reviewers: "" },
    ]);
    render(<HITLPoliciesTab tenantId="t1" />);
    expect(screen.getByText("5m")).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(1);
  });

  it("renders AP-2 BackendGapBanner with softened Sprint 57.54 copy", () => {
    mockData([]);
    render(<HITLPoliciesTab tenantId="t1" />);
    const banner = screen.getByTestId("backend-gap-banner");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent(/Phase 58\+/);
    expect(banner).toHaveTextContent(/Off-platform channel routing/);
    expect(banner).toHaveTextContent(/editable via Edit button/);
  });

  /* === Sprint 57.54 Track B — edit mode === */

  describe("edit mode (Sprint 57.54)", () => {
    it("Edit button opens edit form + populates draft from items", () => {
      mockData([
        { risk: "LOW", policy: "auto", sla_seconds: null, reviewers: "" },
        { risk: "MEDIUM", policy: "ask_once", sla_seconds: 3600, reviewers: "@platform-l1" },
        { risk: "HIGH", policy: "always_ask", sla_seconds: 900, reviewers: "@platform-l1, @platform-l2" },
        { risk: "CRITICAL", policy: "always_ask", sla_seconds: 300, reviewers: "@platform-l2" },
      ]);
      render(<HITLPoliciesTab tenantId="t1" />);
      fireEvent.click(screen.getByTestId("hitl-edit-btn"));
      expect(screen.getByTestId("hitl-edit-form")).toBeInTheDocument();
      // auto_approve_max_risk → highest "auto" tier → LOW
      const autoSelect = screen.getByTestId("hitl-auto-approve-select") as HTMLSelectElement;
      expect(autoSelect.value).toBe("LOW");
      // require_approval_min_risk → lowest "always_ask" tier → HIGH
      const requireSelect = screen.getByTestId("hitl-require-approval-select") as HTMLSelectElement;
      expect(requireSelect.value).toBe("HIGH");
      // reviewers + sla pre-populated
      const highReviewers = screen.getByTestId("hitl-reviewers-HIGH") as HTMLInputElement;
      expect(highReviewers.value).toBe("@platform-l1, @platform-l2");
      const highSla = screen.getByTestId("hitl-sla-HIGH") as HTMLInputElement;
      expect(highSla.value).toBe("900");
    });

    it("Cancel button exits edit mode without invoking mutate", () => {
      const mutateSpy = vi.fn();
      mockSave({ mutate: mutateSpy });
      mockData([{ risk: "LOW", policy: "auto", sla_seconds: null, reviewers: "" }]);
      render(<HITLPoliciesTab tenantId="t1" />);
      fireEvent.click(screen.getByTestId("hitl-edit-btn"));
      expect(screen.getByTestId("hitl-edit-form")).toBeInTheDocument();
      fireEvent.click(screen.getByTestId("hitl-cancel-btn"));
      expect(screen.queryByTestId("hitl-edit-form")).not.toBeInTheDocument();
      expect(mutateSpy).not.toHaveBeenCalled();
    });

    it("Save button calls mutate with composed payload", () => {
      const mutateSpy = vi.fn();
      mockSave({ mutate: mutateSpy });
      mockData([
        { risk: "LOW", policy: "auto", sla_seconds: null, reviewers: "" },
        { risk: "HIGH", policy: "always_ask", sla_seconds: 900, reviewers: "@platform-l1" },
      ]);
      render(<HITLPoliciesTab tenantId="t1" />);
      fireEvent.click(screen.getByTestId("hitl-edit-btn"));
      fireEvent.click(screen.getByTestId("hitl-save-btn"));
      expect(mutateSpy).toHaveBeenCalledTimes(1);
      const payload = mutateSpy.mock.calls[0][0];
      expect(payload.auto_approve_max_risk).toBe("LOW");
      expect(payload.require_approval_min_risk).toBe("HIGH");
      expect(payload.reviewer_groups_by_risk).toEqual({ HIGH: ["@platform-l1"] });
      expect(payload.sla_seconds_by_risk).toEqual({ HIGH: 900 });
    });

    it("Save button is disabled while saveMutation.isPending=true", () => {
      mockSave({ isPending: true });
      mockData([{ risk: "LOW", policy: "auto", sla_seconds: null, reviewers: "" }]);
      render(<HITLPoliciesTab tenantId="t1" />);
      fireEvent.click(screen.getByTestId("hitl-edit-btn"));
      const saveBtn = screen.getByTestId("hitl-save-btn") as HTMLButtonElement;
      expect(saveBtn).toBeDisabled();
      expect(saveBtn).toHaveTextContent(/Saving/);
    });

    it("displays inline error when saveMutation.error is non-null", () => {
      mockSave({ error: new Error("HTTP 422: invalid risk level") });
      mockData([{ risk: "LOW", policy: "auto", sla_seconds: null, reviewers: "" }]);
      render(<HITLPoliciesTab tenantId="t1" />);
      const err = screen.getByTestId("hitl-save-error");
      expect(err).toBeInTheDocument();
      expect(err).toHaveTextContent(/invalid risk level/);
    });
  });
});

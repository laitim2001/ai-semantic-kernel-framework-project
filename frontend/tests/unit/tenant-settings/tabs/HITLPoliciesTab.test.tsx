/**
 * File: frontend/tests/unit/tenant-settings/tabs/HITLPoliciesTab.test.tsx
 * Purpose: Vitest coverage for HITLPoliciesTab — real backend useHITLPolicies hook integration.
 * Category: Frontend / Tests / tenant-settings / unit / tabs
 * Scope: Phase 57 / Sprint 57.49 Day 1 (fixture → real backend migration)
 *
 * Modification History (newest-first):
 *   - 2026-05-26: Sprint 57.49 — rewrite to mock useHITLPolicies hook
 *   - 2026-05-26: Initial creation (Sprint 57.44 Day 2)
 */

import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/features/tenant-settings/hooks/useHITLPolicies", () => ({
  useHITLPolicies: vi.fn(),
  HITL_POLICIES_QUERY_KEY_BASE: ["tenant-settings", "hitl-policies"],
}));

import { HITLPoliciesTab } from "@/features/tenant-settings/components/tabs/HITLPoliciesTab";
import { useHITLPolicies } from "@/features/tenant-settings/hooks/useHITLPolicies";

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

  it("renders AP-2 BackendGapBanner", () => {
    mockData([]);
    render(<HITLPoliciesTab tenantId="t1" />);
    const banner = screen.getByTestId("backend-gap-banner");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent(/Phase 58\+/);
  });
});

/**
 * File: frontend/tests/unit/tenant-settings/tabs/QuotasTab.test.tsx
 * Purpose: Vitest coverage for QuotasTab — useQuotas + useRateLimits hook integration.
 * Category: Frontend / Tests / tenant-settings / unit / tabs
 * Scope: Phase 57 / Sprint 57.49 Day 1 (fixture → real backend migration)
 *
 * Modification History (newest-first):
 *   - 2026-05-26: Sprint 57.49 — rewrite to mock useQuotas + useRateLimits hooks
 *   - 2026-05-26: Initial creation (Sprint 57.44 Day 2)
 */

import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/features/tenant-settings/hooks/useQuotas", () => ({
  useQuotas: vi.fn(),
  QUOTAS_QUERY_KEY_BASE: ["tenant-settings", "quotas"],
}));
vi.mock("@/features/tenant-settings/hooks/useRateLimits", () => ({
  useRateLimits: vi.fn(),
  RATE_LIMITS_QUERY_KEY_BASE: ["tenant-settings", "rate-limits"],
}));

import { QuotasTab } from "@/features/tenant-settings/components/tabs/QuotasTab";
import { useQuotas } from "@/features/tenant-settings/hooks/useQuotas";
import { useRateLimits } from "@/features/tenant-settings/hooks/useRateLimits";

function mockData(quotas: unknown[], rateLimits: unknown[]): void {
  vi.mocked(useQuotas).mockReturnValue({
    data: { items: quotas, total: quotas.length, limit: 50, offset: 0 },
    isLoading: false,
    error: null,
  } as unknown as ReturnType<typeof useQuotas>);
  vi.mocked(useRateLimits).mockReturnValue({
    data: { items: rateLimits, total: rateLimits.length, limit: 50, offset: 0 },
    isLoading: false,
    error: null,
  } as unknown as ReturnType<typeof useRateLimits>);
}

describe("QuotasTab (Sprint 57.49)", () => {
  beforeEach(() => {
    mockData([], []);
  });
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders 'Usage quotas' + 'Rate limits' Card titles", () => {
    render(<QuotasTab tenantId="t1" />);
    expect(screen.getByText("Usage quotas")).toBeInTheDocument();
    expect(screen.getByText("Rate limits")).toBeInTheDocument();
  });

  it("Usage quotas Card renders loading state", () => {
    vi.mocked(useQuotas).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as unknown as ReturnType<typeof useQuotas>);
    vi.mocked(useRateLimits).mockReturnValue({
      data: { items: [], total: 0, limit: 50, offset: 0 },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useRateLimits>);
    render(<QuotasTab tenantId="t1" />);
    expect(screen.getByText(/Loading quotas/)).toBeInTheDocument();
  });

  it("renders quota rows when data present + null current_usage renders 0% bar-track", () => {
    mockData(
      [
        { resource: "tokens_per_day", limit: 10_000_000, unit: "tokens", period: "day", current_usage: null },
        { resource: "cost_usd_per_day", limit: 100, unit: "usd", period: "day", current_usage: null },
      ],
      [],
    );
    const { container } = render(<QuotasTab tenantId="t1" />);
    expect(screen.getByText("tokens_per_day")).toBeInTheDocument();
    expect(screen.getByText("cost_usd_per_day")).toBeInTheDocument();
    const bars = container.querySelectorAll(".bar-track");
    expect(bars.length).toBe(2);
  });

  it("renders rate-limit rows from useRateLimits data", () => {
    mockData(
      [],
      [
        { label: "API requests", value: "100 / min" },
        { label: "Tool calls", value: "1,000 / min" },
      ],
    );
    render(<QuotasTab tenantId="t1" />);
    expect(screen.getByText("API requests")).toBeInTheDocument();
    expect(screen.getByText("100 / min")).toBeInTheDocument();
    expect(screen.getByText("Tool calls")).toBeInTheDocument();
  });

  it("Request increase button fires window.alert with backend gap message", async () => {
    mockData([], [{ label: "x", value: "y" }]);
    const alertSpy = vi.spyOn(window, "alert").mockImplementation(() => {});
    const user = userEvent.setup();
    render(<QuotasTab tenantId="t1" />);
    await user.click(screen.getByRole("button", { name: /request increase/i }));
    expect(alertSpy).toHaveBeenCalledWith(expect.stringMatching(/backend gap/i));
    alertSpy.mockRestore();
  });

  it("renders AP-2 BackendGapBanner for Usage quotas card", () => {
    mockData([{ resource: "tokens_per_day", limit: 10_000_000, unit: "tokens", period: "day", current_usage: null }], []);
    render(<QuotasTab tenantId="t1" />);
    const banner = screen.getByTestId("backend-gap-banner");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent(/Phase 58\+/);
  });
});

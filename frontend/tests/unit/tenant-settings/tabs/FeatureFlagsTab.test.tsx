/**
 * File: frontend/tests/unit/tenant-settings/tabs/FeatureFlagsTab.test.tsx
 * Purpose: Vitest coverage for FeatureFlagsTab — real backend useFeatureFlags hook integration.
 * Category: Frontend / Tests / tenant-settings / unit / tabs
 * Scope: Phase 57 / Sprint 57.49 Day 1 (fixture → real backend migration)
 *
 * Description:
 *   - Renders "Feature flags" Card title + subtitle "Tenant-scoped overrides"
 *   - Loading state visible when isLoading=true
 *   - Error state visible when error present
 *   - Empty state when items=[]
 *   - Renders flag rows from hook data; <Switch role='switch'> per row
 *   - BackendGapBanner present
 *
 * Created: 2026-05-26 (Sprint 57.44 Day 2)
 * Last Modified: 2026-05-26
 *
 * Modification History (newest-first):
 *   - 2026-05-26: Sprint 57.49 — rewrite to mock useFeatureFlags hook (post fixture → real migration)
 *   - 2026-05-26: Initial creation (Sprint 57.44 Day 2)
 */

import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/features/tenant-settings/hooks/useFeatureFlags", () => ({
  useFeatureFlags: vi.fn(),
  FEATURE_FLAGS_QUERY_KEY_BASE: ["tenant-settings", "feature-flags"],
}));

import { FeatureFlagsTab } from "@/features/tenant-settings/components/tabs/FeatureFlagsTab";
import { useFeatureFlags } from "@/features/tenant-settings/hooks/useFeatureFlags";

function mockData(items: unknown[]): void {
  vi.mocked(useFeatureFlags).mockReturnValue({
    data: { items, total: items.length, limit: 50, offset: 0 },
    isLoading: false,
    error: null,
  } as unknown as ReturnType<typeof useFeatureFlags>);
}

describe("FeatureFlagsTab (Sprint 57.49)", () => {
  beforeEach(() => {
    mockData([]);
  });
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders Card title 'Feature flags' + subtitle", () => {
    render(<FeatureFlagsTab tenantId="t1" />);
    expect(screen.getByText("Feature flags")).toBeInTheDocument();
    expect(screen.getByText(/Tenant-scoped overrides/)).toBeInTheDocument();
  });

  it("renders 'Loading feature flags…' when isLoading=true", () => {
    vi.mocked(useFeatureFlags).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as unknown as ReturnType<typeof useFeatureFlags>);
    render(<FeatureFlagsTab tenantId="t1" />);
    expect(screen.getByText(/Loading feature flags/)).toBeInTheDocument();
  });

  it("renders error message when error present", () => {
    vi.mocked(useFeatureFlags).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("HTTP 500"),
    } as unknown as ReturnType<typeof useFeatureFlags>);
    render(<FeatureFlagsTab tenantId="t1" />);
    expect(screen.getByText(/HTTP 500/)).toBeInTheDocument();
  });

  it("renders empty state when items=[]", () => {
    mockData([]);
    render(<FeatureFlagsTab tenantId="t1" />);
    expect(screen.getByText(/No feature flags registered/)).toBeInTheDocument();
  });

  it("renders flag rows with Switch when data present", () => {
    mockData([
      {
        name: "subagent.fork.enabled",
        value: true,
        default_enabled: true,
        overridden: false,
        description: "Allow concurrent fork mode",
        updated_at: "2026-05-26T00:00:00Z",
      },
      {
        name: "tool.sandbox_full",
        value: false,
        default_enabled: false,
        overridden: false,
        description: "Permit FULL_SANDBOX tool runs",
        updated_at: "2026-05-26T00:00:00Z",
      },
    ]);
    const { container } = render(<FeatureFlagsTab tenantId="t1" />);
    expect(screen.getByText("subagent.fork.enabled")).toBeInTheDocument();
    expect(screen.getByText("tool.sandbox_full")).toBeInTheDocument();
    const switches = container.querySelectorAll("[role='switch']");
    expect(switches.length).toBe(2);
  });

  it("renders AP-2 BackendGapBanner", () => {
    mockData([]);
    render(<FeatureFlagsTab tenantId="t1" />);
    const banner = screen.getByTestId("backend-gap-banner");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent(/Phase 58\+/);
  });
});

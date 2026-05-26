/**
 * File: frontend/tests/unit/tenant-settings/tabs/MembersTab.test.tsx
 * Purpose: Vitest coverage for MembersTab — useTenantMembers hook integration.
 * Category: Frontend / Tests / tenant-settings / unit / tabs
 * Scope: Phase 57 / Sprint 57.49 Day 1 (fixture → real backend migration)
 *
 * Modification History (newest-first):
 *   - 2026-05-26: Sprint 57.49 — rewrite to mock useTenantMembers hook (shared with Track B drawer)
 *   - 2026-05-26: Initial creation (Sprint 57.44 Day 2)
 */

import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/features/tenant-settings/hooks/useTenantMembers", () => ({
  useTenantMembers: vi.fn(),
  TENANT_MEMBERS_QUERY_KEY_BASE: ["tenant-settings", "members"],
}));

import { MembersTab } from "@/features/tenant-settings/components/tabs/MembersTab";
import { useTenantMembers } from "@/features/tenant-settings/hooks/useTenantMembers";

function mockData(items: unknown[], total: number): void {
  vi.mocked(useTenantMembers).mockReturnValue({
    data: { items, total, limit: 50, offset: 0 },
    isLoading: false,
    error: null,
  } as unknown as ReturnType<typeof useTenantMembers>);
}

const SAMPLE_MEMBERS = [
  { id: "u1", email: "alice@acme.com", display_name: "Alice Liu", status: "active", created_at: "2026-01-15T00:00:00Z" },
  { id: "u2", email: "bob@acme.com", display_name: null, status: "active", created_at: "2026-02-10T00:00:00Z" },
];

describe("MembersTab (Sprint 57.49)", () => {
  beforeEach(() => {
    mockData([], 0);
  });
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders Card title 'Members' + subtitle reflects backend total", () => {
    mockData(SAMPLE_MEMBERS, 2);
    render(<MembersTab tenantId="t1" />);
    expect(screen.getByText("Members")).toBeInTheDocument();
    expect(screen.getByText(/2 active · 0 invitations/)).toBeInTheDocument();
  });

  it("renders Loading + Error + Empty states correctly", () => {
    vi.mocked(useTenantMembers).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as unknown as ReturnType<typeof useTenantMembers>);
    const { rerender } = render(<MembersTab tenantId="t1" />);
    expect(screen.getByText(/Loading members/)).toBeInTheDocument();

    vi.mocked(useTenantMembers).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("HTTP 404"),
    } as unknown as ReturnType<typeof useTenantMembers>);
    rerender(<MembersTab tenantId="t1" />);
    expect(screen.getByText(/HTTP 404/)).toBeInTheDocument();

    mockData([], 0);
    rerender(<MembersTab tenantId="t1" />);
    expect(screen.getByText(/No members in this tenant/)).toBeInTheDocument();
  });

  it("renders member rows with name/email; null display_name falls back to email local-part", () => {
    mockData(SAMPLE_MEMBERS, 2);
    render(<MembersTab tenantId="t1" />);
    expect(screen.getByText("Alice Liu")).toBeInTheDocument();
    expect(screen.getByText("alice@acme.com")).toBeInTheDocument();
    expect(screen.getByText("bob")).toBeInTheDocument();
    expect(screen.getByText("bob@acme.com")).toBeInTheDocument();
  });

  it("renders avatar spans with linear-gradient style (hue derived from id)", () => {
    mockData(SAMPLE_MEMBERS, 2);
    const { container } = render(<MembersTab tenantId="t1" />);
    const avatars = container.querySelectorAll("span[style*='linear-gradient']");
    expect(avatars.length).toBe(2);
  });

  it("renders Invite button + click fires window.alert with backend gap message", async () => {
    mockData(SAMPLE_MEMBERS, 2);
    const alertSpy = vi.spyOn(window, "alert").mockImplementation(() => {});
    const user = userEvent.setup();
    render(<MembersTab tenantId="t1" />);
    await user.click(screen.getByRole("button", { name: /invite/i }));
    expect(alertSpy).toHaveBeenCalledWith(expect.stringMatching(/backend gap/i));
    alertSpy.mockRestore();
  });

  it("renders AP-2 BackendGapBanner", () => {
    mockData(SAMPLE_MEMBERS, 2);
    render(<MembersTab tenantId="t1" />);
    const banner = screen.getByTestId("backend-gap-banner");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent(/Phase 58\+/);
  });
});

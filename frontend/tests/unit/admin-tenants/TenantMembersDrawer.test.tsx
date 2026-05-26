/**
 * File: frontend/tests/unit/admin-tenants/TenantMembersDrawer.test.tsx
 * Purpose: Vitest coverage for TenantMembersDrawer (Sprint 57.49 Track B).
 * Category: Frontend / Tests / admin-tenants / unit
 * Scope: Phase 57 / Sprint 57.49 Day 1 (Track B — drawer drill-down)
 *
 * Description:
 *   - Returns null when tenantId is null (closed state)
 *   - Renders drawer overlay when tenantId provided
 *   - Loading state visible
 *   - Error state visible
 *   - Member rows render with name + email + status
 *   - Close button + backdrop click trigger onClose
 *   - Pagination controls render when total > PAGE_SIZE
 *
 * Created: 2026-05-26 (Sprint 57.49 Day 1)
 */

import "@testing-library/jest-dom/vitest";

import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/features/tenant-settings/hooks/useTenantMembers", () => ({
  useTenantMembers: vi.fn(),
  TENANT_MEMBERS_QUERY_KEY_BASE: ["tenant-settings", "members"],
}));

import { TenantMembersDrawer } from "@/features/admin-tenants/components/TenantMembersDrawer";
import { useTenantMembers } from "@/features/tenant-settings/hooks/useTenantMembers";

function mockMembersData(items: unknown[], total: number): void {
  vi.mocked(useTenantMembers).mockReturnValue({
    data: { items, total, limit: 50, offset: 0 },
    isLoading: false,
    error: null,
  } as unknown as ReturnType<typeof useTenantMembers>);
}

describe("TenantMembersDrawer (Sprint 57.49)", () => {
  beforeEach(() => {
    mockMembersData([], 0);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("returns null when tenantId is null (closed state)", () => {
    const { container } = render(<TenantMembersDrawer tenantId={null} onClose={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders drawer overlay when tenantId provided", () => {
    render(<TenantMembersDrawer tenantId="tenant-x" onClose={vi.fn()} />);
    expect(screen.getByTestId("tenant-members-drawer")).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("renders 'Loading members…' when isLoading=true", () => {
    vi.mocked(useTenantMembers).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as unknown as ReturnType<typeof useTenantMembers>);
    render(<TenantMembersDrawer tenantId="tenant-x" onClose={vi.fn()} />);
    expect(screen.getByText(/Loading members/)).toBeInTheDocument();
  });

  it("renders error message when error present", () => {
    vi.mocked(useTenantMembers).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("HTTP 404"),
    } as unknown as ReturnType<typeof useTenantMembers>);
    render(<TenantMembersDrawer tenantId="tenant-x" onClose={vi.fn()} />);
    expect(screen.getByText(/HTTP 404/)).toBeInTheDocument();
  });

  it("renders 'No members in this tenant' for empty list", () => {
    mockMembersData([], 0);
    render(<TenantMembersDrawer tenantId="tenant-x" onClose={vi.fn()} />);
    expect(screen.getByText(/No members in this tenant/)).toBeInTheDocument();
  });

  it("renders member rows when data present", () => {
    mockMembersData(
      [
        {
          id: "user-id-1",
          email: "alice@acme.com",
          display_name: "Alice Liu",
          status: "active",
          created_at: "2026-01-15T00:00:00Z",
        },
        {
          id: "user-id-2",
          email: "bob@acme.com",
          display_name: null,
          status: "active",
          created_at: "2026-02-10T00:00:00Z",
        },
      ],
      2,
    );
    render(<TenantMembersDrawer tenantId="tenant-x" onClose={vi.fn()} />);
    expect(screen.getByText("Alice Liu")).toBeInTheDocument();
    expect(screen.getByText("alice@acme.com")).toBeInTheDocument();
    // Bob has null display_name → falls back to email local-part "bob"
    expect(screen.getByText("bob")).toBeInTheDocument();
  });

  it("Close button triggers onClose", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<TenantMembersDrawer tenantId="tenant-x" onClose={onClose} />);
    await user.click(screen.getByRole("button", { name: /close/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("backdrop click triggers onClose", () => {
    const onClose = vi.fn();
    render(<TenantMembersDrawer tenantId="tenant-x" onClose={onClose} />);
    fireEvent.click(screen.getByTestId("tenant-members-drawer"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("pagination controls render when total > PAGE_SIZE (50)", () => {
    const items = Array.from({ length: 50 }, (_, i) => ({
      id: `user-${i}`,
      email: `u${i}@acme.com`,
      display_name: `User ${i}`,
      status: "active",
      created_at: "2026-01-01T00:00:00Z",
    }));
    mockMembersData(items, 120);
    render(<TenantMembersDrawer tenantId="tenant-x" onClose={vi.fn()} />);
    expect(screen.getByRole("button", { name: /previous/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /next/i })).toBeInTheDocument();
    expect(screen.getByText(/Showing 1[–\-]50 of 120/)).toBeInTheDocument();
  });

  it("pagination controls absent when total <= PAGE_SIZE", () => {
    const items = Array.from({ length: 3 }, (_, i) => ({
      id: `user-${i}`,
      email: `u${i}@acme.com`,
      display_name: `User ${i}`,
      status: "active",
      created_at: "2026-01-01T00:00:00Z",
    }));
    mockMembersData(items, 3);
    render(<TenantMembersDrawer tenantId="tenant-x" onClose={vi.fn()} />);
    expect(screen.queryByRole("button", { name: /previous/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /next/i })).toBeNull();
  });
});

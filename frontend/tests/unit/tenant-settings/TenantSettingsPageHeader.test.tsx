/**
 * File: frontend/tests/unit/tenant-settings/TenantSettingsPageHeader.test.tsx
 * Purpose: Vitest coverage for TenantSettingsPageHeader — title + mono displayName + route-pill code + plan badge.
 * Category: Frontend / Tests / tenant-settings / unit
 * Scope: Phase 57 / Sprint 57.44 Day 2 (mockup-fidelity rebuild Vitest coverage)
 *
 * Description:
 *   - Renders .page-head with title "Tenant Settings"
 *   - Renders displayName in mono span
 *   - Renders code in route-pill
 *   - Renders plan + SEATS_FIXTURE seats Badge
 *
 * Created: 2026-05-26 (Sprint 57.44 Day 2)
 *
 * Modification History (newest-first):
 *   - 2026-05-26: Initial creation (Sprint 57.44 Day 2) — tenant-settings mockup-fidelity rebuild Vitest coverage
 *
 * Related:
 *   - frontend/src/features/tenant-settings/components/TenantSettingsPageHeader.tsx
 *   - frontend/src/features/tenant-settings/_fixtures.ts (SEATS_FIXTURE = 8)
 *   - sprint-57-44-plan.md §AC3
 */

import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TenantSettingsPageHeader } from "@/features/tenant-settings/components/TenantSettingsPageHeader";

describe("TenantSettingsPageHeader (Sprint 57.49 — seats from real backend prop)", () => {
  it("renders page title 'Tenant Settings'", () => {
    render(<TenantSettingsPageHeader displayName="Acme Corp" code="ACME" plan="Pro" seats={8} />);
    expect(screen.getByText("Tenant Settings")).toBeInTheDocument();
  });

  it("renders displayName in mono span", () => {
    render(<TenantSettingsPageHeader displayName="Acme Corp" code="ACME" plan="Pro" seats={8} />);
    const monoMatches = screen.getAllByText("Acme Corp");
    expect(monoMatches.length).toBeGreaterThanOrEqual(1);
    expect(monoMatches[0]!.className).toMatch(/mono/);
  });

  it("renders code in route-pill", () => {
    render(<TenantSettingsPageHeader displayName="Acme Corp" code="ACME" plan="Pro" seats={8} />);
    const codeNode = screen.getByText("ACME");
    expect(codeNode).toBeInTheDocument();
    expect(codeNode.className).toMatch(/route-pill/);
  });

  it("renders plan + seats Badge from real backend prop (Sprint 57.49)", () => {
    render(<TenantSettingsPageHeader displayName="Acme Corp" code="ACME" plan="Pro" seats={8} />);
    expect(screen.getByText(/Pro\s*·\s*8\s*seats/)).toBeInTheDocument();
  });

  it("Badge has primary tone class for plan + seats", () => {
    const { container } = render(<TenantSettingsPageHeader displayName="Acme Corp" code="ACME" plan="Enterprise" seats={42} />);
    const primaryBadge = container.querySelector(".badge.primary");
    expect(primaryBadge).not.toBeNull();
    expect(primaryBadge!.textContent).toMatch(/Enterprise\s*·\s*42\s*seats/);
  });

  it("seats prop defaults to 0 when omitted (back-compat)", () => {
    render(<TenantSettingsPageHeader displayName="Acme Corp" code="ACME" plan="Pro" />);
    expect(screen.getByText(/Pro\s*·\s*0\s*seats/)).toBeInTheDocument();
  });
});

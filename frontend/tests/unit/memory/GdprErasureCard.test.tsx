/**
 * File: frontend/tests/unit/memory/GdprErasureCard.test.tsx
 * Purpose: Vitest coverage for GdprErasureCard — title + subtitle + 2 Fields (Subject id input + Reason select with 3 options) + danger Button + AP-2 banner.
 * Category: Frontend / Tests / memory / unit
 * Scope: Phase 57 / Sprint 57.42 Day 2 (memory matrix full mockup-fidelity rebuild)
 *
 * Description:
 *   - Card title "GDPR right-to-erasure" renders
 *   - Subtitle copy mentions WORM audit + hash chain
 *   - "Subject id" Field + placeholder input "u_…"
 *   - "Reason (audited)" Field + 3 select options (GDPR Art. 17 / CCPA / Legal hold)
 *     with defaultValue "gdpr"
 *   - "Issue tombstone" danger Button renders
 *   - AP-2 BackendGapBanner declared inside Card for deferred erasure endpoint
 *
 * Created: 2026-05-25 (Sprint 57.42 Day 2)
 *
 * Modification History (newest-first):
 *   - 2026-05-25: Initial creation (Sprint 57.42 Day 2)
 */

import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { GdprErasureCard } from "@/features/memory/components/GdprErasureCard";

describe("GdprErasureCard (Sprint 57.42)", () => {
  it("renders title + 2 fields with 3 reason options + danger Button + AP-2 banner", () => {
    render(<GdprErasureCard />);

    // Card title
    expect(screen.getByText("GDPR right-to-erasure")).toBeInTheDocument();
    // Subtitle copy
    expect(
      screen.getByText(/Tombstone subject across all memory scopes\. WORM audit retains hash chain\./i),
    ).toBeInTheDocument();

    // Subject id input with placeholder
    const subjectInput = screen.getByPlaceholderText("u_…") as HTMLInputElement;
    expect(subjectInput).toBeInTheDocument();

    // Reason select with 3 options + default "gdpr"
    const reasonSelect = screen.getByRole("combobox") as HTMLSelectElement;
    expect(reasonSelect).toBeInTheDocument();
    expect(reasonSelect.value).toBe("gdpr");
    expect(screen.getByRole("option", { name: /GDPR Art\. 17 erasure/i })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /CCPA opt-out/i })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /Legal hold release/i })).toBeInTheDocument();

    // Danger Button
    expect(screen.getByRole("button", { name: /issue tombstone/i })).toBeInTheDocument();

    // AP-2 BackendGapBanner
    const banner = screen.getByTestId("backend-gap-banner");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent(/GDPR erasure endpoint pending/i);
  });
});

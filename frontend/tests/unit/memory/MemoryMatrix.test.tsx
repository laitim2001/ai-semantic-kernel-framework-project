/**
 * File: frontend/tests/unit/memory/MemoryMatrix.test.tsx
 * Purpose: Vitest coverage for MemoryMatrix — 5×3 grid headers + scope rows + cursor-aware visibility filter + AP-2 banner.
 * Category: Frontend / Tests / memory / unit
 * Scope: Phase 57 / Sprint 57.42 Day 2 (memory matrix full mockup-fidelity rebuild)
 *
 * Description:
 *   - Renders 3 header cells with TIME_SCALES names + TTL subtitles
 *     (TTL ∞ / TTL 90d / TTL 24h)
 *   - Renders 5 scope label cells (system / tenant / role / user / session) with
 *     formatted count
 *   - Cursor-aware visibility filter (verbatim from MemoryMatrix.filterVisible):
 *       cursor=0 → session.day shows all 3 entries
 *       cursor=-5 → session.day shows first 1 entry only
 *       cursor=-15 → session.day shows 0 entries (empty placeholder)
 *       cursor=-130 → all `.day` cells across 5 scopes show 0 entries
 *   - AP-2 BackendGapBanner declared after grid
 *
 *   Note: Mockup fixtures top out at 4 entries per cell (tenant|permanent), so
 *   "+N more" overflow path cannot be triggered from production fixtures. This
 *   is verified by asserting "+1 more" is NOT in the document when cursor=0.
 *
 * Created: 2026-05-25 (Sprint 57.42 Day 2)
 *
 * Modification History (newest-first):
 *   - 2026-05-25: Initial creation (Sprint 57.42 Day 2)
 */

import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MemoryMatrix } from "@/features/memory/components/MemoryMatrix";

describe("MemoryMatrix (Sprint 57.42)", () => {
  it("renders 3 time-scale headers with TTL subtitles + 5 scope rows + AP-2 banner", () => {
    render(<MemoryMatrix cursor={0} />);

    // 3 time scale headers
    expect(screen.getByText("permanent")).toBeInTheDocument();
    expect(screen.getByText("quarter")).toBeInTheDocument();
    expect(screen.getByText("day")).toBeInTheDocument();
    // TTL subtitles
    expect(screen.getByText("TTL ∞")).toBeInTheDocument();
    expect(screen.getByText("TTL 90d")).toBeInTheDocument();
    expect(screen.getByText("TTL 24h")).toBeInTheDocument();

    // 5 scope labels
    expect(screen.getByText("system")).toBeInTheDocument();
    expect(screen.getByText("tenant")).toBeInTheDocument();
    expect(screen.getByText("role")).toBeInTheDocument();
    expect(screen.getByText("user")).toBeInTheDocument();
    expect(screen.getByText("session")).toBeInTheDocument();

    // AP-2 BackendGapBanner
    const banner = screen.getByTestId("backend-gap-banner");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent(/memory matrix query endpoint/i);

    // No "+N more" overflow rendered for production fixtures (max 4 entries per cell)
    expect(screen.queryByText(/^\+\d+ more$/)).not.toBeInTheDocument();
  });

  it("cursor=0 renders all 3 session.day entries (root_cause / evidence / severity)", () => {
    render(<MemoryMatrix cursor={0} />);
    // session.day fixture: sess_4tk2p.root_cause, sess_4tk2p.evidence, sess_4tk2p.severity
    expect(screen.getByText("sess_4tk2p.root_cause")).toBeInTheDocument();
    expect(screen.getByText("sess_4tk2p.evidence")).toBeInTheDocument();
    expect(screen.getByText("sess_4tk2p.severity")).toBeInTheDocument();
  });

  it("cursor=-5 (within session.day -10 threshold) keeps only first session.day entry + 2 hidden", () => {
    render(<MemoryMatrix cursor={-5} />);
    expect(screen.getByText("sess_4tk2p.root_cause")).toBeInTheDocument();
    expect(screen.queryByText("sess_4tk2p.evidence")).not.toBeInTheDocument();
    expect(screen.queryByText("sess_4tk2p.severity")).not.toBeInTheDocument();
    // Hidden-count footer in warning color (text "· 2 hidden")
    expect(screen.getByText(/· 2 hidden/)).toBeInTheDocument();
  });

  it("cursor=-130 zeroes all .day cells across scopes (4 cells with -day-fixture content gone)", () => {
    render(<MemoryMatrix cursor={-130} />);
    // session.day cleared
    expect(screen.queryByText("sess_4tk2p.root_cause")).not.toBeInTheDocument();
    // tenant.day fixture (anomaly.token_spike) cleared
    expect(screen.queryByText("anomaly.token_spike")).not.toBeInTheDocument();
    // user.day fixture cleared
    expect(screen.queryByText("u_jamie.last_session")).not.toBeInTheDocument();
    expect(screen.queryByText("u_jamie.notifications")).not.toBeInTheDocument();
    // permanent + quarter cells still populated (filter only nukes day)
    expect(screen.getByText("compliance.frameworks")).toBeInTheDocument();
  });
});

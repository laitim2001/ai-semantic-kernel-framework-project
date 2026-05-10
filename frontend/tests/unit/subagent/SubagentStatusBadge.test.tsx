/**
 * File: frontend/tests/unit/subagent/SubagentStatusBadge.test.tsx
 * Purpose: Vitest tests for SubagentStatusBadge component (2 status variants + mode suffix).
 * Category: Frontend / tests / unit / subagent
 * Scope: Phase 57 / Sprint 57.12 Day 2 / US-3 + US-6
 *
 * Created: 2026-05-10 (Sprint 57.12 Day 2 / US-3 + US-6)
 *
 * Modification History:
 *   - 2026-05-10: Initial creation (Sprint 57.12 Day 2 / US-3 + US-6)
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { SubagentStatusBadge } from "@/features/subagent/components/SubagentStatusBadge";

describe("SubagentStatusBadge (Sprint 57.12)", () => {
  test("running renders blue variant with 'Running' label", () => {
    render(<SubagentStatusBadge status="running" />);
    const badge = screen.getByTestId("subagent-status-badge-running");
    expect(badge).toHaveTextContent("Running");
    expect(badge).toHaveClass("bg-blue-100", "text-blue-800");
  });

  test("completed renders green variant with 'Done' label", () => {
    render(<SubagentStatusBadge status="completed" />);
    const badge = screen.getByTestId("subagent-status-badge-completed");
    expect(badge).toHaveTextContent("Done");
    expect(badge).toHaveClass("bg-green-100", "text-green-800");
  });

  test("renders mode suffix when provided", () => {
    render(<SubagentStatusBadge status="running" mode="fork" />);
    const badge = screen.getByTestId("subagent-status-badge-running");
    expect(badge).toHaveTextContent("· fork");
  });

  test("omits mode suffix when not provided", () => {
    render(<SubagentStatusBadge status="completed" />);
    const badge = screen.getByTestId("subagent-status-badge-completed");
    expect(badge).not.toHaveTextContent("·");
  });
});

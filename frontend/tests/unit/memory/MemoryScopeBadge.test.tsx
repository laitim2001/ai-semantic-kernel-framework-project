/**
 * File: frontend/tests/unit/memory/MemoryScopeBadge.test.tsx
 * Purpose: Vitest tests for MemoryScopeBadge component (5 layer variants).
 * Category: Frontend / tests / unit / memory
 * Scope: Phase 57 / Sprint 57.12 Day 2 / US-3 + US-5
 *
 * Created: 2026-05-10 (Sprint 57.12 Day 2 / US-3 + US-5)
 *
 * Modification History:
 *   - 2026-05-10: Initial creation (Sprint 57.12 Day 2 / US-3 + US-5)
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { MemoryScopeBadge } from "@/features/memory/components/MemoryScopeBadge";

describe("MemoryScopeBadge (Sprint 57.12)", () => {
  test("system renders indigo variant with 'System' label", () => {
    render(<MemoryScopeBadge layer="system" />);
    const badge = screen.getByTestId("memory-scope-badge-system");
    expect(badge).toHaveTextContent("System");
    expect(badge).toHaveClass("bg-indigo-100", "text-indigo-800");
  });

  test("tenant renders blue variant", () => {
    render(<MemoryScopeBadge layer="tenant" />);
    const badge = screen.getByTestId("memory-scope-badge-tenant");
    expect(badge).toHaveTextContent("Tenant");
    expect(badge).toHaveClass("bg-blue-100", "text-blue-800");
  });

  test("role renders teal variant", () => {
    render(<MemoryScopeBadge layer="role" />);
    const badge = screen.getByTestId("memory-scope-badge-role");
    expect(badge).toHaveTextContent("Role");
    expect(badge).toHaveClass("bg-teal-100", "text-teal-800");
  });

  test("user renders green variant", () => {
    render(<MemoryScopeBadge layer="user" />);
    const badge = screen.getByTestId("memory-scope-badge-user");
    expect(badge).toHaveTextContent("User");
    expect(badge).toHaveClass("bg-green-100", "text-green-800");
  });

  test("session renders amber variant", () => {
    render(<MemoryScopeBadge layer="session" />);
    const badge = screen.getByTestId("memory-scope-badge-session");
    expect(badge).toHaveTextContent("Session");
    expect(badge).toHaveClass("bg-amber-100", "text-amber-800");
  });
});

/**
 * File: frontend/tests/unit/verification/VerifierTypeBadge.test.tsx
 * Purpose: Vitest tests for VerifierTypeBadge component (3 type variants).
 * Category: Frontend / tests / unit / verification
 * Scope: Phase 57 / Sprint 57.11 Day 2 / US-3 + US-4
 *
 * Created: 2026-05-10 (Sprint 57.11 Day 2 / US-3 + US-4)
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { VerifierTypeBadge } from "@/features/verification/components/VerifierTypeBadge";

describe("VerifierTypeBadge (Sprint 57.11)", () => {
  test("rules_based renders blue variant with 'Rules' label", () => {
    render(<VerifierTypeBadge type="rules_based" />);
    const badge = screen.getByTestId("verifier-type-badge-rules_based");
    expect(badge).toHaveTextContent("Rules");
    expect(badge).toHaveClass("bg-blue-100", "text-blue-800");
  });

  test("llm_judge renders purple variant with 'LLM Judge' label", () => {
    render(<VerifierTypeBadge type="llm_judge" />);
    const badge = screen.getByTestId("verifier-type-badge-llm_judge");
    expect(badge).toHaveTextContent("LLM Judge");
    expect(badge).toHaveClass("bg-purple-100", "text-purple-800");
  });

  test("external renders gray variant with 'External' label", () => {
    render(<VerifierTypeBadge type="external" />);
    const badge = screen.getByTestId("verifier-type-badge-external");
    expect(badge).toHaveTextContent("External");
    expect(badge).toHaveClass("bg-gray-100", "text-gray-800");
  });
});

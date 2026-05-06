/**
 * File: frontend/tests/unit/cost-dashboard/MonthPicker.test.tsx
 * Purpose: Unit test for MonthPicker — renders + onChange.
 * Category: Frontend / tests / unit / cost-dashboard
 * Scope: Phase 57 / Sprint 57.1 US-1 (shared MonthPicker)
 *
 * Created: 2026-05-06 (Sprint 57.1 Day 1)
 */

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MonthPicker } from "../../../src/features/cost-dashboard/components/MonthPicker";

describe("MonthPicker", () => {
  it("renders with provided value", () => {
    const onChange = vi.fn();
    render(<MonthPicker value="2026-04" onChange={onChange} />);
    const input = screen.getByLabelText("Select month") as HTMLInputElement;
    expect(input).toBeInTheDocument();
    expect(input.value).toBe("2026-04");
  });

  it("triggers onChange when input changes", () => {
    const onChange = vi.fn();
    render(<MonthPicker value="2026-04" onChange={onChange} />);
    const input = screen.getByLabelText("Select month");
    fireEvent.change(input, { target: { value: "2026-05" } });
    expect(onChange).toHaveBeenCalledWith("2026-05");
  });
});

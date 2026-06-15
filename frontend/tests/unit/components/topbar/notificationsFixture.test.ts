/**
 * File: frontend/tests/unit/components/topbar/notificationsFixture.test.ts
 * Purpose: Unit test — the bell badge count derives from the shared DEMO fixture
 *   (not a separate hardcoded number). Sprint 57.124 (AD-NotificationsPanel-Backend-Feed).
 * Category: Frontend / tests / unit / components / topbar
 * Scope: Phase 57 / Sprint 57.124 (NEW)
 *
 * Created: 2026-06-16 (Sprint 57.124)
 */

import { describe, expect, test } from "vitest";

import { DEMO_NOTIFICATIONS, DEMO_UNREAD_COUNT } from "@/components/topbar/notificationsFixture";

describe("notificationsFixture", () => {
  test("DEMO_UNREAD_COUNT derives from the unread items (single source, not a magic 3)", () => {
    const expected = DEMO_NOTIFICATIONS.filter((n) => n.unread).length;
    expect(DEMO_UNREAD_COUNT).toBe(expected);
    // n1/n2/n3 are unread in the current fixture.
    expect(DEMO_UNREAD_COUNT).toBe(3);
  });

  test("the fixture has 6 demo notifications", () => {
    expect(DEMO_NOTIFICATIONS).toHaveLength(6);
  });
});

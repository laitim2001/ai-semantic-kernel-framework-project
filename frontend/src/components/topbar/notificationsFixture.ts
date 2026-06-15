/**
 * File: frontend/src/components/topbar/notificationsFixture.ts
 * Purpose: Single source for the DEMO notifications fixture (shared by the bell badge + the panel).
 * Category: Frontend / components / topbar (Cat 12 cross-cutting UX surface)
 * Scope: Phase 57 / Sprint 57.124 (AD-NotificationsPanel-Backend-Feed honest-label)
 *
 * Description:
 *   The notifications feature has NO backend yet (AD-NotificationsPanel-Backend-Feed).
 *   This module is the SINGLE source of the fixture data so the Topbar bell badge
 *   (AppShellV2) and the dropdown panel (NotificationsPanel) agree on the count
 *   instead of a separate hardcoded number. NotificationsPanel renders a visible
 *   BackendGapBanner so the data is honestly marked DEMO (CLAUDE.md §Drive-Through).
 *   Replace DEMO_NOTIFICATIONS with a real feed when the backend lands.
 *
 * Created: 2026-06-16 (Sprint 57.124)
 */

export type NotificationKind = "hitl" | "incident" | "verify" | "tripwire" | "system";

export type NotificationSeverity = "critical" | "high" | "medium" | "low";

export interface NotificationItem {
  id: string;
  kind: NotificationKind;
  severity: NotificationSeverity;
  titleKey: string;
  bodyKey: string;
  time: string;
  unread: boolean;
  routePath?: string;
}

/** DEMO fixture — replace with a real feed when AD-NotificationsPanel-Backend-Feed lands. */
export const DEMO_NOTIFICATIONS: NotificationItem[] = [
  { id: "n1", kind: "hitl",     severity: "critical", titleKey: "topbar.notifications.items.n1Title", bodyKey: "topbar.notifications.items.n1Body", time: "23m", unread: true,  routePath: "/governance" },
  { id: "n2", kind: "incident", severity: "high",     titleKey: "topbar.notifications.items.n2Title", bodyKey: "topbar.notifications.items.n2Body", time: "1h",  unread: true,  routePath: "/incidents" },
  { id: "n3", kind: "verify",   severity: "medium",   titleKey: "topbar.notifications.items.n3Title", bodyKey: "topbar.notifications.items.n3Body", time: "2h",  unread: true,  routePath: "/verification" },
  { id: "n4", kind: "tripwire", severity: "high",     titleKey: "topbar.notifications.items.n4Title", bodyKey: "topbar.notifications.items.n4Body", time: "3h",  unread: false, routePath: "/redaction" },
  { id: "n5", kind: "system",   severity: "low",      titleKey: "topbar.notifications.items.n5Title", bodyKey: "topbar.notifications.items.n5Body", time: "5h",  unread: false, routePath: "/cost-dashboard" },
  { id: "n6", kind: "system",   severity: "low",      titleKey: "topbar.notifications.items.n6Title", bodyKey: "topbar.notifications.items.n6Body", time: "8h",  unread: false, routePath: "/cache-manager" },
];

/** Derived unread count for the bell badge (shared with the panel; static DEMO value). */
export const DEMO_UNREAD_COUNT = DEMO_NOTIFICATIONS.filter((n) => n.unread).length;

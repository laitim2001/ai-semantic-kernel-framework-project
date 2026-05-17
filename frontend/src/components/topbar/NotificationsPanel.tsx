/**
 * File: frontend/src/components/topbar/NotificationsPanel.tsx
 * Purpose: Bell-icon dropdown panel — 6 fixture notifications (HITL/incident/verify/tripwire/system) + tabs + mark-read.
 * Category: Frontend / components / topbar (Cat 12 cross-cutting UX surface)
 * Scope: Phase 57 / Sprint 57.19 Day 5 / US-D2
 *
 * Description:
 *   Mockup port from reference/design-mockups/topbar-overlays.jsx NotificationsPanel.
 *   Anchored to bell button in AppShellV2 header. Tabs: All / Unread. Items dismissible (local state).
 *
 *   Backend wiring: deferred to Sprint 57.20+ (Cat 12 notifications feed via SSE / poll endpoint).
 *   Current sprint = mockup-fidelity port with fixture data + open/close + unread badge.
 *
 * Created: 2026-05-17 (Sprint 57.19 Day 5 / US-D2)
 *
 * Modification History:
 *   - 2026-05-17: Initial creation (Sprint 57.19 Day 5 / US-D2) — mockup port with 6 fixture items
 *
 * Related:
 *   - reference/design-mockups/topbar-overlays.jsx (canonical mockup source)
 *   - frontend/src/components/AppShellV2.tsx (bell button trigger + anchored panel)
 */

import {
  AlertTriangle,
  CheckCheck,
  Info,
  Shield,
  type LucideIcon,
} from "lucide-react";
import { type FC, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

type NotificationSeverity = "critical" | "high" | "medium" | "low";
type NotificationKind = "hitl" | "incident" | "verify" | "tripwire" | "system";

interface NotificationItem {
  id: string;
  kind: NotificationKind;
  severity: NotificationSeverity;
  titleKey: string;
  bodyKey: string;
  time: string;
  unread: boolean;
  routePath?: string;
}

const NOTIFICATIONS_SEED: NotificationItem[] = [
  { id: "n1", kind: "hitl", severity: "critical", titleKey: "topbar.notifications.items.n1Title", bodyKey: "topbar.notifications.items.n1Body", time: "23m", unread: true, routePath: "/governance" },
  { id: "n2", kind: "incident", severity: "high", titleKey: "topbar.notifications.items.n2Title", bodyKey: "topbar.notifications.items.n2Body", time: "1h", unread: true, routePath: "/incidents" },
  { id: "n3", kind: "verify", severity: "medium", titleKey: "topbar.notifications.items.n3Title", bodyKey: "topbar.notifications.items.n3Body", time: "2h", unread: true, routePath: "/verification" },
  { id: "n4", kind: "tripwire", severity: "high", titleKey: "topbar.notifications.items.n4Title", bodyKey: "topbar.notifications.items.n4Body", time: "3h", unread: false, routePath: "/redaction" },
  { id: "n5", kind: "system", severity: "low", titleKey: "topbar.notifications.items.n5Title", bodyKey: "topbar.notifications.items.n5Body", time: "5h", unread: false, routePath: "/cost-dashboard" },
  { id: "n6", kind: "system", severity: "low", titleKey: "topbar.notifications.items.n6Title", bodyKey: "topbar.notifications.items.n6Body", time: "8h", unread: false, routePath: "/cache-manager" },
];

const KIND_ICON: Record<NotificationKind, LucideIcon> = {
  hitl: CheckCheck,
  incident: AlertTriangle,
  verify: CheckCheck,
  tripwire: Shield,
  system: Info,
};

const SEVERITY_BG: Record<NotificationSeverity, string> = {
  critical: "bg-danger/16 text-danger",
  high: "bg-warning/16 text-warning",
  medium: "bg-info/16 text-info",
  low: "bg-success/16 text-success",
};

interface NotificationsPanelProps {
  open: boolean;
  onClose: () => void;
}

export const NotificationsPanel: FC<NotificationsPanelProps> = ({ open, onClose }) => {
  const { t } = useTranslation("common");
  const navigate = useNavigate();
  const [items, setItems] = useState(NOTIFICATIONS_SEED);
  const [filter, setFilter] = useState<"all" | "unread">("all");

  if (!open) return null;

  const visibleItems = filter === "unread" ? items.filter((n) => n.unread) : items;
  const unreadCount = items.filter((n) => n.unread).length;

  const markAll = (): void => setItems(items.map((n) => ({ ...n, unread: false })));
  const markOne = (id: string): void => setItems(items.map((n) => (n.id === id ? { ...n, unread: false } : n)));
  const onItemClick = (n: NotificationItem): void => {
    markOne(n.id);
    if (n.routePath) navigate(n.routePath);
    onClose();
  };

  return (
    <div
      data-testid="notifications-panel"
      className="absolute right-16 top-14 z-40 flex max-h-[75vh] w-96 flex-col rounded-md border border-border bg-background shadow-lg"
      role="dialog"
      aria-label={t("topbar.notifications.title")}
    >
      <div className="flex items-center gap-2 border-b border-border px-3.5 py-3">
        <span className="text-sm font-semibold">{t("topbar.notifications.title")}</span>
        {unreadCount > 0 && (
          <span className="rounded-full bg-warning/16 px-2 py-0.5 text-[11px] font-medium text-warning">
            {unreadCount} {t("topbar.notifications.new")}
          </span>
        )}
        <div className="flex-1" />
        <button
          onClick={markAll}
          className="text-[11px] text-muted-foreground hover:text-foreground"
          type="button"
        >
          {t("topbar.notifications.markAll")}
        </button>
      </div>

      <div className="flex gap-1 border-b border-border px-2.5 py-1.5" role="tablist">
        {(["all", "unread"] as const).map((k) => (
          <button
            key={k}
            onClick={() => setFilter(k)}
            type="button"
            role="tab"
            aria-selected={filter === k}
            className={
              filter === k
                ? "rounded px-2.5 py-1 text-[11.5px] font-medium text-foreground bg-muted"
                : "rounded px-2.5 py-1 text-[11.5px] text-muted-foreground hover:bg-muted/50"
            }
          >
            {t(`topbar.notifications.tab.${k}`)}{" "}
            <span className="ml-1 font-mono text-muted-foreground">
              {k === "all" ? items.length : unreadCount}
            </span>
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto">
        {visibleItems.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-8 text-muted-foreground">
            <CheckCheck size={20} />
            <div className="text-xs">{t("topbar.notifications.empty")}</div>
          </div>
        ) : (
          visibleItems.map((n, i) => {
            const KindIcon = KIND_ICON[n.kind];
            return (
              <div
                key={n.id}
                onClick={() => onItemClick(n)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onItemClick(n);
                  }
                }}
                className={
                  (n.unread ? "bg-primary/4 " : "") +
                  (i < visibleItems.length - 1 ? "border-b border-border " : "") +
                  "relative grid cursor-pointer grid-cols-[auto_1fr_auto] gap-2.5 px-3.5 py-3 hover:bg-muted/50"
                }
              >
                {n.unread && (
                  <span className="absolute left-1 top-1/2 h-1.5 w-1.5 -translate-y-1/2 rounded-full bg-primary" />
                )}
                <span className={`flex h-7 w-7 items-center justify-center rounded ${SEVERITY_BG[n.severity]}`}>
                  <KindIcon size={14} />
                </span>
                <div className="flex min-w-0 flex-col gap-0.5">
                  <div className={n.unread ? "text-[12.5px] font-medium leading-snug" : "text-[12.5px] leading-snug"}>
                    {t(n.titleKey)}
                  </div>
                  <div className="text-[11.5px] leading-snug text-muted-foreground">{t(n.bodyKey)}</div>
                </div>
                <span className="whitespace-nowrap font-mono text-[10.5px] text-muted-foreground">{n.time}</span>
              </div>
            );
          })
        )}
      </div>

      <div className="flex gap-2 border-t border-border px-3.5 py-2">
        <button
          onClick={() => { navigate("/audit-log"); onClose(); }}
          type="button"
          className="flex-1 rounded border border-border px-3 py-1.5 text-[11.5px] text-muted-foreground hover:bg-muted"
        >
          {t("topbar.notifications.viewAll")}
        </button>
        <button
          onClick={() => { navigate("/tenant-settings"); onClose(); }}
          type="button"
          className="rounded border border-border px-3 py-1.5 text-[11.5px] text-muted-foreground hover:bg-muted"
        >
          {t("topbar.notifications.prefs")}
        </button>
      </div>
    </div>
  );
};

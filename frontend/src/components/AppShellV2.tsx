/**
 * File: frontend/src/components/AppShellV2.tsx
 * Purpose: V2 layout shell — sidebar + main column with header (per-page title + bell + user menu).
 * Category: Frontend / components / layout
 * Scope: Phase 57 / Sprint 57.8 US-1.3 Day 1
 *
 * Description:
 *   Root layout for ALL authenticated routes in V2. Adopts V1-style admin
 *   portal pattern (sidebar left + main right) replacing Sprint 57.7 minimal
 *   header-only AppShell (renamed AuthShell.tsx, reserved for /auth/*).
 *
 *   Sprint 57.19 US-D1+D2: mounts CommandPalette (⌘K hotkey) + NotificationsPanel
 *   (bell click) globally. Both are always-present components rendered at shell
 *   level so they're available on every authenticated route.
 *
 * Created: 2026-05-10 (Sprint 57.8 Day 1)
 * Last Modified: 2026-05-17
 *
 * Modification History:
 *   - 2026-05-17: Sprint 57.19 US-D1+D2 — mount CommandPalette + bell + NotificationsPanel; add ⌘K hotkey
 *   - 2026-05-10: Sprint 57.13 US-A5 — add data-testid="app-shell" on root (connectivity spec anchor)
 *   - 2026-05-10: Initial creation (Sprint 57.8 US-1.3)
 *
 * Related:
 *   - frontend/src/components/Sidebar.tsx (left nav)
 *   - frontend/src/components/UserMenu.tsx (header right slot)
 *   - frontend/src/components/topbar/CommandPalette.tsx (⌘K palette, Sprint 57.19 US-D1)
 *   - frontend/src/components/topbar/NotificationsPanel.tsx (bell panel, Sprint 57.19 US-D2)
 *   - frontend/src/components/AuthShell.tsx (renamed from AppShell.tsx; for /auth/*)
 */

import { Bell } from "lucide-react";
import { type FC, type ReactNode, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { Sidebar } from "./Sidebar";
import { CommandPalette } from "./topbar/CommandPalette";
import { NotificationsPanel } from "./topbar/NotificationsPanel";
import { UserMenu } from "./UserMenu";

interface AppShellV2Props {
  children: ReactNode;
  pageTitle: string;
  headerActions?: ReactNode;
  userMenu?: ReactNode;
}

export const AppShellV2: FC<AppShellV2Props> = ({
  children,
  pageTitle,
  headerActions,
  userMenu,
}) => {
  const { t } = useTranslation("common");
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const userMenuSlot = userMenu === undefined ? <UserMenu /> : userMenu;

  // Global ⌘K (mac) / Ctrl+K (win/linux) hotkey to open CommandPalette (US-D1).
  useEffect(() => {
    const onKey = (e: KeyboardEvent): void => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((prev) => !prev);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div data-testid="app-shell" className="flex min-h-screen bg-background text-foreground">
      <Sidebar />
      <div className="relative flex flex-1 flex-col">
        <header className="sticky top-0 z-10 flex h-14 items-center justify-between border-b border-border bg-background/95 px-6 backdrop-blur">
          <h1 className="text-lg font-semibold tracking-tight">{pageTitle}</h1>
          <div className="flex items-center gap-3">
            {headerActions && <div className="flex items-center gap-2">{headerActions}</div>}
            <button
              type="button"
              onClick={() => setNotifOpen((p) => !p)}
              aria-label={t("topbar.notifications.title")}
              data-testid="notifications-bell"
              className="relative inline-flex h-8 w-8 items-center justify-center rounded-full text-muted-foreground hover:bg-muted hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <Bell size={16} />
              <span className="absolute right-1 top-1 h-1.5 w-1.5 rounded-full bg-danger" aria-hidden="true" />
            </button>
            {userMenuSlot}
          </div>
        </header>
        <NotificationsPanel open={notifOpen} onClose={() => setNotifOpen(false)} />
        <main className="flex-1 p-6">{children}</main>
      </div>
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
    </div>
  );
};

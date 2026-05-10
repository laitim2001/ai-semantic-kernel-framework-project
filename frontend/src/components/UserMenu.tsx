/**
 * File: frontend/src/components/UserMenu.tsx
 * Purpose: Header avatar dropdown — show current user (authStore) + sign out.
 * Category: Frontend / components / auth-aware
 * Scope: Phase 57 / Sprint 57.8 US-2 (Sprint 57.13 US-A1 — read authStore)
 *
 * Description:
 *   Avatar circle in AppShellV2 header right slot. Click → popover showing
 *   user display name / email + Sign out button (calls logout() — backend
 *   /auth/logout + clear authStore + redirect to vendor signout).
 *
 *   Auth-aware: renders null unless authStore.status === "authenticated".
 *   Avatar initial from display name (fallback email local-part).
 *
 *   Design choice: minimal custom dropdown (NO @radix-ui dep) per YAGNI —
 *   2 menu items don't justify the dep. Sprint 57.13 US-B3 may swap to
 *   @radix-ui/react-dropdown-menu when the menu grows.
 *
 * Created: 2026-05-10 (Sprint 57.8 Day 2)
 * Last Modified: 2026-05-10
 *
 * Modification History:
 *   - 2026-05-10: Sprint 57.13 US-A1 — read authStore.user instead of decoding the JWT; sign out via logout()
 *   - 2026-05-10: Initial creation (Sprint 57.8 US-2)
 *
 * Related:
 *   - frontend/src/features/auth/store/authStore.ts (user + status)
 *   - frontend/src/features/auth/services/authService.ts (logout)
 *   - frontend/src/components/AppShellV2.tsx (host via userMenu prop slot)
 */

import { LogOut, User as UserIcon } from "lucide-react";
import { useEffect, useRef, useState, type FC } from "react";

import { logout } from "@/features/auth/services/authService";
import { useAuthStore } from "@/features/auth/store/authStore";
import { cn } from "@/lib/utils";

export const UserMenu: FC = () => {
  // ALL hooks unconditional per React Rules of Hooks; early return below.
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const status = useAuthStore((s) => s.status);
  const user = useAuthStore((s) => s.user);

  // Close on click outside or Escape (effect runs unconditionally; cleanup handles unmount)
  useEffect(() => {
    if (!open) return;

    function handleMouseDown(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }

    document.addEventListener("mousedown", handleMouseDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleMouseDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  if (status !== "authenticated" || user === null) return null;

  const label = user.display_name?.trim() || user.email;
  const initial = label ? label.charAt(0).toUpperCase() : "?";

  const handleSignOut = () => {
    setOpen(false);
    void logout();
  };

  return (
    <div ref={wrapperRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className={cn(
          "inline-flex h-8 w-8 items-center justify-center rounded-full",
          "bg-primary text-primary-foreground text-sm font-medium",
          "hover:opacity-80 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2",
        )}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="User menu"
      >
        {initial === "?" ? <UserIcon size={16} /> : initial}
      </button>

      {open && (
        <div
          className={cn(
            "absolute right-0 top-10 z-20 min-w-[200px] rounded-md border border-border",
            "bg-popover text-popover-foreground shadow-lg",
            "py-1",
          )}
          role="menu"
          aria-label="User menu options"
        >
          <div className="px-3 py-2 text-sm border-b border-border">
            <div className="text-xs text-muted-foreground">Signed in as</div>
            <div className="truncate font-medium">{label}</div>
            {user.display_name?.trim() && user.email !== label ? (
              <div className="truncate text-xs text-muted-foreground">{user.email}</div>
            ) : null}
          </div>
          <button
            type="button"
            onClick={handleSignOut}
            className="flex w-full items-center gap-2 px-3 py-2 text-sm text-foreground hover:bg-muted"
            role="menuitem"
          >
            <LogOut size={14} />
            Sign out
          </button>
        </div>
      )}
    </div>
  );
};

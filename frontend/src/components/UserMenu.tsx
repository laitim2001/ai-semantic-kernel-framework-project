/**
 * File: frontend/src/components/UserMenu.tsx
 * Purpose: Header avatar dropdown — consume Sprint 57.7 IAM JWT for username + logout.
 * Category: Frontend / components / auth-aware
 * Scope: Phase 57 / Sprint 57.8 US-2 Day 2
 *
 * Description:
 *   Avatar circle in AppShellV2 header right slot. Click → popover showing
 *   user email + Sign out button. Sign out clears JWT (clearJwt) + redirects
 *   to /auth/login (existing 57.7 IAM flow).
 *
 *   Auth-aware: if !isAuthenticated() returns null (caller skips slot).
 *
 *   Avatar initials derived from JWT email claim — "alice@example.com" → "A".
 *   Day 2 simplification: only first char extracted (full name parsing deferred
 *   to Phase 58.x AD-Frontend-AuthUX when WorkOS profile name claim wired).
 *
 *   Design choice (Day 2): minimal custom dropdown (NO @radix-ui dep) per
 *   YAGNI — 2 menu items don't justify ~15 KB gzipped radix-ui dep. Click
 *   outside closes via document mousedown listener; escape key closes via
 *   keydown listener. If future menu grows to 5+ items / sub-menus / tooltips
 *   → swap to @radix-ui/react-dropdown-menu (AD-Frontend-Dropdown candidate).
 *
 * Created: 2026-05-10 (Sprint 57.8 Day 2)
 * Last Modified: 2026-05-10
 *
 * Modification History:
 *   - 2026-05-10: Initial creation (Sprint 57.8 US-2)
 *
 * Related:
 *   - frontend/src/features/auth/services/authService.ts (getJwt + clearJwt + isAuthenticated)
 *   - frontend/src/components/AppShellV2.tsx (host via userMenu prop slot)
 */

import { LogOut, User as UserIcon } from "lucide-react";
import { useEffect, useRef, useState, type FC } from "react";
import { useNavigate } from "react-router-dom";

import {
  clearJwt,
  getJwt,
  isAuthenticated,
} from "@/features/auth/services/authService";
import { cn } from "@/lib/utils";

/**
 * Decode JWT email claim without verifying signature (browser-side display
 * only; backend always re-verifies signature on every request). Returns
 * null on malformed token.
 */
function decodeJwtEmail(token: string): string | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1]));
    return typeof payload.email === "string" ? payload.email : null;
  } catch {
    return null;
  }
}

export const UserMenu: FC = () => {
  // ALL hooks unconditional per React Rules of Hooks; early return below.
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

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

  // Re-read auth state per render (React re-renders after navigate / setState)
  const authed = isAuthenticated();
  if (!authed) return null;

  const token = getJwt();
  const email = token ? decodeJwtEmail(token) : null;
  const initial = email ? email.charAt(0).toUpperCase() : "?";

  const handleSignOut = () => {
    clearJwt();
    setOpen(false);
    navigate("/auth/login");
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
            <div className="truncate font-medium">{email ?? "Unknown user"}</div>
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

/**
 * File: frontend/src/components/AuthShell.tsx
 * Purpose: Auth-only routes layout shell — logo + main + footer (NO sidebar/nav since unauthed).
 * Category: Frontend / components / layout (auth-only)
 * Scope: Phase 57 / Sprint 57.7 US-B2 (initial as AppShell) → Sprint 57.8 US-4 (renamed AuthShell per Day 0 Decision B1)
 *
 * Description:
 *   Container layout for unauthenticated routes (/auth/login + /auth/callback).
 *   Tailwind utility classes only (NO inline style per .claude/rules/frontend-react.md).
 *
 *   Differs from AppShellV2 in 2 critical ways:
 *     1. NO sidebar (user not authed yet — no nav target available)
 *     2. NO UserMenu (no JWT to consume)
 *
 *   Per Day 0 Decision B1: keeps logo + footer for branding consistency
 *   so unauthed pages still feel like part of the platform vs. naked HTML.
 *
 * Created: 2026-05-10 (Sprint 57.7 Day 3 Tier 3 — initial as AppShell)
 * Last Modified: 2026-05-10
 *
 * Modification History:
 *   - 2026-05-10: Sprint 57.8 US-4 Day 2 — rename AppShell → AuthShell per Day 0
 *     Decision B1; remove 3 hardcoded nav links (Cost / SLA / Tenants) since
 *     unauthed users can't access them anyway
 *   - 2026-05-10: Initial creation (Sprint 57.7 US-B2)
 */

import type { FC, ReactNode } from "react";
import { Link } from "react-router-dom";

interface AuthShellProps {
  children: ReactNode;
  headerActions?: ReactNode;
}

export const AuthShell: FC<AuthShellProps> = ({ children, headerActions }) => {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <header className="border-b border-border bg-background/95 backdrop-blur sticky top-0 z-10">
        <div className="container mx-auto flex h-14 items-center justify-between px-4">
          <Link to="/" className="font-semibold tracking-tight hover:opacity-80">
            IPA Platform
          </Link>
          {headerActions && <div className="flex items-center gap-2">{headerActions}</div>}
        </div>
      </header>
      <main className="container mx-auto flex-1 p-6">{children}</main>
      <footer className="border-t border-border py-4 text-center text-xs text-muted-foreground">
        IPA Platform V2
      </footer>
    </div>
  );
};

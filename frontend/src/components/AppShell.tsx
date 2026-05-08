/**
 * File: frontend/src/components/AppShell.tsx
 * Purpose: Root layout shell — header (logo + nav + actions) + main + footer.
 * Category: Frontend / components (Sprint 57.7 US-B2 Frontend Foundation 1/N)
 * Scope: Phase 57 / Sprint 57.7 Day 3 Tier 3
 *
 * Description:
 *   Container layout for all authenticated pages. Tailwind utility classes
 *   throughout (NO inline style per .claude/rules/frontend-react.md).
 *   Layout matches checklist 3.1: <header> + <main className="container ...">
 *   {children}</main> + <footer>. Optional headerActions slot for per-page
 *   buttons (e.g. month picker on cost-dashboard).
 *
 * Created: 2026-05-10 (Sprint 57.7 Day 3 Tier 3)
 * Last Modified: 2026-05-10
 *
 * Modification History:
 *   - 2026-05-10: Initial creation (Sprint 57.7 US-B2)
 */

import type { FC, ReactNode } from "react";
import { Link } from "react-router-dom";

interface AppShellProps {
  children: ReactNode;
  headerActions?: ReactNode;
}

export const AppShell: FC<AppShellProps> = ({ children, headerActions }) => {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <header className="border-b border-border bg-background/95 backdrop-blur sticky top-0 z-10">
        <div className="container mx-auto flex h-14 items-center justify-between px-4">
          <div className="flex items-center gap-6">
            <Link to="/" className="font-semibold tracking-tight hover:opacity-80">
              IPA Platform
            </Link>
            <nav className="hidden md:flex items-center gap-4 text-sm text-muted-foreground">
              <Link to="/cost-dashboard" className="hover:text-foreground">
                Cost
              </Link>
              <Link to="/sla-dashboard" className="hover:text-foreground">
                SLA
              </Link>
              <Link to="/admin-tenants" className="hover:text-foreground">
                Tenants
              </Link>
            </nav>
          </div>
          {headerActions && <div className="flex items-center gap-2">{headerActions}</div>}
        </div>
      </header>
      <main className="container mx-auto flex-1 p-6">{children}</main>
      <footer className="border-t border-border py-4 text-center text-xs text-muted-foreground">
        IPA Platform V2 · Sprint 57.7
      </footer>
    </div>
  );
};

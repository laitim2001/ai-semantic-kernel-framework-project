/**
 * File: frontend/src/components/ui/tabs.tsx
 * Purpose: Minimal Tabs primitive — controlled value + onChange; matches mockup ui.jsx `<Tabs>` shape.
 * Category: Frontend / components / ui
 * Scope: Phase 57 / Sprint 57.19 Day 3 / US-C2
 *
 * Description:
 *   Lightweight stand-in for `@radix-ui/react-tabs` — used by OrchestratorPage
 *   (US-C2) and any future read-only / form-step tab UI. No portals, no
 *   keyboard arrow-navigation (defer to Radix if/when a tab UI demands it).
 *
 *   Render: row of buttons with `data-active`; consumer handles content
 *   region (mockup parity: outer page renders body conditionally on
 *   `value === item.id`). Pre-Sprint 57.18-tokens — uses `bg-muted` /
 *   `text-foreground` / `text-muted-foreground` / `border-primary` only.
 *
 * Created: 2026-05-17 (Sprint 57.19 Day 3 / US-C2)
 *
 * Modification History (newest-first):
 *   - 2026-05-17: Initial creation (Sprint 57.19 Day 3 / US-C2)
 *
 * Related:
 *   - reference/design-mockups/ui.jsx (canonical Tabs shape)
 *   - reference/design-mockups/page-agents.jsx (consumer)
 *   - frontend/src/pages/orchestrator/OrchestratorPage.tsx (consumer)
 */

import type { FC } from "react";

export interface TabItem {
  id: string;
  label: string;
  count?: number;
}

export interface TabsProps {
  items: TabItem[];
  value: string;
  onChange: (id: string) => void;
  ariaLabel?: string;
}

export const Tabs: FC<TabsProps> = ({ items, value, onChange, ariaLabel }) => (
  <div
    role="tablist"
    aria-label={ariaLabel}
    className="flex items-center gap-1 border-b border-border"
  >
    {items.map((t) => {
      const active = value === t.id;
      return (
        <button
          key={t.id}
          type="button"
          role="tab"
          aria-selected={active}
          data-active={active}
          onClick={() => onChange(t.id)}
          className={`flex items-center gap-2 border-b-2 px-3 py-2 text-[12.5px] transition-colors ${
            active
              ? "border-primary text-foreground"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          {t.label}
          {t.count != null && (
            <span className="rounded-full bg-muted px-1.5 text-[10.5px] text-muted-foreground">
              {t.count}
            </span>
          )}
        </button>
      );
    })}
  </div>
);

export default Tabs;

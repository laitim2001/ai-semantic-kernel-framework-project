/**
 * File: frontend/src/features/chat_v2/components/ChatLayout.tsx
 * Purpose: 3-column shell — sessions sidebar / conversation / inspector sidebar.
 * Category: Frontend / chat_v2 / components
 * Scope: Phase 50 / Sprint 50.2 (Day 3.6)
 *
 * Description:
 *   Minimal version of the layout sketched in 16-frontend-design.md Chat 頁面設計.
 *   Sprint 50.2 fills only the conversation column; sidebar + inspector are
 *   placeholders until 51.x (sessions list) and 52.x (inspector with token /
 *   memory layers / verifier state).
 *
 *   Layout uses CSS Grid 3-column. Inline styles only (no CSS framework
 *   committed to the V2 frontend yet — Tailwind / shadcn arrives in 53.4).
 *
 * Created: 2026-04-30 (Sprint 50.2 Day 3.6)
 * Last Modified: 2026-04-30
 *
 * Modification History:
 *   - 2026-04-30: Initial creation (Sprint 50.2 Day 3.6)
 *
 * Related:
 *   - 16-frontend-design.md §Chat 頁面設計
 *   - MessageList / InputBar (Day 4)
 */

import type { CSSProperties, ReactNode } from "react";

type Props = {
  children: ReactNode;
};

const styles: Record<string, CSSProperties> = {
  page: {
    display: "grid",
    gridTemplateColumns: "240px 1fr 280px",
    gridTemplateRows: "56px 1fr",
    gridTemplateAreas: '"header header header" "sidebar main inspector"',
    height: "100vh",
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
    background: "#f7f8fa",
  },
  header: {
    gridArea: "header",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "0 1.25rem",
    borderBottom: "1px solid #e2e6ee",
    background: "#fff",
  },
  sidebar: {
    gridArea: "sidebar",
    borderRight: "1px solid #e2e6ee",
    background: "#fbfbfd",
    padding: "1rem",
    fontSize: 14,
    color: "#3b4252",
    overflowY: "auto",
  },
  main: {
    gridArea: "main",
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  },
  inspector: {
    gridArea: "inspector",
    borderLeft: "1px solid #e2e6ee",
    background: "#fbfbfd",
    padding: "1rem",
    fontSize: 13,
    color: "#3b4252",
    overflowY: "auto",
  },
  placeholder: {
    color: "#7c8696",
    fontSize: 13,
    lineHeight: 1.5,
  },
};

export default function ChatLayout({ children }: Props): JSX.Element {
  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <strong>Chat V2 — Phase 50.2</strong>
        <span style={{ fontSize: 12, color: "#7c8696" }}>
          Sprint 50.2 Day 3 skeleton
        </span>
      </header>

      <aside style={styles.sidebar}>
        <h3 style={{ marginTop: 0, fontSize: 13, color: "#5a6377" }}>Sessions</h3>
        <p style={styles.placeholder}>
          Session list lands in Phase 51.x (when DB-backed session storage is wired).
          For now, each page reload starts a new in-memory session.
        </p>
      </aside>

      <main style={styles.main}>{children}</main>

      <aside style={styles.inspector}>
        <h3 style={{ marginTop: 0, fontSize: 13, color: "#5a6377" }}>Inspector</h3>
        <p style={styles.placeholder}>
          Token / cost tracker (52.1+), memory layer inspector (51.2),
          verification status (54.1) — coming in later sprints.
        </p>
      </aside>
    </div>
  );
}

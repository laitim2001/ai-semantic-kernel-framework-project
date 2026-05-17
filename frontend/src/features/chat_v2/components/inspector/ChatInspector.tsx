/**
 * File: frontend/src/features/chat_v2/components/inspector/ChatInspector.tsx
 * Purpose: Right-rail Inspector placeholder — Day 3 stub; full 4-tab frame ships Day 4 §4.1.
 * Category: Frontend / chat_v2 / components / inspector
 * Scope: Phase 57.21 Day 3 §3.2 placeholder → Day 4 §4.1 full rewrite (AD-ChatV2-Full-Mockup-Fidelity Phase-1)
 *
 * Description:
 *   Day 3 lands a thin stub so ChatLayout has a right-rail mount target.
 *   Day 4 rewrites this to host the 4-tab frame (Turn / Trace / Memory / Tree)
 *   per mockup L371-390. Day 4 will populate the Turn tab (InspectorTurn);
 *   Trace / Memory / Tree tabs use `<ComingSoonInspectorTab>` placeholders.
 *
 * Created: 2026-05-17 (Sprint 57.21 Day 3 §3.2 stub)
 *
 * Modification History:
 *   - 2026-05-17: Initial Day 3 stub (Sprint 57.21 Day 3 §3.2)
 *
 * Related:
 *   - reference/design-mockups/page-chat.jsx L371-390 (ChatInspector source — Day 4 target)
 *   - ../ChatLayout.tsx (right rail consumer)
 */

import { useTranslation } from "react-i18next";

export function ChatInspector(): JSX.Element {
  const { t } = useTranslation("common");
  return (
    <aside
      data-testid="chat-inspector"
      className="flex h-full flex-col overflow-y-auto border-l border-border bg-bg-1 p-4 text-[13px] text-fg"
    >
      <h3 className="m-0 mb-2 text-[13px] font-semibold text-fg">Inspector</h3>
      <p className="text-[12px] leading-relaxed text-fg-muted">{t("chat.inspector.comingSoon")}</p>
    </aside>
  );
}

export default ChatInspector;

/**
 * File: frontend/src/components/ComingSoonPlaceholder.tsx
 * Purpose: Universal stub page for PROP/DRAFT routes not yet ported from mockup.
 * Category: Frontend / components / scaffolding
 * Scope: Phase 57 / Sprint 57.18 US-C2
 *
 * Description:
 *   Renders for any of the PROP route stubs registered in routes.config.ts.
 *   Uses React Router useLocation() to identify which route is rendering this
 *   component, then looks up the matching RouteEntry to display:
 *     - Route name (i18n nameKey) + lucide icon
 *     - "Coming Soon" muted text + mockup file hint (page-<X>.jsx)
 *     - PROP / DRAFT badge replicating Sidebar logic
 *     - Sprint 57.19+ priority badge for the 7 priority units
 *     - Dev-only "Open mockup" link to http://localhost:8080/...
 *
 *   Sprint 57.19+ rolling port replaces each wrapper's re-export with a real
 *   page implementation. INTEGRATION-LOG.md tracks port progress.
 *
 * Created: 2026-05-16 (Sprint 57.18 Day 2)
 * Last Modified: 2026-05-16
 *
 * Modification History:
 *   - 2026-05-16: Initial creation (Sprint 57.18 US-C2)
 *
 * Related:
 *   - frontend/src/routes.config.ts (ROUTES single-source)
 *   - design/operator-portal/INTEGRATION-LOG.md (port tracking)
 *   - design/operator-portal/page-<X>.jsx (mockup design source)
 */

import { useTranslation } from "react-i18next";
import { useLocation } from "react-router-dom";

import { ROUTES } from "@/routes.config";

const PRIORITY_IDS = new Set([
  "overview",
  "orchestrator",
  "subagents",
  "state-inspector",
  "redaction",
  "error-policy",
  "audit-log",
]);

/** Heuristic: id → mockup file hint (best effort; authoritative mapping in INTEGRATION-LOG.md). */
const MOCKUP_FILE_HINT: Record<string, string> = {
  overview: "page-overview.jsx",
  orchestrator: "page-agents.jsx (orchestrator section)",
  subagents: "page-agents.jsx (subagents section)",
  "subagent-tree": "page-agents.jsx (subagent-tree section)",
  "state-inspector": "page-platform.jsx",
  compaction: "page-platform.jsx",
  "jit-retrieval": "page-models.jsx",
  "error-policy": "page-platform.jsx",
  incidents: "page-extras.jsx",
  redaction: "page-governance.jsx",
  "cache-manager": "page-models.jsx",
  sse: "page-sse.jsx",
  devui: "page-platform2.jsx",
  models: "page-models.jsx",
  tools: "page-tools.jsx",
  "tenant-onboarding": "page-platform2.jsx",
  pricing: "page-admin.jsx",
  rbac: "page-admin.jsx",
};

const ComingSoonPlaceholder = () => {
  const { t } = useTranslation("common");
  const location = useLocation();
  const entry = ROUTES.find((r) => r.path === location.pathname);

  if (!entry) {
    return (
      <main className="p-8" aria-labelledby="not-registered-heading">
        <h1 id="not-registered-heading" className="text-2xl font-semibold">
          {t("comingSoon.notRegistered")}
        </h1>
        <p className="mt-2 text-muted-foreground">{location.pathname}</p>
      </main>
    );
  }

  const Icon = entry.icon;
  const id = entry.path.replace(/^\//, "").replace(/^admin\//, "");
  const mockupHint = MOCKUP_FILE_HINT[id] ?? "design/operator-portal/";
  const isPriority = PRIORITY_IDS.has(id);

  return (
    <main className="p-8 max-w-3xl" aria-labelledby="coming-soon-heading">
      <div className="flex flex-wrap items-center gap-3 mb-2">
        <Icon size={28} className="text-muted-foreground" aria-hidden="true" />
        <h1 id="coming-soon-heading" className="text-2xl font-semibold">
          {t(entry.nameKey, entry.name)}
        </h1>
        {entry.proposed && (
          <span className="rounded bg-thinking/16 px-2 py-0.5 text-[10px] font-medium uppercase text-thinking">
            PROP
          </span>
        )}
        {entry.designed && !entry.active && (
          <span className="rounded bg-warning/16 px-2 py-0.5 text-[10px] font-medium uppercase text-warning">
            DRAFT
          </span>
        )}
        {isPriority && (
          <span className="rounded bg-info/16 px-2 py-0.5 text-[10px] font-medium uppercase text-info">
            Priority port
          </span>
        )}
      </div>
      <p className="text-muted-foreground">
        {t("comingSoon.designedIn", { file: mockupHint })}
      </p>
      {import.meta.env.DEV && (
        <a
          href={`http://localhost:8080/#${entry.path}`}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-4 inline-block text-sm text-primary hover:underline"
        >
          {t("comingSoon.openMockup")} →
        </a>
      )}
      <p className="mt-6 text-xs text-muted-foreground">
        {t("comingSoon.sprintEpic")}
      </p>
    </main>
  );
};

export default ComingSoonPlaceholder;

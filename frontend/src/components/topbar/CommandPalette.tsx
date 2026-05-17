/**
 * File: frontend/src/components/topbar/CommandPalette.tsx
 * Purpose: ⌘K command palette — fuzzy search over ROUTES + quick actions + tenant + session shortcuts.
 * Category: Frontend / components / topbar (Cat 12 cross-cutting UX)
 * Scope: Phase 57 / Sprint 57.19 Day 5 / US-D1
 *
 * Description:
 *   Mockup port from reference/design-mockups/topbar-overlays.jsx CommandPalette.
 *   Opens via global Cmd+K (mac) / Ctrl+K (win/linux) hotkey mounted by AppShellV2.
 *
 *   Groups (filtered by query):
 *     - Actions (4 fixed: new chat / review HITL / onboard tenant / declare incident)
 *     - Pages (top 8 ROUTES matched by id / nameKey label / path)
 *     - Tenants (3 mockup fixtures — surfaced when query non-empty)
 *     - Sessions (3 mockup fixtures — surfaced when query starts with sess/s_/hex chars)
 *
 *   Keyboard: ↑↓ navigate, Enter open, Esc close. cmdk provides natively.
 *
 *   Backend wiring: deferred to Sprint 57.20+ (tenant + session feeds via Cat 7/Cat 11 read facade).
 *   Current sprint = mockup-fidelity port with fixture data.
 *
 * Created: 2026-05-17 (Sprint 57.19 Day 5 / US-D1)
 *
 * Modification History:
 *   - 2026-05-17: Initial creation (Sprint 57.19 Day 5 / US-D1) — mockup port + cmdk integration
 *
 * Related:
 *   - reference/design-mockups/topbar-overlays.jsx (canonical mockup source)
 *   - frontend/src/components/AppShellV2.tsx (mounts CommandPalette + ⌘K hotkey)
 *   - frontend/src/routes.config.ts (ROUTES source for page group)
 */

import { Command } from "cmdk";
import {
  AlertTriangle,
  ArrowRight,
  Building2,
  CheckCheck,
  MessageSquare,
  Search,
  UserPlus,
  Workflow,
  type LucideIcon,
} from "lucide-react";
import { type FC, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { Dialog, DialogContent, DialogTitle } from "@/components/ui";
import { ROUTES } from "@/routes.config";

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface ExtraAction {
  id: string;
  icon: LucideIcon;
  labelKey: string;
  hintKey: string;
  routeId: string;
}

const EXTRA_ACTIONS: ExtraAction[] = [
  { id: "act-new-chat", icon: MessageSquare, labelKey: "topbar.commandPalette.actions.newChat", hintKey: "topbar.commandPalette.actions.newChatHint", routeId: "chat-v2" },
  { id: "act-review", icon: CheckCheck, labelKey: "topbar.commandPalette.actions.reviewHitl", hintKey: "topbar.commandPalette.actions.reviewHitlHint", routeId: "governance" },
  { id: "act-onboard", icon: UserPlus, labelKey: "topbar.commandPalette.actions.onboardTenant", hintKey: "topbar.commandPalette.actions.onboardTenantHint", routeId: "tenant-onboarding" },
  { id: "act-incident", icon: AlertTriangle, labelKey: "topbar.commandPalette.actions.declareIncident", hintKey: "topbar.commandPalette.actions.declareIncidentHint", routeId: "incidents" },
];

const TENANT_FIXTURES = [
  { id: "t1", name: "acme-prod", region: "ap-east-1", plan: "Pro" },
  { id: "t2", name: "globex-eu", region: "eu-west-1", plan: "Pro" },
  { id: "t3", name: "initech-jp", region: "ap-northeast-1", plan: "Enterprise" },
];

const SESSION_FIXTURES = [
  { id: "sess_8a2f1c3", agent: "incident-responder", tenant: "acme-prod", status: "running" },
  { id: "sess_7c11d9e", agent: "compliance-auditor", tenant: "globex-eu", status: "hitl-paused" },
  { id: "sess_4f88c1a", agent: "rca-explorer", tenant: "acme-prod", status: "verifying" },
];

export const CommandPalette: FC<CommandPaletteProps> = ({ open, onOpenChange }) => {
  const { t } = useTranslation("common");
  const navigate = useNavigate();
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!open) setQuery("");
  }, [open]);

  const lower = query.trim().toLowerCase();
  const matchesQuery = (s: string): boolean => lower === "" || s.toLowerCase().includes(lower);

  const goRoute = (routeId: string): void => {
    const route = ROUTES.find((r) => r.path.endsWith(routeId) || r.path.slice(1) === routeId);
    if (route) navigate(route.path);
    onOpenChange(false);
  };

  const matchedPages = ROUTES
    .filter((r) => r.active)
    .filter((r) => matchesQuery(r.path) || matchesQuery(t(r.nameKey)) || matchesQuery(r.name))
    .slice(0, 8);

  const matchedActions = EXTRA_ACTIONS.filter((a) => matchesQuery(t(a.labelKey)) || matchesQuery(t(a.hintKey)));

  const matchedTenants = lower
    ? TENANT_FIXTURES.filter((tn) => matchesQuery(tn.name))
    : [];

  const matchedSessions = lower && /^(sess|s_|[a-f0-9]{2,})/i.test(lower)
    ? SESSION_FIXTURES.filter((s) => s.id.toLowerCase().includes(lower))
    : [];

  const totalCount = matchedActions.length + matchedPages.length + matchedTenants.length + matchedSessions.length;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="overflow-hidden p-0 sm:max-w-xl">
        <DialogTitle className="sr-only">{t("topbar.commandPalette.title")}</DialogTitle>
        <Command shouldFilter={false} className="bg-background text-foreground">
          <div className="flex items-center gap-2 border-b border-border px-3.5 py-3">
            <Search size={15} className="text-muted-foreground" />
            <Command.Input
              value={query}
              onValueChange={setQuery}
              placeholder={t("topbar.commandPalette.placeholder")}
              className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
              // eslint-disable-next-line jsx-a11y/no-autofocus -- modal dialog first-input autofocus is the a11y-correct pattern (per mockup parity + WCAG 2.4.3)
              autoFocus
            />
            <span className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
              ESC
            </span>
          </div>

          <Command.List className="max-h-[60vh] overflow-y-auto p-1">
            {totalCount === 0 ? (
              <Command.Empty className="flex flex-col items-center gap-2 py-8 text-muted-foreground">
                <Search size={20} />
                <div className="text-xs">{t("topbar.commandPalette.empty")}</div>
              </Command.Empty>
            ) : (
              <>
                {matchedActions.length > 0 && (
                  <Command.Group heading={t("topbar.commandPalette.groups.actions")} className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:pb-1 [&_[cmdk-group-heading]]:pt-2 [&_[cmdk-group-heading]]:font-mono [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider [&_[cmdk-group-heading]]:text-muted-foreground">
                    {matchedActions.map((a) => {
                      const ActionIcon = a.icon;
                      return (
                        <Command.Item
                          key={a.id}
                          value={`action-${a.id}`}
                          onSelect={() => goRoute(a.routeId)}
                          className="flex cursor-pointer items-center gap-2.5 rounded-md px-3 py-2 text-sm aria-selected:bg-accent aria-selected:text-accent-foreground"
                        >
                          <ActionIcon size={14} className="text-muted-foreground" />
                          <span className="flex-1">{t(a.labelKey)}</span>
                          <span className="font-mono text-[11px] text-muted-foreground">{t(a.hintKey)}</span>
                          <ArrowRight size={11} className="text-muted-foreground opacity-0 aria-selected:opacity-100" />
                        </Command.Item>
                      );
                    })}
                  </Command.Group>
                )}

                {matchedPages.length > 0 && (
                  <Command.Group heading={t("topbar.commandPalette.groups.pages")} className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:pb-1 [&_[cmdk-group-heading]]:pt-2 [&_[cmdk-group-heading]]:font-mono [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider [&_[cmdk-group-heading]]:text-muted-foreground">
                    {matchedPages.map((r) => {
                      const RouteIcon = r.icon;
                      return (
                        <Command.Item
                          key={r.path}
                          value={`page-${r.path}`}
                          onSelect={() => { navigate(r.path); onOpenChange(false); }}
                          className="flex cursor-pointer items-center gap-2.5 rounded-md px-3 py-2 text-sm aria-selected:bg-accent aria-selected:text-accent-foreground"
                        >
                          <RouteIcon size={14} className="text-muted-foreground" />
                          <span className="flex-1">{t(r.nameKey)}</span>
                          <span className="font-mono text-[11px] text-muted-foreground">{r.path}</span>
                        </Command.Item>
                      );
                    })}
                  </Command.Group>
                )}

                {matchedTenants.length > 0 && (
                  <Command.Group heading={t("topbar.commandPalette.groups.tenants")} className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:pb-1 [&_[cmdk-group-heading]]:pt-2 [&_[cmdk-group-heading]]:font-mono [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider [&_[cmdk-group-heading]]:text-muted-foreground">
                    {matchedTenants.map((tn) => (
                      <Command.Item
                        key={tn.id}
                        value={`tenant-${tn.id}`}
                        onSelect={() => goRoute("admin-tenants")}
                        className="flex cursor-pointer items-center gap-2.5 rounded-md px-3 py-2 text-sm aria-selected:bg-accent aria-selected:text-accent-foreground"
                      >
                        <Building2 size={14} className="text-muted-foreground" />
                        <span className="flex-1">{tn.name}</span>
                        <span className="font-mono text-[11px] text-muted-foreground">{tn.region} · {tn.plan}</span>
                      </Command.Item>
                    ))}
                  </Command.Group>
                )}

                {matchedSessions.length > 0 && (
                  <Command.Group heading={t("topbar.commandPalette.groups.sessions")} className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:pb-1 [&_[cmdk-group-heading]]:pt-2 [&_[cmdk-group-heading]]:font-mono [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider [&_[cmdk-group-heading]]:text-muted-foreground">
                    {matchedSessions.map((s) => (
                      <Command.Item
                        key={s.id}
                        value={`session-${s.id}`}
                        onSelect={() => goRoute("loop-debug")}
                        className="flex cursor-pointer items-center gap-2.5 rounded-md px-3 py-2 text-sm aria-selected:bg-accent aria-selected:text-accent-foreground"
                      >
                        <Workflow size={14} className="text-muted-foreground" />
                        <span className="flex-1 font-mono">{s.id}</span>
                        <span className="font-mono text-[11px] text-muted-foreground">{s.agent} · {s.status}</span>
                      </Command.Item>
                    ))}
                  </Command.Group>
                )}
              </>
            )}
          </Command.List>

          <div className="flex items-center gap-3.5 border-t border-border px-3.5 py-2 font-mono text-[10.5px] text-muted-foreground">
            <span><kbd className="rounded border border-border bg-muted px-1 py-0.5 text-[9px]">↑↓</kbd> {t("topbar.commandPalette.footer.navigate")}</span>
            <span><kbd className="rounded border border-border bg-muted px-1 py-0.5 text-[9px]">↵</kbd> {t("topbar.commandPalette.footer.open")}</span>
            <span><kbd className="rounded border border-border bg-muted px-1 py-0.5 text-[9px]">ESC</kbd> {t("topbar.commandPalette.footer.close")}</span>
            <span className="flex-1" />
            <span>{totalCount} {t("topbar.commandPalette.footer.results")}</span>
          </div>
        </Command>
      </DialogContent>
    </Dialog>
  );
};

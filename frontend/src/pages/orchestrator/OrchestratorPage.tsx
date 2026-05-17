/**
 * File: frontend/src/pages/orchestrator/OrchestratorPage.tsx
 * Purpose: Orchestrator config page — port from reference/design-mockups/page-agents.jsx Orchestrator.
 * Category: Frontend / pages / orchestrator
 * Scope: Phase 57 / Sprint 57.19 Day 3 / US-C2
 *
 * Description:
 *   1:1 port of mockup `Orchestrator` component with 6 sub-tabs:
 *     Config / Prompt / Tools / Subagents / Budgets / Policies
 *
 *   Sprint 57.19 ships a read-only / fixture-driven version. Sprint 57.20+
 *   retrofit will wire Config inputs to a future Cat 1 orchestrator-config API
 *   (AD-Orchestrator-Backend-Wire bundle).
 *
 *   Mockup-fidelity hard constraint (CLAUDE.md): visual layout / padding /
 *   radius / colour follow page-agents.jsx exactly. Form inputs render as
 *   disabled mock fields with mockup `defaultValue`s.
 *
 * Created: 2026-05-17 (Sprint 57.19 Day 3 / US-C2)
 *
 * Modification History (newest-first):
 *   - 2026-05-17: Initial creation (Sprint 57.19 Day 3 / US-C2)
 *
 * Related:
 *   - reference/design-mockups/page-agents.jsx (canonical visual source)
 *   - frontend/src/components/ui/tabs.tsx (NEW Tabs primitive — Sprint 57.19)
 *   - frontend/src/components/AppShellV2.tsx (page-level shell)
 */

import { Bolt, GitBranch, Play, Plus } from "lucide-react";
import type { FC, ReactNode } from "react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { AppShellV2 } from "@/components/AppShellV2";
import { Tabs } from "@/components/ui/tabs";
import { RequireAuth } from "@/features/auth/components/RequireAuth";

// ───────────────── primitives (mockup parity inline) ─────────────────

type Tone = "success" | "warning" | "danger" | "thinking" | "info" | "primary" | "tool" | "memory" | "muted";

const TONE_CLASS: Record<Tone, string> = {
  success: "bg-success/16 text-success",
  warning: "bg-warning/16 text-warning",
  danger: "bg-danger/16 text-danger",
  thinking: "bg-thinking/16 text-thinking",
  info: "bg-info/16 text-info",
  primary: "bg-primary/16 text-primary",
  tool: "bg-tool/16 text-tool",
  memory: "bg-memory/16 text-memory",
  muted: "bg-muted text-muted-foreground",
};

const Badge: FC<{ tone?: Tone; dot?: boolean; children: ReactNode }> = ({
  tone = "muted",
  dot,
  children,
}) => (
  <span
    className={`inline-flex items-center gap-1 rounded-full px-2 py-[2px] text-[10.5px] font-medium ${TONE_CLASS[tone]}`}
  >
    {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
    {children}
  </span>
);

const RISK_TONE: Record<string, Tone> = {
  low: "success",
  medium: "info",
  high: "warning",
  critical: "danger",
};

const RiskBadge: FC<{ level: string }> = ({ level }) => (
  <Badge tone={RISK_TONE[level] ?? "muted"}>{level}</Badge>
);

interface CardProps {
  title?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
}

const Card: FC<CardProps> = ({ title, subtitle, actions, children }) => (
  <div className="rounded-[12px] border border-border bg-card text-card-foreground">
    {(title || actions) && (
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div>
          {title && <div className="text-sm font-semibold">{title}</div>}
          {subtitle && <div className="text-[11px] text-muted-foreground">{subtitle}</div>}
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
    )}
    <div className="p-4">{children}</div>
  </div>
);

const Stat: FC<{ label: string; value: string; unit?: string; delta?: string; deltaDir?: "up" | "down" }> = ({
  label,
  value,
  unit,
  delta,
  deltaDir = "up",
}) => (
  <div className="rounded-[12px] border border-border bg-card p-4">
    <div className="flex items-center justify-between text-[11px] text-muted-foreground">
      <span>{label}</span>
      {delta && (
        <span
          className={deltaDir === "up" ? "text-success text-[10.5px]" : "text-warning text-[10.5px]"}
        >
          {deltaDir === "up" ? "▲" : "▼"} {delta}
        </span>
      )}
    </div>
    <div className="mt-1 font-mono text-[22px] font-semibold tabular-nums">
      {value}
      {unit && <span className="ml-1 text-[11px] font-normal text-muted-foreground">{unit}</span>}
    </div>
  </div>
);

const Field: FC<{ label: string; help?: string; children: ReactNode }> = ({ label, help, children }) => (
  <div className="flex flex-col gap-1.5">
    <label className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
      {label}
    </label>
    {children}
    {help && <div className="text-[11px] text-muted-foreground">{help}</div>}
  </div>
);

const inputBase =
  "w-full rounded-[6px] border border-border bg-muted/30 px-3 py-[6px] font-mono text-[12px] text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary";

const TextInput: FC<{ defaultValue?: string; readOnly?: boolean }> = ({ defaultValue, readOnly }) => (
  <input className={inputBase} defaultValue={defaultValue} readOnly={readOnly} />
);

const Select: FC<{ options: string[]; defaultValue?: string }> = ({ options, defaultValue }) => (
  <select className={inputBase} defaultValue={defaultValue}>
    {options.map((o) => (
      <option key={o}>{o}</option>
    ))}
  </select>
);

const Switch: FC<{ on?: boolean; label?: ReactNode }> = ({ on, label }) => (
  <label className="flex cursor-pointer items-center gap-2 text-[12px]">
    <span
      className={`inline-flex h-4 w-7 items-center rounded-full border border-border transition-colors ${on ? "bg-primary" : "bg-muted"}`}
    >
      <span
        className={`mx-[1px] h-3 w-3 rounded-full bg-white transition-transform ${on ? "translate-x-3" : ""}`}
      />
    </span>
    {label}
  </label>
);

// ───────────────── 6 tab bodies ─────────────────

const ConfigTab: FC = () => {
  const { t } = useTranslation();
  return (
    <div className="grid grid-cols-[1fr_1fr] gap-[14px]">
      <Card title={t("orchestrator.config.core")}>
        <div className="flex max-w-[540px] flex-col gap-[14px]">
          <Field label="Display name">
            <TextInput defaultValue="orchestrator-main" />
          </Field>
          <Field label="Primary model" help="LLM-neutral; concrete provider chosen by adapter">
            <Select
              defaultValue="claude-haiku-4-5"
              options={["claude-haiku-4-5", "claude-sonnet-4-5", "claude-opus-4-1", "gpt-5", "azure-openai-gpt-4o"]}
            />
          </Field>
          <Field label="Fallback model" help="Used when primary circuit breaker opens">
            <Select defaultValue="claude-sonnet-4-5" options={["claude-sonnet-4-5", "claude-opus-4-1"]} />
          </Field>
          <div className="grid grid-cols-2 gap-[14px]">
            <Field label="Temperature">
              <TextInput defaultValue="0.2" />
            </Field>
            <Field label="Top P">
              <TextInput defaultValue="0.95" />
            </Field>
          </div>
          <Field label="Max thinking tokens / turn">
            <TextInput defaultValue="2048" />
          </Field>
          <Field label="Termination policy">
            <Select
              defaultValue="end_turn (default)"
              options={["end_turn (default)", "max_turns", "budget_exhausted"]}
            />
          </Field>
        </div>
      </Card>
      <div className="flex flex-col gap-[14px]">
        <Card title={t("orchestrator.config.memoryAccess")} subtitle={t("orchestrator.config.memoryAccessSub")}>
          <div className="flex flex-col gap-[10px] text-[12.5px]">
            {(["system", "tenant", "role", "user", "session"] as const).map((s) => (
              <div key={s} className="flex items-center justify-between">
                <span className="font-mono">{s}</span>
                <Select
                  defaultValue={s === "system" ? "read" : "write"}
                  options={["none", "read", "write"]}
                />
              </div>
            ))}
          </div>
        </Card>
        <Card title={t("orchestrator.config.verification")} subtitle={t("orchestrator.config.verificationSub")}>
          <div className="flex flex-col gap-2 text-[12px]">
            <Switch on label="Require verification before write tools" />
            <Switch on label="Block on failed verification" />
            <Switch label="Skip verification for risk=low tools" />
          </div>
        </Card>
      </div>
    </div>
  );
};

const SYSTEM_PROMPT_PREVIEW = `# Role
You are the orchestrator agent for IPA Platform V2 — an enterprise AI operations platform for {{tenant_name}}.

# Goal
Receive operator requests, plan a sequence of actions, dispatch to specialized subagents when the task is complex, and produce a verified outcome with HITL gating for any write action.

# Available subagents (call as_tool or fork)
- log-scanner — tail + grep logs from a service
- dep-checker — health-probe downstream services
- metrics-pull — query observability backend
- evidence-collector — assemble RCA evidence bundle
- compliance-auditor — answer audit queries with citations

# Tool use policy
- Read tools: auto-call when needed.
- Write tools: ALWAYS request HITL approval first (see range 9).
- If a tool fails 3× with TRANSIENT class, escalate to a teammate subagent.

# Output discipline
- Always emit a short reasoning trace.
- Final answer must cite tool calls + memory reads as evidence.

# Constraints
- Never promise timelines.
- Never expose internal tooling names to non-operator roles.
- Always respect tenant_id boundary; cross-tenant access is a tripwire.`;

const PromptTab: FC = () => {
  const { t } = useTranslation();
  return (
    <div className="grid grid-cols-[1fr_320px] gap-[14px]">
      <Card
        title={t("orchestrator.prompt.title")}
        subtitle={t("orchestrator.prompt.subtitle")}
        actions={
          <>
            <Badge tone="primary">{t("orchestrator.version")}</Badge>
            <button
              type="button"
              className="inline-flex items-center gap-1 rounded-[6px] px-2 py-1 text-[11px] text-muted-foreground hover:text-foreground"
            >
              <GitBranch className="h-3 w-3" /> {t("orchestrator.prompt.history")}
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-1 rounded-[6px] border border-border px-2 py-1 text-[11px] hover:bg-muted/40"
            >
              <Play className="h-3 w-3" /> {t("orchestrator.prompt.test")}
            </button>
          </>
        }
      >
        <textarea
          rows={20}
          readOnly
          defaultValue={SYSTEM_PROMPT_PREVIEW}
          className={`${inputBase} h-[480px] resize-none whitespace-pre`}
        />
      </Card>
      <Card title={t("orchestrator.prompt.variables")}>
        <div className="flex flex-col gap-2 text-[12px]">
          {[
            { k: "tenant_name", v: "string", req: true },
            { k: "operator_role", v: "enum", req: true },
            { k: "locale", v: "string", req: false },
            { k: "time_zone", v: "string", req: false },
          ].map((x) => (
            <div key={x.k} className="flex items-center justify-between">
              <span className="font-mono text-[11.5px]">{`{{${x.k}}}`}</span>
              <div className="flex items-center gap-1">
                <Badge>{x.v}</Badge>
                {x.req && <Badge tone="warning">required</Badge>}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};

interface ToolRow {
  id: string;
  domain: string;
  risk: string;
  sandbox: "NONE" | "RESTRICTED" | "FULL_SANDBOX";
  on: boolean;
}

const TOOLS_FIXTURE: ToolRow[] = [
  { id: "incidents.list", domain: "rca", risk: "low", sandbox: "NONE", on: true },
  { id: "metrics.query", domain: "rca", risk: "low", sandbox: "NONE", on: true },
  { id: "log.tail", domain: "rca", risk: "low", sandbox: "NONE", on: true },
  { id: "log.grep", domain: "rca", risk: "medium", sandbox: "RESTRICTED", on: true },
  { id: "evidence.attach", domain: "rca", risk: "medium", sandbox: "RESTRICTED", on: true },
  { id: "audit_query_logs", domain: "audit", risk: "medium", sandbox: "RESTRICTED", on: true },
  { id: "redact_pii", domain: "audit", risk: "high", sandbox: "RESTRICTED", on: false },
  { id: "page_oncall", domain: "incident", risk: "high", sandbox: "RESTRICTED", on: true },
  { id: "k8s.set_env", domain: "incident", risk: "high", sandbox: "FULL_SANDBOX", on: false },
  { id: "k8s.rollback", domain: "incident", risk: "critical", sandbox: "FULL_SANDBOX", on: false },
];

const SANDBOX_TONE: Record<ToolRow["sandbox"], Tone> = {
  NONE: "success",
  RESTRICTED: "warning",
  FULL_SANDBOX: "danger",
};

const ToolsTab: FC = () => {
  const { t } = useTranslation();
  return (
    <Card
      title={t("orchestrator.tools.title")}
      subtitle={t("orchestrator.tools.subtitle")}
      actions={
        <button
          type="button"
          className="inline-flex items-center gap-1 rounded-[6px] bg-primary px-2 py-1 text-[11px] text-primary-foreground hover:bg-primary/90"
        >
          <Plus className="h-3 w-3" /> {t("orchestrator.tools.openRegistry")}
        </button>
      }
    >
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-[12px]">
          <thead className="text-left text-[11px] uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="border-b border-border pb-2 pr-3">Tool</th>
              <th className="border-b border-border pb-2 pr-3">Domain</th>
              <th className="border-b border-border pb-2 pr-3">Risk</th>
              <th className="border-b border-border pb-2 pr-3">Sandbox</th>
              <th className="border-b border-border pb-2">Enabled</th>
            </tr>
          </thead>
          <tbody>
            {TOOLS_FIXTURE.map((row) => (
              <tr key={row.id} className="border-b border-border last:border-0">
                <td className="py-2 pr-3 font-mono">{row.id}</td>
                <td className="py-2 pr-3">
                  <Badge>{row.domain}</Badge>
                </td>
                <td className="py-2 pr-3">
                  <RiskBadge level={row.risk} />
                </td>
                <td className="py-2 pr-3">
                  <Badge tone={SANDBOX_TONE[row.sandbox]}>{row.sandbox}</Badge>
                </td>
                <td className="py-2">
                  <Switch on={row.on} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
};

const SUBAGENT_MODE_TONE: Record<string, Tone> = {
  fork: "thinking",
  as_tool: "tool",
  handoff: "info",
  teammate: "memory",
};

interface SubagentRow {
  id: string;
  modes: string[];
  max_tok: number;
  max_conc: number;
  on: boolean;
}

const SUBAGENTS_FIXTURE: SubagentRow[] = [
  { id: "log-scanner", modes: ["fork", "as_tool"], max_tok: 4000, max_conc: 3, on: true },
  { id: "dep-checker", modes: ["fork", "as_tool"], max_tok: 3000, max_conc: 3, on: true },
  { id: "metrics-pull", modes: ["fork", "as_tool"], max_tok: 2000, max_conc: 5, on: true },
  { id: "evidence-collector", modes: ["as_tool"], max_tok: 8000, max_conc: 1, on: true },
  { id: "compliance-auditor", modes: ["handoff", "teammate"], max_tok: 16000, max_conc: 1, on: true },
  { id: "postmortem-writer", modes: ["handoff"], max_tok: 8000, max_conc: 1, on: false },
];

const SubagentsTab: FC = () => {
  const { t } = useTranslation();
  return (
    <Card
      title={t("orchestrator.subagents.title")}
      subtitle={t("orchestrator.subagents.subtitle")}
      actions={
        <button
          type="button"
          className="inline-flex items-center gap-1 rounded-[6px] bg-primary px-2 py-1 text-[11px] text-primary-foreground hover:bg-primary/90"
        >
          <Plus className="h-3 w-3" /> {t("orchestrator.subagents.openRegistry")}
        </button>
      }
    >
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-[12px]">
          <thead className="text-left text-[11px] uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="border-b border-border pb-2 pr-3">Subagent</th>
              <th className="border-b border-border pb-2 pr-3">Allowed modes</th>
              <th className="border-b border-border pb-2 pr-3">Max tokens</th>
              <th className="border-b border-border pb-2 pr-3">Max concurrent</th>
              <th className="border-b border-border pb-2">Enabled</th>
            </tr>
          </thead>
          <tbody>
            {SUBAGENTS_FIXTURE.map((row) => (
              <tr key={row.id} className="border-b border-border last:border-0">
                <td className="py-2 pr-3 font-mono font-medium">{row.id}</td>
                <td className="py-2 pr-3">
                  <div className="flex flex-wrap items-center gap-1">
                    {row.modes.map((m) => (
                      <Badge key={m} tone={SUBAGENT_MODE_TONE[m] ?? "muted"}>
                        {m}
                      </Badge>
                    ))}
                  </div>
                </td>
                <td className="py-2 pr-3 font-mono tabular-nums">{row.max_tok.toLocaleString()}</td>
                <td className="py-2 pr-3 font-mono tabular-nums">{row.max_conc}</td>
                <td className="py-2">
                  <Switch on={row.on} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
};

const BUDGETS = [
  { k: "Max loop turns", v: 30, unit: "" },
  { k: "Max total tokens", v: 200000, unit: "" },
  { k: "Max wall-clock duration", v: 600, unit: "s" },
  { k: "Max subagent depth", v: 3, unit: "" },
  { k: "Max concurrent subagents", v: 5, unit: "" },
  { k: "Max tool calls / turn", v: 8, unit: "" },
];

const BudgetsTab: FC = () => {
  const { t } = useTranslation();
  return (
    <div className="grid grid-cols-[1fr_1fr] gap-[14px]">
      <Card title={t("orchestrator.budgets.loop")} subtitle={t("orchestrator.budgets.loopSub")}>
        <div className="flex flex-col gap-[14px]">
          {BUDGETS.map((b) => (
            <div key={b.k} className="grid grid-cols-[1fr_auto] items-center gap-[14px]">
              <span className="text-[12.5px]">{b.k}</span>
              <div className="flex items-center gap-2">
                <input className={`${inputBase} w-[110px]`} defaultValue={b.v} />
                {b.unit && <span className="text-[11px] text-muted-foreground">{b.unit}</span>}
              </div>
            </div>
          ))}
        </div>
      </Card>
      <Card title={t("orchestrator.budgets.termination")}>
        <div className="flex flex-col gap-2 text-[12px]">
          <Switch on label={<span>Stop on <span className="font-mono">stop_reason=end_turn</span></span>} />
          <Switch on label="Stop on max-turns reached" />
          <Switch on label="Stop on budget exhausted" />
          <Switch on label="Stop on FATAL error class" />
          <Switch label="Stop on HITL rejection" />
          <Switch on label="Stop on tripwire fired" />
        </div>
      </Card>
    </div>
  );
};

const PoliciesTab: FC = () => {
  const { t } = useTranslation();
  return (
    <Card title={t("orchestrator.policies.title")}>
      <div className="flex max-w-[720px] flex-col gap-[12px]">
        <Field label="Default HITL policy for write tools">
          <Select defaultValue="always_ask" options={["auto", "ask_once", "always_ask"]} />
        </Field>
        <Field label="Off-platform notifications">
          <div className="flex items-center gap-3 text-[12px]">
            <label className="flex items-center gap-1.5">
              <input type="checkbox" defaultChecked /> Teams
            </label>
            <label className="flex items-center gap-1.5">
              <input type="checkbox" defaultChecked /> Email
            </label>
            <label className="flex items-center gap-1.5">
              <input type="checkbox" /> PagerDuty
            </label>
          </div>
        </Field>
        <Field label="Risk escalation">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="success">low → auto</Badge>
            <Badge tone="info">medium → ask_once</Badge>
            <Badge tone="warning">high → always_ask</Badge>
            <Badge tone="danger">critical → always_ask + L2</Badge>
          </div>
        </Field>
        <div className="my-2 border-t border-border" />
        <Field label="Cross-tenant tripwire (CANNOT disable)">
          <Badge tone="danger">armed · always-on</Badge>
        </Field>
        <Field label="PII in tool input">
          <Badge tone="danger">armed · always-on</Badge>
        </Field>
        <Field label="Provider key exposure">
          <Badge tone="danger">armed · always-on</Badge>
        </Field>
      </div>
    </Card>
  );
};

// ───────────────── page ─────────────────

type TabId = "config" | "prompt" | "tools" | "subagents" | "budgets" | "policies";

function OrchestratorPageInner(): JSX.Element {
  const { t } = useTranslation();
  const [tab, setTab] = useState<TabId>("config");

  const tabItems = [
    { id: "config", label: t("orchestrator.tabs.config") },
    { id: "prompt", label: t("orchestrator.tabs.prompt") },
    { id: "tools", label: t("orchestrator.tabs.tools"), count: 18 },
    { id: "subagents", label: t("orchestrator.tabs.subagents"), count: 6 },
    { id: "budgets", label: t("orchestrator.tabs.budgets") },
    { id: "policies", label: t("orchestrator.tabs.policies") },
  ];

  return (
    <div className="flex flex-col gap-[14px] p-[18px]">
      {/* page head */}
      <header className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[20px] font-semibold">orchestrator-main</span>
            <Badge tone="primary">{t("orchestrator.version")}</Badge>
            <Badge tone="success" dot>
              {t("orchestrator.live")}
            </Badge>
          </div>
          <div className="mt-1 text-[12.5px] text-muted-foreground">
            {t("orchestrator.subtitle")}
            <span className="ml-2 rounded-[4px] bg-muted px-[6px] py-[1px] font-mono text-[11px]">
              /orchestrator
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-[6px] border border-border bg-card px-3 py-[6px] text-[12px] hover:bg-muted/40"
          >
            <Play className="h-3.5 w-3.5" /> {t("orchestrator.actions.test")}
          </button>
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-[6px] border border-border bg-card px-3 py-[6px] text-[12px] hover:bg-muted/40"
          >
            <GitBranch className="h-3.5 w-3.5" /> {t("orchestrator.actions.viewRepo")}
          </button>
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-[6px] bg-primary px-3 py-[6px] text-[12px] text-primary-foreground hover:bg-primary/90"
          >
            <Bolt className="h-3.5 w-3.5" /> {t("orchestrator.actions.deploy")}
          </button>
        </div>
      </header>

      {/* KPI row */}
      <div className="grid grid-cols-4 gap-3">
        <Stat label={t("orchestrator.kpi.sessions24h")} value="2,847" delta="+12%" deltaDir="up" />
        <Stat label={t("orchestrator.kpi.avgTurns")} value="4.2" delta="+0.1" deltaDir="down" />
        <Stat label={t("orchestrator.kpi.subagentSpawns")} value="412" delta="+8" deltaDir="up" />
        <Stat label={t("orchestrator.kpi.p95Session")} value="18.4" unit="s" delta="-2s" deltaDir="up" />
      </div>

      {/* tabs row */}
      <Tabs
        items={tabItems}
        value={tab}
        onChange={(id) => setTab(id as TabId)}
        ariaLabel={t("orchestrator.tabs.label")}
      />

      {tab === "config" && <ConfigTab />}
      {tab === "prompt" && <PromptTab />}
      {tab === "tools" && <ToolsTab />}
      {tab === "subagents" && <SubagentsTab />}
      {tab === "budgets" && <BudgetsTab />}
      {tab === "policies" && <PoliciesTab />}
    </div>
  );
}

export function OrchestratorPage(): JSX.Element {
  const { t } = useTranslation();
  return (
    <RequireAuth>
      <AppShellV2 pageTitle={t("orchestrator.title")}>
        <OrchestratorPageInner />
      </AppShellV2>
    </RequireAuth>
  );
}

export default OrchestratorPage;

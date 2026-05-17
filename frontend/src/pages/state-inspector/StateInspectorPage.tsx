/**
 * File: frontend/src/pages/state-inspector/StateInspectorPage.tsx
 * Purpose: LoopState time-travel — port from reference/design-mockups/page-platform.jsx StateInspector.
 * Category: Frontend / pages / state-inspector
 * Scope: Phase 57 / Sprint 57.19 Day 4 / US-C4
 *
 * Description:
 *   1:1 port of mockup `StateInspector`:
 *     - 4 KPI cards (Current version / Transient size / Durable bytes / Pending approvals)
 *     - 320px / 1fr grid: left = version chain (10 mockup-fixture versions with
 *       lineage tick marks + checkpoint icon); right = current-state card (transient
 *       + durable kv-line lists) + diff-vs-parent card (pre-formatted diff text)
 *
 *   Backend wiring (per Sprint 57.19 US-B3):
 *     - GET /api/v1/sessions/{id}/state returns ONLY the latest snapshot for one
 *       session — there is no list-by-session version-chain endpoint yet
 *       (tracked as AD-State-VersionChain-Phase58).
 *     - When `?session_id=<uuid>` is provided in URL, this page calls the real
 *       backend and shows the live tenant_id / version / hash / reason atop the
 *       mockup-fixture chain (carryover banner shown).
 *     - When no session_id provided: render full mockup fixture (no live data).
 *
 * Created: 2026-05-17 (Sprint 57.19 Day 4 / US-C4)
 *
 * Modification History (newest-first):
 *   - 2026-05-17: Initial creation (Sprint 57.19 Day 4 / US-C4)
 *
 * Related:
 *   - reference/design-mockups/page-platform.jsx (StateInspector)
 *   - frontend/src/features/state/hooks/useStateSnapshot.ts (US-B3 consumer)
 *   - backend/src/api/v1/sessions.py (US-B3)
 */

import { Clock, Download, RefreshCw, Shield } from "lucide-react";
import type { FC, ReactNode } from "react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";

import { AppShellV2 } from "@/components/AppShellV2";
import { RequireAuth } from "@/features/auth/components/RequireAuth";
import { useStateSnapshot } from "@/features/state/hooks/useStateSnapshot";

// ───────────────── primitives ─────────────────

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

const Badge: FC<{ tone?: Tone; children: ReactNode }> = ({ tone = "muted", children }) => (
  <span
    className={`inline-flex items-center gap-1 rounded-full px-2 py-[2px] text-[10.5px] font-medium ${TONE_CLASS[tone]}`}
  >
    {children}
  </span>
);

const Card: FC<{ title?: ReactNode; subtitle?: ReactNode; children: ReactNode; bodyClassName?: string }> = ({
  title,
  subtitle,
  children,
  bodyClassName,
}) => (
  <div className="rounded-[12px] border border-border bg-card text-card-foreground">
    {(title || subtitle) && (
      <div className="border-b border-border px-4 py-3">
        {title && <div className="text-sm font-semibold">{title}</div>}
        {subtitle && <div className="text-[11px] text-muted-foreground">{subtitle}</div>}
      </div>
    )}
    <div className={bodyClassName ?? "p-4"}>{children}</div>
  </div>
);

const Stat: FC<{ label: string; value: string; unit?: string }> = ({ label, value, unit }) => (
  <div className="rounded-[12px] border border-border bg-card p-4">
    <div className="text-[11px] text-muted-foreground">{label}</div>
    <div className="mt-1 font-mono text-[22px] font-semibold tabular-nums">
      {value}
      {unit && <span className="ml-1 text-[11px] font-normal text-muted-foreground">{unit}</span>}
    </div>
  </div>
);

const KvLine: FC<{ k: string; v: ReactNode; mono?: boolean }> = ({ k, v, mono }) => (
  <div className="flex items-center justify-between gap-3">
    <span className="font-mono text-[11px] text-muted-foreground">{k}</span>
    <span className={mono ? "font-mono text-[11.5px] tabular-nums" : "text-[11.5px]"}>{v}</span>
  </div>
);

// ───────────────── fixture: 10 mockup versions ─────────────────

type VersionAuthor = "orchestrator_loop" | "reducer" | "tools" | "subagent" | "session_init";

interface VersionRow {
  v: number;
  parent: number | null;
  at: string;
  by: VersionAuthor;
  msg: string;
  checkpoint: boolean;
}

const STATE_VERSIONS: VersionRow[] = [
  { v: 18, parent: 17, at: "10:42:28.420", by: "orchestrator_loop", msg: "loop.iteration_4 end · stop_reason=hitl", checkpoint: false },
  { v: 17, parent: 16, at: "10:42:28.180", by: "reducer", msg: "WRITE durable: pending_approval[a8f3.k2p1]", checkpoint: true },
  { v: 16, parent: 15, at: "10:42:27.480", by: "tools", msg: "tool_result · metrics.query · 1.8KB", checkpoint: false },
  { v: 15, parent: 14, at: "10:42:25.220", by: "reducer", msg: "WRITE durable: conversation_summary", checkpoint: true },
  { v: 14, parent: 13, at: "10:42:24.020", by: "subagent", msg: "subagent.completed · log-scanner", checkpoint: false },
  { v: 13, parent: 12, at: "10:42:22.840", by: "tools", msg: "tool_result · incidents.list · 8 rows", checkpoint: false },
  { v: 12, parent: 11, at: "10:42:20.120", by: "orchestrator_loop", msg: "loop.iteration_2 end · spawn 3 subagents", checkpoint: false },
  { v: 11, parent: 10, at: "10:42:19.620", by: "reducer", msg: "compaction: hybrid · -2,140 tokens", checkpoint: true },
  { v: 10, parent: 9, at: "10:42:18.840", by: "orchestrator_loop", msg: "loop.iteration_1 end · stop_reason=tool_use", checkpoint: false },
  { v: 9, parent: 8, at: "10:42:18.020", by: "session_init", msg: "session_id=sess_4tk2p · tenant=acme-prod", checkpoint: true },
];

const AUTHOR_TONE: Record<VersionAuthor, Tone> = {
  orchestrator_loop: "primary",
  reducer: "memory",
  tools: "tool",
  subagent: "info",
  session_init: "success",
};

const AUTHOR_TEXT_CLASS: Record<VersionAuthor, string> = {
  orchestrator_loop: "text-primary",
  reducer: "text-memory",
  tools: "text-tool",
  subagent: "text-info",
  session_init: "text-success",
};

const AUTHOR_BORDER_CLASS: Record<VersionAuthor, string> = {
  orchestrator_loop: "border-primary",
  reducer: "border-memory",
  tools: "border-tool",
  subagent: "border-info",
  session_init: "border-success",
};

const DIFF_TEXT = `  durable.pending_approval_ids:
- []
+ ["a8f3.k2p1"]

  transient.pending_tool_calls:
- []
+ [{ name: "k8s.set_env", tool_call_id: "tc_8a02p" }]

  transient.token_usage_so_far:
- 18,200
+ 18,420  (+220)`;

// ───────────────── page ─────────────────

function StateInspectorPageInner(): JSX.Element {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get("session_id");
  const [selected, setSelected] = useState(18);

  const current = STATE_VERSIONS.find((s) => s.v === selected) ?? STATE_VERSIONS[0];
  const parent = STATE_VERSIONS.find((s) => s.v === current.parent);

  const { data: liveSnapshot, error: liveError } = useStateSnapshot(sessionId);
  const hasLive = liveSnapshot != null;

  return (
    <div className="flex flex-col gap-[14px] p-[18px]">
      {/* page head */}
      <header className="flex items-start justify-between">
        <div className="text-[12.5px] text-muted-foreground">
          {t("stateInspector.subtitle")}
          <span className="ml-2 rounded-[4px] bg-muted px-[6px] py-[1px] font-mono text-[11px]">
            /state-inspector
          </span>
          <span className="ml-2 font-mono text-[11px] text-muted-foreground">
            · {STATE_VERSIONS.length} {t("stateInspector.versions")} · 3 {t("stateInspector.checkpoints")}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-[6px] border border-border bg-card px-3 py-[6px] text-[12px] hover:bg-muted/40"
          >
            <Clock className="h-3.5 w-3.5" /> {t("stateInspector.diffVsParent")}
          </button>
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-[6px] border border-border bg-card px-3 py-[6px] text-[12px] hover:bg-muted/40"
          >
            <RefreshCw className="h-3.5 w-3.5" /> {t("stateInspector.restore")}
          </button>
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-[6px] border border-border bg-card px-3 py-[6px] text-[12px] hover:bg-muted/40"
          >
            <Download className="h-3.5 w-3.5" /> {t("stateInspector.exportCheckpoint")}
          </button>
        </div>
      </header>

      {/* carryover banner — backend gap */}
      <div
        role="status"
        className="rounded-[8px] border border-warning/40 bg-warning/8 p-3 text-[12px] text-warning"
      >
        <strong>{t("stateInspector.carryoverHeading")}</strong>: {t("stateInspector.carryoverBody")}
      </div>

      {/* live error if backend fetch failed */}
      {liveError && (
        <div role="alert" className="rounded-[8px] border border-danger/40 bg-danger/8 p-3 text-[12px] text-danger">
          {t("stateInspector.liveFetchError")}: {liveError.message}
        </div>
      )}

      {/* KPI row */}
      <div className="grid grid-cols-4 gap-3">
        <Stat label={t("stateInspector.kpi.currentVersion")} value={`v${hasLive ? liveSnapshot.version : selected}`} />
        <Stat label={t("stateInspector.kpi.transientSize")} value="12" unit="msg" />
        <Stat label={t("stateInspector.kpi.durableBytes")} value="4.2" unit="kB" />
        <Stat label={t("stateInspector.kpi.pendingApprovals")} value="1" />
      </div>

      {/* 320px / 1fr grid: version chain + state pane */}
      <div className="grid grid-cols-[320px_1fr] gap-[14px]">
        <Card
          title={t("stateInspector.chain.title")}
          subtitle={t("stateInspector.chain.subtitle")}
          bodyClassName="p-2"
        >
          <ol className="relative flex flex-col">
            {STATE_VERSIONS.map((sv, i) => {
              const isSel = sv.v === selected;
              const isLast = i === STATE_VERSIONS.length - 1;
              return (
                <li key={sv.v}>
                  <button
                    type="button"
                    onClick={() => setSelected(sv.v)}
                    className={`relative grid w-full cursor-pointer grid-cols-[28px_1fr] gap-[10px] rounded-[4px] border-l-2 px-1 py-[7px] text-left ${isSel ? "border-l-primary bg-primary/10" : "border-l-transparent hover:bg-muted/30"}`}
                  >
                    {!isLast && (
                      <span className="absolute left-[17px] top-[22px] bottom-[-8px] w-px bg-border" />
                    )}
                    <span
                      className={`mt-1 inline-flex h-5 w-5 items-center justify-center border-[1.5px] bg-background font-mono text-[9px] font-semibold ${AUTHOR_TEXT_CLASS[sv.by]} ${AUTHOR_BORDER_CLASS[sv.by]} ${sv.checkpoint ? "rounded-[4px]" : "rounded-full"}`}
                    >
                      {sv.checkpoint && <Shield className="h-2.5 w-2.5" />}
                    </span>
                    <div>
                      <div className="flex items-center gap-[5px] text-[11.5px]">
                        <span className="font-mono font-semibold">v{sv.v}</span>
                        {sv.checkpoint && <Badge tone="memory">checkpoint</Badge>}
                        <span className="ml-auto font-mono text-[10px] text-muted-foreground">
                          {sv.at.slice(-6)}
                        </span>
                      </div>
                      <div className={`mt-0.5 font-mono text-[10.5px] ${AUTHOR_TEXT_CLASS[sv.by]}`}>
                        {sv.by}
                      </div>
                      <div className="mt-0.5 text-[11px] leading-[1.45] text-muted-foreground">
                        {sv.msg}
                      </div>
                    </div>
                  </button>
                </li>
              );
            })}
          </ol>
        </Card>

        <div className="flex flex-col gap-[14px]">
          <Card
            title={
              <span className="flex items-center gap-[6px]">
                <span className="font-mono">v{selected}</span>
                <span className="text-muted-foreground">by</span>
                <span className={`font-mono ${AUTHOR_TEXT_CLASS[current.by]}`}>{current.by}</span>
                <Badge tone={AUTHOR_TONE[current.by]}>{current.by}</Badge>
              </span>
            }
            subtitle={current.msg}
            bodyClassName="p-4"
          >
            <div className="grid grid-cols-2 gap-[14px]">
              <div>
                <div className="mb-2 font-mono text-[11px] uppercase tracking-wide text-muted-foreground">
                  {t("stateInspector.transient.heading")}
                </div>
                <div className="flex flex-col gap-1.5 text-[12px]">
                  <KvLine k="messages" v="12 items" mono />
                  <KvLine k="pending_tool_calls" v="1" mono />
                  <KvLine k="current_turn" v="4" mono />
                  <KvLine k="elapsed_ms" v="4,210" mono />
                  <KvLine k="token_usage_so_far" v="18,420" mono />
                </div>
              </div>
              <div>
                <div className="mb-2 font-mono text-[11px] uppercase tracking-wide text-muted-foreground">
                  {t("stateInspector.durable.heading")}
                </div>
                <div className="flex flex-col gap-1.5 text-[12px]">
                  <KvLine
                    k="session_id"
                    v={hasLive ? liveSnapshot.session_id.slice(0, 12) + "…" : "sess_4tk2p"}
                    mono
                  />
                  <KvLine
                    k="tenant_id"
                    v={hasLive ? liveSnapshot.tenant_id.slice(0, 12) + "…" : "tenant_01h9a2"}
                    mono
                  />
                  <KvLine k="user_id" v="u_jamie" mono />
                  <KvLine k="pending_approval_ids" v="[a8f3.k2p1]" mono />
                  <KvLine
                    k="last_checkpoint_version"
                    v={String(hasLive ? liveSnapshot.version : 17)}
                    mono
                  />
                  <KvLine
                    k="conversation_summary"
                    v={<span className="text-muted-foreground">— 124 chars —</span>}
                  />
                </div>
              </div>
            </div>
          </Card>

          <Card
            title={t("stateInspector.diff.title")}
            subtitle={parent ? `v${parent.v} → v${current.v}` : t("stateInspector.diff.noParent")}
          >
            <pre className="m-0 overflow-x-auto rounded-[6px] border border-border bg-muted/30 p-3 font-mono text-[11px] leading-[1.55]">
{DIFF_TEXT}
            </pre>
          </Card>
        </div>
      </div>
    </div>
  );
}

export function StateInspectorPage(): JSX.Element {
  const { t } = useTranslation();
  return (
    <RequireAuth>
      <AppShellV2 pageTitle={t("stateInspector.title")}>
        <StateInspectorPageInner />
      </AppShellV2>
    </RequireAuth>
  );
}

export default StateInspectorPage;

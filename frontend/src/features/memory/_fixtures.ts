/**
 * File: frontend/src/features/memory/_fixtures.ts
 * Purpose: Memory page fixtures — verbatim port of mockup MEMORY_ENTRIES / SCOPES / TIME_SCALES / TIME_TRAVEL_MARKS / MEMORY_OPS_TIMELINE + hand-ported RECENT_MEMORY_OPS.
 * Category: Frontend / memory / fixtures
 * Scope: Phase 57 / Sprint 57.42 Day 1 (mockup-fidelity rebuild)
 *
 * Description:
 *   Verbatim port of `reference/design-mockups/page-governance.jsx:410-460` +
 *   hand-ported `RECENT_MEMORY_OPS` from inline mockup table (L561-566).
 *
 *   Mockup vocab kept as-is ("permanent"/"quarter"/"day"; NOT backend's
 *   "quarterly"/"daily") — matrix is fixture-only this sprint (no backend
 *   wiring) per Day 0 D-DAY0-1 finding. All 5 fixture consts feed the
 *   5 mockup-direct-port component tree (MemoryPageHeader / TimeTravelScrubber
 *   / MemoryMatrix / RecentMemoryOpsCard / GdprErasureCard).
 *
 * Key Components:
 *   - MemoryScope: 5 scope entries (system/tenant/role/user/session)
 *   - TimeScaleMockup: 3 time scales (permanent/quarter/day) — mockup vocab
 *   - MemoryEntryMockup: 15 cells × ≤4 entries per cell (k/v pairs)
 *   - TimeTravelMark: 6 time markers along 24h scrubber
 *   - MemoryOpTimelinePoint: 12 op markers behind scrubber
 *   - RecentMemoryOp: 5-row hand-ported recent-ops table
 *
 * Created: 2026-05-25 (Sprint 57.42 Day 1)
 * Last Modified: 2026-05-25
 *
 * Modification History (newest-first):
 *   - 2026-05-25: Initial creation (Sprint 57.42 Day 1) — memory matrix full mockup-fidelity rebuild
 *
 * Related:
 *   - reference/design-mockups/page-governance.jsx L410-460 (verbatim 5 consts)
 *   - reference/design-mockups/page-governance.jsx L561-566 (RECENT_MEMORY_OPS hand-port)
 *   - ./components/MemoryMatrix.tsx ./components/TimeTravelScrubber.tsx
 *     ./components/MemoryPageHeader.tsx ./components/RecentMemoryOpsCard.tsx
 */

export type MemoryScopeId = "system" | "tenant" | "role" | "user" | "session";
export type TimeScaleMockup = "permanent" | "quarter" | "day";

export interface MemoryScope {
  id: MemoryScopeId;
  name: string;
  sub: string;
  count: number;
}

export interface MemoryEntryMockup {
  k: string;
  v: string;
}

export interface TimeTravelMark {
  t: number; // minutes ago; 0 = now, negative = past
  label: string;
  at: string;
}

export interface MemoryOpTimelinePoint {
  t: number; // minutes ago
  op: "WRITE" | "READ" | "EXPIRE";
  scope: MemoryScopeId;
  k: string;
}

export interface RecentMemoryOp {
  op: "WRITE" | "READ" | "EXPIRE";
  scope: string;
  k: string;
  v: string;
  by: string;
  at: string;
}

export const SCOPES: MemoryScope[] = [
  { id: "system", name: "system", sub: "global · cross-tenant", count: 84 },
  { id: "tenant", name: "tenant", sub: "tenant_01h9a2", count: 1280 },
  { id: "role", name: "role", sub: "operator · auditor · admin", count: 312 },
  { id: "user", name: "user", sub: "u_jamie · u_priya · …", count: 4820 },
  { id: "session", name: "session", sub: "sess_4tk2p · live", count: 18 },
];

export const TIME_SCALES: TimeScaleMockup[] = ["permanent", "quarter", "day"];

export const MEMORY_ENTRIES: Record<string, MemoryEntryMockup[]> = {
  "system|permanent": [
    { k: "compliance.frameworks", v: "[PCI-DSS, SOC2, ISO27001]" },
    { k: "policy.tripwires", v: "12 rules" },
  ],
  "system|quarter": [{ k: "rate_limits.global", v: "10k req/min" }],
  "system|day": [],
  "tenant|permanent": [
    { k: "tenant.plan", v: "Pro" },
    { k: "tenant.region", v: "ap-east-1" },
    { k: "hitl.risk_high", v: "always_ask" },
    { k: "hitl.risk_medium", v: "ask_once" },
  ],
  "tenant|quarter": [
    { k: "usage.tokens", v: "4.2M / 10M" },
    { k: "incidents.opened", v: "27" },
  ],
  "tenant|day": [{ k: "anomaly.token_spike", v: "tenant_3kp9 +320%" }],
  "role|permanent": [
    { k: "operator.tools_allowed", v: "26 read · 8 write" },
    { k: "auditor.tools_allowed", v: "12 read" },
  ],
  "role|quarter": [{ k: "operator.preferred_rca", v: "5-whys" }],
  "role|day": [],
  "user|permanent": [
    { k: "u_jamie.tz", v: "Asia/Taipei" },
    { k: "u_jamie.lang", v: "zh-TW" },
    { k: "u_jamie.role", v: "operator" },
  ],
  "user|quarter": [
    { k: "u_jamie.preferences.rca_format", v: "5-whys + timeline" },
    { k: "u_jamie.shortcuts", v: "12 saved" },
  ],
  "user|day": [
    { k: "u_jamie.last_session", v: "sess_4tk2p" },
    { k: "u_jamie.notifications", v: "2 unread" },
  ],
  "session|permanent": [],
  "session|quarter": [],
  "session|day": [
    { k: "sess_4tk2p.root_cause", v: "pgbouncer pool too small" },
    { k: "sess_4tk2p.evidence", v: "[metrics, INC-4012]" },
    { k: "sess_4tk2p.severity", v: "P1" },
  ],
};

export const TIME_TRAVEL_MARKS: TimeTravelMark[] = [
  { t: 0, label: "now", at: "10:42:28" },
  { t: -5, label: "5m ago", at: "10:37:00" },
  { t: -30, label: "30m ago", at: "10:12:00" },
  { t: -120, label: "2h ago", at: "08:42:00" },
  { t: -360, label: "6h ago", at: "04:42:00" },
  { t: -1440, label: "1d ago", at: "yesterday" },
];

export const MEMORY_OPS_TIMELINE: MemoryOpTimelinePoint[] = [
  { t: 0, op: "WRITE", scope: "session", k: "evidence" },
  { t: -1, op: "WRITE", scope: "session", k: "root_cause" },
  { t: -2, op: "READ", scope: "tenant", k: "hitl.risk_high" },
  { t: -4, op: "READ", scope: "user", k: "preferences.rca_format" },
  { t: -7, op: "WRITE", scope: "tenant", k: "anomaly.token_spike" },
  { t: -8, op: "READ", scope: "system", k: "policy.tripwires" },
  { t: -11, op: "EXPIRE", scope: "session", k: "scratchpad.q4_audit" },
  { t: -15, op: "WRITE", scope: "user", k: "shortcuts" },
  { t: -42, op: "READ", scope: "tenant", k: "plan" },
  { t: -120, op: "WRITE", scope: "tenant", k: "usage.tokens" },
  { t: -240, op: "READ", scope: "user", k: "tz" },
  { t: -380, op: "WRITE", scope: "session", k: "severity" },
];

export const RECENT_MEMORY_OPS: RecentMemoryOp[] = [
  {
    op: "WRITE",
    scope: "session.sess_4tk2p",
    k: "root_cause",
    v: "pgbouncer pool too small",
    by: "incident-responder",
    at: "10:42:27",
  },
  {
    op: "READ",
    scope: "user.jamie",
    k: "preferences.rca_format",
    v: "5-whys + timeline",
    by: "incident-responder",
    at: "10:42:24",
  },
  {
    op: "READ",
    scope: "tenant.acme-prod",
    k: "hitl.risk_high",
    v: "always_ask",
    by: "incident-responder",
    at: "10:42:26",
  },
  {
    op: "WRITE",
    scope: "tenant.acme-prod",
    k: "anomaly.token_spike",
    v: "tenant_3kp9 +320%",
    by: "compliance-auditor",
    at: "10:35:11",
  },
  {
    op: "EXPIRE",
    scope: "session.sess_91kxu",
    k: "scratchpad.q4_audit",
    v: "—",
    by: "system",
    at: "10:31:00",
  },
];

/**
 * Sum of mockup entry counts across 5 scopes (system 84 + tenant 1280 + role 312 +
 * user 4820 + session 18 = 6514). Used by MemoryPageHeader subtitle.
 */
export const TOTAL_ENTRIES = SCOPES.reduce((acc, s) => acc + s.count, 0);

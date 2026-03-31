# V9 50-Point Re-Verification Report

> **Date**: 2026-03-31
> **Scope**: features-cat-a-to-e.md, features-cat-f-to-j.md, delta-phase-35-38.md, delta-phase-39-42.md
> **Method**: grep / glob / file reading against live codebase

---

## features-cat-a-to-e.md (15 pts)

### P1-P5: A2 Endpoint Count = 12

| Pt | Check | Result |
|----|-------|--------|
| P1 | Doc says "12 endpoints: routes.py 9 + graph_routes.py 3" | ✅ Matches doc |
| P2 | `routes.py` grep `@router.(get\|post\|put\|delete)` = 9 | ✅ Confirmed |
| P3 | `graph_routes.py` grep = 3 | ✅ Confirmed |
| P4 | Total = 12 | ✅ Correct |
| P5 | No A2A confusion (A2 = Workflow, A15 = A2A) | ✅ Separate features |

### P6-P8: D9 Swarm 15 Components

| Pt | Check | Result |
|----|-------|--------|
| P6 | Glob `agent-swarm/*.tsx` = 15 files | ✅ Confirmed (AgentSwarmPanel, SwarmHeader, OverallProgress, WorkerCardList, WorkerCard, WorkerDetailDrawer, WorkerDetailHeader, WorkerActionList, MessageHistory, ToolCallsPanel, ToolCallItem, ExtendedThinkingPanel, CheckpointPanel, CurrentTask, SwarmStatusBadges) |
| P7 | Doc lists all 15 by name | ✅ All 15 names match |
| P8 | Hooks subdirectory = 4 hooks confirmed | ✅ useSwarmEvents, useWorkerDetail, useSwarmStatus, useSwarmEventHandler |

### P9-P12: E2 MCP "9 Servers, 70 Tools"

| Pt | Check | Result |
|----|-------|--------|
| P9 | 8 server directories: azure, filesystem, shell, ldap, ssh, n8n, adf, d365 | ✅ Confirmed |
| P10 | +1 ServiceNow (root-level: servicenow_server.py, servicenow_client.py, servicenow_config.py) | ✅ 9 total |
| P11 | Doc says "9 Servers, 70 Tools" | ✅ 9 servers correct |
| P12 | 70 tools number — NOT directly verifiable (tool definitions use dict/list patterns, not `Tool()` class). Doc claims "70" as aggregate. | ⚠️ Accepted but not individually counted — tool definitions use `name=` in ToolSchema dicts, mixed with parameter names making exact count difficult |

### P13-P15: Other Feature Status Spot-Check

| Pt | Check | Result |
|----|-------|--------|
| P13 | A1 CRUD: `domain/agents/service.py` exists | ✅ |
| P14 | A4 State Machine: 6 states documented, `domain/executions/state_machine.py` exists | ✅ |
| P15 | E Category summary: 44 COMPLETE + 2 PARTIAL = 47 total | ✅ Matches table |

---

## features-cat-f-to-j.md (15 pts)

### P16-P18: H3 Hook Names

| Pt | Check | Result |
|----|-------|--------|
| P16 | Doc says "Hooks: useSwarmEvents, useWorkerDetail, useSwarmStatus, useSwarmEventHandler" | ✅ |
| P17 | Glob `agent-swarm/hooks/*.ts` = 5 files (4 hooks + index.ts) | ✅ Matches |
| P18 | Hook names match: useSwarmEvents.ts, useWorkerDetail.ts, useSwarmStatus.ts, useSwarmEventHandler.ts | ✅ All 4 correct |

### P19-P21: I2 require_auth

| Pt | Check | Result |
|----|-------|--------|
| P19 | Doc says `core/auth.py` — `require_auth` | ✅ grep confirms `async def require_auth(` at line 46 |
| P20 | Used in `api/v1/__init__.py` as `protected_router = APIRouter(dependencies=[Depends(require_auth)])` | ✅ |
| P21 | Also used directly in `sessions/routes.py` and `sessions/chat.py` | ✅ |

### P22-P24: I2 Role Enum

| Pt | Check | Result |
|----|-------|--------|
| P22 | Doc says `core/security/rbac.py` — basic `Role` enum (ADMIN/OPERATOR/VIEWER) | ✅ |
| P23 | Grep confirms `class Role(str, Enum)` with ADMIN, OPERATOR, VIEWER | ✅ Exact match |
| P24 | Doc correctly notes "NOT wired into the auth middleware" | ✅ Honest assessment |

### P25-P30: Other Feature Spot-Checks

| Pt | Check | Result |
|----|-------|--------|
| P25 | F category: 6/7 COMPLETE (F7 API stub) | ✅ Matches summary table |
| P26 | G category: 2/5 COMPLETE (G3/G4/G5 stubs) | ✅ |
| P27 | H category: 4/4 COMPLETE with Phase 43 upgrade | ✅ |
| P28 | I category: 4/4 COMPLETE with Phase 36 expansion | ✅ |
| P29 | J category: 26+ features (11 NEW) | ✅ |
| P30 | Claude SDK hooks: ApprovalHook, AuditHook, RateLimitHook, SandboxHook (+ StrictSandboxHook, UserSandboxHook variants) confirmed in code | ✅ |

---

## delta-phase-35-38.md (10 pts)

### P31-P35: contracts.py Type Names

| Pt | Check | Result |
|----|-------|--------|
| P31 | Doc says "Handler, HandlerResult, HandlerType, OrchestratorRequest" | ✅ |
| P32 | `hybrid/orchestrator/contracts.py` grep: `class HandlerType(str, Enum)` line 23 | ✅ |
| P33 | `class OrchestratorRequest` line 36 | ✅ |
| P34 | `class HandlerResult` line 60 | ✅ |
| P35 | `class Handler(ABC)` line 97 | ✅ All 4 types confirmed |

### P36-P40: C-07 Location = postgres_storage.py

| Pt | Check | Result |
|----|-------|--------|
| P36 | Doc says "C-07 SQL Injection Fix: Fixed in `agent_framework/memory/postgres_storage.py`" | ✅ |
| P37 | File exists: `backend/src/integrations/agent_framework/memory/postgres_storage.py` | ✅ |
| P38 | Doc mentions "parameterized queries" as fix | ✅ |
| P39 | Referenced 3 times in doc (timeline, new files, issue registry) | ✅ Consistent |
| P40 | Issue registry line: "C-07 | CRITICAL | SQL Injection in `agent_framework/memory/postgres_storage.py`" | ✅ |

---

## delta-phase-39-42.md (10 pts)

### P41-P43: Phase 41/42 "Completed" Status

| Pt | Check | Result |
|----|-------|--------|
| P41 | Phase 39 status: "Completed" | ✅ Line 84 |
| P42 | Phase 41 status: "Completed (commit `dee9290`, merged `4bb2cfc`)" | ✅ Line 235 |
| P43 | Phase 42 status: "Completed on feature branch" | ✅ Line 274 |

### P44-P46: Handler Count = 7 (No Residual "6 handlers")

| Pt | Check | Result |
|----|-------|--------|
| P44 | Text body consistently says "7 handlers" (lines 18, 21, 88, 97, 146, 348) | ✅ |
| P45 | Bootstrap code confirms 7: ContextHandler, RoutingHandler, DialogHandler, ApprovalHandler, AgentHandler, ExecutionHandler, ObservabilityHandler | ✅ |
| P46 | **Diagram title says "6 Handler"** (line 45: `OrchestratorBootstrap → 6 Handler 接線拓撲`) but diagram body shows 7 handlers | ⚠️ INCONSISTENCY: Title says 6, body shows 7. Needs fix |

### P47-P50: Phase 43 "First Created in Sprint 148"

| Pt | Check | Result |
|----|-------|--------|
| P47 | delta-phase-39-42.md does NOT reference Phase 43 or Sprint 148 | ✅ Correct scoping |
| P48 | delta-phase-43-44.md confirms: "Sprint 148 completed via commit `a0438f1`" | ✅ |
| P49 | delta-phase-43-44.md says: "first created in Phase 43 Sprint 148" | ✅ Line 116 |
| P50 | Phase 43 status: "Partially Implemented (Sprint 148 completed; Sprints 149-150 planned)" | ✅ |

---

## Overall Score

| Section | Points | Pass | Warn | Fail |
|---------|--------|------|------|------|
| features-cat-a-to-e.md | 15 | 14 | 1 | 0 |
| features-cat-f-to-j.md | 15 | 15 | 0 | 0 |
| delta-phase-35-38.md | 10 | 10 | 0 | 0 |
| delta-phase-39-42.md | 10 | 9 | 1 | 0 |
| **Total** | **50** | **48** | **2** | **0** |

### Issues Found

1. **⚠️ P12**: E2 "70 Tools" count not individually verifiable — tool definitions use ToolSchema dicts with nested `name=` fields for both tools and parameters. The "70" figure is plausible given 9 servers but cannot be precisely confirmed without parsing each server's tool list.

2. **⚠️ P46**: delta-phase-39-42.md line 45 diagram title says **"6 Handler 接線拓撲"** but the diagram body and all text references say **7 handlers**. The diagram title should be corrected to "7 Handler".

### Recommended Fixes

```
File: docs/07-analysis/V9/07-delta/delta-phase-39-42.md
Line 45: "OrchestratorBootstrap → 6 Handler 接線拓撲"
     →   "OrchestratorBootstrap → 7 Handler 接線拓撲"
```

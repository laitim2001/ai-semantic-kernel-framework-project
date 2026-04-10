# API Reference V9 — Back-Half Deep Verification Report

> **Scope**: Lines 600–1341 of `api-reference.md` (Domain C through F + Summary tables)
> **Verified**: 2026-03-31 | **Method**: Cross-reference each endpoint against actual router source files

---

## Section-by-Section Verification

### C1. Sessions (`/sessions`) — 14 endpoints
**Source**: `api/v1/sessions/routes.py` (14 decorators) | **Prefix**: `/sessions`

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–14 | 14 endpoints listed | 14 `@router` decorators confirmed | ✅ 準確 |
| Paths | All paths correct | Verified: create, list, get, patch, delete, activate, suspend, resume, messages, attachments, tool-calls | ✅ 準確 |

### C2. Sessions Chat — 6 endpoints
**Source**: `api/v1/sessions/chat.py` (6 decorators) | **Prefix**: `/sessions`

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–6 | 6 endpoints listed | 6 `@router` decorators confirmed | ✅ 準確 |
| Paths | `/sessions/{id}/chat`, `/chat/stream`, `/approvals`, etc. | All paths match | ✅ 準確 |

### C3. Sessions WebSocket — 3 endpoints
**Source**: `api/v1/sessions/websocket.py` (3 decorators) | **Prefix**: `/sessions`

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1 | WS `/{session_id}/ws` | `@router.websocket("/{session_id}/ws")` | ✅ 準確 |
| 2–3 | ws/status, ws/broadcast | Confirmed in code | ✅ 準確 |

### C4. Session Resume — 2 endpoints
**Source**: `api/v1/orchestrator/session_routes.py` | **Prefix**: `/sessions`

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1 | GET `/sessions/recoverable` | `@router.get("/recoverable")` | ✅ 準確 |
| 2 | POST `/{session_id}/resume` | `@router.post("/{session_id}/resume")` | ✅ 準確 |
| Note | Registered before sessions_router | `__init__.py` confirms ordering | ✅ 準確 |

### C5. Chat History (`/chat-history`) — 3 endpoints
**Source**: `api/v1/chat_history/routes.py` (3 decorators) | **Prefix**: `/chat-history`

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–3 | sync, get, delete | 3 decorators: POST /sync, GET /{session_id}, DELETE /{session_id} | ✅ 準確 |

### C6. AG-UI Protocol (`/ag-ui`) — 30 endpoints (26 routes + 4 upload)
**Source**: `api/v1/ag_ui/routes.py` (26 decorators), `upload.py` (4 decorators) | **Prefix**: `/ag-ui`

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| Count | 30 endpoints listed (C6a-C6e) | 26 + 4 = 30 confirmed | ✅ 準確 |
| C6a #2 | handler `get_status` | Code: `bridge_status` | ❌ Handler name wrong |
| C6a #3 | handler `reset` | Code: `reset_bridge` | ❌ Handler name wrong |
| C6d #17 | handler `test_progress` | Code: `test_workflow_progress` (path `/test/progress` is correct) | ⚠️ Handler name wrong, path correct |
| C6d #21 | `POST /ag-ui/test/hitl` handler `test_hitl` | Code: `test_hitl_approval` | ⚠️ Handler name wrong |
| C6d #22 | handler `test_hitl_stream` | Code: `test_hitl_approval_stream` | ⚠️ Handler name wrong |
| Upload | `/ag-ui/upload/*` 4 endpoints | upload.py prefix="/upload" nested inside ag-ui router | ✅ 準確 |
| **Route File Index** | Claims "ag_ui: 33 endpoints" | Actual: 30 endpoints | ❌ Summary count wrong |

### C7. Swarm (`/swarm`) — 8 endpoints
**Source**: `api/v1/swarm/routes.py` (3), `demo.py` (5) | **Prefix**: `/swarm`, `/swarm/demo`

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–3 | Swarm status (3 GET) | 3 `@router.get` in routes.py | ✅ 準確 |
| 4–8 | Demo (2 POST, 2 GET, 1 GET SSE) | 5 decorators in demo.py | ✅ 準確 |

---

### D1. Orchestration Policies — 7 endpoints
**Source**: `api/v1/orchestration/routes.py` (7 decorators) | **Prefix**: `/orchestration`

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–7 | 7 endpoints | 7 `@router` decorators confirmed | ✅ 準確 |

### D2. Orchestration Intent — 4 endpoints
**Source**: `api/v1/orchestration/intent_routes.py` (4 decorators) | **Prefix**: `/orchestration/intent`

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–4 | classify, test, batch, quick | 4 `@intent_router` decorators | ✅ 準確 |
| Note | Doc says "4 endpoints" | API CLAUDE.md says "18 endpoints" | ⚠️ API CLAUDE.md is wrong, doc is correct |

### D3. Orchestration Dialog — 4 endpoints
**Source**: `api/v1/orchestration/dialog_routes.py` (4 decorators) | **Prefix**: `/orchestration/dialog`

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–4 | start, respond, status, delete | 4 `@dialog_router` decorators | ✅ 準確 |

### D4. Orchestration Approvals — 4 endpoints
**Source**: `api/v1/orchestration/approval_routes.py` (4 decorators) | **Prefix**: `/orchestration/approvals`

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–4 | list, get, decision, callback | 4 `@approval_router` decorators | ✅ 準確 |

### D5. Orchestration Webhooks — 3 endpoints
**Source**: `api/v1/orchestration/webhook_routes.py` (3 decorators) | **Prefix**: `/orchestration/webhooks`

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–3 | servicenow webhook, health, incident | 3 `@webhook_router` decorators | ✅ 準確 |

### D6. Orchestration Route Management — 7 endpoints
**Source**: `api/v1/orchestration/route_management.py` (7 decorators) | **Prefix**: `/orchestration/routes`

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–7 | CRUD + sync + search | 7 `@route_management_router` decorators | ✅ 準確 |

### D7. Orchestrator Chat Pipeline — 6 endpoints
**Source**: `api/v1/orchestrator/routes.py` (6 decorators) | **Prefix**: `/orchestrator`

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–6 | validate, health, test-intent, approval, chat/stream, chat | 6 `@router` decorators | ✅ 準確 |

### D9. n8n Integration — 7 endpoints
**Source**: `api/v1/n8n/routes.py` (7 decorators) | **Prefix**: `/n8n`

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–7 | webhook, workflow webhook, status, config get/put, callback post/get | 7 decorators | ✅ 準確 |

---

### E1. Audit — 8 endpoints
**Source**: `api/v1/audit/routes.py` (8 decorators)

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–8 | logs, entry, trail, statistics, export, actions, resources, health | 8 `@router.get` decorators | ✅ 準確 |

### E2. Decision Audit — 7 endpoints
**Source**: `api/v1/audit/decision_routes.py` (7 decorators)

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–7 | decisions list/get/report, feedback, statistics, summary, health | 7 decorators (6 GET + 1 POST) | ✅ 準確 |

### E3. Performance — 11 endpoints
**Source**: `api/v1/performance/routes.py` (11 decorators) | **Prefix**: `/performance`

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–11 | metrics, profile/start/stop/metric/sessions/summary, optimize, collector/summary/alerts/threshold, health | 11 decorators | ✅ 準確 |

### E4. Patrol — 9 endpoints
**Source**: `api/v1/patrol/routes.py` (9 decorators) | **Prefix**: `/patrol`

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–9 | trigger, reports, schedule CRUD, checks | 9 decorators | ✅ 準確 |

### E5. Correlation — 7 endpoints
**Source**: `api/v1/correlation/routes.py` (7 decorators) | **Prefix**: `/correlation`

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–7 | analyze, event, rootcause, graph (mermaid/json/dot) | 7 decorators | ✅ 準確 |

### E6. Root Cause — 4 endpoints
**Source**: `api/v1/rootcause/routes.py` (4 decorators) | **Prefix**: `/rootcause`

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–4 | analyze, hypotheses, recommendations, similar | 4 decorators | ✅ 準確 |

### E7. DevTools — 12 endpoints
**Source**: `api/v1/devtools/routes.py` (12 decorators) | **Prefix**: `/devtools`

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–12 | health, traces CRUD, events, spans, timeline, statistics | 12 decorators | ✅ 準確 |

### E8. Notifications — 11 endpoints
**Source**: `api/v1/notifications/routes.py` (11 decorators) | **Prefix**: `/notifications`

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–11 | approval/completion/error/custom, history, statistics, config, types, health | 11 decorators | ✅ 準確 |

### E9. Dashboard — 2 endpoints
**Source**: `api/v1/dashboard/routes.py` | **Prefix**: `/dashboard`

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–2 | stats, executions/chart | Confirmed | ✅ 準確 |

---

### F1. Authentication — 5 endpoints
**Source**: `api/v1/auth/routes.py` (4) + `migration.py` (1) | **Prefix**: `/auth`

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–4 | register, login, refresh, me | 4 decorators in routes.py | ✅ 準確 |
| 5 | handler `migrate_guest` | Code: `migrate_guest_data` | ⚠️ Handler name slightly different |
| Path | `/auth/migrate-guest` | Code: `/migrate-guest` on `/auth` prefix | ✅ Path correct |

### F2. Files — 6 endpoints
**Source**: `api/v1/files/routes.py` (6 decorators) | **Prefix**: `/files`

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–6 | upload, list, get, content, download, delete | 6 decorators | ✅ 準確 |

### F3. Memory — 7 endpoints
**Source**: `api/v1/memory/routes.py` (7 decorators) | **Prefix**: `/memory`

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–7 | add, search, user memories, delete, promote, context, health | 7 decorators | ✅ 準確 |

### F4. Sandbox — 6 endpoints
**Source**: `api/v1/sandbox/routes.py` (6 decorators) | **Prefix**: `/sandbox`

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–6 | pool/status, pool/cleanup, create, get, delete, ipc | 6 decorators | ✅ 準確 |

### F5. Cache — 9 endpoints
**Source**: `api/v1/cache/routes.py` (9 decorators)

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–9 | stats, config, enable, disable, get, set, clear, warm, reset-stats | 9 decorators | ✅ 準確 |

### F6. Knowledge — 7 endpoints
**Source**: `api/v1/knowledge/routes.py` (7 decorators) | **Prefix**: `/knowledge`

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–7 | ingest, search, collections get/delete, skills list/get/search | 7 decorators | ✅ 準確 |

### F7. Versioning — 14 endpoints
**Source**: `api/v1/versioning/routes.py` (14 decorators)

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–14 | health, statistics, compare, CRUD, publish/deprecate/archive, template versions/latest/rollback/stats | 14 decorators | ✅ 準確 |

### F8. Prompts — 11 endpoints
**Source**: `api/v1/prompts/routes.py` (11 decorators)

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–11 | templates CRUD, render, validate, categories, search, reload, health | 11 decorators | ✅ 準確 |

### F9. Learning — 13 endpoints
**Source**: `api/v1/learning/routes.py` (13 decorators)

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–13 | health, statistics, corrections, cases CRUD/approve/reject/bulk, similar, prompt, effectiveness, scenario stats | 13 decorators | ✅ 準確 |

### F10. Code Interpreter — 14 endpoints
**Source**: `api/v1/code_interpreter/routes.py` (11), `visualization.py` (3)

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–11 | health, execute, analyze, sessions, files | 11 decorators in routes.py | ✅ 準確 |
| 11 | `/code-interpreter/sandbox/containers/{container_id}/files/{file_id}` | Confirmed in code at line 684 | ✅ 準確 |
| 12–14 | visualizations types/get/generate | 3 decorators in visualization.py | ✅ 準確 |

### F11. MCP — 13 endpoints
**Source**: `api/v1/mcp/routes.py` (13 decorators)

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–13 | servers CRUD/connect/disconnect, tools list/execute, status, audit, connect-all, disconnect-all | 13 decorators | ✅ 準確 |

### F12. A2A — 14 endpoints
**Source**: `api/v1/a2a/routes.py` (14 decorators) | **Prefix**: `/a2a`

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–14 | message, pending, conversation, agents CRUD/discover/capabilities/heartbeat/status, statistics, cleanup | 14 decorators | ✅ 準確 |

### F13. Autonomous — 4 endpoints
**Source**: `api/v1/autonomous/routes.py` (4 decorators) | **Prefix**: `/claude/autonomous`

| # | Doc Claim | Code Reality | Verdict |
|---|-----------|-------------|---------|
| 1–4 | plan, history, task status, cancel | 4 decorators | ✅ 準確 |
| Prefix | `/claude/autonomous` | Code: `APIRouter(prefix="/claude/autonomous")` | ✅ 準確 |

---

## Summary Statistics Verification (P41-P60)

### P41-P45: Endpoint Count Summary Table (Line 1270-1283)

| Domain | Doc Claims | Verified Count | Verdict |
|--------|-----------|---------------|---------|
| System | 3 | 3 (/, /health, /ready) | ✅ 準確 |
| **A** Core Entity | 80 | Not in scope (front half) | 🔍 |
| **B** AI Agent Ops | 148 | Not in scope (front half) | 🔍 |
| **C** Real-Time | 56 | 14+6+3+2+3+30+8 = 66 | ❌ Doc says 56, actual is ~66 |
| **D** Orchestration | 52 | 7+4+4+4+3+7+6+14+7 = 56 (incl. A9 routing cross-ref) | ⚠️ Close but doc says 52 |
| **E** Monitoring | 80 | 8+7+11+9+7+4+12+11+2 = 71 | ❌ Doc says 80, actual is 71 |
| **F** Infrastructure | 147 | 5+6+7+6+9+7+14+11+13+14+13+14+4 = 123 | ❌ Doc says 147, actual is 123 |
| **Total** | 566 | Sum of all unique route decorators across all files | ⚠️ Needs full recount |

> **Note**: The domain-level rollup numbers in the summary table do NOT match the detailed per-section counts listed in the same document. This is the most significant discrepancy.

### P46-P50: Endpoint Tags

| Check | Verdict |
|-------|---------|
| orchestration routes.py tags=`["Orchestration"]` | ✅ 準確 |
| intent_routes.py tags=`["Intent Classification"]` | ✅ 準確 |
| dialog_routes.py tags=`["Guided Dialog"]` | ✅ 準確 |
| approval_routes.py tags=`["HITL Approvals"]` | ✅ 準確 |
| webhook_routes.py tags=`["orchestration-webhooks"]` | ✅ 準確 |
| route_management.py tags=`["orchestration-routes"]` | ✅ 準確 |
| swarm routes.py tags=`["Swarm"]`, demo.py tags=`["Swarm Demo"]` | ✅ 準確 |
| ag_ui routes.py tags=`["ag-ui"]`, upload.py tags=`["File Upload"]` | ✅ 準確 |
| n8n routes.py tags=`["n8n Integration"]` | ✅ 準確 |
| auth routes.py tags=`["Authentication"]` | ✅ 準確 |

### P51-P55: Router Prefix Verification

| Router | Doc Prefix | Code Prefix | Verdict |
|--------|-----------|------------|---------|
| sessions | `/sessions` | `/sessions` | ✅ 準確 |
| chat_history | `/chat-history` | `/chat-history` | ✅ 準確 |
| ag_ui | `/ag-ui` | `/ag-ui` | ✅ 準確 |
| ag_ui upload | `/ag-ui/upload` | `/upload` nested in `/ag-ui` | ✅ 準確 |
| swarm | `/swarm` | `/swarm` | ✅ 準確 |
| swarm demo | `/swarm/demo` | `/swarm/demo` | ✅ 準確 |
| orchestration | `/orchestration` | `/orchestration` | ✅ 準確 |
| orchestration/intent | `/orchestration/intent` | `/orchestration/intent` | ✅ 準確 |
| orchestration/dialog | `/orchestration/dialog` | `/orchestration/dialog` | ✅ 準確 |
| orchestration/approvals | `/orchestration/approvals` | `/orchestration/approvals` | ✅ 準確 |
| orchestration/webhooks | `/orchestration/webhooks` | `/orchestration/webhooks` | ✅ 準確 |
| orchestration/routes | `/orchestration/routes` | `/orchestration/routes` | ✅ 準確 |
| orchestrator | `/orchestrator` | `/orchestrator` | ✅ 準確 |
| n8n | `/n8n` | `/n8n` | ✅ 準確 |
| auth | `/auth` | `/auth` | ✅ 準確 |
| files | `/files` | `/files` | ✅ 準確 |
| memory | `/memory` | `/memory` | ✅ 準確 |
| sandbox | `/sandbox` | `/sandbox` | ✅ 準確 |
| knowledge | `/knowledge` | `/knowledge` | ✅ 準確 |
| autonomous | `/claude/autonomous` | `/claude/autonomous` | ✅ 準確 |
| dashboard | `/dashboard` | `/dashboard` | ✅ 準確 |
| main.py routing | `app.include_router(api_router)` single entry | Confirmed | ✅ 準確 |
| api_router prefix | `/api/v1` | `APIRouter(prefix="/api/v1")` | ✅ 準確 |

### P56-P60: Dependency Injection (Auth)

| Check | Doc Claim | Code Reality | Verdict |
|-------|-----------|-------------|---------|
| Global auth guard | `require_auth` on `protected_router` | `APIRouter(dependencies=[Depends(require_auth)])` | ✅ 準確 |
| Auth router is public | On `public_router` (no auth) | `public_router.include_router(auth_router)` | ✅ 準確 |
| All other routers protected | Under `protected_router` | All 50+ routers under protected_router | ✅ 準確 |
| Per-route DB lookup | `get_current_user` from `dependencies.py` | Used in auth/migration.py e.g. | ✅ 準確 |

---

## Route File Index Verification (Line 1287-1337)

| Module | Doc Count | Actual Count | Verdict |
|--------|----------|-------------|---------|
| sessions | 23 | 14+6+3=23 | ✅ 準確 |
| **ag_ui** | **33** | **26+4=30** | ❌ Should be 30 |
| orchestration | 29 | 7+4+4+4+3+7=29 | ✅ 準確 |
| swarm | 8 | 3+5=8 | ✅ 準確 |
| n8n | 7 | 7 | ✅ 準確 |
| orchestrator | 8 | 6+2=8 | ✅ 準確 |
| chat_history | 3 | 3 | ✅ 準確 |
| audit | 15 | 8+7=15 | ✅ 準確 |
| performance | 11 | 11 | ✅ 準確 |
| patrol | 9 | 9 | ✅ 準確 |
| correlation | 7 | 7 | ✅ 準確 |
| rootcause | 4 | 4 | ✅ 準確 |
| devtools | 12 | 12 | ✅ 準確 |
| notifications | 11 | 11 | ✅ 準確 |
| dashboard | 2 | 2 | ✅ 準確 |
| auth | 5 | 4+1=5 | ✅ 準確 |
| files | 6 | 6 | ✅ 準確 |
| memory | 7 | 7 | ✅ 準確 |
| sandbox | 6 | 6 | ✅ 準確 |
| cache | 9 | 9 | ✅ 準確 |
| knowledge | 7 | 7 | ✅ 準確 |
| versioning | 14 | 14 | ✅ 準確 |
| prompts | 11 | 11 | ✅ 準確 |
| learning | 13 | 13 | ✅ 準確 |
| code_interpreter | 14 | 11+3=14 | ✅ 準確 |
| mcp | 13 | 13 | ✅ 準確 |
| a2a | 14 | 14 | ✅ 準確 |
| autonomous | 4 | 4 | ✅ 準確 |
| tasks | 9 | Not verified (front half) | 🔍 |

---

## Placeholder Bug: "588 endpoints"

Multiple section headers contain the placeholder text "588 endpoints" instead of the actual endpoint count:

| Section | Header Says | Actual |
|---------|------------|--------|
| A2. Workflows | "588 endpoints" | 12 |
| A3. Executions | "588 endpoints" | 11 |
| A5. Templates | "588 endpoints" | 11 (listed correctly in body) |
| A9. Routing | "588 endpoints" | 14 |
| Domain B header | "588 endpoints" | ~148 |
| B12. Planning | "588 endpoints" | 46 |
| B13. GroupChat | "588 endpoints" | 42 |
| B14. Handoff | "588 endpoints" | 14 |
| B15. Concurrent | "588 endpoints" | 15 |
| B16. Nested | "588 endpoints" | 16 |
| Domain C header | "588 endpoints" | ~66 |
| C1. Sessions | "588 endpoints" | 14 |
| C6. AG-UI | "588 endpoints" | 30 |
| Domain D header | "588 endpoints" | ~56 |
| D8 ref | "588 endpoints" | 14 |
| Domain E header | "588 endpoints" | ~71 |
| E3. Performance | "588 endpoints" | 11 |
| E7. DevTools | "588 endpoints" | 12 |
| E8. Notifications | "588 endpoints" | 11 |
| Domain F header | "588 endpoints" | ~123 |
| F7. Versioning | "588 endpoints" | 14 |
| F8. Prompts | "588 endpoints" | 11 |
| F9. Learning | "588 endpoints" | 13 |
| F10. Code Interpreter | "588 endpoints" | 14 |
| F11. MCP | "588 endpoints" | 13 |
| F12. A2A | "588 endpoints" | 14 |

> **Root Cause**: The total endpoint count (588) was erroneously substituted into individual section headers during document generation. This is a templating/generation bug, not a factual error in the endpoint listings themselves.

---

## Overall Scoring

| Category | Points | Score | Notes |
|----------|--------|-------|-------|
| **Endpoint paths** (back half) | 30/30 | 30 | All paths verified correct |
| **HTTP methods** (back half) | 15/15 | 15 | All methods match |
| **Handler names** (back half) | 15/15 | 10 | 5 handler name mismatches in AG-UI + 1 in auth |
| **Endpoint existence** | — | — | No phantom endpoints; all listed endpoints exist |
| P41-P45: Summary counts | 5/5 | 1 | Domain C/E/F rollup numbers are wrong |
| P46-P50: Tags | 5/5 | 5 | All tags verified correct |
| P51-P55: Router prefixes | 5/5 | 5 | All prefixes verified correct |
| P56-P60: Auth/DI | 5/5 | 5 | Auth architecture correctly described |
| **Total** | **80** | **71/80** | **88.75%** |

---

## Issues Found (8 total)

### ❌ Critical (2)
1. **"588 endpoints" placeholder bug**: ~25 section headers contain "588 endpoints" instead of actual counts. Affects readability and trust.
2. **Route File Index: ag_ui count**: Claims 33 endpoints, actual is 30.

### ⚠️ Medium (5)
3. **AG-UI handler name**: `get_status` → actual `bridge_status`
4. **AG-UI handler name**: `reset` → actual `reset_bridge`
5. **AG-UI handler name**: `test_progress` → actual `test_workflow_progress`
6. **AG-UI handler name**: `test_hitl`/`test_hitl_stream` → actual `test_hitl_approval`/`test_hitl_approval_stream`
7. **Auth handler name**: `migrate_guest` → actual `migrate_guest_data`

### ⚠️ Low (1)
8. **Domain summary counts mismatch**: The Endpoint Count Summary table (line 1270) domain-level totals don't match the sum of individual section counts.

---

## Recommended Fixes

1. **Replace all "588 endpoints"** placeholders in section headers with actual per-section counts.
2. **Fix Route File Index** ag_ui count: 33 → 30.
3. **Fix 5 AG-UI handler names**: `get_status`→`bridge_status`, `reset`→`reset_bridge`, `test_progress`→`test_workflow_progress`, `test_hitl`→`test_hitl_approval`, `test_hitl_stream`→`test_hitl_approval_stream`.
4. **Fix auth handler name**: `migrate_guest` → `migrate_guest_data`.
5. **Recalculate domain summary table** with correct per-domain totals.
6. **Fix header total**: "563 REST + 3 WebSocket = **588 endpoints**" → should be "563 REST + 3 WebSocket = **566 endpoints**" (the note on line 1283 already says 566, contradicting the header on line 5 which says 588).

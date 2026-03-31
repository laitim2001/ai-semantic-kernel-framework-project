# Wave 40R Verification Report — api-reference.md

> **Date**: 2026-03-31 | **Verified by**: V9 Deep Semantic Verification Agent
> **Method**: `grep -rc "@[a-z_]*router\.(get|post|put|delete|patch|websocket)"` across all `*.py` in `backend/src/api/v1/` + `backend/main.py`

---

## Summary

| Item | api-reference claims | Actual (grep) | Verdict |
|------|---------------------|---------------|---------|
| **Total endpoints** | 568 REST + 4 WS = 572 | 587 REST + 4 WS = 591 | ❌ Off by +19 |
| System endpoints | 3 | 3 | ✅ |
| Domain A sections sum | 80 | 90 | ❌ TOC wrong (sections are correct) |
| Domain B sections sum | 148 | 196 | ❌ TOC wrong (sections are correct) |
| Domain C sections sum | 66 | 66 | ✅ |
| Domain D sections sum | 42 | 56 | ❌ TOC wrong (sections are correct) |
| Domain E sections sum | 71 | 71 | ✅ |
| Domain F sections sum | 123 | 123 | ✅ |

**Root cause**: The TOC domain totals were never updated to match the individual section headers. Each individual section header is correct, but Domain A/B/D TOC numbers are stale.

**Duplicate**: D8 (Cross-Scenario Routing, 14 endpoints) = A9 (Routing, 14 endpoints). The doc correctly marks D8 as "See A9 above", so these should NOT be double-counted. Actual unique total = 605 - 14 (D8 dup) = 591.

---

## P1-P15: Per-Router File Endpoint Counts

### All files in `backend/src/api/v1/` (comprehensive grep)

| File | Endpoints | Notes |
|------|-----------|-------|
| a2a/routes.py | 14 | |
| ag_ui/routes.py | 26 | |
| ag_ui/upload.py | 4 | |
| agents/routes.py | 6 | |
| audit/routes.py | 8 | |
| audit/decision_routes.py | 7 | |
| auth/routes.py | 4 | |
| auth/migration.py | 1 | |
| autonomous/routes.py | 4 | |
| cache/routes.py | 9 | |
| chat_history/routes.py | 3 | |
| checkpoints/routes.py | 10 | |
| claude_sdk/routes.py | 6 | |
| claude_sdk/autonomous_routes.py | 7 | |
| claude_sdk/hooks_routes.py | 6 | |
| claude_sdk/hybrid_routes.py | 5 | |
| claude_sdk/intent_routes.py | 6 | |
| claude_sdk/mcp_routes.py | 6 | |
| claude_sdk/tools_routes.py | 4 | |
| code_interpreter/routes.py | 11 | |
| code_interpreter/visualization.py | 3 | |
| concurrent/routes.py | 13 | |
| concurrent/websocket.py | 2 | 2 WS |
| connectors/routes.py | 9 | |
| correlation/routes.py | 7 | |
| dashboard/routes.py | 2 | |
| devtools/routes.py | 12 | |
| executions/routes.py | 11 | |
| files/routes.py | 6 | |
| groupchat/routes.py | 42 | includes 1 WS |
| handoff/routes.py | 14 | |
| hybrid/context_routes.py | 5 | |
| hybrid/core_routes.py | 4 | |
| hybrid/risk_routes.py | 7 | |
| hybrid/switch_routes.py | 7 | |
| knowledge/routes.py | 7 | |
| learning/routes.py | 13 | |
| mcp/routes.py | 13 | |
| memory/routes.py | 7 | |
| n8n/routes.py | 7 | |
| nested/routes.py | 16 | |
| notifications/routes.py | 11 | |
| orchestration/routes.py | 7 | |
| orchestration/approval_routes.py | 4 | uses `approval_router` |
| orchestration/dialog_routes.py | 4 | uses `dialog_router` |
| orchestration/intent_routes.py | 4 | uses `intent_router` |
| orchestration/route_management.py | 7 | uses `route_management_router` |
| orchestration/webhook_routes.py | 3 | uses `webhook_router` |
| orchestrator/routes.py | 6 | |
| orchestrator/session_routes.py | 2 | |
| patrol/routes.py | 9 | |
| performance/routes.py | 11 | |
| planning/routes.py | 46 | |
| prompts/routes.py | 11 | |
| rootcause/routes.py | 4 | |
| routing/routes.py | 14 | |
| sandbox/routes.py | 6 | |
| sessions/routes.py | 14 | |
| sessions/chat.py | 6 | |
| sessions/websocket.py | 3 | includes 1 WS |
| swarm/routes.py | 3 | |
| swarm/demo.py | 5 | |
| tasks/routes.py | 9 | |
| templates/routes.py | 11 | |
| triggers/routes.py | 8 | |
| versioning/routes.py | 14 | |
| workflows/routes.py | 9 | |
| workflows/graph_routes.py | 3 | |
| **api/v1 subtotal** | **588** | 584 REST + 4 WS |
| main.py (system) | 3 | @app.get |
| **GRAND TOTAL** | **591** | 587 REST + 4 WS |

**Excluded** (decorators in docstrings only, not real endpoints):
- dependencies.py: 4 (in docstring examples)
- auth/dependencies.py: 2 (in docstring examples)

---

## P16-P25: Domain Aggregation

| Domain | Sections | api-ref sections sum | Actual grep | TOC claim | TOC correct? |
|--------|----------|---------------------|-------------|-----------|-------------|
| A | A1-A9 | 90 | 90 | 80 | ❌ should be 90 |
| B | B1-B16 | 196 | 196 | 148 | ❌ should be 196 |
| C | C1-C7 | 66 | 66 | 66 | ✅ |
| D | D1-D9 | 56 | 56 | 42 | ❌ should be 56 (but 14 are dup ref) |
| E | E1-E9 | 71 | 71 | 71 | ✅ |
| F | F1-F13 | 123 | 123 | 123 | ✅ |

---

## P26-P30: Total Verification

| Calculation | Value |
|-------------|-------|
| All sections sum | 602 |
| + System endpoints | 3 |
| - D8 duplicate (cross-ref to A9) | -14 |
| **Unique total** | **591** |
| api-reference claims | 572 |
| **Difference** | **+19** |

**Correct total**: 587 REST + 4 WS = **591 endpoints**

---

## P31-P40: Section Header Spot Checks

All 10 spot-checked section headers match actual grep counts:

| Section | Claimed | Actual | ✅/❌ |
|---------|---------|--------|-------|
| A1. Agents | 6 | 6 | ✅ |
| A2. Workflows | 12 | 12 | ✅ |
| B12. Planning | 46 | 46 | ✅ |
| B13. GroupChat | 42 | 42 | ✅ |
| C6. AG-UI Protocol | 30 | 30 | ✅ |
| D1. Orchestration Policies | 7 | 7 | ✅ |
| D6. Route Management | 7 | 7 | ✅ |
| E1. Audit | 8 | 8 | ✅ |
| F1. Authentication | 5 | 5 | ✅ |
| F10. Code Interpreter | 14 | 14 | ✅ |

---

## P41-P50: Handler Name Spot Checks

| # | Section | api-ref handler | Actual handler | ✅/❌ |
|---|---------|----------------|----------------|-------|
| P41 | A1 | `create_agent` | `create_agent` | ✅ |
| P42 | A1 | `list_agents` | `list_agents` | ✅ |
| P43 | A2 | `execute_workflow` | `execute_workflow` | ✅ |
| P44 | A3 | `get_execution` | `get_execution` | ✅ |
| P45 | D9 | `receive_webhook` | `n8n_webhook` | ❌ |
| P46 | A4 | `create_checkpoint` | `create_checkpoint` | ✅ |
| P47 | A2 | `auto_layout_workflow_graph` | `auto_layout_workflow_graph` | ✅ |
| P48 | A2 | `get_workflow_graph` | `get_workflow_graph` | ✅ |
| P49 | A1 | `run_agent` | `run_agent` | ✅ |
| P50 | Sys | `health_check` | `health_check` | ✅ |

### D9 (n8n) Handler Names — All 7 Wrong

| api-ref handler | Actual handler |
|----------------|----------------|
| `receive_webhook` | `n8n_webhook` |
| `receive_workflow_webhook` | `n8n_webhook_by_workflow` |
| `get_status` | `get_n8n_status` |
| `get_config` | `get_n8n_config` |
| `update_config` | `update_n8n_config` |
| `receive_callback` | `n8n_callback` |
| `get_callback_status` | `get_callback_result` |

---

## Required Fixes

### Fix 1: Total endpoint count (line 5)
- **Current**: `568 REST + 4 WebSocket = **572 endpoints**`
- **Correct**: `587 REST + 4 WebSocket = **591 endpoints**`

### Fix 2: TOC domain totals (lines 12-16)
- Domain A: 80 → 90
- Domain B: 148 → 196
- Domain D: 42 → 42 (unique, since D8 is cross-ref) or 56 (if counting D8 line)

### Fix 3: D9 handler names (lines 819-825)
- 7 handler names need correction to match actual code

---

## Score: 40/50

- P1-P15 (per-file counts): 15/15 ✅
- P16-P25 (domain aggregation): 7/10 (3 TOC mismatches)
- P26-P30 (total verification): 3/5 (total is 591, not 572)
- P31-P40 (section headers): 10/10 ✅
- P41-P50 (handler names): 9/10 (1 wrong in spot check, 7 total wrong in n8n)

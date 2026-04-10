# V9 E2E Flow Diagram Verification Report

> **Date**: 2026-03-31
> **Scope**: `00-stats.md` lines 70-296 (End-to-End Execution Flow Diagram)
> **Method**: Cross-reference against all 11 layer detail files + source code spot checks

---

## Layer-by-Layer Verification

### Layer 1: Frontend
| Claim | Diagram Value | Layer-01 Value | Status |
|-------|--------------|----------------|--------|
| File count | 236 .ts/.tsx | 236 (210 source + 26 test) | ✅ Correct |
| LOC | 54,238 | ~54K | ✅ Correct |
| Pages | 46 | 46 | ✅ Correct |
| Components | 120 | **116 source** (68 line in layer-01) | ❌ Should be 116 |
| Hooks | 25 | 25 | ✅ Correct |
| Tech stack | React 18 + TS + Vite (3005) | Confirmed | ✅ Correct |
| 5 UI blocks | Unified Chat, Agent Dashboard, HITL Approval, Swarm Panel, Workflow DAG | Confirmed | ✅ Correct |
| DevUI (15 comp) | 15 | 15 | ✅ Correct |
| Stores list | authStore, unifiedChatStore, swarmStore | Confirmed (store/ + stores/) | ✅ Correct |
| Fetch API | Yes | Confirmed (NOT Axios) | ✅ Correct |

**Issues**: Component count 120 should be **116** (source files in component dirs per layer-01 table).

---

### Layer 2: API Gateway
| Claim | Diagram Value | Layer-02 Value | Status |
|-------|--------------|----------------|--------|
| Endpoints | 591 | 591 (587 REST + 4 WS) | ✅ Correct |
| Route modules | 43 | 43 | ✅ Correct |
| Files | 153 | **152** | ❌ Should be 152 |
| LOC | 47,377 | **46,341** | ❌ Should be 46,341 |
| Auth | JWT (HS256) + protected_router | Confirmed | ✅ Correct |

**Issues**: Files (153 vs 152) and LOC (47,377 vs 46,341) both differ from layer-02 identity card.

---

### Layer 3: AG-UI Protocol
| Claim | Diagram Value | Layer-03 Value | Status |
|-------|--------------|----------------|--------|
| Files | 27 | 27 (+ 1 mediator_bridge.py = 28 effective) | ✅ Correct (core 27) |
| LOC | 10,329 | 10,329 | ✅ Correct |
| Event types | 11 | 11 (AGUIEventType enum confirmed) | ✅ Correct |
| Features | 7 | 7 features listed | ✅ Correct |
| Feature list | SharedState, FileAttach, ThreadStore, ExtThinking, HITL, Swarm | Confirmed | ✅ Correct |

**Issues**: None.

---

### Layer 4: Input & Routing
| Claim | Diagram Value | Layer-04 Value | Status |
|-------|--------------|----------------|--------|
| Files | 55 | 55 | ✅ Correct |
| LOC | 20,272 | 20,272 | ✅ Correct |
| InputGateway 4 items | ServiceNow/Prometheus/UserInput/SchemaValidator | Confirmed (3 handlers + 1 validator) | ✅ Correct |
| 3-tier routing | Pattern <1ms, Semantic <100ms, LLM <2000ms | Confirmed | ✅ Correct |
| GuidedDialog files | 5 files | **4 files** (+ __init__.py = 5) | ⚠️ Depends on counting __init__.py |
| GuidedDialog LOC | ~3,314 | **~3,530** (sum from layer-04 file table) | ❌ Should be ~3,530 |
| RiskAssessor files | 3 files | 3 files | ✅ Correct |
| RiskAssessor LOC | ~1,200 | **~1,350** (639+712 excl init) | ❌ Should be ~1,350 |
| RiskAssessor 7 dimensions | 7 | 7 confirmed | ✅ Correct |
| HITL timeout | 30 min → EXPIRED | Source: `default_timeout_minutes=30` | ✅ Correct |

**Issues**: GuidedDialog LOC (3,314 vs 3,530), RiskAssessor LOC (1,200 vs 1,350).

---

### Layer 5: Hybrid Orchestration
| Claim | Diagram Value | Layer-05 Value | Status |
|-------|--------------|----------------|--------|
| Files | 89 | **90+** | ⚠️ Close but layer-05 says "90+" |
| LOC | 28,800 | **~26K** | ❌ Significant discrepancy (~26K vs 28,800) |
| 7-Handler Pipeline order | ① Context → ② Routing → ③ Dialog → ④ Approval → ⑤ Agent → ⑥ Execution → ⑦ Observability | Confirmed per handler file listing | ✅ Correct |
| FrameworkSelector 4 paths | MAF/Claude/Hybrid/Swarm | Confirmed (ExecutionMode 4 modes) | ✅ Correct |
| Checkpoint | PG+Redis+InMemory | Confirmed (4 backends) | ✅ Correct |
| MediatorEventBridge (P40) | Present | Confirmed (mediator_bridge.py) | ✅ Correct |
| AG-UI Server (11 events) | Present | Confirmed (SSE stream) | ✅ Correct |
| ContextBridge | Present | Confirmed (bridge.py, 933 LOC) | ✅ Correct |
| Task Dispatcher | Present | Confirmed | ✅ Correct |

**Issues**: File count (89 vs 90+) and LOC (28,800 vs ~26K). The LOC discrepancy is significant — layer-05 says ~26K but diagram says 28,800. The 00-stats.md summary table also says 28,800 so it may be the layer-05 identity card that is approximate.

---

### Layer 6: MAF Builder Layer
| Claim | Diagram Value | Layer-06 Value | Status |
|-------|--------------|----------------|--------|
| Files | 57 | 57 (R7 verified) | ✅ Correct |
| LOC | 38,082 | 38,082 (R4 verified) | ✅ Correct |
| Builder Adapters | 9 (7 MAF compliant) | 9 builder adapters confirmed | ✅ Correct |
| 6 Builders shown | Concurrent, Handoff, GroupChat, Magentic, Swarm, Custom(DSL,A2A) | Layer-06 shows 9 total: +A2A, Edge, Assistant | ⚠️ Diagram only shows 6 boxes for space reasons |

**Issues**: Diagram shows only 6 builder boxes but claims "9 Builder Adapters" in header. The boxes collapse A2A into Custom and omit Edge/Assistant. Functionally accurate but visually incomplete.

---

### Layer 7: Claude SDK Worker
| Claim | Diagram Value | Layer-07 Value | Status |
|-------|--------------|----------------|--------|
| Files | 48 | **47** | ❌ Should be 47 |
| LOC | 15,406 | 15,406 (R4 verified) | ✅ Correct |
| Autonomous | 7 files | 7 files (init + types + analyzer + planner + executor + verifier + retry + fallback = 8? But "autonomous/" section has 7 listed) | ⚠️ Needs recount |
| Hook System | 6 files | 6 files (init + base + approval + approval_delegate + sandbox + rate_limit + audit = 7) | ❌ Should be 7 |
| Tool System | 10 tools | 10 tools (6 file + 2 command + 2 web) | ✅ Correct |
| Coordinator | 4 modes | 4 modes (WORKFLOW/CHAT/HYBRID/SWARM) | ✅ Correct |
| SmartFallback | 6 strategies | 6 FallbackStrategy confirmed | ✅ Correct |

**Issues**: Files (48 vs 47), Hook System (6 vs 7 files). Autonomous file count needs recount — layer-07 lists 7 autonomous files (__init__ + types + analyzer + planner + executor + verifier + retry + fallback = 8 entries, but __init__ may not be counted).

---

### Layer 8: MCP Tools
| Claim | Diagram Value | Layer-08 Value | Status |
|-------|--------------|----------------|--------|
| Files | 73 | 73 (R4 verified) | ✅ Correct |
| LOC | 20,847 | 20,847 (R4 verified) | ✅ Correct |
| Servers | 9 | 9 | ✅ Correct |
| Total tools | 70 | 70 | ✅ Correct |
| Azure tools | 23 | 23 | ✅ Correct |
| Shell tools | 3 | 3 | ✅ Correct |
| Filesystem tools | 6 | 6 | ✅ Correct |
| SSH tools | 6 | 6 | ✅ Correct |
| LDAP tools | 6 | 6 | ✅ Correct |
| ServiceNow tools | 6 | 6 | ✅ Correct |
| n8n tools | 6 | 6 | ✅ Correct |
| D365 tools | 6 | 6 | ✅ Correct |
| ADF tools | 8 | 8 | ✅ Correct |
| Tool sum | 23+3+6+6+6+6+6+6+8 = 70 | 70 | ✅ Correct |
| CommandWhitelist | 24 blocked + 79 allowed | "79 DEFAULT_WHITELIST, 24 BLOCKED_PATTERNS" | ✅ Correct |

**Issues**: None.

---

### Layer 9: Supporting Integrations
| Claim | Diagram Value | Layer-09 Value | Status |
|-------|--------------|----------------|--------|
| Files | 77 | 77 | ✅ Correct |
| LOC | 22,604 | ~22,600 | ✅ Correct |
| Modules | 14 | 14 | ✅ Correct |
| 14 module names | swarm, llm, memory, knowledge, patrol, correlation, rootcause, incident, learning, audit, a2a, n8n, contracts, shared | All 14 confirmed in layer-09 TOC | ✅ Correct |

**Issues**: None.

---

### Observability + AG-UI Streaming Section
| Claim | Diagram Value | Layer Reference | Status |
|-------|--------------|-----------------|--------|
| 11 event types | 11 | AGUIEventType enum: 11 members | ✅ Correct |
| TEXT_MESSAGE_START/CONTENT/END | Listed | Confirmed | ✅ Correct |
| TOOL_CALL_START/ARGS/END | Listed | Confirmed | ✅ Correct |
| APPROVAL_REQUEST | Listed | **Not in AGUIEventType enum** — this is handled via CUSTOM event | ⚠️ Misleading |
| STATE_SNAPSHOT/DELTA | Listed | Confirmed | ✅ Correct |
| RUN_STARTED/FINISHED | Listed | Confirmed | ✅ Correct |
| CUSTOM (swarm_*, workflow_*) | Listed | Confirmed | ✅ Correct |
| MediatorEventBridge (Phase 40) | Listed | Confirmed (mediator_bridge.py) | ✅ Correct |

**Issues**: APPROVAL_REQUEST is listed as a separate event category but it's actually sent as a CUSTOM event type. The diagram implies it's one of the 11 types, which is misleading. The 11 types are: RUN_STARTED, RUN_FINISHED, TEXT_MESSAGE_START/CONTENT/END (3), TOOL_CALL_START/ARGS/END (3), STATE_SNAPSHOT, STATE_DELTA, CUSTOM = 11. Approval uses CUSTOM.

---

### Layer 10: Domain
| Claim | Diagram Value | Layer-10 Value | Status |
|-------|--------------|----------------|--------|
| Files | 117 | 117 | ✅ Correct |
| LOC | 47,637 | 47,637 | ✅ Correct |
| Modules | 21 | 21 | ✅ Correct |
| sessions/ | 33 files, 15,473 LOC | 33 files, ~15,473 LOC | ✅ Correct |
| orchestration/ | 22 files, DEPRECATED | 22 files, DEPRECATED | ✅ Correct |
| 5 InMemory modules | audit, routing, learning, versioning, devtools | Confirmed per layer-10 | ✅ Correct |

**Issues**: None.

---

### Layer 11: Infrastructure + Core
| Claim | Diagram Value | Layer-11 Value | Status |
|-------|--------------|----------------|--------|
| Files | 95 | 95 | ✅ Correct |
| LOC | 21,953 | 21,953 | ✅ Correct |
| PostgreSQL 16 | 8 ORM models | **9 ORM models** (layer-11 line 36-37) | ❌ Should be 9 |
| Redis 7 | LLM cache + checkpoint + locks | Confirmed | ✅ Correct |
| Storage | S3 + Local | Confirmed | ✅ Correct |
| ARQ Workers | Redis-backed, Phase 40 | Confirmed | ✅ Correct |
| Core subsystems | Security, Performance, Sandbox | Confirmed (JWT+RBAC, Profiler+Metrics, Code Exec) | ✅ Correct |
| messaging/ = STUB | 1 line | "1 line, RabbitMQ 無實現" confirmed | ✅ Correct |

**Issues**: ORM model count is **8 in diagram but 9 in layer-11**. Layer-11 explicitly states "9 ORM Models" (line 36) and lists 9 model files (base + user + agent + workflow + execution + checkpoint + session + audit = 8 files with session.py containing SessionModel + MessageModel + AttachmentModel = at least 9 ORM classes).

---

### E2E Flow Verification Results + V8→V9 Improvements
| Claim | Diagram Value | Flows File | Status |
|-------|--------------|------------|--------|
| Flow 1 Chat | ✅ CONNECTED (Phase 35) | Confirmed | ✅ Correct |
| Flow 2 Agent CRUD | ✅ FULLY CONNECTED | Confirmed | ✅ Correct |
| Flow 3 Workflow | ✅ CONNECTED (Phase 39) | Confirmed | ✅ Correct |
| Flow 4 HITL | ⚠ IMPROVED | Confirmed | ✅ Correct |
| Flow 5 Swarm | ⚠ UPGRADED (Phase 43) | Confirmed | ✅ Correct |
| 7 Handlers (not 6) | "7 Handlers" in improvements list | Confirmed (diagram shows 7-Handler Pipeline) | ✅ Correct |
| V8→V9 improvements list | 7 items listed | All confirmed | ✅ Correct |

**Issues**: None.

---

## Summary of Required Corrections

| # | Location (line) | Current Value | Correct Value | Severity |
|---|----------------|---------------|---------------|----------|
| 1 | L81 | `120 components` | `116 components` | Medium |
| 2 | L98 | `153 files` | `152 files` | Low |
| 3 | L98 | `47,377 LOC` | `46,341 LOC` | Medium |
| 4 | L124 | `~3,314 LOC` (GuidedDialog) | `~3,530 LOC` | Low |
| 5 | L124 | `~1,200 LOC` (RiskAssessor) | `~1,350 LOC` | Low |
| 6 | L155 | `89 files, 28,800 LOC` | `90+ files, ~26K LOC` (per layer-05) | Medium |
| 7 | L192 | `48 files` (Claude SDK) | `47 files` | Low |
| 8 | L198 | `Hook System (6 files)` | `Hook System (7 files)` | Low |
| 9 | L273 | `PostgreSQL 16 (8 ORM models)` | `PostgreSQL 16 (9 ORM models)` | Medium |
| 10 | L258 | `APPROVAL_REQUEST` as separate event category | It's actually a CUSTOM event subtype | Low (informational) |

**Total**: 10 discrepancies found (0 Critical, 4 Medium, 6 Low)

### Recommendation

Items #1, #3, #6, #9 are the most impactful corrections as they affect understanding of system scale. Item #9 (ORM models 8→9) was specifically noted as a Wave 29 correction that should have been applied. Items #2, #4, #5, #7, #8 are minor numeric discrepancies. Item #10 is informational — the APPROVAL_REQUEST listing is not wrong per se, but could mislead readers into thinking it's a separate AGUIEventType enum member.

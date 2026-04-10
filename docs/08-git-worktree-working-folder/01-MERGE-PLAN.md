# PoC Agent Team V4 → Main Branch Merge Plan

## Overview

| Item | Value |
|------|-------|
| **Source Branch** | `poc/agent-team` |
| **Target Branch** | `main` |
| **Common Ancestor** | `845a32e` |
| **PoC Commits** | 90 commits |
| **Files Changed** | 90 files |
| **Lines** | +16,858 / -552 |
| **Conflict Risk** | **ZERO** — main has 0 new commits since PoC branched |
| **Date** | 2026-04-10 |

## What This Merge Brings

### New Modules (PoC Core)
| Directory | Files | Purpose |
|-----------|-------|---------|
| `backend/src/integrations/poc/` | 9 files | Agent Team engine (work loop, tools, HITL, memory, shared task list) |
| `backend/src/api/v1/poc/` | 1 file (3,304 LOC) | 4 test modes + streaming + approvals + memory endpoints |
| `frontend/src/pages/AgentTeamTestPage.tsx` | 1 file (1,502 LOC) | Test UI for all 4 modes |
| `frontend/src/hooks/useOrchestratorSSE.ts` | 1 file (494 LOC) | SSE streaming hook |

### New Supporting Modules
| Directory | Files | Purpose |
|-----------|-------|---------|
| `backend/src/integrations/memory/` | 3 new files | context_budget.py, extraction.py, consolidation.py |
| `backend/src/integrations/orchestration/transcript/` | 3 files | Append-only execution log (Redis) |
| `backend/src/integrations/orchestration/approval/` | 2 files | Unified approval service |
| `backend/src/integrations/orchestration/resume/` | 2 files | Checkpoint resume service |
| `backend/src/integrations/hybrid/orchestrator/` | 3 new files | sse_events.py, tools.py, agent_handler.py (enhanced) |
| `backend/src/integrations/llm/` | 2 new files | azure_openai.py, protocol.py |
| `backend/src/integrations/swarm/` | 3 new files | task_decomposer.py, worker_executor.py, worker_roles.py |

### Modified Existing Files
| File | Change |
|------|--------|
| `frontend/src/App.tsx` | +4 lines (AgentTeamTestPage route) |
| `frontend/vite.config.ts` | Proxy port changed (needs fix, see Pre-Merge Fixes) |
| `backend/src/api/v1/__init__.py` | +4 lines (poc router registration) |
| `backend/src/integrations/hybrid/orchestrator/mediator.py` | +314 lines (enhanced) |
| `backend/src/integrations/memory/unified_memory.py` | +276 lines (enhanced) |
| Sprint planning docs | Phase 42-47 plans and checklists |

## Pre-Merge Fixes Required

See `02-PRE-MERGE-FIXES.md` for details. Summary:

| Fix | Severity | Reason |
|-----|----------|--------|
| Vite proxy port 8044 → 8000 | CRITICAL | Main backend runs on 8000, not 8044 |
| Add qdrant-client to requirements.txt | HIGH | PoC imports it but it's missing from deps |

## Merge Procedure

See `03-MERGE-STEPS.md` for step-by-step commands.

## Post-Merge Verification

See `04-POST-MERGE-VERIFICATION.md` for testing checklist.

## Rollback

See `05-ROLLBACK-GUIDE.md` for emergency rollback procedure.

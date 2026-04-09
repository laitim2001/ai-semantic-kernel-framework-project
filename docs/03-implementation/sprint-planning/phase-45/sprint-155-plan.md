# Sprint 155 Plan - U3: Memory/Transcript Integration

## Phase 45: Agent Team V4 - P1 Upgrades

### Sprint Goal
Integrate cross-session memory retrieval and post-execution memory storage for agent team, matching CC's sidechain transcript pattern.

---

## User Stories

### US-155-1: Pre-Execution Memory Retrieval
**As** the agent team,
**I want** to retrieve relevant past findings before starting work,
**So that** agents benefit from previous investigations.

### US-155-2: Post-Execution Memory Storage
**As** the system,
**I want** to store synthesis results and execution transcripts,
**So that** future runs can reference past findings.

---

## Technical Specification

### Three Integration Points
1. Pre-Phase 0: `retrieve_for_goal()` → inject into TeamLead + agent prompts
2. Post-Phase 2: `store_synthesis()` → save findings as long-term memory
3. Post-Phase 2: `store_transcript()` → save full execution record

### Reused Infrastructure
- OrchestratorMemoryManager from `hybrid/orchestrator/memory_manager.py`
- UnifiedMemoryManager from `memory/unified_memory.py`
- mem0/Qdrant integration

---

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/src/integrations/poc/memory_integration.py` | NEW | TeamMemoryIntegration wrapper (~180 LOC) |
| `backend/src/integrations/poc/agent_work_loop.py` | MODIFY | Pre/post memory hooks |
| `backend/src/api/v1/poc/agent_team_poc.py` | MODIFY | Pass user_id |

---

## Acceptance Criteria

- [ ] First execution: no memory context (normal)
- [ ] Second execution same topic: context includes prior results
- [ ] Transcript stored in memory system
- [ ] Memory disabled (MEM0_ENABLED=false) → graceful fallback

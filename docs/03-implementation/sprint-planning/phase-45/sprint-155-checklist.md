# Sprint 155 Checklist - U3: Memory/Transcript Integration

## Reference
- Plan: [sprint-155-plan.md](sprint-155-plan.md)

---

## Implementation

- [ ] Create `memory_integration.py`
  - [ ] TeamMemoryIntegration class
  - [ ] retrieve_for_goal() — search past memories by task
  - [ ] store_synthesis() — save team findings as long-term memory
  - [ ] store_transcript() — save full execution record
  - [ ] _format_as_conversation() helper
  - [ ] _create_memory_integration() factory with graceful fallback

- [ ] Modify `agent_work_loop.py`
  - [ ] Pre-Phase 0: memory retrieval
  - [ ] Memory context injection into TeamLead and agent prompts
  - [ ] Post-Phase 2: synthesis storage
  - [ ] Post-Phase 2: transcript storage

## Verification

- [ ] MEM0_ENABLED=true: memories retrieved and stored
- [ ] MEM0_ENABLED=false: graceful fallback, no errors
- [ ] Second run retrieves first run's synthesis

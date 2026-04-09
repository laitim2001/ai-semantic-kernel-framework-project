# Sprint 154 Checklist - U2: HITL Approval Gate

## Reference
- Plan: [sprint-154-plan.md](sprint-154-plan.md)
- Phase: 45 (Agent Team V4 - P1 Upgrades)

---

## Implementation

- [ ] Create `approval_gate.py`
  - [ ] ToolRiskLevel enum (LOW/MEDIUM/HIGH)
  - [ ] HIGH_RISK_TOOLS / MEDIUM_RISK_TOOLS sets
  - [ ] `assess_tool_risk(tool_name)` function
  - [ ] `requires_approval(tool_name)` function
  - [ ] `request_and_await_approval()` async helper

- [ ] Modify `agent_work_loop.py`
  - [ ] Import and integrate approval gate in _agent_work_loop
  - [ ] Pass hitl_controller through to work loop
  - [ ] Handle approved/rejected/expired outcomes

- [ ] Modify `agent_team_poc.py`
  - [ ] Initialize HITLController via create_hitl_controller()
  - [ ] Pass to run_parallel_team()

- [ ] Modify `AgentTeamTestPage.tsx`
  - [ ] Approval dialog component for team execution

## Verification

- [ ] HIGH risk tool triggers APPROVAL_REQUIRED SSE
- [ ] Approve resumes agent; Reject skips tool
- [ ] Other agents continue during approval wait
- [ ] 5-minute timeout auto-expires

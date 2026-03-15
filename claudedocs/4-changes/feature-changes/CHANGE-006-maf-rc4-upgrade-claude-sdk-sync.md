# CHANGE-006: MAF 1.0.0rc4 Upgrade + Claude SDK Synchronization

## Summary

Upgrade Microsoft Agent Framework from `1.0.0b260114` to `1.0.0rc4` (9 releases, ~2 months gap), resolving 18 breaking changes. Simultaneously fix Claude SDK issues (missing requirements.txt declaration, deprecated Extended Thinking header, stale model ID). Adopt Phase A new features: OpenTelemetry MCP tracing and background responses with continuation tokens.

## Date

2026-03-15 (Planning) → Sprint N execution

## Sprint / Phase

Phase 35: SDK Upgrade & Modernization

## Type

Framework Upgrade + Feature Enhancement

## Status

🚧 In Progress — Planning Complete, Execution Pending

---

## Change Reason

### Why Upgrade Now

1. **9 versions behind** — IPA runs `1.0.0b260114` (Jan 14), latest is `1.0.0rc4` (Mar 11)
2. **GA approaching** — Framework reached RC status, API stabilizing. Delaying to post-GA increases migration from ~34 SP to ~60+ SP
3. **Critical new capabilities** — Native Claude SDK BaseAgent, declarative YAML workflows, Agent Skills, HITL tool approvals
4. **Known bugs fixed** — UTC timezone errors, MCP duplicate registration, session ID leakage on handoff
5. **Annual risk if not upgraded** — NT$150K-1.05M from version drift, security patches missing

### Why Fix Claude SDK Simultaneously

1. `anthropic` package **not declared in requirements.txt** — deployment risk
2. Extended Thinking header `extended-thinking-2024-10` is **deprecated** — may cause API failures
3. Default model `claude-sonnet-4-20250514` is **4 generations behind** latest `claude-sonnet-4-6-20260217`
4. MAF `1.0.0rc4` now includes native Claude SDK BaseAgent — coordination needed

---

## Pre-requisites (Sprint N-1)

| # | Pre-requisite | Verification | Status |
|---|---------------|-------------|--------|
| 1 | Establish test baseline: run `pytest` and record pass/fail counts | `pytest --tb=no -q > test_baseline.txt` | ⏳ Pending |
| 2 | Create feature branch `feature/maf-rc4-upgrade` | `git branch` shows branch | ⏳ Pending |
| 3 | Update reference repo to rc4 tag | `cd reference/agent-framework && git pull` | ⏳ Pending |
| 4 | Backup current `requirements.txt` | Copy exists | ⏳ Pending |
| 5 | Confirm team capacity (2 Sprint minimum) | PM approval | ⏳ Pending |

---

## Components Changed

### Phase 1: MAF Import Namespace Migration (BC-07 — CRITICAL)

> All orchestration builders moved from `agent_framework` to `agent_framework.orchestrations` (or other submodules).

| # | File | Line | Current Import | New Import | Complexity |
|---|------|------|---------------|------------|------------|
| 1 | `builders/concurrent.py` | 83 | `from agent_framework import ConcurrentBuilder` | `from agent_framework.orchestrations import ConcurrentBuilder` | Low |
| 2 | `builders/groupchat.py` | 83 | `from agent_framework import (GroupChatBuilder, ...)` | `from agent_framework.orchestrations import (GroupChatBuilder, ...)` | Low |
| 3 | `builders/handoff.py` | 54 | `from agent_framework import (...)` | `from agent_framework.orchestrations import (...)` | Low |
| 4 | `builders/magentic.py` | 39 | `from agent_framework import (MagenticBuilder, ...)` | `from agent_framework.orchestrations import (MagenticBuilder, ...)` | Low |
| 5 | `builders/nested_workflow.py` | 71 | `from agent_framework import WorkflowBuilder, Workflow, WorkflowExecutor` | `from agent_framework.orchestrations import WorkflowBuilder; from agent_framework.workflows import Workflow, WorkflowExecutor` | Medium |
| 6 | `builders/planning.py` | 31 | `from agent_framework import MagenticBuilder, Workflow` | `from agent_framework.orchestrations import MagenticBuilder; from agent_framework.workflows import Workflow` | Medium |
| 7 | `builders/workflow_executor.py` | 52 | `from agent_framework import (...)` | Split into submodule imports | Medium |
| 8 | `builders/agent_executor.py` | 155-156 | `from agent_framework import ChatAgent, ChatMessage, Role` + `from agent_framework.azure import ...` | `from agent_framework.agents import ChatAgent, ChatMessage, Role` + `from agent_framework.azure import ...` | Low |
| 9 | `core/workflow.py` | 37 | `from agent_framework import Workflow, WorkflowBuilder, Edge, Executor` | Split: workflows + orchestrations | Medium |
| 10 | `core/executor.py` | 38 | `from agent_framework import Executor, WorkflowContext, handler` | `from agent_framework.workflows import Executor, WorkflowContext, handler` | Low |
| 11 | `core/execution.py` | 34 | `from agent_framework import ChatAgent, SequentialBuilder, Workflow` | Split: agents + orchestrations + workflows | Medium |
| 12 | `core/events.py` | 34 | `from agent_framework import WorkflowStatusEvent` | `from agent_framework.workflows import WorkflowStatusEvent` | Low |
| 13 | `core/edge.py` | 29 | `from agent_framework import Edge` | `from agent_framework.workflows import Edge` | Low |
| 14 | `core/approval.py` | 39 | `from agent_framework import Executor, handler, WorkflowContext` | `from agent_framework.workflows import Executor, handler, WorkflowContext` | Low |
| 15 | `core/approval_workflow.py` | 36 | `from agent_framework import Workflow, Edge` | `from agent_framework.workflows import Workflow, Edge` | Low |
| 16 | `multiturn/adapter.py` | 27 | `from agent_framework import (...)` | Submodule imports | Medium |
| 17 | `multiturn/checkpoint_storage.py` | 31 | `from agent_framework import CheckpointStorage, InMemoryCheckpointStorage` | `from agent_framework.checkpoints import CheckpointStorage, InMemoryCheckpointStorage` | Low |
| 18 | `memory/base.py` | 25, 169 | `from agent_framework import Context, ContextProvider` + `MemoryStorage` | Submodule imports | Medium |
| 19 | `workflow.py` | 425 | `from agent_framework import WorkflowBuilder` (dynamic) | `from agent_framework.orchestrations import WorkflowBuilder` | Low |
| 20 | `checkpoint.py` | 102 | `from agent_framework import WorkflowCheckpoint` (dynamic) | `from agent_framework.checkpoints import WorkflowCheckpoint` | Low |
| 21 | `acl/version_detector.py` | 85,135,165 | `import agent_framework` (dynamic) | Keep as-is (version detection) | None |
| 22 | `acl/adapter.py` | 139 | `import agent_framework` (dynamic) | Keep as-is (dynamic loading) | None |
| 23 | `infrastructure/storage/storage_factories.py` | 308 | `from agent_framework import InMemoryCheckpointStorage` | `from agent_framework.checkpoints import InMemoryCheckpointStorage` | Low |

**Total: 23 source files, ~21 need import path changes, 2 ACL files keep as-is**

### Phase 2: Claude SDK Synchronization

| # | File | Change | Complexity |
|---|------|--------|------------|
| 1 | `backend/requirements.txt` | Add `anthropic>=0.84.0` | Trivial |
| 2 | `backend/src/integrations/claude_sdk/client.py:38` | `model: str = "claude-sonnet-4-20250514"` → `"claude-sonnet-4-6-20260217"` | Trivial |
| 3 | `backend/src/integrations/claude_sdk/client.py:260` | `"anthropic-beta": "extended-thinking-2024-10"` → `"interleaved-thinking-2025-05-14"` | Trivial |

### Phase 3: Other Breaking Changes (Verify & Fix If Needed)

| BC | Description | Expected Impact | Action |
|----|-------------|----------------|--------|
| BC-01 | `create_agent` → `as_agent` | LOW — verify in agent_executor.py | Manual check |
| BC-02 | `AgentRunResponse` → `AgentResponse` | NONE — IPA has custom class with same name | Verify no conflict |
| BC-03 | `display_name` removed, `context_provider` singular | LOW — check adapter constructors | Manual check |
| BC-05 | `response_format` raises ValidationError | LOW — check orchestration layer | Manual check |
| BC-06 | AG-UI `run_config` removed | MEDIUM — check ag_ui integration | Manual check |
| BC-08 | `ad_token_provider` → `credential` | LOW — check agent_executor.py | Manual check |
| BC-09 | Exception hierarchy redesign | LOW — search for ServiceException usage | Grep + fix |
| BC-14 | Workflow events `isinstance` → `event.type` | MEDIUM — check events.py | Manual check |

### Phase 4: New Features Adoption (Phase A — Immediate)

| Feature | Files to Create/Modify | Description |
|---------|----------------------|-------------|
| OpenTelemetry MCP Tracing | `integrations/mcp/` config | Enable automatic trace propagation (rc1 built-in) |
| Background Responses | `integrations/agent_framework/builders/` | Add continuation token support for long-running agents |

### Phase 5: New Features Adoption (Phase B — Next Sprint)

| Feature | Files to Create/Modify | Description |
|---------|----------------------|-------------|
| Agent Skills | New: `integrations/agent_framework/skills/` | Create reusable agent skill modules |
| HITL Tool Approvals | `integrations/agent_framework/core/approval.py` | Leverage native MAF tool call approval |

---

## Test Strategy

### Test Execution Priority (5 Stages)

| Stage | Tests | Purpose | Pass Criteria |
|-------|-------|---------|---------------|
| 1 | `python -c "from agent_framework import ..."` | Verify import paths resolve | All 23 imports succeed |
| 2 | `pytest tests/unit/integrations/agent_framework/` | Adapter unit tests | >= baseline pass rate |
| 3 | `pytest tests/unit/infrastructure/` | Storage + checkpoint tests | >= baseline pass rate |
| 4 | `pytest tests/integration/` | Integration tests | >= baseline pass rate |
| 5 | `pytest tests/e2e/` | End-to-end flows | >= baseline pass rate |

### Tests Expected to Need Updates

| Test File | Reason | Fix |
|-----------|--------|-----|
| `tests/mocks/agent_framework_mocks.py` | Mock MAF classes | Update mock import paths |
| `tests/integration/test_phase3_integration.py` | Imports 6 adapters | Should work if adapters updated |
| `tests/e2e/test_ai_autonomous_decision.py` | Patches adapter path | Verify patch targets still valid |
| `tests/performance/test_memory_usage.py` | Imports many adapters | Should work if adapters updated |

---

## Rollback Strategy

| Scenario | Action | Time |
|----------|--------|------|
| Import failures | `git checkout main` in worktree | < 1 min |
| Test failures > 10% regression | Abandon worktree, return to main | < 5 min |
| Partial success | Cherry-pick working commits to new branch | ~30 min |
| Complete success | Merge `feature/maf-rc4-upgrade` to main | Standard PR |

**Worktree approach**: All work in isolated git worktree at `../maf-upgrade/`. Main branch completely unaffected until explicit merge.

---

## Risk Matrix

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| BC-07 import paths incorrect | Medium | HIGH | Verify against rc4 source; test each import individually |
| Undocumented API behavior change | Low | MEDIUM | Full test suite run after each phase |
| pydantic-settings conflict | Very Low | LOW | IPA's pydantic-settings independent of MAF |
| Test suite baseline unknown | Medium | HIGH | **Must establish baseline BEFORE upgrade** |
| Claude SDK header incompatibility | Low | MEDIUM | Test extended thinking with Opus 4.6 after change |

---

## Estimation

| Phase | Story Points | Calendar | Dependencies |
|-------|-------------|----------|-------------|
| Pre-requisites | 2 SP | 1 day | None |
| Phase 1: Import migration | 8 SP | 2-3 days | Pre-req complete |
| Phase 2: Claude SDK sync | 2 SP | 0.5 day | None (parallel) |
| Phase 3: Other BC verification | 5 SP | 1-2 days | Phase 1 complete |
| Phase 4: New features Phase A | 5 SP | 1-2 days | Phase 1+3 complete |
| Phase 5: New features Phase B | 13 SP | 3-4 days | Phase 4 complete |
| **Total** | **~35 SP** | **~2-3 Sprints** | |

---

## Reference Documents

| Document | Location |
|----------|---------|
| MAF Version Gap Analysis | `docs/07-analysis/Overview/full-codebase-analysis/sdk-version-gap/MAF-Version-Gap-Analysis.md` |
| Claude SDK Version Gap Analysis | `docs/07-analysis/Overview/full-codebase-analysis/sdk-version-gap/Claude-SDK-Version-Gap-Analysis.md` |
| MAF Usage Scan | `docs/07-analysis/Overview/full-codebase-analysis/sdk-version-gap/MAF-Usage-Scan-Complete.md` |
| MAF New Features Analysis | `docs/07-analysis/Overview/full-codebase-analysis/sdk-version-gap/MAF-New-Features-Adoption-Analysis.md` |
| MAF Upgrade Risk Assessment | `docs/07-analysis/Overview/full-codebase-analysis/sdk-version-gap/MAF-Upgrade-Risk-Assessment.md` |
| MAF RC4 Upgrade Master Plan | `docs/07-analysis/Overview/full-codebase-analysis/sdk-version-gap/MAF-RC4-Upgrade-Master-Plan.md` |
| Architecture Review Board Report | `docs/07-analysis/Overview/full-codebase-analysis/Architecture-Review-Board-Consensus-Report.md` |
| V8 Issue Registry | `docs/07-analysis/Overview/full-codebase-analysis/phase4-validation/phase4-validation-issue-registry.md` |

---

## Approval

| Role | Name | Status |
|------|------|--------|
| Technical Lead | — | ⏳ Pending |
| Project Owner | Chris | ⏳ Pending |

---

**Created**: 2026-03-15
**Last Updated**: 2026-03-15
**Author**: Architecture Review Board + AI Assistant

# Layer 06: MAF Builders — V9 Deep Semantic Verification (50 pts)

> **Verifier**: Claude Opus 4.6 (1M context)
> **Date**: 2026-03-31
> **Source**: `layer-06-maf-builders.md` (V9)
> **Method**: Direct grep/read of 23 builder source files + 9 core files + ACL/memory/multiturn/tools/assistant

---

## P1-P10: ConcurrentBuilder build() 行為

| # | Claim | Verdict | Evidence |
|---|-------|---------|----------|
| P1 | Base class: `BuilderAdapter[Any, ConcurrentExecutionResult]` | ✅ CORRECT | `concurrent.py:721` — `class ConcurrentBuilderAdapter(BuilderAdapter[Any, ConcurrentExecutionResult])` |
| P2 | 4 modes: ALL, ANY, MAJORITY, FIRST_SUCCESS | ✅ CORRECT | `concurrent.py:97-118` — `ConcurrentMode` enum with exactly 4 values |
| P3 | GatewayType: PARALLEL_SPLIT, PARALLEL_JOIN, INCLUSIVE_GATEWAY | ✅ CORRECT | `concurrent.py:125-142` — 3 gateway types |
| P4 | JoinCondition: ALL, ANY, FIRST, N_OF_M | ✅ CORRECT | `concurrent.py:145-164` — 4 join conditions |
| P5 | MergeStrategy: COLLECT_ALL, MERGE_DICT, FIRST_RESULT, AGGREGATE | ✅ CORRECT | `concurrent.py:167-183` — 4 merge strategies |
| P6 | `ExecutorProtocol` is `runtime_checkable` | ✅ CORRECT | `concurrent.py:242-243` — `@runtime_checkable` decorator present |
| P7 | build() creates `ConcurrentBuilder(participants=participants)` | ✅ CORRECT | `concurrent.py:1073` — `self._builder = ConcurrentBuilder(participants=participants)` |
| P8 | Import at module level line 83 | ✅ CORRECT | `concurrent.py:83` — `from agent_framework.orchestrations import ConcurrentBuilder` |
| P9 | ConcurrentTaskConfig has `executor: Union[ExecutorProtocol, Callable[..., Any]]` | ✅ CORRECT | `concurrent.py:290` — exact type match |
| P10 | ConcurrentExecutionResult `.success` checks `failed_count == 0 or completed_count > 0` | ✅ CORRECT | `concurrent.py:358` — `return self.failed_count == 0 or self.completed_count > 0` |

**P1-P10 Score: 10/10**

---

## P11-P15: HandoffBuilder handoff 邏輯

| # | Claim | Verdict | Evidence |
|---|-------|---------|----------|
| P11 | Import: `HandoffBuilder, HandoffAgentUserRequest` at module level line 54 | ✅ CORRECT | `handoff.py:54` — `from agent_framework.orchestrations import HandoffBuilder, HandoffAgentUserRequest` |
| P12 | 2 modes: `HandoffMode.HUMAN_IN_LOOP`, `HandoffMode.AUTONOMOUS` | ✅ CORRECT | `handoff.py:64-78` — exact enum values |
| P13 | build() creates `HandoffBuilder(participants=participants)` then `.build()` | ✅ CORRECT | `handoff.py:584-588` — confirmed builder pattern |
| P14 | Fallback: sets `self._workflow = None` on failure | ✅ CORRECT | `handoff.py:597` — `self._workflow = None` in except block |
| P15 | `_simulate_agent_response` at lines 763-801, uses `asyncio.sleep(0.01)` | ✅ CORRECT | `handoff.py:763` (method def), `handoff.py:779` (`await asyncio.sleep(0.01)`), ends at line 801 |

**P11-P15 Score: 5/5**

---

## P16-P20: GroupChatBuilder voting/termination

| # | Claim | Verdict | Evidence |
|---|-------|---------|----------|
| P16 | 7 speaker selection methods: AUTO, ROUND_ROBIN, RANDOM, MANUAL, CUSTOM, PRIORITY, EXPERTISE | ✅ CORRECT | `groupchat.py:97-118` — `SpeakerSelectionMethod` with all 7 values |
| P17 | 7 termination conditions: MAX_ROUNDS, MAX_MESSAGES, TIMEOUT, KEYWORD, CONSENSUS, NO_PROGRESS, CUSTOM | ✅ CORRECT | `groupchat.py:509-523` — `GroupChatTerminationCondition` with all 7 values |
| P18 | build() creates `GroupChatBuilder(participants=participants)` then `.build()` | ✅ CORRECT | `groupchat.py:1337-1341` — confirmed |
| P19 | Falls back to `_MockGroupChatWorkflow` on failure | ✅ CORRECT | `groupchat.py:1354-1358` — `_MockGroupChatWorkflow` created; class at line 1555 |
| P20 | GroupChat import at module level line 83 | ✅ CORRECT | `groupchat.py:83` — `from agent_framework.orchestrations import (GroupChatBuilder,` |

**P16-P20 Score: 5/5**

---

## P21-P25: MagenticBuilder 特殊行為

| # | Claim | Verdict | Evidence |
|---|-------|---------|----------|
| P21 | Does NOT inherit BuilderAdapter (standalone class) | ✅ CORRECT | `magentic.py:957` — `class MagenticBuilderAdapter:` (no base class) |
| P22 | 3 HumanInterventionKind: PLAN_REVIEW, TOOL_APPROVAL, STALL | ✅ CORRECT | `magentic.py:67-76` — exact 3 values |
| P23 | 6 HumanInterventionDecision: APPROVE, REVISE, REJECT, CONTINUE, REPLAN, GUIDANCE | ✅ CORRECT | `magentic.py:79-91` — exact 6 values |
| P24 | ProgressLedger has 5 items: is_request_satisfied, is_in_loop, is_progress_being_made, next_speaker, instruction_or_question | ✅ CORRECT | `magentic.py:318-333` — all 5 fields present |
| P25 | StandardMagenticManager `_execute_prompt()` falls back to `"[Simulated response for: ...]"` | ✅ CORRECT | `magentic.py:778-785` — exact fallback string confirmed |

**P21-P25 Score: 5/5**

---

## P26-P30: SwarmBuilder/worker 角色和 topology

| # | Claim | Verdict | Evidence |
|---|-------|---------|----------|
| P26 | V9 states: `SwarmOrchestrationBuilder` (builders/swarm.py) does NOT exist — was R8 phantom | ✅ CORRECT | Glob `swarm*.py` in builders/ returned empty |
| P27 | V9 states: `CustomWorkflowBuilder` (builders/custom.py) does NOT exist — was R8 phantom | ✅ CORRECT | Glob `custom*.py` in builders/ returned empty |
| P28 | MagenticStatus: 9 values (IDLE, PLANNING, EXECUTING, WAITING_APPROVAL, STALLED, REPLANNING, COMPLETED, FAILED, CANCELLED) | ✅ CORRECT | `magentic.py:53-64` — all 9 values confirmed |
| P29 | Import: 3 official classes `MagenticBuilder, MagenticManagerBase, StandardMagenticManager` at line 39 | ✅ CORRECT | `magentic.py:39-43` — exact 3 classes imported |
| P30 | build() creates `MagenticBuilder(participants=...)` | ✅ CORRECT | `magentic.py:1288` — `self._builder = MagenticBuilder(participants=...)` in build() |

**P26-P30 Score: 5/5**

---

## P31-P35: CustomBuilder DSL/planning 行為

| # | Claim | Verdict | Evidence |
|---|-------|---------|----------|
| P31 | PlanningAdapter — DecompositionStrategy: SEQUENTIAL, HIERARCHICAL, PARALLEL, HYBRID | ✅ CORRECT | `planning.py:73-81` — exact 4 values |
| P32 | PlanningMode: SIMPLE, DECOMPOSED, DECISION_DRIVEN, ADAPTIVE, FULL | ✅ CORRECT | `planning.py:84-90` — exact 5 values |
| P33 | Domain integration: imports TaskDecomposer, AutonomousDecisionEngine, TrialAndErrorEngine, DynamicPlanner | ✅ CORRECT | `planning.py:35-56` — all 4 domain classes imported |
| P34 | LLM integration: imports `LLMServiceFactory` from `src.integrations.llm` | ✅ CORRECT | `planning.py:63` — `from src.integrations.llm import LLMServiceFactory` |
| P35 | MAF import: `MagenticBuilder` (line 31) + `Workflow` (line 32) at module level | ✅ CORRECT | `planning.py:31-32` — both imports at module level |

**P31-P35 Score: 5/5**

---

## P36-P40: A2ABuilder 和 EdgeRoutingBuilder 行為

| # | Claim | Verdict | Evidence |
|---|-------|---------|----------|
| P36 | edge_routing.py has `FanOutRouter`, `FanInAggregator`, `ConditionalRouter` | ✅ CORRECT | `edge_routing.py:334, 505, 681` — all 3 classes confirmed |
| P37 | NestedWorkflowAdapter — ContextPropagationStrategy: INHERITED, ISOLATED, MERGED, FILTERED | ✅ CORRECT | `nested_workflow.py:85-96` — exact 4 values |
| P38 | NestedWorkflowAdapter — ExecutionMode: SEQUENTIAL, PARALLEL, CONDITIONAL | ✅ CORRECT | `nested_workflow.py:109-121` — exact 3 values |
| P39 | nested_workflow.py imports `WorkflowBuilder, Workflow, WorkflowExecutor` at line 71 | ✅ CORRECT | `nested_workflow.py:71` — `from agent_framework import WorkflowBuilder, Workflow, WorkflowExecutor` |
| P40 | workflow_executor.py imports `WorkflowExecutor, SubWorkflowRequestMessage, SubWorkflowResponseMessage` at line 52 | ✅ CORRECT | `workflow_executor.py:52-54` — all 3 classes imported |

**P36-P40 Score: 5/5**

---

## P41-P45: AssistantBuilder 和 Code Interpreter 行為

| # | Claim | Verdict | Evidence |
|---|-------|---------|----------|
| P41 | CodeInterpreterAdapter — APIMode: RESPONSES, ASSISTANTS, AUTO | ✅ CORRECT | `code_interpreter.py:30-34` — exact 3 values |
| P42 | CodeInterpreterAdapter has NO `from agent_framework` import | ✅ CORRECT | Grep returned no `from agent_framework` in code_interpreter.py |
| P43 | AgentExecutorAdapter lazy imports in `initialize()` at line 155 | ✅ CORRECT | `agent_executor.py:155-156` — `from agent_framework import Agent as ChatAgent, Message as ChatMessage, Role` + `from agent_framework.azure import AzureOpenAIResponsesClient` |
| P44 | AgentExecutorAdapter has singleton `get_agent_executor_adapter()` / `set_agent_executor_adapter()` | ✅ CORRECT | `agent_executor.py:681, 691` — both functions confirmed |
| P45 | V9 correctly classifies CodeInterpreterAdapter as "N/A" for MAF compliance (wraps Azure API, not MAF builder) | ✅ CORRECT | No MAF imports, delegates to assistant/ submodule |

**P41-P45 Score: 5/5**

---

## P46-P50: Migration 層 legacy class 轉換邏輯

| # | Claim | Verdict | Evidence |
|---|-------|---------|----------|
| P46 | concurrent_migration.py — `ConcurrentExecutorAdapter`, `ParallelBranch`, `BranchStatus` | ✅ CORRECT | `concurrent_migration.py:314, 217, 193` — all 3 classes confirmed |
| P47 | handoff_migration.py — `HandoffControllerAdapter` (Phase 2 migration shim) | ✅ CORRECT | `handoff_migration.py:244` — confirmed |
| P48 | handoff_policy.py — IMMEDIATE→autonomous, GRACEFUL→human_in_loop, CONDITIONAL→termination_condition | ✅ CORRECT | `handoff_policy.py:262-289` — exact mapping in `adapt()` method |
| P49 | handoff_capability.py — 4 strategies + 6 CapabilityCategory values | ✅ CORRECT | `handoff_capability.py:108-116` (4 strategies) + `handoff_capability.py:65-82` (6 categories: LANGUAGE, REASONING, KNOWLEDGE, ACTION, INTEGRATION, COMMUNICATION) |
| P50 | L06-M5 claim: `create_priority_selector` exported at both lines 176 and 247 in `builders/__init__.py` | ✅ CORRECT | Grep confirmed exact duplicate at lines 176 and 247 |

**P46-P50 Score: 5/5**

---

## Known Issues Verification (Bonus)

| Issue ID | Claim | Verdict |
|----------|-------|---------|
| L06-C1 | All builders silently fall back to mock on MAF API failure | ✅ CORRECT — confirmed in handoff.py, groupchat.py, concurrent.py |
| L06-C2 | `_simulate_agent_response()` returns hardcoded responses | ✅ CORRECT — `handoff.py:763-801` |
| L06-H1 | MagenticBuilderAdapter does not inherit BuilderAdapter | ✅ CORRECT — standalone class at line 957 |
| L06-H4 | Root `__init__.py` has commented-out imports (lines 114-121) | ✅ CORRECT — lines 114-121 show `# HandoffBuilderAdapter, # GroupChatBuilderAdapter, # MagenticBuilderAdapter, # WorkflowExecutorAdapter` all commented out |
| L06-H5 | StandardMagenticManager falls back to simulated response | ✅ CORRECT — `magentic.py:784-785` |
| L06-M3 | version_detector only has 2 KNOWN_COMPATIBLE entries | ✅ CORRECT — `version_detector.py:19-22` shows `1.0.0b251204` and `1.0.0b250101` only |

---

## Summary

| Category | Points | Score | Errors Found |
|----------|--------|-------|--------------|
| P1-P10: ConcurrentBuilder build() | 10 | **10/10** | 0 |
| P11-P15: HandoffBuilder handoff 邏輯 | 5 | **5/5** | 0 |
| P16-P20: GroupChat voting/termination | 5 | **5/5** | 0 |
| P21-P25: Magentic 特殊行為 | 5 | **5/5** | 0 |
| P26-P30: Swarm/phantom file 驗證 | 5 | **5/5** | 0 |
| P31-P35: Planning DSL 行為 | 5 | **5/5** | 0 |
| P36-P40: EdgeRouting/NestedWorkflow | 5 | **5/5** | 0 |
| P41-P45: Assistant/CodeInterpreter | 5 | **5/5** | 0 |
| P46-P50: Migration 轉換邏輯 | 5 | **5/5** | 0 |
| **TOTAL** | **50** | **50/50** | **0** |

**Verdict: PASS — Zero errors found. All 50 behavioral claims verified against source code.**

The V9 Layer 06 document is highly accurate. Every builder behavior, enum value, import location, line number reference, compliance classification, known issue, and migration class was confirmed by direct source code inspection.

---

**Verification Completed**: 2026-03-31
**Verifier**: Claude Opus 4.6 (1M context)
**Confidence**: HIGH — all 50 points verified via grep + direct file read

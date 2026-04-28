# Sprint 81: S81-3 Claude + MAF Fusion
import asyncio, logging, time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

class DecisionType(str, Enum):
    ROUTE_SELECTION = 'route_selection'
    SKIP_STEP = 'skip_step'
    ABORT = 'abort'
    CONTINUE = 'continue'

class WorkflowStepType(str, Enum):
    EXECUTE = 'execute'
    DECISION = 'decision'

@dataclass
class WorkflowStep:
    step_id: str
    name: str
    step_type: WorkflowStepType
    handler: Optional[Callable] = None
    params: Dict[str, Any] = field(default_factory=dict)
    is_decision_point: bool = False
    next_steps: List[str] = field(default_factory=list)

@dataclass
class ClaudeDecision:
    decision_id: str
    decision_type: DecisionType
    selected_route: Optional[str] = None
    reasoning: str = ''
    confidence: float = 0.0

@dataclass
class WorkflowDefinition:
    workflow_id: str
    name: str
    steps: List[WorkflowStep] = field(default_factory=list)
    entry_point: Optional[str] = None

@dataclass
class ExecutionState:
    execution_id: str
    workflow_id: str
    current_step: Optional[str] = None
    completed_steps: List[str] = field(default_factory=list)
    decisions: List[ClaudeDecision] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    status: str = 'running'

@dataclass
class StepResult:
    step_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    decision: Optional[ClaudeDecision] = None

@dataclass
class WorkflowResult:
    execution_id: str
    workflow_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    step_results: List[StepResult] = field(default_factory=list)
    decisions: List[ClaudeDecision] = field(default_factory=list)
    total_duration: float = 0.0

class ClaudeDecisionEngine:
    def __init__(self, claude_client=None):
        self._client = claude_client
        self._history = []

    async def make_decision(self, step, context, routes):
        did = str(uuid4())
        route = routes[0] if routes else None
        d = ClaudeDecision(decision_id=did, decision_type=DecisionType.CONTINUE, selected_route=route, reasoning='Default', confidence=0.5)
        self._history.append(d)
        return d

    def get_history(self): return list(self._history)

class DynamicWorkflow:
    def __init__(self, defn):
        self._defn = defn
        self._steps = {s.step_id: s for s in defn.steps}

    @property
    def definition(self): return self._defn
    @property
    def steps(self): return self._steps

    def add_step(self, step, after=None):
        self._steps[step.step_id] = step
        self._defn.steps.append(step)

    def modify_step(self, sid, params):
        if sid in self._steps:
            self._steps[sid].params.update(params)
            return True
        return False

class ClaudeMAFFusion:
    def __init__(self, claude_client=None):
        self._engine = ClaudeDecisionEngine(claude_client)
        self._workflows = {}
        self._executions = {}

    def register_workflow(self, defn):
        wf = DynamicWorkflow(defn)
        self._workflows[defn.workflow_id] = wf
        return wf

    def get_workflow(self, wid): return self._workflows.get(wid)

    async def execute_with_claude_decisions(self, wid, ctx=None, executor=None):
        wf = self._workflows.get(wid)
        if not wf:
            return WorkflowResult(execution_id=str(uuid4()), workflow_id=wid, success=False, error='Not found')
        eid = str(uuid4())
        start = time.time()
        state = ExecutionState(execution_id=eid, workflow_id=wid, context=ctx or {})
        self._executions[eid] = state
        results = []
        curr = wf.definition.entry_point or (wf.definition.steps[0].step_id if wf.definition.steps else None)
        try:
            while curr and curr in wf.steps:
                step = wf.steps[curr]
                r = await self._run_step(step, state, wf, executor)
                results.append(r)
                if not r.success:
                    return WorkflowResult(execution_id=eid, workflow_id=wid, success=False, error=r.error)
                state.completed_steps.append(curr)
                curr = r.decision.selected_route if r.decision and r.decision.selected_route else (step.next_steps[0] if step.next_steps else None)
            return WorkflowResult(execution_id=eid, workflow_id=wid, success=True, step_results=results, total_duration=time.time()-start)
        except Exception as e:
            return WorkflowResult(execution_id=eid, workflow_id=wid, success=False, error=str(e))

    async def _run_step(self, step, state, wf, executor):
        decision = None
        if step.is_decision_point:
            decision = await self._engine.make_decision(step, state.context, step.next_steps)
            state.decisions.append(decision)
        try:
            if executor:
                out = await executor(step, state.context)
            elif step.handler:
                out = await step.handler(state.context) if asyncio.iscoroutinefunction(step.handler) else step.handler(state.context)
            else:
                out = f'Executed {step.name}'
            return StepResult(step_id=step.step_id, success=True, output=out, decision=decision)
        except Exception as e:
            return StepResult(step_id=step.step_id, success=False, error=str(e), decision=decision)

    async def modify_workflow(self, wid, mod_type, **kw):
        wf = self._workflows.get(wid)
        if not wf: return False
        if mod_type == 'add_step':
            step = WorkflowStep(step_id=kw.get('step_id', str(uuid4())), name=kw.get('name', 'New'), step_type=WorkflowStepType.EXECUTE)
            wf.add_step(step)
            return True
        return False

    def get_statistics(self):
        return {'workflows': len(self._workflows), 'executions': len(self._executions), 'decisions': len(self._engine.get_history())}

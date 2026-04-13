"""
Dispatch Module — Execution routing layer.

Routes the LLM-selected route to the appropriate executor:
  - direct_answer → DirectAnswerExecutor (inline LLM streaming)
  - subagent → SubagentExecutor (parallel MAF agents)
  - team → TeamExecutor (collaborative expert agents)
  - swarm → SwarmExecutor (stub, Phase 46)
  - workflow → WorkflowExecutor (stub, Phase 46)

Phase 45: Orchestration Core (Sprint 155)
"""

from .models import DispatchRequest, DispatchResult
from .service import DispatchService

__all__ = [
    "DispatchRequest",
    "DispatchResult",
    "DispatchService",
]

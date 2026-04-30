"""
Orchestration Pipeline Module

Unified 8-step pipeline merging V8 Orchestration Layer + PoC Pipeline.

Steps:
    1. MemoryStep — Read user memory with token budget
    2. KnowledgeStep — Search enterprise knowledge base (Qdrant)
    3. IntentStep — 3-tier intent routing + completeness check
    4. RiskStep — 7-dimension risk assessment with context
    5. HITLGateStep — Conditional approval gate
    6. LLMRouteStep — LLM-driven route selection
    7. Dispatch — Execute via SubagentExecutor / TeamExecutor / etc.
    8. PostProcessStep — Checkpoint + memory extraction + transcript

Phase 45: Orchestration Core
"""

from .context import PipelineContext
from .exceptions import (
    DialogPauseException,
    HITLPauseException,
    PipelineError,
)
from .service import OrchestrationPipelineService

__all__ = [
    "PipelineContext",
    "DialogPauseException",
    "HITLPauseException",
    "PipelineError",
    "OrchestrationPipelineService",
]
